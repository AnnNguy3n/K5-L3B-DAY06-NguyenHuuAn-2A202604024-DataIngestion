# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Tiến độ bài làm cá nhân

Tôi đã hoàn thành checkpoint 1 — chọn dữ liệu và thiết lập công cụ đọc corpus — checkpoint 2 — xây benchmark — và checkpoint 3 — đọc, chuẩn hóa và thử chunk — ngày 14/11/2026. Tôi sử dụng 32 trang nội dung từ sách *Project Management* của Adrienne Watt (BCcampus); nguồn, giấy phép, snapshot và quy tắc tính trang được ghi trong [manifest](data/manifest.json).

Tôi đã lưu kết quả đọc trong [data/processed/](data/processed/), gồm 32 trang, log lỗi và thống kê. Cách cài đặt, chạy lại và yêu cầu model local được ghi trong [data/README.md](data/README.md). Báo cáo tiến độ nằm tại [báo cáo cá nhân](report/individual/2A202604024_NguyenHuuAn.md).

Tôi đã xây [20 câu hỏi tiếng Anh](benchmark/questions.jsonl), chia 15 dev / 5 test, gồm 5 câu filter và 1 câu filter thuộc test. Tôi đã đối chiếu evidence với nguồn; quy tắc chọn cấu hình, cách chia tập và giới hạn rò rỉ được ghi trong [BENCHMARK.md](BENCHMARK.md#quy-tắc-chọn-cấu-hình-cho-corpus-project-management).

Tôi đã xuất [206 chunk A và 131 chunk B](starter/results/ingestion_summary.json), giữ metadata nguồn/trang và offset. Tôi chốt B cho phạm vi demo, giữ các giới hạn cắt giữa từ và nhận diện heading bằng heuristic trong báo cáo. Cách chạy được ghi trong [starter/README.md](starter/README.md#4-xuất-trang-và-chunk-ab).

Các lệnh kiểm tra tôi sử dụng từ thư mục gốc repo, sau khi cài dependencies:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/read_corpus.py
python3 -m starter.src.prepare
```

Lệnh đọc corpus cần Ollama và model vision local như mô tả trong hướng dẫn dữ liệu. Các test dùng mock cho phản hồi VLM và ghi kết quả vào thư mục tạm, không thay thế kết quả corpus thật. Tôi chưa thực hiện embedding, vector retrieval hoặc đo chỉ số benchmark ở checkpoint này.

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.
