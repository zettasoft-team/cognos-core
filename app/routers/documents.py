from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.core.config import UPLOADS_DIR
from app.models.schemas import DocumentListResponse, DeleteRequest
from app.services import store

router = APIRouter()


@router.get("", response_model=DocumentListResponse)
def list_documents(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100)):
    all_docs    = store.list_documents()
    total       = len(all_docs)
    total_pages = max(1, -(-total // size))
    items       = all_docs[(page - 1) * size: page * size]
    return {
        "items":       items,
        "total":       total,
        "page":        page,
        "size":        size,
        "total_pages": total_pages,
    }


@router.get("/{doc_id}")
def get_document(doc_id: str):
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    return doc


@router.post("", status_code=201)
async def upload_document(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        if not file.filename.endswith(".xml"):
            results.append({"name": file.filename, "error": "XML 파일만 업로드 가능합니다."})
            continue

        doc    = store.create_document(file.filename)
        doc_id = doc["id"]

        xml_path = UPLOADS_DIR / doc_id
        contents = await file.read()
        xml_path.write_bytes(contents)
        store.update_document_status(doc_id, "ok")
        results.append(store.get_document(doc_id))

    return results


@router.delete("")
def delete_documents(req: DeleteRequest):
    store.delete_documents(req.ids)
    return {"deleted": req.ids}
