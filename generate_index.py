import requests

# GitHub bilgileri
user = "kullaniciAdi"      # GitHub kullanıcı adınız
repo = "repoAdi"           # Repo adı
branch = "main"            # Branch adı
output_file = "index.html" # Oluşturulacak HTML dosyası

# Ana klasör URL (GitHub API)
base_url = f"https://api.github.com/repos/{user}/{repo}/contents/ders-notlari?ref={branch}"

# Başlangıç HTML
html_content = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Ders Notları</title>
</head>
<body>
<h1>Ders Notları</h1>
"""

# Her klasörü işleyen fonksiyon
def process_folder(url, folder_name):
    global html_content
    response = requests.get(url).json()
    html_content += f"\n<h2>{folder_name}</h2>\n<ul>\n"
    for item in response:
        if item['type'] == 'file' and item['name'].lower().endswith(('.pdf', '.docx', '.pptx')):
            # GitHub Pages linki
            link = f"https://not.iücjeofizik.com/ders-notlari/{folder_name}/{item['name']}"
            html_content += f'  <li><a href="{link}" target="_blank">{item["name"]}</a></li>\n'
    html_content += "</ul>\n"

# Ana klasördeki tüm sınıfları al
response = requests.get(base_url).json()
for item in response:
    if item['type'] == 'dir':
        process_folder(item['url'], item['name'])

# HTML kapanış tagleri
html_content += "\n</body>\n</html>"

# Dosyayı yaz
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Index dosyası oluşturuldu: {output_file}")
