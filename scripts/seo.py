#!/usr/bin/env python3
"""Add per-page SEO metadata and generate the sitemap after mdBook builds."""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SITE = "https://hakodb.github.io"
DOCS = f"{SITE}/docs"
OG_IMAGE = f"{SITE}/assets/avatar.png"
SKIP = {"404.html", "print.html", "toc.html"}


def first_paragraph(page: str) -> str:
    main = re.search(r"<main[^>]*>(.*?)</main>", page, re.S)
    if not main:
        return ""
    body = re.sub(r"<blockquote.*?</blockquote>", "", main.group(1), flags=re.S)
    paragraphs = []
    for match in re.finditer(r"<p(?:\s[^>]*)?>(.*?)</p>", body, re.S):
        text = re.sub(r"<[^>]+>", "", match.group(1))
        text = re.sub(r"\s+", " ", html.unescape(text)).strip()
        if text:
            paragraphs.append(text)
    for text in paragraphs:
        if len(text) >= 80:
            return text
    return paragraphs[0] if paragraphs else ""


def description_for(title: str, page: str) -> str:
    text = first_paragraph(page)
    if not text:
        text = f"{title} - HakoDB documentation."
    elif len(text) < 80:
        text = f"{title}: {text}"
    if len(text) > 160:
        text = text[:157].rsplit(" ", 1)[0].rstrip(".,;:") + "..."
    if text.endswith(":"):
        text = text[:-1] + "."
    return text


def canonical_for(page_path: Path, docs_dir: Path) -> str:
    rel = page_path.relative_to(docs_dir).as_posix()
    if rel == "index.html":
        return f"{DOCS}/"
    return f"{DOCS}/{rel}"


def seo_block(title: str, description: str, canonical: str) -> str:
    schema = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": title,
        "description": description,
        "url": canonical,
        "image": OG_IMAGE,
        "inLanguage": "en",
        "isPartOf": {"@type": "WebSite", "name": "HakoDB Docs", "url": f"{DOCS}/"},
        "publisher": {
            "@type": "Organization",
            "name": "HakoDB",
            "url": f"{SITE}/",
            "logo": {"@type": "ImageObject", "url": OG_IMAGE},
        },
    }
    social_title = html.escape(f"{title} - HakoDB Docs", quote=True)
    description_attr = html.escape(description, quote=True)
    canonical_attr = html.escape(canonical, quote=True)
    return "\n".join(
        [
            "<!-- seo:start -->",
            f'<meta name="description" content="{description_attr}">',
            f'<link rel="canonical" href="{canonical_attr}">',
            '<meta property="og:type" content="article">',
            '<meta property="og:site_name" content="HakoDB">',
            f'<meta property="og:title" content="{social_title}">',
            f'<meta property="og:description" content="{description_attr}">',
            f'<meta property="og:url" content="{canonical_attr}">',
            f'<meta property="og:image" content="{OG_IMAGE}">',
            '<meta property="og:image:alt" content="HakoDB logo">',
            '<meta name="twitter:card" content="summary">',
            f'<meta name="twitter:title" content="{social_title}">',
            f'<meta name="twitter:description" content="{description_attr}">',
            f'<meta name="twitter:image" content="{OG_IMAGE}">',
            '<script type="application/ld+json">',
            json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
            "</script>",
            "<!-- seo:end -->",
        ]
    )


def add_home_link(page: str) -> str:
    if '<h1 class="menu-title"><a ' in page:
        return page
    return page.replace(
        '<h1 class="menu-title">HakoDB Docs</h1>',
        '<h1 class="menu-title"><a href="https://hakodb.github.io/" title="HakoDB homepage">HakoDB</a> Docs</h1>',
        1,
    )


def process_page(page_path: Path, docs_dir: Path) -> bool:
    page = page_path.read_text(encoding="utf-8")
    title_match = re.search(r"<title>(.*?)</title>", page, re.S)
    title = html.unescape(title_match.group(1)).replace(" - HakoDB Docs", "").strip()
    description = description_for(title, page)
    canonical = canonical_for(page_path, docs_dir)

    page = add_home_link(page)
    has_home_link = '<h1 class="menu-title"><a ' in page
    page = re.sub(r"\s*<!-- seo:start -->.*?<!-- seo:end -->", "", page, flags=re.S)
    page = re.sub(r'\s*<meta name="description" content="[^"]*">', "", page, count=1)
    page = page.replace("</head>", seo_block(title, description, canonical) + "\n</head>", 1)
    page_path.write_text(page, encoding="utf-8")
    return has_home_link


def write_sitemap(site_dir: Path, docs_dir: Path) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    entries = [(f"{SITE}/", "1.0", "weekly"), (f"{DOCS}/", "0.9", "weekly")]
    for page_path in sorted(docs_dir.glob("*.html")):
        if page_path.name in SKIP or page_path.name == "index.html":
            continue
        entries.append((f"{DOCS}/{page_path.name}", "0.7", "monthly"))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url, priority, changefreq in entries:
        lines.extend(
            [
                "  <url>",
                f"    <loc>{html.escape(url)}</loc>",
                f"    <lastmod>{today}</lastmod>",
                f"    <changefreq>{changefreq}</changefreq>",
                f"    <priority>{priority}</priority>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    (site_dir / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    site_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    docs_dir = site_dir / "docs"
    if not docs_dir.is_dir():
        print(f"missing docs directory: {docs_dir}", file=sys.stderr)
        return 1

    processed = linked = 0
    for page_path in sorted(docs_dir.glob("*.html")):
        if page_path.name not in SKIP:
            processed += 1
            linked += process_page(page_path, docs_dir)
    write_sitemap(site_dir, docs_dir)

    sitemap = (site_dir / "sitemap.xml").read_text(encoding="utf-8")
    missing_roots = [url for url in (f"{SITE}/", f"{DOCS}/") if f"<loc>{url}</loc>" not in sitemap]
    if linked != processed or missing_roots:
        print(f"seo: home link {linked}/{processed}, missing sitemap roots {missing_roots}", file=sys.stderr)
        return 1
    print(f"seo: {processed} pages, sitemap written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
