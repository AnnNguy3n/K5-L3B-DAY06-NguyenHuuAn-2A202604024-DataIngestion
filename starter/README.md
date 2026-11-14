# Starter · PostgreSQL + pgvector

Starter dùng PostgreSQL 16, pgvector và Ollama local. Checkpoint 5 dùng lại hai file chunk đã xuất. Phần đánh giá chất lượng retrieval thuộc checkpoint tiếp theo.

## 1. Cài và kiểm tra database

Cần Docker Desktop hoặc Docker Engine + Compose, Python **3.11–3.14**, và mạng để tải image/dependencies lần đầu. Các lệnh sau chạy từ thư mục `starter/`:

```bash
cd starter
python3 -m venv .venv
```

Kích hoạt `.venv`: macOS/Linux dùng `source .venv/bin/activate`; Windows PowerShell dùng `.venv\Scripts\Activate.ps1`. Sau đó:

```bash
python -m pip install -r requirements.txt
# macOS/Linux: cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

Kỳ vọng: hiện tên database, phiên bản PostgreSQL và pgvector, sau đó `Setup OK`. Đây **chỉ là kiểm tra hạ tầng**, không phải kết quả benchmark. Docker dùng cổng `127.0.0.1:55433` và mật khẩu cố định **chỉ dùng local cho lab**; nếu cổng bận, sửa đồng thời port trong `docker-compose.yml` và `DATABASE_URL` trong `.env`. `init.sql` chỉ chạy khi volume mới được tạo; nếu database sẵn có chưa bật extension, xem log Docker và kiểm tra cấu hình thay vì xóa volume chứa dữ liệu.

Dừng container nhưng giữ dữ liệu:

```bash
docker compose -p day6_student_starter stop
```

## 2. Lưu vector và chạy dev

Bật Ollama local ở `127.0.0.1:11434`. Kiểm tra `ollama list` có đúng tag `embeddinggemma-2:740m-mxfp8`. Adapter dùng HTTP qua thư viện chuẩn Python, đọc chiều native từ `/api/tags`, dò hai vector qua `/api/embed` và kiểm tra chiều từng vector. Lần chạy này dùng Ollama 0.40.16. Query dùng tiền tố `task: search result | query: `, document dùng `title: none | text: `. Không truyền tham số rút gọn chiều. Hai tiền tố khớp với cấu hình retrieval đóng gói trong model. [Model card](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2)

Sau bước cài đặt ở trên, chạy từ **thư mục gốc repo** với hai file `starter/results/chunks_{A,B}.jsonl` đã chốt.

```bash
starter/.venv/bin/python -m starter.src.run build --label initial
starter/.venv/bin/python -m starter.src.run build --label reload
starter/.venv/bin/python -m starter.src.run dev --label restart
starter/.venv/bin/python -m starter.scripts.check_reingestion
```

Mỗi lệnh build nạp cả hai snapshot trong một transaction, cập nhật theo khóa (strategy, chunk_id) và xóa ID đã biến mất ở từng snapshot. C đọc trực tiếp các hàng B. Với corpus nhỏ, SQL lọc JSONB trước khi lấy ba hàng có cosine similarity cao nhất, dùng chunk ID để phân xử đồng điểm. Mỗi câu dev được embed một lần rồi dùng chung cho A/B/C. Lệnh dev chỉ đọc bảng đã lưu. Lệnh cuối kiểm tra thay đổi dữ liệu trong bảng tạm của phiên riêng.

Trong `results/`, mỗi lần chạy pipeline ghi lại `dev_top3.jsonl` và một `checkpoint5_<label>.json`. So sánh `trace_sha256` giữa ba lần chạy và với SHA-256 của trace. Mỗi dòng `stored` lần lượt ghi chiến lược vật lý, số hàng, số ID phân biệt, chiều nhỏ nhất và lớn nhất trong database. Thời gian dùng giây. Chế độ dev và build đều chỉ truy vấn split dev.

## 4. Xuất trang và chunk A/B

Chạy từ **thư mục gốc repository** (để import được cả `starter` và module
`scripts/figure_extraction.py` dùng chung; không copy riêng `starter/`):

```bash
starter/.venv/bin/python -m starter.src.prepare
starter/.venv/bin/python -m unittest discover -s tests -v
```

Lệnh đọc đúng các trang vật lý được chọn trong `data/manifest.json`, xác minh
SHA-256 PDF, giữ `section`, `printed_page`, ngôn ngữ và loại tài liệu. Hàm
`load_pdf(path, document_id, source)` mặc định đọc tất cả các trang; truyền
`page_numbers`, `page_metadata`, `errors=[]`, `stats={}` khi cần chọn trang và
thu thập chẩn đoán. Số trang vật lý bắt đầu từ 1.

Chữ PDF lấy bằng pypdf; chữ/nhãn và mô tả ảnh nhúng dùng cùng `FigureExtractor`
và `merge_figures` như `scripts/read_corpus.py`. Cần Ollama local với model vision
`mimo-v2.6:9b-mxfp8`. Cache mặc định là `data/processed/pages.jsonl`: chỉ tái sử dụng
khi model digest, ảnh, ngữ cảnh, prompt và cấu hình trùng khớp. Cache vẫn cần
Ollama để xác thực model. Có thể đổi `--cache`, `--model`, `--ollama-url`,
`--timeout`. Đây là vision trên ảnh nhúng, không render toàn trang để nhận dạng
các hình vẽ vector. Nếu vision lỗi, giữ text PDF, ghi lỗi ảnh và trả exit code 1.

Chuẩn hóa NFC và khoảng trắng, nối dòng bị ngắt; giữ dòng trống và heading làm ranh giới
đoạn. Nhận diện heading Markdown (`#`–`######`), đánh số, IN HOA và Title Case
ngắn (tối đa 120 ký tự/12 từ đối với heading plain text). Đây là heuristic từ text,
không dựa vào font PDF; heading viết kiểu câu thường có thể không được nhận diện. Loại footer đã biết và references/attributions của corpus khi có metadata
trang in. Nội dung ảnh được ghép tại caption, hoặc cuối trang nếu không định vị
được. Bản ghi trang giữ `text_only`, `figures`, `blocks` trong `metadata` để kiểm tra.

Đầu ra được ghi đè mỗi lần chạy trong `starter/results/`:

- `pages.jsonl`: trang chuẩn hóa, gồm nội dung ảnh và nguồn truy vết.
- `ingestion_errors.jsonl`: lỗi nguồn, text, ảnh hoặc trang rỗng; file 0 byte nếu không lỗi.
- `chunks_A.jsonl`: cửa sổ 500 ký tự, overlap 50.
- `chunks_B.jsonl`: chia theo heading, tối đa 1.000 ký tự. Không coi nhãn trong khối ảnh và ô dưới caption bảng là heading. Heading liên tiếp được giữ cùng nội dung phía sau. Các mục liền kề đều ngắn dưới 1/3 giới hạn có thể ghép nếu vừa giới hạn; metadata `headings` lưu tất cả tiêu đề, `heading` là tiêu đề cuối trong danh sách (không phải filter thay thế cho `section`).
- Đoạn quá 1.000 ký tự được chia cửa sổ cố định 1.000 ký tự, overlap chính xác 100 ký tự (bước 900), chỉ trong đoạn dài đó. Heading đứng trước được giữ cùng đoạn đầu. Các đoạn ngắn vẫn được gom theo cấu trúc, không overlap qua đoạn khác, heading khác hoặc trang khác. Cửa sổ cuối có thể ngắn; không cân bằng lại và không đổi điểm cắt theo câu/từ. Metadata `overlap_char_count`, `split_scope_start`, `split_scope_end` ghi vùng overlap và phạm vi đoạn dài.
- `ingestion_summary.json`: tổng trang được chọn, trang lưu, trang rỗng, số ảnh, số lỗi (kể cả 0), cấu hình và phân bố độ dài chunk (`chunk_size_stats`).

Mọi chunk nằm trong một trang, giữ `chunk_id`, `document_id`, `source`, `page`,
`text`, cùng metadata filter `section` (và `language`, `document_type`). Offset
`char_start`, `char_end` trỏ vào text chuẩn hóa của trang. ID SHA-256 dựa trên
nguồn, tài liệu, trang, cấu hình có version và vị trí; chạy lại cùng đầu vào không
nhân đôi. Khi nạp vector sau này, upsert ID hiện có và xóa chunk cũ không còn
trong lần xuất mới.

A và B truy vấn toàn bộ chunk của từng chiến lược. C dùng cùng chunk/vector B và lọc trong SQL theo metadata của câu hỏi.
