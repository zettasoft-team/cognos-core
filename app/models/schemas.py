from pydantic import BaseModel
from typing import List, Optional


class SheetData(BaseModel):
    sheet_id: str
    columns: List[str]
    rows: List[List[str]]


class DocumentMeta(BaseModel):
    id: str
    name: str
    upload_date: str
    status: str          # "ok" | "pending"


class DocumentListResponse(BaseModel):
    items: List[DocumentMeta]
    total: int
    page: int
    size: int
    total_pages: int


class DeleteRequest(BaseModel):
    ids: List[str]


class ErdNode(BaseModel):
    id: str
    label: str
    columns: List[str]


class ErdEdge(BaseModel):
    from_: str
    to: str
    label: str


class ErdResponse(BaseModel):
    nodes: List[ErdNode]
    edges: List[ErdEdge]
