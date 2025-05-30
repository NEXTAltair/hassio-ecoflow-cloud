# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom component for EcoFlow power stations (DELTA, RIVER, PowerStream, Glacier, Wave series). The integration provides real-time monitoring and control via EcoFlow's cloud MQTT broker, supporting 15+ device types with 400+ entities.

## Development Commands

### Environment Setup
```bash
# Install dependencies with UV package manager
uv sync

# Reset Home Assistant environment (via VS Code Tasks)
Tasks: Run Task → Reset homeassistant

# Run development scripts
uv run python main.py
```

### Debugging and Testing
- Use "Home Assistant" or "Home Assistant (skip pip)" debugger in VS Code
- Access HA instance at `http://127.0.0.1:8123/`
- Development uses Home Assistant core as git submodule in `core/`

### Documentation Generation
```bash
# Generate device documentation
python docs/gen.py

# Update documentation (via VS Code Tasks)
Tasks: Run Task → Generate Docs
```

### Protocol Buffer Compilation
```bash
# Compile .proto files (when adding new device protocols)
protoc --python_out=. *.proto
```

## Architecture

### Core Structure
```
custom_components/ecoflow_cloud/
├── api/                   # MQTT client & API communication layer
├── devices/               # Device management & protocol handling
│   ├── internal/         # Private MQTT API devices (delta*.py, river*.py)
│   ├── public/           # Public REST API devices
│   └── proto/            # Protocol Buffer definitions
├── entities/             # Common entity base classes
├── {sensor,switch,etc}.py # Home Assistant entity implementations
```

### Communication Architecture
- **MQTT Layer**: Real-time bidirectional communication with `mqtt.ecoflow.com`
- **Dual API Support**: Internal MQTT + Public REST APIs
- **Protocol Buffers**: Binary serialization for internal device communication
- **Data Holder Pattern**: Centralized state management per device

### Key Design Patterns
1. **Config Entry Pattern**: Modern HA configuration with migration support (v5→v9)
2. **Entity Platform Pattern**: Separate files per entity type (sensor.py, switch.py, etc.)
3. **Device Registry Pattern**: Dynamic device discovery in `devices/registry.py`
4. **Coordinator Pattern**: Centralized updates via `data_holder.py`

## Development Guidelines

### Code Standards (from .cursor/rules/)
- **Strict Encapsulation**: Never access private variables directly (`_` prefixed)
- **Modern Python Syntax**: Use `list|dict` over `typing.List|Dict`, `str|None` over `Optional[str]`
- **Type Hints**: All functions/methods must have comprehensive type annotations
- **Error Handling**: Use specific exceptions, avoid broad `except Exception`
- **YAGNI Principle**: Implement only current requirements, complete one feature before starting another

### Architecture Constraints
- **Tell, Don't Ask**: Objects expose behavior, not internal state
- **Single Responsibility**: Each class/function has one clear purpose
- **Async/Await**: All I/O operations must be asynchronous
- **Dependency Injection**: Avoid tight coupling between components

### Device Implementation
- New devices go in `devices/internal/` (MQTT) or `devices/public/` (REST API)
- Device registration happens in `devices/registry.py`
- Entity definitions use factory pattern for dynamic creation
- Support for slave devices (multi-battery configurations)

## Special Considerations

### MQTT Protocol
- **Encrypted Payloads**: AES-128-ECB decryption for secure communication
- **Dynamic Protobuf Decoding**: Runtime message type resolution
- **Connection Resilience**: Automatic reconnection with exponential backoff

### Multi-Device Support
- 15+ device types with device-specific implementations
- Each device type has its own module in `devices/internal/` or `devices/public/`
- Comprehensive entity coverage (sensors, switches, selects, numbers, buttons)

### Testing and Diagnostics
- Sample diagnostic data in `diag/` directory for each device type
- MQTT capture tools in `scripts/ecoflow_mqtt_parser/`
- Diagnostics integration for troubleshooting (`diagnostics.py`)

## Common Tasks

### Adding New Device Support
1. Create device module in `devices/internal/` or `devices/public/`
2. Define entities and capabilities
3. Register device in `devices/registry.py`
4. Add diagnostic sample to `diag/`
5. Update device documentation in `docs/devices/`

### Protocol Buffer Updates
1. Update .proto files in `devices/internal/proto/`
2. Recompile with `protoc --python_out=. *.proto`
3. Update device handlers to use new message types

### Entity Implementation
- Inherit from appropriate base classes in `entities/`
- Follow Home Assistant entity patterns
- Implement proper state management through data holder
- Add appropriate device class and entity categories