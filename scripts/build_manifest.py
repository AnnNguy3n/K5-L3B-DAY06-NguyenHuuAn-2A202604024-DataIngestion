"""Rebuild data/manifest.json from the local PDF (requires pypdf==6.21.4)."""
import hashlib
import importlib.metadata
import json
from pathlib import Path

from pypdf import PdfReader
from corpus_text import normalize_page

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "data/raw/project-management.pdf"
SOURCE_ID = "project-management-2019-v1.03"
SECTIONS = [
    (35, 37, "3. The Project Life Cycle (Phases)"),
    (38, 52, "4. Framework for Project Management"),
    (53, 63, "5. Stakeholder Management"),
    (65, 67, "6. Culture and Project Management"),
]


def main():
    path = ROOT / SOURCE
    reader = PdfReader(path)
    pages, errors = [], []
    for start, end, section in SECTIONS:
        for number in range(start, end + 1):
            try:
                raw = reader.pages[number - 1].extract_text() or ""
                normalized = normalize_page(raw, number - 11, section)
                pages.append({
                    "page_id": f"{SOURCE_ID}:p{number:03d}",
                    "page": number,
                    "printed_page": number - 11,
                    "section": section,
                    "raw_char_count": len(raw),
                    "char_count": len(normalized),
                    "normalized_text_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
                    "counted_as_useful": True,
                    "extraction_status": "ok",
                })
            except Exception as exc:
                errors.append({"page": number, "error": str(exc)})
    if errors:
        raise RuntimeError(json.dumps(errors, ensure_ascii=False))
    data = {
        "schema_version": "1.0",
        "corpus_id": "project-management-foundations",
        "description": "Corpus về vòng đời, khung quản lý, stakeholder và văn hóa dự án; chỉ ingest các trang được chọn.",
        "accessed_at": "2026-11-14",
        "accessed_at_note": "Ngày kiểm tra bản PDF local trong phiên làm việc; không phải ngày tải gốc hay ngày hiệu lực.",
        "path_base": "repository_root",
        "sources": [{
            "source_id": SOURCE_ID,
            "title": "Project Management",
            "author": "Adrienne Watt",
            "publisher": "BCcampus",
            "language": "en",
            "document_type": "textbook",
            "source_path_or_url": SOURCE,
            "original_url": "https://opentextbc.ca/projectmanagement/",
            "accessed_at": "2026-11-14",
            "snapshot": {
                "version": "1.03",
                "version_date": "2019-09-18",
                "version_evidence_pdf_pages": [216, 217],
                "edition_label": "2nd Edition (running footer)",
                "pdf_creation_date_from_metadata": str(reader.metadata.creation_date),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
                "note": "Hash xác định snapshot local; bản tải hiện tại có thể khác. Không suy diễn ngày hiệu lực.",
            },
            "license_or_permission": {
                "default_license": "CC-BY-4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "scope": "Except where otherwise noted; giấy phép riêng trong từng chương vẫn áp dụng.",
                "evidence_pdf_pages": [3, 37, 52, 64, 67, 217],
                "attribution": "Project Management by Adrienne Watt, © 2014, BCcampus, https://opentextbc.ca/projectmanagement/. CC BY 4.0 except where otherwise noted.",
                "selected_corpus_notes": [
                    "Chương 3, 5, 6 ghi nguồn CC BY; chương 4 có hình PM star model của GeekDesplaced ghi CC BY-SA (PDF 52). Giữ ghi công và giấy phép riêng nếu dùng hình hoặc bản chuyển thể của hình.",
                    "Trích xuất text, chuẩn hóa Unicode và bỏ footer, references/attributions khỏi nội dung truy xuất; thông tin quyền vẫn giữ trong PDF và manifest.",
                ],
                "full_pdf_exceptions": [
                    {"evidence_pdf_page": 34, "item": "Petrobras sinking — Richard Collinson", "license": "CC BY-NC-ND"},
                    {"evidence_pdf_page": 83, "item": "Project Management — Andreas Cappell", "license": "CC BY-NC-SA"},
                    {"evidence_pdf_page": 101, "item": "Requirements Traceability Matrix — DHWiki", "license": "CC BY-NC-ND"},
                    {"evidence_pdf_pages": [115, 156, 157, 167, 179, 185, 195, 196, 203], "item": "Các nội dung/hình có ghi nguồn riêng", "license": "CC BY-NC-SA"},
                ],
                "redistribution_conditions": [
                    "Chia sẻ nguyên bản PDF cho mục đích phi thương mại, giữ đầy đủ ghi công, thông báo và giấy phép.",
                    "Không coi toàn bộ PDF là CC BY thuần túy. Sử dụng thương mại hoặc phát hành bản sửa đổi cần rà soát ngoại lệ NC/ND/SA và xin phép khi cần.",
                    "Không áp đặt hạn chế bổ sung trái giấy phép. Khi phát hành bản trích xuất, giữ nguồn và ghi rõ các thay đổi.",
                ],
            },
            "acquisition": {
                "local_file_provided_by_user": True,
                "instructions": "Mở original_url, chọn Download this book > Print PDF, lưu vào source_path_or_url. So sánh SHA-256; nếu khác phải kiểm tra lại trang và tạo lại manifest/benchmark.",
                "rebuild_command": "python3 scripts/build_manifest.py",
                "dependency": "pypdf==6.21.4",
            },
            "physical_page_count": len(reader.pages),
            "useful_page_count": len(pages),
            "selected_pdf_pages": [p["page"] for p in pages],
            "excluded_pdf_page_ranges": [
                {"start": 1, "end": 11, "reason": "Bìa, mục lục, bản quyền và phần đầu sách; ngoài corpus đã chọn."},
                {"start": 12, "end": 34, "reason": "Chương 1–2 ngoài chủ đề corpus đã chọn; không khẳng định tất cả là trang không hữu ích."},
                {"start": 64, "end": 64, "reason": "Trang hỗn hợp references, mô tả hình 5.2 và attributions; chủ động loại khỏi corpus, không phải trang chỉ có references."},
                {"start": 68, "end": 219, "reason": "Chương 7 trở đi và phần cuối sách ngoài phạm vi corpus đã chọn."},
            ],
            "total_normalized_char_count": sum(p["char_count"] for p in pages),
            "pages": pages,
            "extraction": {
                "tool": "pypdf.PdfReader.pages[i].extract_text()",
                "tool_version": importlib.metadata.version("pypdf"),
                "ocr_used": False,
                "normalization": "Bỏ dòng footer cuối đã kiểm chứng theo số trang in; cắt phần từ heading References/Text Attributions/Media Attributions (nếu có); Unicode NFC; gộp mọi whitespace thành một dấu cách; strip. Giữ nguyên từ gạch nối khi xuống dòng, không tự sửa nội dung.",
                "char_count_definition": "len(normalized_text): số Unicode code point, gồm dấu cách; không phải số byte/token hay chỉ ký tự chữ.",
                "raw_char_count_definition": "len(extract_text() or '') trước chuẩn hóa.",
                "errors": errors,
                "limitations": "Text-only: không OCR hình; thứ tự đọc bảng/phân cột có thể chưa tối ưu. Không coi extract_text thành công là đã kiểm chứng mọi evidence; kiểm tra từng đoạn benchmark trực tiếp với PDF.",
            },
        }],
        "page_counting_rule": {
            "minimum_useful_pages": 30,
            "actual_useful_pages": len(pages),
            "meets_minimum": len(pages) >= 30,
            "physical_page_numbering": "1-based theo thứ tự PDF; không dùng chỉ số 0-based hoặc số trang in để truy xuất.",
            "printed_page_mapping": "Trong corpus: printed_page = page - 11.",
            "rule": "Đếm mỗi trang vật lý được chọn đúng một lần nếu còn nội dung chuyên môn sau chuẩn hóa, gồm bảng có nội dung. Trang hỗn hợp 37, 52, 67 chỉ giữ phần chuyên môn; không tính phần ghi nguồn. Không áp ngưỡng 1.500 ký tự dành cho nguồn không phân trang lên PDF.",
        },
        "chunk_metadata_contract": {
            "document_id": {"type": "string", "value": SOURCE_ID, "origin": "sources[].source_id"},
            "source": {"type": "string", "value": SOURCE, "origin": "sources[].source_path_or_url"},
            "page": {"type": "integer", "origin": "pages[].page; trang vật lý 1-based"},
            "page_id": {"type": "string", "origin": "pages[].page_id"},
            "section": {
                "type": "string",
                "allowed_values": [s[2] for s in SECTIONS],
                "origin": "Heading chương và ranh giới chương trong PDF; chương 5 bắt đầu ở PDF 53.",
                "purpose": "Lọc câu hỏi theo chương do câu hỏi/ngữ cảnh cung cấp trước; không dùng gold source hay đáp án để suy ra filter.",
            },
            "cross_page_chunks": "Giữ danh sách page_ids/pages thực sự chứa nội dung; không gán một trang cho toàn bộ chunk nhiều trang. Không ghép vượt ranh giới section.",
        },
        "validation": {
            "scope": "Chỉ xác minh manifest/corpus; chưa chạy pipeline, embedding hay benchmark.",
            "selected_page_ids_unique": len({p["page_id"] for p in pages}) == len(pages),
            "all_selected_pages_have_extractable_text": all(p["char_count"] > 0 for p in pages),
        },
    }
    assert len(reader.pages) == 219, "Snapshot changed; review page selection"
    assert len(pages) >= 30
    target = ROOT / "data/manifest.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target}: {len(pages)} useful pages, {data['sources'][0]['total_normalized_char_count']} characters")


if __name__ == "__main__":
    main()
