#!/usr/bin/env python3
"""Extract a rulebook PDF into a staging folder that Claude can work from
without re-reading the PDF.

  python pdf_extract.py BOOK.pdf --out STAGING_DIR [--render auto|all|none] [--dpi 110]
                                 [--pages 1-40] [--columns auto|1|2]

Produces in STAGING_DIR:
  manifest.json     page count, printed page labels, per-page stats and flags
  outline.json      PDF bookmarks (if any) with page numbers
  headings.md       font-size-based heading candidates per page (for chapter mapping)
  text.md           all text, with <!-- page N | printed L --> markers (grep this)
  pages/pNNNN.txt   one file per page
  tables/pNNNN-tK.csv   table candidates found by pdfplumber (always verify!)
  images/pNNNN.png  page renders for table pages and scanned pages (read these to check layout)
  REPORT.md         summary: scanned pages, table pages, two-column pages, warnings

Requires: pip install pdfplumber pypdf
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber is required: pip install pdfplumber pypdf")
try:
    import pypdf
except ImportError:
    pypdf = None

DICE_HINT = re.compile(r"\b(\d*d\d+|d%|\d+\s*[-–]\s*\d+)\b", re.I)


def parse_pages(spec: str | None, n: int):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        lo = int(a)
        hi = int(b) if b else lo
        out += list(range(lo - 1, min(hi, n)))
    return out


def page_labels(pdf_path: Path, n: int):
    if pypdf is None:
        return [str(i + 1) for i in range(n)]
    try:
        r = pypdf.PdfReader(str(pdf_path))
        labels = list(r.page_labels)
        if len(labels) == n:
            return labels
    except Exception:
        pass
    return [str(i + 1) for i in range(n)]


def outline(pdf_path: Path):
    if pypdf is None:
        return []
    try:
        r = pypdf.PdfReader(str(pdf_path))
    except Exception:
        return []
    out = []

    def walk(items, depth):
        for it in items:
            if isinstance(it, list):
                walk(it, depth + 1)
                continue
            try:
                out.append({"title": it.title, "page": r.get_destination_page_number(it) + 1, "depth": depth})
            except Exception:
                pass
    try:
        walk(r.outline, 0)
    except Exception:
        pass
    return out


def detect_gutter(page, words):
    """Return x of a vertical gutter splitting two text columns, or None."""
    if len(words) < 40:
        return None
    w = page.width
    lo, hi = w * 0.35, w * 0.65
    best, best_cross = None, None
    step = w / 200
    x = lo
    while x <= hi:
        cross = sum(1 for wd in words if wd["x0"] < x < wd["x1"])
        if best_cross is None or cross < best_cross:
            best, best_cross = x, cross
        x += step
    left = sum(1 for wd in words if wd["x1"] <= best)
    right = sum(1 for wd in words if wd["x0"] >= best)
    if best_cross is not None and best_cross <= max(2, len(words) * 0.01) and min(left, right) > len(words) * 0.2:
        return best
    return None


def page_text(page, columns_mode):
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    gutter = None
    if columns_mode == "2" or (columns_mode == "auto"):
        gutter = detect_gutter(page, words)
        if columns_mode == "2" and gutter is None:
            gutter = page.width / 2
    if gutter:
        left = page.crop((0, 0, gutter, page.height)).extract_text() or ""
        right = page.crop((gutter, 0, page.width, page.height)).extract_text() or ""
        return left.rstrip() + "\n\n" + right.strip(), True
    return page.extract_text() or "", False


def headings_for(page, body_size):
    lines = {}
    for ch in page.chars:
        key = round(ch["top"])
        lines.setdefault(key, []).append(ch)
    out = []
    for top, chars in sorted(lines.items()):
        size = statistics.median(c["size"] for c in chars)
        bold = sum("Bold" in c.get("fontname", "") for c in chars) > len(chars) / 2
        text = "".join(c["text"] for c in sorted(chars, key=lambda c: c["x0"])).strip()
        if len(text) < 3 or len(text) > 90:
            continue
        if size >= body_size * 1.25 or (bold and size >= body_size * 1.05 and len(text) < 60):
            out.append((round(size, 1), text))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--render", choices=["auto", "all", "none"], default="auto")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--pages", help="e.g. 1-40,55")
    ap.add_argument("--columns", choices=["auto", "1", "2"], default="auto")
    a = ap.parse_args(argv)

    pdf_path = Path(a.pdf).expanduser().resolve()
    out = Path(a.out)
    for sub in ("pages", "tables", "images"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    with pdfplumber.open(str(pdf_path)) as pdf:
        n = len(pdf.pages)
        labels = page_labels(pdf_path, n)
        idxs = parse_pages(a.pages, n)

        # body font size = most common char size over a sample of pages
        sizes = Counter()
        for i in idxs[: min(len(idxs), 30)]:
            for c in pdf.pages[i].chars[:4000]:
                sizes[round(c["size"], 1)] += 1
        body = sizes.most_common(1)[0][0] if sizes else 10.0

        manifest = {"pdf": str(pdf_path), "pages": n, "body_font_size": body, "page_info": []}
        text_md = [f"# Extracted text: {pdf_path.name}\n"]
        heading_md = [f"# Heading candidates: {pdf_path.name}\n", f"Body font size ≈ {body}\n"]
        scanned, table_pages, two_col = [], [], []

        for i in idxs:
            page = pdf.pages[i]
            pno, label = i + 1, labels[i]
            txt, split = page_text(page, a.columns)
            info = {"page": pno, "printed": label, "chars": len(txt.strip()), "two_column": split,
                    "tables": 0, "dice_hints": len(DICE_HINT.findall(txt))}
            if len(txt.strip()) < 25 and page.images:
                info["scanned"] = True
                scanned.append(pno)
            if split:
                two_col.append(pno)
            (out / "pages" / f"p{pno:04d}.txt").write_text(txt, encoding="utf-8")
            text_md.append(f"\n<!-- page {pno} | printed {label} -->\n{txt}\n")

            try:
                tables = page.extract_tables()
            except Exception:
                tables = []
            k = 0
            for t in tables:
                rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in t if any(r)]
                if len(rows) < 2:
                    continue
                k += 1
                with open(out / "tables" / f"p{pno:04d}-t{k}.csv", "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerows(rows)
            info["tables"] = k
            # pages with lots of dice-looking ranges are probably tables even if pdfplumber saw no grid
            likely_table = k > 0 or info["dice_hints"] >= 6
            if likely_table:
                table_pages.append(pno)
            info["likely_table"] = likely_table

            hs = headings_for(page, body)
            if hs:
                heading_md.append(f"\n## page {pno} (printed {label})")
                heading_md += [f"- [{s}] {t}" for s, t in hs]

            render = a.render == "all" or (a.render == "auto" and (likely_table or info.get("scanned")))
            if render:
                try:
                    page.to_image(resolution=a.dpi).save(str(out / "images" / f"p{pno:04d}.png"))
                    info["image"] = f"images/p{pno:04d}.png"
                except Exception as e:  # rendering is optional
                    info["image_error"] = str(e)
            manifest["page_info"].append(info)
            if pno % 25 == 0:
                print(f"  ...page {pno}/{n}", file=sys.stderr)

    ol = outline(pdf_path)
    (out / "outline.json").write_text(json.dumps(ol, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "text.md").write_text("".join(text_md), encoding="utf-8")
    (out / "headings.md").write_text("\n".join(heading_md) + "\n", encoding="utf-8")

    def rng(v):
        return ", ".join(map(str, v)) if len(v) < 40 else f"{len(v)} pages: {v[:20]} ..."
    rep = [f"# Extraction report: {pdf_path.name}", "",
           f"- Pages extracted: {len(idxs)} of {n}",
           f"- PDF bookmarks: {len(ol)} {'(use outline.json for chapters)' if ol else '(none — use headings.md)'}",
           f"- Printed page labels differ from PDF index: {'yes' if any(labels[i] != str(i + 1) for i in idxs) else 'no'}",
           f"- Two-column pages (split at gutter): {rng(two_col) or 'none'}",
           f"- Likely table pages (rendered to images/): {rng(table_pages) or 'none'}",
           f"- Scanned / image-only pages: {rng(scanned) or 'none'}"]
    if scanned:
        rep.append("\n⚠️ Image-only pages have no extractable text. OCR the PDF first "
                   "(e.g. `ocrmypdf in.pdf out.pdf`) or transcribe those pages from the images.")
    rep.append("\n⚠️ tables/*.csv are machine guesses. Always check against images/ before transcribing.")
    (out / "REPORT.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
