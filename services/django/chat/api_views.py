import json
import uuid

import httpx
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods

from .models import ChatSession, ChatMessage


# ── 공통 유틸 ────────────────────────────────────────────────────────────────


def _chat_base_url():
    return settings.FASTAPI_INTERNAL_CHAT_URL.rstrip("/")


def _internal_headers(user_id, include_content_type=True):
    headers = {
        "X-Internal-Service-Token": settings.INTERNAL_SERVICE_TOKEN,
        "X-User-Id": str(user_id),
    }
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _read_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("유효한 JSON 요청이 필요합니다.")


def _require_authenticated(request):
    """세션 쿠키 또는 JWT Bearer 토큰으로 인증을 확인한다."""
    if request.user.is_authenticated:
        return None

    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

    try:
        jwt_auth = JWTAuthentication()
        result = jwt_auth.authenticate(request)
        if result:
            request.user, _ = result
            return None
    except (InvalidToken, TokenError):
        pass

    return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)


def _serialize_session(session):
    return {
        "session_id": str(session.session_id),
        "title": session.title,
        "target_pet_id": str(session.target_pet_id) if session.target_pet_id else None,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def _serialize_message(msg):
    return {
        "message_id": str(msg.message_id),
        "role": msg.role,
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
    }


# ── FastAPI SSE 프록시 (메시지 전송만) ────────────────────────────────────────


def _stream_and_save(url, payload, user_id, session):
    """FastAPI SSE 스트리밍을 중계하면서 완료된 응답을 DB에 저장한다."""
    headers = _internal_headers(user_id)
    assistant_text = ""

    with httpx.Client(timeout=None) as client:
        with client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code != 200:
                detail = "채팅 요청 처리에 실패했습니다."
                try:
                    detail = response.json().get("detail", detail)
                except Exception:
                    text = response.text.strip()
                    if text:
                        detail = text
                yield f"data: {json.dumps({'type': 'error', 'message': detail}, ensure_ascii=False)}\n\n"
                return

            for chunk in response.iter_bytes():
                if not chunk:
                    continue
                yield chunk

                # done 이벤트 감지 시 assistant 메시지 저장
                for line in chunk.decode("utf-8", errors="ignore").split("\n\n"):
                    if not line.startswith("data: "):
                        continue
                    try:
                        evt = json.loads(line[6:])
                        if evt.get("type") == "token":
                            assistant_text += evt.get("content", "")
                        elif evt.get("type") == "done" and assistant_text:
                            ChatMessage.objects.create(
                                session=session,
                                role="assistant",
                                content=assistant_text,
                            )
                    except (json.JSONDecodeError, KeyError):
                        pass


# ── 세션 CRUD (Django ORM 직접 처리) ─────────────────────────────────────────


@require_http_methods(["GET", "POST"])
def sessions_view(request):
    unauthorized = _require_authenticated(request)
    if unauthorized:
        return unauthorized

    if request.method == "GET":
        sessions = request.user.chat_sessions.order_by("-updated_at")[:50]
        data = [_serialize_session(s) for s in sessions]
        return JsonResponse(data, safe=False)

    # POST: 세션 생성
    try:
        payload = _read_json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    title = (payload.get("title") or "새 대화").strip()
    target_pet_id = payload.get("target_pet_id")

    session = ChatSession.objects.create(
        user=request.user,
        title=title[:100],
        target_pet_id=target_pet_id,
    )
    return JsonResponse(_serialize_session(session), status=201)


@require_http_methods(["PATCH", "DELETE"])
def session_detail_view(request, session_id):
    unauthorized = _require_authenticated(request)
    if unauthorized:
        return unauthorized

    try:
        session = request.user.chat_sessions.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({"detail": "세션을 찾을 수 없습니다."}, status=404)

    if request.method == "DELETE":
        session.delete()
        return JsonResponse({"status": "deleted"}, status=200)

    # PATCH: 제목 수정
    try:
        payload = _read_json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    new_title = (payload.get("title") or "").strip()
    if new_title:
        session.title = new_title[:100]
        session.save(update_fields=["title", "updated_at"])

    return JsonResponse(_serialize_session(session))


# ── 메시지 조회 + SSE 전송 (하이브리드) ──────────────────────────────────────


@require_http_methods(["GET", "POST"])
def session_messages_view(request, session_id):
    unauthorized = _require_authenticated(request)
    if unauthorized:
        return unauthorized

    try:
        session = request.user.chat_sessions.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({"detail": "세션을 찾을 수 없습니다."}, status=404)

    # GET: 메시지 히스토리 조회 (Django ORM)
    if request.method == "GET":
        messages = session.messages.order_by("created_at")
        data = {"messages": [_serialize_message(m) for m in messages]}
        return JsonResponse(data)

    # POST: 메시지 전송 (FastAPI SSE 프록시)
    try:
        payload = _read_json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"detail": "message is required."}, status=400)

    # 사용자 메시지를 DB에 저장
    ChatMessage.objects.create(session=session, role="user", content=message)

    # 세션 updated_at 갱신
    session.save(update_fields=["updated_at"])

    safe_payload = {
        "message": message,
        "thread_id": str(session_id),
        "pet_profile": payload.get("pet_profile"),
        "health_concerns": payload.get("health_concerns") or [],
        "allergies": payload.get("allergies") or [],
        "food_preferences": payload.get("food_preferences") or [],
    }

    return StreamingHttpResponse(
        _stream_and_save(_chat_base_url() + "/", safe_payload, request.user.id, session),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
