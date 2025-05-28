import logging
from typing import Type, cast, Any

# 生成されたProtobufコードをインポート (scriptsフォルダ直下にあると仮定)
# import sys
# from pathlib import Path
# current_dir = Path(__file__).resolve().parent # ecoflow_mqtt_parser
# scripts_dir = current_dir.parent # scripts
# sys.path.append(str(scripts_dir))

# ef_dp3_iobroker_pb2.py は scripts ディレクトリにあり、
# main_parser.py で sys.path が調整されることを前提として直接インポートします。
import ef_dp3_iobroker_pb2 as ecopacket_pb2

from google.protobuf.message import Message

logger = logging.getLogger(__name__)

# DELTA Pro 3 specific cmdId/cmdFunc to Protobuf message type mapping
# This mapping is based on ioBroker.ecoflow-mqtt/lib/dict_data/ef_deltapro3_data.js
DELTA_PRO_3_MESSAGE_DECODERS: dict[int, dict[int, type]] = {
    2: {  # cmdId
        32: ecopacket_pb2.cmdFunc32_cmdId2_Report,
    },
    17: {  # cmdId
        254: ecopacket_pb2.set_dp3,
    },
    18: {  # cmdId
        254: ecopacket_pb2.setReply_dp3,
    },
    21: {  # cmdId
        254: ecopacket_pb2.DisplayPropertyUpload,
    },
    22: {  # cmdId
        254: ecopacket_pb2.RuntimePropertyUpload,
    },
    23: {  # cmdId
        254: ecopacket_pb2.cmdFunc254_cmdId23_Report,
    },
    50: {  # cmdId (Interpreted from 'cmdFunc50_cmdId30_Report', assuming typo in original ioBroker file for cmdId)
        32: ecopacket_pb2.cmdFunc50_cmdId30_Report,  # Note: Message name implies cmdId 30, but key is 50
    },
    # Add other cmdId/cmdFunc mappings for DELTA Pro 3 as they are identified
    # Example:
    # 1: { # cmdId for a hypothetical "GetStatus"
    #     1: ecopacket_pb2.GetStatusReply, # cmdFunc for reply
    # },
}

# Re-export key Protobuf types for convenience
Header = ecopacket_pb2.Header
HeaderMessage = ecopacket_pb2.HeaderMessage
setMessage = ecopacket_pb2.setMessage

# Header parameters for requesting all data from DELTA Pro 3
# Based on ioBroker.ecoflow-mqtt/lib/dict_data/ef_deltapro3_data.js -> deviceCmd.action.latestQuotas
GET_ALL_DATA_HEADER_PARAMS = {
    "dest": 32,  # Typically the device address (e.g., 0x20 for DeltaPro3)
    "cmd_func": 20,  # As per ef_deltapro3_data.js 'action.latestQuotas'
    "cmd_id": 1,  # As per ef_deltapro3_data.js 'action.latestQuotas'
    "pdata": b"",  # Usually empty for "get all data" type requests
    "data_len": 0,
    # src, enc_type, seq などは送信時に動的に設定されるべき
}


# cmdId と cmdFunc の組み合わせに基づいて、適切な Protobuf メッセージ型を返す関数
def get_protobuf_decoder(cmd_id: int, cmd_func: int) -> Type[Message] | None:
    """指定された cmd_id と cmd_func に基づいて Protobuf デコーダーメッセージ型を返します。"""
    cmd_id_map = DELTA_PRO_3_MESSAGE_DECODERS.get(cmd_id)
    if cmd_id_map:
        return cast(Type[Message], cmd_id_map.get(cmd_func))
    return None


def get_all_header_params_for_request() -> dict[str, Any]:
    """全データ取得要求のためのヘッダーパラメータを返します。"""
    # この関数はmqtt_client_setup.pyで使用される想定
    # 必要に応じて、より動的なパラメータ生成ロジックをここに追加できます。
    return GET_ALL_DATA_HEADER_PARAMS.copy()


# 必要に応じて、他のデバイスや汎用的なマッピングもここに追加できます。

# --- ef_dp3_iobroker_pb2.py に含まれる主要なメッセージの再エクスポート (利便性のため) ---
# これにより、他のモジュールは protobuf_mapping から直接これらの型をインポートできる。
# ただし、ef_dp3_iobroker_pb2.py が正しく生成され、これらの型を含んでいることが前提。

# AppVersion = ecopacket_pb2.AppVersion  # もしあれば
# ... その他の共通して使われる型

# グローバルな Protobuf 型へのアクセスポイントを提供
# ecopacket = ecopacket_pb2 # これで ecopacket.Header のようにアクセスできる

# ioBroker の ef_deltapro3_data.js にある protoSource のような、
# インラインの .proto スキーマ定義を Python で扱う場合、
# protobuf ライブラリの TextFormat や DescriptorPool を使って動的にメッセージ型を
# ロード・コンパイルする必要があり、より複雑になります。
# 現時点では、事前に生成された _pb2.py ファイルが存在することを前提とします。

# --- デバイスコマンド定義 (送信メッセージ用) ---
# issue_02 の deviceCmd オブジェクトに相当する情報
# (例: 全データ取得要求など)
# これらは送信メッセージを構築する際に使用します。

# 例: 全データ取得要求 (ioBroker の latestQuotas に相当)
# main.js の onReady で送信しているメッセージは Header のみで pdata は空だった。
# deviceCmd の latestQuotas は cmdFunc: 20, cmdId: 1 を示しているが、これは
# おそらく何らかの状態変化をトリガーするための内部的なIDであり、
# MQTTで送信する際のHeaderのcmdFunc/cmdIdとは直接対応しない可能性がある。
# mqtt_capture_dp3_debug.py の on_connect で送信していたのは空のHeaderだった。

logger.info(
    f"Protobuf mapping initialized. Available base types from ecopacket_pb2: Header, HeaderMessage, setMessage"
)
if not DELTA_PRO_3_MESSAGE_DECODERS:
    logger.warning(
        "DELTA_PRO_3_MESSAGE_DECODERS is empty. Specific pdata decoding will not be available until this is populated and ef_dp3_iobroker_pb2.py contains the necessary types."
    )
