#!/usr/bin/env python3
"""Build the R. Napitalai Limited website.

Reads the editable content in content/ (written by staff through /admin),
renders every page, and writes a static site to _site/.

No third-party packages are needed: Python 3.8+ only.

Usage:
  python3 build.py                     # production build (indexable)
  python3 build.py --staging           # adds a staging banner and blocks search engines
  python3 build.py --relative          # links work when opened from a folder or a preview host
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="_site")
ap.add_argument("--staging", action="store_true")
ap.add_argument("--relative", action="store_true")
ARGS = ap.parse_args()
OUT = ROOT / ARGS.out

esc = lambda s: html.escape(str(s or ""), quote=True)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_folder(name, key="order"):
    items = [load(p) for p in sorted((CONTENT / name).glob("*.json"))]
    return sorted(items, key=lambda x: (x.get(key) is None, x.get(key, 0)))


SET = load(CONTENT / "settings.json")
HOME = load(CONTENT / "home.json")
ABOUT = load(CONTENT / "about.json")
SERVICES = load_folder("services")
PROJECTS = load_folder("projects")
TEAM = load_folder("team")
NEWS = sorted(load_folder("news", key="date"), key=lambda n: str(n.get("date", "")), reverse=True)
SITE_URL = SET["site_url"].rstrip("/")


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


# ---------- URL helpers -------------------------------------------------
class Page:
    """Tracks where the page being rendered lives, for relative links."""
    path = "/"


def depth_prefix():
    parts = [p for p in Page.path.strip("/").split("/") if p and not p.endswith(".html")]
    return "../" * len(parts) if parts else "./"


def link(target):
    """Site link. target is an absolute site path like /about/ or /about/#x."""
    if not target or re.match(r"^(https?:|mailto:|tel:|#)", target):
        return target
    if not ARGS.relative:
        return target
    path, _, frag = target.partition("#")
    rel = depth_prefix() + path.lstrip("/")
    if rel.endswith("/") or path == "/":
        rel += "index.html"
    return rel + ("#" + frag if frag else "")


def asset(src):
    if not src or re.match(r"^(https?:|data:)", src):
        return src
    return depth_prefix() + src.lstrip("/") if ARGS.relative else src


def absolute(src):
    return src if re.match(r"^https?:", src or "") else SITE_URL + "/" + (src or "").lstrip("/")


def img_tag(src, alt="", cls="", sizes="100vw", lazy=True, extra=""):
    """Responsive <img>. Uses the -800 twin of a -1600 image when one exists."""
    if not src:
        return ""
    srcset = ""
    m = re.match(r"^(.*)-1600(\.\w+)$", src)
    if m and (STATIC / (m.group(1) + "-800" + m.group(2)).lstrip("/")).exists():
        small = m.group(1) + "-800" + m.group(2)
        srcset = f' srcset="{asset(small)} 800w, {asset(src)} 1600w" sizes="{sizes}"'
        src_attr = asset(small) if lazy else asset(src)
    else:
        src_attr = asset(src)
    return (f'<img{" class=" + chr(34) + cls + chr(34) if cls else ""} src="{src_attr}"{srcset}'
            f' alt="{esc(alt)}"{" loading=" + chr(34) + "lazy" + chr(34) if lazy else ""}{extra}>')


# ---------- Minimal Markdown -------------------------------------------
def inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
               lambda m: f'<a href="{esc(link(html.unescape(m.group(2))))}">{m.group(1)}</a>', s)
    return s


def md(text):
    """Headings (##, ###), paragraphs, bullet and numbered lists, bold, italic, links, images."""
    out, para, items, kind = [], [], [], None

    def flush():
        nonlocal para, items, kind
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
        if items:
            out.append(f"<{kind}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{kind}>")
            items, kind = [], None

    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        img = re.match(r"^!\[([^\]]*)\]\(([^)\s]+)\)$", line)
        if not line:
            flush()
        elif img:
            flush()
            out.append(img_tag(img.group(2), img.group(1), "post-img", "(max-width: 760px) 100vw, 720px"))
        elif re.match(r"^#{2,4}\s", line):
            flush()
            lvl = min(len(line) - len(line.lstrip("#")), 4)
            out.append(f"<h{lvl}>{inline(line[lvl:].strip())}</h{lvl}>")
        elif re.match(r"^[-*]\s+", line):
            if para or kind == "ol":
                flush()
            kind = "ul"
            items.append(re.sub(r"^[-*]\s+", "", line))
        elif re.match(r"^\d+[.)]\s+", line):
            if para or kind == "ul":
                flush()
            kind = "ol"
            items.append(re.sub(r"^\d+[.)]\s+", "", line))
        else:
            if items:
                flush()
            para.append(line)
    flush()
    return "\n".join(out)


def paras(text):
    return "".join(f"<p>{inline(p.strip())}</p>" for p in (text or "").split("\n\n") if p.strip())


def fmt_date(d):
    try:
        x = dt.date.fromisoformat(str(d)[:10])
        return f"{x.day} {x.strftime('%B %Y')}"
    except ValueError:
        return str(d)


# ---------- Layout -------------------------------------------------------
NAV = [("About", "/about/"), ("Services", "/services/"), ("Projects", "/projects/"),
       ("Team", "/team/"), ("News", "/news/"), ("Contact", "/contact/")]


def tel(n):
    return "tel:" + re.sub(r"[^\d+]", "", n or "")


def org_jsonld():
    data = {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "name": SET["site_name"],
        "alternateName": SET["brand_name"],
        "description": SET["description"],
        "url": SITE_URL,
        "logo": absolute("/assets/img/apple-touch-icon.png"),
        "image": absolute(SET.get("social_image")),
        "telephone": SET["phone"],
        "email": SET["email"],
        "address": {"@type": "PostalAddress", "streetAddress": SET["street_address"],
                    "addressLocality": SET["city"], "addressRegion": SET["region"], "addressCountry": "PG"},
        "areaServed": "Papua New Guinea",
        "knowsAbout": [s["title"] for s in SERVICES],
        "sameAs": [u for u in (SET.get("facebook"), SET.get("linkedin")) if u],
    }
    return json.dumps(data, indent=2, ensure_ascii=False).replace("</", "<\\/")


def head(title, description, path, image=None, noindex=False, og_type="website"):
    full_title = f"{title} | {SET['site_name']}" if title else f"{SET['site_name']} | {SET['brand_name']}"
    canonical = SITE_URL + path
    a = SET.get("analytics", {})
    robots = "noindex, nofollow" if (ARGS.staging or noindex) else "index, follow"
    ga = a.get("ga4_measurement_id", "").strip()
    gsc = a.get("search_console_verification", "").strip()
    ga_tag = (f'\n  <script async src="https://www.googletagmanager.com/gtag/js?id={esc(ga)}"></script>'
              f"\n  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
              f"gtag('js',new Date());gtag('config','{esc(ga)}');</script>") if ga and not ARGS.staging else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(full_title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta name="robots" content="{robots}">
  <meta name="theme-color" content="#014C73">{chr(10) + '  <meta name="google-site-verification" content="' + esc(gsc) + '">' if gsc else ''}
  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="{esc(SET['site_name'])}">
  <meta property="og:title" content="{esc(title or SET['site_name'])}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(absolute(image or SET.get('social_image')))}">
  <meta property="og:locale" content="en_PG">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="{asset('/favicon.svg')}" type="image/svg+xml">
  <link rel="icon" href="{asset('/assets/img/favicon.png')}" type="image/png" sizes="64x64">
  <link rel="apple-touch-icon" href="{asset('/assets/img/apple-touch-icon.png')}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{asset('/assets/css/site.css')}">
  <script type="application/ld+json">{org_jsonld()}</script>{ga_tag}
</head>"""


def brand(light=False):
    mark = "/assets/img/mark-light.svg" if light else "/assets/img/mark.svg"
    return (f'<a class="brand{" brand-light" if light else ""}" href="{link("/")}" aria-label="{esc(SET["site_name"])} home">'
            f'<img class="brand-mark" src="{asset(mark)}" alt="" width="62" height="30">'
            f'<span class="brand-text"><strong>{esc(SET["brand_name"])}</strong><span>{esc(SET["slogan"])}</span></span></a>')


def header(active):
    items = "".join(
        f'<li><a href="{link(u)}"{" aria-current=" + chr(34) + "page" + chr(34) if active == u else ""}>{t}</a></li>'
        for t, u in NAV)
    bar = ('<div class="preview-bar" role="note"><strong>Staging site</strong> for review by R. Napitalai Limited. '
           'Not yet live; enquiries are not sent.</div>') if ARGS.staging else ""
    return f"""<a class="skip" href="#main">Skip to content</a>
  {bar}
  <header class="site-header">
  <div class="wrap header-inner">
    {brand()}
    <button class="nav-toggle" aria-expanded="false" aria-controls="site-nav"><span class="nav-toggle-bar"></span><span class="sr">Menu</span></button>
    <nav id="site-nav" class="site-nav" aria-label="Main">
      <ul>{items}</ul>
      <a class="btn btn-accent nav-cta" href="{link('/contact/')}">Request a quote</a>
    </nav>
  </div>
</header>"""


def footer():
    company = "".join(f'<li><a href="{link(u)}">{t}</a></li>' for t, u in
                      [("About", "/about/"), ("Our team", "/team/"), ("Projects", "/projects/"), ("News", "/news/")])
    services = "".join(f'<li><a href="{link("/services/#" + s["slug"])}">{esc(s["title"])}</a></li>' for s in SERVICES)
    social = " · ".join(f'<a href="{esc(u)}" rel="noopener">{n}</a>' for n, u in
                        [("Facebook", SET.get("facebook")), ("LinkedIn", SET.get("linkedin"))] if u)
    offices = ", ".join(b["name"] for b in SET["branches"])
    offices = re.sub(r", ([^,]+)$", r" and \1", offices)
    return f"""<footer class="site-footer">
  <div class="wrap footer-grid">
    <div class="footer-about">
      {brand(light=True)}
      <p>{esc(SET['footer_blurb'])}</p>
    </div>
    <div><h2 class="footer-h">Company</h2><ul>{company}</ul></div>
    <div><h2 class="footer-h">Services</h2><ul>{services}</ul></div>
    <div>
      <h2 class="footer-h">Head office</h2>
      <address>{esc(SET['street_address'])}<br>{esc(SET['city'])}<br>{esc(SET['postal_address'])}</address>
      <p><a href="{tel(SET['phone'])}">{esc(SET['phone'])}</a><br><a href="mailto:{esc(SET['email'])}">{esc(SET['email'])}</a></p>
      {f'<p class="footer-social">{social}</p>' if social else ''}
    </div>
  </div>
  <div class="wrap footer-base"><span>© {dt.date.today().year} {esc(SET['site_name'])}. All rights reserved.</span><span>Offices in {esc(offices)}</span></div>
</footer>
  <script src="{asset('/assets/js/site.js')}" defer></script>"""


def cta():
    return f"""<section class="cta"><div class="wrap cta-inner">
  <div><h2>{esc(SET['cta_title'])}</h2><p>{esc(SET['cta_text'])}</p></div>
  <div class="cta-actions"><a class="btn btn-accent" href="{link('/contact/')}">Send an enquiry</a><a class="btn btn-ghost" href="{tel(SET['phone'])}">Call {esc(SET['phone'])}</a></div>
</div></section>"""


def page_head(eyebrow, title, lead="", narrow=False):
    return (f'<section class="page-head"><div class="wrap{" narrow" if narrow else ""}">'
            f'{f"<p class=" + chr(34) + "eyebrow eyebrow-light" + chr(34) + ">" + eyebrow + "</p>" if eyebrow else ""}'
            f"<h1>{esc(title)}</h1>{f'<p class=' + chr(34) + 'lead' + chr(34) + '>' + esc(lead) + '</p>' if lead else ''}</div></section>")


PAGES = []  # (path, lastmod) for the sitemap


def write(path, title, description, body, active=None, image=None, noindex=False, og_type="website", lastmod=None):
    Page.path = path
    doc = (head(title, description, path, image, noindex, og_type) + "\n<body>\n  " + header(active)
           + '\n  <main id="main">\n' + body() + "\n  </main>\n  " + footer() + "\n</body>\n</html>\n")
    target = OUT / (path.strip("/") + "/index.html" if path.strip("/") else "index.html")
    if path.endswith(".html"):
        target = OUT / path.strip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, encoding="utf-8")
    if not noindex:
        PAGES.append((path, lastmod))


# ---------- Components ---------------------------------------------------
def project_card(p):
    sector_slug = slugify(p.get("sector"))
    top = (img_tag(p["cover_image"], p.get("cover_alt", ""), "card-img", "(max-width: 760px) 100vw, 33vw")
           if p.get("cover_image") else
           f'<div class="card-band" aria-hidden="true"><span>{esc(p.get("sector"))}</span></div>')
    eyebrow = f'<p class="eyebrow">{esc(p.get("sector"))}</p>' if p.get("cover_image") else ""
    return f"""<article class="card project-card" data-sector="{sector_slug}">
  <a class="card-link" href="{link('/projects/' + p['slug'] + '/')}">
    {top}
    <div class="card-body">
      {eyebrow}
      <h3>{esc(p['title'])}</h3>
      <p>{esc(p['summary'])}</p>
      <p class="card-meta">{esc(p.get('client'))}</p>
    </div>
  </a>
</article>"""


def gallery(items, title=None, eyebrow=None):
    if not items:
        return ""
    figs = "".join(
        f'<figure class="gallery-item">{img_tag(g["image"], g.get("caption", ""), "", "(max-width: 760px) 100vw, 33vw")}'
        f'{f"<figcaption>" + esc(g.get("caption")) + "</figcaption>" if g.get("caption") else ""}</figure>'
        for g in items if g.get("image"))
    heading = (f'<p class="eyebrow">{esc(eyebrow)}</p>' if eyebrow else "") + (
        f'<h2 class="section-title">{esc(title)}</h2>' if title else "")
    return f'{heading}<div class="gallery">{figs}</div>'


# ---------- Pages --------------------------------------------------------
def build_home():
    h = HOME
    stats = "".join(f'<div class="stat"><span class="stat-value">{esc(s["value"])}</span><span class="stat-label">{esc(s["label"])}</span></div>' for s in h["stats"])
    services = "".join(f'<a class="service" href="{link("/services/#" + s["slug"])}"><span class="service-num">{i:02d}</span><h3>{esc(s["title"])}</h3><p>{esc(s["summary"])}</p></a>' for i, s in enumerate(SERVICES, 1))
    featured = [p for p in PROJECTS if p.get("featured")][:3] or PROJECTS[:3]
    why = "".join(f'<div><h3>{esc(w["title"])}</h3><p>{esc(w["text"])}</p></div>' for w in h["why"])
    clients = "".join(f"<li>{esc(c)}</li>" for c in h["clients"])
    Page.path = "/"
    slides = [x for x in (h.get("hero_slides") or []) if x.get("image")] or [{"image": h["hero_image"], "alt": h.get("hero_image_alt")}]
    hero = '<div class="hero-slides" data-interval="6000">' + "".join(
        img_tag(x["image"], x.get("alt"), "hero-img hero-slide" + (" is-active" if i == 0 else ""), "100vw",
                lazy=i > 0, extra=' fetchpriority="high"' if i == 0 else ' aria-hidden="true"')
        for i, x in enumerate(slides)) + "</div>"

    def body():
        return f"""<section class="hero">
  {hero}
  <div class="hero-shade"></div>
  <div class="wrap hero-inner">
    <div class="lockup">
      <img class="lockup-mark" src="{asset('/assets/img/mark-light.svg')}" alt="{esc(SET['brand_name'])} logo" width="150" height="73">
      <div class="lockup-text"><span class="lockup-name">{esc(SET['brand_name'])}</span><span class="lockup-slogan">{esc(SET['slogan'])}</span></div>
    </div>
    <h1>{esc(h['hero_title'])}</h1>
    <p class="hero-text">{esc(h['hero_text'])}</p>
    <div class="hero-actions"><a class="btn btn-accent" href="{link('/projects/')}">See our projects</a><a class="btn btn-ghost" href="{link('/contact/')}">Request a quote</a></div>
  </div>
</section>
<section class="stats" aria-label="RNL at a glance"><div class="wrap stats-grid">{stats}</div></section>
<section class="section"><div class="wrap split">
  <div>
    <p class="eyebrow">{esc(h['intro_eyebrow'])}</p>
    <h2 class="section-title">{esc(h['intro_title'])}</h2>
    <p>{esc(h['intro_text'])}</p>
    <a class="text-link" href="{link('/about/')}">More about RNL →</a>
  </div>
  {img_tag(h['intro_image'], h.get('intro_image_alt'), 'split-img', '(max-width: 760px) 100vw, 50vw')}
</div></section>
<section class="section section-alt"><div class="wrap">
  <div class="section-head"><div><p class="eyebrow">What we do</p><h2 class="section-title">Engineering services</h2></div><a class="text-link" href="{link('/services/')}">All services →</a></div>
  <div class="grid grid-3">{services}</div>
</div></section>
<section class="section"><div class="wrap">
  <div class="section-head"><div><p class="eyebrow">Selected work</p><h2 class="section-title">Featured projects</h2></div><a class="text-link" href="{link('/projects/')}">All projects →</a></div>
  <div class="grid grid-3">{''.join(project_card(p) for p in featured)}</div>
</div></section>
<section class="section section-dark"><div class="wrap">
  <p class="eyebrow eyebrow-accent">Why RNL</p>
  <h2 class="section-title">Engineering with local knowledge</h2>
  <div class="grid grid-3 why">{why}</div>
</div></section>
<section class="section section-alt"><div class="wrap">{gallery(h.get('gallery'), h.get('gallery_title'), 'On site')}</div></section>
<section class="section"><div class="wrap">
  <p class="eyebrow">Clients</p>
  <h2 class="section-title">Trusted by clients across PNG</h2>
  <ul class="clients">{clients}</ul>
</div></section>
{cta()}"""
    write("/", "", SET["description"], body, active="/", image=h["hero_image"])


def branch_cards():
    out = []
    for b in SET["branches"]:
        lines = []
        if b.get("address"):
            lines.append(f"<p>{esc(b['address'])}</p>")
        if b.get("phone"):
            lines.append(f'<p><a href="{tel(b["phone"])}">{esc(b["phone"])}</a></p>')
        if b.get("email"):
            lines.append(f'<p><a href="mailto:{esc(b["email"])}">{esc(b["email"])}</a></p>')
        if not lines:
            lines.append('<p class="muted">Contact via head office</p>')
        out.append(f'<div class="branch"><h3>{esc(b["name"])}</h3><p class="branch-label">{esc(b.get("label"))}</p>{"".join(lines)}</div>')
    return "".join(out)


def build_about():
    a = ABOUT
    Page.path = "/about/"
    scope = "".join(f"<li>{esc(s)}</li>" for s in a.get("scope", []))
    team_photo = (f'<section class="section section-alt"><div class="wrap"><figure class="wide-figure">'
                  f'{img_tag(a["team_photo"], a.get("team_photo_caption"), "", "(max-width: 760px) 100vw, 1100px")}'
                  f'<figcaption>{esc(a.get("team_photo_caption"))}</figcaption></figure></div></section>') if a.get("team_photo") else ""

    def body():
        return f"""{page_head('About RNL', a['title'], a['lead'])}
<section class="section"><div class="wrap split">
  <div class="prose">{md(a['body'])}</div>
  {img_tag(a['image'], a.get('image_alt'), 'split-img', '(max-width: 760px) 100vw, 50vw')}
</div></section>
<section class="section section-alt"><div class="wrap">
  <h2 class="section-title">Our scope of work</h2>
  <ul class="scope">{scope}</ul>
</div></section>
<section class="section"><div class="wrap narrow">
  <p class="eyebrow">Director's statement</p>
  <blockquote class="quote">{paras(a['statement'])}
    <footer><strong>{esc(a['statement_name'])}</strong><span>{esc(a['statement_role'])}</span></footer>
  </blockquote>
</div></section>
{team_photo}
<section class="section"><div class="wrap">
  <h2 class="section-title">Our offices</h2>
  <div class="grid grid-4">{branch_cards()}</div>
</div></section>
{cta()}"""
    write("/about/", "About", a["lead"], body, active="/about/", image=a.get("image"))


def build_services():
    Page.path = "/services/"
    rows = []
    for i, s in enumerate(SERVICES, 1):
        pts = "".join(f"<li>{esc(p)}</li>" for p in s.get("points", []))
        pic = img_tag(s["image"], s.get("image_alt"), "service-img", "(max-width: 760px) 100vw, 40vw") if s.get("image") else ""
        rows.append(f"""<article class="service-row" id="{esc(s['slug'])}">
    <div class="service-row-head"><span class="service-num">{i:02d}</span><h2>{esc(s['title'])}</h2>{pic}</div>
    <div><p>{esc(s['summary'])}</p><ul class="ticks">{pts}</ul></div>
  </article>""")

    def body():
        return f"""{page_head('What we do', 'Engineering services')}
<section class="section"><div class="wrap">
  <p class="lead-dark">From first site visit to final certificate, we provide the engineering a project needs, designed for Papua New Guinea's climate, terrain and communities.</p>
  <div class="service-list">{''.join(rows)}</div>
</div></section>
{cta()}"""
    write("/services/", "Services", "Civil, structural, drafting, investigation, construction supervision and project management services from R. Napitalai Limited.", body, active="/services/")


def build_projects():
    sectors = []
    for p in PROJECTS:
        if p.get("sector") and p["sector"] not in sectors:
            sectors.append(p["sector"])
    chips = "".join(f'<button class="chip" data-filter="{slugify(s)}" aria-pressed="false">{esc(s)}</button>' for s in sectors)
    site_photos = [g for g in HOME.get("gallery", [])]

    def body():
        return f"""{page_head('Selected work', 'Projects across Papua New Guinea', 'Wharves, telecommunications, undersea cable landings, remedial works and national education infrastructure.')}
<section class="section"><div class="wrap">
  <div class="filters" role="group" aria-label="Filter projects by sector">
    <button class="chip is-active" data-filter="all" aria-pressed="true">All</button>{chips}
  </div>
  <div class="grid grid-3" id="project-grid">{''.join(project_card(p) for p in PROJECTS)}</div>
</div></section>
<section class="section section-alt"><div class="wrap">{gallery(site_photos, 'From our sites', 'Photos')}</div></section>
{cta()}"""
    write("/projects/", "Projects", "Selected engineering projects by R. Napitalai Limited across Papua New Guinea.", body, active="/projects/")

    for p in PROJECTS:
        facts = [("Client", p.get("client")), ("Location", p.get("location")), ("RNL's role", p.get("role")),
                 ("Project value", p.get("value")), ("Sector", p.get("sector"))]
        dl = "".join(f"<dt>{k}</dt><dd>{esc(v)}</dd>" for k, v in facts if v)
        Page.path = f"/projects/{p['slug']}/"
        others = [o for o in PROJECTS if o["slug"] != p["slug"]][:3]
        hero = img_tag(p["cover_image"], p.get("cover_alt"), "project-hero", "(max-width: 760px) 100vw, 760px", lazy=False) if p.get("cover_image") else ""
        pics = gallery(p.get("gallery"), "Photos")

        def body(p=p, dl=dl, others=others, hero=hero, pics=pics):
            return f"""{page_head('<a href="' + link('/projects/') + '">Projects</a> · ' + esc(p.get('sector')), p['title'], p['summary'])}
<section class="section"><div class="wrap project-layout">
  <div class="prose">{hero}{md(p.get('body'))}</div>
  <aside class="facts"><dl>{dl}</dl><a class="btn btn-primary" href="{link('/contact/')}">Discuss a similar project</a></aside>
</div></section>
{f'<section class="section"><div class="wrap">{pics}</div></section>' if pics else ''}
<section class="section section-alt"><div class="wrap">
  <h2 class="section-title">More projects</h2>
  <div class="grid grid-3">{''.join(project_card(o) for o in others)}</div>
</div></section>"""
        write(f"/projects/{p['slug']}/", p["title"], p["summary"], body, active="/projects/", image=p.get("cover_image"))


def build_team():
    Page.path = "/team/"
    people = []
    for t in TEAM:
        initials = "".join(w[0] for w in re.sub(r"^(Mr|Mrs|Ms|Dr)\s+", "", t["name"]).split()[:3:2]).upper()
        photo = (img_tag(t["photo"], t["name"], "person-photo") if t.get("photo")
                 else f'<div class="person-photo person-initials" aria-hidden="true">{esc(initials)}</div>')
        people.append(f"""<article class="person{' person-lead' if t.get('lead') else ''}">
    {photo}
    <div class="person-body">
      <h2>{esc(t['name'])}</h2>
      <p class="person-role">{esc(t.get('role'))}</p>
      {f'<p class="person-cred">{esc(t["credentials"])}</p>' if t.get('credentials') else ''}
      {f'<div class="prose">{md(t["bio"])}</div>' if t.get('bio') else ''}
    </div>
  </article>""")

    def body():
        return f"""{page_head('Key personnel', 'Leadership you can build on', 'We believe the success of any project depends on the quality of the people involved.')}
<section class="section"><div class="wrap"><div class="team">{''.join(people)}</div></div></section>
{cta()}"""
    write("/team/", "Our team", "Meet the engineers and leadership of R. Napitalai Limited.", body, active="/team/")


def build_news():
    items = "".join(
        f'<article class="news-item"><time datetime="{esc(n["date"])}">{fmt_date(n["date"])}</time>'
        f'<h2><a href="{link("/news/" + n["slug"] + "/")}">{esc(n["title"])}</a></h2><p>{esc(n.get("summary"))}</p></article>'
        for n in NEWS) or '<p class="muted">News will appear here soon.</p>'

    def body():
        return f"""{page_head('News', 'News and project updates', 'Milestones, company news and updates from our projects.')}
<section class="section"><div class="wrap narrow">{items}</div></section>"""
    write("/news/", "News", "News and project updates from R. Napitalai Limited.", body, active="/news/")

    for n in NEWS:
        def body(n=n):
            pic = img_tag(n["image"], n.get("image_alt", ""), "post-img", "(max-width: 760px) 100vw, 720px", lazy=False) if n.get("image") else ""
            return (f'<section class="page-head"><div class="wrap narrow"><p class="eyebrow eyebrow-light"><a href="{link("/news/")}">News</a> · '
                    f'<time datetime="{esc(n["date"])}">{fmt_date(n["date"])}</time></p><h1>{esc(n["title"])}</h1>'
                    f'<p class="lead">{esc(n.get("summary"))}</p></div></section>'
                    f'<section class="section"><div class="wrap narrow prose">{pic}{md(n.get("body"))}</div></section>{cta()}')
        write(f"/news/{n['slug']}/", n["title"], n.get("summary", ""), body, active="/news/", image=n.get("image"),
              og_type="article", lastmod=str(n.get("date"))[:10])


def build_contact():
    f = SET["form"]
    provider = (f.get("provider") or "").lower()
    endpoint, hidden, attrs = "", "", ""
    if provider == "web3forms" and f.get("web3forms_access_key"):
        endpoint = "https://api.web3forms.com/submit"
        hidden = (f'<input type="hidden" name="access_key" value="{esc(f["web3forms_access_key"])}">'
                  f'<input type="hidden" name="from_name" value="{esc(SET["brand_name"])} website">')
    elif provider == "netlify":
        endpoint = "netlify"
        attrs = ' name="enquiry" data-netlify="true" netlify-honeypot="botcheck"'
        hidden = '<input type="hidden" name="form-name" value="enquiry">'
    elif provider == "endpoint" and f.get("endpoint"):
        endpoint = f["endpoint"]
    options = "".join(f"<option>{esc(o)}</option>" for o in f.get("enquiry_types", []))
    others = "".join(f'<li><strong>{esc(b["name"])}</strong> — {esc(b.get("label"))}</li>' for b in SET["branches"][1:])

    def body():
        return f"""{page_head('Get in touch', "Let's talk about your project", 'Whether you are planning a new facility, need structural certification or want to discuss a project, we will reply within two working days.')}
<section class="section"><div class="wrap contact-grid">
  <form class="form" id="enquiry-form" method="post"{attrs} data-endpoint="{esc(endpoint)}" data-mailto="{esc(f.get('notify_email') or SET['email'])}"{' data-preview="1"' if ARGS.staging else ''} novalidate>
    {hidden}
    <input type="hidden" name="subject" value="New website enquiry — {esc(SET['brand_name'])}">
    <div class="hp" aria-hidden="true"><label>Leave this empty <input type="text" name="botcheck" tabindex="-1" autocomplete="off"></label></div>
    <div class="field-row">
      <div class="field"><label for="f-name">Name</label><input id="f-name" name="name" autocomplete="name" required></div>
      <div class="field"><label for="f-org">Organisation <span class="opt">(optional)</span></label><input id="f-org" name="organisation" autocomplete="organization"></div>
    </div>
    <div class="field-row">
      <div class="field"><label for="f-email">Email</label><input id="f-email" name="email" type="email" autocomplete="email" required></div>
      <div class="field"><label for="f-phone">Phone <span class="opt">(optional)</span></label><input id="f-phone" name="phone" type="tel" autocomplete="tel"></div>
    </div>
    <div class="field"><label for="f-type">Type of enquiry</label><select id="f-type" name="enquiry_type">{options}</select></div>
    <div class="field"><label for="f-msg">Tell us about your project</label><textarea id="f-msg" name="message" rows="6" required></textarea></div>
    <button class="btn btn-primary" type="submit">Send enquiry</button>
    <p class="form-status" role="status" aria-live="polite"></p>
  </form>
  <aside class="contact-side">
    <div class="contact-block"><h2>Head office</h2><p>{esc(SET['street_address'])}<br>{esc(SET['city'])}<br>{esc(SET['postal_address'])}</p><p><a class="text-link" href="{esc(SET['map_link'])}" rel="noopener">Open in Google Maps →</a></p></div>
    <div class="contact-block"><h2>Phone and email</h2><p><a href="{tel(SET['phone'])}">{esc(SET['phone'])}</a><br><a href="mailto:{esc(SET['email'])}">{esc(SET['email'])}</a></p></div>
    <div class="contact-block"><h2>Other offices</h2><ul class="plain">{others}</ul></div>
    <div class="contact-block"><h2>Careers</h2><p>We hire graduate civil and structural engineers. Vacancies are posted on our <a href="{esc(SET.get('facebook'))}" rel="noopener">Facebook page</a>.</p></div>
  </aside>
</div></section>"""
    write("/contact/", "Contact", "Contact R. Napitalai Limited in Port Moresby, Lae, Kokopo or Goroka.", body, active="/contact/")


def build_404():
    def body():
        return (page_head("", "Page not found", "The page you were looking for has moved or no longer exists.")
                + f'<section class="section"><div class="wrap"><a class="btn btn-primary" href="{link("/")}">Back to the home page</a></div></section>')
    write("/404.html", "Page not found", SET["description"], body, noindex=True)


def build_seo_files():
    today = dt.date.today().isoformat()
    urls = "".join(f"<url><loc>{esc(SITE_URL + p)}</loc><lastmod>{m or today}</lastmod></url>" for p, m in PAGES)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', encoding="utf-8")
    robots = ("User-agent: *\nDisallow: /\n" if ARGS.staging
              else f"User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    (OUT / "robots.txt").write_text(robots, encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    build_home(); build_about(); build_services(); build_projects()
    build_team(); build_news(); build_contact(); build_404(); build_seo_files()
    (OUT / ".nojekyll").write_text("")
    print(f"Built {len(PAGES) + 1} pages into {OUT.relative_to(ROOT)}"
          f"{' (staging)' if ARGS.staging else ''}{' (relative links)' if ARGS.relative else ''}")


if __name__ == "__main__":
    main()
