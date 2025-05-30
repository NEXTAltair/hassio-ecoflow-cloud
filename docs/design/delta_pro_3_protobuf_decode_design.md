# Delta Pro 3 Protobuf Decode Processing Design

## Overview

This document outlines the comprehensive design for protobuf decode processing for the EcoFlow Delta Pro 3 integration in Home Assistant. The design includes message identification, decode logic, entity integration, and error handling.

## 1. Current Infrastructure Analysis

### 1.1 Existing Protobuf Infrastructure

**Current .proto file (`scripts/ef_dp3_iobroker.proto`)**:
- Contains comprehensive message definitions for Delta Pro 3
- Main message types:
  - `RuntimePropertyUpload` - Real-time telemetry data
  - `DisplayPropertyUpload` - Display and configuration data
  - `cmdFunc50_cmdId30_Report` - Battery management system data
  - `cmdFunc32_cmdId2_Report` - Energy management system data
  - `set_dp3` / `setReply_dp3` - Configuration commands and responses

**Current mapping (`scripts/ecoflow_mqtt_parser/protobuf_mapping.py`)**:
- Basic cmdId/cmdFunc to message type mapping
- Limited to key message types
- Needs expansion for comprehensive Delta Pro 3 support

**Current device implementation (`custom_components/ecoflow_cloud/devices/public/delta_pro_3.py`)**:
- Basic protobuf decode logic in `_prepare_data()`
- Simple cmdFunc/cmdId routing
- Limited error handling and fallback mechanisms

## 2. Message Identification and Routing Design

### 2.1 Enhanced cmdFunc/cmdId Mapping

```python
# Enhanced message decoder mapping for Delta Pro 3
DELTA_PRO_3_MESSAGE_DECODERS: dict[tuple[int, int], type] = {
    # Core telemetry messages
    (1, 1): DisplayPropertyUpload,      # Display properties and status
    (1, 2): DisplayPropertyUpload,      # Display properties reply
    (20, 1): RuntimePropertyUpload,     # Runtime telemetry
    (20, 2): RuntimePropertyUpload,     # Runtime telemetry reply
    
    # Battery management system
    (50, 30): cmdFunc50_cmdId30_Report,  # BMS detailed report
    
    # Energy management system
    (32, 2): cmdFunc32_cmdId2_Report,    # EMS status report
    
    # Configuration and commands
    (254, 17): set_dp3,                  # Configuration set command
    (254, 18): setReply_dp3,             # Configuration set reply
    (254, 23): cmdFunc254_cmdId23_Report, # Special status report
    
    # Fallback patterns for unknown messages
    (129, 1): Send_Header_Msg,           # Generic header message
    (131, 1): Send_Header_Msg,           # Alternative header format
}

# Message priority for overlapping cmdFunc/cmdId combinations
MESSAGE_PRIORITY = {
    DisplayPropertyUpload: 1,
    RuntimePropertyUpload: 2,
    cmdFunc50_cmdId30_Report: 3,
    cmdFunc32_cmdId2_Report: 4,
    setReply_dp3: 5,
    Send_Header_Msg: 10,  # Lowest priority (fallback)
}
```

### 2.2 Message Identification Logic

```python
def identify_message_type(cmd_func: int, cmd_id: int, pdata_length: int) -> Type[Message] | None:
    """
    Identify the appropriate protobuf message type based on cmd_func, cmd_id, and context.
    
    Args:
        cmd_func: Command function ID from MQTT header
        cmd_id: Command ID from MQTT header  
        pdata_length: Length of payload data for context
        
    Returns:
        Protobuf message class or None if no match found
    """
    # Primary lookup by exact (cmd_func, cmd_id) tuple
    exact_match = DELTA_PRO_3_MESSAGE_DECODERS.get((cmd_func, cmd_id))
    if exact_match:
        return exact_match
    
    # Secondary lookup by cmd_func only (for flexible matching)
    func_matches = [
        msg_type for (f, _), msg_type in DELTA_PRO_3_MESSAGE_DECODERS.items() 
        if f == cmd_func
    ]
    
    if func_matches:
        # Return highest priority match
        return min(func_matches, key=lambda t: MESSAGE_PRIORITY.get(t, 999))
    
    # Context-based fallbacks
    if cmd_id == 2:  # Common reply command
        if pdata_length > 1000:  # Large payload suggests telemetry
            return RuntimePropertyUpload
        else:
            return DisplayPropertyUpload
    
    # Ultimate fallback
    return Send_Header_Msg
```

## 3. Decode Processing Architecture

### 3.1 Enhanced _prepare_data Method

```python
def _prepare_data(self, raw_data: bytes) -> dict[str, typing.Any]:
    """
    Enhanced protobuf decode processing with comprehensive error handling,
    XOR decoding, and intelligent message type detection.
    """
    try:
        # 1. Parse MQTT JSON wrapper
        mqtt_data = self._parse_mqtt_wrapper(raw_data)
        if not mqtt_data:
            return {}
        
        # 2. Extract protobuf payload and metadata
        pdata_hex = mqtt_data.get("pdata")
        cmd_func = int(mqtt_data.get("cmdFunc", 0))
        cmd_id = int(mqtt_data.get("cmdId", 0))
        enc_type = int(mqtt_data.get("encType", 0))
        seq = int(mqtt_data.get("seq", 0))
        src = int(mqtt_data.get("src", 0))
        
        if not pdata_hex:
            _LOGGER.debug(f"[{self.device_info.sn}] Empty pdata for cmd_func={cmd_func}, cmd_id={cmd_id}")
            return {}
        
        # 3. Decode hex payload
        pdata_bytes = bytes.fromhex(pdata_hex)
        
        # 4. Apply XOR decoding if needed
        decoded_pdata = self._apply_xor_decoding(pdata_bytes, enc_type, seq, src)
        
        # 5. Identify and decode protobuf message
        result = self._decode_protobuf_message(decoded_pdata, cmd_func, cmd_id)
        
        # 6. Add metadata for diagnostics
        result.update({
            "_metadata": {
                "cmd_func": cmd_func,
                "cmd_id": cmd_id,
                "enc_type": enc_type,
                "seq": seq,
                "src": src,
                "payload_length": len(pdata_bytes),
                "xor_decoded": enc_type == 1 and src != 32,
            }
        })
        
        return result
        
    except Exception as e:
        _LOGGER.error(f"[{self.device_info.sn}] Critical error in _prepare_data: {e}")
        return {}
```

### 3.2 XOR Decoding Implementation

```python
def _apply_xor_decoding(self, pdata: bytes, enc_type: int, seq: int, src: int) -> bytes:
    """
    Apply XOR decoding to encrypted payload data.
    Based on EcoFlow protocol analysis and ioBroker implementation.
    """
    # XOR decoding conditions based on protocol analysis
    if enc_type != 1 or src == 32:
        return pdata  # No decoding needed
    
    try:
        # XOR key generation based on sequence number
        # This implements the EcoFlow XOR decoding algorithm
        xor_key = self._generate_xor_key(seq)
        
        decoded = bytearray()
        for i, byte in enumerate(pdata):
            decoded.append(byte ^ xor_key[i % len(xor_key)])
        
        _LOGGER.debug(f"[{self.device_info.sn}] XOR decoded {len(pdata)} bytes with seq={seq}")
        return bytes(decoded)
        
    except Exception as e:
        _LOGGER.error(f"[{self.device_info.sn}] XOR decoding failed: {e}")
        return pdata  # Return original data on failure

def _generate_xor_key(self, seq: int) -> bytes:
    """Generate XOR key from sequence number using EcoFlow algorithm."""
    # Implementation based on reverse engineering of EcoFlow protocol
    # This is a simplified version - actual implementation may be more complex
    key_base = seq.to_bytes(4, byteorder='little')
    return key_base * 64  # Repeat to cover typical message sizes
```

### 3.3 Protobuf Message Decoding

```python
def _decode_protobuf_message(self, pdata: bytes, cmd_func: int, cmd_id: int) -> dict[str, Any]:
    """
    Decode protobuf message with comprehensive fallback handling.
    """
    # Identify message type
    message_class = identify_message_type(cmd_func, cmd_id, len(pdata))
    
    decode_attempts = []
    
    if message_class:
        # Try primary message type
        result = self._attempt_decode(pdata, message_class, "primary")
        if result:
            return result
        decode_attempts.append(message_class.__name__)
    
    # Try fallback message types in order of likelihood
    fallback_types = [
        DisplayPropertyUpload,
        RuntimePropertyUpload,
        cmdFunc50_cmdId30_Report,
        Send_Header_Msg,
    ]
    
    for fallback_type in fallback_types:
        if fallback_type == message_class:
            continue  # Already tried
            
        result = self._attempt_decode(pdata, fallback_type, "fallback")
        if result:
            _LOGGER.info(
                f"[{self.device_info.sn}] Fallback decode success: {fallback_type.__name__} "
                f"for cmd_func={cmd_func}, cmd_id={cmd_id}"
            )
            return result
        decode_attempts.append(fallback_type.__name__)
    
    # All decode attempts failed
    _LOGGER.error(
        f"[{self.device_info.sn}] All decode attempts failed for cmd_func={cmd_func}, "
        f"cmd_id={cmd_id}. Tried: {', '.join(decode_attempts)}"
    )
    
    return {
        "_decode_error": {
            "attempted_types": decode_attempts,
            "cmd_func": cmd_func,
            "cmd_id": cmd_id,
            "payload_hex": pdata.hex()[:200] + ("..." if len(pdata) > 100 else ""),
        }
    }

def _attempt_decode(self, pdata: bytes, message_class: Type[Message], attempt_type: str) -> dict[str, Any] | None:
    """Attempt to decode pdata with specific message class."""
    try:
        proto_message = message_class()
        proto_message.ParseFromString(pdata)
        
        # Convert to dictionary with proper field handling
        data_dict = json_format.MessageToDict(
            proto_message,
            always_print_fields_with_no_presence=True,
            preserving_proto_field_name=True,
            use_integers_for_enums=True,
        )
        
        # Add decode metadata
        data_dict["_decode_info"] = {
            "message_type": message_class.__name__,
            "attempt_type": attempt_type,
            "success": True,
        }
        
        _LOGGER.debug(
            f"[{self.device_info.sn}] {attempt_type.title()} decode success: "
            f"{message_class.__name__} ({len(data_dict)} fields)"
        )
        
        return data_dict
        
    except Exception as e:
        _LOGGER.debug(
            f"[{self.device_info.sn}] {attempt_type.title()} decode failed: "
            f"{message_class.__name__} - {e}"
        )
        return None
```

## 4. Entity Integration Design

### 4.1 Enhanced Entity Field Mapping

```python
# Comprehensive field mapping for Delta Pro 3 entities
DP3_ENTITY_MAPPINGS = {
    # Battery sensors from multiple message sources
    "battery_soc": {
        "primary_key": "bms_batt_soc",  # From DisplayPropertyUpload
        "fallback_keys": [
            "bms_batt_soc_percent_float1",  # From cmdFunc50_cmdId30_Report
            "bms_batt_soc_percent_float2",
            "cms_batt_soc_percent",         # From cmdFunc32_cmdId2_Report
        ],
        "unit": "%",
        "device_class": "battery",
    },
    
    "battery_voltage": {
        "primary_key": "bms_batt_vol",
        "fallback_keys": [
            "cms_batt_vol_mv",
        ],
        "unit": "V",
        "device_class": "voltage",
        "value_transform": lambda x: x / 1000 if x > 100 else x,  # Convert mV to V
    },
    
    # Power sensors
    "total_input_power": {
        "primary_key": "pow_in_sum_w",
        "unit": "W",
        "device_class": "power",
    },
    
    "total_output_power": {
        "primary_key": "pow_out_sum_w",
        "unit": "W", 
        "device_class": "power",
    },
    
    "solar_input_power": {
        "primary_key": "pow_get_pv_h",
        "fallback_keys": ["pow_get_pv_l"],
        "unit": "W",
        "device_class": "power",
    },
    
    # Temperature sensors
    "battery_temp_max": {
        "primary_key": "bms_max_cell_temp",
        "fallback_keys": ["max_cell_temp_c"],
        "unit": "°C",
        "device_class": "temperature",
    },
    
    # Configuration entities
    "ac_charge_limit": {
        "primary_key": "plug_in_info_ac_in_chg_pow_max",
        "unit": "W",
        "entity_type": "number",
        "min_value": 0,
        "max_value": 3600,
        "command": {
            "cmd_func": 254,
            "cmd_id": 17,
            "field": "plugInInfoAcInChgPowMax",
        },
    },
}

def create_entity_with_fallback(client: EcoflowApiClient, device: BaseDevice, 
                               entity_config: dict) -> BaseSensorEntity:
    """Create entity with intelligent field fallback support."""
    
    class FallbackSensorEntity(BaseSensorEntity):
        def __init__(self, client, device, config):
            super().__init__(client, device, config["primary_key"], config.get("name", "Unknown"))
            self.fallback_keys = config.get("fallback_keys", [])
            self.value_transform = config.get("value_transform", lambda x: x)
            
        def _update_value(self, val: Any) -> bool:
            # Try primary key first
            if val is not None:
                transformed_val = self.value_transform(val)
                if self._attr_native_value != transformed_val:
                    self._attr_native_value = transformed_val
                    return True
            
            # Try fallback keys
            for fallback_key in self.fallback_keys:
                fallback_val = self._get_nested_value(self.coordinator.data.data_holder.params, fallback_key)
                if fallback_val is not None:
                    transformed_val = self.value_transform(fallback_val)
                    if self._attr_native_value != transformed_val:
                        self._attr_native_value = transformed_val
                        return True
            
            return False
    
    return FallbackSensorEntity(client, device, entity_config)
```

### 4.2 Enhanced Entity Creation

```python
def sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    """Create comprehensive sensor entities for Delta Pro 3."""
    sensors = []
    
    # Create sensors from mapping configuration
    for entity_id, config in DP3_ENTITY_MAPPINGS.items():
        if config.get("entity_type", "sensor") == "sensor":
            entity = create_entity_with_fallback(client, self, config)
            sensors.append(entity)
    
    # Add diagnostic sensors for protobuf debugging
    if self.device_data.options.diagnostic_mode:
        sensors.extend([
            DiagnosticSensorEntity(client, self, "_metadata.cmd_func", "Last Command Function"),
            DiagnosticSensorEntity(client, self, "_metadata.cmd_id", "Last Command ID"),
            DiagnosticSensorEntity(client, self, "_metadata.payload_length", "Payload Length"),
            DiagnosticSensorEntity(client, self, "_decode_info.message_type", "Message Type"),
        ])
    
    return sensors
```

## 5. Command Sending Design

### 5.1 Protobuf Command Construction

```python
def send_protobuf_command(self, client: EcoflowApiClient, command_config: dict, value: Any) -> bool:
    """
    Send protobuf-based command to Delta Pro 3.
    
    Args:
        client: API client for MQTT communication
        command_config: Command configuration from entity mapping
        value: Value to set
        
    Returns:
        True if command sent successfully
    """
    try:
        # Create protobuf command message
        cmd_message = set_dp3()
        
        # Set the specific field
        field_name = command_config["field"]
        if hasattr(cmd_message, field_name):
            setattr(cmd_message, field_name, int(value))
        else:
            _LOGGER.error(f"Unknown field {field_name} in set_dp3 message")
            return False
        
        # Serialize protobuf message
        pdata = cmd_message.SerializeToString()
        
        # Create MQTT command wrapper
        mqtt_command = {
            "cmdFunc": command_config["cmd_func"],
            "cmdId": command_config["cmd_id"],
            "pdata": pdata.hex(),
            "encType": 1,  # Enable encryption
            "seq": int(time.time() * 1000) & 0xFFFFFFFF,
        }
        
        # Send via MQTT client
        client.mqtt_client.send_set_message(
            self.device_info.sn,
            {command_config["field"]: value},  # Target state
            mqtt_command
        )
        
        _LOGGER.debug(
            f"[{self.device_info.sn}] Sent protobuf command: {field_name}={value}"
        )
        return True
        
    except Exception as e:
        _LOGGER.error(f"[{self.device_info.sn}] Failed to send protobuf command: {e}")
        return False
```

## 6. Error Handling and Diagnostics

### 6.1 Comprehensive Error Handling

```python
class ProtobufDecodeError(Exception):
    """Custom exception for protobuf decode errors."""
    pass

def _handle_decode_error(self, error: Exception, context: dict) -> dict[str, Any]:
    """Centralized error handling for decode failures."""
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "timestamp": dt.utcnow().isoformat(),
    }
    
    # Log appropriate level based on error type
    if isinstance(error, (UnicodeDecodeError, json.JSONDecodeError)):
        _LOGGER.warning(f"[{self.device_info.sn}] Data format error: {error}")
    elif isinstance(error, ProtobufDecodeError):
        _LOGGER.error(f"[{self.device_info.sn}] Protobuf decode error: {error}")
    else:
        _LOGGER.error(f"[{self.device_info.sn}] Unexpected error: {error}", exc_info=True)
    
    # Store error for diagnostics
    if self.device_data.options.diagnostic_mode:
        if not hasattr(self, '_recent_errors'):
            self._recent_errors = BoundFifoList(maxlen=10)
        self._recent_errors.append(error_info)
    
    return {"_error": error_info}
```

### 6.2 Performance Optimization

```python
class ProtobufDecodeCache:
    """Cache for decoded protobuf messages to improve performance."""
    
    def __init__(self, max_size: int = 100):
        self.cache: dict[str, tuple[dict, datetime]] = {}
        self.max_size = max_size
        self.cache_ttl = timedelta(seconds=30)
    
    def get(self, key: str) -> dict | None:
        """Get cached decode result if still valid."""
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.utcnow() - timestamp < self.cache_ttl:
                return result
            else:
                del self.cache[key]
        return None
    
    def put(self, key: str, result: dict) -> None:
        """Cache decode result."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (result, datetime.utcnow())

# Usage in _prepare_data
def _prepare_data(self, raw_data: bytes) -> dict[str, typing.Any]:
    # Create cache key from raw data hash
    cache_key = hashlib.md5(raw_data).hexdigest()
    
    # Check cache first
    cached_result = self.decode_cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Perform decode...
    result = self._decode_message(raw_data)
    
    # Cache successful results
    if not result.get("_error"):
        self.decode_cache.put(cache_key, result)
    
    return result
```

## 7. Testing Strategy

### 7.1 Unit Test Framework

```python
class TestDeltaPro3ProtobufDecoding(unittest.TestCase):
    
    def setUp(self):
        self.device = DeltaPro3(mock_device_info, mock_device_data)
        self.test_payloads = self._load_test_payloads()
    
    def test_runtime_property_decode(self):
        """Test decoding of RuntimePropertyUpload messages."""
        test_payload = self.test_payloads["runtime_property_upload"]
        result = self.device._prepare_data(test_payload)
        
        self.assertIn("bms_batt_vol", result)
        self.assertIn("pow_in_sum_w", result)
        self.assertEqual(result["_decode_info"]["message_type"], "RuntimePropertyUpload")
    
    def test_xor_decoding(self):
        """Test XOR decoding functionality."""
        encrypted_payload = self.test_payloads["encrypted_message"]
        result = self.device._prepare_data(encrypted_payload)
        
        self.assertTrue(result["_metadata"]["xor_decoded"])
        self.assertNotIn("_error", result)
    
    def test_fallback_decoding(self):
        """Test fallback message type detection."""
        ambiguous_payload = self.test_payloads["ambiguous_message"]
        result = self.device._prepare_data(ambiguous_payload)
        
        self.assertEqual(result["_decode_info"]["attempt_type"], "fallback")
        self.assertNotIn("_error", result)
    
    def test_command_generation(self):
        """Test protobuf command generation."""
        command_config = DP3_ENTITY_MAPPINGS["ac_charge_limit"]["command"]
        success = self.device.send_protobuf_command(mock_client, command_config, 2000)
        
        self.assertTrue(success)
        # Verify command was sent to MQTT client
        mock_client.mqtt_client.send_set_message.assert_called_once()
```

## 8. Migration and Deployment Plan

### 8.1 Backwards Compatibility

- Maintain existing JSON-based decode as fallback
- Gradual migration to protobuf-first approach
- Feature flags for enabling/disabling protobuf decoding

### 8.2 Validation Against Real Device

- Capture real Delta Pro 3 MQTT messages
- Validate decode accuracy against known device states
- Performance testing with high-frequency message streams

## 9. Future Enhancements

### 9.1 Dynamic Message Discovery

- Runtime analysis of unknown cmdFunc/cmdId combinations
- Automatic protobuf schema inference
- Community-driven message type identification

### 9.2 Enhanced Command Support

- Bidirectional protobuf communication
- Command acknowledgment handling
- Batch command operations

### 9.3 Multi-Device Protocol Support

- Extensible framework for other EcoFlow devices
- Shared protobuf infrastructure
- Protocol version negotiation

## 10. Implementation Checklist

- [ ] Update protobuf_mapping.py with comprehensive message decoders
- [ ] Enhance delta_pro_3.py with new _prepare_data implementation
- [ ] Implement XOR decoding functionality
- [ ] Create fallback entity mapping system
- [ ] Add comprehensive error handling
- [ ] Implement command sending infrastructure
- [ ] Create unit test suite
- [ ] Add diagnostic mode enhancements
- [ ] Performance optimization with caching
- [ ] Documentation and examples

This design provides a robust, extensible foundation for Delta Pro 3 protobuf integration while maintaining backwards compatibility and providing comprehensive error handling and diagnostic capabilities.