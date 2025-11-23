from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from supabase import Client
from config.settings import settings

from core.supabase import supabase
from dependencies.auth import verify_admin  # 추천: 구조화된 경로

router = APIRouter(tags=["Admin Dashboard"])


# ------------------------------------------------------
# ✅ 1) 크롤링 서버 상태
# ------------------------------------------------------
@router.get("/crawler/status")
async def crawler_status(_: bool = Depends(verify_admin)):
    """크롤링 서버 상태 + 마지막 실행 시간"""

    res = (
        supabase.table("crawl_logs")
        .select("started_at, ended_at")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )

    last = res.data[0] if res.data else None

    return {
        "server_running": True,
        "scheduler_enabled": True,
        "last_started": last["started_at"] if last else None,
        "last_finished": last["ended_at"] if last else None,
        "timestamp": datetime.now().isoformat(),
    }


# ------------------------------------------------------
# ✅ 2) 크롤링 로그 리스트 (최근 100개)
# ------------------------------------------------------
@router.get("/crawler/logs")
async def crawler_logs(_: bool = Depends(verify_admin)):
    """크롤링 실행 이력 조회"""

    res = (
        supabase.table("crawl_logs")
        .select("*")
        .order("started_at", desc=True)
        .limit(100)
        .execute()
    )

    return res.data


# ------------------------------------------------------
# ✅ 3) 회원 리스트
# ------------------------------------------------------
@router.get("/users")
async def get_users(_: bool = Depends(verify_admin)):
    """회원 리스트 + provider + 가입일 + 마지막 로그인 + 등록한 알림 수"""

    # 사용자
    users_res = (
        supabase.table("users")
        .select(
            "id, email, name, provider_name, created_at, updated_at, last_signin_at"
        )
        .execute()
    )
    users = users_res.data or []

    # 알림 Rule 개수
    rules_res = (
        supabase.table("notification_rules")
        .select("user_id, count(*)")
        .group("user_id")
        .execute()
    )
    rule_counts = {r["user_id"]: r["count"] for r in rules_res.data or []}

    # 병합
    result = []
    for u in users:
        result.append(
            {
                "id": u["id"],
                "email": u.get("email"),
                "name": u.get("name"),
                "provider": u.get("provider_name"),
                "created_at": u.get("created_at"),
                "last_signin_at": u.get("last_signin_at") or u.get("updated_at"),
                "rule_count": rule_counts.get(u["id"], 0),
            }
        )

    return result


# ------------------------------------------------------
# ✅ 4) 전체 관리자 대시보드 종합 API
# ------------------------------------------------------
@router.get("/dashboard")
async def admin_dashboard(_: bool = Depends(verify_admin)):
    """관리자 페이지용 종합 데이터"""

    # ---- 크롤링 상태 ----
    status_res = (
        supabase.table("crawl_logs")
        .select("started_at, ended_at")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    last = status_res.data[0] if status_res.data else None

    # ---- 최근 크롤링 로그 20개 ----
    logs_res = (
        supabase.table("crawl_logs")
        .select("*")
        .order("started_at", desc=True)
        .limit(20)
        .execute()
    )

    # ---- 사용자 정보 ----
    users_res = (
        supabase.table("users")
        .select("id, email, name, provider_name, created_at, last_login_at")
        .order("created_at", desc=True)
        .execute()
    )
    users = users_res.data or []

    # ---- 알림 rule 전체 가져와서 Python으로 groupBy ----
    rules_res = supabase.table("notification_rules").select("user_id").execute()
    rules = rules_res.data or []

    rule_counts = {}
    for r in rules:
        uid = r["user_id"]
        rule_counts[uid] = rule_counts.get(uid, 0) + 1

    # ---- 사용자 리스트에 rule_count 추가 ----
    for u in users:
        u["rule_count"] = rule_counts.get(u["id"], 0)

    # ---- 전체 응답 ----
    return {
        "crawler": {
            "server_running": True,
            "scheduler_enabled": True,
            "last_started": last["started_at"] if last else None,
            "last_finished": last["ended_at"] if last else None,
        },
        "logs": logs_res.data,
        "summary": {
            "user_count": len(users),
            "rule_count": len(rules),
        },
        "users": users,
        "timestamp": datetime.now().isoformat(),
    }
