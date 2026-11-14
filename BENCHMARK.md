# Benchmark — năm tiêu chí đánh giá

Mục tiêu là so sánh **ít nhất ba chiến lược dữ liệu** trên cùng corpus, model và bộ câu hỏi để chọn chiến lược phù hợp, kèm bằng chứng và lý do. Benchmark gồm bộ câu hỏi có gold, kết quả truy xuất, mẫu chấm thủ công và phân tích theo **năm tiêu chí** dưới đây.

| Tiêu chí | Cần đo hoặc kiểm tra | Minh chứng |
|---|---|---|
| **1. Độ chính xác truy xuất** | Hit@1 và Evidence Hit@3 trên cùng bộ câu hỏi | Số câu đúng/tổng câu, top-3 và gold theo từng chiến lược |
| **2. Tính mạch lạc của chunk** | Chunk có giữ trọn ý và đủ ngữ cảnh để hiểu không? | Chấm thủ công cùng 10 vị trí nguồn cho mỗi chiến lược, thang 0–2, kèm lý do |
| **3. Tính hữu dụng của metadata** | Metadata có đúng, đủ để truy vết và giúp lọc phạm vi không? | Kiểm tra `source`, `page` và trường lọc trong top-3; tỷ lệ tuân thủ filter khi có yêu cầu |
| **4. Chất lượng thông tin nền (Grounding Quality)** | Top-3 có đủ bằng chứng và điều kiện để trả lời, có truy được nguồn không? | Chấm thủ công 5 câu test mỗi chiến lược, thang 0–2, kèm lý do |
| **5. Tác động của chiến lược dữ liệu** | Các thay đổi về chunking/metadata ảnh hưởng kết quả, chất lượng và tài nguyên ra sao? | So sánh A–B và B–C, số chunk, thời gian, chi phí, ví dụ lỗi và đánh đổi |

Định nghĩa chi tiết thang điểm, mẫu và công thức xem [GUIDE.md](GUIDE.md). **Grounding ở đây đánh giá độ đủ của bằng chứng truy xuất**, không phải độ chính xác của câu trả lời LLM. Hit@3 không thay cho chấm thủ công coherence hoặc grounding. Điểm bài làm theo [RUBRIC.md](RUBRIC.md); năm tiêu chí trên là các khía cạnh cần báo cáo, không phải năm loại câu hỏi.

## Bộ câu hỏi và gold

Tự xây **ít nhất 20 câu** từ corpus, chia trước tối thiểu **15 dev / 5 test**. Nên có câu hỏi trực tiếp, diễn đạt lại, điều kiện/ngoại lệ và câu cần phân biệt bằng metadata, tùy dữ liệu. Đây là **gợi ý để phủ các lỗi**, không bắt buộc một tỷ lệ số câu cố định. Chọn và ghi cách phân chia trước khi thử nghiệm; có ít nhất **3 câu có filter**, trong đó ít nhất **1 câu test**, để kiểm tra metadata filter. Không điều chỉnh chiến lược dựa vào test; nếu đã xem test để sửa bài, ghi rõ và tạo tập test mới nếu có thể.

Mỗi câu ghi: `id`, `split`, `question`, `expected_answer`, `gold_source_id`, `gold_page`, `evidence_quote` và `filter` nếu dùng. Có thể thêm nhãn loại câu để phân tích lỗi. `gold_page` là số trang PDF hoặc ID đơn vị truy vết tương đương.

Trước khi chạy, kiểm chứng evidence tồn tại ở nguồn và đủ hỗ trợ đáp án, kể cả điều kiện/ngoại lệ. Nếu nhiều nguồn hoặc trang hợp lệ, ghi tất cả và chấp nhận một trong số đó. Không đưa đáp án hoặc gold source vào query/filter; giá trị filter phải được người dùng hoặc ngữ cảnh cung cấp **trước khi truy xuất**. Với câu không có filter, cấu hình C chạy không filter cho câu đó và ghi rõ. Không dùng câu không có đáp án trong nguồn cho chỉ số bắt buộc.

Filter cần dựa vào metadata đáng tin, ví dụ `year`, `section`, `category`, `audience`, `language` hoặc `version`. Chọn corpus có ít nhất hai phạm vi phân biệt được; không tạo giá trị giả để filter đạt điểm. Xem [data/format-example.json](data/format-example.json) để tham khảo cấu trúc, không phải benchmark hoàn chỉnh.

## Quy tắc chọn cấu hình cho corpus Project Management

Cố định trước khi chạy: q01–q15 là dev, q16–q20 là test. Hai tập đều có câu nêu rõ chương để kiểm tra filter. Chọn cấu hình theo thứ tự: Evidence Hit@3 cao nhất trên dev, rồi Hit@1 cao nhất trên dev, rồi tổng thời gian truy xuất 15 câu dev thấp nhất trong cùng điều kiện. Nếu vẫn hòa, chọn cấu hình đứng trước theo tên. Khóa cấu hình trước khi đánh giá test và chỉ dùng kết quả test để báo cáo.

Trong `benchmark/questions.jsonl`, trang được đếm từ 1 theo thứ tự vật lý của PDF. Filter rỗng áp dụng cho toàn corpus. Khi có `accepted_alternatives`, mỗi mục bổ sung một bộ nguồn, trang và trích dẫn có giá trị ngang với gold chính.

## Cách chia tập và giới hạn của benchmark cá nhân

Tôi xây 20 câu hỏi tiếng Anh trong [benchmark/questions.jsonl](benchmark/questions.jsonl), chia ở cấp câu hỏi: q01–q15 thuộc dev và q16–q20 thuộc test. Tôi giữ các chủ đề xuất hiện trong cả hai tập để đánh giá trên phạm vi chương 3–6 của cùng corpus. Cả hai tập dùng chung sách và các chương; q01 và q16 cùng lấy bằng chứng ở trang PDF 35 nhưng hỏi hai nội dung khác nhau. Vì vậy, test không độc lập theo tài liệu hoặc chủ đề, có nguy cơ chia sẻ ngữ cảnh với dev và không đại diện cho khả năng tổng quát hóa sang tài liệu mới.

Tôi cố định bộ câu hỏi, split và tiêu chí chọn cấu hình tại checkpoint 2, trước bước thử retrieval. Tôi chỉ dùng dev để điều chỉnh tham số; sau khi khóa cấu hình, tôi dùng test để báo cáo. Việc kiểm tra gold trước khi chạy nhằm xác minh benchmark, không phải dùng kết quả retrieval trên test để tinh chỉnh.

Tôi có 5 câu dùng filter `section`: q01, q04, q11, q14 thuộc dev và q16 thuộc test. Mỗi câu nêu rõ chương trong câu hỏi; filter là đầu vào phạm vi được xác định trước retrieval, không suy ra từ gold. Với 15 câu còn lại, tôi dùng filter rỗng và chạy cấu hình C không lọc. Tôi giữ cùng corpus, model và bộ câu hỏi cho A/B/C.

Tôi đã đối chiếu 20 evidence chính và 1 evidence thay thế của q11 với text trích từ đúng trang PDF sau chuẩn hóa và với `data/processed/pages.jsonl`; tất cả đều khớp. Tôi kiểm tra nội dung câu hỏi, đáp án và evidence để giữ các điều kiện cần thiết. Các evidence hiện tại đều lấy từ text PDF, không dựa vào phần mô tả hình do VLM sinh. Khi hiện thực bộ chấm, tôi sẽ chấp nhận gold chính hoặc evidence trong `accepted_alternatives`, và không tính hit chỉ vì đúng trang nhưng thiếu bằng chứng.
