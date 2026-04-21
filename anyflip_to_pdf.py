"""
Download an AnyFlip flipbook and save it as a PDF.

Usage:
    python anyflip_to_pdf.py <anyflip-url-or-id>

Examples:
    python anyflip_to_pdf.py https://anyflip.com/sdffp/ieyn/basic
    python anyflip_to_pdf.py sdffp/ieyn

The script:
  1. Fetches the book's mobile `config.js`.
  2. Parses the ordered list of large-page image hashes.
  3. Downloads every page (webp) in parallel.
  4. Converts all pages into a single PDF next to this script.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import io
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
ASSET_HOST = "https://online.anyflip.com"
PAGE_REGEX = re.compile(r'"n":\["[^"]*large[^"]*?([a-f0-9]{32})\.webp[^"]*"\]')
TITLE_REGEX = re.compile(r'"bookTitle"\s*:\s*"([^"]{1,200})"')


def parse_book_id(arg: str) -> str:
    """Return '<code>/<book>' from a full URL or a bare id."""
    s = arg.strip()
    if "://" in s:
        parts = [p for p in urlparse(s).path.split("/") if p]
        if len(parts) < 2:
            raise ValueError(f"Cannot parse book id from URL: {arg}")
        return f"{parts[0]}/{parts[1]}"
    parts = [p for p in s.split("/") if p]
    if len(parts) != 2:
        raise ValueError(f"Expected '<code>/<book>' or AnyFlip URL, got: {arg}")
    return f"{parts[0]}/{parts[1]}"


def fetch_config(book_id: str, session: requests.Session) -> str:
    url = f"{ASSET_HOST}/{book_id}/mobile/javascript/config.js"
    r = session.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.text


def extract_pages(config_js: str) -> list[str]:
    hashes = PAGE_REGEX.findall(config_js)
    if not hashes:
        raise RuntimeError("No pages found in config.js - layout may have changed.")
    return hashes


def extract_title(config_js: str, book_id: str) -> str:
    m = TITLE_REGEX.search(config_js)
    if m:
        title = m.group(1).strip()
    else:
        title = book_id.replace("/", "_")
    return re.sub(r'[\\/:*?"<>|]+', "_", title).strip() or book_id.replace("/", "_")


def download_page(
    session: requests.Session,
    book_id: str,
    page_hash: str,
    idx: int,
    out_dir: Path,
    retries: int = 4,
) -> Path:
    url = f"{ASSET_HOST}/{book_id}/files/large/{page_hash}.webp"
    dest = out_dir / f"{idx:04d}.webp"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    referer = f"{ASSET_HOST}/{book_id}/mobile/index.html"
    headers = {"User-Agent": UA, "Referer": referer, "Origin": ASSET_HOST}
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = session.get(url, headers=headers, timeout=30)
            if r.status_code == 200 and r.content:
                dest.write_bytes(r.content)
                return dest
            last_err = RuntimeError(f"HTTP {r.status_code} for {url}")
        except requests.RequestException as e:
            last_err = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to download page {idx}: {last_err}")


def images_to_pdf(paths: list[Path], out_pdf: Path) -> None:
    if not paths:
        raise RuntimeError("No pages to assemble.")
    first, *rest = [Image.open(p).convert("RGB") for p in paths]
    first.save(out_pdf, "PDF", save_all=True, append_images=rest)


def main() -> int:
    ap = argparse.ArgumentParser(description="Download an AnyFlip book to PDF.")
    ap.add_argument("url", help="AnyFlip URL or '<code>/<book>' id")
    ap.add_argument("-o", "--output", help="Output PDF path (default: derived from book title)")
    ap.add_argument("-w", "--workers", type=int, default=12, help="Parallel downloads")
    ap.add_argument("--keep-webp", action="store_true", help="Keep downloaded webp pages")
    args = ap.parse_args()

    book_id = parse_book_id(args.url)
    print(f"[*] Book id: {book_id}")

    session = requests.Session()

    print("[*] Fetching config.js …")
    config_js = fetch_config(book_id, session)
    pages = extract_pages(config_js)
    title = extract_title(config_js, book_id)
    print(f"[*] Title: {title}")
    print(f"[*] Pages: {len(pages)}")

    work_dir = Path(__file__).resolve().parent / "pages" / book_id.replace("/", "_")
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Downloading pages into {work_dir} …")
    downloaded: list[Path] = [work_dir / f"{i + 1:04d}.webp" for i in range(len(pages))]
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(download_page, session, book_id, h, i + 1, work_dir): i
            for i, h in enumerate(pages)
        }
        done = 0
        for fut in cf.as_completed(futures):
            fut.result()
            done += 1
            if done % 10 == 0 or done == len(pages):
                print(f"    {done}/{len(pages)}")

    pdf_path = Path(args.output) if args.output else Path(__file__).resolve().parent / f"{title}.pdf"
    print(f"[*] Writing PDF -> {pdf_path}")
    images_to_pdf(downloaded, pdf_path)

    if not args.keep_webp:
        for p in downloaded:
            try:
                p.unlink()
            except OSError:
                pass
        try:
            work_dir.rmdir()
            work_dir.parent.rmdir()
        except OSError:
            pass

    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    print(f"[+] Done: {pdf_path} ({size_mb:.1f} MB, {len(pages)} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
