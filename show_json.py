with open('last_ai_response.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract just the JSON
start = content.find('{')
json_part = content[start:]

print("="*70)
print("EXTRACTED JSON:")
print("="*70)
print(json_part)
print("\n" + "="*70)
print("RAW REPR:")
print("="*70)
print(repr(json_part))
