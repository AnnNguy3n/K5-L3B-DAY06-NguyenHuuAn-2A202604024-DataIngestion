# Báo cáo cá nhân — Day 6

- Họ và tên: Nguyễn Hữu An
- MSSV: 2A202604024
- Lớp: L3B
- Ngày cập nhật: 14/11/2026
- Phạm vi báo cáo: Hoàn thành checkpoint 1 — chọn dữ liệu và setup — và checkpoint 2 — xây benchmark. Đây là báo cáo tiến độ, chưa phải báo cáo kết quả cuối bài.

## Dữ liệu và pipeline

### Corpus, nguồn và quyền sử dụng

Tôi chọn chủ đề quản lý dự án, sử dụng sách *Project Management* của Adrienne Watt, BCcampus, từ https://opentextbc.ca/projectmanagement/. Snapshot PDF local có 219 trang vật lý; phiên bản và SHA-256 được lưu trong [manifest](../../data/manifest.json).

Tôi ghi nhận giấy phép chung CC BY 4.0 cùng các ngoại lệ ghi trong tài liệu. Tôi giữ PDF gốc, thông tin ghi công và ghi chú giấy phép riêng trong manifest; không coi toàn bộ PDF chỉ có một giấy phép CC BY. Các thay đổi phục vụ trích xuất gồm chuẩn hóa Unicode, bỏ footer và phần references/attributions khỏi nội dung truy xuất.

### Số trang và quy tắc tính

Tôi chọn 32 trang vật lý: 35–37, 38–52, 53–63 và 65–67, thuộc chương 3–6. Tôi tính mỗi trang được chọn một lần khi còn nội dung chuyên môn sau chuẩn hóa; không tính bìa, mục lục hoặc trang chỉ chứa tài liệu tham khảo. Các trang hỗn hợp 37, 52 và 67 chỉ giữ phần nội dung chuyên môn. Tôi chủ động loại trang 64 và ghi rõ lý do trong manifest.

Tôi dùng số trang vật lý PDF bắt đầu từ 1 để truy nguồn. Trong phạm vi corpus, số trang in bằng số trang PDF trừ 11. Mỗi trang có ID ổn định, số ký tự và hash văn bản để kiểm tra snapshot.

### Công cụ đọc, chuẩn hóa và kết quả

Tôi hiện thực công cụ đọc tại `scripts/read_corpus.py`, dùng pypdf 6.21.4; công cụ dựng manifest tại `scripts/build_manifest.py`; quy tắc chuẩn hóa dùng chung tại `scripts/corpus_text.py`. Tôi kiểm tra hash PDF, số trang, số ký tự và hash text với manifest trước khi lưu kết quả.

Tôi chuẩn hóa Unicode NFC, bỏ footer đã xác định, cắt phần references/attributions và gộp whitespace. Tôi giữ riêng `raw_text`, `text_only` và `text` hợp nhất với nội dung hình để phân biệt text nguồn với nội dung do model trích xuất.

| Kết quả checkpoint 1 | Giá trị thực tế |
|---|---:|
| Số trang dự kiến / đã lưu | 32 / 32 |
| Số ký tự text sau chuẩn hóa, chưa thêm hình | 85.519 |
| Số ký tự text hợp nhất | 87.887 |
| Số embedded images đã xử lý | 3 |
| Số lỗi trong lần trích xuất hiện tại | 0 |
| Trạng thái trích xuất | complete |

Tôi xử lý hình ở trang PDF 40, 54 và 63 bằng model vision local `mimo-v2.6:9b-mxfp8` qua Ollama. Tên model, digest, prompt, hash ảnh, phản hồi gốc và usage được lưu theo từng hình. Model này phục vụ đọc hình; tôi chưa chọn hoặc chạy embedding model cho retrieval. Tôi không gọi dịch vụ API trả phí trong bước đọc corpus; chi phí điện và phần cứng local chưa được đo.

Tôi ghi log theo từng trang và ảnh, trạng thái cache HIT/MISS, lỗi và tổng kết tại [extract.log](../../data/processed/extract.log). Kết quả nằm tại [pages.jsonl](../../data/processed/pages.jsonl), [errors.jsonl](../../data/processed/errors.jsonl) và [summary.json](../../data/processed/summary.json).

### Metadata và kiểm tra

Tôi giữ `document_id`, `source`, `page`, `page_id`, `printed_page` và `section` theo từng trang. Trường `section` có bốn giá trị tương ứng các chương 3–6, được lấy từ heading và ranh giới chương; tôi dự kiến dùng trường này để lọc khi câu hỏi hoặc ngữ cảnh cung cấp phạm vi chương trước retrieval.

Tôi kiểm tra lại 32 trang bằng pypdf và đối chiếu với kết quả đã lưu: hash PDF/manifest, raw text, text chuẩn hóa, metadata nguồn/trang, blocks, text hợp nhất, số ký tự và hash đều khớp. Tôi chạy `python -m unittest discover -s tests -v`: 5 test đều pass, bao gồm cache, phản hồi không hợp lệ, neo caption, ghi log và giữ text khi model lỗi. Phản hồi VLM trong test được mock và không đưa vào corpus thật.

### Giới hạn và phần chưa hoàn thành

- Tôi chưa xác minh trạng thái chạy PostgreSQL/pgvector và chưa hiện thực vector store. Việc kiểm tra pgvector bằng starter là tùy chọn tại checkpoint 1.
- Tôi đã bỏ nhãn review khỏi output; thay đổi này không phải bằng chứng nội dung hình đã được kiểm chứng. Trước khi dùng làm gold evidence, tôi cần đối chiếu nội dung VLM với hình gốc.
- Figure 5.2 ở trang PDF 63 đang có `placement: page_end_unresolved`; tôi chưa xác định hoàn chỉnh vị trí đọc của hình này.
- Việc gộp whitespace làm mất ranh giới đoạn trong `text_only`. Tôi cần xử lý cấu trúc đoạn trước khi triển khai chunking theo đoạn; nếu đổi chuẩn hóa, tôi sẽ cập nhật manifest và output tương ứng.
- Công cụ hiện xử lý embedded images, chưa bao phủ vector drawings hoặc OCR riêng cho trang scan. Tôi chưa đánh giá đầy đủ thứ tự đọc bảng/phân cột.

## Cấu hình và benchmark

Tôi đã xây [20 câu hỏi tiếng Anh](../../benchmark/questions.jsonl) từ corpus Project Management. Mỗi câu có ID, split, question, expected_answer, gold_source_id, gold_page, evidence_quote và filter. Tôi dùng số trang vật lý PDF bắt đầu từ 1.

| Kết quả checkpoint 2 | Giá trị thực tế |
|---|---|
| Số câu / số ID riêng biệt | 20 / 20 |
| Dev | 15 câu, q01–q15 |
| Test | 5 câu, q16–q20 |
| Câu filter trên dev | q01, q04, q11, q14 |
| Câu filter trên test | q16 |
| Evidence chính khớp text PDF và corpus | 20 / 20 |
| Evidence thay thế đã đối chiếu | 1 / 1, q11 tại trang PDF 53 |

Tôi dùng filter `section` với giá trị được xác định từ chương nêu trong câu hỏi. Tôi đã kiểm tra các giá trị tồn tại trong metadata và khớp trang nguồn, kể cả evidence thay thế. Các câu không yêu cầu phạm vi chương dùng filter rỗng. Tôi không đưa gold source hoặc đáp án vào truy vấn/filter; evidence đều đến từ text PDF, không dựa vào phần hình do VLM sinh.

Tôi chia tập ở cấp câu hỏi, giữ các chủ đề trong cả dev và test. Hai tập dùng chung sách và các chương; q01 và q16 cùng có gold ở trang PDF 35 nhưng hỏi hai nội dung khác nhau. Tôi ghi nhận nguy cơ chia sẻ ngữ cảnh giữa hai tập; test không độc lập theo tài liệu/chủ đề và chỉ minh họa kết quả trong corpus này.

Tôi cố định benchmark và tiêu chí chọn cấu hình trước bước thử retrieval: ưu tiên Evidence Hit@3 trên dev, tiếp theo Hit@1 trên dev, tiếp theo tổng thời gian truy xuất 15 câu dev trong cùng điều kiện; nếu vẫn hòa, chọn cấu hình đứng trước theo tên. Tôi chỉ dùng dev để điều chỉnh, khóa cấu hình trước khi đánh giá test và chỉ dùng kết quả test để báo cáo. Chi tiết nằm trong [BENCHMARK.md](../../BENCHMARK.md).

Tôi chưa chốt tham số A/B/C, embedding model hoặc số chiều. Nhật ký `artifacts/experiment_log.csv` giữ nguyên các ô kết quả trống vì tôi chưa chạy thí nghiệm retrieval. Bước tiếp theo của tôi là xử lý cấu trúc đoạn và triển khai hai cấu hình chunk, đồng thời giữ truy vết nguồn/trang.

## Kết quả retrieval và audit

Tôi chưa có Hit@1, Evidence Hit@3, chunk count, nhãn coherence, audit metadata hoặc điểm grounding. Tôi chưa thực hiện so sánh A–B và B–C, chưa có chiến lược được chọn hoặc ví dụ lỗi retrieval. Các bảng theo mẫu báo cáo sẽ được bổ sung bằng kết quả thực chạy ở những checkpoint sau.

## Công cụ AI và cách kiểm tra

Tôi sử dụng Codex để hỗ trợ giải thích yêu cầu, review code, đối chiếu bộ câu hỏi với yêu cầu benchmark, kiểm tra evidence và tính nhất quán dữ liệu, đồng thời cập nhật báo cáo tiến độ. Tôi sử dụng Ollama với model vision local để trích nội dung hình. Tôi lưu nguồn và output để đối chiếu, chạy test và kiểm tra hash; tôi không coi phản hồi AI là gold evidence khi chưa xác minh với tài liệu gốc.

## Kết luận tiến độ

Tôi đã chuẩn bị corpus đủ 32 trang nội dung, ghi manifest nguồn/quyền và quy tắc tính trang, đồng thời có công cụ đọc hoạt động và kết quả kiểm tra nhất quán. Tôi đã xây và kiểm tra bộ 20 câu hỏi, cố định split 15 dev / 5 test và tiêu chí chọn cấu hình, đồng thời ghi giới hạn của benchmark. Tôi hoàn thành checkpoint 1 và checkpoint 2; chunking, embedding, lưu vector và đánh giá retrieval thuộc các bước tiếp theo.
