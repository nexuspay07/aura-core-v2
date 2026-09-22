"""Bounded, content-free aggregate queries for Control Center V1."""
from __future__ import annotations

import base64
import json
import math
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import and_, case, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.db.organization_member_table import organization_member_table
from app.db.personal_decision_table import personal_decision_table
from app.db.usage_log_table import usage_log_table
from app.db.user_table import user_table
from app.db.workspace_member_table import workspace_member_table


CANONICAL_TELEMETRY_SINCE = datetime(2026, 9, 21, tzinfo=timezone.utc)
WINDOWS = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
OUTCOMES = ("success", "partial", "failure", "clarification", "safety")


def resolve_window(window: str, now: datetime | None = None):
    if window not in WINDOWS:
        raise HTTPException(status_code=422, detail="window must be one of: 24h, 7d, 30d")
    end = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return end - WINDOWS[window], end


def _canonical(start, end):
    return and_(usage_log_table.c.request_id.is_not(None), usage_log_table.c.created_at >= start, usage_log_table.c.created_at < end)


def _completeness(start):
    return {
        "request_telemetry": "complete_for_selected_window" if start >= CANONICAL_TELEMETRY_SINCE else "partial_before_canonical_instrumentation",
        "canonical_telemetry_since": CANONICAL_TELEMETRY_SINCE,
    }


def _window_fields(start, end):
    return {"window_start": start, "window_end": end, "generated_at": end, "data_completeness": _completeness(start)}


def _count(db, statement) -> int:
    return int(db.scalar(statement) or 0)


def _latency(db, where):
    valid = and_(where, usage_log_table.c.latency_ms.is_not(None))
    count = _count(db, select(func.count()).select_from(usage_log_table).where(valid))
    average = db.scalar(select(func.avg(usage_log_table.c.latency_ms)).where(valid))
    def percentile(fraction):
        if not count:
            return None
        offset = max(0, math.ceil(count * fraction) - 1)
        return db.scalar(select(usage_log_table.c.latency_ms).where(valid).order_by(usage_log_table.c.latency_ms).offset(offset).limit(1))
    return {"average_latency_ms": round(float(average), 2) if average is not None else None,
            "p50_latency_ms": percentile(.50), "p95_latency_ms": percentile(.95)}


def _tokens(db, where):
    row = db.execute(select(
        func.coalesce(func.sum(usage_log_table.c.input_tokens), 0),
        func.coalesce(func.sum(usage_log_table.c.output_tokens), 0),
        func.coalesce(func.sum(usage_log_table.c.reasoning_tokens), 0),
        func.coalesce(func.sum(usage_log_table.c.tokens_used), 0),
        func.sum(case((usage_log_table.c.tokens_used.is_not(None), 1), else_=0)),
        func.count(),
    ).where(where)).one()
    return {"known_input_tokens": int(row[0]), "known_output_tokens": int(row[1]),
            "known_reasoning_tokens": int(row[2]), "known_total_tokens": int(row[3]),
            "requests_with_token_data": int(row[4] or 0),
            "requests_without_token_data": int(row[5] or 0) - int(row[4] or 0)}


def _distribution(db, where, column):
    rows = db.execute(select(column, func.count()).where(where, column.is_not(None)).group_by(column).order_by(func.count().desc(), column)).all()
    return [{"key": str(key), "count": int(count)} for key, count in rows]


def overview(db: Session, start, end):
    where = _canonical(start, end)
    outcomes = dict(db.execute(select(usage_log_table.c.outcome, func.count()).where(where).group_by(usage_log_table.c.outcome)).all())
    total = sum(int(outcomes.get(item, 0)) for item in OUTCOMES)
    eligible = int(outcomes.get("success", 0)) + int(outcomes.get("partial", 0)) + int(outcomes.get("failure", 0))
    active = select(usage_log_table.c.user_id.label("uid")).where(
        where, usage_log_table.c.user_id.is_not(None)).distinct().subquery()
    returning = _count(db, select(func.count()).select_from(active).where(
        select(func.count()).select_from(usage_log_table).where(
            usage_log_table.c.request_id.is_not(None), usage_log_table.c.user_id == active.c.uid,
            usage_log_table.c.created_at < start).scalar_subquery() > 0))
    return {**_window_fields(start, end),
        "users": {"total_users": _count(db, select(func.count()).select_from(user_table)),
                  "new_users_in_window": _count(db, select(func.count()).select_from(user_table).where(user_table.c.created_at >= start, user_table.c.created_at < end)),
                  "active_users_in_window": _count(db, select(func.count()).select_from(active)), "returning_users_in_window": returning},
        "intelligence": {"total_requests": total, "successful_requests": int(outcomes.get("success", 0)),
            "partial_requests": int(outcomes.get("partial", 0)), "failed_requests": int(outcomes.get("failure", 0)),
            "clarification_requests": int(outcomes.get("clarification", 0)), "safety_requests": int(outcomes.get("safety", 0)),
            "operational_reliability_rate": round(int(outcomes.get("success", 0)) / eligible, 4) if eligible else None},
        "decisions": {"total_saved_decisions": _count(db, select(func.count()).select_from(personal_decision_table)),
                      "new_saved_decisions_in_window": _count(db, select(func.count()).select_from(personal_decision_table).where(personal_decision_table.c.created_at >= start, personal_decision_table.c.created_at < end))},
        "performance": _latency(db, where), "usage": _tokens(db, where),
        "system": {"status": "available", "telemetry_freshness_at": db.scalar(select(func.max(usage_log_table.c.created_at)).where(usage_log_table.c.request_id.is_not(None)))}}


def _encode_cursor(created_at, user_id):
    raw = json.dumps([created_at.isoformat(), user_id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(value):
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        created, user_id = json.loads(raw)
        parsed = datetime.fromisoformat(created)
        return parsed, int(user_id)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid pagination cursor") from exc


def users(db: Session, start, end, page_size: int, cursor: str | None):
    request_agg = select(usage_log_table.c.user_id.label("uid"), func.count().label("requests"),
                         func.max(usage_log_table.c.created_at).label("last_activity")).where(
        usage_log_table.c.request_id.is_not(None)).group_by(usage_log_table.c.user_id).subquery()
    window_agg = select(usage_log_table.c.user_id.label("uid"), func.count().label("requests")).where(
        _canonical(start, end)).group_by(usage_log_table.c.user_id).subquery()
    org_agg = select(organization_member_table.c.user_id.label("uid"), func.count(distinct(organization_member_table.c.organization_id)).label("count")).where(organization_member_table.c.is_active.is_(True)).group_by(organization_member_table.c.user_id).subquery()
    workspace_agg = select(workspace_member_table.c.user_id.label("uid"), func.count(distinct(workspace_member_table.c.workspace_id)).label("count")).where(workspace_member_table.c.is_active.is_(True)).group_by(workspace_member_table.c.user_id).subquery()
    decision_agg = select(personal_decision_table.c.user_id.label("uid"), func.count().label("count")).group_by(personal_decision_table.c.user_id).subquery()
    statement = select(user_table.c.id, user_table.c.email, user_table.c.full_name, user_table.c.created_at,
        user_table.c.is_active, user_table.c.is_verified, func.coalesce(org_agg.c.count, 0), func.coalesce(workspace_agg.c.count, 0),
        request_agg.c.last_activity, func.coalesce(window_agg.c.requests, 0), func.coalesce(decision_agg.c.count, 0)
    ).outerjoin(org_agg, org_agg.c.uid == user_table.c.id).outerjoin(workspace_agg, workspace_agg.c.uid == user_table.c.id
    ).outerjoin(request_agg, request_agg.c.uid == user_table.c.id).outerjoin(window_agg, window_agg.c.uid == user_table.c.id
    ).outerjoin(decision_agg, decision_agg.c.uid == user_table.c.id)
    if cursor:
        created, user_id = _decode_cursor(cursor)
        statement = statement.where(or_(user_table.c.created_at < created, and_(user_table.c.created_at == created, user_table.c.id < user_id)))
    rows = db.execute(statement.order_by(user_table.c.created_at.desc(), user_table.c.id.desc()).limit(page_size + 1)).all()
    more = len(rows) > page_size
    rows = rows[:page_size]
    items = [{"user_id": row[0], "email": row[1], "full_name": row[2], "created_at": row[3],
              "is_active": bool(row[4]), "is_verified": bool(row[5]), "organization_count": int(row[6]),
              "workspace_count": int(row[7]), "last_intelligence_activity": row[8],
              "request_count_in_window": int(row[9]), "saved_decision_count": int(row[10])} for row in rows]
    next_cursor = _encode_cursor(rows[-1][3], rows[-1][0]) if more and rows else None
    return {**_window_fields(start, end), "items": items, "next_cursor": next_cursor, "page_size": page_size}


def intelligence(db: Session, start, end, window_name: str):
    where = _canonical(start, end)
    total = _count(db, select(func.count()).select_from(usage_log_table).where(where))
    dialect = db.get_bind().dialect.name
    bucket = "hour" if window_name == "24h" else "day"
    if dialect == "sqlite":
        expression = func.strftime("%Y-%m-%dT%H:00:00+00:00" if bucket == "hour" else "%Y-%m-%dT00:00:00+00:00", usage_log_table.c.created_at)
    else:
        expression = func.date_trunc(bucket, usage_log_table.c.created_at)
    series = db.execute(select(expression.label("bucket"), func.count(),
        func.sum(case((usage_log_table.c.outcome == "success", 1), else_=0)),
        func.sum(case((usage_log_table.c.outcome == "failure", 1), else_=0))).where(where).group_by(expression).order_by(expression)).all()
    time_series = [{"bucket_start": datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0],
                    "request_count": int(row[1]), "success_count": int(row[2] or 0), "failure_count": int(row[3] or 0)} for row in series]
    known_provider = _count(db, select(func.count()).select_from(usage_log_table).where(where, usage_log_table.c.provider.is_not(None)))
    known_model = _count(db, select(func.count()).select_from(usage_log_table).where(where, usage_log_table.c.model.is_not(None)))
    execution = db.execute(select(func.coalesce(func.sum(usage_log_table.c.retry_count), 0),
        func.sum(case((usage_log_table.c.retry_count > 0, 1), else_=0)),
        func.coalesce(func.sum(usage_log_table.c.provider_call_count), 0),
        func.sum(case((usage_log_table.c.provider_call_count.is_not(None), 1), else_=0))).where(where)).one()
    return {**_window_fields(start, end), "total_requests": total,
        "outcomes": _distribution(db, where, usage_log_table.c.outcome), "routes": _distribution(db, where, usage_log_table.c.route),
        "modes": _distribution(db, where, usage_log_table.c.request_mode), "providers": _distribution(db, where, usage_log_table.c.provider),
        "models": _distribution(db, where, usage_log_table.c.model), "error_categories": _distribution(db, where, usage_log_table.c.error_category),
        "provider_coverage": {"known_provider_requests": known_provider, "unknown_provider_requests": total-known_provider,
                              "known_model_requests": known_model, "unknown_model_requests": total-known_model},
        "tokens": _tokens(db, where), "performance": _latency(db, where),
        "execution": {"total_retries": int(execution[0]), "requests_with_retries": int(execution[1] or 0),
                      "known_provider_calls": int(execution[2]), "requests_with_provider_call_data": int(execution[3] or 0)},
        "bucket": bucket, "time_series": time_series}
