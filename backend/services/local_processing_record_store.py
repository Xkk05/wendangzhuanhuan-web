from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.utils.logger import logger


class LocalProcessingRecordStore:
    def __init__(self, path: str, max_records_per_user: int = 200):
        self.path = path
        self.max_records_per_user = max(1, max_records_per_user)
        self._lock = threading.RLock()

    @staticmethod
    def _empty_store() -> dict:
        return {"version": 1, "records": []}

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return self._empty_store()
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
                return self._empty_store()
            return payload
        except Exception as exc:
            logger.warning("[local_processing_records] read_failed path=%s error=%s", self.path, exc)
            return self._empty_store()

    def _save(self, payload: dict):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp_path, self.path)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

    def append(
        self,
        *,
        app_user_id: str,
        global_user_id: str,
        app_scope: str,
        tool_name: str,
        file_name: Optional[str],
        file_size: Optional[int],
        source_format: Optional[str],
        target_format: Optional[str],
        status: str,
        result_path: Optional[str] = None,
        result_message: Optional[str] = None,
    ) -> dict:
        now = self._utc_now()
        record = {
            "id": f"local_{uuid.uuid4().hex}",
            "appUserId": app_user_id,
            "globalUserId": global_user_id,
            "appScope": app_scope,
            "toolName": tool_name,
            "fileName": file_name,
            "fileSize": file_size,
            "sourceFormat": source_format,
            "targetFormat": target_format,
            "status": status,
            "createdAt": now,
            "completedAt": now if status in {"completed", "failed"} else None,
            "resultPath": result_path,
            "resultMessage": result_message,
        }

        with self._lock:
            payload = self._load()
            records = payload.setdefault("records", [])
            records.append(record)

            matching_indices = [
                index
                for index, item in enumerate(records)
                if item.get("appUserId") == app_user_id and item.get("appScope") == app_scope
            ]
            stale_indices = set(matching_indices[:-self.max_records_per_user])
            if stale_indices:
                payload["records"] = [item for index, item in enumerate(records) if index not in stale_indices]

            self._save(payload)

        return dict(record)

    def get_recent(self, *, app_user_id: str, app_scope: str, limit: int = 10) -> list[dict]:
        safe_limit = max(1, min(limit, 20))
        with self._lock:
            records = self._load().get("records", [])
            scoped_records = [
                dict(record)
                for record in records
                if record.get("appUserId") == app_user_id and record.get("appScope") == app_scope
            ]

        scoped_records.sort(
            key=lambda record: record.get("completedAt") or record.get("createdAt") or "",
            reverse=True,
        )
        return [
            {key: value for key, value in record.items() if key not in {"appUserId", "globalUserId", "appScope"}}
            for record in scoped_records[:safe_limit]
        ]
