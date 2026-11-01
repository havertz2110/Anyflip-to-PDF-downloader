# pip install requests img2pdf
import os
import re
import glob
import time
import requests
import img2pdf
from concurrent.futures import ThreadPoolExecutor

HTML_FILE = "scribd.html"     # file HTML bạn đã lưu
OUT_DIR = "anh_trang"         # thư mục lưu ảnh
PDF_FILE = "book.pdf"         # tên file PDF đầu ra
WORKERS = 6                   # số luồng tải song song

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Referer": "https://www.scribd.com/",
}

os.makedirs(OUT_DIR, exist_ok=True)
html = open(HTML_FILE, encoding="utf-8").read()

# ---------- 1. Lấy token và danh sách trang ----------
m = re.search(r"token=([A-Za-z0-9._\-]+)", html)
TOKEN = m.group(1) if m else None
print("Token:", "có" if TOKEN else "KHÔNG tìm thấy")

direct = {int(n): u for n, u in re.findall(
    r'id="page(\d+)".*?orig="([^"]+)"', html, re.S)}

pages = [(int(n), u) for n, u in re.findall(
    r'pageNum:\s*(\d+)\s*,.*?contentUrl:\s*"([^"]+)"', html, re.S)]
print(f"Tìm thấy {len(pages)} trang")


def fix_url(url):
    url = url.replace("\\/", "/")
    url = re.sub(r"^https?://html\.scribd\.com/", "https://html.scribdassets.com/", url)
    url = url.split("?")[0]
    if TOKEN:
        url += "?token=" + TOKEN
    return url


def get(url, retries=4):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r
            print(f"  HTTP {r.status_code}: {url[:90]}")
        except requests.RequestException as e:
            print(f"  Lỗi: {e}")
        time.sleep(2 * (i + 1))
    return None


def image_urls_for_page(num, jsonp_url):
    r = get(fix_url(jsonp_url))
    if r:
        found = re.findall(r'orig=\\?"(https?://[^"\\]+)', r.text)
        if found:
            return found
    return [direct[num]] if num in direct else []


# ---------- 2. Tải ảnh ----------
def process(page):
    num, jsonp_url = page
    urls = image_urls_for_page(num, jsonp_url)
    if not urls:
        print(f"[{num}] không tìm thấy ảnh")
        return
    for i, u in enumerate(urls):
        ext = os.path.splitext(u.split("?")[0])[1] or ".jpg"
        suffix = f"_{i + 1}" if len(urls) > 1 else ""
        path = os.path.join(OUT_DIR, f"trang_{num:03d}{suffix}{ext}")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        r = get(fix_url(u))
        if r:
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"[{num}] OK")
        else:
            print(f"[{num}] THẤT BẠI")


with ThreadPoolExecutor(WORKERS) as ex:
    list(ex.map(process, pages))

# ---------- 3. Kiểm tra trang thiếu ----------
downloaded = {int(re.search(r"trang_(\d+)", f).group(1))
              for f in glob.glob(os.path.join(OUT_DIR, "trang_*"))}
missing = [n for n, _ in pages if n not in downloaded]
if missing:
    print(f"\nThiếu {len(missing)} trang: {missing}")
    print("Chạy lại script để tải bù (trang đã có sẽ được bỏ qua).")

# ---------- 4. Ghép PDF ----------
files = sorted(
    glob.glob(os.path.join(OUT_DIR, "trang_*")),
    key=lambda f: [int(x) for x in re.findall(r"\d+", os.path.basename(f))],
)
if files:
    with open(PDF_FILE, "wb") as f:
        f.write(img2pdf.convert(files))
    print(f"\nĐã tạo {PDF_FILE} với {len(files)} trang.")
else:
    print("Không có ảnh nào để ghép PDF.")