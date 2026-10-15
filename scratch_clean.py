import re
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove login redirects
content = re.sub(r"elif current_user\.role == 'citizen':\s*return redirect\(url_for\('citizen_dashboard'\)\)", '', content)
content = re.sub(r"elif user\.role == 'citizen':\s*return redirect\(url_for\('citizen_dashboard'\)\)", '', content)

# Remove CITIZEN routes
content = re.sub(r"# ===+[\r\n\s]+# CITIZEN DASHBOARD.*?# ===+[\r\n\s]+", "", content, flags=re.DOTALL)
content = re.sub(r"@app\.route\('/citizen/dashboard'\).*?def citizen_dashboard\(\):.*?return render_template\([\r\n\s]*'citizen/dashboard\.html'.*?\)[\r\n\s]+", "", content, flags=re.DOTALL)
content = re.sub(r"@app\.route\('/citizen/portal'.*?def citizen_portal\(\):.*?return render_template\([\r\n\s]*'citizen/portal\.html'.*?\)[\r\n\s]+", "", content, flags=re.DOTALL)
content = re.sub(r"@app\.route\('/citizen/grievance'.*?def submit_grievance\(\):.*?return redirect\(url_for\('citizen_portal'.*?\)[\r\n\s]+", "", content, flags=re.DOTALL)

# Remove print statement
content = re.sub(r"print\(\" Citizen: citizen1 / citizen123\"\)", "", content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
