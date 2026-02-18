import json
import os

debug_file = 'debug_ai_response.txt'

print(f"Looking for: {debug_file}")
print(f"File exists: {os.path.exists(debug_file)}")

if not os.path.exists(debug_file):
    print("File not found!")
    exit(1)

try:
    with open(debug_file, 'r', encoding='utf-8') as f:
        raw = f.read()
    
    print(f"File size: {len(raw)} characters")
    
    # Find where JSON starts and ends
    start = raw.find('{')
    end = raw.rfind('}')
    
    if start == -1 or end == -1:
        print("No JSON found in file")
        with open('error_details.txt', 'w', encoding='utf-8') as f:
            f.write("No JSON braces found\n")
            f.write(f"File content:\n{raw}")
        exit(1)
    
    json_text = raw[start:end+1]
    
    print(f"JSON extracted, length: {len(json_text)}")
    
    # Save extracted JSON
    with open('extracted_json.txt', 'w', encoding='utf-8') as f:
        f.write(json_text)
    
    # Try to parse
    try:
        data = json.loads(json_text)
        with open('parse_result.txt', 'w', encoding='utf-8') as f:
            f.write("SUCCESS - JSON is valid!\n\n")
            f.write(json.dumps(data, indent=2))
        print("SUCCESS - JSON parsed!")
    except json.JSONDecodeError as e:
        with open('parse_result.txt', 'w', encoding='utf-8') as f:
            f.write(f"PARSE ERROR\n")
            f.write(f"Error: {e}\n")
            f.write(f"Line: {e.lineno}, Column: {e.colno}, Position: {e.pos}\n\n")
            
            if e.pos < len(json_text):
                start_ctx = max(0, e.pos - 100)
                end_ctx = min(len(json_text), e.pos + 100)
                f.write(f"Context around error:\n")
                f.write(f"{json_text[start_ctx:e.pos]}")
                f.write("<<<ERROR HERE>>>")
                f.write(f"{json_text[e.pos:end_ctx]}\n\n")
                
            # Show first few lines
            f.write(f"\nFirst 500 characters of JSON:\n")
            f.write(json_text[:500])
        
        print(f"PARSE ERROR - check parse_result.txt")

except Exception as e:
    print(f"Error: {e}")
    with open('error_details.txt', 'w', encoding='utf-8') as f:
        f.write(f"Exception: {e}\n")
        import traceback
        f.write(traceback.format_exc())
