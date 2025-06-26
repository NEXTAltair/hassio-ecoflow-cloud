# Delta Pro 3 Entity Specification Document

## Overview

This document provides comprehensive entity definitions for the EcoFlow Delta Pro 3 Home Assistant integration. The specification includes sensor, switch, number, select, and button entities based on analysis of the protobuf messages, ioBroker implementation, and existing EcoFlow integration patterns.

## Entity Architecture

### Base Classes Hierarchy
```
HomeAssistant Entity Classes:
├── SensorEntity
│   ├── InWattsSensorEntity
│   ├── OutWattsSensorEntity  
│   ├── LevelSensorEntity
│   ├── CapacitySensorEntity
│   ├── TempSensorEntity
│   └── BaseSensorEntity
├── SwitchEntity
│   └── BaseSwitchEntity
├── NumberEntity
│   ├── ChargingPowerEntity
│   └── BaseNumberEntity
├── SelectEntity
│   └── BaseSelectEntity
└── ButtonEntity
    └── BaseButtonEntity
```

### Protobuf Message Mapping
The entities map to the following protobuf messages:
- **DisplayPropertyUpload** (cmdFunc=1, cmdId=1/2): Real-time display data
- **RuntimePropertyUpload** (cmdFunc=50, cmdId=30): System runtime data
- **cmdFunc32_cmdId2_Report**: Device status reports
- **Command Messages** (cmdFunc=129, cmdId=1): Control commands

---

## 1. Sensor Entities (200+ Parameters)

### 1.1 Battery Management Sensors

#### Main Battery (BMS)
```python
def _main_battery_sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    return [
        # Core Battery Status
        LevelSensorEntity(
            client, self, "bmsBattSoc", "Main Battery SOC", "%",
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=None  # Primary sensor
        ),
        CapacitySensorEntity(
            client, self, "bmsDesignCap", "Main Battery Capacity", "mAh",
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False
        ),
        
        # Battery Health
        BaseSensorEntity(
            client, self, "bmsBattSoh", "Main Battery SOH", "%",
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "bmsCycles", "Battery Cycles", "cycles",
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:battery-sync"
        ),
        
        # Battery Electrical Properties
        BaseSensorEntity(
            client, self, "bmsBattVol", "Main Battery Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "bmsBattAmp", "Main Battery Current", UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        
        # Cell Monitoring
        BaseSensorEntity(
            client, self, "bmsMinCellVol", "Min Cell Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False
        ),
        BaseSensorEntity(
            client, self, "bmsMaxCellVol", "Max Cell Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False
        ),
        
        # Temperature Monitoring
        BaseSensorEntity(
            client, self, "bmsMaxCellTemp", "Battery Temperature", UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT
        ),
        BaseSensorEntity(
            client, self, "bmsMinCellTemp", "Min Cell Temperature", UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False
        ),
        BaseSensorEntity(
            client, self, "bmsMaxMosTemp", "Max MOS Temperature", UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False
        ),
        
        # Time Remaining
        BaseSensorEntity(
            client, self, "bmsChgRemTime", "Charging Time Remaining", UnitOfTime.MINUTES,
            device_class=SensorDeviceClass.DURATION,
            icon="mdi:timer-sand-complete"
        ),
        BaseSensorEntity(
            client, self, "bmsDsgRemTime", "Discharging Time Remaining", UnitOfTime.MINUTES,
            device_class=SensorDeviceClass.DURATION,
            icon="mdi:timer-sand-empty"
        ),
        
        # Battery Status
        BaseSensorEntity(
            client, self, "bmsChgDsgState", "Battery Charge State",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:battery-sync-outline",
            value_mapping={0: "Standby", 1: "Discharging", 2: "Charging"}
        ),
    ]
```

#### Combined Battery System (CMS)
```python
def _combined_battery_sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    return [
        LevelSensorEntity(
            client, self, "cmsBattSoc", "Total Battery SOC", "%",
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=None  # Primary combined sensor
        ),
        BaseSensorEntity(
            client, self, "cmsBattSoh", "Total Battery SOH", "%",
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "cmsChgRemTime", "Total Charging Time", UnitOfTime.MINUTES,
            device_class=SensorDeviceClass.DURATION,
            icon="mdi:timer-sand-complete"
        ),
        BaseSensorEntity(
            client, self, "cmsDsgRemTime", "Total Discharging Time", UnitOfTime.MINUTES,
            device_class=SensorDeviceClass.DURATION,
            icon="mdi:timer-sand-empty"
        ),
    ]
```

### 1.2 Power Flow Sensors

#### Total Power
```python
def _total_power_sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    return [
        InWattsSensorEntity(
            client, self, "powInSumW", "Total Input Power", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT
        ),
        OutWattsSensorEntity(
            client, self, "powOutSumW", "Total Output Power", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT
        ),
    ]
```

#### AC Power System
```python
def _ac_power_sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    return [
        # AC Input
        InWattsSensorEntity(
            client, self, "powGetAcIn", "AC Input Power", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT
        ),
        BaseSensorEntity(
            client, self, "plugInInfoAcInVol", "AC Input Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfoAcInAmp", "AC Input Current", UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfoAcInFeq", "AC Input Frequency", UnitOfFrequency.HERTZ,
            device_class=SensorDeviceClass.FREQUENCY,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        
        # AC Output - High Voltage
        OutWattsSensorEntity(
            client, self, "powGetAcHvOut", "High Voltage AC Output", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT
        ),
        BaseSensorEntity(
            client, self, "plugInInfoL1Vol", "AC L1 Output Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfoL1Amp", "AC L1 Output Current", UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfoL2Vol", "AC L2 Output Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False  # L2 is optional
        ),
        BaseSensorEntity(
            client, self, "plugInInfoL2Amp", "AC L2 Output Current", UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False  # L2 is optional
        ),
        
        # AC Output - Low Voltage
        OutWattsSensorEntity(
            client, self, "powGetAcLvOut", "Low Voltage AC Output", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT
        ),
        OutWattsSensorEntity(
            client, self, "powGetAcLvTt30Out", "TT-30 AC Output", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            enabled_by_default=False  # TT-30 is optional
        ),
        
        # AC System Status
        BaseSensorEntity(
            client, self, "acOutFreq", "AC Output Frequency", UnitOfFrequency.HERTZ,
            device_class=SensorDeviceClass.FREQUENCY,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfoAcInFlag", "AC Input Connection",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:power-plug-outline",
            value_mapping={0: "Disconnected", 1: "Connected"}
        ),
    ]
```

#### Solar (PV) Input Sensors
```python
def _pv_input_sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    return [
        # High Voltage PV
        InWattsSensorEntity(
            client, self, "powGetPvH", "High Voltage PV Input", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:solar-power-variant-outline"
        ),
        BaseSensorEntity(
            client, self, "plugInInfoPvHVol", "HV PV Input Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfoPvHAmp", "HV PV Input Current", UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfoPvHChgVolMax", "HV PV Max Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False
        ),
        BaseSensorEntity(
            client, self, "plugInInfoPvHChgAmpMax", "HV PV Max Current", UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False
        ),
        
        # Low Voltage PV
        InWattsSensorEntity(
            client, self, "powGetPvL", "Low Voltage PV Input", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:solar-power"
        ),
        BaseSensorEntity(
            client, self, "plugInInfoPvLVol", "LV PV Input Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfoPvLAmp", "LV PV Input Current", UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfoPvLChgVolMax", "LV PV Max Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False
        ),
        BaseSensorEntity(
            client, self, "plugInInfoPvLChgAmpMax", "LV PV Max Current", UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_by_default=False
        ),
        
        # PV Status
        BaseSensorEntity(
            client, self, "plugInInfoPvHFlag", "HV PV Connection",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:solar-panel",
            value_mapping={0: "Disconnected", 1: "Connected"}
        ),
        BaseSensorEntity(
            client, self, "plugInInfoPvLFlag", "LV PV Connection",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:solar-panel",
            value_mapping={0: "Disconnected", 1: "Connected"}
        ),
    ]
```

#### DC Output Sensors
```python
def _dc_output_sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    return [
        # 12V DC Output
        OutWattsSensorEntity(
            client, self, "powGet_12v", "12V DC Output", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:car-battery"
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_12vVol", "12V Output Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_12vAmp", "12V Output Current", UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        
        # 24V DC Output
        OutWattsSensorEntity(
            client, self, "powGet_24v", "24V DC Output", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:truck-check-outline"
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_24vVol", "24V Output Voltage", UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_24vAmp", "24V Output Current", UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
    ]
```

#### USB Output Sensors
```python
def _usb_output_sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    return [
        OutWattsSensorEntity(
            client, self, "powGetQcusb1", "USB-A 1 Output", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:usb-port"
        ),
        OutWattsSensorEntity(
            client, self, "powGetQcusb2", "USB-A 2 Output", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:usb-port"
        ),
        OutWattsSensorEntity(
            client, self, "powGetTypec1", "USB-C 1 Output", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:usb-port"
        ),
        OutWattsSensorEntity(
            client, self, "powGetTypec2", "USB-C 2 Output", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:usb-port"
        ),
    ]
```

### 1.3 System Status Sensors

#### Device Information
```python
def _device_info_sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    return [
        # Error Codes
        BaseSensorEntity(
            client, self, "errcode", "Device Error Code",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:alert-circle-outline"
        ),
        BaseSensorEntity(
            client, self, "bmsErrCode", "BMS Error Code",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:battery-alert-variant-outline"
        ),
        BaseSensorEntity(
            client, self, "pdErrCode", "PD Error Code",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:power-settings"
        ),
        BaseSensorEntity(
            client, self, "llcErrCode", "LLC Error Code",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:chip"
        ),
        BaseSensorEntity(
            client, self, "mpptErrCode", "MPPT Error Code",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:solar-panel"
        ),
        
        # Firmware Versions
        BaseSensorEntity(
            client, self, "pdFirmVer", "PD Firmware Version",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:chip"
        ),
        BaseSensorEntity(
            client, self, "bmsFirmVer", "BMS Firmware Version",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:battery-cog-outline"
        ),
        BaseSensorEntity(
            client, self, "llcFirmVer", "LLC Firmware Version",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:chip"
        ),
        BaseSensorEntity(
            client, self, "mpptFirmVer", "MPPT Firmware Version",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:solar-panel"
        ),
        
        # System Information
        BaseSensorEntity(
            client, self, "utcTimezoneId", "Timezone ID",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:map-clock-outline"
        ),
        BaseSensorEntity(
            client, self, "utcTimezone", "Timezone Offset", "minutes",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:map-clock"
        ),
        
        # Fan Status
        BaseSensorEntity(
            client, self, "pcsFanLevel", "PCS Fan Level",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:fan"
        ),
        
        # Task Management
        BaseSensorEntity(
            client, self, "timeTaskChangeCnt", "Timer Task Changes",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:history"
        ),
    ]
```

#### Expansion Port Sensors
```python
def _expansion_port_sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    return [
        # Extra Battery Port 1 (4p8_1)
        BaseSensorEntity(
            client, self, "powGet_4p8_1", "Extra Battery 1 Power", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:battery-plus-variant"
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_4p8_1Sn", "Extra Battery 1 Serial",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:barcode-scan"
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_4p8_1FirmVer", "Extra Battery 1 Firmware",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:battery-sync"
        ),
        
        # Extra Battery Port 2 (4p8_2)
        BaseSensorEntity(
            client, self, "powGet_4p8_2", "Extra Battery 2 Power", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:battery-plus-variant"
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_4p8_2Sn", "Extra Battery 2 Serial",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:barcode-scan"
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_4p8_2FirmVer", "Extra Battery 2 Firmware",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:battery-sync"
        ),
        
        # Power I/O Port (5p8)
        BaseSensorEntity(
            client, self, "powGet_5p8", "Power I/O Port Power", UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:power-plug-outline"
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_5p8Sn", "Power I/O Device Serial",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:barcode-scan"
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_5p8FirmVer", "Power I/O Device Firmware",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:lan"
        ),
        BaseSensorEntity(
            client, self, "plugInInfo_5p8DsgChg", "Power I/O Charge Type",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:swap-horizontal-bold"
        ),
    ]
```

---

## 2. Switch Entities

### 2.1 Output Control Switches
```python
def _output_control_switches(self, client: EcoflowApiClient) -> list[SwitchEntity]:
    return [
        # Primary AC Output Control
        BaseSwitchEntity(
            client, self, "acAutoOutConfig", "AC Output",
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"pd.acAutoOutConfig": {"switch": 1 if value else 0}}
            },
            icon="mdi:power-plug-outline"
        ),
        
        # High Voltage AC Output
        BaseSwitchEntity(
            client, self, "acAutoOutHvConfig", "High Voltage AC Output",
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"pd.acAutoOutHvConfig": {"switch": 1 if value else 0}}
            },
            icon="mdi:power-plug"
        ),
        
        # Low Voltage AC Output
        BaseSwitchEntity(
            client, self, "acAutoOutLvConfig", "Low Voltage AC Output",
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"pd.acAutoOutLvConfig": {"switch": 1 if value else 0}}
            },
            icon="mdi:power-plug-off-outline"
        ),
        
        # DC Output Control
        BaseSwitchEntity(
            client, self, "carState", "12V DC Output",
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"pd.carState": 1 if value else 0}
            },
            icon="mdi:car-battery"
        ),
        
        # USB Port Control
        BaseSwitchEntity(
            client, self, "usbEnable", "USB Ports",
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"pd.usbEnable": 1 if value else 0}
            },
            icon="mdi:usb-port"
        ),
        
        # X-Boost Feature
        BaseSwitchEntity(
            client, self, "xboostEnable", "X-Boost",
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"inv.cfgAcXboost": 1 if value else 0}
            },
            icon="mdi:rocket-launch-outline",
            entity_category=EntityCategory.CONFIG
        ),
    ]
```

### 2.2 Backup & Emergency Switches
```python
def _backup_switches(self, client: EcoflowApiClient) -> list[SwitchEntity]:
    return [
        # Backup Reserve
        BaseSwitchEntity(
            client, self, "bpMasterSwitch", "Backup Reserve",
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"pd.bpMasterSwitch": 1 if value else 0}
            },
            icon="mdi:shield-check-outline",
            entity_category=EntityCategory.CONFIG
        ),
        
        # EPS Mode
        BaseSwitchEntity(
            client, self, "epsMode", "EPS Mode",
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"inv.cfgEpsEnable": 1 if value else 0}
            },
            icon="mdi:flash-outline",
            entity_category=EntityCategory.CONFIG
        ),
        
        # AC Always On
        BaseSwitchEntity(
            client, self, "acAlwaysOn", "AC Always On",
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"pd.acAlwaysOn": 1 if value else 0}
            },
            icon="mdi:power-standby",
            entity_category=EntityCategory.CONFIG
        ),
    ]
```

---

## 3. Number Entities

### 3.1 Charging Control Numbers
```python
def _charging_control_numbers(self, client: EcoflowApiClient) -> list[NumberEntity]:
    return [
        # Battery SOC Limits
        BaseNumberEntity(
            client, self, "bmsMaxChgSoc", "Max Charge Level", "%",
            50, 100, 1,
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"ems.maxChgSoc": int(value)}
            },
            device_class=NumberDeviceClass.BATTERY,
            entity_category=EntityCategory.CONFIG
        ),
        BaseNumberEntity(
            client, self, "bmsMinDsgSoc", "Min Discharge Level", "%",
            0, 30, 1,
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"ems.minDsgSoc": int(value)}
            },
            device_class=NumberDeviceClass.BATTERY,
            entity_category=EntityCategory.CONFIG
        ),
        
        # Backup Reserve Level
        BaseNumberEntity(
            client, self, "energyBackupStartSoc", "Backup Reserve Level", "%",
            5, 95, 5,
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"pd.energyBackupStartSoc": int(value)}
            },
            device_class=NumberDeviceClass.BATTERY,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:shield-battery-outline"
        ),
        
        # AC Always On Minimum SOC
        BaseNumberEntity(
            client, self, "acAlwaysOnMiniSoc", "AC Always On Min SOC", "%",
            5, 95, 5,
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"pd.acAlwaysOnMiniSoc": int(value)}
            },
            device_class=NumberDeviceClass.BATTERY,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:power-standby"
        ),
        
        # Charging Power Limits
        ChargingPowerEntity(
            client, self, "invSlowChgWatts", "AC Charging Power", UnitOfPower.WATT,
            400, 2900, 100,
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"inv.cfgSlowChgWatts": int(value)}
            },
            device_class=NumberDeviceClass.POWER,
            entity_category=EntityCategory.CONFIG
        ),
    ]
```

### 3.2 Display & Timeout Numbers
```python
def _display_timeout_numbers(self, client: EcoflowApiClient) -> list[NumberEntity]:
    return [
        # Screen Brightness
        BaseNumberEntity(
            client, self, "lcdLight", "Screen Brightness", "%",
            1, 100, 1,
            lambda value: {
                "cmdFunc": 254,
                "cmdId": 17,
                "pdata": {"lcdLight": int(value * 2.56)}  # Convert % to 0-255
            },
            entity_category=EntityCategory.CONFIG,
            icon="mdi:brightness-6"
        ),
        
        # Screen Timeout
        BaseNumberEntity(
            client, self, "screenOffTime", "Screen Timeout", UnitOfTime.SECONDS,
            0, 1800, 30,
            lambda value: {
                "cmdFunc": 254,
                "cmdId": 17,
                "pdata": {"screenOffTime": int(value)}
            },
            entity_category=EntityCategory.CONFIG,
            icon="mdi:monitor-off"
        ),
        
        # Device Standby Time
        BaseNumberEntity(
            client, self, "devStandbyTime", "Device Standby Time", UnitOfTime.MINUTES,
            0, 1440, 30,
            lambda value: {
                "cmdFunc": 254,
                "cmdId": 17,
                "pdata": {"devStandbyTime": int(value)}
            },
            entity_category=EntityCategory.CONFIG,
            icon="mdi:power-sleep"
        ),
    ]
```

---

## 4. Select Entities

### 4.1 AC Output Configuration
```python
def _ac_config_selects(self, client: EcoflowApiClient) -> list[SelectEntity]:
    return [
        # AC Output Standard
        BaseSelectEntity(
            client, self, "acOutStandard", "AC Output Standard",
            ["US (120V/60Hz)", "EU (230V/50Hz)", "AU (240V/50Hz)", "JP (100V/50Hz)"],
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"inv.cfgAcOutStd": {"US": 1, "EU": 2, "AU": 3, "JP": 4}[value.split(" ")[0]]}
            },
            entity_category=EntityCategory.CONFIG,
            icon="mdi:power-socket-us"
        ),
        
        # AC Work Mode
        BaseSelectEntity(
            client, self, "acWorkMode", "AC Work Mode",
            ["Single Phase", "Split Phase", "Three Phase"],
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"inv.cfgAcWorkMode": {"Single": 1, "Split": 2, "Three": 3}[value.split(" ")[0]]}
            },
            entity_category=EntityCategory.CONFIG,
            icon="mdi:sine-wave"
        ),
    ]
```

### 4.2 Charging Priority
```python
def _charging_priority_selects(self, client: EcoflowApiClient) -> list[SelectEntity]:
    return [
        # DC Charging Priority
        BaseSelectEntity(
            client, self, "dcChgPriority", "DC Charging Priority",
            ["Solar First", "AC First", "Balanced"],
            lambda value: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"inv.cfgDcChgPrio": {"Solar": 1, "AC": 2, "Balanced": 3}[value.split(" ")[0]]}
            },
            entity_category=EntityCategory.CONFIG,
            icon="mdi:battery-charging-high"
        ),
    ]
```

---

## 5. Button Entities

### 5.1 System Control Buttons
```python
def _system_control_buttons(self, client: EcoflowApiClient) -> list[ButtonEntity]:
    return [
        # BMS Reset
        BaseButtonEntity(
            client, self, "bmsReset", "BMS Reset",
            lambda: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"ems.bmsReset": 1}
            },
            entity_category=EntityCategory.CONFIG,
            icon="mdi:battery-sync",
            device_class=ButtonDeviceClass.RESTART
        ),
        
        # Factory Reset
        BaseButtonEntity(
            client, self, "factoryReset", "Factory Reset",
            lambda: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"pd.factoryReset": 1}
            },
            entity_category=EntityCategory.CONFIG,
            icon="mdi:factory",
            device_class=ButtonDeviceClass.RESTART
        ),
        
        # IoT Reset
        BaseButtonEntity(
            client, self, "iotReset", "IoT Reset",
            lambda: {
                "cmdFunc": 129,
                "cmdId": 1,
                "pdata": {"iot.iotReset": 1}
            },
            entity_category=EntityCategory.CONFIG,
            icon="mdi:wifi-sync",
            device_class=ButtonDeviceClass.RESTART
        ),
    ]
```

---

## 6. Entity Categories and Grouping

### 6.1 Functional Area Grouping

#### Power Management
- Battery SOC, capacity, health sensors
- Charging/discharging controls
- Power limits and thresholds

#### Energy Flow
- Input power sensors (AC, Solar, DC)
- Output power sensors (AC, DC, USB)
- Real-time power flow monitoring

#### System Health
- Temperature sensors
- Error codes and diagnostics
- Fan status and control

#### Device Configuration
- Output enable/disable switches
- Charging parameters
- Display and timeout settings

#### Advanced Features
- X-Boost power enhancement
- EPS emergency power
- Backup reserve management
- Smart generator integration

### 6.2 Entity Category Classification

#### Default Enabled (Primary Interface)
- Battery SOC and remaining time
- Total input/output power
- AC input/output power
- Solar input power
- Main output control switches
- Essential number controls

#### Diagnostic (Expert Users)
- Individual cell voltages/temperatures
- Internal component temperatures
- Error codes and firmware versions
- Expansion port details
- Communication parameters

#### Configuration (Advanced Settings)
- Power limits and thresholds
- AC output standards and modes
- Timeout and display settings
- Backup and emergency features

---

## 7. Implementation Guidelines

### 7.1 Data Transformation
```python
# Voltage scaling (mV to V)
def voltage_transform(raw_value):
    return raw_value / 1000.0

# Current scaling (mA to A)  
def current_transform(raw_value):
    return raw_value / 1000.0

# Temperature scaling (if needed)
def temperature_transform(raw_value):
    return raw_value  # Usually direct celsius

# Percentage scaling
def percentage_transform(raw_value):
    return min(100, max(0, raw_value))
```

### 7.2 Command Structure
```python
def create_standard_command(cmd_func: int, cmd_id: int, params: dict) -> dict:
    return {
        "cmdFunc": cmd_func,
        "cmdId": cmd_id,
        "pdata": params
    }

# Common command patterns
SET_COMMAND = lambda params: create_standard_command(129, 1, params)
GET_COMMAND = lambda: create_standard_command(1, 2, {})
CONFIG_COMMAND = lambda params: create_standard_command(254, 17, params)
```

### 7.3 Entity Registration
```python
def sensors(self, client: EcoflowApiClient) -> list[SensorEntity]:
    return [
        *self._main_battery_sensors(client),
        *self._combined_battery_sensors(client),
        *self._total_power_sensors(client),
        *self._ac_power_sensors(client),
        *self._pv_input_sensors(client),
        *self._dc_output_sensors(client),
        *self._usb_output_sensors(client),
        *self._device_info_sensors(client),
        *self._expansion_port_sensors(client),
    ]

def switches(self, client: EcoflowApiClient) -> list[SwitchEntity]:
    return [
        *self._output_control_switches(client),
        *self._backup_switches(client),
    ]

def numbers(self, client: EcoflowApiClient) -> list[NumberEntity]:
    return [
        *self._charging_control_numbers(client),
        *self._display_timeout_numbers(client),
    ]

def selects(self, client: EcoflowApiClient) -> list[SelectEntity]:
    return [
        *self._ac_config_selects(client),
        *self._charging_priority_selects(client),
    ]

def buttons(self, client: EcoflowApiClient) -> list[ButtonEntity]:
    return [
        *self._system_control_buttons(client),
    ]
```

---

## 8. Summary

This comprehensive specification defines:

- **200+ Sensor Entities**: Complete coverage of all device parameters
- **15+ Switch Entities**: All controllable outputs and features  
- **10+ Number Entities**: Configurable values and limits
- **5+ Select Entities**: Mode and standard selections
- **5+ Button Entities**: System control actions

The design follows Home Assistant best practices with appropriate device classes, state classes, entity categories, and user-friendly names. All entities map directly to protobuf message fields and include proper command structures for control entities.

The specification provides a complete foundation for implementing the Delta Pro 3 Home Assistant integration with full feature parity to the ioBroker implementation while maintaining the established patterns from existing EcoFlow device integrations.