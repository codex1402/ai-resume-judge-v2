with open('last_ai_response.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Write to a new file for viewing
with open('response_repr.txt', 'w', encoding='utf-8') as f:
    f.write("REPR:\n")
    f.write(repr(content))
    f.write("\n\nACTUAL:\n")
    f.write(content)

print("Written to response_repr.txt")

# Also print line by line
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    print(f"Line {i}: {repr(line)}")
