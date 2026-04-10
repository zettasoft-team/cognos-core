from fastapi import APIRouter, HTTPException
from app.core.config import UPLOADS_DIR
from app.services import store
from app.services.xml_service import parse_xml

router = APIRouter()


def _get_parsed(doc_id: str) -> dict:
    """XML 파일을 직접 파싱해서 6개 시트 데이터 반환"""
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    xml_path = UPLOADS_DIR / doc_id
    if not xml_path.exists():
        raise HTTPException(status_code=404, detail="XML 파일을 찾을 수 없습니다.")

    try:
        return parse_xml(xml_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"XML 파싱 실패: {e}")


@router.get("/{doc_id}/sheets")
def get_all_sheets(doc_id: str):
    return _get_parsed(doc_id)


@router.get("/{doc_id}/sheets/{sheet_id}")
def get_sheet(doc_id: str, sheet_id: str):
    sheets = _get_parsed(doc_id)
    if sheet_id not in sheets:
        raise HTTPException(status_code=404, detail="시트를 찾을 수 없습니다.")
    return {"sheet_id": sheet_id, **sheets[sheet_id]}
