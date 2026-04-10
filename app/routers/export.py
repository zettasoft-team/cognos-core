from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import io

from app.core.config import UPLOADS_DIR
from app.services import store
from app.services.xml_service import parse_xml, generate_xml
from app.services.excel_service import sheets_to_excel, excel_to_sheets
from app.services.erd_service import build_erd_from_sheets
from app.services.tree_service import build_tree_from_sheets

router = APIRouter()


def _parse(doc_id: str) -> dict:
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


@router.get("/{doc_id}/export/excel")
def export_excel(doc_id: str):
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    sheets = _parse(doc_id)
    excel_bytes = sheets_to_excel(sheets)
    filename = doc["name"].replace(".xml", "") + "_meta.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{doc_id}/import/excel")
async def import_excel(doc_id: str, file: UploadFile = File(...)):
    """Excel 업로드 → XML 재생성 후 기존 파일 덮어쓰기"""
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    contents = await file.read()
    try:
        sheets = excel_to_sheets(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel 파싱 실패: {e}")

    # 수정된 내용을 XML로 변환해서 저장
    xml_bytes = generate_xml(sheets)
    xml_path  = UPLOADS_DIR / doc_id
    xml_path.write_bytes(xml_bytes)

    return {"imported_sheets": list(sheets.keys())}


@router.post("/{doc_id}/export/xml")
def export_xml(doc_id: str):
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    sheets    = _parse(doc_id)
    xml_bytes = generate_xml(sheets)
    filename  = doc["name"].replace(".xml", "") + "_generated.xml"
    return StreamingResponse(
        io.BytesIO(xml_bytes),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{doc_id}/erd")
def get_erd(doc_id: str):
    sheets = _parse(doc_id)
    return build_erd_from_sheets(sheets)


@router.get("/{doc_id}/tree")
def get_tree(doc_id: str):
    sheets = _parse(doc_id)
    return build_tree_from_sheets(sheets)
