"""
Analyze the malformed JSON from the AI
"""
import json

# Read the debug file
with open('debug_ai_response.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract just the JSON part (between the header and footer)
lines = content.split('\n')
json_lines = []
capture = False

for line in lines:
    if line.strip() == '':
        continue
    if line.startswith('='):
        if capture:
            break
        continue
    if 'DEBUG' in line or 'Error' in line:
        continue
    capture = True
    json_lines.append(line)

json_text = '\n'.join(json_lines)

print("JSON TEXT:")
print(repr(json_text[:500]))
print("\n\n")

# Try to parse
try:
    data = json.loads(json_text)
    print("✅ Valid JSON!")
    print(json.dumps(data, indent=2))
except json.JSONDecodeError as e:
    print(f"❌ JSONDecodeError: {e}")
    print(f"\nCharacter at error position:")
    error_pos = e.pos
    print(f"Position {error_pos}: {repr(json_text[max(0, error_pos-50):error_pos+50])}")
    print(f"                           {'~' * 50}^")
