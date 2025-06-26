#!/usr/bin/env python3
"""
Test script to validate the fixed data processor using saved test data
"""

import sys
import json
from pathlib import Path

# Add protobuf path
sys.path.append(str(Path.cwd().parent.parent))

import logging

from prepare_data_processor import DeltaPro3PrepareDataProcessor

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s - %(message)s")

def test_fixed_processor():
    """Test the fixed processor with saved raw messages"""
    
    raw_messages_file = Path("test_results/raw_messages.jsonl")
    if not raw_messages_file.exists():
        print("No raw messages file found")
        return
    
    processor = DeltaPro3PrepareDataProcessor()
    
    with open(raw_messages_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if line_num > 10:  # Test first 10 messages
                break
                
            try:
                data = json.loads(line)
                raw_data = bytes.fromhex(data['payload_hex'])
                
                print(f"\n=== Testing Message {line_num} ===")
                print(f"Length: {len(raw_data)} bytes")
                
                # Test the processor
                result = processor.prepare_data(raw_data)
                
                if result:
                    print(f"✅ SUCCESS: {len(result)} fields extracted")
                    for key, value in list(result.items())[:5]:  # Show first 5 fields
                        print(f"  {key}: {value}")
                    if len(result) > 5:
                        print(f"  ... and {len(result) - 5} more fields")
                else:
                    print("❌ FAILED: No data extracted")
                    
            except Exception as e:
                print(f"❌ ERROR processing line {line_num}: {e}")


if __name__ == "__main__":
    test_fixed_processor()