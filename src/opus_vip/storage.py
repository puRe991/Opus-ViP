"""File-backed project storage with path traversal protections."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from .analysis import ClipCandidate

DATA_ROOT = Path("data/projects")
UPLOAD_ROOT = Path("data/uploads")


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    source_filename: str | None
    transcript: str
    clips: list[dict]
    created_at: str


def create_project(name: str, transcript: str, clips: list[ClipCandidate], source_filename: str | None = None) -> Project:
    safe_name = (name or "Untitled project").strip()[:120]
    if not transcript.strip():
        raise ValueError("transcript is required")
    project = Project(
        id=uuid4().hex,
        name=safe_name,
        source_filename=source_filename,
        transcript=transcript,
        clips=[clip.to_dict() for clip in clips],
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    _project_path(project.id).write_text(json.dumps(asdict(project), indent=2, ensure_ascii=False), encoding="utf-8")
    return project


def list_projects() -> list[Project]:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    projects = [Project(**json.loads(path.read_text(encoding="utf-8"))) for path in DATA_ROOT.glob("*.json")]
    return sorted(projects, key=lambda p: p.created_at, reverse=True)


def get_project(project_id: str) -> Project:
    path = _project_path(project_id)
    if not path.exists():
        raise FileNotFoundError(project_id)
    return Project(**json.loads(path.read_text(encoding="utf-8")))


def save_upload(filename: str, content: bytes, max_bytes: int = 750_000_000) -> str:
    if len(content) > max_bytes:
        raise ValueError("upload exceeds maximum size")
    safe = Path(filename).name.replace("\x00", "") or "upload.bin"
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_ROOT / f"{uuid4().hex}-{safe}"
    destination.write_bytes(content)
    return destination.name


def _project_path(project_id: str) -> Path:
    if not project_id.isalnum():
        raise ValueError("invalid project id")
    return DATA_ROOT / f"{project_id}.json"
