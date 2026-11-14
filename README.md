# Day 06 · Truy xuất bằng chứng từ sách Project Management

Nguyễn Hữu An · 2A202604024 · L3B. Tôi đã so sánh ba cách truy xuất trên 32 trang của cùng một sách và 20 câu có gold. Tôi đã khóa C trên dev. Trên test, cả ba cấu hình đều đạt 2/5 Hit@1 và 2/5 Evidence Hit@3. Báo cáo có phân tích theo câu, nhãn có AI hỗ trợ và giới hạn của việc chỉ kiểm tra metadata tự động. [Báo cáo cá nhân](report/individual/2A202604024_NguyenHuuAn.md) · [Thông tin học viên](STUDENT.md) · [Kết quả](results/README.md)

## Dữ liệu và cấu hình đã chạy

- Corpus tiếng Anh gồm các trang PDF 35–63 và 65–67 của *Project Management* v1.03 (Adrienne Watt, BCcampus). Manifest ghi hash snapshot, giấy phép CC BY 4.0 và ngoại lệ theo nội dung. Gold được lấy từ chữ PDF. [PDF](data/raw/project-management.pdf) · [Manifest](data/manifest.json) · [15 câu dev và 5 câu test](benchmark/questions.jsonl)
- A chia cửa sổ 500 ký tự, overlap 50. B gom đoạn theo heading, tối đa 1.000 ký tự, overlap 100 chỉ trong đoạn quá dài. C dùng 131 vector của B và lọc SQL theo section nếu câu hỏi nêu chương. A có 206 vector. [Nhật ký thí nghiệm](artifacts/experiment_log.csv) · [Mã pipeline](starter/src/)
- Môi trường đã đo dùng Python 3.14.10, Ollama 0.40.16 (MLX), model vision local `mimo-v2.6:9b-mxfp8` và embedding `embeddinggemma-2:740m-mxfp8` (768 chiều, batch 16). PostgreSQL 16.16 + pgvector 0.8.7 lưu bảng `day6_lab.public.day6_chunks` trong volume Compose `pg_data`. Truy xuất exact cosine top-3. [Build, digest model và prefix query/document](starter/results/checkpoint5_initial.json) · [Compose](starter/docker-compose.yml) · [SQL truy xuất](starter/src/store.py)
- Build đầu 10,29 s. Tổng search dev A/B/C lần lượt 60,00/35,93/34,60 ms và test 11,47/7,85/8,71 ms, tách khỏi embedding query dùng chung. Phí API pipeline local 0 USD, chưa đo điện và phần cứng. [Thời gian dev và khóa C](starter/results/checkpoint6/selection_lock.json) · [Thời gian test](starter/results/checkpoint6/test_summary.json)

## Cài đặt và kiểm tra

Các lệnh dưới đây chạy từ gốc repo, dùng shell macOS/Linux. Cần Python 3.11–3.14. Cài cả hai bộ requirements trong cùng môi trường để dùng đúng phiên bản pypdf và Pillow của snapshot. Kiểm tra unit test chỉ dùng dữ liệu thử, có thể chạy trước khi bật dịch vụ. [Dependencies trích xuất](scripts/requirements.txt) · [Dependencies pipeline](starter/requirements.txt)

```bash
python3 -m venv starter/.venv
source starter/.venv/bin/activate
python -m pip install -r scripts/requirements.txt -r starter/requirements.txt
python -m pip check
python -m unittest discover -s tests -v
```

Để chạy pipeline, cần Docker Compose, Ollama local đang chạy tại 127.0.0.1:11434 và hai model đúng tag ở trên đã cài trong Ollama. Có thể bật Ollama bằng ứng dụng hoặc chạy `ollama serve` trong terminal riêng. Dùng `ollama list` để kiểm tra model trước khi chạy. Bản chạy test kiểm tra cả thông tin model local đã lưu ở lần build. [Hướng dẫn starter](starter/README.md) · [Điều kiện khớp snapshot](starter/scripts/checkpoint6.py)

```bash
cp -n starter/.env.example starter/.env
docker compose -f starter/docker-compose.yml -p day6_student_starter up -d --wait
python starter/scripts/check_setup.py
```

## Tái lập từ snapshot

Các lệnh pipeline ghi kết quả theo đường dẫn cố định. Để giữ minh chứng gốc, thực hiện trong **bản sao riêng** và dùng database lab dành cho lần tái lập. Với kho chunk đã giao, hai lệnh đầu nạp snapshot và kiểm tra nạp lại, sau đó tiến trình mới đọc dữ liệu đã lưu. Lần build đầu dùng nhãn mặc định build, lần nạp lại dùng nhãn reload để giữ tệp initial mà khóa đã ghi hash. Test xác minh hash đầu vào và dùng khóa C có sẵn.

```bash
python -m starter.src.run build
python -m starter.src.run build --label reload
python -m starter.src.run dev --label restart
python -m starter.scripts.check_reingestion
python -m starter.scripts.checkpoint6 test
python -m starter.scripts.audit_metadata
```

Để tái tạo từ PDF thay vì bắt đầu ở chunk, chạy hai lệnh sau **trước** bước build trong bản sao. Lệnh đọc corpus dùng cache ảnh nếu snapshot khớp, còn prepare bảo toàn ranh giới đoạn phục vụ chunking. Cả hai cần model vision local đúng phiên bản. [Hướng dẫn đọc PDF và cache](data/README.md) · [Trang và chunk đã giao](starter/results/ingestion_summary.json)

```bash
python scripts/read_corpus.py
python -m starter.src.prepare
```

Trình tự lần đo gốc là build initial → reload → dev restart → `python -m starter.scripts.checkpoint6 select` trên dev → test → audit metadata tự động. Nếu tái lập toàn bộ thí nghiệm trên máy khác, dùng build đầu với `--label initial` cho lần đo mới, giữ mẫu coherence và di chuyển khóa cũ ra ngoài thư mục kết quả **của bản sao** trước bước select. Model, trace và hash phải khớp trong cùng lần đo. Thời gian phân xử có thể đổi theo máy. Nhãn coherence/grounding của bài nộp gắn với ID và nội dung đã lưu. [Quy tắc benchmark](BENCHMARK.md) · [Hướng dẫn chi tiết](starter/README.md)

## Đối chiếu bài nộp

Mã nằm ở [starter/src](starter/src/), còn [chỉ mục kết quả](results/README.md) dẫn tới minh chứng gốc trong starter/results. Trạng thái gửi bài được ghi trong [STUDENT.md](STUDENT.md). [Checklist](SUBMISSION.md) · [Rubric](RUBRIC.md) · [Hướng dẫn](GUIDE.md) · [Quy định](RULES.md)
