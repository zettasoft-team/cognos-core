from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import documents, sheets, export

app = FastAPI(title="cognosFM-core", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(sheets.router,    prefix="/api/documents", tags=["sheets"])
app.include_router(export.router,    prefix="/api/documents", tags=["export"])


@app.get("/")
def health():
    return {"status": "ok"}
