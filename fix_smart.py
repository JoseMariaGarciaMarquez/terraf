"""Simple indentation fix - add 4 spaces to lines that need it, excluding with/except/else"""

with open('app/terraf_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line ranges that need +4 spaces (Python 0-indexed, so line N in editor = index N-1)
ranges_to_indent = [
    (380, 458),  # Landsat tab1 content (line 381-459 in editor)
    (459, 516),  # Landsat tab2 content (line 460-517 in editor)
    (586, 661),  # Magnetometry tab1 content (line 587-662 in editor)  
    (662, 763),  # Magnetometry tab2 content (line 663-764 in editor)
    (1357, 1402), # Download spinner content (line 1358-1403 in editor)
]

for start, end in ranges_to_indent:
    for i in range(start, min(end, len(lines))):
        line = lines[i]
        # Only indent non-empty lines that don't start with 'with', 'except', 'else', 'elif'
        stripped = line.strip()
        if stripped and not any(stripped.startswith(kw) for kw in ['with ', 'except ', 'else:', 'elif ']):
            # Add 4 spaces at the beginning
            lines[i] = '    ' + line

with open('app/terraf_app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation")
