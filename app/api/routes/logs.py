from fastapi import APIRouter, Depends, File, Query, UploadFile, WebSocket, WebSocketDisconnect, status

from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.log import (
    AlertEvalResponse,
    AlertRuleCreate,
    AlertRuleListResponse,
    AnalysisHistoryResponse,
    AnalyzeResponse,
    AnalyzeStatusResponse,
    BatchLogUploadResponse,
    LogDetailResponse,
    LogListResponse,
    LogUploadResponse,
    StatsResponse,
)
from app.services.log_service import log_service


router = APIRouter()


@router.post("/upload", response_model=LogUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_log(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> LogUploadResponse:
    return await log_service.upload(file, current_user)


@router.post("/upload/batch", response_model=BatchLogUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_logs(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
) -> BatchLogUploadResponse:
    return await log_service.upload_many(files, current_user)


@router.get("", response_model=LogListResponse)
def list_logs(
    keyword: str | None = Query(default=None),
    level: str | None = Query(default=None),
    log_status: str | None = Query(default=None, alias="status"),
    service: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> LogListResponse:
    return log_service.list_logs(current_user, keyword, level, log_status, service, start_time, end_time, page, per_page)


@router.get("/{log_id}", response_model=LogDetailResponse)
def get_log(
    log_id: int,
    keyword: str | None = Query(default=None),
    level: str | None = Query(default=None),
    service: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
) -> LogDetailResponse:
    return log_service.get_log(log_id, current_user, keyword, level, service, start_time, end_time, page, per_page)


@router.post("/{log_id}/analyze", response_model=AnalyzeResponse)
def analyze_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
) -> AnalyzeResponse:
    return log_service.analyze(log_id, current_user)


@router.get("/{log_id}/analyze/status", response_model=AnalyzeStatusResponse)
def get_analyze_status(
    log_id: int,
    current_user: User = Depends(get_current_user),
) -> AnalyzeStatusResponse:
    return log_service.get_analyze_status(log_id, current_user)


@router.get("/{log_id}/analyses", response_model=AnalysisHistoryResponse)
def list_analyses(
    log_id: int,
    current_user: User = Depends(get_current_user),
) -> AnalysisHistoryResponse:
    return log_service.list_analyses(log_id, current_user)


@router.get("/{log_id}/stats", response_model=StatsResponse)
def get_log_stats(
    log_id: int,
    current_user: User = Depends(get_current_user),
) -> StatsResponse:
    return log_service.get_stats(log_id, current_user)


@router.websocket("/{log_id}/analyze/ws")
async def analyze_ws(websocket: WebSocket, log_id: int) -> None:
    await websocket.accept()

    from app.core.security import decode_access_token
    from app.services.task_queue import TASK_EVENTS_KEY, _get_redis, get_task_by_log, get_task_status

    token = websocket.query_params.get("token") or websocket.cookies.get("access_token")
    payload = decode_access_token(token) if token else None
    if not payload or not payload.get("sub"):
        await websocket.send_json({"status": "error", "error": "Authentication required."})
        await websocket.close()
        return

    user_id = int(payload["sub"])

    task_id = get_task_by_log(log_id, user_id)
    if not task_id:
        await websocket.send_json({"status": "none"})
        await websocket.close()
        return

    import json as _json

    r = _get_redis()
    pubsub = r.pubsub()
    pubsub.subscribe(TASK_EVENTS_KEY)

    current = get_task_status(task_id)
    if current:
        await websocket.send_json({"status": current.get("status", "unknown")})
        if current.get("status") in ("completed", "failed"):
            pubsub.unsubscribe()
            await websocket.close()
            return

    terminal_states = {"completed", "failed"}

    try:
        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                event = _json.loads(message["data"])
            except (_json.JSONDecodeError, TypeError):
                continue
            if event.get("task_id") != task_id:
                continue

            data = get_task_status(task_id)
            if data:
                await websocket.send_json({"status": data.get("status", "unknown")})

            if event.get("status") in terminal_states:
                break
    except WebSocketDisconnect:
        pass
    finally:
        pubsub.unsubscribe()


@router.get("/alerts/rules", response_model=AlertRuleListResponse)
def list_alert_rules(current_user: User = Depends(get_current_user)) -> AlertRuleListResponse:
    return log_service.list_alert_rules(current_user)


@router.post("/alerts/rules", response_model=AlertRuleCreate, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    data: AlertRuleCreate,
    current_user: User = Depends(get_current_user),
):
    return log_service.create_alert_rule(current_user, data)


@router.delete("/alerts/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
):
    log_service.delete_alert_rule(rule_id, current_user)


@router.get("/{log_id}/alerts/eval", response_model=AlertEvalResponse)
def evaluate_alerts(
    log_id: int,
    current_user: User = Depends(get_current_user),
) -> AlertEvalResponse:
    return log_service.evaluate_alert_rules(log_id, current_user)
