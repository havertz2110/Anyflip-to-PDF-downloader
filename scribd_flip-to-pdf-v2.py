#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
script.py — Tải sách FlipHTML5 / AnyFlip thành 1 file PDF.

CÁCH DÙNG
    python3 script.py <url> [tuỳ chọn]

VÍ DỤ
    python3 script.py https://online.fliphtml5.com/ksgeo/zerq/
    python3 script.py https://anyflip.com/sdffp/ieyn/basic
    python3 script.py sdffp/ieyn                       # dạng rút gọn = AnyFlip
    python3 script.py <url> -o sach.pdf -j 10 --keep

TUỲ CHỌN
    -o, --output     Tên file PDF (mặc định: theo tiêu đề sách)
    -j, --jobs       Số luồng tải song song (mặc định 8)
    --keep           Giữ lại thư mục ảnh sau khi ghép PDF
    --no-browser     Không dùng trình duyệt ẩn (bỏ qua cách 2 và 3)
    --show-browser   Hiện cửa sổ trình duyệt (để debug cách 2/3)

CÀI ĐẶT (1 lần)
    pip install requests img2pdf pillow
    # Tuỳ chọn, cần cho sách bị mã hoá:
    pip install playwright
    python3 -m playwright install --with-deps chromium

CÁC CÁCH LẤY DANH SÁCH TRANG (thử lần lượt, cách nào được thì dừng)
    1. Đọc config.js (bản mobile trước, rồi desktop)   -> nhanh, sách cũ
    2. Mở trình duyệt ẩn, lấy danh sách đã giải mã     -> sách bị mã hoá
    3. Tự lật trang trong trình duyệt, bắt link ảnh    -> dự phòng
    4. Dò ảnh theo số trang 1.jpg, 2.jpg, ...          -> dự phòng cuối

GHI CHÚ CẬP NHẬT
    Các chỗ có đánh dấu  # [UPDATE]  là chỗ cần sửa khi trang web đổi cấu trúc.
    Khi sửa, nhớ tăng VERSION và ghi vào CHANGELOG bên dưới.

CHANGELOG
    2.0.0  Gộp script AnyFlip cũ + FlipHTML5: hỗ trợ cả 2 trang, thử config
           mobile trước, thêm Playwright cho sách mã hoá, chịu lỗi từng trang,
           ghép PDF bằng img2pdf (nhẹ RAM).
    1.0.0  Bản cũ: chỉ AnyFlip, chỉ đọc mobile/javascript/config.js.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import img2pdf
import requests
from PIL import Image

VERSION = "2.0.0"

# =============================================================================
# CẤU HÌNH — phần lớn các lần cập nhật chỉ cần sửa ở đây
# =============================================================================

# [UPDATE] User-Agent giả lập trình duyệt. Nếu bị chặn 403, thử đổi bản Chrome mới hơn.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

# [UPDATE] Các trang web được hỗ trợ. Thêm tên miền mới vào đây nếu cùng nền tảng
#          (ví dụ một trang "xxxflip.com" dùng chung cấu trúc online.xxx.com/a/b/).
SITES = ("anyflip", "fliphtml5")

# Trang mặc định khi người dùng nhập dạng rút gọn "abc/xyz"
DEFAULT_SITE = "anyflip"

# [UPDATE] Đường dẫn file config.js, thử theo thứ tự.
#          Bản mobile hay KHÔNG bị mã hoá nên để lên đầu (bài học từ script cũ).
CONFIG_PATHS = (
    "mobile/javascript/config.js",
    "javascript/config.js",
)

# [UPDATE] Thư mục chứa ảnh trang. "large" là ảnh nét nhất.
DEFAULT_IMG_FOLDER = "files/large/"
GUESS_FOLDERS = ("files/large/", "files/page/", "files/mobile/")
GUESS_EXTS = (".jpg", ".webp", ".png")

# [UPDATE] Regex nhận diện link ảnh trang khi bắt request mạng (cách 3).
#          Cố ý KHÔNG khớp "files/thumb/" (ảnh thu nhỏ).
IMG_URL_RE = re.compile(r"/files/(large|page|mobile)/[^?#]+\.(jpe?g|png|webp)", re.I)

# [UPDATE] Regex đọc config.js
RE_TITLE = re.compile(r'"bookTitle"\s*:\s*"((?:[^"\\]|\\.){1,300})"')
# Mỗi trang trong config có dạng {"n":["files/large/abc.jpg"], "t":"files/thumb/abc.jpg"}
# hoặc đôi khi "n":"abc.jpg". Regex này bắt cả 2 dạng.
RE_PAGE_N = re.compile(r'"n"\s*:\s*\[?\s*"([^"]+)"')
# Tên ảnh hợp lệ (để loại chuỗi rác/mã hoá)
RE_IMG_NAME = re.compile(r"\.(jpe?g|png|webp)(\?.*)?$", re.I)

# [UPDATE] Đoạn JS chạy trong trình duyệt (cách 2): quét biến toàn cục tìm mảng
#          trang đã được trình đọc giải mã. Nhận diện = mảng các object có khoá "n".
#          Nếu nền tảng đổi tên khoá (ví dụ "n" -> "url"), sửa hàm isPages và dòng return.
JS_FIND_PAGES = r"""
() => {
  const isPages = a => Array.isArray(a) && a.length > 0 && a[0] &&
                       typeof a[0] === 'object' && 'n' in a[0];
  const seen = new Set();
  let pages = null;
  function scan(obj, depth) {
    if (pages || !obj || depth > 4 || seen.has(obj)) return;
    if (typeof obj !== 'object' && typeof obj !== 'function') return;
    if (typeof Node !== 'undefined' && obj instanceof Node) return;
    seen.add(obj);
    if (isPages(obj)) { pages = obj; return; }
    let keys; try { keys = Object.keys(obj); } catch (e) { return; }
    for (const k of keys) {
      let v; try { v = obj[k]; } catch (e) { continue; }
      scan(v, depth + 1);
      if (pages) return;
    }
  }
  scan(window, 0);
  if (!pages) return null;
  return pages.map(p => Array.isArray(p.n) ? p.n[0] : p.n);
}
"""

# Thời gian chờ (giây / mili-giây)
HTTP_TIMEOUT = 30
BROWSER_LOAD_TIMEOUT_MS = 90_000
BROWSER_SCAN_TRIES = 20          # số lần quét tìm danh sách trang (cách 2)
BROWSER_SCAN_DELAY_MS = 1500
FLIP_DELAY_MS = 600              # thời gian chờ mỗi lần lật trang (cách 3)
FLIP_IDLE_LIMIT = 10             # lật N lần liên tiếp không có ảnh mới thì dừng
FLIP_MAX = 3000                  # giới hạn số lần lật trang


# =============================================================================
# TIỆN ÍCH
# =============================================================================

def log(msg: str = "", end: str = "\n") -> None:
    print(msg, end=end, flush=True)


def normalize_base(url: str) -> str:
    """
    Chuẩn hoá mọi dạng link về dạng gốc: https://online.<site>.com/<a>/<b>/

    Nhận được:
      https://online.fliphtml5.com/ksgeo/zerq/#p=1
      https://fliphtml5.com/ksgeo/zerq/
      https://anyflip.com/sdffp/ieyn/basic
      https://online.anyflip.com/sdffp/ieyn/mobile/index.html
      sdffp/ieyn   (rút gọn -> DEFAULT_SITE)
    """
    url = url.strip().split("#")[0].split("?")[0]

    if "://" not in url:
        parts = [p for p in url.split("/") if p]
        if len(parts) != 2:
            raise ValueError(f"Link không hợp lệ: {url}")
        return f"https://online.{DEFAULT_SITE}.com/{parts[0]}/{parts[1]}/"

    # [UPDATE] Nếu nền tảng đổi dạng link, sửa regex này.
    sites = "|".join(SITES)
    m = re.match(rf"https?://(?:www\.)?(?:online\.)?({sites})\.com/([^/]+)/([^/]+)", url, re.I)
    if m:
        site, a, b = m.groups()
        return f"https://online.{site.lower()}.com/{a}/{b}/"

    # Tên miền lạ: giữ nguyên, chỉ bỏ index.html
    url = re.sub(r"(mobile/)?index\.html?$", "", url)
    return url if url.endswith("/") else url + "/"


def safe_filename(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", s).strip(" ._")
    return s[:150]


def make_session(base: str) -> requests.Session:
    s = requests.Session()
    origin = re.match(r"https?://[^/]+", base).group(0)
    # [UPDATE] Nếu ảnh bị 403, có thể server kiểm tra Referer/Origin: chỉnh ở đây.
    s.headers.update({"User-Agent": UA, "Referer": base, "Origin": origin})
    return s


def http_get(session: requests.Session, url: str, retries: int = 4):
    """GET có thử lại. Trả về Response nếu 200, None nếu 403/404 hoặc hết lượt."""
    for i in range(retries):
        try:
            r = session.get(url, timeout=HTTP_TIMEOUT)
            if r.status_code == 200 and r.content:
                return r
            if r.status_code in (403, 404):
                return None
        except requests.RequestException:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def name_to_url(base: str, name: str) -> str:
    """Đổi tên ảnh trong config ('abc.jpg', 'files/large/abc.jpg', link đầy đủ) thành URL."""
    name = str(name).strip().replace("\\/", "/")
    if name.startswith("http"):
        return name
    name = re.sub(r"^(\./|\.\./|/)+", "", name)
    if name.startswith("files/"):
        return base + name
    return base + DEFAULT_IMG_FOLDER + name


def decode_js_string(s: str) -> str:
    try:
        return json.loads(f'"{s}"')
    except Exception:
        return s


# =============================================================================
# CÁCH 1 — đọc config.js
# =============================================================================

def parse_config(text: str):
    """Trả về (danh sách tên ảnh, tiêu đề). Danh sách rỗng nếu bị mã hoá."""
    title = None
    m = RE_TITLE.search(text)
    if m:
        title = decode_js_string(m.group(1)).strip() or None

    # Chỉ tìm trong phần sau "fliphtml5_pages" (nếu có) để tránh bắt nhầm khoá "n" khác
    idx = text.find("fliphtml5_pages")
    section = text[idx:] if idx >= 0 else text

    names = [n for n in RE_PAGE_N.findall(section) if RE_IMG_NAME.search(n)]
    if not names and idx >= 0:
        # Thử lại trên toàn file phòng khi cấu trúc khác
        names = [n for n in RE_PAGE_N.findall(text) if RE_IMG_NAME.search(n)]
    return names, title


def method_config(session: requests.Session, base: str):
    log("→ Cách 1: đọc config.js")
    title = None
    for path in CONFIG_PATHS:
        r = http_get(session, base + path, retries=2)
        if not r:
            log(f"   {path}: không tải được")
            continue
        names, t = parse_config(r.text)
        title = title or t
        if names:
            log(f"   {path}: OK, {len(names)} trang")
            return [name_to_url(base, n) for n in names], title
        log(f"   {path}: bị mã hoá / không có danh sách trang")
    return [], title


# =============================================================================
# CÁCH 2 + 3 — trình duyệt ẩn (Playwright)
# =============================================================================

def method_browser(base: str, show: bool = False):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("→ Bỏ qua cách 2/3: chưa cài Playwright")
        log("   pip install playwright && python3 -m playwright install --with-deps chromium")
        return [], None

    captured: list[str] = []
    title = None

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=not show)
        except Exception as e:
            log(f"→ Không mở được Chromium: {e}")
            log("   Chạy: python3 -m playwright install --with-deps chromium")
            return [], None

        page = browser.new_page(user_agent=UA, viewport={"width": 1400, "height": 1000})

        # Ghi lại mọi request ảnh trang (dùng cho cách 3)
        def on_request(req):
            u = req.url.split("?")[0]
            if IMG_URL_RE.search(u) and u not in captured:
                captured.append(u)

        page.on("request", on_request)

        # ---------------- Cách 2 ----------------
        log("→ Cách 2: mở trình duyệt, lấy danh sách trang đã giải mã")
        try:
            page.goto(base, wait_until="networkidle", timeout=BROWSER_LOAD_TIMEOUT_MS)
        except Exception as e:
            log(f"   cảnh báo khi tải trang: {e}")

        try:
            title = page.title() or None
        except Exception:
            pass

        names = None
        for _ in range(BROWSER_SCAN_TRIES):
            try:
                names = page.evaluate(JS_FIND_PAGES)
            except Exception:
                names = None
            if names:
                break
            page.wait_for_timeout(BROWSER_SCAN_DELAY_MS)

        if names:
            names = [n for n in names if n]
            browser.close()
            log(f"   OK: {len(names)} trang")
            return [name_to_url(base, n) for n in names], title

        # ---------------- Cách 3 ----------------
        # Lưu ý: thứ tự ảnh bắt được = thứ tự trình duyệt tải, đa số đúng thứ tự trang
        # nhưng có thể lệch nếu trình đọc tải trước (preload) không theo thứ tự.
        log("   không tìm thấy -> Cách 3: tự lật trang và bắt link ảnh (hơi lâu)")
        try:
            page.mouse.click(700, 500)  # focus vào sách để nhận phím
        except Exception:
            pass

        # [UPDATE] Phím lật trang. Nếu trình đọc đổi phím, sửa ở đây.
        idle, last = 0, len(captured)
        for _ in range(FLIP_MAX):
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(FLIP_DELAY_MS)
            if len(captured) == last:
                idle += 1
                if idle >= FLIP_IDLE_LIMIT:
                    break
            else:
                idle, last = 0, len(captured)
                log(f"   đã bắt {len(captured)} ảnh...", end="\r")
        browser.close()

    large = [u for u in captured if "/files/large/" in u]
    urls = large or captured
    log(f"\n   bắt được {len(urls)} ảnh")
    return urls, title


# =============================================================================
# CÁCH 4 — dò theo số trang
# =============================================================================

def method_guess(session: requests.Session, base: str):
    log("→ Cách 4: dò ảnh theo số trang (1.jpg, 2.jpg, ...)")
    for folder in GUESS_FOLDERS:
        for ext in GUESS_EXTS:
            if not http_get(session, f"{base}{folder}1{ext}", retries=1):
                continue
            urls, i = [], 1
            while True:
                u = f"{base}{folder}{i}{ext}"
                try:
                    r = session.head(u, timeout=HTTP_TIMEOUT)
                except requests.RequestException:
                    break
                if r.status_code != 200:
                    break
                urls.append(u)
                i += 1
            log(f"   OK: mẫu {folder}N{ext}, {len(urls)} trang")
            return urls
    log("   không tìm thấy")
    return []


# =============================================================================
# TẢI ẢNH
# =============================================================================

def download_all(session: requests.Session, urls: list[str], out_dir: str, jobs: int):
    """Tải song song. Trả về list đường dẫn theo đúng thứ tự trang (None = lỗi)."""
    os.makedirs(out_dir, exist_ok=True)

    def job(idx: int, url: str):
        ext = os.path.splitext(url.split("?")[0])[1].lower() or ".jpg"
        path = os.path.join(out_dir, f"{idx:04d}{ext}")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return idx, path  # đã tải ở lần chạy trước
        r = http_get(session, url)
        if not r:
            return idx, None
        with open(path, "wb") as f:
            f.write(r.content)
        return idx, path

    results: dict[int, str | None] = {}
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(job, i, u) for i, u in enumerate(urls, 1)]
        for n, fut in enumerate(as_completed(futures), 1):
            idx, path = fut.result()
            results[idx] = path
            log(f"   tải {n}/{len(urls)}", end="\r")
    log()
    return [results[i] for i in sorted(results)]


# =============================================================================
# GHÉP PDF
# =============================================================================

def ensure_jpeg(path: str) -> str:
    """
    img2pdf nhúng JPEG trực tiếp (không nén lại, nhẹ RAM).
    Ảnh khác (webp, png có alpha, hoặc file .jpg nhưng thực ra là webp) -> chuyển sang JPEG.
    """
    try:
        with Image.open(path) as im:
            if im.format == "JPEG" and im.mode in ("RGB", "L", "CMYK"):
                return path
            out = os.path.splitext(path)[0] + ".conv.jpg"
            if os.path.exists(out):
                return out
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                im = bg
            else:
                im = im.convert("RGB")
            im.save(out, "JPEG", quality=95)
            return out
    except Exception as e:
        log(f"   ⚠ bỏ qua ảnh hỏng {path}: {e}")
        return ""


def build_pdf(paths: list[str], pdf_path: str) -> int:
    ready = [p for p in (ensure_jpeg(p) for p in paths) if p]
    if not ready:
        raise RuntimeError("Không có ảnh hợp lệ để ghép PDF.")
    try:
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(ready))
    except Exception as e:
        # Dự phòng: dùng Pillow (tốn RAM hơn nhưng chịu được ảnh lạ)
        log(f"   img2pdf lỗi ({e}), chuyển sang Pillow...")
        imgs = [Image.open(p).convert("RGB") for p in ready]
        imgs[0].save(pdf_path, "PDF", save_all=True, append_images=imgs[1:])
    return len(ready)


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(
        description=f"Tải sách FlipHTML5 / AnyFlip thành PDF (v{VERSION})")
    ap.add_argument("url", help="Link sách hoặc dạng rút gọn 'abc/xyz'")
    ap.add_argument("-o", "--output", help="Tên file PDF")
    ap.add_argument("-j", "--jobs", type=int, default=8, help="Số luồng tải (mặc định 8)")
    ap.add_argument("--keep", action="store_true", help="Giữ lại thư mục ảnh")
    ap.add_argument("--no-browser", action="store_true", help="Không dùng trình duyệt ẩn")
    ap.add_argument("--show-browser", action="store_true", help="Hiện trình duyệt (debug)")
    args = ap.parse_args()

    try:
        base = normalize_base(args.url)
    except ValueError as e:
        log(f"❌ {e}")
        return 1

    log(f"flipbook-to-pdf v{VERSION}")
    log(f"Sách: {base}\n")
    session = make_session(base)

    # ---- Lấy danh sách trang (thử lần lượt) ----
    urls, title = method_config(session, base)

    if not urls and not args.no_browser:
        urls, t2 = method_browser(base, show=args.show_browser)
        title = title or t2

    if not urls:
        urls = method_guess(session, base)

    if not urls:
        log("\n❌ Không lấy được danh sách trang.")
        log("   Thử: --show-browser để xem trình duyệt, hoặc gửi log để chỉnh script.")
        return 1

    # ---- Đặt tên ----
    slug = "_".join(base.rstrip("/").split("/")[-2:])
    pdf_name = args.output or f"{safe_filename(title) or slug}.pdf"
    img_dir = f"_imgs_{slug}"
    log(f"\nTiêu đề: {title or '(không rõ)'}")
    log(f"Số trang: {len(urls)}")

    # ---- Tải ảnh ----
    log(f"\nĐang tải ảnh vào {img_dir}/")
    paths = download_all(session, urls, img_dir, args.jobs)

    failed = [i + 1 for i, p in enumerate(paths) if not p]
    ok = [p for p in paths if p]
    if failed:
        shown = ", ".join(map(str, failed[:30])) + (" ..." if len(failed) > 30 else "")
        log(f"⚠ {len(failed)} trang lỗi: {shown}")
        log("  Chạy lại đúng lệnh này để tải bù (ảnh đã có sẽ được bỏ qua).")
    if not ok:
        log("❌ Không tải được ảnh nào (có thể bị chặn 403).")
        return 1

    # ---- Ghép PDF ----
    log("Đang ghép PDF...")
    try:
        n = build_pdf(ok, pdf_name)
    except Exception as e:
        log(f"❌ Lỗi ghép PDF: {e}")
        return 1

    size_mb = os.path.getsize(pdf_name) / (1024 * 1024)
    log(f"✅ Xong: {pdf_name} ({n} trang, {size_mb:.1f} MB)")

    # Chỉ xoá thư mục ảnh khi đầy đủ, để lần sau còn tải bù
    if not args.keep and not failed:
        shutil.rmtree(img_dir, ignore_errors=True)
    elif failed:
        log(f"  (Giữ lại {img_dir}/ vì còn trang lỗi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())