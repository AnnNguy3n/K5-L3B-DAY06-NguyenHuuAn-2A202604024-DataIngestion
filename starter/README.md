# Starter · PostgreSQL + pgvector

Bộ khởi động **tùy chọn** cho lab cá nhân. Docker Compose tạo PostgreSQL + pgvector local; `ingestion.py` và `chunking.py` đã đọc PDF, trích xuất chữ trong ảnh và xuất chunk; embedding, vector store, đánh giá và `run.py` còn **TODO**. Vẫn có thể chọn Qdrant, Chroma hoặc vector store tương đương theo [GUIDE.md](../GUIDE.md).

## Cấu trúc

```text
starter/
├── docker-compose.yml     # PostgreSQL 16 + pgvector, chỉ mở cổng local
├── init.sql               # bật extension khi tạo database mới
├── requirements.txt       # psycopg, pypdf, Pillow và python-dotenv
├── .env.example           # cấu hình mẫu; copy thành .env
├── scripts/check_setup.py # kiểm tra kết nối và extension (đã chạy được)
├── src/
│   ├── models.py          # cấu trúc dữ liệu mẫu
│   ├── ingestion.py       # đọc text + chữ trong ảnh, chuẩn hóa
│   ├── chunking.py        # fixed-size / theo đoạn, ID ổn định
│   ├── embeddings.py      # TODO: chọn model API hoặc local
│   ├── store.py           # TODO: lưu vector, metadata và filter
│   ├── evaluation.py      # TODO: chấm truy xuất, lưu trace
│   └── run.py             # TODO: kết nối các bước thành pipeline
├── data/                  # bạn tự chuẩn bị corpus được phép sử dụng
└── results/               # lưu kết quả của bạn
```

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

## 2. Chọn embedding model

Điền key tương ứng trong `.env` nếu dùng OpenRouter, OpenAI hoặc Gemini; **không commit `.env`**. Model local không cần API key. `requirements.txt` chỉ có dependencies cơ bản: tự cài SDK hoặc thư viện local phù hợp với model bạn chọn và ghi lại version/lệnh cài trong báo cáo. Ghi tên model và số chiều; dùng cùng model cho toàn bộ chiến lược và vector query tương thích vector document.

## 3. Hoàn thiện pipeline

1. Đặt corpus vào `data/` hoặc cung cấp manifest/hướng dẫn truy cập. Đọc [GUIDE.md](../GUIDE.md) về **30 trang nội dung**, quyền dữ liệu và metadata.
2. Hoàn thiện từng hàm TODO trong `src/`. Lưu ID tài liệu, nguồn, trang/vị trí và ít nhất một trường filter có ích.
3. Xây ít nhất ba cấu hình; ví dụ A fixed-size, B theo đoạn, C như B nhưng có filter. Cần cùng corpus, model và benchmark; nạp lại không nhân đôi và xử lý chunk cũ khi dữ liệu đổi.
4. Tự viết ít nhất 20 câu hỏi kèm evidence, tách dev/test trước khi thử theo [BENCHMARK.md](../BENCHMARK.md). Lưu trace top-3 và báo cáo đủ năm tiêu chí.
5. Sau khi hoàn thiện, chạy `python -m src.run` từ thư mục `starter/`. Trước khi làm TODO, lệnh này **chủ động báo `NotImplementedError`**.

Lưu code, cấu hình, kết quả và lệnh chạy để người chấm tái lập; không commit key, dữ liệu mật hoặc dữ liệu không có quyền chia sẻ.


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

A/B chưa áp dụng filter. C dùng **chính `chunks_B.jsonl`**, áp dụng
`question.filter` khi truy vấn có filter; bước truy vấn thuộc phần retrieval chưa
hiện thực. Các kích thước là tham số khởi đầu, chưa tối ưu trên dev. Có thể đổi
`--size 500 --overlap 50 --max-size 1000 --long-overlap 100`; không dùng test để chọn tham số.
