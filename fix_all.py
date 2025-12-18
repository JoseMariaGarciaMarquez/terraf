"""Fix all tab content indentation"""

with open('app/terraf_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Ranges to indent (0-indexed)
# After "with tab1:" at line 380, indent 381-459
for i in range(380, 459):
    if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('with tab'):
        lines[i] = '    ' + lines[i]

# After "with tab2:" at line 460, indent 461-516  
for i in range(460, 516):
    if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('with tab'):
        lines[i] = '    ' + lines[i]

# After "with tab1:" at line 586, indent 587-661
for i in range(586, 661):
    if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('with tab'):
        lines[i] = '    ' + lines[i]

# After "with tab2:" at line 662, indent 663-763
for i in range(662, 763):
    if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('with tab'):
        lines[i] = '    ' + lines[i]

# After "with st.spinner" at line 1357, indent 1358-1406
for i in range(1357, 1406):
    if i < len(lines) and lines[i].strip():
        if not any(lines[i].strip().startswith(kw) for kw in ['except ', 'else:', 'elif ']):
            lines[i] = '    ' + lines[i]

with open('app/terraf_app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("All indentation fixed")
