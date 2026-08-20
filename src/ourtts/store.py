from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

_SCHEMA_VERSION = 1

_MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS segments (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    text TEXT NOT NULL,
    voice_id TEXT,
    language TEXT,
    style TEXT NOT NULL DEFAULT 'natural',
    quality TEXT NOT NULL DEFAULT 'auto',
    controls_json TEXT NOT NULL DEFAULT '{}',
    locked INTEGER NOT NULL DEFAULT 0,
    muted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_segments_project_position
ON segments(project_id, position);

CREATE TABLE IF NOT EXISTS takes (
    id TEXT PRIMARY KEY,
    segment_id TEXT NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
    audio_path TEXT,
    manifest_path TEXT,
    engine TEXT,
    status TEXT NOT NULL,
    favorite INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_takes_segment_created
ON takes(segment_id, created_at DESC);

CREATE TABLE IF NOT EXISTS voices (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    voicepack_path TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS voice_references (
    id TEXT PRIMARY KEY,
    voice_id TEXT NOT NULL REFERENCES voices(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    sha256 TEXT,
    consent TEXT NOT NULL,
    license TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS voice_states (
    id TEXT PRIMARY KEY,
    voice_id TEXT NOT NULL REFERENCES voices(id) ON DELETE CASCADE,
    engine TEXT NOT NULL,
    model_revision TEXT,
    state_path TEXT NOT NULL,
    sha256 TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS models (
    id TEXT PRIMARY KEY,
    manifest_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_installations (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    state TEXT NOT NULL,
    install_path TEXT,
    revision TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_model_installations_model
ON model_installations(model_id);

CREATE TABLE IF NOT EXISTS generation_jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    phase TEXT NOT NULL,
    progress REAL NOT NULL DEFAULT 0,
    request_json TEXT NOT NULL,
    result_json TEXT,
    error TEXT,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_created
ON generation_jobs(created_at DESC);

CREATE TABLE IF NOT EXISTS generation_history (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES generation_jobs(id) ON DELETE SET NULL,
    text_preview TEXT NOT NULL,
    voice_id TEXT,
    language TEXT,
    engine TEXT,
    audio_path TEXT,
    manifest_path TEXT,
    favorite INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_generation_history_created
ON generation_history(created_at DESC);

CREATE TABLE IF NOT EXISTS pronunciations (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    scope_id TEXT,
    source TEXT NOT NULL,
    replacement TEXT,
    phonemes TEXT,
    language TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS router_preferences (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class LocalStore:
    """Small SQLite source of truth for the local product.

    Connections are short-lived so API/background worker threads do not share sqlite connection
    objects. WAL improves local reader/writer concurrency while retaining SQLite's transaction
    semantics on one machine.
    """

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()
        self.recover_interrupted_jobs()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def migrate(self) -> None:
        with self._connect() as connection:
            connection.executescript(_MIGRATION_1)
            existing = connection.execute(
                "SELECT version FROM schema_migrations WHERE version = ?", (_SCHEMA_VERSION,)
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (_SCHEMA_VERSION, self._now()),
                )

    def schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
        return int(row["version"] or 0)

    def recover_interrupted_jobs(self) -> int:
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE generation_jobs
                SET status='interrupted', phase='interrupted',
                    error=COALESCE(error, 'ourTTS restarted before this job completed.'),
                    updated_at=?
                WHERE status IN ('queued','planning','loading_model','generating','rendering','quality_check','cancel_requested')
                """,
                (now,),
            )
        return int(cursor.rowcount)

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        data = dict(row)
        for key in tuple(data):
            if key.endswith("_json") and data[key] is not None:
                decoded_key = key.removesuffix("_json")
                data[decoded_key] = json.loads(data.pop(key))
        for key in ("locked", "muted", "favorite", "cancel_requested"):
            if key in data:
                data[key] = bool(data[key])
        return data

    def create_project(self, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("project name must not be empty")
        project_id = uuid4().hex
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO projects(id,name,metadata_json,created_at,updated_at) VALUES (?,?,?,?,?)",
                (project_id, clean_name, json.dumps(metadata or {}), now, now),
            )
        return self.get_project(project_id) or {}

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC, created_at DESC"
            ).fetchall()
        return [self._decode(row) or {} for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        return self._decode(row)

    def add_segment(
        self,
        project_id: str,
        text: str,
        *,
        voice_id: str | None = None,
        language: str | None = None,
        style: str = "natural",
        quality: str = "auto",
        controls: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.get_project(project_id) is None:
            raise KeyError(project_id)
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("segment text must not be empty")
        segment_id = uuid4().hex
        now = self._now()
        with self._connect() as connection:
            position_row = connection.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS next_position FROM segments WHERE project_id=?",
                (project_id,),
            ).fetchone()
            position = int(position_row["next_position"])
            connection.execute(
                """
                INSERT INTO segments(
                    id,project_id,position,text,voice_id,language,style,quality,controls_json,
                    created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    segment_id,
                    project_id,
                    position,
                    clean_text,
                    voice_id,
                    language,
                    style,
                    quality,
                    json.dumps(controls or {}),
                    now,
                    now,
                ),
            )
            connection.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return self.get_segment(segment_id) or {}

    def get_segment(self, segment_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM segments WHERE id=?", (segment_id,)).fetchone()
        return self._decode(row)

    def list_segments(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM segments WHERE project_id=? ORDER BY position ASC", (project_id,)
            ).fetchall()
        return [self._decode(row) or {} for row in rows]

    def add_take(
        self,
        segment_id: str,
        *,
        status: str,
        audio_path: str | None = None,
        manifest_path: str | None = None,
        engine: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.get_segment(segment_id) is None:
            raise KeyError(segment_id)
        take_id = uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO takes(id,segment_id,audio_path,manifest_path,engine,status,metadata_json,created_at)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    take_id,
                    segment_id,
                    audio_path,
                    manifest_path,
                    engine,
                    status,
                    json.dumps(metadata or {}),
                    self._now(),
                ),
            )
        return self.get_take(take_id) or {}

    def get_take(self, take_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM takes WHERE id=?", (take_id,)).fetchone()
        return self._decode(row)

    def list_takes(self, segment_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM takes WHERE segment_id=? ORDER BY created_at DESC", (segment_id,)
            ).fetchall()
        return [self._decode(row) or {} for row in rows]

    def create_job(self, request: dict[str, Any]) -> dict[str, Any]:
        job_id = uuid4().hex
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO generation_jobs(
                    id,status,phase,progress,request_json,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (job_id, "queued", "queued", 0.0, json.dumps(request), now, now),
            )
        return self.get_job(job_id) or {}

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        phase: str | None = None,
        progress: float | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        cancel_requested: bool | None = None,
    ) -> dict[str, Any]:
        current = self.get_job(job_id)
        if current is None:
            raise KeyError(job_id)
        fields: list[str] = ["updated_at=?"]
        values: list[Any] = [self._now()]
        for column, value in (("status", status), ("phase", phase), ("progress", progress), ("error", error)):
            if value is not None:
                fields.append(f"{column}=?")
                values.append(value)
        if result is not None:
            fields.append("result_json=?")
            values.append(json.dumps(result))
        if cancel_requested is not None:
            fields.append("cancel_requested=?")
            values.append(int(cancel_requested))
        values.append(job_id)
        with self._connect() as connection:
            connection.execute(f"UPDATE generation_jobs SET {', '.join(fields)} WHERE id=?", values)
        return self.get_job(job_id) or {}

    def request_cancel(self, job_id: str) -> dict[str, Any]:
        return self.update_job(job_id, status="cancel_requested", cancel_requested=True)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()
        return self._decode(row)

    def list_jobs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 500))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM generation_jobs ORDER BY created_at DESC LIMIT ?", (bounded,)
            ).fetchall()
        return [self._decode(row) or {} for row in rows]

    def record_history(
        self,
        *,
        job_id: str | None,
        text: str,
        voice_id: str | None,
        language: str | None,
        engine: str | None,
        audio_path: str | None,
        manifest_path: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        history_id = uuid4().hex
        preview = " ".join(text.split())[:180]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO generation_history(
                    id,job_id,text_preview,voice_id,language,engine,audio_path,manifest_path,
                    metadata_json,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    history_id,
                    job_id,
                    preview,
                    voice_id,
                    language,
                    engine,
                    audio_path,
                    manifest_path,
                    json.dumps(metadata or {}),
                    self._now(),
                ),
            )
        return self.get_history(history_id) or {}

    def get_history(self, history_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM generation_history WHERE id=?", (history_id,)
            ).fetchone()
        return self._decode(row)

    def list_history(self, *, limit: int = 100) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 500))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM generation_history ORDER BY created_at DESC LIMIT ?", (bounded,)
            ).fetchall()
        return [self._decode(row) or {} for row in rows]

    def set_setting(self, key: str, value: Any) -> None:
        clean_key = key.strip()
        if not clean_key:
            raise ValueError("setting key must not be empty")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO settings(key,value_json,updated_at) VALUES (?,?,?)
                ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at
                """,
                (clean_key, json.dumps(value), self._now()),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._connect() as connection:
            row = connection.execute("SELECT value_json FROM settings WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row["value_json"])
