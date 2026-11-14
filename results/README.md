# Kết quả bài nộp

Pipeline ghi minh chứng gốc vào [starter/results](../starter/results/). Các liên kết dưới đây trỏ đến cùng snapshot dùng trong báo cáo.

| Nội dung | Minh chứng |
|---|---|
| Đọc corpus và chia chunk | [Log đọc PDF](../data/processed/extract.log) · [Thống kê ingest](../starter/results/ingestion_summary.json) · [Lỗi ingest](../starter/results/ingestion_errors.jsonl) |
| Nạp vector và mở lại | [Build đầu](../starter/results/checkpoint5_initial.json) · [Reload](../starter/results/checkpoint5_reload.json) · [Restart](../starter/results/checkpoint5_restart.json) |
| Quyết định trên dev | [Trace đã chấm](../starter/results/checkpoint6/dev_scored.jsonl) · [Điểm dev](../starter/results/checkpoint6/dev_summary.json) · [Khóa C](../starter/results/checkpoint6/selection_lock.json) |
| Đánh giá trên test | [Trace đã chấm](../starter/results/checkpoint6/test_scored.jsonl) · [Điểm test](../starter/results/checkpoint6/test_summary.json) |
| Nhãn có AI hỗ trợ | [Vị trí mẫu](../starter/results/checkpoint6/coherence_positions.json) · [Coherence](../starter/results/checkpoint6/coherence.jsonl) · [Grounding](../starter/results/checkpoint6/grounding.jsonl) |
| Metadata tự động | [Từng hạng](../starter/results/checkpoint6/metadata.jsonl) · [Tổng hợp](../starter/results/checkpoint6/metadata_summary.json) |
