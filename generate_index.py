#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tüm "ders-notlari" dizinine eklenen dosyaları gösteren index oluşturucu.
- Tüm dosya türleri gösterilir.
- Alt klasörler recursive olarak taranır.
- Çıktıda her dosya için repository içindeki relatif yol gösterilir ve
  GitHub Pages altında erişim linki üretilir.

Ayarlamalar:
 - user, repo, branch, root_path ve base_site değerlerini gerektiğinde düzenleyin.
 - Eğer private repo ise GITHUB_TOKEN environment variable olarak ekleyin.
"""
import os
import sys
import requests
from urllib.parse import quote

# --- Ayarlar (gerektiğinde değiştirin) ---
user = "iucjeofizik"
repo = "ders-notlari"
branch = "main"
output_file = "index.html"
root_path = "ders-notlari"  # repo içindeki başlangıç dizini; boş string ise repo kökü

# Site üstündeki base path; dosya linkleri buraya göre oluşturulacak
base_site = "https://not.iücjeofizik.com/ders-notlari"

# --- GitHub API URL ve headers ---
base_url = f"https://api.github.com/repos/{user}/{repo}/contents/{root_path}?ref={branch}"
token = os.environ.get("GITHUB_TOKEN")
headers = {"Accept": "application/vnd.github.v3+json"}
if token:
    headers["Authorization"] = f"token {token}"

html_header = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Ders Notları</title>
</head>
<body>
<h1>Ders Notları</h1>
<p>Bu sayfada <strong>ders-notlari</strong> dizinine eklenen tüm dosyalar listelenir.</p>
"""

html_footer = """
</body>
</html>
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

def collect_files(url, collected):
    """
    response of GitHub contents API for a directory is a list of items.
    This function appends tuples (repo_path, name) into collected for files,
    and recurses into directories.
    """
    response = get_json(url)
    if not isinstance(response, list):
        print(f"Beklenen liste dönmedi: {type(response)} - içerik: {response}", file=sys.stderr)
        return
    for item in response:
        if not isinstance(item, dict):
            continue
        itype = item.get('type')
        if itype == 'file':
            # item['path'] is the repo-relative path (e.g. "ders-notlari/Hafta1/dosya.pdf")
            collected.append({
                "path": item.get('path'),
                "name": item.get('name'),
            })
        elif itype == 'dir':
            # recurse
            collect_files(item.get('url'), collected)
        # symlink/submodule ignored

def make_link_for_item(item_path):
    """
    Given repo path like "ders-notlari/Hafta1/dosya.pdf", produce the public link:
    base_site + "/" + part_after_root (URL-encoded, preserving slashes).
    If root_path is empty, use whole path after repo root.
    """
    path = item_path or ""
    if root_path:
        prefix = root_path.rstrip('/') + '/'
        if path.startswith(prefix):
            rel = path[len(prefix):]
        else:
            # fallback: if unexpected, use basename
            rel = path
    else:
        rel = path
    # encode but keep slashes
    encoded = quote(rel, safe="/")
    return f"{base_site}/{encoded}"

def main():
    print("Base API URL:", base_url)
    files = []
    collect_files(base_url, files)

    # Sort by path for predictable ordering
    files.sort(key=lambda x: x['path'] or "")

    # Build HTML: single Ders Notları list with relative paths
    html = [html_header]
    html.append("<ul>\n")
    if not files:
        html.append("<li>Henüz dosya bulunmamaktadır.</li>\n")
    else:
        for f in files:
            path = f.get('path', '')
            name = f.get('name', '')
            link = make_link_for_item(path)
            # show relative path (after root_path/) or full path if root_path empty
            if root_path and path.startswith(root_path.rstrip('/') + '/'):
                display_path = path[len(root_path.rstrip('/') + '/'):]
            else:
                display_path = path
            html.append(f'  <li><a href="{link}" target="_blank">{display_path or name}</a> <small>({name})</small></li>\n')
    html.append("</ul>\n")
    html.append(html_footer)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(''.join(html))

    print(f"Index dosyası oluşturuldu: {output_file} (toplam {len(files)} dosya)")

if __name__ == "__main__":
    main()
