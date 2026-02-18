import json

with open('debug_ai_response.txt', 'r', encoding='utf-8') as f:
    raw = f.read()

# Find where JSON starts
start = raw.find('{')
end = raw.rfind('}') + 1

if start != -1 and end != 0:
    json_text = raw[start:end]
    
    with open('extracted_json.txt', 'w', encoding='utf-8') as f:
        f.write(json_text)
    
    try:
        data = json.loads(json_text)
        with open('result.txt', 'w', encoding='utf-8') as f:
            f.write("SUCCESS\n")
            f.write(json.dumps(data, indent=2))
    except json.JSONDecodeError as e:
        with open('result.txt', 'w', encoding='utf-8') as f:
            f.write(f"ERROR: {e}\n")
            f.write(f"Position: {e.pos}\n")
            if e.pos < len(json_text):
                f.write(f"Character: {repr(json_text[e.pos])}\n")
                f.write(f"Context: {repr(json_text[max(0, e.pos-100):e.pos+100])}\n")

print("Done - check extracted_json.txt and result.txt")
