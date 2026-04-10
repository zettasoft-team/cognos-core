"""
문서 메타 정보를 JSON 파일로 관리하는 단순 저장소.
추후 DB로 교체 시 이 모듈만 수정하면 됩니다.
"""
import json
import uuid
from datetime import date
from pathlib import Path

from app.core.config import UPLOADS_DIR, STORAGE_DIR, DB_FILE


def _load() -> dict:
    if not DB_FILE.exists():
        DB_FILE.write_text(json.dumps({"documents": {}}), encoding="utf-8")
    return json.loads(DB_FILE.read_text(encoding="utf-8"))


def _save(data: dict):
    DB_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 문서 ──────────────────────────────────────────────────────────────────

def create_document(filename: str) -> dict:
    data = _load()
    doc_id = str(uuid.uuid4())
    doc = {
        "id":          doc_id,
        "name":        filename,
        "upload_date": date.today().isoformat(),
        "status":      "pending",
        "sheets":      {},
    }
    data["documents"][doc_id] = doc
    _save(data)
    return doc


def list_documents() -> list:
    data = _load()
    return list(data["documents"].values())


def get_document(doc_id: str) -> dict | None:
    data = _load()
    return data["documents"].get(doc_id)


def delete_documents(ids: list[str]):
    data = _load()
    for doc_id in ids:
        doc = data["documents"].pop(doc_id, None)
        if doc:
            xml_path = UPLOADS_DIR / doc_id
            if xml_path.exists():
                xml_path.unlink()
    _save(data)


def update_document_status(doc_id: str, status: str):
    data = _load()
    if doc_id in data["documents"]:
        data["documents"][doc_id]["status"] = status
        _save(data)


# ── 시트 ──────────────────────────────────────────────────────────────────

def get_sheet(doc_id: str, sheet_id: str) -> dict | None:
    data = _load()
    doc  = data["documents"].get(doc_id)
    if not doc:
        return None
    return doc["sheets"].get(sheet_id)


def save_sheet(doc_id: str, sheet_id: str, sheet_data: dict):
    data = _load()
    doc  = data["documents"].get(doc_id)
    if not doc:
        return
    doc["sheets"][sheet_id] = sheet_data
    _save(data)


def get_all_sheets(doc_id: str) -> dict:
    data = _load()
    doc  = data["documents"].get(doc_id)
    return doc["sheets"] if doc else {}
