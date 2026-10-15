with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.strip().startswith('grv_code = f"GRV-'):
        skip = True
    
    if skip:
        if line.strip() == "return redirect(url_for('citizen_portal', card_number=rc_no))":
            skip = False
        continue
    
    new_lines.append(line)

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
