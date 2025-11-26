#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tüm 'ders-notlari' dizinine eklenen dosyaları listeleyen index oluşturucu
ve README içeriğini sayfa başlığı altında gösterir.

Davranış:
 - Önce yerel README (README.md veya README.rst) aranır (çalışma dizininde veya root_path içinde).
 - Yerel README yoksa GitHub API ile repo README'si alınmaya çalışılır.
 - Eğer 'markdown' paketi yüklüyse README Markdown -> HTML dönüştürülür.
 - markdown yoksa README <pre> içinde ham metin olarak gösterilir.
"""
import os
import sys
import requests
import base64
import html
from urllib.parse import quote

# --- Ayarlar ---
user = "iucjeofizik"
repo = "ders-notlari"
branch = "main"
output_file = "index.html"
root_path = "ders-notlari"  # repo içindeki başlangıç dizini; boş string ise repo kökü
base_site = "https://not.iücjeofizik.com/ders-notlari"

# GitHub API
base_url = f"https://api.github.com/repos/{user}/{repo}/contents/{root_path}?ref={branch}"
readme_api_url = f"https://api.github.com/repos/{user}/{repo}/readme?ref={branch}"
token = os.environ.get("GITHUB_TOKEN")
headers = {"Accept": "application/vnd.github.v3+json"}
if token:
    headers["Authorization"] = f"token {token}"

html_header_template = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Ders Notları</title>
</head>
<body>
<h1>Ders Notları</h1>
<div id="readme">
{readme_html}
</div>
<hr/>
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

def try_local_readme():
    """
    Yerel README dosyalarını kontrol et.
    Öncelik: ./README.md, ./README.rst, ./{root_path}/README.md, ./{root_path}/README.rst
    Döndürür: (content:str, format:str) format 'md' veya 'rst' veya 'text' - None dönebilir
    """
    candidates = ["README.md", "README.rst"]
    if root_path:
        candidates += [os.path.join(root_path, "README.md"), os.path.join(root_path, "README.rst")]
    for p in candidates:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    text = f.read()
                if p.lower().endswith(".md"):
                    return text, "md"
                if p.lower().endswith(".rst"):
                    return text, "rst"
            except Exception as e:
                print(f"Yerel README okunamadı: {p} -> {e}", file=sys.stderr)
    return None, None

def try_github_readme_via_api():
    """
    GitHub API /repos/{owner}/{repo}/readme endpoint'inden README'yi al.
    Döndürür (text, format) veya (None, None).
    """
    try:
        resp = requests.get(readme_api_url, headers=headers, timeout=15)
    except requests.RequestException as e:
        print(f"GitHub README isteği başarısız: {e}", file=sys.stderr)
        return None, None
    if resp.status_code != 200:
        # hata, geri dön
        print(f"GitHub README alınamadı: status {resp.status_code} - {resp.text}", file=sys.stderr)
        return None, None
    try:
        data = resp.json()
    except ValueError:
        print("README API'sinden gelen JSON parse edilemedi.", file=sys.stderr)
        return None, None
    content_b64 = data.get("content")
    encoding = data.get("encoding")
    name = data.get("name","README")
    if not content_b64 or encoding != "base64":
        return None, None
    try:
        decoded = base64.b64decode(content_b64).decode("utf-8", errors="replace")
    except Exception as e:
        print("README decode edilemedi:", e, file=sys.stderr)
        return None, None
    if name.lower().endswith(".md"):
        return decoded, "md"
    if name.lower().endswith(".rst"):
        return decoded, "rst"
    return decoded, "text"

def render_readme_to_html(text, fmt):
    """
    Eğer 'markdown' paketi yüklüyse md -> HTML çevir, yoksa <pre> içinde ham göster.
    RST için dönüşüm yapılmıyor (pre içine konur) — isterseniz docutils eklenebilir.
    """
    if not text:
        return "<p>README bulunamadı.</p>"
    if fmt == "md":
        try:
            import markdown
            # temel eklentiler (fenced code, tables) ekleniyor
            html_out = markdown.markdown(text, extensions=['fenced_code', 'tables'])
            return html_out
        except Exception:
            # markdown yoksa ham göster
            safe = html.escape(text)
            return f"<pre>{safe}</pre>"
    else:
        # rst veya text - ham göster
        safe = html.escape(text)
        return f"<pre>{safe}</pre>"

def collect_files(url, collected):
    response = get_json(url)
    if not isinstance(response, list):
        print(f"Beklenen liste dönmedi: {type(response)} - içerik: {response}", file=sys.stderr)
        return
    for item in response:
        if not isinstance(item, dict):
            continue
        itype = item.get('type')
        if itype == 'file':
            collected.append({
                "path": item.get('path'),
                "name": item.get('name'),
            })
        elif itype == 'dir':
            collect_files(item.get('url'), collected)

def make_link_for_item(item_path):
    path = item_path or ""
    if root_path:
        prefix = root_path.rstrip('/') + '/'
        if path.startswith(prefix):
            rel = path[len(prefix):]
        else:
            rel = path
    else:
        rel = path
    encoded = quote(rel, safe="/")
    return f"{base_site}/{encoded}"

def main():
    # README al (önce yerel, sonra API)
    readme_text, readme_fmt = try_local_readme()
    if readme_text is None:
        readme_text, readme_fmt = try_github_readme_via_api()
    readme_html = render_readme_to_html(readme_text, readme_fmt)

    # dosyaları topla
    files = []
    collect_files(base_url, files)
    files.sort(key=lambda x: x['path'] or "")

    # HTML oluştur
    html_parts = [html_header_template.format(readme_html=readme_html)]
    html_parts.append("<h2>Tüm Dosyalar</h2>\n<ul>\n")
    if not files:
        html_parts.append("<li>Henüz dosya bulunmamaktadır.</li>\n")
    else:
        for f in files:
            path = f.get('path', '')
            name = f.get('name', '')
            link = make_link_for_item(path)
            if root_path and path.startswith(root_path.rstrip('/') + '/'):
                display_path = path[len(root_path.rstrip('/') + '/'):]
            else:
                display_path = path
            html_parts.append(f'  <li><a href="{link}" target="_blank">{display_path or name}</a> <small>({name})</small></li>\n')
    html_parts.append("</ul>\n")
    html_parts.append(html_footer)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(''.join(html_parts))

    print(f"Index dosyası oluşturuldu: {output_file} (toplam {len(files)} dosya)")

if __name__ == "__main__":
    main()
