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
    OutMilliVoltSensorEntity,
    OutVoltDcSensorEntity,
    OutWattsDcSensorEntity,
    OutWattsSensorEntity,
    QuotaStatusSensorEntity,
    RemainSensorEntity,
    TempSensorEntity,
    WattsSensorEntity,
)
from custom_components.ecoflow_cloud.switch import BeeperEntity, EnabledEntity


class DeltaPro3(BaseDevice):
    def sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
        return [
            # Main Battery System - using actual protobuf field names
            LevelSensorEntity(client, self, "bms_batt_soc", const.MAIN_BATTERY_LEVEL)
            .attr("bms_design_cap", const.ATTR_DESIGN_CAPACITY, 0)
            .attr("bms_full_cap_mah", const.ATTR_FULL_CAPACITY, 0)
            .attr("bms_remain_cap_mah", const.ATTR_REMAIN_CAPACITY, 0),
            CapacitySensorEntity(
                client, self, "bms_design_cap", const.MAIN_DESIGN_CAPACITY, False
            ),
            CapacitySensorEntity(
                client, self, "bms_full_cap_mah", const.MAIN_FULL_CAPACITY, False
            ),
            CapacitySensorEntity(
                client, self, "bms_remain_cap_mah", const.MAIN_REMAIN_CAPACITY, False
            ),
            LevelSensorEntity(client, self, "bms_batt_soh", const.SOH),
            CyclesSensorEntity(client, self, "bms_cycles", const.CYCLES),
            # Battery Voltage and Current
            MilliVoltSensorEntity(
                client, self, "bms_batt_vol", const.BATTERY_VOLT, False
            )
            .attr("bms_min_cell_vol", const.ATTR_MIN_CELL_VOLT, 0)
            .attr("bms_max_cell_vol", const.ATTR_MAX_CELL_VOLT, 0),
            MilliVoltSensorEntity(
                client, self, "bms_min_cell_vol", const.MIN_CELL_VOLT, False
            ),
            MilliVoltSensorEntity(
                client, self, "bms_max_cell_vol", const.MAX_CELL_VOLT, False
            ),
            AmpSensorEntity(
                client, self, "bms_batt_amp", const.MAIN_BATTERY_CURRENT, False
            ),
            # Battery Temperature
            TempSensorEntity(
                client, self, "bms_max_cell_temp", const.MAX_CELL_TEMP, False
            ),
            TempSensorEntity(
                client, self, "bms_min_cell_temp", const.MIN_CELL_TEMP, False
            ),
            TempSensorEntity(client, self, "bms_max_mos_temp", const.BATTERY_TEMP)
            .attr("bms_min_cell_temp", const.ATTR_MIN_CELL_TEMP, 0)
            .attr("bms_max_cell_temp", const.ATTR_MAX_CELL_TEMP, 0),
            # Charge/Discharge Times
            RemainSensorEntity(
                client, self, "bms_chg_rem_time", const.CHARGE_REMAINING_TIME
            ),
            RemainSensorEntity(
                client, self, "bms_dsg_rem_time", const.DISCHARGE_REMAINING_TIME
            ),
            # Combined System Status
            LevelSensorEntity(
                client, self, "cms_batt_soc", const.COMBINED_BATTERY_LEVEL
            ),
            # Power Input/Output - using correct protobuf field names
            OutWattsSensorEntity(client, self, "pow_out_sum_w", const.TOTAL_OUT_POWER),
            InWattsSensorEntity(client, self, "pow_in_sum_w", const.TOTAL_IN_POWER),
            # AC Power System
            InWattsSensorEntity(client, self, "pow_get_ac_in", const.AC_IN_POWER),
            OutWattsSensorEntity(client, self, "pow_get_ac", const.AC_OUT_POWER),
            OutWattsSensorEntity(
                client, self, "pow_get_ac_hv_out", "AC HV Output Power"
            ),
            OutWattsSensorEntity(
                client, self, "pow_get_ac_lv_out", "AC LV Output Power"
            ),
            # AC Input Voltage/Current
            InMilliVoltSensorEntity(
                client, self, "plug_in_info_ac_in_vol", const.AC_IN_VOLT
            ),
            InAmpSolarSensorEntity(
                client, self, "plug_in_info_ac_in_amp", "AC Input Current"
            ),
            # DC Power System
            OutWattsDcSensorEntity(client, self, "pow_get_12v", "12V DC Output Power"),
            OutWattsDcSensorEntity(client, self, "pow_get_24v", "24V DC Output Power"),
            OutVoltDcSensorEntity(
                client, self, "pow_get_12v_vol", "12V DC Output Voltage"
            ),
            OutVoltDcSensorEntity(
                client, self, "pow_get_24v_vol", "24V DC Output Voltage"
            ),
            # Solar Input
            InWattsSolarSensorEntity(
                client, self, "pow_get_pv_h", "Solar High Voltage Input Power"
            ),
            InWattsSolarSensorEntity(
                client, self, "pow_get_pv_l", "Solar Low Voltage Input Power"
            ),
            InVoltSolarSensorEntity(
                client, self, "pow_get_pv_h_vol", "Solar HV Input Voltage"
            ),
            InVoltSolarSensorEntity(
                client, self, "pow_get_pv_l_vol", "Solar LV Input Voltage"
            ),
            InAmpSolarSensorEntity(
                client, self, "pow_get_pv_h_amp", "Solar HV Input Current"
            ),
            InAmpSolarSensorEntity(
                client, self, "pow_get_pv_l_amp", "Solar LV Input Current"
            ),
            # USB Ports
            OutWattsSensorEntity(
                client, self, "pow_get_qcusb1", const.USB_QC_1_OUT_POWER
            ),
            OutWattsSensorEntity(
                client, self, "pow_get_qcusb2", const.USB_QC_2_OUT_POWER
            ),
            OutWattsSensorEntity(
                client, self, "pow_get_typec1", const.TYPEC_1_OUT_POWER
            ),
            OutWattsSensorEntity(
                client, self, "pow_get_typec2", const.TYPEC_2_OUT_POWER
            ),
            # Power I/O and Extra Battery Ports
            OutWattsDcSensorEntity(
                client, self, "pow_get_5p8", "5P8 Power I/O Port Power"
            ),
            OutWattsDcSensorEntity(
                client, self, "pow_get_4p8_1", "4P8 Extra Battery Port 1 Power"
            ),
            OutWattsDcSensorEntity(
                client, self, "pow_get_4p8_2", "4P8 Extra Battery Port 2 Power"
            ),
            # System Frequencies
            OutWattsSensorEntity(client, self, "ac_out_freq", "AC Output Frequency"),
            # Power Management Status
            LevelSensorEntity(
                client, self, "cms_max_chg_soc", "Max Charge SOC Setting"
            ),
            LevelSensorEntity(
                client, self, "cms_min_dsg_soc", "Min Discharge SOC Setting"
            ),
            # Energy Counters
            InEnergySensorEntity(
                client, self, "pow_in_sum_energy", "Total Input Energy"
            ),
            OutEnergySensorEntity(
                client, self, "pow_out_sum_energy", "Total Output Energy"
            ),
            InEnergySensorEntity(
                client, self, "ac_in_energy_total", const.CHARGE_AC_ENERGY
            ),
            OutEnergySensorEntity(
                client, self, "ac_out_energy_total", const.DISCHARGE_AC_ENERGY
            ),
            InEnergySensorEntity(
                client, self, "pv_in_energy_total", const.SOLAR_IN_ENERGY
            ),
            OutEnergySensorEntity(
                client, self, "dc_out_energy_total", const.DISCHARGE_DC_ENERGY
            ),
            QuotaStatusSensorEntity(client, self),
        ]

    def numbers(self, client: EcoflowApiClient) -> list[BaseNumberEntity]:
        return [
            # Battery Management
            MaxBatteryLevelEntity(
                client,
                self,
                "cms_max_chg_soc",
                const.MAX_CHARGE_LEVEL,
                50,
                100,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 49, "cmsMaxChgSoc": value},
                },
            ),
            MinBatteryLevelEntity(
                client,
                self,
                "cms_min_dsg_soc",
                const.MIN_DISCHARGE_LEVEL,
                0,
                30,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 51, "cmsMinDsgSoc": value},
                },
            ),
            # AC Charging Power
            ChargingPowerEntity(
                client,
                self,
                "plug_in_info_ac_in_chg_pow_max",
                const.AC_CHARGING_POWER,
                200,
                3000,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 69, "plugInInfoAcInChgPowMax": value},
                },
            ),
        ]

    def switches(self, client: EcoflowApiClient) -> list[BaseSwitchEntity]:
        return [
            # Audio Control
            BeeperEntity(
                client,
                self,
                "en_beep",
                const.BEEPER,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 38, "enBeep": value},
                },
            ),
            # AC Output Control
            EnabledEntity(
                client,
                self,
                "cfg_hv_ac_out_open",
                "AC HV Output Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 66, "cfgHvAcOutOpen": value},
                },
            ),
            EnabledEntity(
                client,
                self,
                "cfg_lv_ac_out_open",
                "AC LV Output Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 66, "cfgLvAcOutOpen": value},
                },
            ),
            # DC Output Control
            EnabledEntity(
                client,
                self,
                "cfg_dc_12v_out_open",
                "12V DC Output Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 81, "cfgDc12vOutOpen": value},
                },
            ),
            EnabledEntity(
                client,
                self,
                "cfg_dc_24v_out_open",
                "24V DC Output Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 81, "cfgDc24vOutOpen": value},
                },
            ),
            # Xboost Control
            EnabledEntity(
                client,
                self,
                "xboost_en",
                const.XBOOST_ENABLED,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 66, "xboostEn": value},
                },
            ),
            # Energy Saving
            EnabledEntity(
                client,
                self,
                "ac_energy_saving_open",
                "AC Energy Saving Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 95, "acEnergySavingOpen": value},
                },
            ),
            # GFCI Control
            EnabledEntity(
                client,
                self,
                "llc_gfci_flag",
                "GFCI Protection Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 153, "llcGFCIFlag": value},
                },
            ),
        ]

    def selects(self, client: EcoflowApiClient) -> list[BaseSelectEntity]:
        return [
            # Screen Timeout
            TimeoutDictSelectEntity(
                client,
                self,
                "screen_off_time",
                const.SCREEN_TIMEOUT,
                const.SCREEN_TIMEOUT_OPTIONS,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"screenOffTime": value, "id": 39},
                },
            ),
            # AC Standby Timeout
            TimeoutDictSelectEntity(
                client,
                self,
                "ac_standby_time",
                const.AC_TIMEOUT,
                const.AC_TIMEOUT_OPTIONS,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"acStandbyTime": value, "id": 153},
                },
            ),
            # DC Standby Timeout
            TimeoutDictSelectEntity(
                client,
                self,
                "dc_standby_time",
                "DC Timeout",
                const.UNIT_TIMEOUT_OPTIONS_LIMITED,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"dcStandbyTime": value, "id": 33},
                },
            ),
            # AC Output Type
            DictSelectEntity(
                client,
                self,
                "plug_in_info_ac_out_type",
                "AC Output Type",
                {"HV+LV": 0, "HV Only": 1, "LV Only": 2},
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"plugInInfoAcOutType": int(value), "id": 153},
                },
            ),
        ]
