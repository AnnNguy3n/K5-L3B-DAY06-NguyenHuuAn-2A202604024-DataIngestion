# Đọc corpus theo manifest

Chạy từ thư mục gốc repo (Python 3.11–3.14):

```bash
python3 -m pip install -r scripts/requirements.txt
ollama serve  # chỉ cần nếu Ollama chưa chạy; hoặc mở ứng dụng Ollama
```

Trong terminal khác, chạy:

```bash
python3 scripts/read_corpus.py
```

Script đọc **32 trang được chọn** trong `data/manifest.json`, không đọc toàn bộ
219 trang vào corpus. Đường dẫn PDF trong manifest tính từ thư mục gốc repo.
Có thể đổi đầu vào/đầu ra bằng `--manifest PATH --output-dir PATH`.
Model mặc định là `mimo-v2.6:9b-mxfp8` đã tải trong Ollama. Có thể đổi bằng
`--model NAME`, `--ollama-url http://127.0.0.1:11434` và `--timeout 300` (giây
cho mỗi request). Chỉ chấp nhận địa chỉ loopback; script không tải model hoặc
gửi ảnh lên cloud. Kiểm tra model quảng bá capability `vision` trước khi gọi.

Kết quả UTF-8 tại `data/processed/`:

- `pages.jsonl`: mỗi dòng JSON ứng với một trang, chứa `raw_text` nguyên bản
  do pypdf đọc được, `text_only` đã chuẩn hóa, và `text` hợp nhất với nội dung
  hình. `blocks` giữ thứ tự text/figure; `figures` giữ kết quả model, prompt,
  hash ảnh/model và usage. Có ID tài liệu/trang,
  nguồn, `section`, số ký tự và hash. Dấu xuống dòng được JSON escape;
  dùng `json.loads()` để khôi phục.
- `errors.jsonl`: lỗi theo nguồn/trang; file rỗng nếu không có lỗi. Nếu đọc được
  text nhưng kiểm tra trang thất bại, text đó được giữ trong bản ghi lỗi.
- `summary.json`: số trang dự kiến/đã lưu, tổng ký tự, phiên bản thư viện và trạng
  thái `complete` hoặc `incomplete`.
- `extract.log`: log tiến độ giống terminal, gồm thời gian, thứ tự xử lý trong
  corpus, số trang vật lý PDF, kết quả đọc text, số ảnh, cache HIT/MISS, kết quả
  từng ảnh/trang, lỗi và tổng kết. File được nối thêm giữa các lần chạy; mỗi lần
  có mốc START/END. Ví dụ `[6/32] ... | PDF page 40` nghĩa là trang corpus thứ 6,
  tương ứng trang vật lý 40 của PDF. Log được ghi ngay khi xử lý, không đợi xong.

Script kiểm tra SHA-256 của PDF, số trang và số ký tự/hash văn bản so với manifest.
Lỗi nguồn/trang được ghi lại và tiến trình trả mã 1 khi kết quả chưa đầy đủ.
Chạy lại sẽ thay kết quả của lần trước, không nối thêm các trang trùng.
Kết quả model thành công được lưu sau mỗi trang ngay trong `pages.jsonl`;
chạy lại tái sử dụng khi hash ảnh, model và prompt/ngữ cảnh khớp. Để chạy mới
hoàn toàn, chọn một `--output-dir` khác. Model lỗi/timeout không âm thầm bỏ qua:
trang vẫn lưu text đọc được, đánh dấu `image_extraction_status: incomplete`,
ghi lỗi và trả mã 1.

Chuẩn hóa dùng chung với `scripts/build_manifest.py`: bỏ footer cuối trang đã
kiểm chứng, bỏ phần cuối từ heading References/Text Attributions/Media
Attributions, chuẩn hóa NFC và gộp whitespace. Giữ nguyên từ bị gạch nối khi
xuống dòng. Quy tắc và hash trong manifest áp dụng cho `text_only`; `text`
hợp nhất có số ký tự/hash riêng trong từng bản ghi đầu ra.

Script tự tìm embedded images bằng `pypdf.PageObject.images` (kể cả ảnh trong
form XObject được thư viện hỗ trợ), chuyển sang PNG và gọi Ollama `/api/chat`.
Trong snapshot hiện tại có ảnh ở trang 40, 54 và 63. Ảnh không được lưu thành
file riêng. Model trả transcription, description, uncertainties và caption anchor.
Figure được chèn trước caption `Figure N.N:` tương ứng; nếu không khớp thì nối
cuối trang với `placement: page_end_unresolved`. Không coi cách neo caption này
là xác định hoàn hảo thứ tự đọc của mọi PDF.

Text hợp nhất dùng nhãn `[Figure image: Figure N.N]` cho nội dung hình,
không thêm trạng thái review. Nguồn trích xuất vẫn thể hiện qua `method`,
`model`, `model_digest` và `prompt`. `complete` xác nhận quá trình trích xuất xong.
Vector drawings không phải embedded images nên chưa được phát hiện;
PDF scan toàn trang và ảnh trang trí cần xử lý riêng. Không chạy OCR riêng;
phần chữ trong ảnh do VLM đọc. Cố định output hợp nhất cho cả A/B/C và lưu
summary/hash để tái lập, không trộn các lần model sinh khác nhau.

Tái tạo manifest sau khi đã kiểm tra lại snapshot và phạm vi corpus:

```bash
python3 scripts/build_manifest.py
```

Nguồn: *Project Management*, Adrienne Watt, © 2014, BCcampus,
<https://opentextbc.ca/projectmanagement/>. Giấy phép chung CC BY 4.0,
ngoại trừ nội dung có ghi chú riêng. Thông tin giấy phép và các ngoại lệ được
giữ trong `data/manifest.json` và PDF gốc; việc bỏ ghi công khỏi `text` chỉ để
chuẩn bị nội dung truy xuất. Giữ các thông tin này khi chia sẻ kết quả trích xuất.
