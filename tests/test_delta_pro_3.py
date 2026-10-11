"""Tests for DELTA Pro 3 MQTT message decoding."""

import base64
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from custom_components.ecoflow_cloud.api import EcoflowApiClient
from custom_components.ecoflow_cloud.devices.internal.delta_pro_3 import (
    DeltaPro3,
    DeltaPro3CommandMessage,
    _create_dp3_proto_command,
)
from custom_components.ecoflow_cloud.devices.internal.proto import ef_dp3_iobroker_pb2 as dp3


class DeltaPro3MessageTests(unittest.TestCase):
    def setUp(self) -> None:
        # Message decoding does not need a live device or an API client.
        self.device = object.__new__(DeltaPro3)

    def test_json_messages_do_not_log_protobuf_errors(self):
        messages = [
            {"params": {"status": 1}},
            {"id": 123, "version": "1.0", "params": {"cmsMaxChgSoc": 80}},
            {"id": 123, "code": "0", "message": "success"},
        ]
        for message in messages:
            for prefix in (b"", b" \t\r\n"):
                with self.subTest(message=message, prefix=prefix):
                    with self.assertNoLogs("custom_components.ecoflow_cloud", level="WARNING"):
                        result = self.device._prepare_data(prefix + json.dumps(message).encode())
                    self.assertEqual(result, message)

    def test_json_status_message_preserves_online_state(self):
        for status in (0, 1):
            with self.subTest(status=status):
                message = {"params": {"status": status}}
                with self.assertNoLogs("custom_components.ecoflow_cloud", level="WARNING"):
                    result = self.device._prepare_data_status_topic(json.dumps(message).encode())
                self.assertEqual(result.online, bool(status))
                self.assertIsNone(result.params)
                self.assertEqual(result.raw_data, message)

    def test_protobuf_telemetry_is_still_decoded(self):
        payload = dp3.DP3DisplayPropertyUpload(bms_batt_soc=65.0).SerializeToString()
        envelope = dp3.DP3HeaderMessage()
        header = envelope.header.add()
        header.cmd_func = 254
        header.cmd_id = 21
        header.pdata = payload
        header.data_len = len(payload)
        raw_data = envelope.SerializeToString()
        for message in (raw_data, base64.b64encode(raw_data)):
            with self.subTest(message=message):
                with self.assertNoLogs("custom_components.ecoflow_cloud", level="WARNING"):
                    result = self.device._prepare_data(message)
                self.assertEqual(result["params"]["bms_batt_soc"], 65.0)

    def test_invalid_json_is_still_logged_and_ignored(self):
        with self.assertLogs("custom_components.ecoflow_cloud", level="ERROR"):
            result = self.device._prepare_data(b'{"params":')
        self.assertEqual(result, {})

    def test_invalid_binary_data_is_still_logged_and_ignored(self):
        with self.assertLogs("custom_components.ecoflow_cloud", level="ERROR"):
            result = self.device._prepare_data(b"\xff\xff")
        self.assertEqual(result, {})


class DeltaPro3CommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.device_sn = "offline-test-device"
        self.device = object.__new__(DeltaPro3)
        self.device.device_data = SimpleNamespace(sn=self.device_sn)
        self.device.device_info = SimpleNamespace(
            sn=self.device_sn,
            public_api=False,
            set_topic="offline-test/set",
        )
        self.device.coordinator = Mock()
        self.device.data = Mock(params={})
        self.device.power_step = 100
        self.client = Mock(spec=EcoflowApiClient)
        self.client.devices = {self.device_sn: self.device}
        self.client.mqtt_client = Mock()
        # Exercise the real serializer/publish path with a mocked MQTT transport.
        self.client.send_set_message.side_effect = lambda *args: EcoflowApiClient.send_set_message(self.client, *args)
        self.entities = {
            entity.mqtt_key: entity
            for entity in (
                self.device.numbers(self.client) + self.device.switches(self.client) + self.device.selects(self.client)
            )
        }

    def decode_command(self, wire_data):
        self.assertIsInstance(wire_data, bytes)
        envelope = dp3.DP3SendHeaderMsg.FromString(wire_data)
        self.assertEqual(len(envelope.msg), 1)
        header = envelope.msg[0]
        self.assertEqual((header.cmd_func, header.cmd_id), (254, 17))
        self.assertEqual((header.src, header.dest, header.d_src, header.d_dest), (32, 2, 1, 1))
        self.assertEqual(header.need_ack, 1)
        self.assertEqual((header.product_id, header.version, header.payload_ver), (1, 19, 1))
        self.assertEqual(header.device_sn, self.device_sn)
        self.assertEqual(header.data_len, len(header.pdata))
        self.assertGreater(header.seq, 0)
        return dp3.DP3SetCommand.FromString(header.pdata)

    def test_supported_entities_send_only_the_requested_protobuf_field(self):
        fields = {
            "cms_max_chg_soc": ("cmsMaxChgSoc", 80),
            "cms_min_dsg_soc": ("cmsMinDsgSoc", 20),
            "plug_in_info_ac_in_chg_pow_max": ("plugInInfoAcInChgPowMax", 500),
            "en_beep": ("enBeep", 1),
            "cfg_hv_ac_out_open": ("cfgHvAcOutOpen", 1),
            "cfg_lv_ac_out_open": ("cfgLvAcOutOpen", 1),
            "cfg_dc_12v_out_open": ("cfgDc12vOutOpen", 1),
            "xboost_en": ("xboostEn", 1),
            "ac_energy_saving_open": ("acEnergySavingOpen", 1),
            "llc_gfci_flag": ("llc_GFCIFlag", 1),
            "screen_off_time": ("screenOffTime", 60),
            "ac_standby_time": ("acStandbyTime", 60),
            "dc_standby_time": ("dcStandbyTime", 60),
        }
        for key, (field_name, value) in fields.items():
            with self.subTest(entity=key):
                command = self.entities[key].command_dict(value)
                self.assertIsInstance(command, DeltaPro3CommandMessage)
                payload = self.decode_command(command.to_mqtt_payload())
                self.assertEqual([(field.name, val) for field, val in payload.ListFields()], [(field_name, value)])

    def test_output_switches_publish_binary_commands_through_the_api(self):
        fields = {
            "cfg_hv_ac_out_open": "cfgHvAcOutOpen",
            "cfg_lv_ac_out_open": "cfgLvAcOutOpen",
            "cfg_dc_12v_out_open": "cfgDc12vOutOpen",
        }
        for key, field_name in fields.items():
            for action, value in (("turn_on", 1), ("turn_off", 0)):
                with self.subTest(entity=key, action=action):
                    self.client.mqtt_client.publish.reset_mock()
                    getattr(self.entities[key], action)()
                    self.client.mqtt_client.publish.assert_called_once()
                    topic, wire_data = self.client.mqtt_client.publish.call_args.args
                    self.assertEqual(topic, "offline-test/set")
                    payload = self.decode_command(wire_data)
                    self.assertTrue(payload.HasField(field_name))
                    self.assertEqual(getattr(payload, field_name), value)
                    self.assertEqual(len(payload.ListFields()), 1)

    def test_unsupported_controls_never_publish_or_change_target_state(self):
        for key in ("cfg_dc_24v_out_open", "plug_in_info_ac_out_type"):
            entity = self.entities[key]
            self.assertFalse(entity.enabled_default)
            self.assertIsNone(entity._command)
        self.entities["cfg_dc_24v_out_open"].turn_on()
        self.entities["cfg_dc_24v_out_open"].turn_off()
        self.entities["plug_in_info_ac_out_type"].select_option("HV Only")
        self.client.mqtt_client.publish.assert_not_called()
        self.device.data.update_to_target_state.assert_not_called()

    def test_ac_charging_range_matches_the_upstream_hardware_fix(self):
        entity = self.entities["plug_in_info_ac_in_chg_pow_max"]
        self.assertEqual((entity.native_min_value, entity.native_max_value), (400, 2900))
        self.assertEqual(entity.native_step, 100)

    def test_command_diagnostics_decode_payload_and_omit_sequence(self):
        command = _create_dp3_proto_command("cmsMaxChgSoc", 80, self.device_sn)
        header = command.to_dict()["DP3SendHeaderMsg"]["msg"][0]
        self.assertEqual(header["pdata"], {"DP3SetCommand": {"cmsMaxChgSoc": 80}})
        self.assertNotIn("seq", header)

    def test_unknown_set_fields_fail_before_any_publish(self):
        for field_name in ("cfgDc24vOutOpen", "plugInInfoAcOutType"):
            with self.subTest(field=field_name), self.assertRaises(ValueError):
                _create_dp3_proto_command(field_name, 1, self.device_sn)
        self.client.mqtt_client.publish.assert_not_called()
        self.device.data.update_to_target_state.assert_not_called()
