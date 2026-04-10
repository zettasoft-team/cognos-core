from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# 프로젝트 루트 기준 경로 처리
_raw = os.getenv("UPLOADS_DIR", "./storage/uploads")
UPLOADS_DIR: Path = Path(_raw) if Path(_raw).is_absolute() else (
    Path(__file__).parent.parent.parent / _raw.lstrip("./")
)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

STORAGE_DIR = UPLOADS_DIR.parent
DB_FILE     = STORAGE_DIR / "db.json"
