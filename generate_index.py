#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ders notları index oluşturucu (düzgün hata kontrolü ile)

Kısa açıklama:
- GitHub API hatalarını yakalar ve anlamlı mesaj verir
- Private repolar için GITHUB_TOKEN destekler
- Dizin/ dosya isimlerini URL-encode eder
- .pdf, .docx, .pptx dosyalarını indexler
"""

import os
import sys
import requests
from urllib.parse import quote

# --- Ayarlar (gerektiğinde değiştirin) ---
user = "iucjeofizik"      # GitHub kullanıcı adı veya org
repo = "ders-notlari"     # Repo adı
branch = "main"           # Branch adı
output_file = "index.html" # Oluşturulacak HTML dosyası
root_path = "ders-notlari" # GitHub repo içindeki dizin (ör. "ders-notlari"); boş string ise repo kökü

# --- GitHub API URL ---
base_url = f"https://api.github.com/repos/{user}/{repo}/contents/{root_path}?ref={branch}"

# --- Headers (opsiyonel token ile) ---
token = os.environ.get("GITHUB_TOKEN")
headers = {"Accept": "application/vnd.github.v3+json"}
if token:
    headers["Authorization"] = f"token {token}"

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

def get_json(url):
    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as e:
        print(f"HTTP isteği başarısız: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        data = resp.json()
    except ValueError:
        print("Sunucudan JSON parse edilemedi. Raw içerik:", resp.text, file=sys.stderr)
        sys.exit(1)
    if resp.status_code >= 400:
        message = data.get("message") if isinstance(data, dict) else None
        print(f"GitHub API hata {resp.status_code}: {message or resp.text}", file=sys.stderr)
        sys.exit(1)
    return data

def process_folder(url, folder_name):
    global html_content
    response = get_json(url)
    if not isinstance(response, list):
        print(f"Beklenen liste dönmedi for folder {folder_name}. JSON tip: {type(response)}", file=sys.stderr)
        print("JSON içerik (özet):", response, file=sys.stderr)
        return
    html_content += f"\n<h2>{folder_name}</h2>\n<ul>\n"
    for item in response:
        if not isinstance(item, dict):
            continue
        if item.get('type') == 'file' and item.get('name','').lower().endswith(('.pdf', '.docx', '.pptx')):
            encoded_folder = quote(folder_name)
            encoded_name = quote(item['name'])
            link = f"https://not.iücjeofizik.com/ders-notlari/{encoded_folder}/{encoded_name}"
            html_content += f'  <li><a href="{link}" target="_blank">{item["name"]}</a></li>\n'
    html_content += "</ul>\n"

def main():
    print("Base URL:", base_url)
    response = get_json(base_url)
    if isinstance(response, dict):
        print("GitHub API beklenmeyen bir JSON döndürdü (muhtemelen hata):", file=sys.stderr)
        print(response, file=sys.stderr)
        sys.exit(1)
    if not isinstance(response, list):
        print(f"Beklenmeyen JSON tipi: {type(response)}", file=sys.stderr)
        print(response, file=sys.stderr)
        sys.exit(1)

    for item in response:
        if not isinstance(item, dict):
            continue
        if item.get('type') == 'dir':
            process_folder(item.get('url'), item.get('name'))

    global html_content
    html_content += "\n</body>\n</html>"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Index dosyası oluşturuldu: {output_file}")

if __name__ == "__main__":
    main()
