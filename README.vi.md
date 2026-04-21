# Anyflip to PDF Downloader

**Ngôn ngữ:** **Tiếng Việt** · [English](README.md)

Tải một cuốn sách công khai trên [AnyFlip](https://anyflip.com) về máy dưới dạng file PDF, chỉ với một dòng lệnh.

Công cụ này không phá mật khẩu, không bẻ khoá DRM — nó chỉ tự động hoá việc tải những trang mà trình duyệt của bạn vốn đã có thể xem được.

> **Scope:** Chỉ dùng với sách ở chế độ public (URL kết thúc bằng `/basic` hoặc tương tự). Không hỗ trợ sách đặt password/DRM. Hãy tôn trọng bản quyền của tác giả/nhà xuất bản khi sử dụng.

---

## 🖥️ Dành cho người không biết code (Windows)

### Bước 1 — Cài Python

1. Mở trang https://www.python.org/downloads/ → nhấn nút vàng **Download Python** (lấy bản mới nhất, 3.10 trở lên).
2. Chạy file `.exe` vừa tải. **Trong màn hình đầu tiên, tick vào ô `Add Python to PATH`** rồi bấm **Install Now**.
3. Chờ cài xong, bấm **Close**.

### Bước 2 — Tải công cụ

1. Vào [trang GitHub của repo này](https://github.com/havertz2110/Anyflip-to-PDF-downloader).
2. Nhấn nút xanh **Code** → **Download ZIP**.
3. Giải nén file ZIP ra Desktop (ví dụ: `C:\Users\<tên-bạn>\Desktop\Anyflip-to-PDF-downloader-main`).

### Bước 3 — Cài thư viện cần thiết

1. Nhấn `Win + R`, gõ `cmd`, bấm Enter để mở Command Prompt.
2. Gõ lệnh sau rồi Enter (copy-paste cả dòng):
   ```
   pip install requests pillow
   ```
3. Đợi đến khi hiện `Successfully installed …`.

### Bước 4 — Tải sách

1. Vẫn ở Command Prompt, `cd` vào thư mục vừa giải nén:
   ```
   cd %USERPROFILE%\Desktop\Anyflip-to-PDF-downloader-main
   ```
2. Chạy lệnh, thay `<URL-sách>` bằng URL AnyFlip bạn muốn tải:
   ```
   python anyflip_to_pdf.py <URL-sách>
   ```
   Ví dụ:
   ```
   python anyflip_to_pdf.py https://anyflip.com/sdffp/ieyn/basic
   ```
3. Đợi vài giây, file PDF sẽ xuất hiện ngay trong thư mục đang đứng. Tên file lấy theo tiêu đề sách.

---

## 🍎 Dành cho người dùng macOS

1. Mở **Terminal** (Cmd+Space → gõ `Terminal`).
2. Cài Python (nếu chưa có) bằng [Homebrew](https://brew.sh):
   ```bash
   brew install python
   ```
3. Tải repo và cài thư viện:
   ```bash
   git clone https://github.com/havertz2110/Anyflip-to-PDF-downloader.git
   cd Anyflip-to-PDF-downloader
   pip3 install requests pillow
   ```
4. Chạy:
   ```bash
   python3 anyflip_to_pdf.py https://anyflip.com/sdffp/ieyn/basic
   ```

---

## ⚙️ Tuỳ chọn nâng cao

```
python anyflip_to_pdf.py <url> [--output my-book.pdf] [--workers 20] [--keep-webp]
```

| Tuỳ chọn | Ý nghĩa |
|---|---|
| `-o, --output` | Đường dẫn file PDF xuất ra (mặc định: lấy theo tiêu đề sách). |
| `-w, --workers` | Số luồng tải song song (mặc định 12, tăng lên nếu mạng khoẻ). |
| `--keep-webp` | Giữ lại ảnh webp gốc của từng trang thay vì xoá sau khi gộp. |

Ngoài URL đầy đủ, bạn cũng có thể truyền vào dạng rút gọn `<code>/<book>`, ví dụ:
```
python anyflip_to_pdf.py sdffp/ieyn
```

---

## 🛠️ Cách hoạt động (phần kỹ thuật)

1. AnyFlip lưu cấu hình mỗi cuốn sách ở file `config.js` công khai:
   `https://online.anyflip.com/<code>/<book>/mobile/javascript/config.js`
2. Trong đó có mảng `fliphtml5_pages` liệt kê từng trang dưới dạng hash nội dung:
   ```
   {"n":["../files/large/<md5>.webp"], "t":"../files/thumb/<md5>.webp"}
   ```
3. Script parse mảng này theo thứ tự, tải song song từng file `.webp` tại
   `https://online.anyflip.com/<code>/<book>/files/large/<md5>.webp`,
   rồi dùng [Pillow](https://pillow.readthedocs.io) ghép toàn bộ thành một file PDF duy nhất.

Không có bước nào cần cookie, token, hay đăng nhập — vì nội dung đã là public.

---

## ❓ FAQ

**Hỏi: Tải được sách có password không?**
Không. Sách có password sẽ trả về trang yêu cầu nhập password thay vì `config.js` hợp lệ — script sẽ báo lỗi.

**Hỏi: Tải có vi phạm pháp luật không?**
Bản thân việc tải một trang web công khai không phải hành vi kỹ thuật trái phép, nhưng **phân phối lại nội dung có bản quyền là vi phạm**. Chỉ sử dụng với sách bạn có quyền đọc/sao lưu (do chính bạn upload, sách public-domain, tài liệu miễn phí được tác giả cho phép tải…).

**Hỏi: Lệnh `pip` báo `not recognized`?**
Bạn chưa tick **Add Python to PATH** khi cài Python. Cách nhanh nhất: gỡ Python rồi cài lại, lần này nhớ tick ô đó. Hoặc dùng `py -m pip install requests pillow` thay vì `pip install …`.

**Hỏi: Tải được một nửa thì lỗi mạng?**
Chạy lại lệnh cũ — script sẽ bỏ qua những trang đã tải thành công và chỉ tải nốt phần còn thiếu (các file `.webp` tạm nằm trong thư mục `pages/`).

**Hỏi: Chất lượng ảnh thế nào?**
Script tải bản `large` (bản đẹp nhất AnyFlip serve cho viewer). Chất lượng thường đủ để đọc nhưng không bằng file gốc của publisher.

---

## 📜 Giấy phép

[MIT License](LICENSE) — dùng tự do cho mục đích cá nhân, học thuật và các use-case hợp pháp khác.
