# Báo cáo cá nhân — Day 6

- Họ và tên: Nguyễn Hữu An
- MSSV: 2A202604024
- Lớp: L3B
- Ngày cập nhật: 14/11/2026
- Phạm vi báo cáo: Hoàn thành checkpoint 1 — chọn dữ liệu và setup — checkpoint 2 — xây benchmark — checkpoint 3 — đọc, chuẩn hóa và thử chunk — cùng checkpoint 5 — lưu vector và chạy A/B/C. Đây là báo cáo tiến độ, chưa phải báo cáo kết quả cuối bài.

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

Tôi xử lý hình ở trang PDF 40, 54 và 63 bằng model vision local `mimo-v2.6:9b-mxfp8` qua Ollama. Tên model, digest, prompt, hash ảnh, phản hồi gốc và usage được lưu theo từng hình. Model này phục vụ đọc hình; ở checkpoint 1 tôi chưa chọn hoặc chạy embedding model cho retrieval. Tôi không gọi dịch vụ API trả phí trong bước đọc corpus; chi phí điện và phần cứng local chưa được đo.

Tôi ghi log theo từng trang và ảnh, trạng thái cache HIT/MISS, lỗi và tổng kết tại [extract.log](../../data/processed/extract.log). Kết quả nằm tại [pages.jsonl](../../data/processed/pages.jsonl), [errors.jsonl](../../data/processed/errors.jsonl) và [summary.json](../../data/processed/summary.json).

### Metadata và kiểm tra

Tôi giữ `document_id`, `source`, `page`, `page_id`, `printed_page` và `section` theo từng trang. Trường `section` có bốn giá trị tương ứng các chương 3–6, được lấy từ heading và ranh giới chương; tôi dự kiến dùng trường này để lọc khi câu hỏi hoặc ngữ cảnh cung cấp phạm vi chương trước retrieval.

Tôi kiểm tra lại 32 trang bằng pypdf và đối chiếu với kết quả đã lưu: hash PDF/manifest, raw text, text chuẩn hóa, metadata nguồn/trang, blocks, text hợp nhất, số ký tự và hash đều khớp. Tôi chạy `python -m unittest discover -s tests -v`: 5 test đều pass, bao gồm cache, phản hồi không hợp lệ, neo caption, ghi log và giữ text khi model lỗi. Phản hồi VLM trong test được mock và không đưa vào corpus thật.

### Giới hạn và phần chưa hoàn thành

- Ở checkpoint 1, tôi chưa xác minh trạng thái chạy PostgreSQL/pgvector và chưa hiện thực vector store. Việc kiểm tra pgvector bằng starter là tùy chọn tại checkpoint 1.
- Tôi đã bỏ nhãn review khỏi output; thay đổi này không phải bằng chứng nội dung hình đã được kiểm chứng. Trước khi dùng làm gold evidence, tôi cần đối chiếu nội dung VLM với hình gốc.
- Figure 5.2 ở trang PDF 63 đang có `placement: page_end_unresolved`; tôi chưa xác định hoàn chỉnh vị trí đọc của hình này.
- Bản trích xuất checkpoint 1 tại `data/processed/` gộp whitespace và không giữ đoạn. Tại checkpoint 3, tôi giữ riêng output mới tại `starter/results/`, bảo toàn dòng trống và tách heading bằng heuristic; manifest vẫn mô tả snapshot và text chuẩn hóa của checkpoint 1. Tôi đã kiểm tra evidence trên output mới.
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

Tôi đã chốt cấu hình chunk ban đầu cho bài demo: A dùng cửa sổ 500 ký tự, overlap 50; B gom đoạn/heading tối đa 1.000 ký tự, chỉ dùng cửa sổ cố định overlap 100 khi một đơn vị đoạn dài vượt giới hạn. C dự kiến dùng chính chunk của B và thêm filter từ câu hỏi lúc retrieval. Tôi ghi tham số và giả thuyết trong [experiment_log.csv](../../artifacts/experiment_log.csv), tại checkpoint 2 các ô model và điểm retrieval còn trống.

## Đọc, chuẩn hóa và chunking — checkpoint 3

Tôi hiện thực `DocumentPage` và `Chunk` tại `starter/src/models.py`, đọc dữ liệu qua `ingestion.py`, chia chunk qua `chunking.py` và xuất dữ liệu bằng `prepare.py`. Tôi dùng nhận diện heading theo ngữ cảnh tại `text_structure.py`; xử lý nhãn hình và bảng để giảm việc coi từng từ là heading. Tôi gom các khối ngắn, giữ heading trong metadata và giới hạn chunk trong từng trang vật lý.

Tôi giữ Unicode NFC, nối các dòng bị ngắt, bảo toàn dòng trống và ranh giới heading nhận diện được. Phương pháp này là heuristic trên text, chưa phục hồi đầy đủ đoạn và bố cục PDF. Metadata chunk có nguồn, trang, section, cấu hình và offset `[char_start, char_end)` trong text trang. ID được tạo ổn định theo tài liệu, nguồn, trang, cấu hình và vị trí.

Tôi chạy từ thư mục gốc repo sau khi cài dependencies tại `starter/requirements.txt`:

```bash
starter/.venv/bin/python -m starter.src.prepare
starter/.venv/bin/python -m unittest discover -s tests -v
```

Lệnh prepare cần Ollama local và model vision theo [starter/README.md](../../starter/README.md#4-xuất-trang-và-chunk-ab); cache ảnh vẫn cần xác thực model digest. Tôi lưu [trang chuẩn hóa](../../starter/results/pages.jsonl), [chunk A](../../starter/results/chunks_A.jsonl), [chunk B](../../starter/results/chunks_B.jsonl), [log lỗi](../../starter/results/ingestion_errors.jsonl) và [summary](../../starter/results/ingestion_summary.json).

| Thống kê thực tế | A | B |
|---|---:|---:|
| Số chunk | 206 | 131 |
| Độ dài nhỏ nhất, ký tự | 107 | 73 |
| Trung vị, ký tự | 500 | 790 |
| Trung bình, ký tự | 469,6 | 712,5 |
| Độ dài lớn nhất, ký tự | 500 | 1.000 |
| Chunk dưới 100 ký tự | 0 | 1 |
| Chunk dưới 200 ký tự | 8 | 8 |
| Tổng ký tự, gồm overlap | 96.732 | 93.342 |

Tôi đọc được 32/32 trang, không có trang rỗng hoặc lỗi trong output hiện tại; 3 hình được giữ trong dữ liệu trang. Tôi kiểm tra kết quả tái tạo A/B khớp hoàn toàn các file đã xuất, ID không trùng, offset và metadata đúng, không mất ký tự nội dung ngoài whitespace. Tôi kiểm tra lại 20 evidence chính và 1 evidence thay thế: tất cả khớp nguyên văn cả text nguồn chuẩn hóa và text hợp nhất mới. Tôi chạy toàn bộ 22 test, tất cả pass; phần VLM trong test được mock và ghi vào thư mục tạm.

Tôi chốt B ở mức đủ dùng cho bài demo và không tối ưu chunking thêm tại checkpoint này. Giới hạn còn lại gồm cửa sổ đoạn dài có thể cắt giữa từ, ranh giới trang có thể cắt giữa câu, và heuristic có thể nhận một dòng liệt kê dài là heading. Ví dụ output có chunk bắt đầu bằng `les. Also` ở trang 57 và metadata heading chứa cả dòng diễn giải `5. Managing quality...` ở trang 39. Tôi chưa coi việc giảm chunk ngắn là bằng chứng B truy xuất tốt hơn A; coherence và retrieval sẽ được đánh giá ở các checkpoint sau.

## Lưu vector và truy xuất top-3 — checkpoint 5 (2:40)

Tôi đã dùng đúng tag local `embeddinggemma-2:740m-mxfp8` trên Ollama 0.40.16, runner MLX. Tôi đã đối chiếu cấu hình model local và vector thật. Backbone có hidden size 512, đầu chiếu embedding là 768. Trường embedding_length của /api/show báo 512, còn /api/tags báo 768. Tôi đã bỏ tham số dimensions và đo được 768 ở cả query, document và mọi vector trong PostgreSQL. Tôi dùng prefix Retrieval-query và Retrieval-document của model, theo thứ tự là `task: search result | query: ` và `title: none | text: `. Tôi dùng cùng prompt document mặc định cho mọi chunk. [Cấu hình trích từ model local](../../starter/results/checkpoint5_model_config.json) · [Thông tin lần chạy](../../starter/results/checkpoint5_initial.json)

Tôi đã nạp 206 vector A và 131 vector B vào PostgreSQL 16.16 với pgvector 0.8.7. C dùng chung 131 vector B. Tôi dùng exact cosine, top-3, batch document 16 và giữ nguyên hai file chunk. Lần build đầu mất 10,29 giây, gồm 5,64 giây embed A, 3,97 giây embed B và 0,37 giây embed query + truy vấn dev. Phí API là 0 USD do chạy local. Tôi chưa đo điện năng và khấu hao phần cứng.

Tôi đã truy vấn 15 câu dev và lưu 45 trace với 135 kết quả truy xuất; đây chưa phải 135 kết quả được chấm đúng evidence. Cả 4 câu C có filter đều trả ba chunk khớp section. Trên 11 câu còn lại, C và B trả cùng ID, thứ tự, score, text và metadata. Tôi chỉ truyền văn bản câu hỏi sang embedder và chỉ lấy filter đã khai báo từ câu hỏi. [Trace top-3](../../starter/results/dev_top3.jsonl)

Tôi đã nạp lại trong 10,22 giây. Database vẫn có 206 và 131 ID phân biệt. Tôi đã mở tiến trình Python mới, chạy lại dev trong 0,50 giây tính cả khởi tạo và thu được cùng hash trace như hai lần build. Trong bảng tạm, tôi đã thay text/vector của một ID, xóa một ID khỏi snapshot A và kiểm tra B vẫn truy xuất được dữ liệu cũ của B. Tôi đã chạy lại 22 test hiện có và tất cả đều đạt. [Nạp lại](../../starter/results/checkpoint5_reload.json) · [Tiến trình mới](../../starter/results/checkpoint5_restart.json) · [Thay đổi snapshot](../../starter/results/checkpoint5_changed.json) · [Log test](../../starter/results/checkpoint5_unittest.log)

### Phạm vi minh chứng và giới hạn checkpoint 5

Tôi lưu kết quả dev trong `dev_top3.jsonl`, mỗi dòng là một cặp câu hỏi–chiến lược, chứa filter thực tế và ba kết quả theo thứ tự xếp hạng. Score là cosine similarity, không phải xác suất đúng hoặc nhãn hit. Tôi chưa chấm Hit@1/Hit@3, chưa gọi retrieval trên năm câu test và chưa chọn chiến lược thắng.

Tôi dùng `checkpoint5_reload.json` để ghi nhận nạp lại cùng snapshot không tăng số hàng; `checkpoint5_restart.json` ghi nhận mở tiến trình Python mới và truy vấn dữ liệu đã lưu, không build lại. Kiểm tra restart này chưa bao gồm khởi động lại container PostgreSQL. Tôi đối chiếu hash trace của initial, reload và restart để xác nhận kết quả nhất quán. `checkpoint5_changed.json` kiểm tra cập nhật và xóa chunk trong bảng tạm của phiên kết nối, không thay đổi bảng corpus chính.

Tôi lưu cấu hình local tại `checkpoint5_model_config.json`: hidden size 512 khác chiều đầu ra embedding 768; tôi sử dụng chiều embedding 768 và kiểm tra độ dài vector thực tế. `checkpoint5_unittest.log` là lần chạy lại 22 test ingestion/chunking và trích xuất hình đã có, không phải bộ test riêng cho embedding hoặc SQL retrieval. Minh chứng tích hợp nằm trong các báo cáo initial/reload/restart/changed và trace dev. Tôi chưa có thời gian truy xuất riêng cho từng chiến lược; `dev_seconds` đo embedding câu hỏi và truy vấn cả A/B/C.

## Kết quả retrieval và audit

Tôi chưa có Hit@1, Evidence Hit@3, nhãn coherence, audit metadata hoặc điểm grounding. Tôi chưa thực hiện so sánh A–B và B–C, chưa có chiến lược được chọn hoặc ví dụ lỗi retrieval. Các bảng theo mẫu báo cáo sẽ được bổ sung bằng kết quả thực chạy ở những checkpoint sau.

## Công cụ AI và cách kiểm tra

Tôi sử dụng Codex để hỗ trợ giải thích yêu cầu, hiện thực adapter embedding, vector store và orchestration, review code, đối chiếu bộ câu hỏi với yêu cầu benchmark, kiểm tra evidence và tính nhất quán dữ liệu, đồng thời cập nhật báo cáo tiến độ. Tôi sử dụng Ollama với model vision local để trích nội dung hình. Tôi lưu nguồn và output để đối chiếu, chạy test và kiểm tra hash; tôi không coi phản hồi AI là gold evidence khi chưa xác minh với tài liệu gốc.

## Kết luận tiến độ

Tôi đã chuẩn bị corpus đủ 32 trang nội dung, ghi manifest nguồn/quyền và quy tắc tính trang, đồng thời có công cụ đọc hoạt động và kết quả kiểm tra nhất quán. Tôi đã xây và kiểm tra bộ 20 câu hỏi, cố định split 15 dev / 5 test và tiêu chí chọn cấu hình, đồng thời ghi giới hạn của benchmark. Tôi đã xuất và kiểm tra hai cấu hình chunk cùng log lỗi và metadata truy nguồn. Tôi đã hoàn thành checkpoint 1, 2, 3 và 5. Tôi chưa chạy retrieval trên 5 câu test, chưa chấm chất lượng hoặc chọn chiến lược thắng.
