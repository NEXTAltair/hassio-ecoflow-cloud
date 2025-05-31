import logging
import struct
from typing import Any

from google.protobuf.message import DecodeError

from custom_components.ecoflow_cloud.api import EcoflowApiClient
from custom_components.ecoflow_cloud.devices import BaseDevice, const
from custom_components.ecoflow_cloud.entities import (
    BaseNumberEntity,
    BaseSelectEntity,
    BaseSensorEntity,
    BaseSwitchEntity,
)
from custom_components.ecoflow_cloud.number import (
    ChargingPowerEntity,
    MaxBatteryLevelEntity,
    MinBatteryLevelEntity,
)
from custom_components.ecoflow_cloud.select import (
    DictSelectEntity,
    TimeoutDictSelectEntity,
)
from custom_components.ecoflow_cloud.sensor import (
    AmpSensorEntity,
    CapacitySensorEntity,
    CyclesSensorEntity,
    InAmpSolarSensorEntity,
    InEnergySensorEntity,
    InMilliVoltSensorEntity,
    InVoltSolarSensorEntity,
    InWattsSensorEntity,
    InWattsSolarSensorEntity,
    LevelSensorEntity,
    MilliVoltSensorEntity,
    OutEnergySensorEntity,
    OutVoltDcSensorEntity,
    OutWattsDcSensorEntity,
    OutWattsSensorEntity,
    QuotaStatusSensorEntity,
    RemainSensorEntity,
    TempSensorEntity,
    WattsSensorEntity,
)
from custom_components.ecoflow_cloud.switch import BeeperEntity, EnabledEntity

# Try to import protobuf module
try:
    from custom_components.ecoflow_cloud.devices.internal.proto import (
        ef_dp3_iobroker_pb2 as ecopacket_pb2,
    )  # type: ignore

    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False
    ecopacket_pb2 = None

_LOGGER = logging.getLogger(__name__)

# Delta Pro 3 specific cmdId/cmdFunc to Protobuf message type mapping
DELTA_PRO_3_MESSAGE_DECODERS = {
    2: {  # cmdId
        32: "cmdFunc32_cmdId2_Report",
    },
    17: {  # cmdId
        254: "set_dp3",
    },
    18: {  # cmdId
        254: "setReply_dp3",
    },
    21: {  # cmdId
        254: "DisplayPropertyUpload",
    },
    22: {  # cmdId
        254: "RuntimePropertyUpload",
    },
    23: {  # cmdId
        254: "cmdFunc254_cmdId23_Report",
    },
    50: {  # cmdId
        32: "cmdFunc50_cmdId30_Report",
    },
}


class DeltaPro3(BaseDevice):
    def flat_json(self) -> bool:
        """Delta Pro 3 uses protobuf messages, not flat JSON"""
        return False

    def _xor_decode_pdata(self, pdata: bytes, seq: int) -> bytes:
        """XOR decode pdata using seq as key"""
        if not pdata:
            return b""

        xor_key = seq & 0xFF  # Lower byte of seq
        decoded_payload = bytearray()

        for byte_val in pdata:
            decoded_payload.append((byte_val ^ xor_key) & 0xFF)

        return bytes(decoded_payload)

    def _decode_protobuf_message(
        self, cmd_id: int, cmd_func: int, pdata: bytes
    ) -> dict[str, Any]:
        """Decode protobuf message based on cmd_id and cmd_func"""
        if not PROTOBUF_AVAILABLE:
            _LOGGER.warning(
                "Protobuf not available, cannot decode Delta Pro 3 messages"
            )
            return {}

        # Get the appropriate message class
        cmd_id_map = DELTA_PRO_3_MESSAGE_DECODERS.get(cmd_id)
        if not cmd_id_map:
            _LOGGER.debug(f"No decoder found for cmd_id {cmd_id}")
            return {}

        message_type_name = cmd_id_map.get(cmd_func)
        if not message_type_name:
            _LOGGER.debug(f"No decoder found for cmd_id {cmd_id}, cmd_func {cmd_func}")
            return {}

        # Get the message class from the protobuf module
        message_class = getattr(ecopacket_pb2, message_type_name, None)
        if not message_class:
            _LOGGER.warning(
                f"Message class {message_type_name} not found in protobuf module"
            )
            return {}

        try:
            # Parse the protobuf message
            message = message_class()
            message.ParseFromString(pdata)

            # Convert protobuf message to dict
            result = {}
            for field in message.DESCRIPTOR.fields:
                value = getattr(message, field.name)
                if field.label == field.LABEL_REPEATED:
                    result[field.name] = list(value)
                else:
                    result[field.name] = value

            return result

        except DecodeError as e:
            _LOGGER.warning(
                f"Failed to decode protobuf message {message_type_name}: {e}"
            )
            return {}
        except Exception as e:
            _LOGGER.error(
                f"Unexpected error decoding protobuf message {message_type_name}: {e}"
            )
            return {}

    def _prepare_data(self, raw_data) -> dict[str, Any]:
        """Prepare Delta Pro 3 data by decoding protobuf with XOR."""
        if not isinstance(raw_data, bytes):
            _LOGGER.warning("Delta Pro 3 expects bytes data, got %s", type(raw_data))
            return {}

        if not PROTOBUF_AVAILABLE:
            _LOGGER.warning("Protobuf not available, using fallback JSON decoding")
            return super()._prepare_data(raw_data)

        try:
            # Parse the header first
            if len(raw_data) < 20:  # Minimum header size
                _LOGGER.debug("Raw data too short for Delta Pro 3 header")
                return {}

            # Parse header structure (based on ioBroker implementation)
            header_data = raw_data[:20]
            header = struct.unpack("<HHHHHHHHB", header_data[:17])

            (
                src,
                dest,
                d_src,
                d_dest,
                enc_type,
                check_type,
                cmd_func,
                cmd_id,
                seq_low,
            ) = header
            seq = seq_low

            # Extract pdata
            pdata = raw_data[20:]

            # XOR decode pdata if it exists
            if pdata:
                pdata = self._xor_decode_pdata(pdata, seq)

            # Decode protobuf message
            decoded_data = self._decode_protobuf_message(cmd_id, cmd_func, pdata)

            if decoded_data:
                _LOGGER.debug(
                    f"Successfully decoded Delta Pro 3 message: cmd_id={cmd_id}, cmd_func={cmd_func}"
                )
                return decoded_data
            else:
                _LOGGER.debug(
                    f"No decoder for Delta Pro 3 message: cmd_id={cmd_id}, cmd_func={cmd_func}"
                )
                return {}

        except Exception as e:
            _LOGGER.error(f"Error preparing Delta Pro 3 data: {e}")
            return {}

    def sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
        return [
            # Main Battery System
            LevelSensorEntity(client, self, "bmsBattSoc", const.MAIN_BATTERY_LEVEL)
            .attr("bmsDesignCap", const.ATTR_DESIGN_CAPACITY, 0)
            .attr("bmsFullCap", const.ATTR_FULL_CAPACITY, 0)
            .attr("bmsRemainCap", const.ATTR_REMAIN_CAPACITY, 0),
            CapacitySensorEntity(
                client, self, "bmsDesignCap", const.MAIN_DESIGN_CAPACITY, False
            ),
            CapacitySensorEntity(
                client, self, "bmsFullCap", const.MAIN_FULL_CAPACITY, False
            ),
            CapacitySensorEntity(
                client, self, "bmsRemainCap", const.MAIN_REMAIN_CAPACITY, False
            ),
            LevelSensorEntity(client, self, "bmsBattSoh", const.SOH),
            CyclesSensorEntity(client, self, "bmsCycles", const.CYCLES),
            # Battery Voltage and Current
            MilliVoltSensorEntity(client, self, "bmsBattVol", const.BATTERY_VOLT, False)
            .attr("bmsMinCellVol", const.ATTR_MIN_CELL_VOLT, 0)
            .attr("bmsMaxCellVol", const.ATTR_MAX_CELL_VOLT, 0),
            MilliVoltSensorEntity(
                client, self, "bmsMinCellVol", const.MIN_CELL_VOLT, False
            ),
            MilliVoltSensorEntity(
                client, self, "bmsMaxCellVol", const.MAX_CELL_VOLT, False
            ),
            AmpSensorEntity(
                client, self, "bmsBattAmp", const.MAIN_BATTERY_CURRENT, False
            ),
            # Battery Temperature
            TempSensorEntity(
                client, self, "bmsMaxCellTemp", const.MAX_CELL_TEMP, False
            ),
            TempSensorEntity(
                client, self, "bmsMinCellTemp", const.MIN_CELL_TEMP, False
            ),
            TempSensorEntity(client, self, "bmsMaxMosTemp", const.BATTERY_TEMP)
            .attr("bmsMinCellTemp", const.ATTR_MIN_CELL_TEMP, 0)
            .attr("bmsMaxCellTemp", const.ATTR_MAX_CELL_TEMP, 0),
            # Charge/Discharge Times
            RemainSensorEntity(
                client, self, "bmsChgRemTime", const.CHARGE_REMAINING_TIME
            ),
            RemainSensorEntity(
                client, self, "bmsDsgRemTime", const.DISCHARGE_REMAINING_TIME
            ),
            # Combined System Status
            LevelSensorEntity(client, self, "cmsBattSoc", const.COMBINED_BATTERY_LEVEL),
            # Power Input/Output
            WattsSensorEntity(client, self, "powGetSum", const.TOTAL_OUT_POWER),
            InWattsSensorEntity(client, self, "powInSum", const.TOTAL_IN_POWER),
            # AC Power System
            InWattsSensorEntity(client, self, "powGetAcIn", const.AC_IN_POWER),
            OutWattsSensorEntity(client, self, "powGetAc", const.AC_OUT_POWER),
            OutWattsSensorEntity(client, self, "powGetAcHvOut", "AC HV Output Power"),
            OutWattsSensorEntity(client, self, "powGetAcLvOut", "AC LV Output Power"),
            # AC Input Voltage/Current
            InMilliVoltSensorEntity(
                client, self, "plugInInfoAcInVol", const.AC_IN_VOLT
            ),
            InAmpSolarSensorEntity(
                client, self, "plugInInfoAcInAmp", "AC Input Current"
            ),
            # DC Power System
            OutWattsDcSensorEntity(client, self, "powGet_12v", "12V DC Output Power"),
            OutWattsDcSensorEntity(client, self, "powGet_24v", "24V DC Output Power"),
            OutVoltDcSensorEntity(
                client, self, "powGet_12vVol", "12V DC Output Voltage"
            ),
            OutVoltDcSensorEntity(
                client, self, "powGet_24vVol", "24V DC Output Voltage"
            ),
            # Solar Input
            InWattsSolarSensorEntity(
                client, self, "powGetPvH", "Solar High Voltage Input Power"
            ),
            InWattsSolarSensorEntity(
                client, self, "powGetPvL", "Solar Low Voltage Input Power"
            ),
            InVoltSolarSensorEntity(
                client, self, "powGetPvHVol", "Solar HV Input Voltage"
            ),
            InVoltSolarSensorEntity(
                client, self, "powGetPvLVol", "Solar LV Input Voltage"
            ),
            InAmpSolarSensorEntity(
                client, self, "powGetPvHAmp", "Solar HV Input Current"
            ),
            InAmpSolarSensorEntity(
                client, self, "powGetPvLAmp", "Solar LV Input Current"
            ),
            # USB Ports
            OutWattsSensorEntity(
                client, self, "powGetQcusb1", const.USB_QC_1_OUT_POWER
            ),
            OutWattsSensorEntity(
                client, self, "powGetQcusb2", const.USB_QC_2_OUT_POWER
            ),
            OutWattsSensorEntity(client, self, "powGetTypec1", const.TYPEC_1_OUT_POWER),
            OutWattsSensorEntity(client, self, "powGetTypec2", const.TYPEC_2_OUT_POWER),
            # Power I/O and Extra Battery Ports
            OutWattsDcSensorEntity(
                client, self, "powGet_5p8", "5P8 Power I/O Port Power"
            ),
            OutWattsDcSensorEntity(
                client, self, "powGet_4p8_1", "4P8 Extra Battery Port 1 Power"
            ),
            OutWattsDcSensorEntity(
                client, self, "powGet_4p8_2", "4P8 Extra Battery Port 2 Power"
            ),
            # System Frequencies
            OutWattsSensorEntity(client, self, "acOutFreq", "AC Output Frequency"),
            # Power Management Status
            LevelSensorEntity(client, self, "cmsMaxChgSoc", "Max Charge SOC Setting"),
            LevelSensorEntity(
                client, self, "cmsMinDsgSoc", "Min Discharge SOC Setting"
            ),
            # Energy Counters
            InEnergySensorEntity(client, self, "powInSumEnergy", "Total Input Energy"),
            OutEnergySensorEntity(
                client, self, "powOutSumEnergy", "Total Output Energy"
            ),
            InEnergySensorEntity(
                client, self, "acInEnergyTotal", const.CHARGE_AC_ENERGY
            ),
            OutEnergySensorEntity(
                client, self, "acOutEnergyTotal", const.DISCHARGE_AC_ENERGY
            ),
            InEnergySensorEntity(
                client, self, "pvInEnergyTotal", const.SOLAR_IN_ENERGY
            ),
            OutEnergySensorEntity(
                client, self, "dcOutEnergyTotal", const.DISCHARGE_DC_ENERGY
            ),
            QuotaStatusSensorEntity(client, self),
        ]

    def numbers(self, client: EcoflowApiClient) -> list[BaseNumberEntity]:
        return [
            # Battery Management
            MaxBatteryLevelEntity(
                client,
                self,
                "cmsMaxChgSoc",
                const.MAX_CHARGE_LEVEL,
                50,
                100,
                lambda value: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"cmsMaxChgSoc": value},
                },
            ),
            MinBatteryLevelEntity(
                client,
                self,
                "cmsMinDsgSoc",
                const.MIN_DISCHARGE_LEVEL,
                0,
                30,
                lambda value: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"cmsMinDsgSoc": value},
                },
            ),
            # AC Charging Power
            ChargingPowerEntity(
                client,
                self,
                "plugInInfoAcInChgPowMax",
                const.AC_CHARGING_POWER,
                200,
                3000,
                lambda value: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"plugInInfoAcInChgPowMax": value},
                },
            ),
        ]

    def switches(self, client: EcoflowApiClient) -> list[BaseSwitchEntity]:
        return [
            # Audio Control
            BeeperEntity(
                client,
                self,
                "enBeep",
                const.BEEPER,
                lambda value, command_dict: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"enBeep": value},
                },
            ),
            # AC Output Control
            EnabledEntity(
                client,
                self,
                "cfgHvAcOutOpen",
                "AC HV Output Enabled",
                lambda value, command_dict: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"cfgHvAcOutOpen": value},
                },
            ),
            EnabledEntity(
                client,
                self,
                "cfgLvAcOutOpen",
                "AC LV Output Enabled",
                lambda value, command_dict: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"cfgLvAcOutOpen": value},
                },
            ),
            # DC Output Control
            EnabledEntity(
                client,
                self,
                "cfgDc12vOutOpen",
                "12V DC Output Enabled",
                lambda value, command_dict: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"cfgDc12vOutOpen": value},
                },
            ),
            EnabledEntity(
                client,
                self,
                "cfgDc24vOutOpen",
                "24V DC Output Enabled",
                lambda value, command_dict: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"cfgDc24vOutOpen": value},
                },
            ),
            # Xboost Control
            EnabledEntity(
                client,
                self,
                "xboostEn",
                const.XBOOST_ENABLED,
                lambda value, command_dict: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"xboostEn": value},
                },
            ),
            # Energy Saving
            EnabledEntity(
                client,
                self,
                "acEnergySavingOpen",
                "AC Energy Saving Enabled",
                lambda value, command_dict: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"acEnergySavingOpen": value},
                },
            ),
            # GFCI Control
            EnabledEntity(
                client,
                self,
                "llc_GFCIFlag",
                "GFCI Protection Enabled",
                lambda value, command_dict: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"llc_GFCIFlag": value},
                },
            ),
        ]

    def selects(self, client: EcoflowApiClient) -> list[BaseSelectEntity]:
        return [
            # Screen Timeout
            TimeoutDictSelectEntity(
                client,
                self,
                "screenOffTime",
                const.SCREEN_TIMEOUT,
                const.SCREEN_TIMEOUT_OPTIONS,
                lambda value: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"screenOffTime": value},
                },
            ),
            # AC Standby Timeout
            TimeoutDictSelectEntity(
                client,
                self,
                "acStandbyTime",
                const.AC_TIMEOUT,
                const.AC_TIMEOUT_OPTIONS,
                lambda value: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"acStandbyTime": value},
                },
            ),
            # DC Standby Timeout
            TimeoutDictSelectEntity(
                client,
                self,
                "dcStandbyTime",
                "DC Timeout",
                const.UNIT_TIMEOUT_OPTIONS_LIMITED,
                lambda value: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"dcStandbyTime": value},
                },
            ),
            # AC Output Type
            DictSelectEntity(
                client,
                self,
                "plugInInfoAcOutType",
                "AC Output Type",
                {"0": 0, "1": 1, "2": 2},
                lambda value: {
                    "cmdFunc": 254,
                    "cmdId": 17,
                    "params": {"plugInInfoAcOutType": int(value)},
                },
            ),
        ]
