# Anyflip to PDF Downloader

**Language:** **English** · [Tiếng Việt](README.vi.md)

Download a public [AnyFlip](https://anyflip.com) flipbook to a single PDF from the command line.

This tool does not bypass passwords or break DRM — it only automates fetching the page images that your browser can already render for you.

> **Scope:** Works with public books only (URLs ending in `/basic` or similar). Password-protected / DRM-locked books are not supported. Please respect the copyright of authors and publishers.

---

## 🖥️ For non-technical users (Windows)

### Step 1 — Install Python

1. Go to https://www.python.org/downloads/ and click the big yellow **Download Python** button (version 3.10 or newer).
2. Run the installer. **On the first screen, tick the `Add Python to PATH` checkbox**, then click **Install Now**.
3. Wait for it to finish, then click **Close**.

### Step 2 — Get this tool

1. Open the [GitHub page for this repo](https://github.com/havertz2110/Anyflip-to-PDF-downloader).
2. Click the green **Code** button → **Download ZIP**.
3. Extract the ZIP to your Desktop (e.g. `C:\Users\<your-name>\Desktop\Anyflip-to-PDF-downloader-main`).

### Step 3 — Install the required libraries

1. Press `Win + R`, type `cmd`, press Enter to open Command Prompt.
2. Type the following line and press Enter (copy-paste works):
   ```
   pip install requests pillow
   ```
3. Wait until you see `Successfully installed …`.

### Step 4 — Download a book

1. In the same Command Prompt, `cd` into the extracted folder:
   ```
   cd %USERPROFILE%\Desktop\Anyflip-to-PDF-downloader-main
   ```
2. Run the tool, replacing `<book-URL>` with the AnyFlip URL you want to download:
   ```
   python anyflip_to_pdf.py <book-URL>
   ```
   Example:
   ```
   python anyflip_to_pdf.py https://anyflip.com/sdffp/ieyn/basic
   ```
3. After a few seconds, the PDF appears in the current folder. The filename is derived from the book's title.

---

## 🍎 macOS users

1. Open **Terminal** (Cmd+Space → type `Terminal`).
2. Install Python (if you don't have it yet) via [Homebrew](https://brew.sh):
   ```bash
   brew install python
   ```
3. Clone the repo and install dependencies:
   ```bash
   git clone https://github.com/havertz2110/Anyflip-to-PDF-downloader.git
   cd Anyflip-to-PDF-downloader
   pip3 install requests pillow
   ```
4. Run:
   ```bash
   python3 anyflip_to_pdf.py https://anyflip.com/sdffp/ieyn/basic
   ```

---

## ⚙️ Advanced options

```
python anyflip_to_pdf.py <url> [--output my-book.pdf] [--workers 20] [--keep-webp]
```

| Flag | Meaning |
|---|---|
| `-o, --output` | Output PDF path (default: derived from the book title). |
| `-w, --workers` | Number of parallel downloads (default 12, raise it on a fast connection). |
| `--keep-webp` | Keep the individual per-page webp images instead of deleting them after assembly. |

Instead of a full URL you can also pass the short `<code>/<book>` form, for example:
```
python anyflip_to_pdf.py sdffp/ieyn
```

---

## 🛠️ How it works (technical notes)

1. AnyFlip stores each book's configuration in a public `config.js`:
   `https://online.anyflip.com/<code>/<book>/mobile/javascript/config.js`
2. That file contains an ordered `fliphtml5_pages` array, where every page is listed by its content hash:
   ```
   {"n":["../files/large/<md5>.webp"], "t":"../files/thumb/<md5>.webp"}
   ```
3. The script parses that array in order, downloads each page in parallel from
   `https://online.anyflip.com/<code>/<book>/files/large/<md5>.webp`,
   then uses [Pillow](https://pillow.readthedocs.io) to assemble all pages into a single PDF.

No cookies, tokens, or login are needed — the content is already public.

---

## ❓ FAQ

**Q: Can it download password-protected books?**
No. A protected book returns a password-challenge page instead of a valid `config.js`, so the script errors out.

**Q: Is downloading legal?**
Downloading a public web page by itself is not a technical offence, but **redistributing copyrighted material is**. Only use this on books you have the right to read/archive (books you uploaded yourself, public-domain material, free resources the author has authorised for download…).

**Q: `pip` is not recognized?**
You didn't tick **Add Python to PATH** during Python install. Quickest fix: uninstall Python and reinstall with the checkbox ticked. Alternatively, run `py -m pip install requests pillow` instead of `pip install …`.

**Q: Download fails halfway through?**
Re-run the same command — the script skips pages already downloaded and only fetches the missing ones (temporary `.webp` files live in the `pages/` directory).

**Q: What about image quality?**
The script grabs the `large` variant (the highest-quality version the AnyFlip viewer itself serves). Quality is usually good enough for reading but not as sharp as a publisher's original source file.

---

## 📜 License

[MIT License](LICENSE) — free to use for personal, educational, and other lawful purposes.
