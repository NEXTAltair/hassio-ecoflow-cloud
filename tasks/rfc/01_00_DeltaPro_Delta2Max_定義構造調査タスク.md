# 既存Delta Pro/Delta 2 Max 定義・構造調査タスク

## 1. デバイス定義ファイルの全体構造把握(クラス・メソッド構成の俯瞰)

### delta_pro.py
- 定義クラス: `DeltaPro(BaseDevice)`
- 主なメソッド:
    - `sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]`
        - バッテリー残量、設計容量、SOH、合計入出力W、AC/DC/USB/TypeC/ソーラー/スレーブバッテリー等、多数のセンサーエンティティを生成
    - `numbers(self, client: EcoflowApiClient) -> list[BaseNumberEntity]`
        - 充電上限/下限、バックアップリザーブ、発電機自動起動/停止しきい値、AC充電パワー等のナンバーエンティティを生成
    - `switches(self, client: EcoflowApiClient) -> list[BaseSwitchEntity]`
        - ビーパー、DC出力、AC出力、X-Boost、AC常時出力、バックアップ電源設定等のスイッチエンティティを生成
    - `selects(self, client: EcoflowApiClient) -> list[BaseSelectEntity]`
        - DC充電電流、LCDオフタイマー、スタンバイモード、ACスタンバイタイマー等のセレクトエンティティを生成

### delta2_max.py
- 定義クラス: `Delta2Max(BaseDevice)`
- 主なメソッド:
    - `sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]`
        - delta_pro.pyと類似だが、paramsキーや一部名称が異なる(例: bms_bmsStatus.soc など)
    - `numbers(self, client: EcoflowApiClient) -> list[BaseNumberEntity]`
        - 充電上限/下限、バックアップリザーブ、発電機自動起動/停止しきい値、AC充電パワー等
    - `switches(self, client: EcoflowApiClient) -> list[BaseSwitchEntity]`
        - ビーパー、DC出力、AC常時出力、AC出力、X-Boost等
    - `selects(self, client: EcoflowApiClient) -> list[BaseSelectEntity]`
        - LCDオフタイマー、スタンバイモード、ACスタンバイタイマー等

---

## 2. 各メソッドの役割・呼び出し関係

- `sensors`/`numbers`/`switches`/`selects`は、Home Assistantの各種エンティティ(センサー/ナンバー/スイッチ/セレクト)を生成しリストで返す。
    - それぞれ `BaseSensorEntity` などのエンティティクラスを使い、paramsキーや属性名、単位等を指定。
    - コマンド送信が必要なエンティティはlambdaでparams構造を組み立てる。
- 各クラスは `BaseDevice` を継承し、Home Assistantのデバイスとして登録される。
- データパースや保持は `BaseDevice`・`EcoflowDataHolder` で共通実装。
- paramsキーやコマンド構造は機種ごとに異なる部分があるため、各クラスで個別に定義。

---

### ファイルごとの主な処理定義
- `custom_components/ecoflow_cloud/devices/internal/delta_pro.py`:
    - DeltaPro用のエンティティ定義(sensors/numbers/switches/selects)
    - paramsキーやコマンド構造の個別実装
- `custom_components/ecoflow_cloud/devices/internal/delta2_max.py`:
    - Delta2Max用のエンティティ定義(sensors/numbers/switches/selects)
    - paramsキーやコマンド構造の個別実装
- `custom_components/ecoflow_cloud/devices/__init__.py`:
    - BaseDeviceクラス(共通ロジック、データパース、エンティティ生成の抽象メソッド)
- `custom_components/ecoflow_cloud/devices/data_holder.py`:
    - EcoflowDataHolder(データ保持・履歴管理・params更新処理)
- `custom_components/ecoflow_cloud/devices/const.py`:
    - センサー名・属性名・単位等の定数・キー定義

---

このように、各デバイスごとに個別のエンティティ定義・コマンド構造を持ちつつ、共通部分はBaseDeviceやEcoflowDataHolderで実装されています。

## 3. センサー定義(sensorsメソッド)の詳細調査

### delta_pro.py
- **主なセンサー項目・属性**
    | センサー名 | paramsキー | データ型 | 単位 | 備考 |
    |:---|:---|:---|:---|:---|
    | Main Battery Level | bmsMaster.soc | int | % | メインバッテリー残量 |
    | Main Battery Level (Precise) | bmsMaster.f32ShowSoc | float | % | 精密残量 |
    | Main Design Capacity | bmsMaster.designCap | int | mAh | 設計容量 |
    | Main Full Capacity | bmsMaster.fullCap | int | mAh | フル充電容量 |
    | Main Remain Capacity | bmsMaster.remainCap | int | mAh | 残容量 |
    | State of Health | bmsMaster.soh | int | % | SOH |
    | Combined Battery Level | ems.lcdShowSoc | int | % | 複合バッテリー残量 |
    | Combined Battery Level (Precise) | ems.f32LcdShowSoc | float | % | |
    | Total In Power | pd.wattsInSum | int | W | 合計入力W |
    | Total Out Power | pd.wattsOutSum | int | W | 合計出力W |
    | AC In Power | inv.inputWatts | int | W | AC入力W |
    | AC Out Power | inv.outputWatts | int | W | AC出力W |
    | AC In Volts | inv.acInVol | int | mV | AC入力電圧 |
    | AC Out Volts | inv.invOutVol | int | mV | AC出力電圧 |
    | Solar In Power | mppt.inWatts | int | W | ソーラー入力W |
    | Solar In Voltage | mppt.inVol | int | V | ソーラー入力電圧 |
    | Solar In Current | mppt.inAmp | int | A | ソーラー入力電流 |
    | DC Out Power | mppt.outWatts | int | W | DC出力W |
    | DC Out Voltage | mppt.outVol | int | V | DC出力電圧 |
    | DC Car Out Power | mppt.carOutWatts | int | W | シガーソケット出力 |
    | DC Anderson Out Power | mppt.dcdc12vWatts | int | W | アンダーソン出力 |
    | Type-C (1) Out Power | pd.typec1Watts | int | W | Type-C1出力 |
    | Type-C (2) Out Power | pd.typec2Watts | int | W | Type-C2出力 |
    | USB (1) Out Power | pd.usb1Watts | int | W | USB1出力 |
    | USB (2) Out Power | pd.usb2Watts | int | W | USB2出力 |
    | USB QC (1) Out Power | pd.qcUsb1Watts | int | W | QC1出力 |
    | USB QC (2) Out Power | pd.qcUsb2Watts | int | W | QC2出力 |
    | Charge Remaining Time | ems.chgRemainTime | int | min | 充電残時間 |
    | Discharge Remaining Time | ems.dsgRemainTime | int | min | 放電残時間 |
    | Cycles | bmsMaster.cycles | int | 回 | サイクル数 |
    | Battery Temperature | bmsMaster.temp | int | ℃ | バッテリー温度 |
    | Min Cell Temperature | bmsMaster.minCellTemp | int | ℃ | 最小セル温度 |
    | Max Cell Temperature | bmsMaster.maxCellTemp | int | ℃ | 最大セル温度 |
    | Main Battery Current | bmsMaster.amp | int | mA | バッテリー電流 |
    | Battery Volts | bmsMaster.vol | int | mV | バッテリー電圧 |
    | Min Cell Volts | bmsMaster.minCellVol | int | mV | 最小セル電圧 |
    | Max Cell Volts | bmsMaster.maxCellVol | int | mV | 最大セル電圧 |
    | Solar In Energy | pd.chgSunPower | int | Wh | ソーラー充電量 |
    | Battery Charge Energy from AC | pd.chgPowerAc | int | Wh | AC充電量 |
    | Battery Charge Energy from DC | pd.chgPowerDc | int | Wh | DC充電量 |
    | Battery Discharge Energy to AC | pd.dsgPowerAc | int | Wh | AC放電量 |
    | Battery Discharge Energy to DC | pd.dsgPowerDc | int | Wh | DC放電量 |
    | Quota Status | - | - | - | ステータス用 |
- **スレーブバッテリー等の特殊項目**
    - bmsSlave1, bmsSlave2系の項目(残量、設計容量、SOH、温度、電圧、入出力W、サイクル数等)を個別に定義。
    - スレーブバッテリーが接続されている場合のみ有効。

### delta2_max.py
- **主なセンサー項目・属性**
    | センサー名 | paramsキー | データ型 | 単位 | 備考 |
    |:---|:---|:---|:---|:---|
    | Main Battery Level | bms_bmsStatus.soc | int | % | メインバッテリー残量 |
    | Main Design Capacity | bms_bmsStatus.designCap | int | mAh | 設計容量 |
    | Main Full Capacity | bms_bmsStatus.fullCap | int | mAh | フル充電容量 |
    | Main Remain Capacity | bms_bmsStatus.remainCap | int | mAh | 残容量 |
    | State of Health | bms_bmsStatus.soh | int | % | SOH |
    | Combined Battery Level | bms_emsStatus.lcdShowSoc | int | % | 複合バッテリー残量 |
    | Total In Power | pd.wattsInSum | int | W | 合計入力W |
    | Total Out Power | pd.wattsOutSum | int | W | 合計出力W |
    | AC In Power | inv.inputWatts | int | W | AC入力W |
    | AC Out Power | inv.outputWatts | int | W | AC出力W |
    | AC In Volts | inv.acInVol | int | mV | AC入力電圧 |
    | AC Out Volts | inv.invOutVol | int | mV | AC出力電圧 |
    | Solar (1) In Power | mppt.inWatts | int | W | ソーラー1入力W |
    | Solar (2) In Power | mppt.pv2InWatts | int | W | ソーラー2入力W |
    | Solar (1) In Volts | mppt.inVol | int | V | ソーラー1入力電圧 |
    | Solar (2) In Volts | mppt.pv2InVol | int | V | ソーラー2入力電圧 |
    | Solar (1) In Amps | mppt.inAmp | int | A | ソーラー1入力電流 |
    | Solar (2) In Amps | mppt.pv2InAmp | int | A | ソーラー2入力電流 |
    | DC Out Power | mppt.outWatts | int | W | DC出力W |
    | Type-C (1) Out Power | pd.typec1Watts | int | W | Type-C1出力 |
    | Type-C (2) Out Power | pd.typec2Watts | int | W | Type-C2出力 |
    | USB (1) Out Power | pd.usb1Watts | int | W | USB1出力 |
    | USB (2) Out Power | pd.usb2Watts | int | W | USB2出力 |
    | USB QC (1) Out Power | pd.qcUsb1Watts | int | W | QC1出力 |
    | USB QC (2) Out Power | pd.qcUsb2Watts | int | W | QC2出力 |
    | Charge Remaining Time | bms_emsStatus.chgRemainTime | int | min | 充電残時間 |
    | Discharge Remaining Time | bms_emsStatus.dsgRemainTime | int | min | 放電残時間 |
    | Cycles | bms_bmsStatus.cycles | int | 回 | サイクル数 |
    | Battery Temperature | bms_bmsStatus.temp | int | ℃ | バッテリー温度 |
    | Min Cell Temperature | bms_bmsStatus.minCellTemp | int | ℃ | 最小セル温度 |
    | Max Cell Temperature | bms_bmsStatus.maxCellTemp | int | ℃ | 最大セル温度 |
    | Battery Volts | bms_bmsStatus.vol | int | mV | バッテリー電圧 |
    | Min Cell Volts | bms_bmsStatus.minCellVol | int | mV | 最小セル電圧 |
    | Max Cell Volts | bms_bmsStatus.maxCellVol | int | mV | 最大セル電圧 |
    | Battery level SOC | bms_bmsStatus.f32ShowSoc | float | % | 精密残量 |
    | Quota Status | - | - | - | ステータス用 |
- **スレーブバッテリー等の特殊項目**
    - bms_slave_bmsSlaveStatus_1, bms_slave_bmsSlaveStatus_2系の項目(残量、設計容量、SOH、温度、電圧、入出力W、サイクル数等)を個別に定義。
    - スレーブバッテリーが接続されている場合のみ有効。

### delta_pro_3.py(作りかけ)
- **主なセンサー項目・属性**
    | センサー名 | paramsキー | データ型 | 単位 | 備考 |
    |:---|:---|:---|:---|:---|
    | Main Battery Level | bmsBattSoc | int | % | メインバッテリー残量 |
    | Main Design Capacity | bmsDesignCap | int | mAh | 設計容量 |
    | Combined Battery Level | cmsBattSoc | int | % | 複合バッテリー残量 |
    | Total In Power | powInSumW | int | W | 合計入力W |
    | Total Out Power | powOutSumW | int | W | 合計出力W |
    | AC In Power | powGetAcIn | int | W | AC入力W |
- **未実装・不足項目**
    - スレーブバッテリー関連、SOH、温度、電圧、サイクル数、USB/TypeC/DC/ソーラー等の詳細センサーが未定義。
    - 既存delta_pro.py/delta2_max.pyの定義と比較し、paramsキーやエンティティの追加が必要。

## 4. スイッチ定義(switchesメソッド)の詳細調査

### delta_pro.py
- **主なスイッチ項目・属性**
    | スイッチ名 | paramsキー | 操作内容 | コマンド構造(lambda/params例) | 備考 |
    |:---|:---|:---|:---|:---|
    | Beeper | pd.beepState | ビーパーON/OFF | {"moduleType":0, "operateType":"TCP", "params":{"id":38, "enabled":value}} | |
    | DC Enabled | mppt.carState | DC出力ON/OFF | {"moduleType":0, "operateType":"TCP", "params":{"id":81, "enabled":value}} | シガーソケット等 |
    | AC Enabled | inv.cfgAcEnabled | AC出力ON/OFF | {"moduleType":0, "operateType":"TCP", "params":{"id":66, "enabled":value}} | |
    | X-Boost Enabled | inv.cfgAcXboost | X-Boost機能ON/OFF | {"moduleType":0, "operateType":"TCP", "params":{"id":66, "xboost":value}} | |
    | AC Always On | pd.acautooutConfig | AC常時出力ON/OFF | {"moduleType":0, "operateType":"TCP", "params":{"id":95, "acautooutConfig":value}} | |
    | Backup Reserve Enabled | pd.watthisconfig | バックアップ電源設定 | {"moduleType":0, "operateType":"TCP", "params":{"id":94, "isConfig":value, "bpPowerSoc":value*50, "minDsgSoc":0, "maxChgSoc":0}} | |

### delta2_max.py
- **主なスイッチ項目・属性**
    | スイッチ名 | paramsキー | 操作内容 | コマンド構造(lambda/params例) | 備考 |
    |:---|:---|:---|:---|:---|
    | Beeper | pd.beepMode | ビーパーON/OFF | {"moduleType":1, "operateType":"quietCfg", "moduleSn":sn, "params":{"enabled":value}} | |
    | DC Enabled | pd.dcOutState | DC出力ON/OFF | {"moduleType":1, "operateType":"dcOutCfg", "moduleSn":sn, "params":{"enabled":value}} | |
    | AC Always On | pd.newAcAutoOnCfg | AC常時出力ON/OFF | {"moduleType":1, "operateType":"newAcAutoOnCfg", "moduleSn":sn, "params":{"enabled":value, "minAcSoc":5}} | |
    | AC Enabled | inv.cfgAcEnabled | AC出力ON/OFF | {"moduleType":3, "operateType":"acOutCfg", "moduleSn":sn, "params":{"enabled":value, "out_voltage":-1, "out_freq":255, "xboost":255}} | |
    | X-Boost Enabled | inv.cfgAcXboost | X-Boost機能ON/OFF | {"moduleType":3, "operateType":"acOutCfg", "moduleSn":sn, "params":{"xboost":value}} | |
    | DC Enabled (MPPT) | pd.carState | DC出力ON/OFF | {"moduleType":5, "operateType":"mpptCar", "params":{"enabled":value}} | Delta2Max固有 |
    | Backup Reserve Enabled | pd.watchIsConfig | バックアップ電源設定 | {"moduleType":1, "operateType":"watthConfig", "params":{"bpPowerSoc":value*50, "minChgSoc":0, "isConfig":value, "minDsgSoc":0}} | |

### delta_pro_3.py(作りかけ)
- **現状スイッチ定義なし**
    - switchesメソッドは空リストを返すのみ。今後、既存機種のスイッチ定義・コマンド構造を参考にDP3用のスイッチ項目・paramsキー・コマンド構造を追加実装する必要あり。

## 5. スライダー/ナンバー定義(numbersメソッド)の詳細調査

### delta_pro.py
- **主なナンバー項目・属性**
    | ナンバー名 | paramsキー | 設定範囲 | 単位 | コマンド構造(lambda/params例) | 備考 |
    |:---|:---|:---|:---|:---|:---|
    | Max Charge Level | ems.maxChargeSoc | 50-100 | % | {"moduleType":0, "operateType":"TCP", "params":{"id":49, "maxChgSoc":value}} | 充電上限 |
    | Min Discharge Level | ems.minDsgSoc | 0-30 | % | {"moduleType":0, "operateType":"TCP", "params":{"id":51, "minDsgSoc":value}} | 放電下限 |
    | Backup Reserve Level | pd.bppowerSoc | 5-100 | % | {"moduleType":0, "operateType":"TCP", "params":{"isConfig":1, "bpPowerSoc":int(value), "minDsgSoc":0, "maxChgSoc":0, "id":94}} | バックアップリザーブ |
    | Generator Auto Start Level | ems.minOpenOilEbSoc | 0-30 | % | {"moduleType":0, "operateType":"TCP", "params":{"openOilSoc":value, "id":52}} | 発電機自動起動しきい値 |
    | Generator Auto Stop Level | ems.maxCloseOilEbSoc | 50-100 | % | {"moduleType":0, "operateType":"TCP", "params":{"closeOilSoc":value, "id":53}} | 発電機自動停止しきい値 |
    | AC Charging Power | inv.cfgSlowChgWatts | 200-2900 | W | {"moduleType":0, "operateType":"TCP", "params":{"slowChgPower":value, "id":69}} | AC充電パワー |

### delta2_max.py
- **主なナンバー項目・属性**
    | ナンバー名 | paramsキー | 設定範囲 | 単位 | コマンド構造(lambda/params例) | 備考 |
    |:---|:---|:---|:---|:---|:---|
    | Max Charge Level | bms_emsStatus.maxChargeSoc | 50-100 | % | {"moduleType":2, "operateType":"upsConfig", "moduleSn":sn, "params":{"maxChgSoc":int(value)}} | 充電上限 |
    | Min Discharge Level | bms_emsStatus.minDsgSoc | 0-30 | % | {"moduleType":2, "operateType":"dsgCfg", "moduleSn":sn, "params":{"minDsgSoc":int(value)}} | 放電下限 |
    | Backup Reserve Level | pd.bpPowerSoc | 5-100 | % | {"moduleType":1, "operateType":"watthConfig", "params":{"isConfig":1, "bpPowerSoc":int(value), "minDsgSoc":0, "minChgSoc":0}} | バックアップリザーブ |
    | Generator Auto Start Level | bms_emsStatus.minOpenOilEbSoc | 0-30 | % | {"moduleType":2, "operateType":"openOilSoc", "moduleSn":sn, "params":{"openOilSoc":value}} | 発電機自動起動しきい値 |
    | Generator Auto Stop Level | bms_emsStatus.maxCloseOilEbSoc | 50-100 | % | {"moduleType":2, "operateType":"closeOilSoc", "moduleSn":sn, "params":{"closeOilSoc":value}} | 発電機自動停止しきい値 |
    | AC Charging Power | inv.SlowChgWatts | 200-2400 | W | {"moduleType":3, "operateType":"acChgCfg", "moduleSn":sn, "params":{"slowChgWatts":int(value), "fastChgWatts":2000, "chgPauseFlag":0}} | AC充電パワー |

### delta_pro_3.py(作りかけ)
- **主なナンバー項目・属性**
    | ナンバー名 | paramsキー | 設定範囲 | 単位 | コマンド構造(lambda/params例) | 備考 |
    |:---|:---|:---|:---|:---|:---|
    | AC Charging Power | cfgPlugInInfoAcInChgPowMax | 400-2900 | W | {"sn":sn, "cmdId":17, "dirDest":1, "dirSrc":1, "cmdFunc":254, "dest":2, "params":{"cfgPlugInInfoAcInChgPowMax":value}} | AC充電パワーのみ定義、他は未実装 |
- **未実装・不足項目**
    - 既存機種のMax/Minバッテリーレベル、バックアップリザーブ、発電機しきい値等のナンバー項目が未定義。今後追加実装が必要。

## 6. セレクト定義(selectsメソッド)の詳細調査

### delta_pro.py
- **主なセレクト項目・属性**
    | セレクト名 | paramsキー | 選択肢 | コマンド構造(lambda/params例) | 備考 |
    |:---|:---|:---|:---|:---|
    | DC Charge Current | mppt.cfgDcChgCurrent | 4A/6A/8A | {"moduleType":0, "operateType":"TCP", "params":{"currMa":value, "id":71}} | DC充電電流 |
    | Screen Timeout | pd.lcdOffSec | Never/10sec/30sec/1min/5min/30min | {"moduleType":0, "operateType":"TCP", "params":{"lcdTime":value, "id":39}} | LCDオフタイマー |
    | Unit Timeout | pd.standByMode | Never/30min/1hr/2hr/6hr/12hr | {"moduleType":0, "operateType":"TCP", "params":{"standByMode":value, "id":33}} | スタンバイモード |
    | AC Timeout | inv.cfgStandbyMin | Never/30min/1hr/2hr/4hr/6hr/12hr/24hr | {"moduleType":0, "operateType":"TCP", "params":{"standByMins":value, "id":153}} | ACスタンバイタイマー |

### delta2_max.py
- **主なセレクト項目・属性**
    | セレクト名 | paramsキー | 選択肢 | コマンド構造(lambda/params例) | 備考 |
    |:---|:---|:---|:---|:---|
    | Screen Timeout | pd.lcdOffSec | Never/10sec/30sec/1min/5min/30min | {"moduleType":1, "operateType":"lcdCfg", "moduleSn":sn, "params":{"brighLevel":255, "delayOff":value}} | LCDオフタイマー |
    | Unit Timeout | inv.standbyMin | Never/30min/1hr/2hr/4hr/6hr/12hr/24hr | {"moduleType":1, "operateType":"standbyTime", "moduleSn":sn, "params":{"standbyMin":value}} | スタンバイモード |
    | AC Timeout | mppt.carStandbyMin | Never/30min/1hr/2hr/4hr/6hr/12hr/24hr | {"moduleType":5, "operateType":"standbyTime", "moduleSn":sn, "params":{"standbyMins":value}} | ACスタンバイタイマー |

### delta_pro_3.py(作りかけ)
- **現状セレクト定義なし**
    - selectsメソッドは空リストを返すのみ。今後、既存機種のセレクト定義・コマンド構造を参考にDP3用のセレクト項目・paramsキー・コマンド構造を追加実装する必要あり。

## 7. データパース・保持ロジックの調査

### BaseDeviceクラスの役割・継承構造
- ファイル: `custom_components/ecoflow_cloud/devices/__init__.py`
- 役割:
    - 各デバイス(DeltaPro, Delta2Max, DeltaPro3等)の基底クラス。
    - Home Assistant連携のためのエンティティ生成(sensors/numbers/switches/selects/buttons)抽象メソッドを持つ。
    - データ保持用に `EcoflowDataHolder` をself.dataとして保持。
    - `update_data(raw_data, data_type)` でMQTT等から受信した生データをパースし、EcoflowDataHolderへ格納。
    - データパース処理は `_prepare_data(raw_data)` で実施。標準はJSONデコードだが、機種ごとにオーバーライド可能。
    - 継承構造: 各デバイス定義クラス(DeltaPro等)はBaseDeviceを継承し、エンティティ定義やコマンド構造を個別実装。

### EcoflowDataHolderによるデータ保持・履歴管理
- ファイル: `custom_components/ecoflow_cloud/devices/data_holder.py`
- 役割:
    - params(最新のパラメータ辞書)、status(状態値)、get/setメッセージ履歴、rawデータ履歴を保持。
    - BoundFifoListで各種履歴(最大20件)をFIFO管理。
    - update_data(raw)でparamsを更新、update_status(raw)でstatusを更新。
    - add_set_message/add_get_message等でコマンド送信・応答履歴を管理。
    - update_to_target_stateでjsonpathによる部分更新も可能。
    - last_received_timeで最新受信時刻を取得し、HA側の更新判定に利用。

### update_data/_prepare_dataのデータパース処理詳細
- BaseDevice.update_data(raw_data, data_type):
    - data_typeに応じて_set/_get/_reply等の種別を判定し、_prepare_dataでパース後EcoflowDataHolderへ格納。
    - _prepare_dataの標準実装はUTF-8デコード→JSONデコード。UnicodeDecodeError等も考慮。
    - デバイスごとに必要に応じてオーバーライドし、Protobufやバイナリ→dict変換等も可能。
- EcoflowDataHolder.update_data(raw):
    - params(パラメータ辞書)を更新。module_sn指定時は一致するデータのみ反映。
    - __add_raw_dataで生データ履歴も管理(diagnostic_mode時)。
    - update_status(raw)でstatus値のみを個別更新可能。

---

このように、BaseDeviceがデータ受信・パース・保持の流れを統括し、EcoflowDataHolderが各種データの履歴・状態管理を担う構造となっている。DP3対応時もこの枠組みを踏襲しつつ、必要に応じてパース処理やparams構造を拡張することが推奨される。

## 8. 定数・キー定義の調査

### const.pyの主な定数・キー(センサー名、属性名、単位等)
- ファイル: `custom_components/ecoflow_cloud/devices/const.py`
- 代表的な定数・キー一覧(一部抜粋):
    - センサー名:
        - `MAIN_BATTERY_LEVEL` = "Main Battery Level"
        - `COMBINED_BATTERY_LEVEL` = "Battery Level"
        - `TOTAL_IN_POWER` = "Total In Power"
        - `AC_IN_POWER` = "AC In Power"
        - `SOLAR_IN_POWER` = "Solar In Power"
        - `USB_1_OUT_POWER` = "USB (1) Out Power"
        - `TYPEC_1_OUT_POWER` = "Type-C (1) Out Power"
        - `CYCLES` = "Cycles"
        - `SOH` = "State of Health"
        - `BATTERY_TEMP` = "Battery Temperature"
        - `MIN_CELL_TEMP` = "Min Cell Temperature"
        - `MAX_CELL_TEMP` = "Max Cell Temperature"
        - `BATTERY_VOLT` = "Battery Volts"
        - `MIN_CELL_VOLT` = "Min Cell Volts"
        - `MAX_CELL_VOLT` = "Max Cell Volts"
        - ...(他、多数)
    - 属性名:
        - `ATTR_DESIGN_CAPACITY` = "Design Capacity (mAh)"
        - `ATTR_FULL_CAPACITY` = "Full Capacity (mAh)"
        - `ATTR_REMAIN_CAPACITY` = "Remain Capacity (mAh)"
        - `ATTR_MIN_CELL_TEMP` = "Min Cell Temperature"
        - `ATTR_MAX_CELL_TEMP` = "Max Cell Temperature"
        - `ATTR_MIN_CELL_VOLT` = "Min Cell Volts"
        - `ATTR_MAX_CELL_VOLT` = "Max Cell Volts"
        - ...
    - 単位:
        - %(バッテリー残量、SOH等)
        - mAh(容量)
        - W(電力)
        - V/mV(電圧)
        - A(電流)
        - ℃(温度)
        - min(残時間)
        - 回(サイクル数)
        - ...

### paramsキーとエンティティ名の対応表(一部例)
| paramsキー | エンティティ名(const.py定数) | 単位 | 備考 |
|:---|:---|:---|:---|
| bmsMaster.soc | MAIN_BATTERY_LEVEL | % | メインバッテリー残量 |
| bmsMaster.f32ShowSoc | MAIN_BATTERY_LEVEL_F32 | % | 精密残量 |
| ems.lcdShowSoc | COMBINED_BATTERY_LEVEL | % | 複合バッテリー残量 |
| pd.wattsInSum | TOTAL_IN_POWER | W | 合計入力W |
| inv.inputWatts | AC_IN_POWER | W | AC入力W |
| mppt.inWatts | SOLAR_IN_POWER | W | ソーラー入力W |
| pd.typec1Watts | TYPEC_1_OUT_POWER | W | Type-C1出力 |
| pd.usb1Watts | USB_1_OUT_POWER | W | USB1出力 |
| bmsMaster.cycles | CYCLES | 回 | サイクル数 |
| bmsMaster.soh | SOH | % | State of Health |
| bmsMaster.temp | BATTERY_TEMP | ℃ | バッテリー温度 |
| bmsMaster.minCellTemp | MIN_CELL_TEMP | ℃ | 最小セル温度 |
| bmsMaster.maxCellTemp | MAX_CELL_TEMP | ℃ | 最大セル温度 |
| bmsMaster.vol | BATTERY_VOLT | mV | バッテリー電圧 |
| bmsMaster.minCellVol | MIN_CELL_VOLT | mV | 最小セル電圧 |
| bmsMaster.maxCellVol | MAX_CELL_VOLT | mV | 最大セル電圧 |
| ... | ... | ... | ... |

> ※全対応表はdelta_pro.py/delta2_max.pyのsensorsメソッド定義とconst.pyを突き合わせて随時拡充してください。

## 9. エンティティ生成・Home Assistant連携フローの調査

### エンティティクラス(BaseSensorEntity等)の役割整理
- ファイル: `custom_components/ecoflow_cloud/entities/__init__.py`
- 主なエンティティ基底クラス:
    - `BaseSensorEntity`(SensorEntity, EcoFlowDictEntity継承)
        - paramsキーで指定された値をHome Assistantのセンサーとして公開
        - 追加属性(attr)もparamsから抽出し、extra_state_attributesとして付与
        - データ更新時は_coordinator経由でparamsを監視し、値・属性を更新
    - `BaseNumberEntity`(NumberEntity, EcoFlowBaseCommandEntity継承)
        - 数値入力(スライダー)エンティティ。コマンド送信ロジックも内包
    - `BaseSwitchEntity`(SwitchEntity, EcoFlowBaseCommandEntity継承)
        - ON/OFFスイッチエンティティ。コマンド送信ロジックも内包
    - `BaseSelectEntity`(SelectEntity, EcoFlowBaseCommandEntity継承)
        - 選択肢(セレクト)エンティティ。コマンド送信ロジックも内包
    - `EcoFlowDictEntity`/`EcoFlowAbstractEntity`
        - paramsから値・属性を抽出し、coordinatorのデータ更新を監視
        - unique_idやdevice_infoなどHA連携に必要な情報も生成

### エンティティ生成からHome Assistant登録・値更新までの流れ
1. **デバイス定義クラス(例: DeltaPro)でsensors/numbers/switches/selectsメソッドを実装**
    - 各メソッドでBaseSensorEntity等のリストを生成し、paramsキー・タイトル・属性等を指定
2. **custom_components/ecoflow_cloud/sensor.py等のasync_setup_entryで各デバイスのエンティティを取得**
    - 例: `async_add_entities(device.sensors(client))`
3. **Home Assistantにエンティティが登録される**
    - unique_id, device_info, entity_category等が自動付与
4. **EcoflowDeviceUpdateCoordinatorが定期的にデータ更新を検知**
    - MQTT等で新データ受信→EcoflowDataHolderのparams更新→coordinator.changedフラグON
5. **エンティティ(BaseSensorEntity等)が_coordinator経由でparamsの変化を検知し、値・属性を更新**
    - _handle_coordinator_update→_updatedでparamsから値・属性を抽出し、HAに反映
6. **ユーザー操作(スイッチON/OFF等)はBaseSwitchEntity等のcommand_dict/send_set_message経由でコマンド送信**

#### 流れ図(簡易)
```
[MQTT/REST受信] → [EcoflowDataHolder(params更新)]
        ↓
[EcoflowDeviceUpdateCoordinator.changed]
        ↓
[BaseSensorEntity等._handle_coordinator_update]
        ↓
[paramsから値・属性抽出] → [HAエンティティ値/属性更新]
```

> ※コマンド送信系(スイッチ/ナンバー/セレクト)はユーザー操作時にcommand_dict/send_set_messageが呼ばれ、API経由でデバイスに反映される。

## 10. 既存定義のDP3対応時の流用・拡張ポイント整理
- [ ] 共通化できる部分、DP3特有の追加・修正が必要な部分の洗い出し
- [ ] コード・定義の差分比較、流用設計案の作成

---

### RIVER 2 Pro定義の試みから得られた知見(DP3開発への参考情報)

本調査の一環として、既存の`delta2_max.py`をベースに`river2_pro.py`のデバイス定義ファイル作成を試みました。この過程で得られた知見は、DP3のような新機種を開発する上でも参考になると考えられます。

*   **仕様差異の具体例とエンティティ定義への影響:**
    *   Web検索により、RIVER 2 Proの主な仕様(容量768Wh, AC出力800W(X-Boost時1600W), ソーラー入力最大220W, 拡張バッテリー非対応など)が判明しました。
    *   **センサーエンティティ:** DELTA2 Maxがデュアルソーラー入力や複数拡張バッテリーに対応可能なのに対し、RIVER 2 Proはシングルソーラー入力であり、拡張バッテリーも接続できません。このため、`sensors`メソッド内で定義するセンサーエンティティは、`mppt.pv2InWatts`のような2つ目のソーラー入力関連や、`bms_slave_bmsSlaveStatus_X`のような拡張バッテリー関連のものが不要になります。
    *   **ナンバーエンティティ:** RIVER 2 ProのAC充電電力の最大値は940Wであり、DELTA2 Maxの2400Wとは異なります。これにより、`ChargingPowerEntity`の最大値パラメータや、コマンド送信時の`fastChgWatts`のような関連パラメータの調整が必要です。また、発電機連携機能を持たない可能性が高いため、`MinGenStartLevelEntity`や`MaxGenStopLevelEntity`は不要となるでしょう。
    *   **スイッチ/セレクトエンティティ:** RIVER 2 Proの機能セットに合わせて、不要なスイッチ(例:発電機制御関連)を削除したり、タイムアウト設定などの選択肢やコマンドパラメータをRIVER 2 Proの仕様に合わせる必要があります。
*   **コマンド構造と型シグネチャに関する注意点:**
    *   実際に`river2_pro.py`の雛形を作成し、各種エンティティ(特に`BaseNumberEntity`を継承するクラス)を定義する過程で、コマンド送信時の`lambda`関数の引数構造に関して型エラーが観測されました。
    *   これは、`BaseNumberEntity`などの基底クラスが期待する`command`コールバックの型シグネチャ(例: `Callable[[int, Optional[Dict[str, Any]]], Dict[str, Any]]`)と、単純な`lambda value: {...}`という形式(これは`Callable[[int], Dict[str, Any]]`に相当)との間に不一致が生じたためです。
    *   この経験から、コマンドを送信するエンティティを定義する際には、基底クラスのインターフェースを正確に理解し、`lambda`関数が適切な数の引数(第二引数として現在の全パラメータ辞書を受け取る可能性があるなど)を取るように定義する必要があることがわかります。DP3実装時も、既存コードを流用する際にはこの点に注意し、必要に応じて`lambda`のシグネチャを調整するか、より明示的な関数定義を用いることを検討すべきです。

### DP3開発への具体的な示唆・アクションアイテム

上記のRIVER 2 Proのケーススタディや、既存のDelta Pro/Delta 2 Max/Delta Pro 3(作りかけ)の調査結果を踏まえ、DP3開発においては以下の点に注力・留意すべきです。

1.  **パラメータキーの特定と正規化戦略:**
    *   **傾向:** `bmsMaster.soc` (Delta Pro), `bms_bmsStatus.soc` (Delta 2 Max), `bmsBattSoc` (Delta Pro 3初期案) のように、同一機能でも機種・世代間でキー名が異なるケースが散見されます。
    *   **DP3対応:** DP3の正確なパラメータキーを特定するため、公式ドキュメント、API仕様書(入手可能であれば)、あるいは実機からのMQTTデータキャプチャが不可欠です。特定後は、既存機種との対応関係を明確にし、必要であれば内部的に正規化したキー名へマッピングするような抽象化レイヤーの導入も検討します(メンテナンス性向上のため)。

2.  **コマンド構造の解析と共通化:**
    *   **傾向:** Delta ProのTCPベースのID指定型コマンド (`{"moduleType":0, "operateType":"TCP", "params":{"id": ..., ...}}`) と、Delta 2 Max/RIVER 2 Pro(推定)のSN指定・個別オペレーション名型コマンド (`{"moduleType":X, "operateType":"someCfg", "moduleSn":sn, "params":{...}}`) の2系統が見られます。
    *   **DP3対応:** DP3がどちらの系統に属するのか、あるいは新しい構造を持つのかを早期に特定します。コマンド送信部分のロジックを機種共通のヘルパー関数やクラスに集約し、機種ごとの差異(`moduleType`, `operateType`, `id`の有無など)をパラメータで吸収できるような設計を目指します。

3.  **機能セットの網羅的把握とエンティティ設計:**
    *   **DP3のフル機能リスト作成:** Delta Proの機能セットをベースに、Delta 2 Maxや他社ハイエンド機種の機能も参考に、DP3に搭載されうる機能(特に電力制御、エネルギーマネジメント、スマートホーム連携関連)の網羅的なリストを作成します。
    *   **エンティティマッピング:** 各機能に対して、Home Assistantでどのエンティティ種別(センサー、スイッチ、ナンバー、セレクト、ボタン等)で表現するのが最適かを検討します。既存のエンティティクラスで対応可能か、新規作成・拡張が必要かを判断します。DP3特有の高度な設定項目については、複数のエンティティを組み合わせたり、専用のUI(例: 設定ダイアログ)を検討する必要も出てくるかもしれません。

4.  **スレーブバッテリー・拡張性の考慮:**
    *   DP3は拡張バッテリーや他デバイスとの連携機能を持つ可能性が高いです。Delta ProやDelta 2 Maxのスレーブバッテリー処理(`bms_slave_bmsSlaveStatus_X`系のパラメータ群)を参考に、DP3における拡張ユニットの認識方法、データ取得・コマンド送信の仕組みを調査し、柔軟に対応できる構造を設計します。

5.  **段階的実装とテスト計画:**
    *   まずは主要な基本機能(バッテリー残量、AC/DC入出力、充電制御など)から実装を開始し、段階的に高度な機能やオプション機能へと拡張していく計画を立てます。各機能の実装単位でテストケースを作成し、実機検証(可能であれば)またはシミュレータによる検証を行います。

これらのポイントを踏まえ、DP3のデバイス定義ファイル (`delta_pro_3.py`) の具体的な実装に着手していくことになります。

---

### 備考
- 各タスクは進捗や新たな発見に応じてさらに細分化・追記してください。
- 実装・設計・ドキュメント化の各フェーズで本タスクを参照・更新すること。