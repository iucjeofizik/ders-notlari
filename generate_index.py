#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ders notları dizini için index oluşturucu.
- Ağaç yapısında (klasör) çıktı üretir.
- Klasörler daraltılıp/genişletilebilir (JS ile).
- Dosya bağlantıları sadece dosya adı üzerine embed edilmiş şekilde gösterilir (tam path gösterilmez).
"""
import os
import sys
import requests
import base64
import html
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
<style>
  body { font-family: sans-serif; line-height: 1.5; padding: 1rem; }
  .tree { margin: 0; padding: 0; }
  .tree ul { list-style: none; margin: 0; padding-left: 1.25rem; }
  .caret { cursor: pointer; user-select: none; display: inline-block; }
  .caret .symbol { display: inline-block; width: 1.0rem; }
  .nested { display: none; }
  .nested.active { display: block; }
  .file a { text-decoration: none; color: #0366d6; }
  .file a:hover { text-decoration: underline; }
  .empty { font-style: italic; color: #888; margin-left: 1.25rem; }
</style>
</head>
<body>
<h1>Ders Notları</h1>
<p>Bu sayfada <strong>ders-notlari</strong> dizinine eklenen tüm dosyalar ağaç yapısında listelenir. Klasör isimlerine tıklayarak daraltıp/ genişletebilirsiniz.</p>
<div id="readme">
{readme_html}
</div>
<hr/>
<script>
document.addEventListener("DOMContentLoaded", function() {{
  var carets = document.getElementsByClassName("caret");
  Array.prototype.forEach.call(carets, function(c) {{
    c.addEventListener("click", function(e) {{
      var nested = this.parentElement.querySelector(".nested");
      if (!nested) return;
      nested.classList.toggle("active");
      var sym = this.querySelector(".symbol");
      if (sym) {{
        sym.textContent = nested.classList.contains("active") ? "▼" : "▶";
      }}
    }});
  }});
}});
</script>
"""

html_footer = """
</body>
</html>
"""

def get_json(url):
    """GET request and return parsed JSON or exit on error."""
    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as e:
        print(f"HTTP isteği başarısız: {e}", file=sys.stderr)
        sys.exit(1)
    if resp.status_code != 200:
        print(f"Beklenmeyen status kodu {resp.status_code} for {url}: {resp.text}", file=sys.stderr)
        return None
    try:
        return resp.json()
    except ValueError:
        print("JSON parse edilemedi.", file=sys.stderr)
        return None

def try_local_readme():
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
    try:
        resp = requests.get(readme_api_url, headers=headers, timeout=15)
    except requests.RequestException as e:
        print(f"GitHub README isteği başarısız: {e}", file=sys.stderr)
        return None, None
    if resp.status_code != 200:
        print(f"GitHub README alınamadı: status {resp.status_code} - {resp.text}", file=sys.stderr)
        return None, None
    try:
        data = resp.json()
    except ValueError:
        print("README API'sinden gelen JSON parse edilemedi.", file=sys.stderr)
        return None, None
    content_b64 = data.get("content")
    encoding = data.get("encoding")
    name = data.get("name", "README")
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
    if not text:
        return "<p>README bulunamadı.</p>"
    if fmt == "md":
        try:
            import markdown
            html_out = markdown.markdown(text, extensions=['fenced_code', 'tables'])
            return html_out
        except Exception:
            safe = html.escape(text)
            return f"<pre>{safe}</pre>"
    else:
        safe = html.escape(text)
        return f"<pre>{safe}</pre>"

def collect_tree(url):
    """
    Build a tree from GitHub contents API for the given directory.
    Nodes:
     - dir: {'type':'dir','name':..., 'path':..., 'children':[...]}
     - file: {'type':'file','name':..., 'path':...}
    """
    response = get_json(url)
    if not isinstance(response, list):
        return []
    nodes = []
    for item in response:
        if not isinstance(item, dict):
            continue
        itype = item.get('type')
        if itype == 'dir':
            children = collect_tree(item.get('url'))
            nodes.append({
                "type": "dir",
                "name": item.get('name'),
                "path": item.get('path'),
                "children": children
            })
        elif itype == 'file':
            nodes.append({
                "type": "file",
                "name": item.get('name'),
                "path": item.get('path'),
            })
    nodes.sort(key=lambda n: (0 if n.get('type') == 'dir' else 1, (n.get('name') or "").lower()))
    return nodes

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

def render_nodes(nodes):
    """
    Recursively render nodes as <ul>/<li>. Fark: dosyalar sadece dosya adı ile gösterilir
    ve dosya adı link'e gömülüdür. Klasörler daraltılabilir/gevşetilebilir.
    """
    out = ["<ul class=\"tree\">\n"]
    for n in nodes:
        if n.get('type') == 'dir':
            children = n.get('children') or []
            out.append('<li>\n')
            # caret with symbol
            out.append(f'  <span class="caret"><span class="symbol">▶</span> {html.escape(n.get("name") or "")}</span>\n')
            if children:
                out.append('<div class="nested">\n')
                out.append(render_nodes(children))
                out.append('</div>\n')
            else:
                out.append('<div class="nested"><div class="empty">(boş)</div></div>\n')
            out.append('</li>\n')
        else:
            path = n.get('path', '')
            name = n.get('name', '')
            link = make_link_for_item(path)
            # Only show the file name as the link text (no full path)
            out.append(f'  <li class="file"><a href="{link}" target="_blank">{html.escape(name)}</a></li>\n')
    out.append("</ul>\n")
    return ''.join(out)

def main():
    print("Base API URL:", base_url)
    readme_text, readme_fmt = try_local_readme()
    if readme_text is None:
        readme_text, readme_fmt = try_github_readme_via_api()
    readme_html = render_readme_to_html(readme_text, readme_fmt)

    tree = collect_tree(base_url)

    parts = [html_header_template.format(readme_html=readme_html)]
    parts.append("<h2>Ders Notları - Ağaç Görünümü</h2>\n")
    if not tree:
        parts.append("<p>Henüz dosya bulunmamaktadır.</p>\n")
    else:
        parts.append(render_nodes(tree))
    parts.append(html_footer)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(''.join(parts))

    def count_files(nodes):
        c = 0
        for n in nodes:
            if n.get('type') == 'file':
                c += 1
            else:
                c += count_files(n.get('children') or [])
        return c

    total_files = count_files(tree)
    print(f"Index dosyası oluşturuldu: {output_file} (toplam {total_files} dosya)")

if __name__ == "__main__":
    main()
