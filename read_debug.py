"""
Read and display debug file content
"""
import json

try:
    with open('debug_ai_response.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("="*70)
    print("RAW AI RESPONSE:")
    print("="*70)
    print(content)
    print("\n" + "="*70)
    print("ANALYSIS:")
    print("="*70)
    
    # Try to find the JSON part
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('{'):
            json_start = i
            print(f"JSON starts at line {i+1}")
            break
    
    # Show the problematic area
    print("\nShowing lines around the error:")
    for i in range(max(0, json_start), min(len(lines), json_start + 10)):
        print(f"Line {i+1}: {repr(lines[i])}")
        
except Exception as e:
    print(f"Error: {e}")
