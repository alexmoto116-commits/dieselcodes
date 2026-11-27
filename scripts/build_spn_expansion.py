"""Build the reviewed SPN batch with the existing DieselCodes article shell."""
import argparse
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://dieselcodes.com"
TEMPLATE = ROOT / "kody/spn-627.html"
SITEMAP = ROOT / "sitemap.xml"
DATA = ROOT / "content/spn-expansion-2026-11-27.json"
LD = re.compile(r'<script type="application/ld\+json">.*?</script>', re.S)
ESC = html.escape


def schema(data):
    return ('<script type="application/ld+json">'
            + json.dumps(data,ensure_ascii=False).replace("<","\\u003c") + "</script>")


def section(title, content):
    return f"<section><h2>{ESC(title)}</h2>{content}</section>"


def bullets(items, ordered=False):
    tag = "ol" if ordered else "ul"
    return f"<{tag}>"+"".join(f"<li>{ESC(item)}</li>" for item in items)+f"</{tag}>"


def render(shell, item):
    spn = item["spn"]
    url = f"{DOMAIN}/kody/spn-{spn}.html"
    heading = f"SPN {spn} — {item['topic']}"
    title = heading + " | DieselCodes"
    description = item["description"]
    opening, rest = shell.split("<h1>",1)
    footer = rest[rest.rindex("<footer"):]
    article = {"@context":"https://schema.org","@type":"TechArticle","headline":heading,
               "description":description,"url":url,"mainEntityOfPage":url,"inLanguage":"en",
               "author":{"@type":"Organization","name":"DieselCodes editorial team","url":DOMAIN+"/about.html"},
               "publisher":{"@type":"Organization","name":"DieselCodes"},
               "citation":[link for _,link in item["sources"]]}
    crumbs = {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":i,"name":name,"item":link} for i,(name,link)
        in enumerate((("Home",DOMAIN+"/"),("Codes",DOMAIN+"/kody/"),(f"SPN {spn}",url)),1)]}
    opening = LD.sub("",opening)
    opening = opening.replace("</head>",schema(article)+"\n"+schema(crumbs)+"\n</head>")
    opening = re.sub(r"<title>.*?</title>",lambda _:f"<title>{ESC(title)}</title>",opening,count=1)
    for attr,key,value in (("name","description",description),("property","og:title",title),
                           ("property","og:description",description),("property","og:url",url)):
        opening = re.sub(fr'(<meta {attr}="{re.escape(key)}" content=")[^"]*',
                         lambda m:m[1]+ESC(value,quote=True),opening,count=1)
    opening = re.sub(r'(<link rel="canonical" href=")[^"]*',lambda m:m[1]+url,opening,count=1)
    opening = opening.replace("<span>SPN 627</span>",f"<span>SPN {spn}</span>")
    rows = "".join(f'<tr><td class="fmi">{ESC(fmi)}</td><td>{ESC(platform)}</td><td>{ESC(meaning)}</td></tr>'
                   for fmi,platform,meaning in item["fmis"])
    table = ('<table><thead><tr><th scope="col">FMI</th><th scope="col">Platform or controller</th>'
             '<th scope="col">Meaning</th></tr></thead><tbody>'+rows+"</tbody></table>")
    related = '<ul class="near">'+''.join(
        f'<li><a href="/kody/spn-{num}.html">SPN {num} — {ESC(label)}</a></li>'
        for num,label in item["related"])+"</ul>"
    sources = "<ul>"+''.join(f'<li><a href="{ESC(link,quote=True)}">{ESC(label)}</a></li>'
                             for label,link in item["sources"])+"</ul>"
    return (opening+f"<h1>{ESC(heading)}</h1>\n"
            f'<p class="sub">J1939 parameter: {ESC(item["name"])}</p>\n'
            +section("What the code means",f"<p>{ESC(item['meaning'])}</p>")
            +section("FMI by platform",table)
            +section("Possible symptoms",f"<p>{ESC(item['symptoms'])}</p>")
            +section("Possible causes",bullets(item["causes"]))
            +section("Diagnostic sequence",bullets(item["steps"],ordered=True))
            +section("What to do next",f"<p>{ESC(item['action'])}</p>")
            +section("Related codes",related)+section("Manufacturer references",sources)
            +"\n</div>\n"+footer)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true",help="Verify generated output without writing")
    args = parser.parse_args()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    ids = {item["spn"] for item in data}
    if len(data) != 10 or len(ids) != 10:
        raise SystemExit("Expected ten different SPNs")
    shell = TEMPLATE.read_text(encoding="utf-8")
    generated = {}
    for item in data:
        for num,_ in item["related"]:
            if num not in ids and not (ROOT/f"kody/spn-{num}.html").is_file():
                raise SystemExit(f"Missing related SPN {num}")
        path = ROOT/f"kody/spn-{item['spn']}.html"
        generated[path] = render(shell,item)
    raw = SITEMAP.read_bytes()
    lines = b"\r\n" if b"\r\n" in raw else b"\n"
    entries = []
    for num in sorted(ids):
        canonical = f"{DOMAIN}/kody/spn-{num}.html".encode()
        if raw.count(b"<loc>"+canonical+b"</loc>") > 1:
            raise SystemExit(f"Duplicate sitemap URL for SPN {num}")
        if b"<loc>"+canonical+b"</loc>" not in raw:
            entries.append(b"<url><loc>"+canonical+b"</loc></url>")
    expected_map = raw.replace(b"</urlset>",lines.join(entries)+lines+b"</urlset>",1) if entries else raw
    if b"</urlset>" not in raw:
        raise SystemExit("Unexpected sitemap structure")
    if args.check:
        for path, body in generated.items():
            if not path.exists() or path.read_text(encoding="utf-8") != body:
                raise SystemExit(f"Generated page differs: {path.name}")
        if raw != expected_map:
            raise SystemExit("Sitemap is missing batch URLs")
    else:
        for path, body in generated.items():
            if path.exists() and path.read_text(encoding="utf-8") != body:
                raise SystemExit(f"Refusing to replace an existing page: {path.name}")
        for path, body in generated.items():
            if not path.exists():
                path.write_text(body,encoding="utf-8",newline="\n")
        if raw != expected_map:
            SITEMAP.write_bytes(expected_map)
    print(f"Checked {len(generated)} SPN pages and sitemap entries")


if __name__=="__main__":
    main()
