from __future__ import annotations

# backend/api/routes.py
import base64
import hashlib
import hmac
import json
import os
import time
import threading
import urllib.error
import urllib.request
import urllib.parse
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from typing import Optional, List
from pydantic import BaseModel
from backend.services.converter_service import ConverterService, UPLOAD_DIR, DOWNLOAD_DIR
from backend.services.user_center_service import UserCenterService, UserCenterError
from backend.utils.logger import logger
from backend.utils.file_handler import FileHandler
from backend.utils.validator import Validator
from backend.utils.diagnostics import run_all_diagnostics

router = APIRouter()
converter_service = ConverterService()
file_handler = FileHandler(UPLOAD_DIR)
validator = Validator()
user_center_service = UserCenterService()

AUTH_BASE_URL = "https://api-web.kunqiongai.com"
LOGIN_SECRET_KEY = os.environ.get("DESKTOP_LOGIN_SECRET_KEY", "")
MEMBERSHIP_SUBSITE_NAME = os.environ.get("MEMBERSHIP_SUBSITE_NAME", "https://doc.kunqiongai.com/")
TRIAL_DAYS = int(os.environ.get("MEMBERSHIP_TRIAL_DAYS", "7"))
MEMBERSHIP_PAY_PAGE = os.environ.get("MEMBERSHIP_PAY_PAGE", "https://kunqiongai.com/web_member_pay.html")
OAUTH_AUTHORIZE_URL = os.environ.get("OAUTH_AUTHORIZE_URL", "https://login.kunqiongai.com/authorize.html")
OAUTH_TOKEN_URL = os.environ.get("OAUTH_TOKEN_URL", "https://login.kunqiongai.com/api/oauth/token")
OAUTH_LOGIN_URL = os.environ.get("OAUTH_LOGIN_URL", "https://login.kunqiongai.com/login.html")
OAUTH_SCOPE = os.environ.get("OAUTH_SCOPE", "basic")
DEV_OAUTH_CLIENT_ID = os.environ.get("DEV_OAUTH_CLIENT_ID", "")
DEV_OAUTH_CLIENT_SECRET = os.environ.get("DEV_OAUTH_CLIENT_SECRET", "")
DEV_OAUTH_REDIRECT_URI = os.environ.get("DEV_OAUTH_REDIRECT_URI", "http://localhost:5176/oauth/callback")
DEV_OAUTH_REDIRECT_URIS = {
    DEV_OAUTH_REDIRECT_URI,
    "http://localhost:5176/oauth/callback",
    "http://127.0.0.1:5176/oauth/callback",
}
PROD_OAUTH_CLIENT_ID = os.environ.get("PROD_OAUTH_CLIENT_ID", "")
PROD_OAUTH_CLIENT_SECRET = os.environ.get("PROD_OAUTH_CLIENT_SECRET", "")
PROD_OAUTH_REDIRECT_URI = os.environ.get("PROD_OAUTH_REDIRECT_URI", "https://doc.kunqiongai.com/oauth/callback")
PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "")
TRIAL_STATE_CACHE = {}
TRIAL_STATE_LOCK = threading.Lock()
TRIAL_STATE_FILE = Path(__file__).resolve().parents[1] / "data" / "trial_state.json"
USER_ID_CACHE = {}
LOCAL_SESSION_CACHE = {}
MEMBERSHIP_CACHE = {}
MEMBERSHIP_CACHE_LOCK = threading.Lock()
MEMBERSHIP_CACHE_TTL_SECONDS = float(os.environ.get("MEMBERSHIP_CACHE_TTL_SECONDS", "20"))
UPSTREAM_TOKEN_VALIDATION_CACHE = {}
UPSTREAM_TOKEN_VALIDATION_LOCK = threading.Lock()
UPSTREAM_TOKEN_VALIDATION_TTL_SECONDS = int(os.environ.get("UPSTREAM_TOKEN_VALIDATION_TTL_SECONDS", "20"))
LOGIN_USERINFO_FETCH_TIMEOUT_SECONDS = float(os.environ.get("LOGIN_USERINFO_FETCH_TIMEOUT_SECONDS", "3"))

FREE_DAILY_LIMIT = int(os.environ.get("FREE_DAILY_LIMIT", "10"))
FREE_MAX_FILE_SIZE = int(os.environ.get("FREE_MAX_FILE_SIZE", str(50 * 1024 * 1024)))
VIP_MAX_FILE_SIZE = int(os.environ.get("VIP_MAX_FILE_SIZE", str(500 * 1024 * 1024)))


class LoginUrlPayload(BaseModel):
    redirect_uri: Optional[str] = None
    redirectUri: Optional[str] = None
    state: Optional[str] = None


class OAuthExchangePayload(BaseModel):
    code: str
    state: Optional[str] = None
    redirectUri: Optional[str] = None
    redirect_uri: Optional[str] = None


def _debug_token_tail(value: str) -> str:
    token = str(value or "").strip()
    return token[-8:] if token else "-"


def _encode_signed_nonce(signed_nonce: dict) -> str:
    encoded = base64.urlsafe_b64encode(
        json.dumps(signed_nonce, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8")
    return encoded.rstrip("=")


def _generate_signed_nonce() -> dict:
    nonce = uuid.uuid4().hex
    timestamp = int(time.time())
    message = f"{nonce}|{timestamp}".encode("utf-8")
    signature = base64.b64encode(
        hmac.new(LOGIN_SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    ).decode("utf-8")
    return {
        "nonce": nonce,
        "timestamp": timestamp,
        "signature": signature,
    }


def _fetch_base_web_login_url() -> str:
    request = urllib.request.Request(
        f"{AUTH_BASE_URL}/soft_desktop/get_web_login_url",
        data=b"",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("code") == 1 and payload.get("data", {}).get("login_url"):
        return payload["data"]["login_url"]

    raise ValueError(payload.get("msg") or "Failed to fetch login URL")


def _request_api_web(path: str, body: dict, api_web_token: str) -> dict:
    form_body = urllib.parse.urlencode(body).encode("utf-8")
    request = urllib.request.Request(
        f"{AUTH_BASE_URL}{path}",
        data=form_body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "token": api_web_token
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_api_web_json(path: str, api_web_token: str, timeout: float = 15) -> dict:
    request = urllib.request.Request(
        f"{AUTH_BASE_URL}{path}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "token": api_web_token
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_api_web_form(path: str, body: dict, api_web_token: str) -> dict:
    form_body = urllib.parse.urlencode(body).encode("utf-8")
    request = urllib.request.Request(
        f"{AUTH_BASE_URL}{path}",
        data=form_body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "token": api_web_token
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_oauth_token(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    form_body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }).encode("utf-8")
    request = urllib.request.Request(
        OAUTH_TOKEN_URL,
        data=form_body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_token_candidate(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _first_non_blank(*values) -> str:
    for value in values:
        candidate = _read_token_candidate(value)
        if candidate:
            return candidate
    return ""


GUEST_TOKEN = "__guest_bypass_token__"

GUEST_USER_INFO = {
    "id": "guest_001",
    "user_id": "guest_001",
    "username": "访客",
    "nickname": "访客用户",
    "email": "",
    "phone": "",
    "avatar": "",
}

GUEST_PROFILE = {
    "user_id": "guest_001",
    "username": "访客",
    "nickname": "访客用户",
    "email": "",
    "phone": "",
    "avatar": "",
    "is_vip": False,
    "vip_level": 0,
    "access_state": "free",
    "remaining_daily_count": 3,
    "remaining_days": 0,
    "allow_batch": False,
    "trial_active": False,
    "payment_url": "",
    "payment_auth_expired": False,
    "access_code": "",
    "daily_used_count": 0,
    "daily_limit": 3,
}

def _extract_api_web_token(request: Request) -> str:
    token = request.headers.get("token")
    if token:
        return token.strip()
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    # 跳过登录：未登录用户使用访客 token
    return GUEST_TOKEN


def _request_meta(request: Request) -> dict:
    client_host = request.client.host if request.client else None
    return {
        "client_ip": client_host,
        "user_agent": request.headers.get("user-agent"),
    }


def _resolve_upstream_token(local_token: str) -> str:
    if local_token == GUEST_TOKEN:
        raise HTTPException(status_code=401, detail={
            "success": False,
            "code": "login_expired",
            "message": "访客用户不支持支付功能，请登录后重试",
        })
    now = time.time()
    with UPSTREAM_TOKEN_VALIDATION_LOCK:
        cached = UPSTREAM_TOKEN_VALIDATION_CACHE.get(local_token)
        if cached:
            checked_at = float(cached.get("checked_at") or 0)
            cached_token = str(cached.get("token") or "").strip()
            if cached_token and now - checked_at < UPSTREAM_TOKEN_VALIDATION_TTL_SECONDS:
                return cached_token

    api_web_token = user_center_service.resolve_valid_api_web_token(local_token)
    if api_web_token:
        try:
            payload = _request_api_web_json("/soft_desktop/get_user_info", api_web_token)
            if (payload.get("code") == 1) or ((payload.get("data") or {}).get("user_info")) or ((payload.get("data") or {}).get("user")):
                with UPSTREAM_TOKEN_VALIDATION_LOCK:
                    UPSTREAM_TOKEN_VALIDATION_CACHE[local_token] = {
                        "token": api_web_token,
                        "checked_at": now,
                    }
                return api_web_token
        except urllib.error.HTTPError:
            pass
        except urllib.error.URLError:
            pass

    refreshed = user_center_service.refresh_upstream_session(local_token)
    refreshed_token = ((refreshed or {}).get("api_web_token") or (refreshed or {}).get("upstream_access_token") or "").strip()
    if refreshed_token:
        try:
            payload = _request_api_web_json("/soft_desktop/get_user_info", refreshed_token)
            if (payload.get("code") == 1) or ((payload.get("data") or {}).get("user_info")) or ((payload.get("data") or {}).get("user")):
                with UPSTREAM_TOKEN_VALIDATION_LOCK:
                    UPSTREAM_TOKEN_VALIDATION_CACHE[local_token] = {
                        "token": refreshed_token,
                        "checked_at": time.time(),
                    }
                return refreshed_token
        except urllib.error.HTTPError:
            pass
        except urllib.error.URLError:
            pass

    with UPSTREAM_TOKEN_VALIDATION_LOCK:
        UPSTREAM_TOKEN_VALIDATION_CACHE.pop(local_token, None)

    raise HTTPException(status_code=401, detail={
        "success": False,
        "code": "login_expired",
        "message": "登录会话已过期或不支持支付（请重新登录获取支付凭证）",
    })


def _fetch_subsite_membership(local_token: str, use_cache: bool = True) -> dict:
    started_at = time.time()
    if use_cache:
        with MEMBERSHIP_CACHE_LOCK:
            cached = MEMBERSHIP_CACHE.get(local_token)
            if cached and time.time() - float(cached.get("cached_at") or 0) < MEMBERSHIP_CACHE_TTL_SECONDS:
                payload = cached.get("payload")
                if payload:
                    logger.info(
                        "[membership_fetch] token_tail=%s source=cache elapsed_ms=%s active=%s expire=%s",
                        _debug_token_tail(local_token),
                        round((time.time() - started_at) * 1000, 2),
                        payload.get("web_member_active"),
                        payload.get("web_member_expire_at") or "-",
                    )
                    return dict(payload)
    try:
        upstream_token = _resolve_upstream_token(local_token)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        return {
            "packages": [],
            "web_member_expire_at": None,
            "web_member_active": None,
            "subsite_name": MEMBERSHIP_SUBSITE_NAME,
            "upstream_status": "login_expired" if detail.get("code") == "login_expired" else "unavailable",
            "upstream_message": detail.get("message") or "支付登录态已失效",
        }
    try:
        payload = _request_api_web_form(
            "/user/get_web_member_package_info",
            {"subsite_name": MEMBERSHIP_SUBSITE_NAME},
            upstream_token,
        )
        if payload.get("code") != 1:
            raise HTTPException(status_code=400, detail={
                "success": False,
                "code": "membership_fetch_failed",
                "message": payload.get("msg") or "获取会员状态失败",
            })
        data = payload.get("data") or {}
        result = {
            "packages": data.get("packages", []),
            "web_member_expire_at": data.get("web_member_expire_at"),
            "web_member_active": bool(data.get("web_member_active")),
            "subsite_name": data.get("subsite_name") or MEMBERSHIP_SUBSITE_NAME,
            "upstream_status": "ok",
            "upstream_message": "",
        }
        with MEMBERSHIP_CACHE_LOCK:
            MEMBERSHIP_CACHE[local_token] = {
                "cached_at": time.time(),
                "payload": dict(result),
            }
        logger.info(
            "[membership_fetch] token_tail=%s source=upstream elapsed_ms=%s active=%s expire=%s",
            _debug_token_tail(local_token),
            round((time.time() - started_at) * 1000, 2),
            result.get("web_member_active"),
            result.get("web_member_expire_at") or "-",
        )
        return result
    except urllib.error.HTTPError:
        return {
            "packages": [],
            "web_member_expire_at": None,
            "web_member_active": None,
            "subsite_name": MEMBERSHIP_SUBSITE_NAME,
            "upstream_status": "unavailable",
            "upstream_message": "获取主站会员状态失败",
        }
    except urllib.error.URLError:
        return {
            "packages": [],
            "web_member_expire_at": None,
            "web_member_active": None,
            "subsite_name": MEMBERSHIP_SUBSITE_NAME,
            "upstream_status": "unavailable",
            "upstream_message": "主站会员服务暂时不可用",
        }


def _membership_changed(membership: dict, previous_expire_at: str = "", previous_active: Optional[bool] = None) -> bool:
    current_expire_at = str(membership.get("web_member_expire_at") or "").strip()
    current_active = membership.get("web_member_active")

    if previous_active is not None and current_active is not None and bool(current_active) != bool(previous_active):
        return True

    if previous_expire_at:
        return current_expire_at and current_expire_at != previous_expire_at

    return bool(current_expire_at) if current_active else False


def _fetch_subsite_membership_until_changed(
    local_token: str,
    previous_expire_at: str = "",
    previous_active: Optional[bool] = None,
    timeout_seconds: int = 4,
    interval_seconds: float = 0.8,
) -> dict:
    started_at = time.time()
    latest = _fetch_subsite_membership(local_token, use_cache=False)
    current_expire_at = str(latest.get("web_member_expire_at") or "").strip()
    current_active = latest.get("web_member_active")
    if (
        previous_active is True
        and current_active is True
        and previous_expire_at
        and current_expire_at == previous_expire_at
    ):
        logger.info(
            "[membership_sync] phase=short_circuit token_tail=%s prev_expire=%s prev_active=%s curr_expire=%s curr_active=%s elapsed_ms=%s",
            _debug_token_tail(local_token),
            previous_expire_at or "-",
            previous_active,
            current_expire_at or "-",
            current_active,
            round((time.time() - started_at) * 1000, 2),
        )
        return latest
    changed = _membership_changed(latest, previous_expire_at=previous_expire_at, previous_active=previous_active)
    logger.info(
        "[membership_sync] phase=initial token_tail=%s prev_expire=%s prev_active=%s curr_expire=%s curr_active=%s changed=%s",
        _debug_token_tail(local_token),
        previous_expire_at or "-",
        previous_active,
        str(latest.get("web_member_expire_at") or "-"),
        latest.get("web_member_active"),
        changed,
    )
    if changed:
        return latest

    iteration = 0
    while time.time() - started_at < timeout_seconds:
        time.sleep(interval_seconds)
        iteration += 1
        latest = _fetch_subsite_membership(local_token, use_cache=False)
        changed = _membership_changed(latest, previous_expire_at=previous_expire_at, previous_active=previous_active)
        logger.info(
            "[membership_sync] phase=poll iteration=%s token_tail=%s prev_expire=%s prev_active=%s curr_expire=%s curr_active=%s changed=%s",
            iteration,
            _debug_token_tail(local_token),
            previous_expire_at or "-",
            previous_active,
            str(latest.get("web_member_expire_at") or "-"),
            latest.get("web_member_active"),
            changed,
        )
        if changed:
            return latest

    logger.info(
        "[membership_sync] phase=timeout token_tail=%s prev_expire=%s prev_active=%s final_expire=%s final_active=%s elapsed_ms=%s",
        _debug_token_tail(local_token),
        previous_expire_at or "-",
        previous_active,
        str(latest.get("web_member_expire_at") or "-"),
        latest.get("web_member_active"),
        round((time.time() - started_at) * 1000, 2),
    )
    return latest


def _merge_profile_with_membership(local_token: str, membership: Optional[dict] = None) -> dict:
    started_at = time.time()
    membership = membership or _fetch_subsite_membership(local_token)
    try:
        profile = user_center_service.get_user_profile(local_token)
    except Exception as exc:
        logger.warning(
            "[membership_merge] fallback_to_upstream token_tail=%s error=%s",
            _debug_token_tail(local_token),
            exc,
        )
        profile = _build_user_profile(local_token)
    upstream_member_active = membership.get("web_member_active")
    upstream_status = membership.get("upstream_status") or ""
    is_vip = bool(profile.get("is_vip"))
    vip_expire_time = profile.get("vip_expire_time")
    if upstream_member_active is not None:
        is_vip = bool(upstream_member_active)
        vip_expire_time = membership.get("web_member_expire_at") or vip_expire_time
        snapshot_changed = (
            bool(profile.get("is_vip")) != is_vip
            or str(profile.get("vip_expire_time") or "") != str(vip_expire_time or "")
            or int(profile.get("vip_level") or 0) != (1 if is_vip else 0)
        )
        if snapshot_changed:
            user_center_service.update_membership_snapshot(
                local_token,
                is_vip=is_vip,
                vip_level=1 if is_vip else 0,
                vip_expire_time=vip_expire_time,
            )

    profile["is_vip"] = is_vip
    profile["vip_level"] = 1 if is_vip else 0
    profile["vip_expire_time"] = vip_expire_time
    profile["subsite_name"] = membership.get("subsite_name")
    profile["packages"] = membership.get("packages", [])
    profile["payment_auth_expired"] = upstream_status == "login_expired"
    profile["access_code"] = "upstream_login_expired" if profile["payment_auth_expired"] else ""
    profile["payment_url"] = ""
    if is_vip:
        profile["access_state"] = "member_active"
        if vip_expire_time:
            try:
                expire_dt = datetime.strptime(vip_expire_time, "%Y-%m-%d %H:%M:%S")
                delta = expire_dt - datetime.utcnow()
                profile["remaining_days"] = max(delta.days + (1 if delta.seconds > 0 else 0), 0)
            except ValueError:
                pass
    logger.info(
        "[membership_merge] token_tail=%s elapsed_ms=%s is_vip=%s access_state=%s upstream_status=%s",
        _debug_token_tail(local_token),
        round((time.time() - started_at) * 1000, 2),
        profile.get("is_vip"),
        profile.get("access_state"),
        upstream_status or "-",
    )
    return profile


def _assert_processing_access(local_token: str, origin: str = "http://localhost:5176") -> dict:
    # 跳过登录：所有访客均拥有无限访问权限
    return {
        "is_vip": True,
        "vip_level": 1,
        "access_state": "member_active",
        "remaining_daily_count": 999999,
        "remaining_days": 999,
        "allow_batch": True,
        "trial_active": False,
        "payment_url": "",
        "payment_auth_expired": False,
        "access_code": "",
    }


def _build_oauth_state() -> str:
    return uuid.uuid4().hex


def _get_request_origin(request: Optional[Request]) -> str:
    if not request:
        return ""
    origin = (request.headers.get("origin") or "").strip().rstrip("/")
    if origin:
        return origin

    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    host = forwarded_host or (request.headers.get("host") or "").strip()
    if not host:
        return ""
    proto = forwarded_proto or str(request.url.scheme or "http")
    return f"{proto}://{host}".rstrip("/")


def _resolve_redirect_uri(redirect_uri: str, request: Optional[Request] = None) -> tuple[str, str, str]:
    normalized = (redirect_uri or "").strip()
    if normalized in DEV_OAUTH_REDIRECT_URIS:
        return DEV_OAUTH_CLIENT_ID, DEV_OAUTH_CLIENT_SECRET, normalized
    if normalized == PROD_OAUTH_REDIRECT_URI:
        return PROD_OAUTH_CLIENT_ID, PROD_OAUTH_CLIENT_SECRET, PROD_OAUTH_REDIRECT_URI

    dynamic_prod_redirects = []
    if PUBLIC_SITE_URL:
        dynamic_prod_redirects.append(f"{PUBLIC_SITE_URL.rstrip('/')}/oauth/callback")
    request_origin = _get_request_origin(request)
    if request_origin:
        dynamic_prod_redirects.append(f"{request_origin}/oauth/callback")
    if normalized in dynamic_prod_redirects:
        return PROD_OAUTH_CLIENT_ID, PROD_OAUTH_CLIENT_SECRET, normalized

    raise HTTPException(status_code=400, detail=f"Unsupported redirect_uri: {redirect_uri}")


def _normalize_user_info_payload(payload: dict) -> dict:
    data = (payload or {}).get("data") or {}
    user_info = data.get("user_info") or data.get("user") or {}
    user_id = user_info.get("user_id") or user_info.get("id") or ""
    return {
        "id": user_id,
        "username": user_info.get("username") or user_info.get("nickname") or "",
        "nickname": user_info.get("nickname") or user_info.get("username") or "",
        "email": user_info.get("email"),
        "phone": user_info.get("phone"),
        "avatar": user_info.get("avatar"),
    }


def _build_user_info_from_oauth_payload(remote_user: dict) -> dict:
    remote_user = remote_user or {}
    return {
        "id": remote_user.get("id") or remote_user.get("user_id") or "",
        "username": remote_user.get("username") or remote_user.get("nickname") or "",
        "nickname": remote_user.get("nickname") or remote_user.get("username") or "",
        "email": remote_user.get("email"),
        "phone": remote_user.get("phone"),
        "avatar": remote_user.get("avatar"),
    }


def _normalize_return_url(return_url: Optional[str], request: Request) -> str:
    fallback_origin = request.headers.get("origin", "http://localhost:5176")
    raw = (return_url or "").strip()
    if not raw:
        return f"{fallback_origin}/account?returnTo=%2F"

    if raw.startswith("http://") or raw.startswith("https://"):
        return raw

    if raw.startswith("/"):
        return f"{fallback_origin}{raw}"

    return f"{fallback_origin}/{raw.lstrip('/')}"


def _build_fallback_user_profile(user_info: dict) -> dict:
    fallback_token = str(user_info.get("_session_token") or "")
    trial_state = _compute_trial_state(fallback_token) if fallback_token else {
        "trial_active": True,
        "trial_started_at": None,
        "trial_expire_time": None,
    }
    trial_expire_time = trial_state.get("trial_expire_time")
    remaining_days = FREE_DAILY_LIMIT
    if trial_expire_time:
        try:
            expire_dt = datetime.fromisoformat(str(trial_expire_time).replace("Z", ""))
            delta = expire_dt - datetime.utcnow()
            remaining_days = max(delta.days + (1 if delta.seconds > 0 else 0), 0)
        except Exception:
            remaining_days = FREE_DAILY_LIMIT

    return {
        "user_id": str(user_info.get("id") or ""),
        "is_vip": False,
        "vip_level": 0,
        "vip_expire_time": None,
        "daily_limit_count": FREE_DAILY_LIMIT,
        "daily_used_count": 0,
        "remaining_daily_count": FREE_DAILY_LIMIT,
        "max_file_size": FREE_MAX_FILE_SIZE,
        "allow_batch": False,
        "allow_no_watermark": False,
        "trial_active": bool(trial_state.get("trial_active", True)),
        "trial_started_at": trial_state.get("trial_started_at"),
        "trial_expire_time": trial_expire_time,
        "remaining_days": remaining_days,
        "access_state": "trial",
    }


def _fetch_remote_user_info(api_web_token: str, timeout: float = 15) -> dict:
    payload = _request_api_web_json("/soft_desktop/get_user_info", api_web_token, timeout=timeout)
    return _normalize_user_info_payload(payload)


def _build_user_profile(api_web_token: str) -> dict:
    membership_state = _fetch_membership_state(api_web_token)
    user_info = _fetch_remote_user_info(api_web_token)
    is_vip = bool(membership_state.get("web_member_active"))
    daily_limit_count = 999999 if is_vip else FREE_DAILY_LIMIT
    daily_used_count = 0
    remaining_days = None
    expire_at = membership_state.get("web_member_expire_at") or membership_state.get("trial_expire_time")
    if expire_at:
        try:
            expire_dt = datetime.fromisoformat(str(expire_at).replace("Z", ""))
            delta = expire_dt - datetime.utcnow()
            remaining_days = max(delta.days + (1 if delta.seconds > 0 else 0), 0)
        except Exception:
            remaining_days = None

    return {
        "user_id": str(user_info.get("id") or ""),
        "is_vip": is_vip,
        "vip_level": membership_state.get("vip_level") or (1 if is_vip else 0),
        "vip_expire_time": membership_state.get("web_member_expire_at"),
        "daily_limit_count": daily_limit_count,
        "daily_used_count": daily_used_count,
        "remaining_daily_count": max(daily_limit_count - daily_used_count, 0),
        "max_file_size": VIP_MAX_FILE_SIZE if is_vip else FREE_MAX_FILE_SIZE,
        "allow_batch": is_vip,
        "allow_no_watermark": is_vip,
        "trial_active": bool(membership_state.get("trial_active")),
        "trial_started_at": membership_state.get("trial_started_at"),
        "trial_expire_time": membership_state.get("trial_expire_time"),
        "remaining_days": remaining_days,
        "access_state": membership_state.get("access_state"),
    }


def _remember_local_session(access_token: str, user_info: dict, user_profile: dict):
    LOCAL_SESSION_CACHE[access_token] = {
        "user_info": user_info,
        "user_profile": user_profile,
        "recent_records": [],
    }


def _read_local_session(api_web_token: str) -> Optional[dict]:
    return LOCAL_SESSION_CACHE.get(api_web_token)


def _load_trial_state_file() -> dict:
    if not TRIAL_STATE_FILE.exists():
        return {}
    try:
        with TRIAL_STATE_FILE.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _save_trial_state_file(data: dict):
    TRIAL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TRIAL_STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _trial_user_key(api_web_token: str) -> str:
    # Fallback key when user_id is unavailable.
    return hashlib.sha256(api_web_token.encode("utf-8")).hexdigest()


def _resolve_user_id(api_web_token: str) -> str:
    if api_web_token in USER_ID_CACHE:
        return USER_ID_CACHE[api_web_token]
    try:
        payload = _request_api_web_json("/soft_desktop/get_user_info", api_web_token)
        user_info = (payload or {}).get("data", {}).get("user_info", {})
        user_id = user_info.get("user_id") or user_info.get("id")
        if user_id:
            user_id = str(user_id)
            USER_ID_CACHE[api_web_token] = user_id
            return user_id
    except Exception:
        pass
    return ""


def _compute_trial_state(api_web_token: str) -> dict:
    now = datetime.utcnow()
    user_id = _resolve_user_id(api_web_token)
    user_key = f"user:{user_id}" if user_id else f"token:{_trial_user_key(api_web_token)}"
    cache = TRIAL_STATE_CACHE.get(user_key)
    if not cache:
        with TRIAL_STATE_LOCK:
            persisted = _load_trial_state_file()
            cache = persisted.get(user_key)
            if not cache:
                started_at = now
                expire_at = now + timedelta(days=TRIAL_DAYS)
                cache = {
                    "trial_started_at": started_at.isoformat() + "Z",
                    "trial_expire_time": expire_at.isoformat() + "Z",
                }
                persisted[user_key] = cache
                _save_trial_state_file(persisted)
            TRIAL_STATE_CACHE[user_key] = cache
    expire_dt = datetime.fromisoformat(cache["trial_expire_time"].replace("Z", ""))
    return {
        **cache,
        "trial_active": expire_dt > now,
    }


def _normalize_membership_state(package_payload: dict, api_web_token: str) -> dict:
    data = package_payload.get("data") or {}
    trial_state = _compute_trial_state(api_web_token)
    member_active = bool(data.get("web_member_active"))
    trial_active = bool(trial_state.get("trial_active"))
    access_allowed = member_active or trial_active
    access_state = "member_active" if member_active else ("trial" if trial_active else "upgrade_required")

    return {
        "packages": data.get("packages", []),
        "web_member_active": member_active,
        "web_member_expire_at": data.get("web_member_expire_at"),
        "vip_level": data.get("vip_level") or data.get("level") or (1 if member_active else 0),
        "subsite_name": data.get("subsite_name") or MEMBERSHIP_SUBSITE_NAME,
        "trial_active": trial_active,
        "trial_expire_time": trial_state.get("trial_expire_time"),
        "trial_started_at": trial_state.get("trial_started_at"),
        "access_state": access_state,
        "requires_upgrade": not access_allowed,
    }


def _fetch_membership_state(api_web_token: str) -> dict:
    payload = _request_api_web(
        "/user/get_web_member_package_info",
        {"subsite_name": MEMBERSHIP_SUBSITE_NAME},
        api_web_token,
    )
    return _normalize_membership_state(payload, api_web_token)


def _assert_membership_access(api_web_token: str):
    state = _fetch_membership_state(api_web_token)
    if not state["requires_upgrade"]:
        return
    raise HTTPException(status_code=403, detail={
        "success": False,
        "code": "membership_required",
        "message": "7天免费试用已结束，请开通会员后继续使用",
        "access_state": state["access_state"],
        "requires_upgrade": True,
    })

@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}

@router.get("/diagnostics")
async def diagnostics():
    """诊断环境接口"""
    return run_all_diagnostics()


@router.post("/auth/login-url")
async def get_auth_login_url(payload: LoginUrlPayload, request: Request):
    try:
        redirect_uri = payload.redirect_uri or payload.redirectUri or DEV_OAUTH_REDIRECT_URI
        client_id, _, resolved_redirect_uri = _resolve_redirect_uri(redirect_uri, request)
        state = (payload.state or "").strip() or _build_oauth_state()
        query = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": resolved_redirect_uri,
            "state": state,
            "scope": OAUTH_SCOPE,
        })
        authorize_url = f"{OAUTH_AUTHORIZE_URL}?{query}"
        return {
            "url": f"{OAUTH_LOGIN_URL}?returnUrl={urllib.parse.quote(authorize_url, safe='')}",
            "authorize_url": authorize_url,
            "state": state,
            "redirect_uri": resolved_redirect_uri,
            "client_id": client_id,
        }
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream auth service unavailable: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[auth_login_url] unexpected error redirect_uri=%s", payload.redirect_uri or payload.redirectUri)
        raise HTTPException(status_code=500, detail=f"Failed to build login URL: {exc}") from exc


@router.post("/auth/oauth-exchange")
async def exchange_oauth_code(payload: OAuthExchangePayload, request: Request):
    started_at = time.time()
    redirect_uri = payload.redirectUri or payload.redirect_uri or DEV_OAUTH_REDIRECT_URI
    client_id, client_secret, resolved_redirect_uri = _resolve_redirect_uri(redirect_uri, request)

    try:
        token_started_at = time.time()
        token_payload = _request_oauth_token(
            code=payload.code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=resolved_redirect_uri,
        )
        logger.info(
            "[oauth_exchange_step] step=oauth_token elapsed_ms=%s redirect_uri=%s",
            round((time.time() - token_started_at) * 1000, 2),
            resolved_redirect_uri,
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=exc.code or 502, detail=detail or "OAuth token exchange failed") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"OAuth service unavailable: {exc}") from exc
    except Exception as exc:
        logger.exception("[oauth_exchange_step] step=oauth_token unexpected_error redirect_uri=%s", resolved_redirect_uri)
        raise HTTPException(status_code=502, detail=f"OAuth token exchange failed: {exc}") from exc

    if token_payload.get("code") != 200:
        raise HTTPException(status_code=400, detail=token_payload.get("message") or "OAuth token exchange failed")

    data = token_payload.get("data") or {}
    access_token = data.get("access_token") or token_payload.get("access_token")
    api_web_token = _first_non_blank(
        data.get("api_web_token"),
        token_payload.get("api_web_token"),
        data.get("token"),
        token_payload.get("token"),
        (data.get("user") or {}).get("api_web_token"),
        (data.get("user") or {}).get("token"),
    ) or access_token
    refresh_token = _first_non_blank(
        data.get("refresh_token"),
        token_payload.get("refresh_token"),
    ) or ""
    remote_user = data.get("user") or {}
    if not access_token:
        raise HTTPException(status_code=400, detail="OAuth token response missing access_token")

    user_info = _build_user_info_from_oauth_payload(remote_user)
    should_fetch_remote_user = not user_info.get("id")
    if should_fetch_remote_user:
        try:
            user_fetch_started_at = time.time()
            user_info = _fetch_remote_user_info(
                access_token,
                timeout=LOGIN_USERINFO_FETCH_TIMEOUT_SECONDS,
            )
            logger.info(
                "[oauth_exchange_step] step=remote_user_info elapsed_ms=%s fetched=True",
                round((time.time() - user_fetch_started_at) * 1000, 2),
            )
        except Exception:
            pass

    try:
        session_started_at = time.time()
        session_data = user_center_service.create_or_update_session(
            remote_user=user_info,
            upstream_access_token=access_token,
            request_meta=_request_meta(request),
            api_web_token=api_web_token,
            refresh_token=refresh_token,
        )
        logger.info(
            "[oauth_exchange_step] step=create_local_session elapsed_ms=%s user_id=%s",
            round((time.time() - session_started_at) * 1000, 2),
            user_info.get("id") or user_info.get("user_id") or "-",
        )
    except UserCenterError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"success": False, "code": exc.code, "message": exc.message, **exc.payload},
        ) from exc
    except Exception as exc:
        logger.exception(
            "[oauth_exchange_step] step=create_local_session unexpected_error redirect_uri=%s user_id=%s",
            resolved_redirect_uri,
            user_info.get("id") or user_info.get("user_id") or "-",
        )
        raise HTTPException(status_code=500, detail=f"Failed to create local login session: {exc}") from exc

    logger.info(
        "[oauth_exchange] elapsed_ms=%s redirect_uri=%s user_id=%s local_token_tail=%s api_web_token_tail=%s",
        round((time.time() - started_at) * 1000, 2),
        resolved_redirect_uri,
        (session_data.get("user_profile") or {}).get("user_id") or (session_data.get("user") or {}).get("id") or "-",
        _debug_token_tail(session_data.get("access_token") or ""),
        _debug_token_tail(session_data.get("api_web_token") or ""),
    )

    return {
        "success": True,
        "code": "ok",
        "data": {
            **session_data,
        },
    }


@router.get("/auth/check-login")
async def check_login(request: Request):
    api_web_token = _extract_api_web_token(request)
    if api_web_token == GUEST_TOKEN:
        return {"success": True, "code": "ok", "data": {"logged_in": False}}
    try:
        profile = user_center_service.get_user_profile(api_web_token, allow_missing=True)
        return {"success": True, "code": "ok", "data": {"logged_in": bool(profile)}}
    except UserCenterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception:
        return {"success": True, "code": "ok", "data": {"logged_in": False}}


@router.get("/auth/user-info")
async def get_user_info(request: Request):
    api_web_token = _extract_api_web_token(request)
    if api_web_token == GUEST_TOKEN:
        return {"success": True, "code": "ok", "data": dict(GUEST_USER_INFO)}
    try:
        return {"success": True, "code": "ok", "data": user_center_service.get_user_info(api_web_token)}
    except UserCenterError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"success": False, "code": exc.code, "message": exc.message, **exc.payload},
        ) from exc


@router.get("/auth/user-profile")
async def get_user_profile(request: Request):
    api_web_token = _extract_api_web_token(request)
    if api_web_token == GUEST_TOKEN:
        return {"success": True, "code": "ok", "data": dict(GUEST_PROFILE)}
    started_at = time.time()
    try:
        payload = _merge_profile_with_membership(api_web_token)
        logger.info(
            "[user_profile_api] token_tail=%s elapsed_ms=%s access_state=%s is_vip=%s",
            _debug_token_tail(api_web_token),
            round((time.time() - started_at) * 1000, 2),
            payload.get("access_state"),
            payload.get("is_vip"),
        )
        return {"success": True, "code": "ok", "data": payload}
    except UserCenterError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"success": False, "code": exc.code, "message": exc.message, **exc.payload},
        ) from exc


@router.get("/user-center/recent-records")
async def get_recent_records(request: Request, limit: int = 10):
    api_web_token = _extract_api_web_token(request)
    if api_web_token == GUEST_TOKEN:
        return {"success": True, "code": "ok", "data": []}
    try:
        return {"success": True, "code": "ok", "data": user_center_service.get_recent_records(api_web_token, limit)}
    except UserCenterError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"success": False, "code": exc.code, "message": exc.message, **exc.payload},
        ) from exc


@router.post("/auth/logout")
async def logout(request: Request):
    api_web_token = _extract_api_web_token(request)
    if api_web_token == GUEST_TOKEN:
        return {"success": True, "code": "ok"}
    try:
        user_center_service.logout(api_web_token)
    except UserCenterError:
        pass
    LOCAL_SESSION_CACHE.pop(api_web_token, None)
    with MEMBERSHIP_CACHE_LOCK:
        MEMBERSHIP_CACHE.pop(api_web_token, None)
    with UPSTREAM_TOKEN_VALIDATION_LOCK:
        UPSTREAM_TOKEN_VALIDATION_CACHE.pop(api_web_token, None)
    return {"success": True, "code": "ok"}

@router.post("/convert/json")
async def convert_json(
    request: Request,
    file: UploadFile = File(...),
    target_format: str = Form(...),
    indent: Optional[int] = Form(2),
    sort_keys: Optional[bool] = Form(False)
):
    """
    JSON 转换接口
    """
    input_path = None
    api_web_token = None
    source_format = "json"
    try:
        api_web_token = _extract_api_web_token(request)
        _assert_processing_access(api_web_token, request.headers.get("origin", "http://localhost:5176"))
        # 1. 验证目标格式
        allowed_targets = [tgt for src, tgt in converter_service.converters.keys() if src == source_format]
        target_format = validator.validate_target_format(target_format, allowed_targets)
        
        # 2. 保存上传文件
        input_path = await file_handler.save_upload_file(file)
        
        # 3. 准备转换选项
        options = {
            'indent': indent,
            'sort_keys': sort_keys
        }
        options = validator.validate_json_options(options)
        
        # 4. 执行转换
        result = converter_service.convert_file(
            input_path, 
            target_format, 
            original_filename=file.filename,
            **options
        )
        try:
            user_center_service.record_processing(
                api_web_token,
                tool_name=f"{source_format.upper()} To {target_format.upper()}",
                file_name=file.filename,
                file_size=getattr(file, "size", None),
                source_format=source_format,
                target_format=target_format,
                status="completed",
                result_path=result.get("download_url"),
            )
        except Exception:
            pass
        
        return result
    except UserCenterError as e:
        raise HTTPException(status_code=e.status_code, detail={"success": False, "code": e.code, "message": e.message, **e.payload})
        
    except ValueError as e:
        print(f"ValueError during conversion: {e}")
        if api_web_token:
            try:
                user_center_service.record_processing(
                    api_web_token,
                    tool_name=f"{source_format.upper()} To {target_format.upper()}",
                    file_name=file.filename,
                    file_size=getattr(file, "size", None),
                    source_format=source_format,
                    target_format=target_format,
                    status="failed",
                    result_message=str(e),
                )
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error during conversion: {e}")
        import traceback
        traceback.print_exc()
        if api_web_token:
            try:
                user_center_service.record_processing(
                    api_web_token,
                    tool_name=f"{source_format.upper()} To {target_format.upper()}",
                    file_name=file.filename,
                    file_size=getattr(file, "size", None),
                    source_format=source_format,
                    target_format=target_format,
                    status="failed",
                    result_message=str(e),
                )
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    finally:
        # 5. 清理临时上传文件
        if input_path:
            file_handler.cleanup_file(input_path)

@router.post("/convert/xml")
async def convert_xml(
    request: Request,
    file: UploadFile = File(...),
    target_format: str = Form(...),
    indent: Optional[int] = Form(2),
    sort_keys: Optional[bool] = Form(False)
):
    """
    XML 转换接口
    """
    input_path = None
    api_web_token = None
    source_format = "xml"
    try:
        api_web_token = _extract_api_web_token(request)
        _assert_processing_access(api_web_token, request.headers.get("origin", "http://localhost:5176"))
        # 1. 验证目标格式
        allowed_targets = [tgt for src, tgt in converter_service.converters.keys() if src == source_format]
        target_format = validator.validate_target_format(target_format, allowed_targets)
        
        # 2. 保存上传文件
        input_path = await file_handler.save_upload_file(file)
        
        # 3. 准备转换选项
        options = {
            'indent': indent,
            'sort_keys': sort_keys
        }
        # 复用 JSON 的选项验证逻辑，因为参数相似
        options = validator.validate_json_options(options)
        
        # 4. 执行转换
        result = converter_service.convert_file(
            input_path, 
            target_format, 
            original_filename=file.filename,
            **options
        )
        user_center_service.record_processing(
            api_web_token,
            tool_name=f"{source_format.upper()} To {target_format.upper()}",
            file_name=file.filename,
            file_size=getattr(file, "size", None),
            source_format=source_format,
            target_format=target_format,
            status="completed",
            result_path=result.get("download_url"),
        )
        
        return result
    except UserCenterError as e:
        raise HTTPException(status_code=e.status_code, detail={"success": False, "code": e.code, "message": e.message, **e.payload})
        
    except ValueError as e:
        print(f"ValueError during conversion: {e}")
        if api_web_token:
            user_center_service.record_processing(
                api_web_token,
                tool_name=f"{source_format.upper()} To {target_format.upper()}",
                file_name=file.filename,
                file_size=getattr(file, "size", None),
                source_format=source_format,
                target_format=target_format,
                status="failed",
                result_message=str(e),
            )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error during conversion: {e}")
        import traceback
        traceback.print_exc()
        if api_web_token:
            user_center_service.record_processing(
                api_web_token,
                tool_name=f"{source_format.upper()} To {target_format.upper()}",
                file_name=file.filename,
                file_size=getattr(file, "size", None),
                source_format=source_format,
                target_format=target_format,
                status="failed",
                result_message=str(e),
            )
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    finally:
        # 5. 清理临时上传文件
        if input_path:
            file_handler.cleanup_file(input_path)

@router.post("/convert/general")
async def convert_general(
    request: Request,
    file: UploadFile = File(...),
    target_format: str = Form(...),
    # 通用选项
    encoding: Optional[str] = Form('utf-8'),
    # HTML 选项
    enable_preview: Optional[bool] = Form(False),
    code_mode: Optional[bool] = Form(False),  # 新增：代码模式
    css_handling: Optional[str] = Form(None),
    compress_css: Optional[bool] = Form(False),
    custom_css: Optional[str] = Form(None),
    remove_scripts: Optional[bool] = Form(False),
    remove_comments: Optional[bool] = Form(False),
    compress_html: Optional[bool] = Form(False),
    remove_empty_tags: Optional[bool] = Form(False),
    page_size: Optional[str] = Form(None),
    orientation: Optional[str] = Form(None),
    # 图片选项
    quality: Optional[int] = Form(85),
    background_color: Optional[str] = Form('#ffffff'),
    # 水印选项
    watermark_text: Optional[str] = Form(''),
    watermark_opacity: Optional[int] = Form(30),
    watermark_size: Optional[int] = Form(40),
    watermark_color: Optional[str] = Form('#cccccc'),
    watermark_angle: Optional[int] = Form(45),
    watermark_position: Optional[str] = Form('center'),
    # CSV 选项
    csv_delimiter: Optional[str] = Form(None),
    # PDF 页面选择
    pdf_page_selection: Optional[str] = Form(None),
    pdf_page_range: Optional[str] = Form(None),
    # GIF 动画选项
    animation_delay: Optional[int] = Form(100),
    loop_animation: Optional[bool] = Form(True)
):
    """
    通用转换接口 (DOCX, HTML, PDF, TXT)
    """
    print(f"\n{'='*60}")
    print(f"[API] 收到转换请求")
    print(f"[API] 文件名: {file.filename}")
    print(f"[API] 目标格式: {target_format}")
    print(f"{'='*60}\n")
    
    input_path = None
    api_web_token = None
    source_format = None
    try:
        api_web_token = _extract_api_web_token(request)
        _assert_processing_access(api_web_token, request.headers.get("origin", "http://localhost:5176"))
        # 1. 获取源格式
        filename = file.filename
        if not filename:
            raise ValueError("Filename is missing")
        source_format = filename.split('.')[-1].lower()
        print(f"[API] 源格式: {source_format}")
        
        # 2. 验证目标格式
        allowed_targets = [tgt for src, tgt in converter_service.converters.keys() if src == source_format]
        if not allowed_targets:
            raise ValueError(f"Unsupported source format: {source_format}")
            
        target_format = validator.validate_target_format(target_format, allowed_targets)
        print(f"[API] 验证目标格式成功: {target_format}")
        
        # 3. 保存上传文件
        print("[API] 开始保存上传文件...")
        input_path = await file_handler.save_upload_file(file)
        print(f"[API] 文件已保存: {input_path}")
        
        # 4. 准备转换选项
        options = {
            'encoding': encoding,
            'enable_preview': enable_preview,
            'code_mode': code_mode,  # 新增
            'css_handling': css_handling,
            'compress_css': compress_css,
            'custom_css': custom_css,
            'remove_scripts': remove_scripts,
            'remove_comments': remove_comments,
            'compress_html': compress_html,
            'remove_empty_tags': remove_empty_tags,
            'page_size': page_size,
            'orientation': orientation,
            'quality': quality,
            'background_color': background_color,
            'watermark_text': watermark_text,
            'watermark_opacity': watermark_opacity,
            'watermark_size': watermark_size,
            'watermark_color': watermark_color,
            'watermark_angle': watermark_angle,
            'watermark_position': watermark_position,
            'csv_delimiter': csv_delimiter,
            'pdf_page_selection': pdf_page_selection,
            'pdf_page_range': pdf_page_range,
            'animation_delay': animation_delay,
            'loop_animation': loop_animation
        }
        
        # 5. 执行转换
        print(f"[API] 调用 converter_service.convert_file...")
        result = converter_service.convert_file(
            input_path, 
            target_format, 
            original_filename=file.filename,
            **options
        )
        print(f"[API] 转换完成，结果: {result}")
        try:
            user_center_service.record_processing(
                api_web_token,
                tool_name=f"{source_format.upper()} To {target_format.upper()}",
                file_name=file.filename,
                file_size=getattr(file, "size", None),
                source_format=source_format,
                target_format=target_format,
                status="completed",
                result_path=result.get("download_url"),
            )
        except Exception:
            pass  # DB记录失败不影响转换结果
        
        return result
    except UserCenterError as e:
        raise HTTPException(status_code=e.status_code, detail={"success": False, "code": e.code, "message": e.message, **e.payload})
        
    except ValueError as e:
        print(f"[API] ValueError during conversion: {e}")
        if api_web_token and source_format:
            try:
                user_center_service.record_processing(
                    api_web_token,
                    tool_name=f"{source_format.upper()} To {target_format.upper()}",
                    file_name=file.filename,
                    file_size=getattr(file, "size", None),
                    source_format=source_format,
                    target_format=target_format,
                    status="failed",
                    result_message=str(e),
                )
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        # 使用 logger 记录错误堆栈，确保写入日志文件
        from backend.utils.logger import logger
        logger.error(f"[API] Unexpected error during conversion: {e}\n{traceback_str}")
        print(f"[API] Unexpected error during conversion: {e}")
        print(traceback_str)
        if api_web_token and source_format:
            user_center_service.record_processing(
                api_web_token,
                tool_name=f"{source_format.upper()} To {target_format.upper()}",
                file_name=file.filename,
                file_size=getattr(file, "size", None),
                source_format=source_format,
                target_format=target_format,
                status="failed",
                result_message=str(e),
            )
        # 返回详细的错误信息，方便调试
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}\nTraceback: {traceback_str}")
    finally:
        # 6. 清理临时上传文件
        if input_path:
            file_handler.cleanup_file(input_path)


@router.post("/user-center/member-package-info")
async def member_package_info(
    request: Request,
    force_sync: Optional[bool] = Form(False),
    previous_expire_at: Optional[str] = Form(None),
    previous_active: Optional[bool] = Form(None),
):
    api_web_token = _extract_api_web_token(request)
    if api_web_token == GUEST_TOKEN:
        return {
            "success": True,
            "code": "ok",
            "data": {
                "packages": [],
                "web_member_expire_at": None,
                "web_member_active": False,
                "subsite_name": MEMBERSHIP_SUBSITE_NAME,
                "access_state": "free",
                "trial_active": False,
                "trial_started_at": None,
                "trial_expire_time": None,
                "remaining_daily_count": 3,
                "remaining_days": 0,
                "daily_limit": 3,
                "is_vip": False,
                "vip_level": 0,
                "subsite": {},
            },
        }
    started_at = time.time()
    membership = None
    if force_sync:
        sync_started_at = time.time()
        membership = _fetch_subsite_membership_until_changed(
            api_web_token,
            previous_expire_at=(previous_expire_at or "").strip(),
            previous_active=previous_active,
        )
        logger.info(
            "[member_package_info_step] token_tail=%s step=force_sync elapsed_ms=%s",
            _debug_token_tail(api_web_token),
            round((time.time() - sync_started_at) * 1000, 2),
        )
    merge_started_at = time.time()
    profile = _merge_profile_with_membership(api_web_token, membership=membership)
    logger.info(
        "[member_package_info_step] token_tail=%s step=merge_profile elapsed_ms=%s",
        _debug_token_tail(api_web_token),
        round((time.time() - merge_started_at) * 1000, 2),
    )
    logger.info(
        "[member_package_info] token_tail=%s force_sync=%s prev_expire=%s prev_active=%s result_expire=%s result_active=%s access_state=%s elapsed_ms=%s",
        _debug_token_tail(api_web_token),
        force_sync,
        (previous_expire_at or "").strip() or "-",
        previous_active,
        str(profile.get("vip_expire_time") or "-"),
        bool(profile.get("is_vip")),
        profile.get("access_state") or "-",
        round((time.time() - started_at) * 1000, 2),
    )
    return {
        "success": True,
        "code": "ok",
        "data": {
            "packages": profile.get("packages", []),
            "web_member_expire_at": profile.get("vip_expire_time"),
            "web_member_active": bool(profile.get("is_vip")),
            "subsite_name": profile.get("subsite_name") or MEMBERSHIP_SUBSITE_NAME,
            "access_state": profile.get("access_state"),
            "trial_active": profile.get("trial_active"),
            "trial_started_at": profile.get("trial_started_at"),
            "trial_expire_time": profile.get("trial_expire_time"),
            "remaining_days": profile.get("remaining_days"),
        },
    }


@router.get("/membership/plans")
async def membership_plans(request: Request):
    api_web_token = _extract_api_web_token(request)
    membership = _fetch_subsite_membership(api_web_token)
    return {"success": True, "code": "ok", "data": {"packages": membership.get("packages", [])}}


@router.post("/user-center/create-member-order")
async def create_member_order(
    request: Request,
    package_id: str = Form(...),
    pay_type: int = Form(...),
):
    api_web_token = _extract_api_web_token(request)
    if api_web_token == GUEST_TOKEN:
        raise HTTPException(status_code=400, detail={
            "success": False, "code": "guest_not_allowed",
            "message": "访客用户不支持购买会员，请登录后重试",
        })
    upstream_token = _resolve_upstream_token(api_web_token)
    payload = _request_api_web_form(
        "/user/create_web_member_order",
        {
            "package_id": package_id,
            "pay_type": pay_type,
            "subsite_name": MEMBERSHIP_SUBSITE_NAME,
        },
        upstream_token,
    )
    if payload.get("code") != 1:
        raise HTTPException(status_code=400, detail={
            "success": False,
            "code": "create_member_order_failed",
            "message": payload.get("msg") or "创建会员订单失败",
        })
    return payload


@router.post("/user-center/check-member-order-paystatus")
async def check_member_order_status(
    request: Request,
    order_no: str = Form(...),
):
    api_web_token = _extract_api_web_token(request)
    if api_web_token == GUEST_TOKEN:
        raise HTTPException(status_code=400, detail={
            "success": False, "code": "guest_not_allowed",
            "message": "访客用户不支持购买会员，请登录后重试",
        })
    upstream_token = _resolve_upstream_token(api_web_token)
    payload = _request_api_web_form(
        "/user/check_web_member_order_paystatus",
        {"order_no": order_no},
        upstream_token,
    )
    if payload.get("code") != 1:
        raise HTTPException(status_code=400, detail={
            "success": False,
            "code": "check_member_order_failed",
            "message": payload.get("msg") or "查询支付状态失败",
        })
    data = payload.get("data") or {}
    if int(data.get("pay_status") or 0) == 1:
        membership = _fetch_subsite_membership(api_web_token)
        user_center_service.update_membership_snapshot(
            api_web_token,
            is_vip=bool(membership.get("web_member_active")),
            vip_level=1 if membership.get("web_member_active") else 0,
            vip_expire_time=membership.get("web_member_expire_at"),
        )
    return payload


@router.get("/user-center/payment-page-url")
async def get_payment_page_url(request: Request, return_url: Optional[str] = None):
    api_web_token = _extract_api_web_token(request)
    if api_web_token == GUEST_TOKEN:
        return {
            "success": True, "code": "ok",
            "data": {"payment_url": "", "subsite_name": MEMBERSHIP_SUBSITE_NAME,
                      "access_state": "free", "payment_auth_expired": False, "requires_relogin": False,
                      "message": "访客用户无需支付，使用限制次数即可"},
        }
    effective_return_url = _normalize_return_url(return_url, request)
    try:
        _resolve_upstream_token(api_web_token)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        raw_payment_url = user_center_service.build_payment_url(api_web_token, effective_return_url, include_token=False)
        relogin_url = f"{OAUTH_LOGIN_URL}?returnUrl={urllib.parse.quote(raw_payment_url, safe='')}"
        return {
            "success": True,
            "code": "ok",
            "data": {
                "payment_url": relogin_url,
                "subsite_name": MEMBERSHIP_SUBSITE_NAME,
                "access_state": "upgrade_required",
                "payment_auth_expired": True,
                "requires_relogin": True,
                "message": detail.get("message") or "支付登录态已失效，已跳转登录",
            }
        }
    return {
        "success": True,
        "code": "ok",
        "data": {
            "payment_url": user_center_service.build_payment_url(api_web_token, effective_return_url),
            "subsite_name": MEMBERSHIP_SUBSITE_NAME,
            "access_state": "member_active",
        }
    }

@router.post("/batch-download")
async def batch_download(request: Request, files: List[str] = Form(...)):
    """批量打包下载 - 将多个转换结果打包为ZIP文件"""
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    if not files:
        raise HTTPException(status_code=400, detail="No files specified")

    # 安全检查：防止路径遍历攻击
    safe_files = []
    for f in files:
        basename = os.path.basename(f)  # 剥离任何路径信息
        filepath = os.path.join(DOWNLOAD_DIR, basename)
        if not os.path.isfile(filepath):
            continue  # 跳过不存在的文件
        safe_files.append((basename, filepath))

    if not safe_files:
        raise HTTPException(status_code=404, detail="No valid files found for download")

    # 在内存中创建 ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for basename, filepath in safe_files:
            zf.write(filepath, arcname=basename)
    zip_buffer.seek(0)

    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_filename = f"converted-{timestamp}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
        },
    )


@router.get("/health")
async def health_check():
    return {"status": "ok"}
