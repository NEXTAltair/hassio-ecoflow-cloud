import logging
import json
import base64
import binascii
from typing import Any, Type
from datetime import datetime, timezone
import time

import paho.mqtt.client as mqtt
from google.protobuf import json_format
from google.protobuf.message import Message

# from . import protobuf_mapping as pm
# from . import common
import protobuf_mapping as pm  # main_parser.py でのPYTHONPATH調整を期待
import common

logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(self, config: dict[str, Any]):
        self.config = config  # resolve_topic_placeholders 済みのconfigを期待
        self.output_file_path = config.get("output_file")
        self.message_count = 0
        self.logger = logging.getLogger(__name__)  # self.logger を初期化

    def _decode_protobuf_message(
        self, payload: bytes, expected_type: Type[Message]
    ) -> Message | None:
        """指定されたProtobuf型でペイロードをデコードします。"""
        try:
            message_obj = expected_type()
            message_obj.ParseFromString(payload)
            self.logger.debug(f"Successfully decoded as {expected_type.__name__}")
            return message_obj
        except Exception as e:
            self.logger.warning(f"Failed to decode as {expected_type.__name__}: {e}")
            return None

    def _process_header_pdata(
        self,
        pdata_bytes: bytes | None,
        cmd_id: int,
        cmd_func: int,
        enc_type: int,
        seq: int,
        src: int,  # For XOR decode condition
        context_prefix: str = "pdata",
    ) -> dict[str, Any]:
        """単一のHeaderオブジェクトのpdataを処理します (XORデコード、個別デコード試行)。"""
        self.logger.debug(
            f"    Processing {context_prefix} (cmd_id:{cmd_id}, cmd_func:{cmd_func}, seq:{seq})"
        )
        pdata_processing_result: dict[str, Any] = {}
        pdata_for_final_decode: bytes | None = pdata_bytes

        if pdata_bytes:
            pdata_processing_result["pdata_raw_hex"] = pdata_bytes.hex()[:100] + (
                "..." if len(pdata_bytes.hex()) > 100 else ""
            )

            perform_xor = enc_type == 1 and src != 32
            if perform_xor:
                self.logger.info(f"      XOR decoding {context_prefix} (seq: {seq})")
                try:
                    xored_pdata = common.xor_decode_pdata(pdata_bytes, seq)
                    pdata_processing_result["pdata_xor_decoded_hex"] = (
                        xored_pdata.hex()[:100]
                        + ("..." if len(xored_pdata.hex()) > 100 else "")
                    )
                    pdata_for_final_decode = xored_pdata
                    self.logger.debug(
                        f"        XOR decode successful (len: {len(xored_pdata)})"
                    )
                except Exception as e_xor:
                    pdata_processing_result["error_xor"] = (
                        f"{context_prefix} XOR decode error: {e_xor}"
                    )
                    self.logger.error(
                        f"      {context_prefix} XOR decode error: {e_xor}"
                    )
            else:
                self.logger.debug(
                    f"      No XOR decoding for {context_prefix} (encType={enc_type}, src={src})"
                )

            if pdata_for_final_decode:
                self.logger.info(
                    f"      Attempting to decode {context_prefix} with cmdId={cmd_id}, cmdFunc={cmd_func}"
                )
                specific_decoder = pm.get_protobuf_decoder(cmd_id, cmd_func)
                if specific_decoder:
                    specific_message = self._decode_protobuf_message(
                        pdata_for_final_decode, specific_decoder
                    )
                    if specific_message:
                        pdata_processing_result["pdata_decoded_specific"] = {
                            "type": specific_decoder.__name__,
                            "data": self._protobuf_to_dict_with_hex(specific_message),
                        }
                        self.logger.info(
                            f"        Successfully decoded {context_prefix} as {specific_decoder.__name__}"
                        )
                    else:
                        pdata_processing_result["error_specific_decode"] = (
                            f"Failed to decode {context_prefix} as {specific_decoder.__name__}"
                        )
                        self.logger.warning(
                            f"        Failed to decode {context_prefix} as {specific_decoder.__name__}"
                        )
                else:
                    pdata_processing_result["info_specific_decode"] = (
                        f"No specific decoder for cmdId={cmd_id}, cmdFunc={cmd_func}. Raw/XORed pdata available."
                    )
                    self.logger.info(
                        f"        No specific {context_prefix} decoder for cmdId={cmd_id}, cmdFunc={cmd_func}. Raw/XORed pdata logged."
                    )
            else:
                pdata_processing_result["info_specific_decode"] = (
                    f"No {context_prefix} for final decode (original or XORed)."
                )
                self.logger.debug(
                    f"      No {context_prefix} available for final decode."
                )
        else:
            self.logger.debug(f"    No {context_prefix} bytes provided.")
            pdata_processing_result["info_pdata"] = (
                f"No {context_prefix} bytes provided."
            )
        return pdata_processing_result

    def _process_device_property_message(
        self, msg_topic: str, payload: bytes, output_data: dict
    ) -> None:
        """/app/device/property/{DEVICE_SN} トピックのメッセージを処理します。"""
        self.logger.info(
            f"  Processing device property message from topic: {msg_topic}"
        )
        actual_payload_for_proto = payload

        try:
            decoded_b64_payload = base64.b64decode(
                payload, validate=True
            )  # validate=True for stricter checking
            output_data["payload_base64_decoded_hex"] = decoded_b64_payload.hex()[
                :200
            ] + ("..." if len(decoded_b64_payload.hex()) > 200 else "")
            self.logger.info(
                f"  Base64 decode successful (len: {len(decoded_b64_payload)}) for device_property"
            )
            actual_payload_for_proto = decoded_b64_payload
        except (binascii.Error, ValueError) as e_b64_val:
            self.logger.warning(
                f"  Base64 decode failed for device_property (validate=True): {e_b64_val}. Using original payload."
            )
            output_data["info_base64_decode"] = (
                f"Base64 decode failed (validate=True): {e_b64_val}, using original."
            )
            actual_payload_for_proto = payload
        except Exception as e_b64_other:
            self.logger.error(
                f"  Unexpected error during Base64 decode for device_property: {e_b64_other}"
            )
            output_data["error_base64_decode"] = (
                f"Base64 unexpected error: {e_b64_other}"
            )
            actual_payload_for_proto = payload

        if not actual_payload_for_proto:
            self.logger.warning(
                "  Payload is empty for processing after Base64 attempt for device_property."
            )
            output_data["error"].append(
                "Payload empty after Base64 attempt for device_property."
            )
            return

        decoded_message_obj = self._decode_protobuf_message(
            actual_payload_for_proto, pm.HeaderMessage
        )
        protobuf_type_name = "HeaderMessage"

        if decoded_message_obj and isinstance(decoded_message_obj, pm.HeaderMessage):
            self.logger.info(
                f"  Successfully decoded device_property as HeaderMessage with {len(decoded_message_obj.header)} inner header(s)."
            )
            output_data["decoded_headers"] = []
            for idx, header_item_proto in enumerate(decoded_message_obj.header):
                header_info_dict: dict[str, Any] = {"index": idx}
                self.logger.debug(
                    f"    Processing Header item {idx} from HeaderMessage (device_property)..."
                )
                if not isinstance(header_item_proto, pm.Header):
                    self.logger.warning(
                        f"    Item {idx} is not a Header object, skipping."
                    )
                    header_info_dict["error"] = "Item not a Header object"
                    output_data["decoded_headers"].append(header_info_dict)
                    continue

                header_info_dict["original_header_obj"] = (
                    self._protobuf_to_dict_with_hex(header_item_proto)
                )

                pdata_bytes = getattr(header_item_proto, "pdata", b"")
                cmd_id = getattr(header_item_proto, "cmd_id", 0)
                cmd_func = getattr(header_item_proto, "cmd_func", 0)
                enc_type = getattr(header_item_proto, "enc_type", 0)
                seq = getattr(header_item_proto, "seq", 0)
                src = getattr(header_item_proto, "src", 0)

                header_info_dict["pdata_processing_result"] = (
                    self._process_header_pdata(
                        pdata_bytes,
                        cmd_id,
                        cmd_func,
                        enc_type,
                        seq,
                        src,
                        f"device_property_header_{idx}_pdata",
                    )
                )
                output_data["decoded_headers"].append(header_info_dict)

            # Store the top-level HeaderMessage object as well, if needed for context
            output_data["decoded_protobuf"] = {
                "type": protobuf_type_name,
                "data": self._protobuf_to_dict_with_hex(decoded_message_obj),
            }

        else:  # Fallback to Header if HeaderMessage fails
            self.logger.warning(
                "  HeaderMessage decode failed for device_property. Attempting to decode as single Header."
            )
            decoded_message_obj_header = self._decode_protobuf_message(
                actual_payload_for_proto, pm.Header
            )
            protobuf_type_name = "Header"
            if decoded_message_obj_header and isinstance(
                decoded_message_obj_header, pm.Header
            ):
                self.logger.info(
                    "  Successfully decoded device_property as single Header (fallback)."
                )
                header_item_proto = decoded_message_obj_header
                header_info_dict = {"index": 0, "is_fallback": True}
                header_info_dict["original_header_obj"] = (
                    self._protobuf_to_dict_with_hex(header_item_proto)
                )

                pdata_bytes = getattr(header_item_proto, "pdata", b"")
                cmd_id = getattr(header_item_proto, "cmd_id", 0)
                cmd_func = getattr(header_item_proto, "cmd_func", 0)
                enc_type = getattr(header_item_proto, "enc_type", 0)
                seq = getattr(header_item_proto, "seq", 0)
                src = getattr(header_item_proto, "src", 0)

                header_info_dict["pdata_processing_result"] = (
                    self._process_header_pdata(
                        pdata_bytes,
                        cmd_id,
                        cmd_func,
                        enc_type,
                        seq,
                        src,
                        "device_property_fallback_header_pdata",
                    )
                )
                output_data["decoded_headers"] = [header_info_dict]
                output_data["decoded_protobuf"] = {
                    "type": protobuf_type_name,
                    "data": self._protobuf_to_dict_with_hex(decoded_message_obj_header),
                }
            else:
                self.logger.error(
                    f"  Failed to decode device_property as HeaderMessage or Header. Payload: {actual_payload_for_proto.hex()[:100]}..."
                )
                output_data["error"].append(
                    "Failed to decode as HeaderMessage or Header for device_property."
                )
                output_data["decoded_protobuf"] = None
        return

    def _process_get_reply_message(
        self, topic: str, payload: bytes, output_data: dict
    ) -> None:
        """Process messages from /app/{USER_ID}/{DEVICE_SN}/thing/property/get_reply topic."""
        self.logger.info(f"  Processing get_reply message from topic: {topic}")

        decoded_payload: bytes
        try:
            decoded_payload = base64.b64decode(payload, validate=True)
            self.logger.info(
                f"  Base64 decoded payload for get_reply (len: {len(decoded_payload)}): {decoded_payload.hex()[:100]}..."
            )
            output_data["payload_base64_decoded_hex"] = decoded_payload.hex()[:200] + (
                "..." if len(decoded_payload.hex()) > 200 else ""
            )
        except (binascii.Error, ValueError) as e:
            self.logger.warning(
                f"  Base64 decode failed for get_reply (validate=True): {e}. Using original payload."
            )
            output_data["info_base64_decode"] = (
                f"Base64 decode failed (validate=True): {e}, using original."
            )
            decoded_payload = payload
        except Exception as e_b64_other:
            self.logger.error(
                f"  Unexpected error during Base64 decode for get_reply: {e_b64_other}"
            )
            output_data["error_base64_decode"] = (
                f"Base64 unexpected error: {e_b64_other}"
            )
            decoded_payload = payload

        if not decoded_payload:
            self.logger.warning(
                "  Payload for get_reply is empty after Base64 attempt."
            )
            output_data["error"].append(
                "Payload empty for get_reply after Base64 attempt."
            )
            return

        # Standard processing: Attempt to decode as HeaderMessage, then process internal Headers
        try:
            header_msg = pm.HeaderMessage()
            header_msg.ParseFromString(decoded_payload)
            self.logger.info(
                f"  Successfully parsed get_reply as HeaderMessage with {len(header_msg.header)} inner header(s)."
            )
            output_data["decoded_headers"] = []

            for i, header_proto in enumerate(header_msg.header):
                self.logger.info(
                    f"    Processing inner header {i + 1}/{len(header_msg.header)} from get_reply's HeaderMessage"
                )
                header_dict_entry: dict[str, Any] = {"index": i}
                header_dict_entry["original_header_obj"] = (
                    self._protobuf_to_dict_with_hex(header_proto)
                )

                pdata_bytes = getattr(header_proto, "pdata", b"")
                cmd_id = getattr(header_proto, "cmd_id", 0)
                cmd_func = getattr(header_proto, "cmd_func", 0)
                enc_type = getattr(header_proto, "enc_type", 0)
                seq = getattr(header_proto, "seq", 0)
                src = getattr(header_proto, "src", 0)

                header_dict_entry["pdata_processing_result"] = (
                    self._process_header_pdata(
                        pdata_bytes,
                        cmd_id,
                        cmd_func,
                        enc_type,
                        seq,
                        src,
                        f"get_reply_inner_header_{i}",
                    )
                )
                output_data["decoded_headers"].append(header_dict_entry)

            # Store the top-level HeaderMessage object as well
            output_data["decoded_protobuf"] = {
                "type": "HeaderMessage_from_get_reply",
                "data": self._protobuf_to_dict_with_hex(header_msg),
            }

        except Exception as e_hdr_msg:
            self.logger.error(
                f"  Failed to parse get_reply payload as HeaderMessage: {e_hdr_msg}"
            )
            output_data["error"].append(
                f"Failed to decode get_reply as HeaderMessage: {e_hdr_msg}"
            )
            output_data["decoded_protobuf"] = None
        return

    def _protobuf_to_dict_with_hex(self, message: Message) -> dict[str, Any]:
        """Protobufメッセージを辞書に変換し、bytesフィールドをhex文字列にします。
        MessageToDict は bytes を Base64 文字列にするため、それをデコードして hex に変換します。
        """
        try:
            temp_dict = json_format.MessageToDict(
                message,
                preserving_proto_field_name=True,
                always_print_fields_with_no_presence=True,
                use_integers_for_enums=True,
            )

            def convert_potential_base64_to_hex_recursive(item: Any) -> Any:
                if isinstance(item, dict):
                    return {
                        k: convert_potential_base64_to_hex_recursive(v)
                        for k, v in item.items()
                    }
                elif isinstance(item, list):
                    return [
                        convert_potential_base64_to_hex_recursive(elem) for elem in item
                    ]
                elif isinstance(item, str):
                    # Attempt to decode as Base64. If successful, it was likely a bytes field.
                    try:
                        # Check if it looks like base64 (heuristic, not perfect)
                        # A more robust check might involve regex or checking length divisibility by 4
                        # For now, we assume any string that successfully decodes from base64 was originally bytes.
                        decoded_bytes = base64.b64decode(
                            item.encode("ascii"), validate=False
                        )
                        # If it decodes without error, convert to hex
                        return decoded_bytes.hex()
                    except (binascii.Error, ValueError, UnicodeEncodeError):
                        # Not a Base64 string, or not ASCII encodable (should not happen for b64 from MessageToDict)
                        return item  # Return original string
                return item

            return convert_potential_base64_to_hex_recursive(temp_dict)

        except Exception as e_json:
            self.logger.error(
                f"Error converting protobuf to dict with hex bytes: {e_json}",
                exc_info=True,
            )
            return {"error_converting_to_json": str(e_json)}

    def handle_message(self, msg: mqtt.MQTTMessage) -> None:
        self.message_count += 1
        self.logger.info(
            f"Message received (Topic: {msg.topic}, QoS: {msg.qos}, Retain: {msg.retain}, "
            f"MID: {msg.mid}, Length: {len(msg.payload)}, LocalSeq: {self.message_count})"
        )
        payload_hex_for_log = (
            msg.payload.hex() if isinstance(msg.payload, bytes) else str(msg.payload)
        )[:200]
        self.logger.debug(
            f"  Raw payload (hex or str, truncated): {payload_hex_for_log}..."
        )

        output_data: dict[str, Any] = {
            "timestamp_iso": datetime.now(timezone.utc).isoformat(),
            "timestamp_unix": time.time(),
            "topic": msg.topic,
            "qos": msg.qos,
            "retain": msg.retain,
            "mid": msg.mid,
            "payload_length": len(msg.payload),
            "message_seq_local": self.message_count,
            "payload_raw_hex": (
                msg.payload.hex() if isinstance(msg.payload, bytes) else None
            ),
            "payload_base64_decoded_hex": None,  # Will be filled if Base64 decoding is attempted
            "info_base64_decode": None,  # For info/warnings about base64
            "error_base64_decode": None,  # For errors during base64
            "decoded_protobuf": None,  # For the top-level decoded object (HeaderMessage or Header)
            "decoded_headers": [],  # For detailed processing of each inner Header
            "error": [],  # General processing errors
        }

        if not isinstance(msg.payload, bytes):
            self.logger.warning(
                "  Payload is not bytes, attempting to encode to UTF-8 for further processing."
            )
            try:
                payload_bytes = str(msg.payload).encode("utf-8")
            except Exception as e_enc:
                self.logger.error(f"  Failed to encode payload to bytes: {e_enc}")
                output_data["error"].append("Payload not bytes and failed to encode.")
                if self.output_file_path:
                    self._write_output_to_file(output_data)
                return
        else:
            payload_bytes = msg.payload

        device_prop_topic = self.config.get("device_property_topic")
        get_reply_topic = self.config.get("get_reply_topic")

        if device_prop_topic and msg.topic == device_prop_topic:
            self._process_device_property_message(msg.topic, payload_bytes, output_data)
        elif get_reply_topic and msg.topic == get_reply_topic:
            self._process_get_reply_message(msg.topic, payload_bytes, output_data)
        else:
            self.logger.info(f"  Unhandled topic: {msg.topic}")
            output_data["info"] = f"Unhandled topic: {msg.topic}"

        if self.output_file_path:
            self._write_output_to_file(output_data)

    def _write_output_to_file(self, data: dict[str, Any]) -> None:
        if not self.output_file_path:
            return
        try:
            with open(self.output_file_path, "a", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except Exception as e_write:
            self.logger.error(
                f"Error writing JSON to file {self.output_file_path}: {e_write}"
            )
