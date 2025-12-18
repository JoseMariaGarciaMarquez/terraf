"""Fix indentation issues in terraf_app.py"""
import re

with open('app/terraf_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Split into lines but keep track of line endings
lines = content.splitlines(keepends=True)

# Track when we're inside a specific context that needs indenting
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if we're at a "with tab1:" or "with tab2:" that needs its content indented
    # These should be at 12 spaces indent (inside the else block)
    if re.match(r'            with tab[12]:\s*$', line):
        # Indent all following lines until we hit another "with tab" or dedent
        i += 1
        while i < len(lines):
            next_line = lines[i]
            # Stop if we hit another tab, or if we dedent back to same or less level
            if re.match(r'            with tab[12]:', next_line):
                break
            if re.match(r'^    # SECCIÓN|^with col_', next_line):
                break
            # If line has content (not just whitespace/newline) and starts with fewer than 16 spaces
            if next_line.strip() and not next_line.startswith('                '):
                # Add 4 spaces
                if next_line.startswith('            '):
                    lines[i] = '    ' + next_line
            i += 1
        continue
    
    i += 1

# Write back
with open('app/terraf_app.py', 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)

print("Fixed indentation")
