#!/usr/bin/env python3
"""
Debug script to understand the protobuf message structure from saved test data
"""

import sys
import json
from pathlib import Path

# Add protobuf path
sys.path.append(str(Path.cwd().parent.parent))

from custom_components.ecoflow_cloud.devices.internal.proto import (
    ef_dp3_iobroker_pb2 as pb2,
)


def analyze_protobuf_data():
    """Analyze the saved raw messages to understand structure"""
    
    raw_messages_file = Path("test_results/raw_messages.jsonl")
    if not raw_messages_file.exists():
        print("No raw messages file found")
        return
    
    with open(raw_messages_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if line_num > 5:  # Only check first 5 messages
                break
                
            try:
                data = json.loads(line)
                raw_data = bytes.fromhex(data['payload_hex'])
                
                print(f"\n=== Message {line_num} ===")
                print(f"Length: {len(raw_data)} bytes")
                print(f"First 32 bytes: {raw_data[:32].hex()}")
                
                # Try different approaches
                print("\n--- Trying HeaderMessage ---")
                try:
                    header_msg = pb2.HeaderMessage()
                    header_msg.ParseFromString(raw_data)
                    print(f"Headers found: {len(header_msg.header)}")
                    if header_msg.header:
                        header = header_msg.header[0]
                        print(f"  cmdFunc: {header.cmd_func}, cmdId: {header.cmd_id}")
                        print(f"  pdata length: {len(header.pdata) if header.pdata else 0}")
                except Exception as e:
                    print(f"  Failed: {e}")
                
                print("\n--- Trying setMessage ---")
                try:
                    set_msg = pb2.setMessage()
                    set_msg.ParseFromString(raw_data)
                    if hasattr(set_msg, 'header') and set_msg.header:
                        print(f"  setHeader found")
                        print(f"  cmdFunc: {set_msg.header.cmd_func}, cmdId: {set_msg.header.cmd_id}")
                    else:
                        print("  No header in setMessage")
                except Exception as e:
                    print(f"  Failed: {e}")
                
                # Try decoding pdata if it's a large message
                if len(raw_data) > 300:
                    print("\n--- Trying to decode large message pdata ---")
                    try:
                        header_msg = pb2.HeaderMessage()
                        header_msg.ParseFromString(raw_data)
                        if header_msg.header and header_msg.header[0].pdata:
                            pdata = header_msg.header[0].pdata
                            
                            # Try RuntimePropertyUpload
                            try:
                                runtime_msg = pb2.RuntimePropertyUpload()
                                runtime_msg.ParseFromString(pdata)
                                print(f"  RuntimePropertyUpload success! Found {len(runtime_msg.ListFields())} fields")
                                for field, value in runtime_msg.ListFields()[:5]:  # Show first 5 fields
                                    print(f"    {field.name}: {value}")
                            except Exception as e:
                                print(f"  RuntimePropertyUpload failed: {e}")
                                
                    except Exception as e:
                        print(f"  Large message analysis failed: {e}")
                    
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")


if __name__ == "__main__":
    analyze_protobuf_data()