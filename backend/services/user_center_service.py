from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pymysql
from pymysql.cursors import DictCursor
from backend.services.local_processing_record_store import LocalProcessingRecordStore
from backend.utils.logger import logger


APP_SCOPE = os.environ.get("MEMBERSHIP_SUBSITE_NAME", "https://doc.kunqiongai.com/")
TRIAL_DAYS = int(os.environ.get("MEMBERSHIP_TRIAL_DAYS", "7"))
FREE_DAILY_LIMIT = int(os.environ.get("FREE_DAILY_LIMIT", "10"))
FREE_MAX_FILE_SIZE = int(os.environ.get("FREE_MAX_FILE_SIZE", str(50 * 1024 * 1024)))
VIP_MAX_FILE_SIZE = int(os.environ.get("VIP_MAX_FILE_SIZE", str(500 * 1024 * 1024)))
LOCAL_SESSION_EXPIRE_SECONDS = int(os.environ.get("LOCAL_SESSION_EXPIRE_SECONDS", str(7 * 24 * 60 * 60)))
MEMBERSHIP_PAY_PAGE = os.environ.get("MEMBERSHIP_PAY_PAGE", "https://kunqiongai.com/web_member_pay.html")
OAUTH_TOKEN_URL = os.environ.get("OAUTH_TOKEN_URL", "https://login.kunqiongai.com/api/oauth/token")
DEV_OAUTH_CLIENT_ID = os.environ.get("DEV_OAUTH_CLIENT_ID", "")
DEV_OAUTH_CLIENT_SECRET = os.environ.get("DEV_OAUTH_CLIENT_SECRET", "")
PROD_OAUTH_CLIENT_ID = os.environ.get("PROD_OAUTH_CLIENT_ID", "")
PROD_OAUTH_CLIENT_SECRET = os.environ.get("PROD_OAUTH_CLIENT_SECRET", "")

DB_CONFIG = {
    "host": os.environ.get("USER_CENTER_DB_HOST", "localhost"),
    "port": int(os.environ.get("USER_CENTER_DB_PORT", "3306")),
    "user": os.environ.get("USER_CENTER_DB_USER", "root"),
    "password": os.environ.get("USER_CENTER_DB_PASSWORD", ""),
    "database": os.environ.get("USER_CENTER_DB_NAME", "kqai_web_doc"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "autocommit": False,
    "connect_timeout": int(os.environ.get("USER_CENTER_DB_CONNECT_TIMEOUT", "5")),
    "read_timeout": int(os.environ.get("USER_CENTER_DB_READ_TIMEOUT", "8")),
    "write_timeout": int(os.environ.get("USER_CENTER_DB_WRITE_TIMEOUT", "8")),
}
DB_CONNECTION_MAX_AGE_SECONDS = int(os.environ.get("USER_CENTER_DB_CONNECTION_MAX_AGE_SECONDS", "120"))
USER_PROFILE_CACHE_TTL_SECONDS = int(os.environ.get("USER_PROFILE_CACHE_TTL_SECONDS", "30"))
LOCAL_SESSION_FALLBACK_ENABLED = os.environ.get("LOCAL_SESSION_FALLBACK_ENABLED", "true").lower() not in {"0", "false", "no"}
LOCAL_SESSION_STORE_PATH = os.environ.get("LOCAL_SESSION_STORE_PATH", "/data/local-sessions.json")
LOCAL_PROCESSING_RECORD_STORE_PATH = os.environ.get("LOCAL_PROCESSING_RECORD_STORE_PATH", "/data/local-processing-records.json")
LOCAL_PROCESSING_RECORDS_PER_USER = int(os.environ.get("LOCAL_PROCESSING_RECORDS_PER_USER", "200"))
PROCESSING_RECORD_QUERY_LIMIT = max(
    1,
    int(os.environ.get("PROCESSING_RECORD_QUERY_LIMIT", str(LOCAL_PROCESSING_RECORDS_PER_USER))),
)
DB_FALLBACK_ERROR_CODES = {1045, 1130, 2002, 2003, 2005, 2013}

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS global_user_identity (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        global_user_id VARCHAR(64) NOT NULL,
        oauth_user_id VARCHAR(64) NULL,
        username VARCHAR(100) NULL,
        nickname VARCHAR(100) NULL,
        avatar VARCHAR(500) NULL,
        email VARCHAR(200) NULL,
        phone VARCHAR(30) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_global_user_id (global_user_id),
        KEY idx_oauth_user_id (oauth_user_id),
        KEY idx_email (email),
        KEY idx_phone (phone)
    ) COMMENT='Unified user identity'
    """,
    """
    CREATE TABLE IF NOT EXISTS app_user_profile (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        app_user_id VARCHAR(96) NOT NULL,
        global_user_id VARCHAR(64) NOT NULL,
        app_scope VARCHAR(64) NOT NULL,
        nickname VARCHAR(100) NULL,
        avatar VARCHAR(500) NULL,
        is_vip TINYINT(1) NOT NULL DEFAULT 0,
        vip_level INT NOT NULL DEFAULT 0,
        vip_expire_time DATETIME NULL,
        is_permanent_vip TINYINT(1) NOT NULL DEFAULT 0,
        trial_started_at DATETIME NULL,
        trial_expire_time DATETIME NULL,
        daily_used_count INT NOT NULL DEFAULT 0,
        daily_limit_count INT NOT NULL DEFAULT 10,
        last_quota_reset_date DATE NULL,
        max_file_size BIGINT NOT NULL DEFAULT 52428800,
        allow_batch TINYINT(1) NOT NULL DEFAULT 0,
        allow_no_watermark TINYINT(1) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_app_user_id (app_user_id),
        KEY idx_global_user_id (global_user_id),
        KEY idx_app_scope (app_scope)
    ) COMMENT='App scoped user profile'
    """,
    """
    CREATE TABLE IF NOT EXISTS app_user_session (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(128) NOT NULL,
        app_user_id VARCHAR(96) NOT NULL,
        global_user_id VARCHAR(64) NOT NULL,
        login_token VARCHAR(512) NOT NULL,
        api_web_token VARCHAR(512) NULL,
        upstream_access_token VARCHAR(512) NULL,
        refresh_token VARCHAR(512) NULL,
        expired_at DATETIME NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
        login_ip VARCHAR(64) NULL,
        user_agent VARCHAR(500) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_session_id (session_id),
        UNIQUE KEY uk_login_token (login_token(191)),
        KEY idx_app_user_id (app_user_id),
        KEY idx_global_user_id (global_user_id),
        KEY idx_status (status)
    ) COMMENT='Local app session'
    """,
    """
    CREATE TABLE IF NOT EXISTS app_tool_processing_record (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        app_user_id VARCHAR(96) NOT NULL,
        global_user_id VARCHAR(64) NOT NULL,
        app_scope VARCHAR(64) NOT NULL,
        tool_name VARCHAR(100) NOT NULL,
        file_name VARCHAR(255) NULL,
        file_size BIGINT NULL,
        source_format VARCHAR(50) NULL,
        target_format VARCHAR(50) NULL,
        result_path VARCHAR(1000) NULL,
        result_message VARCHAR(1000) NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'waiting',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at DATETIME NULL,
        KEY idx_processing_app_user_id (app_user_id),
        KEY idx_processing_scope (app_scope),
        KEY idx_processing_created_at (created_at)
    ) COMMENT='App scoped processing records'
    """,
]


class UserCenterError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "user_center_error", payload: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.payload = payload or {}


class UserCenterService:
    def __init__(self):
        self._schema_ready = False
        self._thread_local = threading.local()
        self._profile_cache = {}
        self._profile_cache_lock = threading.Lock()
        self._local_session_lock = threading.RLock()
        self._local_processing_records = LocalProcessingRecordStore(
            LOCAL_PROCESSING_RECORD_STORE_PATH,
            max_records_per_user=LOCAL_PROCESSING_RECORDS_PER_USER,
        )

    @contextmanager
    def get_connection(self):
        connect_started_at = time.time()
        conn = getattr(self._thread_local, "conn", None)
        created_at = float(getattr(self._thread_local, "conn_created_at", 0) or 0)
        should_reconnect = (
            conn is None
            or not getattr(conn, "open", False)
            or (time.time() - created_at) > DB_CONNECTION_MAX_AGE_SECONDS
        )
        if should_reconnect:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            conn = pymysql.connect(**DB_CONFIG)
            self._thread_local.conn = conn
            self._thread_local.conn_created_at = time.time()
            logger.info(
                "[db_connect] reused=False elapsed_ms=%s host=%s port=%s",
                round((time.time() - connect_started_at) * 1000, 2),
                DB_CONFIG.get("host"),
                DB_CONFIG.get("port"),
            )
        else:
            ping_started_at = time.time()
            conn.ping(reconnect=True)
            logger.info(
                "[db_connect] reused=True ping_ms=%s host=%s port=%s",
                round((time.time() - ping_started_at) * 1000, 2),
                DB_CONFIG.get("host"),
                DB_CONFIG.get("port"),
            )
        try:
            yield conn
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

    def invalidate_profile_cache(self, token: Optional[str] = None):
        with self._profile_cache_lock:
            if token:
                self._profile_cache.pop(token, None)
            else:
                self._profile_cache.clear()

    def _get_cached_profile(self, token: str) -> Optional[dict]:
        if not token:
            return None
        with self._profile_cache_lock:
            cached = self._profile_cache.get(token)
            if not cached:
                return None
            if time.time() - float(cached.get("cached_at") or 0) > USER_PROFILE_CACHE_TTL_SECONDS:
                self._profile_cache.pop(token, None)
                return None
            profile = cached.get("profile")
            return dict(profile) if profile else None

    def _set_cached_profile(self, token: str, profile: Optional[dict]):
        if not token or not profile:
            return
        with self._profile_cache_lock:
            self._profile_cache[token] = {
                "cached_at": time.time(),
                "profile": dict(profile),
            }

    def _log_db_step(self, operation: str, started_at: float, **fields):
        payload = " ".join(f"{key}={value}" for key, value in fields.items())
        logger.info(
            "[db_timing] op=%s elapsed_ms=%s%s",
            operation,
            round((time.time() - started_at) * 1000, 2),
            f" {payload}" if payload else "",
        )

    def _should_use_local_session_fallback(self, exc: Exception) -> bool:
        if not LOCAL_SESSION_FALLBACK_ENABLED:
            return False
        if isinstance(exc, pymysql.MySQLError):
            code = exc.args[0] if exc.args else None
            return code in DB_FALLBACK_ERROR_CODES
        return False

    def _empty_local_session_store(self) -> dict:
        return {"version": 1, "sessions": {}}

    def _load_local_session_store(self) -> dict:
        if not LOCAL_SESSION_FALLBACK_ENABLED:
            return self._empty_local_session_store()
        if not os.path.exists(LOCAL_SESSION_STORE_PATH):
            return self._empty_local_session_store()
        try:
            with open(LOCAL_SESSION_STORE_PATH, "r", encoding="utf-8") as file:
                payload = json.load(file)
            if not isinstance(payload, dict):
                return self._empty_local_session_store()
            sessions = payload.get("sessions")
            if not isinstance(sessions, dict):
                payload["sessions"] = {}
            return payload
        except Exception as exc:
            logger.warning("[local_session_store] read_failed path=%s error=%s", LOCAL_SESSION_STORE_PATH, exc)
            return self._empty_local_session_store()

    def _save_local_session_store(self, payload: dict):
        os.makedirs(os.path.dirname(LOCAL_SESSION_STORE_PATH) or ".", exist_ok=True)
        tmp_path = f"{LOCAL_SESSION_STORE_PATH}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp_path, LOCAL_SESSION_STORE_PATH)

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            raw_value = str(value).strip()
            iso_value = raw_value[:-1] + "+00:00" if raw_value.endswith("Z") else raw_value
            try:
                parsed = datetime.fromisoformat(iso_value)
            except ValueError:
                parsed = None
            if parsed is None:
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        parsed = datetime.strptime(raw_value, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return None

        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    def _build_lightweight_profile(
        self,
        *,
        remote_user: dict,
        profile_id: Optional[int],
        session_id: str,
        global_user_id: str,
        app_user_id: str,
        oauth_user_id: str,
        local_token: str,
        api_web_token: Optional[str],
        upstream_access_token: str,
        now: datetime,
        trial_expire_at: datetime,
        session_source: str = "mysql",
    ) -> dict:
        return {
            "profile_id": profile_id,
            "session_id": session_id,
            "global_user_id": global_user_id,
            "user_id": app_user_id,
            "id": oauth_user_id,
            "username": remote_user.get("username") or "",
            "nickname": remote_user.get("nickname") or remote_user.get("username") or "",
            "avatar": remote_user.get("avatar"),
            "email": remote_user.get("email"),
            "phone": remote_user.get("phone"),
            "token": local_token,
            "api_web_token": api_web_token or upstream_access_token,
            "app_scope": APP_SCOPE,
            "is_vip": False,
            "vip_level": 0,
            "vip_expire_time": None,
            "is_permanent_vip": False,
            "trial_active": True,
            "trial_started_at": self._format_datetime(now),
            "trial_expire_time": self._format_datetime(trial_expire_at),
            "remaining_days": self._compute_remaining_days(trial_expire_at),
            "access_state": "trial",
            "daily_used_count": 0,
            "daily_limit_count": FREE_DAILY_LIMIT,
            "remaining_daily_count": FREE_DAILY_LIMIT,
            "max_file_size": FREE_MAX_FILE_SIZE,
            "allow_batch": False,
            "allow_no_watermark": False,
            "disable_watermark": False,
            "session_source": session_source,
        }

    def _build_session_result(
        self,
        *,
        local_token: str,
        profile: dict,
        api_web_token: Optional[str],
        refresh_token: Optional[str],
    ) -> dict:
        return {
            "access_token": local_token,
            "token_type": "Bearer",
            "expires_in": LOCAL_SESSION_EXPIRE_SECONDS,
            "user": self._build_user_info(profile),
            "user_profile": profile,
            "api_web_token": api_web_token or profile.get("api_web_token"),
            "refresh_token": refresh_token,
        }

    def _create_local_fallback_session(
        self,
        *,
        remote_user: dict,
        upstream_access_token: str,
        request_meta: Optional[dict] = None,
        api_web_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> dict:
        request_meta = request_meta or {}
        oauth_user_id = str(remote_user.get("id") or remote_user.get("user_id") or "")
        if not oauth_user_id:
            raise UserCenterError("Upstream login succeeded but user info is missing", 502, "upstream_user_missing")

        global_user_id = f"kq_{oauth_user_id}"
        app_user_id = f"{APP_SCOPE}_{hashlib.md5(global_user_id.encode('utf-8')).hexdigest()[:24]}"
        now = datetime.utcnow()
        expired_at = now + timedelta(seconds=LOCAL_SESSION_EXPIRE_SECONDS)
        session_id = urllib.parse.quote_plus(f"{APP_SCOPE}:{now.timestamp()}:{oauth_user_id}")
        local_token = f"{session_id}:{oauth_user_id}"
        trial_expire_at = now + timedelta(days=TRIAL_DAYS)
        profile = self._build_lightweight_profile(
            remote_user=remote_user,
            profile_id=None,
            session_id=session_id,
            global_user_id=global_user_id,
            app_user_id=app_user_id,
            oauth_user_id=oauth_user_id,
            local_token=local_token,
            api_web_token=api_web_token,
            upstream_access_token=upstream_access_token,
            now=now,
            trial_expire_at=trial_expire_at,
            session_source="local_file",
        )

        with self._local_session_lock:
            store = self._load_local_session_store()
            sessions = store.setdefault("sessions", {})
            for record in sessions.values():
                if (record.get("user_profile") or {}).get("user_id") == app_user_id:
                    record["status"] = "LOGOUT"
            sessions[local_token] = {
                "status": "ACTIVE",
                "expired_at": self._format_datetime(expired_at),
                "user_profile": profile,
                "api_web_token": api_web_token or upstream_access_token,
                "upstream_access_token": upstream_access_token,
                "refresh_token": refresh_token or "",
                "login_ip": request_meta.get("client_ip"),
                "user_agent": request_meta.get("user_agent"),
                "created_at": self._format_datetime(now),
            }
            self._save_local_session_store(store)

        self._set_cached_profile(local_token, profile)
        logger.warning(
            "[local_session_store] created token_tail=%s app_user_id=%s path=%s",
            str(local_token)[-8:],
            app_user_id,
            LOCAL_SESSION_STORE_PATH,
        )
        return self._build_session_result(
            local_token=local_token,
            profile=profile,
            api_web_token=api_web_token or upstream_access_token,
            refresh_token=refresh_token,
        )

    def _get_local_session_record(self, token: str, *, include_expired: bool = False) -> Optional[dict]:
        if not LOCAL_SESSION_FALLBACK_ENABLED or not token:
            return None
        changed = False
        with self._local_session_lock:
            store = self._load_local_session_store()
            sessions = store.setdefault("sessions", {})
            record = sessions.get(token)
            if not record or record.get("status") != "ACTIVE":
                return None
            expired_at = self._parse_datetime(record.get("expired_at"))
            if expired_at and expired_at < datetime.utcnow() and not include_expired:
                record["status"] = "EXPIRED"
                changed = True
                result = None
            else:
                result = dict(record)
                result["user_profile"] = dict(record.get("user_profile") or {})
            if changed:
                self._save_local_session_store(store)
            return result

    def _get_local_session_profile(self, token: str, allow_missing: bool = False) -> Optional[dict]:
        record = self._get_local_session_record(token)
        if not record:
            if allow_missing:
                return None
            raise UserCenterError("Login session expired, please log in again", 401, "login_expired")
        profile = dict(record.get("user_profile") or {})
        profile["api_web_token"] = record.get("api_web_token") or record.get("upstream_access_token") or profile.get("api_web_token")
        profile["session_source"] = "local_file"
        self._set_cached_profile(token, profile)
        return profile

    def _update_local_session_record(self, token: str, **updates):
        with self._local_session_lock:
            store = self._load_local_session_store()
            record = store.setdefault("sessions", {}).get(token)
            if not record:
                return
            profile_updates = updates.pop("user_profile", None)
            record.update(updates)
            if profile_updates:
                profile = record.setdefault("user_profile", {})
                profile.update(profile_updates)
            self._save_local_session_store(store)
        self.invalidate_profile_cache(token)

    def _logout_local_session(self, token: str) -> bool:
        with self._local_session_lock:
            store = self._load_local_session_store()
            record = store.setdefault("sessions", {}).get(token)
            if not record:
                return False
            record["status"] = "LOGOUT"
            self._save_local_session_store(store)
        self.invalidate_profile_cache(token)
        return True

    def ensure_schema(self):
        if self._schema_ready:
            return

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for statement in SCHEMA_STATEMENTS:
                    cursor.execute(statement)

                self._ensure_column(cursor, "app_user_profile", "app_scope", "ALTER TABLE app_user_profile ADD COLUMN app_scope VARCHAR(64) NOT NULL DEFAULT 'document_converter' AFTER global_user_id")
                self._ensure_column(cursor, "app_user_profile", "trial_started_at", "ALTER TABLE app_user_profile ADD COLUMN trial_started_at DATETIME NULL AFTER is_permanent_vip")
                self._ensure_column(cursor, "app_user_profile", "trial_expire_time", "ALTER TABLE app_user_profile ADD COLUMN trial_expire_time DATETIME NULL AFTER trial_started_at")
                self._ensure_column(cursor, "app_user_profile", "last_quota_reset_date", "ALTER TABLE app_user_profile ADD COLUMN last_quota_reset_date DATE NULL AFTER daily_limit_count")
                self._ensure_column(cursor, "app_user_session", "api_web_token", "ALTER TABLE app_user_session ADD COLUMN api_web_token VARCHAR(512) NULL AFTER login_token")
                self._ensure_column(cursor, "app_user_session", "upstream_access_token", "ALTER TABLE app_user_session ADD COLUMN upstream_access_token VARCHAR(512) NULL AFTER login_token")
                self._ensure_column(cursor, "app_user_session", "refresh_token", "ALTER TABLE app_user_session ADD COLUMN refresh_token VARCHAR(512) NULL AFTER upstream_access_token")
                self._ensure_column(cursor, "app_tool_processing_record", "app_scope", "ALTER TABLE app_tool_processing_record ADD COLUMN app_scope VARCHAR(64) NOT NULL DEFAULT 'document_converter' AFTER global_user_id")
                cursor.execute("UPDATE app_user_profile SET app_scope = %s WHERE app_scope IS NULL OR app_scope = ''", (APP_SCOPE,))
                cursor.execute("UPDATE app_tool_processing_record SET app_scope = %s WHERE app_scope IS NULL OR app_scope = ''", (APP_SCOPE,))
            conn.commit()

        self._schema_ready = True

    def _ensure_column(self, cursor, table_name: str, column_name: str, ddl: str):
        cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
        if not cursor.fetchone():
            cursor.execute(ddl)

    def create_or_update_session(
        self,
        remote_user: dict,
        upstream_access_token: str,
        request_meta: Optional[dict] = None,
        api_web_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> dict:
        op_started_at = time.time()
        self.invalidate_profile_cache()
        request_meta = request_meta or {}

        oauth_user_id = str(remote_user.get("id") or remote_user.get("user_id") or "")
        if not oauth_user_id:
            raise UserCenterError("Upstream login succeeded but user info is missing", 502, "upstream_user_missing")

        global_user_id = f"kq_{oauth_user_id}"
        app_user_id = f"{APP_SCOPE}_{hashlib.md5(global_user_id.encode('utf-8')).hexdigest()[:24]}"
        now = datetime.utcnow()
        expired_at = now + timedelta(seconds=LOCAL_SESSION_EXPIRE_SECONDS)
        session_id = urllib.parse.quote_plus(f"{APP_SCOPE}:{now.timestamp()}:{oauth_user_id}")
        local_token = f"{session_id}:{oauth_user_id}"
        trial_expire_at = now + timedelta(days=TRIAL_DAYS)

        try:
            self.ensure_schema()
        except Exception as exc:
            if self._should_use_local_session_fallback(exc):
                logger.warning(
                    "[local_session_store] fallback_on_schema_error error=%s host=%s port=%s",
                    exc,
                    DB_CONFIG.get("host"),
                    DB_CONFIG.get("port"),
                )
                return self._create_local_fallback_session(
                    remote_user=remote_user,
                    upstream_access_token=upstream_access_token,
                    request_meta=request_meta,
                    api_web_token=api_web_token,
                    refresh_token=refresh_token,
                )
            raise

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                write_started_at = time.time()
                cursor.execute(
                    """
                    INSERT INTO global_user_identity (
                        global_user_id, oauth_user_id, username, nickname, avatar, email, phone
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        oauth_user_id = VALUES(oauth_user_id),
                        username = VALUES(username),
                        nickname = VALUES(nickname),
                        avatar = VALUES(avatar),
                        email = VALUES(email),
                        phone = VALUES(phone),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        global_user_id,
                        oauth_user_id,
                        remote_user.get("username"),
                        remote_user.get("nickname") or remote_user.get("username"),
                        remote_user.get("avatar"),
                        remote_user.get("email"),
                        remote_user.get("phone"),
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO app_user_profile (
                        app_user_id, global_user_id, app_scope, nickname, avatar, trial_started_at, trial_expire_time,
                        daily_limit_count, last_quota_reset_date, max_file_size
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        nickname = VALUES(nickname),
                        avatar = VALUES(avatar),
                        app_scope = VALUES(app_scope),
                        trial_started_at = COALESCE(app_user_profile.trial_started_at, VALUES(trial_started_at)),
                        trial_expire_time = COALESCE(app_user_profile.trial_expire_time, VALUES(trial_expire_time)),
                        daily_limit_count = CASE
                            WHEN app_user_profile.daily_limit_count IS NULL OR app_user_profile.daily_limit_count = 0
                            THEN VALUES(daily_limit_count)
                            ELSE app_user_profile.daily_limit_count
                        END,
                        max_file_size = CASE
                            WHEN app_user_profile.max_file_size IS NULL OR app_user_profile.max_file_size = 0
                            THEN VALUES(max_file_size)
                            ELSE app_user_profile.max_file_size
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        app_user_id,
                        global_user_id,
                        APP_SCOPE,
                        remote_user.get("nickname") or remote_user.get("username"),
                        remote_user.get("avatar"),
                        now,
                        trial_expire_at,
                        FREE_DAILY_LIMIT,
                        date.today(),
                        FREE_MAX_FILE_SIZE,
                    ),
                )
                profile_id = None
                cursor.execute(
                    """
                    SELECT id, app_user_id
                    FROM app_user_profile
                    WHERE global_user_id = %s
                    LIMIT 1
                    """,
                    (global_user_id,),
                )
                persisted_profile = cursor.fetchone()
                if persisted_profile:
                    profile_id = persisted_profile.get("id")
                    app_user_id = persisted_profile.get("app_user_id") or app_user_id

                cursor.execute(
                    """
                    UPDATE app_user_session
                    SET status = 'LOGOUT', updated_at = CURRENT_TIMESTAMP
                    WHERE app_user_id = %s AND status = 'ACTIVE'
                    """,
                    (app_user_id,),
                )
                cursor.execute(
                    """
                    INSERT INTO app_user_session (
                        session_id, app_user_id, global_user_id, login_token, api_web_token,
                        upstream_access_token, refresh_token, expired_at, status, login_ip, user_agent
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s)
                    """,
                    (
                        session_id,
                        app_user_id,
                        global_user_id,
                        local_token,
                        api_web_token,
                        upstream_access_token,
                        refresh_token,
                        expired_at,
                        request_meta.get("client_ip"),
                        request_meta.get("user_agent"),
                    ),
                )
            conn.commit()
        self._log_db_step(
            "create_or_update_session",
            write_started_at,
            token_tail=str(local_token)[-8:],
            app_user_id=app_user_id,
        )

        lightweight_profile = {
            "profile_id": profile_id,
            "session_id": session_id,
            "global_user_id": global_user_id,
            "user_id": app_user_id,
            "id": oauth_user_id,
            "username": remote_user.get("username") or "",
            "nickname": remote_user.get("nickname") or remote_user.get("username") or "",
            "avatar": remote_user.get("avatar"),
            "email": remote_user.get("email"),
            "phone": remote_user.get("phone"),
            "token": local_token,
            "api_web_token": api_web_token or upstream_access_token,
            "app_scope": APP_SCOPE,
            "is_vip": False,
            "vip_level": 0,
            "vip_expire_time": None,
            "is_permanent_vip": False,
            "trial_active": True,
            "trial_started_at": self._format_datetime(now),
            "trial_expire_time": self._format_datetime(trial_expire_at),
            "remaining_days": self._compute_remaining_days(trial_expire_at),
            "access_state": "trial",
            "daily_used_count": 0,
            "daily_limit_count": FREE_DAILY_LIMIT,
            "remaining_daily_count": FREE_DAILY_LIMIT,
            "max_file_size": FREE_MAX_FILE_SIZE,
            "allow_batch": False,
            "allow_no_watermark": False,
            "disable_watermark": False,
        }
        result = {
            "access_token": local_token,
            "token_type": "Bearer",
            "expires_in": LOCAL_SESSION_EXPIRE_SECONDS,
            "user": self._build_user_info(lightweight_profile),
            "user_profile": lightweight_profile,
            "api_web_token": api_web_token,
            "refresh_token": refresh_token,
        }
        self._log_db_step("create_or_update_session_total", op_started_at, token_tail=str(local_token)[-8:])
        return result

    def get_user_profile(self, token: str, allow_missing: bool = False) -> Optional[dict]:
        op_started_at = time.time()
        if not token:
            if allow_missing:
                return None
            raise UserCenterError("请先登录后再使用", 401, "login_required")

        cached_profile = self._get_cached_profile(token)
        if cached_profile is not None:
            self._log_db_step("get_user_profile_cache_hit", op_started_at, token_tail=str(token)[-8:])
            return cached_profile

        local_profile = self._get_local_session_profile(token, allow_missing=True)
        if local_profile is not None:
            self._log_db_step("get_user_profile_local_store_hit", op_started_at, token_tail=str(token)[-8:])
            return local_profile

        try:
            self.ensure_schema()
        except Exception as exc:
            if self._should_use_local_session_fallback(exc):
                return self._get_local_session_profile(token, allow_missing=allow_missing)
            raise
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                query_started_at = time.time()
                cursor.execute(
                    """
                    SELECT
                        s.session_id,
                        s.login_token,
                        s.api_web_token,
                        s.upstream_access_token,
                        s.expired_at,
                        s.status AS session_status,
                        p.id AS profile_id,
                        p.app_user_id,
                        p.global_user_id,
                        p.app_scope,
                        p.nickname AS profile_nickname,
                        p.avatar AS profile_avatar,
                        p.is_vip,
                        p.vip_level,
                        p.vip_expire_time,
                        p.is_permanent_vip,
                        p.trial_started_at,
                        p.trial_expire_time,
                        p.daily_used_count,
                        p.daily_limit_count,
                        p.last_quota_reset_date,
                        p.max_file_size,
                        p.allow_batch,
                        p.allow_no_watermark,
                        i.oauth_user_id,
                        i.username,
                        i.nickname AS identity_nickname,
                        i.avatar AS identity_avatar,
                        i.email,
                        i.phone
                    FROM app_user_session s
                    INNER JOIN app_user_profile p ON p.app_user_id = s.app_user_id
                    INNER JOIN global_user_identity i ON i.global_user_id = s.global_user_id
                    WHERE s.login_token = %s AND s.status = 'ACTIVE' AND p.app_scope = %s
                    LIMIT 1
                    """,
                    (token, APP_SCOPE),
                )
                row = cursor.fetchone()
                self._log_db_step("get_user_profile_query", query_started_at, token_tail=str(token)[-8:])
                if not row:
                    local_profile = self._get_local_session_profile(token, allow_missing=True)
                    if local_profile is not None:
                        return local_profile
                    if allow_missing:
                        return None
                    raise UserCenterError("登录状态已失效，请重新登录", 401, "login_expired")

                now = datetime.utcnow()
                expired_at = row.get("expired_at")
                if expired_at and expired_at < now:
                    expire_started_at = time.time()
                    cursor.execute(
                        "UPDATE app_user_session SET status = 'EXPIRED', updated_at = CURRENT_TIMESTAMP WHERE login_token = %s",
                        (token,),
                    )
                    conn.commit()
                    self._log_db_step("get_user_profile_mark_expired", expire_started_at, token_tail=str(token)[-8:])
                    self.invalidate_profile_cache(token)
                    if allow_missing:
                        return None
                    raise UserCenterError("登录状态已失效，请重新登录", 401, "login_expired")

                if self._reset_daily_quota_if_needed(cursor, row):
                    quota_started_at = time.time()
                    conn.commit()
                    self._log_db_step("get_user_profile_quota_reset", quota_started_at, token_tail=str(token)[-8:])

        profile = self._build_profile_payload(row)
        self._set_cached_profile(token, profile)
        self._log_db_step("get_user_profile_total", op_started_at, token_tail=str(token)[-8:], cached=False)
        return profile

    def get_user_info(self, token: str) -> dict:
        return self._build_user_info(self.get_user_profile(token))

    def resolve_valid_api_web_token(self, token: str) -> str:
        """
        解析并返回有效的 api_web_token。
        逻辑参考 zhuanghuanqi-master:
        1. 优先从 session 表读取已存的 api_web_token
        2. 如果 api_web_token 为空，回退到 upstream_access_token
        3. 如果两者都为空，尝试用 refresh_token 刷新会话
        """
        local_record = self._get_local_session_record(token)
        if local_record:
            local_api_token = (local_record.get("api_web_token") or "").strip()
            if local_api_token:
                return local_api_token
            local_upstream_token = (local_record.get("upstream_access_token") or "").strip()
            if local_upstream_token:
                return local_upstream_token

        try:
            self.ensure_schema()
        except Exception as exc:
            if self._should_use_local_session_fallback(exc):
                return ""
            raise
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT api_web_token, upstream_access_token, refresh_token
                    FROM app_user_session
                    WHERE login_token = %s AND status = 'ACTIVE'
                    LIMIT 1
                    """,
                    (token,),
                )
                row = cursor.fetchone()

        if not row:
            return ""

        api_web_token = (row.get("api_web_token") or "").strip()
        if api_web_token:
            return api_web_token

        upstream_token = (row.get("upstream_access_token") or "").strip()
        if upstream_token:
            return upstream_token

        # 尝试刷新上游 token
        refreshed = self.refresh_upstream_session(token)
        if refreshed:
            refreshed_api_web = (refreshed.get("api_web_token") or "").strip()
            if refreshed_api_web:
                return refreshed_api_web
            refreshed_upstream = (refreshed.get("upstream_access_token") or "").strip()
            if refreshed_upstream:
                return refreshed_upstream

        return ""

    def refresh_upstream_session(self, local_token: str) -> Optional[dict]:
        """
        使用 refresh_token 刷新上游 OAuth 会话，并更新本地 session 记录。
        参考 zhuanghuanqi-master 的 refreshUpstreamSession 实现。
        """
        local_record = self._get_local_session_record(local_token)
        if local_record:
            row = {
                "id": None,
                "refresh_token": local_record.get("refresh_token"),
                "expired_at": local_record.get("expired_at"),
                "session_source": "local_file",
            }
        else:
            try:
                self.ensure_schema()
            except Exception as exc:
                if self._should_use_local_session_fallback(exc):
                    return None
                raise
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, refresh_token, expired_at
                        FROM app_user_session
                        WHERE login_token = %s AND status = 'ACTIVE'
                        LIMIT 1
                        """,
                        (local_token,),
                    )
                    row = cursor.fetchone()

        if not row:
            print(f"[DEBUG] No active session found for token={local_token}")
            return None

        refresh_token = (row.get("refresh_token") or "").strip()
        if not refresh_token:
            print(f"[DEBUG] Skip upstream token refresh because refresh_token is missing for local session {local_token}")
            return None

        client_configs = [
            (DEV_OAUTH_CLIENT_ID, DEV_OAUTH_CLIENT_SECRET),
            (PROD_OAUTH_CLIENT_ID, PROD_OAUTH_CLIENT_SECRET),
        ]

        for client_id, client_secret in client_configs:
            try:
                refreshed = self._exchange_refresh_token(refresh_token, client_id, client_secret)
                if not refreshed:
                    continue
                next_access_token = (refreshed.get("access_token") or "").strip()
                if not next_access_token:
                    continue
                next_refresh_token = (refreshed.get("refresh_token") or "").strip() or refresh_token
                next_api_web_token = (refreshed.get("api_web_token") or "").strip() or next_access_token

                new_expired_at = datetime.utcnow() + timedelta(seconds=LOCAL_SESSION_EXPIRE_SECONDS)
                if row.get("session_source") == "local_file":
                    self._update_local_session_record(
                        local_token,
                        upstream_access_token=next_access_token,
                        refresh_token=next_refresh_token,
                        api_web_token=next_api_web_token,
                        expired_at=self._format_datetime(new_expired_at),
                        user_profile={"api_web_token": next_api_web_token},
                    )
                else:
                    with self.get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute(
                                """
                                UPDATE app_user_session
                                SET upstream_access_token = %s,
                                    refresh_token = %s,
                                    api_web_token = %s,
                                    expired_at = %s,
                                    status = 'ACTIVE',
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                                """,
                                (
                                    next_access_token,
                                    next_refresh_token,
                                    next_api_web_token,
                                    new_expired_at,
                                    row["id"],
                                ),
                            )
                        conn.commit()

                print(f"[DEBUG] Upstream token refresh succeeded for client_id={client_id}")
                return {
                    "upstream_access_token": next_access_token,
                    "refresh_token": next_refresh_token,
                    "api_web_token": next_api_web_token,
                }
            except Exception as exc:
                print(f"[DEBUG] Upstream token refresh failed for clientId={client_id}: {exc}")
                continue

        return None

    def _exchange_refresh_token(self, refresh_token: str, client_id: str, client_secret: str) -> Optional[dict]:
        """调用 OAuth refresh token 端点获取新 token。"""
        try:
            form_body = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            }).encode("utf-8")
            request = urllib.request.Request(
                OAUTH_TOKEN_URL,
                data=form_body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))

            data = payload.get("data") or payload
            print(f"[DEBUG] Refresh token response for client_id={client_id}: data={data}")

            access_token = (data.get("access_token") or "").strip()
            if not access_token:
                return None

            return {
                "access_token": access_token,
                "refresh_token": (data.get("refresh_token") or "").strip(),
                "api_web_token": (
                    (data.get("api_web_token") or "").strip()
                    or (data.get("token") or "").strip()
                    or access_token
                ),
            }
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            print(f"[DEBUG] Refresh token HTTPError for client_id={client_id}: {exc.code} {detail}")
            return None
        except Exception as exc:
            print(f"[DEBUG] Refresh token error for client_id={client_id}: {exc}")
            return None

    def get_api_web_token(self, token: str) -> Optional[str]:
        local_record = self._get_local_session_record(token)
        if local_record:
            return local_record.get("api_web_token") or local_record.get("upstream_access_token")

        try:
            self.ensure_schema()
        except Exception as exc:
            if self._should_use_local_session_fallback(exc):
                return None
            raise
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT api_web_token
                    FROM app_user_session
                    WHERE login_token = %s AND status = 'ACTIVE'
                    LIMIT 1
                    """,
                    (token,),
                )
                row = cursor.fetchone()
        return row.get("api_web_token") if row else None

    def get_upstream_access_token(self, token: str) -> Optional[str]:
        local_record = self._get_local_session_record(token)
        if local_record:
            return local_record.get("upstream_access_token") or local_record.get("api_web_token")

        try:
            self.ensure_schema()
        except Exception as exc:
            if self._should_use_local_session_fallback(exc):
                return None
            raise
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT upstream_access_token
                    FROM app_user_session
                    WHERE login_token = %s AND status = 'ACTIVE'
                    LIMIT 1
                    """,
                    (token,),
                )
                row = cursor.fetchone()
        return row.get("upstream_access_token") if row else None

    def update_membership_snapshot(
        self,
        token: str,
        *,
        is_vip: bool,
        vip_level: int = 0,
        vip_expire_time: Optional[str] = None,
    ):
        op_started_at = time.time()
        profile = self.get_user_profile(token, allow_missing=True)
        if not profile:
            return

        if profile.get("session_source") == "local_file":
            self._update_local_session_record(
                token,
                user_profile={
                    "is_vip": bool(is_vip),
                    "vip_level": vip_level if is_vip else 0,
                    "vip_expire_time": vip_expire_time,
                    "allow_batch": bool(is_vip),
                    "allow_no_watermark": bool(is_vip),
                    "disable_watermark": bool(is_vip),
                    "access_state": "member_active" if is_vip else profile.get("access_state", "trial"),
                },
            )
            self._log_db_step("update_membership_snapshot_local", op_started_at, token_tail=str(token)[-8:], is_vip=is_vip)
            return

        expire_dt = self._parse_datetime(vip_expire_time)

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                update_started_at = time.time()
                cursor.execute(
                    """
                    UPDATE app_user_profile
                    SET
                        is_vip = %s,
                        vip_level = %s,
                        vip_expire_time = %s,
                        allow_batch = %s,
                        allow_no_watermark = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE app_user_id = %s
                    """,
                    (
                        1 if is_vip else 0,
                        vip_level if is_vip else 0,
                        expire_dt,
                        1 if is_vip else 0,
                        1 if is_vip else 0,
                        profile["user_id"],
                    ),
                )
            conn.commit()
        self._log_db_step("update_membership_snapshot", update_started_at, token_tail=str(token)[-8:], is_vip=is_vip)
        self.invalidate_profile_cache(token)
        self._log_db_step("update_membership_snapshot_total", op_started_at, token_tail=str(token)[-8:])

    def get_recent_records(self, token: str, limit: int = 10) -> list[dict]:
        try:
            safe_limit = int(limit)
        except (TypeError, ValueError):
            safe_limit = 10
        safe_limit = max(1, min(safe_limit, PROCESSING_RECORD_QUERY_LIMIT))
        profile = self.get_user_profile(token)
        local_records = self._local_processing_records.get_recent(
            app_user_id=profile["user_id"],
            app_scope=APP_SCOPE,
            limit=safe_limit,
        )
        if profile.get("session_source") == "local_file":
            return local_records
        try:
            self.ensure_schema()
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id, tool_name, file_name, file_size, source_format, target_format,
                            status, created_at, completed_at, result_path
                        FROM app_tool_processing_record
                        WHERE app_user_id = %s AND app_scope = %s
                        ORDER BY COALESCE(completed_at, created_at) DESC
                        LIMIT %s
                        """,
                        (profile["user_id"], APP_SCOPE, safe_limit),
                    )
                    rows = cursor.fetchall()
        except Exception as exc:
            if self._should_use_local_session_fallback(exc):
                logger.warning(
                    "[processing_record] mysql_read_failed_using_local user_id=%s error=%s",
                    profile.get("user_id"),
                    exc,
                )
                return local_records
            raise

        database_records = [
            {
                "id": str(row["id"]),
                "toolName": row["tool_name"],
                "fileName": row["file_name"],
                "fileSize": row["file_size"],
                "sourceFormat": row["source_format"],
                "targetFormat": row["target_format"],
                "status": row["status"],
                "createdAt": self._format_datetime(row["created_at"]),
                "completedAt": self._format_datetime(row["completed_at"]),
                "resultPath": row["result_path"],
            }
            for row in rows
        ]
        combined_records = database_records + local_records
        combined_records.sort(
            key=lambda record: record.get("completedAt") or record.get("createdAt") or "",
            reverse=True,
        )
        return combined_records[:safe_limit]

    def logout(self, token: str):
        if not token:
            return
        local_logged_out = self._logout_local_session(token)
        try:
            self.ensure_schema()
        except Exception as exc:
            if self._should_use_local_session_fallback(exc) and local_logged_out:
                return
            raise
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE app_user_session SET status = 'LOGOUT', updated_at = CURRENT_TIMESTAMP WHERE login_token = %s",
                    (token,),
                )
            conn.commit()
        self.invalidate_profile_cache(token)

    def require_processing_access(self, token: str):
        profile = self.get_user_profile(token)
        if profile["access_state"] == "upgrade_required":
            raise UserCenterError(
                "7天试用已结束，请充值后继续使用",
                403,
                "membership_required",
                {
                    "access_state": profile["access_state"],
                    "requires_upgrade": True,
                    "payment_url": self.build_payment_url(token),
                },
            )
        if profile["remaining_daily_count"] <= 0:
            raise UserCenterError(
                "今日使用次数已用完，请充值后继续使用",
                403,
                "membership_required",
                {
                    "access_state": profile["access_state"],
                    "requires_upgrade": True,
                    "payment_url": self.build_payment_url(token),
                },
            )
        return profile

    def record_processing(
        self,
        token: str,
        tool_name: str,
        file_name: Optional[str],
        file_size: Optional[int],
        source_format: Optional[str],
        target_format: Optional[str],
        status: str,
        result_path: Optional[str] = None,
        result_message: Optional[str] = None,
    ):
        profile = None
        record_payload = {
            "tool_name": tool_name,
            "file_name": file_name,
            "file_size": file_size,
            "source_format": source_format,
            "target_format": target_format,
            "status": status,
            "result_path": result_path,
            "result_message": result_message,
        }
        try:
            profile = self.get_user_profile(token, allow_missing=True)
            if not profile:
                return
            if profile.get("session_source") == "local_file":
                self._local_processing_records.append(
                    app_user_id=profile["user_id"],
                    global_user_id=profile["global_user_id"],
                    app_scope=APP_SCOPE,
                    **record_payload,
                )
                return

            self.ensure_schema()
            completed_at = datetime.utcnow() if status in {"completed", "failed"} else None
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO app_tool_processing_record (
                            app_user_id, global_user_id, app_scope, tool_name, file_name, file_size,
                            source_format, target_format, result_path, result_message, status, completed_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            profile["user_id"],
                            profile["global_user_id"],
                            APP_SCOPE,
                            tool_name,
                            file_name,
                            file_size,
                            source_format,
                            target_format,
                            result_path,
                            result_message,
                            status,
                            completed_at,
                        ),
                    )
                    if status == "completed":
                        cursor.execute(
                            """
                            UPDATE app_user_profile
                            SET daily_used_count = daily_used_count + 1, updated_at = CURRENT_TIMESTAMP
                            WHERE app_user_id = %s
                            """,
                            (profile["user_id"],),
                    )
                conn.commit()
            self.invalidate_profile_cache(token)
        except Exception as exc:
            if profile:
                try:
                    self._local_processing_records.append(
                        app_user_id=profile["user_id"],
                        global_user_id=profile["global_user_id"],
                        app_scope=APP_SCOPE,
                        **record_payload,
                    )
                except Exception as fallback_exc:
                    logger.warning(
                        "[processing_record] mysql_and_local_write_failed user_id=%s error=%s fallback_error=%s",
                        profile.get("user_id"),
                        exc,
                        fallback_exc,
                    )
                    return
            logger.warning(
                "[processing_record] mysql_write_failed_saved_locally=%s user_id=%s error=%s",
                bool(profile),
                (profile or {}).get("user_id", "-"),
                exc,
            )

    def build_payment_url(self, token: str = "", return_url: str = "https://doc.kunqiongai.com/account?returnTo=%2F", include_token: bool = True) -> str:
        profile = None
        active_token = ""

        if token:
            local_record = self._get_local_session_record(token)
            if local_record:
                local_profile = local_record.get("user_profile") or {}
                profile = {
                    "id": local_profile.get("id") or "",
                    "user_id": local_profile.get("user_id") or "",
                }
                if include_token:
                    active_token = (
                        (local_record.get("api_web_token") or "").strip()
                        or (local_record.get("upstream_access_token") or "").strip()
                    )
                row = None
            else:
                self.ensure_schema()
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT
                                s.api_web_token,
                                s.upstream_access_token,
                                p.app_user_id,
                                i.oauth_user_id
                            FROM app_user_session s
                            INNER JOIN app_user_profile p ON p.app_user_id = s.app_user_id
                            INNER JOIN global_user_identity i ON i.global_user_id = s.global_user_id
                            WHERE s.login_token = %s AND s.status = 'ACTIVE' AND p.app_scope = %s
                            LIMIT 1
                            """,
                            (token, APP_SCOPE),
                        )
                        row = cursor.fetchone()

            if row:
                profile = {
                    "id": row.get("oauth_user_id") or "",
                    "user_id": row.get("app_user_id") or "",
                }
                if include_token:
                    active_token = (
                        (row.get("api_web_token") or "").strip()
                        or (row.get("upstream_access_token") or "").strip()
                    )

        if token and include_token and not active_token:
            active_token = self.resolve_valid_api_web_token(token)

        query_payload = {
            "source": "subsite",
            "user_id": (profile or {}).get("id") or (profile or {}).get("user_id") or "",
            "subsite_name": APP_SCOPE,
            "return_url": return_url,
        }
        if include_token and active_token:
            query_payload["token"] = active_token
            query_payload["api_web_token"] = active_token

        query = urllib.parse.urlencode(query_payload)
        return f"{MEMBERSHIP_PAY_PAGE}?{query}"

    def _refresh_profile_row(self, cursor, token: str):
        cursor.execute(
            """
            SELECT
                s.session_id,
                s.login_token,
                s.api_web_token,
                s.upstream_access_token,
                s.expired_at,
                s.status AS session_status,
                p.id AS profile_id,
                p.app_user_id,
                p.global_user_id,
                p.app_scope,
                p.nickname AS profile_nickname,
                p.avatar AS profile_avatar,
                p.is_vip,
                p.vip_level,
                p.vip_expire_time,
                p.is_permanent_vip,
                p.trial_started_at,
                p.trial_expire_time,
                p.daily_used_count,
                p.daily_limit_count,
                p.last_quota_reset_date,
                p.max_file_size,
                p.allow_batch,
                p.allow_no_watermark,
                i.oauth_user_id,
                i.username,
                i.nickname AS identity_nickname,
                i.avatar AS identity_avatar,
                i.email,
                i.phone
            FROM app_user_session s
            INNER JOIN app_user_profile p ON p.app_user_id = s.app_user_id
            INNER JOIN global_user_identity i ON i.global_user_id = s.global_user_id
            WHERE s.login_token = %s AND s.status = 'ACTIVE' AND p.app_scope = %s
            LIMIT 1
            """,
            (token, APP_SCOPE),
        )
        return cursor.fetchone()

    def _reset_daily_quota_if_needed(self, cursor, row: dict) -> bool:
        today = date.today()
        if row.get("last_quota_reset_date") == today:
            return False
        cursor.execute(
            """
            UPDATE app_user_profile
            SET daily_used_count = 0, last_quota_reset_date = %s, updated_at = CURRENT_TIMESTAMP
            WHERE app_user_id = %s
            """,
            (today, row["app_user_id"]),
        )
        row["daily_used_count"] = 0
        row["last_quota_reset_date"] = today
        return True

    def _build_profile_payload(self, row: dict) -> Optional[dict]:
        if not row:
            return None

        now = datetime.utcnow()
        vip_expire_time = row.get("vip_expire_time")
        trial_expire_time = row.get("trial_expire_time")
        vip_active = bool(row.get("is_permanent_vip"))
        if not vip_active and row.get("is_vip"):
            vip_active = vip_expire_time is None or vip_expire_time >= now
        trial_active = bool(trial_expire_time and trial_expire_time >= now and not vip_active)

        if vip_active:
            access_state = "member_active"
        elif trial_active:
            access_state = "trial"
        else:
            access_state = "upgrade_required"

        daily_limit_count = 999999 if vip_active else int(row.get("daily_limit_count") or FREE_DAILY_LIMIT)
        daily_used_count = int(row.get("daily_used_count") or 0)
        remaining_daily_count = 999999 if vip_active else max(daily_limit_count - daily_used_count, 0)
        remaining_anchor = vip_expire_time if vip_active else trial_expire_time
        remaining_days = self._compute_remaining_days(remaining_anchor)

        return {
            "profile_id": row.get("profile_id"),
            "session_id": row.get("session_id"),
            "global_user_id": row.get("global_user_id"),
            "user_id": row.get("app_user_id"),
            "id": row.get("oauth_user_id") or row.get("app_user_id"),
            "username": row.get("username"),
            "nickname": row.get("profile_nickname") or row.get("identity_nickname") or row.get("username"),
            "avatar": row.get("profile_avatar") or row.get("identity_avatar"),
            "email": row.get("email"),
            "phone": row.get("phone"),
            "token": row.get("login_token"),
            "api_web_token": row.get("api_web_token") or row.get("upstream_access_token"),
            "app_scope": row.get("app_scope") or APP_SCOPE,
            "is_vip": vip_active,
            "vip_level": int(row.get("vip_level") or 0),
            "vip_expire_time": self._format_datetime(vip_expire_time),
            "is_permanent_vip": bool(row.get("is_permanent_vip")),
            "trial_active": trial_active,
            "trial_started_at": self._format_datetime(row.get("trial_started_at")),
            "trial_expire_time": self._format_datetime(trial_expire_time),
            "remaining_days": remaining_days,
            "access_state": access_state,
            "daily_used_count": daily_used_count,
            "daily_limit_count": daily_limit_count,
            "remaining_daily_count": remaining_daily_count,
            "max_file_size": VIP_MAX_FILE_SIZE if vip_active else int(row.get("max_file_size") or FREE_MAX_FILE_SIZE),
            "allow_batch": bool(row.get("allow_batch") or vip_active),
            "allow_no_watermark": bool(row.get("allow_no_watermark") or vip_active),
            "disable_watermark": bool(row.get("allow_no_watermark") or vip_active),
        }

    def _build_user_info(self, profile: dict) -> dict:
        return {
            "id": profile.get("id"),
            "user_id": profile.get("user_id"),
            "profile_id": profile.get("profile_id"),
            "username": profile.get("username"),
            "nickname": profile.get("nickname"),
            "avatar": profile.get("avatar"),
            "email": profile.get("email"),
            "phone": profile.get("phone"),
        }

    def _compute_remaining_days(self, anchor: Optional[datetime]) -> Optional[int]:
        if not anchor:
            return None
        delta = anchor - datetime.utcnow()
        return max(delta.days + (1 if delta.seconds > 0 else 0), 0)

    def _format_datetime(self, value: Optional[datetime]) -> Optional[str]:
        if not value:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
