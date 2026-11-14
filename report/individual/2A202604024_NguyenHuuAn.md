# Quản lý dự án · Báo cáo cá nhân Day 6

Nguyễn Hữu An · 2A202604024 · L3B · 14/11/2026

Tôi đã chọn **C trên dev**. B và C cùng tìm đủ evidence cho 15/15 câu trong top-3 và cho 14/15 câu ở hạng 1. Theo quy tắc phân xử đã chốt, C có tổng thời gian search thấp hơn trong lượt đo dev. Sau khi khóa C, tôi ghi nhận cả A, B và C đều đạt **2/5 Hit@1 và 2/5 Evidence Hit@3 trên test**. Các chiến lược đạt cùng điểm nhưng trả lời được các câu khác nhau bằng evidence nguyên văn. [Khóa lựa chọn](../../starter/results/checkpoint6/selection_lock.json) · [Trace test](../../starter/results/checkpoint6/test_scored.jsonl)

## Dữ liệu và pipeline

Tôi đã dùng sách *Project Management* của Adrienne Watt, BCcampus, bản 1.03 ngày 18/09/2019. Trong 219 trang PDF, tôi chọn 32 trang có nội dung chuyên môn thuộc chương 3–6 (trang vật lý 35–63 và 65–67, đếm từ 1). Mỗi trang tính một lần sau khi bỏ footer và phần tài liệu tham khảo, ghi công cuối chương. Tôi giữ PDF gốc và thông tin giấy phép CC BY 4.0 cùng các ngoại lệ riêng trong manifest. [PDF](../../data/raw/project-management.pdf) · [Nguồn, quyền, danh sách trang và SHA-256](../../data/manifest.json)

Tôi đã dùng pypdf 6.21.4 để đọc chữ, chuẩn hóa Unicode NFC và khoảng trắng. Bản trích xuất có 85.519 ký tự text thuần và 87.887 ký tự sau khi ghép nội dung ba hình ở trang 40, 54, 63. Ollama local đọc ảnh nhúng bằng `mimo-v2.6:9b-mxfp8`. Tôi lưu riêng chữ PDF, phản hồi model và vị trí ghép. Hình ở trang 63 được nối cuối trang vì chưa xác định được vị trí caption. Phần đọc ảnh chưa bao phủ hình vector hoặc OCR toàn trang. [Trang và nội dung hình](../../data/processed/pages.jsonl) · [Thống kê](../../data/processed/summary.json) · [Log trích xuất](../../data/processed/extract.log)

Khi chuẩn bị dữ liệu retrieval, tôi đã giữ ranh giới đoạn và dùng heuristic nhận diện heading từ text. Cả 32 trang đều có nội dung, không ghi nhận lỗi ingest. Mỗi chunk nằm trong một trang. Các trường chuỗi `document_id`, `source`, `page_id` và số nguyên `page` cho phép tra về PDF. Hai offset xác định đoạn trong text chuẩn hóa. Trường chuỗi `section` lấy theo ranh giới chương trong manifest để lọc khi câu hỏi nêu chương. [Pipeline](../../starter/src/prepare.py) · [Trang đã chuẩn hóa](../../starter/results/pages.jsonl) · [Thống kê chunk](../../starter/results/ingestion_summary.json) · [Log lỗi](../../starter/results/ingestion_errors.jsonl)

## Cấu hình và benchmark

| Cấu hình | Cách chia trong một trang | Filter | Số chunk | Độ dài min / trung vị / max (ký tự) | Tổng ký tự gồm overlap |
|---|---|---|---:|---:|---:|
| A | Cửa sổ 500 ký tự, overlap 50 | Không lọc | 206 | 107 / 500 / 500 | 96.732 |
| B | Gom theo heading và đoạn, tối đa 1.000 ký tự. Chỉ overlap 100 trong đoạn vượt giới hạn | Không lọc | 131 | 73 / 790 / 1.000 | 93.342 |
| C | Dùng lại chunk và vector B | SQL JSONB theo section khi câu hỏi có filter | 131 | 73 / 790 / 1.000 | 93.342 |

Tôi đã giữ nguyên corpus, embedding và phép tìm kiếm giữa ba cấu hình. A–B chỉ đổi cách chunk. B–C chỉ đổi việc áp dụng filter. [Chunk A](../../starter/results/chunks_A.jsonl) · [Chunk B dùng chung với C](../../starter/results/chunks_B.jsonl) · [Nhật ký cấu hình và giả thuyết](../../artifacts/experiment_log.csv)

Tôi đã dùng Ollama 0.40.16 (MLX), model `embeddinggemma-2:740m-mxfp8`, batch document 16, prefix query `task: search result | query: ` và prefix document `title: none | text: `. Vector thực đo có 768 chiều cho cả query lẫn document. PostgreSQL 16.16 và pgvector 0.8.7 lưu 337 vector trong bảng `day6_chunks`, tìm exact cosine top-3, phân xử đồng điểm bằng ID chunk. Tôi đã nạp lại cùng snapshot, giữ nguyên 206 ID A và 131 ID B. Tiến trình Python mới đọc lại cùng trace. Kiểm tra thay đổi văn bản và xóa ID cũ dùng bảng tạm. [Model](../../starter/results/checkpoint5_model_config.json) · [Build đầu](../../starter/results/checkpoint5_initial.json) · [Reload](../../starter/results/checkpoint5_reload.json) · [Restart](../../starter/results/checkpoint5_restart.json) · [Thử thay đổi snapshot](../../starter/results/checkpoint5_changed.json) · [Lệnh setup và chạy](../../README.md)

Tôi đã chia 20 câu tiếng Anh trước khi chạy retrieval. Dev gồm q01–q15, test gồm q16–q20. Các câu q01, q04, q11, q14 và q16 nêu chương ngay trong câu hỏi. C dùng phạm vi này trước retrieval và tìm trên toàn corpus cho 15 câu còn lại. Tôi đã đối chiếu 20 trích dẫn chính và một trích dẫn thay thế của q11 với chữ trên đúng trang PDF sau chuẩn hóa. Tất cả gold lấy từ text nguồn. [Câu hỏi, đáp án và evidence](../../benchmark/questions.jsonl) · [Quy tắc chia tập và chọn chiến lược](../../BENCHMARK.md)

Tôi đã tính một hit khi **một chunk** đúng tài liệu, đúng trang và chứa trọn trích dẫn chính hoặc thay thế sau khi gộp khoảng trắng. Hit@1 xét hạng đầu, Evidence Hit@3 xét cả ba hạng. Tôi dùng grounding để xét mức đủ bằng chứng khi đọc chung top-3. Thí nghiệm dừng ở retrieval. [Mã chấm](../../starter/src/evaluation.py)

## Kết quả

| Cấu hình | Split | Hit@1 | Evidence Hit@3 | Tổng search (ms) |
|---|---|---:|---:|---:|
| A | Dev | 6/15 | 9/15 | 60,00 |
| B | Dev | 14/15 | 15/15 | 35,93 |
| C | Dev | 14/15 | 15/15 | 34,60 |
| A | Test | 2/5 | 2/5 | 11,47 |
| B | Test | 2/5 | 2/5 | 7,85 |
| C | Test | 2/5 | 2/5 | 8,71 |

Tôi đã chọn theo thứ tự Evidence Hit@3, Hit@1, tổng thời gian search dev, rồi tên chiến lược nếu vẫn hòa. B và C hòa hai tiêu chí đầu. Tổng search của C thấp hơn B khoảng 1,33 ms cho 15 câu. Tôi đã khóa C lúc 20:28:49 ngày 14/11/2026 (UTC+7). Lượt test kết thúc lúc 20:29:05 và lưu hash của khóa. Tôi giữ nguyên lựa chọn sau test. [Trace dev](../../starter/results/checkpoint6/dev_scored.jsonl) · [Điểm dev](../../starter/results/checkpoint6/dev_summary.json) · [Khóa và thời gian dev](../../starter/results/checkpoint6/selection_lock.json) · [Điểm và thời gian test](../../starter/results/checkpoint6/test_summary.json)

Tôi ghi thời gian search phía client, gồm gọi SQL và đọc kết quả. Mỗi câu được embed một lần cho cả ba chiến lược, tổng riêng 338,29 ms trên dev và 102,46 ms trên test. Build đầu mất 10,29 s gồm cả lượt dev ban đầu. Embed/ghi A mất 5,640/0,087 s, B mất 3,972/0,062 s, C dùng lại B. Phí API cho pipeline local là 0 USD. Điện, phần cứng và công cụ hỗ trợ chấm chưa được tính. [Build và phạm vi đo](../../starter/results/checkpoint5_initial.json) · [Đo thời gian retrieval](../../starter/scripts/checkpoint6.py)

| Cấu hình | Coherence TB /2 (10 vị trí) | Metadata đạt kiểm tra tự động | Top-3 đúng chương yêu cầu | Grounding mức 0 / 1 / 2 (5 câu) | Grounding TB /2 |
|---|---:|---:|---:|---:|---:|
| A | 1,10 | 15/15 hạng | 1/1 câu | 0 / 0 / 5 | 2,00 |
| B | 1,20 | 15/15 hạng | 1/1 câu | 1 / 1 / 3 | 1,40 |
| C | 1,20 | 15/15 hạng | 1/1 câu | 1 / 1 / 3 | 1,40 |

Tôi đã dùng cùng offset 0 trên mười trang 35–44 để xét chunk bị cắt ý (0), hiểu một phần (1), hoặc tự hiểu được và trọn ý (2). Ví dụ ở trang 40, B giữ trọn mục mua sắm, A lấn sang mục stakeholder rồi cắt câu. Với grounding, tôi dùng cùng năm câu test, mỗi mẫu gồm đủ ba hạng. Điểm 0, 1, 2 lần lượt chỉ thiếu bằng chứng, có một phần, hoặc đủ trả lời và truy nguồn. Tôi dùng `student_score` hiện có cho cả hai bảng nhãn. Codex hỗ trợ đọc chunk, đề xuất điểm và lý do. Cả 30 nhãn coherence và 15 nhãn grounding đều trùng `ai_score`. Sự trùng khớp có thể phản ánh thiên lệch theo gợi ý AI. Chưa có người chấm độc lập thứ hai. [Vị trí mẫu](../../starter/results/checkpoint6/coherence_positions.json) · [Nhãn coherence và lý do](../../starter/results/checkpoint6/coherence.jsonl) · [Nhãn grounding và lý do](../../starter/results/checkpoint6/grounding.jsonl)

Tôi đã báo riêng **kết quả kiểm tra metadata tự động**. Script đối chiếu trường nguồn/trang/chương với manifest, kiểm tra text tại offset và tìm một đoạn chữ khớp trên trang PDF bằng pypdf. Cả 45 hạng đều qua kiểm tra. Trên q16, cả ba hạng của từng chiến lược đều thuộc chương 3, chỉ C áp dụng filter SQL. Trường section giúp giới hạn chương nhưng trong cùng chương vẫn có đoạn nói về đóng dự án thay cho kế hoạch nghiệm thu. Tôi đã bỏ qua đối chiếu metadata trực tiếp với PDF bằng tay cho bản demo. Phần audit thủ công theo GUIDE còn thiếu. [Kiểm tra theo hạng](../../starter/results/checkpoint6/metadata.jsonl) · [Tổng hợp](../../starter/results/checkpoint6/metadata_summary.json) · [Mã kiểm tra](../../starter/scripts/audit_metadata.py)

## Phân tích lỗi và kết luận

- **q16 · Project Management, PDF trang 35.** C lọc đúng chương nhưng hai hạng đầu ở trang 36 nói về tiêu chí nghiệm thu và đóng dự án. Top-3 thiếu tên *acceptance plan*, grounding 1/2. A có tên kế hoạch ở hạng 2 nhưng mất phần đầu trích dẫn. Cả ba trượt Evidence Hit@3. [Trang nguồn](../../data/raw/project-management.pdf#page=35) · [Các hạng trả về](../../starter/results/checkpoint6/test_scored.jsonl)
- **q18 · Project Management, PDF trang 59.** A tách điều kiện thiếu biện pháp giảm thiểu và cơ hội thi công giữa hai mùa mưa qua hai chunk. Đọc chung hạng 1 và 2 đủ để trả lời (grounding 2/2), còn phép chấm từng chunk ghi miss. B và C giữ đủ evidence ở hạng 1. [Trang nguồn](../../data/raw/project-management.pdf#page=59) · [Nhãn và lý do](../../starter/results/checkpoint6/grounding.jsonl)
- **q19 · Project Management, PDF trang 62.** A tìm được ý về lợi tức kỳ vọng ở hạng 1. B và C lấy các trang 55, 48, 53 về rủi ro, giao tiếp và stakeholder. Top-3 thiếu thông tin tài chính cần trả lời nên grounding bằng 0. [Trang nguồn](../../data/raw/project-management.pdf#page=62) · [Trace test](../../starter/results/checkpoint6/test_scored.jsonl)

Tôi đã giữ C cho bản demo theo quy tắc dev. So với A, B dùng ít hơn 75 vector, tăng số câu dev có evidence trong top-3 từ 9 lên 15 và tăng coherence trung bình 0,10/2. Trên test, A trúng q17 và q19, B/C trúng q17 và q18. A có grounding cao hơn khi đọc chung ba hạng. Từ B sang C, filter cho phép thực thi ràng buộc chương với cùng dung lượng vector. B và C cho cùng top-3 ở cả năm câu test. Lợi ích quan sát được của C là kiểm soát phạm vi, chưa thấy tăng Hit so với B. [Trace dev](../../starter/results/checkpoint6/dev_scored.jsonl) · [Trace test](../../starter/results/checkpoint6/test_scored.jsonl)

Tôi giới hạn kết luận ở một sách, năm câu test và một câu test có filter. Một câu đổi trạng thái làm tỷ lệ test đổi 20 điểm phần trăm. Hai tập dùng chung chương, q01 và q16 cùng có gold ở trang 35. Mẫu coherence đầu trang thiên về heading. Phép khớp nguyên văn có thể bỏ sót bằng chứng tương đương hoặc bị tách qua nhiều chunk như q18. Lượt đo thời gian cố định thứ tự A/B/C nên C có thể hưởng cache sau B. Với một thí nghiệm mới, tôi sẽ tách test theo tài liệu, thêm câu lọc dễ nhầm chương, nhờ người thứ hai chấm độc lập và đo nhiều lượt với thứ tự thay đổi. [Quy tắc benchmark](../../BENCHMARK.md) · [Mẫu coherence](../../starter/results/checkpoint6/coherence_positions.json) · [Quy trình đo](../../starter/scripts/checkpoint6.py)
