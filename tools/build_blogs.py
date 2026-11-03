#!/usr/bin/env python3
"""Build blog posts: blog-src/<slug>/post.md  ->  Blogs/<slug>/index.html + Blogs/blogs.json

Run locally:  python tools/build_blogs.py
GitHub Actions runs it automatically on every push that touches blog-src/.

Extra post syntax (image beside text, text wraps under the image):

    ::: image-left 320px
    ![Alt text](nmap.png "Optional caption")
    Long paragraph(s) here. They sit beside the image and flow
    underneath it once they are taller than the image.
    :::

    options (all optional, any order):  image-left | image-right
        320px / 40% / 20rem   image width (default 40%)
        center                no wrapping; text is vertically centred beside the image
"""
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from string import Template
from urllib.parse import quote, unquote

import markdown
from pygments.formatters import HtmlFormatter

SITE_URL = "https://nayush-ghimire.com.np"
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "blog-src"
OUT = ROOT / "Blogs"
TEMPLATE = Path(__file__).resolve().parent / "post_template.html"
MARKER = ".generated"  # lets the script delete only folders it created
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# Only these files are copied from blog-src/<slug>/ to the public site (so notes.txt, .psd, etc. never leak)
ASSET_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".mp4", ".webm", ".pdf"}
TRUTHY = {"true", "yes", "1"}

MEDIA_RE = re.compile(
    r"^:::[ \t]*(image-left|image-right)[ \t]*([^\n]*)\n(.*?)^:::[ \t]*$", re.S | re.M
)
IMG_LINE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
WIDTH_RE = re.compile(r"\d{1,4}(?:px|%|rem)")

# Appended to the pygments CSS, so post_template.html needs no change.
# (Move it into your main stylesheet later if you prefer.)
MEDIA_CSS = """
.media{display:flow-root;margin:2rem 0}
.media figure{float:left;width:var(--w,40%);max-width:60%;margin:.25rem 1.75rem 1rem 0}
.media-right figure{float:right;margin:.25rem 0 1rem 1.75rem}
.media figure img{display:block;width:100%;height:auto}
.media figcaption{font-size:.85em;opacity:.7;margin-top:.4rem}
.media-text>:first-child{margin-top:0}
.media-text>:last-child{margin-bottom:0}
.media-center{display:flex;align-items:center;gap:1.75rem}
.media-center figure{float:none;flex:0 0 var(--w,40%);margin:0}
.media-center.media-right{flex-direction:row-reverse}
.media-center .media-text{flex:1;min-width:0}
h1,h2,h3,h4{clear:both}
@media(max-width:640px){
 .media figure,.media-right figure{float:none;width:100%;max-width:100%;margin:0 0 1rem}
 .media-center{display:block}
}
"""


def fail(msg):
    sys.exit(f"ERROR: {msg}")


def strip_quotes(v):
    v = v.strip()
    # only strip a MATCHING pair, so  title: Understanding "sudo"  keeps its closing quote
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_list(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return [strip_quotes(c) for c in v.split(",") if c.strip()]


def parse_post(path):
    text = path.read_text(encoding="utf-8").lstrip("\ufeff").replace("\r\n", "\n")
    m = re.match(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)(.*)", text, re.S)
    if not m:
        fail(f"{path}: missing front matter block (--- ... ---) at the very top")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition(":")
            meta[key.strip().lower()] = strip_quotes(value)
    return meta, m.group(2)


def render_media(kind, opts, inner):
    """Turn one ::: image-left/right block into HTML. Raises ValueError on bad input."""
    lines = inner.strip("\n").split("\n")
    first = lines[0].strip() if lines else ""
    if not IMG_LINE_RE.fullmatch(first):
        raise ValueError(
            "the first line inside an '::: image-left/right' block must be an image, "
            f'e.g. ![alt](pic.png "caption"); got: {first[:60]!r}'
        )
    classes = ["media", "media-right" if kind == "image-right" else "media-left"]
    style = ""
    for word in opts.split():
        if word == "center":
            classes.append("media-center")
        elif WIDTH_RE.fullmatch(word):
            style = f' style="--w:{word}"'
        else:
            raise ValueError(f"unknown option '{word}' (use e.g. 320px, 40%, center)")
    figure = render_markdown(first, allow_media=False)
    text = render_markdown("\n".join(lines[1:]).strip(), allow_media=False)
    return (f'<div class="{" ".join(classes)}"{style}>\n{figure}\n'
            f'<div class="media-text">\n{text}\n</div>\n</div>')


def render_markdown(body, allow_media=True):
    blocks = []
    if allow_media:
        def stash(m):
            blocks.append(render_media(m.group(1), m.group(2), m.group(3)))
            return f"\n\nZZMEDIABLOCK{len(blocks) - 1}ZZ\n\n"
        body = MEDIA_RE.sub(stash, body)

    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc", "codehilite", "sane_lists"],
        extension_configs={"codehilite": {"guess_lang": False, "css_class": "codehilite"}},
    )
    out = md.convert(body)

    def figure(m):
        img = m.group(1)
        title = re.search(r'title="([^"]*)"', img)
        img = re.sub(r'\s*title="[^"]*"', "", img).replace("<img ", '<img loading="lazy" ', 1)
        cap = f"<figcaption>{title.group(1)}</figcaption>" if title else ""
        return f"<figure>{img}{cap}</figure>"

    out = re.sub(r"<p>(<img [^>]*>)</p>", figure, out)
    out = out.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    for i, block in enumerate(blocks):
        out = out.replace(f"<p>ZZMEDIABLOCK{i}ZZ</p>", block)
    return out


def plain_text(content):
    return html.unescape(re.sub(r"<[^>]+>", " ", content))


def make_summary(meta, content):
    raw = meta.get("summary", "")
    if not raw:
        m = re.search(r"<p>(.*?)</p>", content, re.S)
        raw = plain_text(m.group(1)) if m else ""
    raw = " ".join(raw.split())
    if len(raw) > 200:  # cut at a word boundary, not mid-word
        raw = raw[:200].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"
    return html.escape(raw, quote=True)  # escape ONCE (the old code double-escaped & < >)


def check_local_refs(content, folder, source):
    """Fail the build if the post points at an image/file that isn't in its folder."""
    visible = re.sub(r"<(pre|code)\b.*?</\1>", "", content, flags=re.S)  # ignore code samples
    for ref in re.findall(r'(?:src|href)="([^"#?]+)', visible):
        if re.match(r"([a-z][a-z0-9+.-]*:|//|/)", ref, re.I):
            continue
        if not (folder / unquote(ref)).is_file():
            fail(f"{source}: references '{ref}' but that file is not in {folder}")


def collect_assets(folder, source):
    keep = []
    for f in sorted(folder.rglob("*")):
        rel = f.relative_to(folder)
        if not f.is_file() or f == source or any(part.startswith(".") for part in rel.parts):
            continue
        if f.suffix.lower() in ASSET_EXTS:
            keep.append(f)
        else:
            print(f"note: not publishing {folder.name}/{rel} (extension not in ASSET_EXTS)")
    return keep


def main():
    template = Template(TEMPLATE.read_text(encoding="utf-8"))
    code_css = HtmlFormatter(style="monokai").get_style_defs(".codehilite") + MEDIA_CSS
    folders = sorted(p for p in SRC.iterdir() if p.is_dir()) if SRC.exists() else []
    built = []

    # ---- Phase 1: parse + validate + render everything IN MEMORY (nothing on disk changes yet) ----
    for folder in folders:
        slug = folder.name
        if slug.startswith(("_", ".")):
            continue
        if not SLUG_RE.match(slug):
            fail(f"folder '{slug}' must be lowercase letters, numbers and hyphens only")
        source = folder / "post.md"
        if not source.exists():
            fail(f"{folder}: no post.md found")
        meta, body = parse_post(source)
        if meta.get("draft", "").lower() in TRUTHY:
            print(f"skip (draft): {slug}")
            continue
        if not meta.get("title"):
            fail(f"{source}: 'title' is required")
        try:
            d = date.fromisoformat(meta.get("date", ""))
        except ValueError:
            fail(f"{source}: 'date' must look like 2026-10-23")
        if d > date.today():
            print(f"warning: {slug} is dated in the future ({d}) but will be published now")
        cover = meta.get("cover", "")
        if cover and not (folder / cover).is_file():
            fail(f"{source}: cover file '{cover}' not found in {folder}")
        if not cover:
            print(f"warning: {slug} has no cover image (the listing shows an empty thumbnail)")
        cats = parse_list(meta.get("categories", ""))

        try:
            content = render_markdown(body)
        except ValueError as e:
            fail(f"{source}: {e}")
        check_local_refs(content, folder, source)

        dest = OUT / slug
        if dest.exists() and not (dest / MARKER).exists():
            fail(f"{dest} already exists and was not generated by this script; pick another folder name")

        minutes = max(1, round(len(plain_text(content).split()) / 220))
        cover_url = quote(cover, safe="/")
        cats_html = f'<span class="cats">{html.escape(", ".join(cats))}</span>' if cats else ""
        cover_html = (f'<img class="cover" src="{html.escape(cover_url)}" alt="" width="1200" height="630">'
                      if cover else "")
        url = f"{SITE_URL}/Blogs/{slug}/"
        page = template.safe_substitute(
            title=html.escape(meta["title"], quote=True), summary=make_summary(meta, content),
            canonical=html.escape(url),
            og_image=html.escape(f"{SITE_URL}/Blogs/{slug}/{cover_url}") if cover else "",
            date_iso=d.isoformat(), date_display=f"{d:%b} {d.day}, {d.year}",
            categories=cats_html, minutes=minutes, cover=cover_html,
            content=content, code_css=code_css, year=date.today().year,
        )
        built.append({
            "slug": slug, "folder": folder, "source": source, "dest": dest, "page": page,
            "assets": collect_assets(folder, source),
            "entry": {"title": meta["title"], "date": d.isoformat(), "categories": cats,
                      "cover": f"{slug}/{cover_url}" if cover else "", "url": f"{slug}/"},
        })

    # ---- Phase 2: write to disk ----
    slugs = set()
    for b in built:
        dest = b["dest"]
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for f in b["assets"]:
            target = dest / f.relative_to(b["folder"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
        (dest / MARKER).write_text("generated by tools/build_blogs.py\n")
        (dest / "index.html").write_text(b["page"], encoding="utf-8")
        slugs.add(b["slug"])
        print(f"built: {b['slug']}")

    # Remove generated folders whose source post was deleted (or turned into a draft)
    for old in OUT.iterdir() if OUT.exists() else []:
        if old.is_dir() and (old / MARKER).exists() and old.name not in slugs:
            shutil.rmtree(old)
            print(f"removed: {old.name}")

    posts = sorted(built, key=lambda b: (b["entry"]["date"], b["slug"]))
    index = [{"id": i, **b["entry"]} for i, b in enumerate(posts, 1)]
    OUT.mkdir(exist_ok=True)
    (OUT / "blogs.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"blogs.json: {len(index)} post(s)")


if __name__ == "__main__":
    main()
