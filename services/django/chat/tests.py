from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from chat.models import ChatMessage, ChatSession
from pets.models import Pet, PetAllergy, PetFoodPreference, PetHealthConcern
from users.models import User, UserProfile


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _create_user(email="chat@example.com"):
    user = User.objects.create_user(email=email, password="Password123!")
    UserProfile.objects.create(user=user, nickname=email.split("@")[0])
    return user


def _create_session(user, title="테스트 대화", target_pet=None):
    return ChatSession.objects.create(user=user, title=title, target_pet=target_pet)


def _create_message(session, role, content):
    return ChatMessage.objects.create(session=session, role=role, content=content)


# ── Page View Tests ──────────────────────────────────────────────────────────


class ChatPageTests(TestCase):
    def setUp(self):
        self.user = _create_user("chat-owner@example.com")
        self.client.force_login(self.user)

    def test_chat_page_renders_related_pet_fields(self):
        pet = Pet.objects.create(
            user=self.user, name="Nabi", species="cat",
            gender="female", budget_range="5_10",
        )
        PetHealthConcern.objects.create(pet=pet, concern="skin")
        PetAllergy.objects.create(pet=pet, ingredient="chicken")
        PetFoodPreference.objects.create(pet=pet, food_type="dry")

        response = self.client.get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["member_pets"]), 1)
        serialized = response.context["member_pets"][0]
        self.assertEqual(serialized["health_concerns"], ["skin"])
        self.assertEqual(serialized["allergies"], ["chicken"])
        self.assertEqual(serialized["food_preferences"], ["dry"])

    def test_chat_page_includes_sessions_in_context(self):
        _create_session(self.user, "기존 대화")

        response = self.client.get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["sessions"]), 1)


# ── Session CRUD Tests (Django ORM) ──────────────────────────────────────────


class SessionListCreateTests(TestCase):
    def setUp(self):
        self.user = _create_user("session@example.com")
        self.client.force_login(self.user)

    def test_unauthenticated_returns_401(self):
        self.client.logout()
        response = self.client.get("/api/chat/sessions/")
        self.assertEqual(response.status_code, 401)

    def test_list_returns_user_sessions(self):
        _create_session(self.user, "세션 1")
        _create_session(self.user, "세션 2")
        other_user = _create_user("other@example.com")
        _create_session(other_user, "타인 세션")

        response = self.client.get("/api/chat/sessions/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        titles = [s["title"] for s in data]
        self.assertIn("세션 1", titles)
        self.assertIn("세션 2", titles)
        self.assertNotIn("타인 세션", titles)

    def test_create_session(self):
        response = self.client.post(
            "/api/chat/sessions/",
            data='{"title":"새 대화","target_pet_id":null}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], "새 대화")
        self.assertIn("session_id", data)
        self.assertEqual(ChatSession.objects.filter(user=self.user).count(), 1)

    def test_create_session_default_title(self):
        response = self.client.post(
            "/api/chat/sessions/",
            data="{}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["title"], "새 대화")

    def test_create_session_with_pet(self):
        pet = Pet.objects.create(
            user=self.user, name="콩이", species="dog",
            gender="male", budget_range="5_10",
        )
        response = self.client.post(
            "/api/chat/sessions/",
            data=f'{{"title":"콩이 상담","target_pet_id":"{pet.pet_id}"}}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["target_pet_id"], str(pet.pet_id))


class SessionDetailTests(TestCase):
    def setUp(self):
        self.user = _create_user("detail@example.com")
        self.session = _create_session(self.user, "원래 제목")
        self.client.force_login(self.user)

    def test_patch_updates_title(self):
        response = self.client.patch(
            f"/api/chat/sessions/{self.session.session_id}/",
            data='{"title":"수정된 제목"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "수정된 제목")
        self.session.refresh_from_db()
        self.assertEqual(self.session.title, "수정된 제목")

    def test_delete_removes_session(self):
        response = self.client.delete(
            f"/api/chat/sessions/{self.session.session_id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ChatSession.objects.filter(session_id=self.session.session_id).exists())

    def test_delete_cascades_messages(self):
        _create_message(self.session, "user", "안녕")
        _create_message(self.session, "assistant", "반갑습니다")

        self.client.delete(f"/api/chat/sessions/{self.session.session_id}/")

        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_cannot_access_other_users_session(self):
        other_user = _create_user("other2@example.com")
        other_session = _create_session(other_user, "타인 세션")

        response = self.client.patch(
            f"/api/chat/sessions/{other_session.session_id}/",
            data='{"title":"해킹"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_session_returns_404(self):
        response = self.client.delete(
            "/api/chat/sessions/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, 404)


# ── Message Tests ────────────────────────────────────────────────────────────


class MessageListTests(TestCase):
    def setUp(self):
        self.user = _create_user("messages@example.com")
        self.session = _create_session(self.user)
        _create_message(self.session, "user", "추천해줘")
        _create_message(self.session, "assistant", "이 사료를 추천합니다.")
        self.client.force_login(self.user)

    def test_get_messages_returns_ordered_history(self):
        response = self.client.get(
            f"/api/chat/sessions/{self.session.session_id}/messages/"
        )

        self.assertEqual(response.status_code, 200)
        messages = response.json()["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "추천해줘")
        self.assertEqual(messages[1]["role"], "assistant")

    def test_cannot_read_other_users_messages(self):
        other_user = _create_user("msg-other@example.com")
        other_session = _create_session(other_user)

        response = self.client.get(
            f"/api/chat/sessions/{other_session.session_id}/messages/"
        )
        self.assertEqual(response.status_code, 404)


# ── SSE Proxy Tests (FastAPI mock) ───────────────────────────────────────────


class _FakeStreamResponse:
    def __init__(self, chunks, status_code=200):
        self._chunks = chunks
        self.status_code = status_code
        self.text = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iter_bytes(self):
        for chunk in self._chunks:
            yield chunk

    def json(self):
        return {"detail": "error"}


class _FakeHttpxClient:
    last_stream_request = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def stream(self, method, url, headers=None, json=None):
        self.__class__.last_stream_request = {
            "method": method, "url": url, "headers": headers, "json": json,
        }
        return _FakeStreamResponse([
            b'data: {"type":"token","content":"hello "}\n\n',
            b'data: {"type":"token","content":"world"}\n\n',
            b'data: {"type":"products","cards":[{"goods_id":"GI001"}]}\n\n',
            b'data: {"type":"done"}\n\n',
        ])


class MessageSendSSETests(TestCase):
    def setUp(self):
        self.user = _create_user("sse@example.com")
        self.session = _create_session(self.user)
        self.client.force_login(self.user)

    @patch("chat.api_views.httpx.Client", _FakeHttpxClient)
    def test_post_message_streams_sse_and_saves_messages(self):
        response = self.client.post(
            f"/api/chat/sessions/{self.session.session_id}/messages/",
            data='{"message":"사료 추천해줘","pet_profile":{"species":"dog"}}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")

        payload = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn('"type":"token"', payload)
        self.assertIn('"type":"done"', payload)

        # 사용자 메시지가 DB에 저장되었는지 확인
        user_msgs = ChatMessage.objects.filter(session=self.session, role="user")
        self.assertEqual(user_msgs.count(), 1)
        self.assertEqual(user_msgs.first().content, "사료 추천해줘")

        # assistant 메시지가 done 이벤트 시 DB에 저장되었는지 확인
        assistant_msgs = ChatMessage.objects.filter(session=self.session, role="assistant")
        self.assertEqual(assistant_msgs.count(), 1)
        self.assertEqual(assistant_msgs.first().content, "hello world")

    @patch("chat.api_views.httpx.Client", _FakeHttpxClient)
    def test_post_message_sends_internal_token_to_fastapi(self):
        _FakeHttpxClient.last_stream_request = None
        response = self.client.post(
            f"/api/chat/sessions/{self.session.session_id}/messages/",
            data='{"message":"hello"}',
            content_type="application/json",
        )
        # Consume streaming content to trigger httpx call
        b"".join(response.streaming_content)

        req = _FakeHttpxClient.last_stream_request
        self.assertIsNotNone(req)
        self.assertEqual(req["headers"]["X-Internal-Service-Token"], settings.INTERNAL_SERVICE_TOKEN)
        self.assertEqual(req["headers"]["X-User-Id"], str(self.user.id))
        self.assertEqual(req["json"]["message"], "hello")
        self.assertEqual(req["json"]["thread_id"], str(self.session.session_id))

    @patch("chat.api_views.httpx.Client", _FakeHttpxClient)
    def test_post_message_updates_session_timestamp(self):
        old_updated = self.session.updated_at
        self.client.post(
            f"/api/chat/sessions/{self.session.session_id}/messages/",
            data='{"message":"hello"}',
            content_type="application/json",
        )
        self.session.refresh_from_db()
        self.assertGreaterEqual(self.session.updated_at, old_updated)

    def test_post_empty_message_returns_400(self):
        response = self.client.post(
            f"/api/chat/sessions/{self.session.session_id}/messages/",
            data='{"message":"  "}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_post_message_unauthenticated_returns_401(self):
        self.client.logout()
        response = self.client.post(
            f"/api/chat/sessions/{self.session.session_id}/messages/",
            data='{"message":"hello"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)


class _FakeErrorHttpxClient(_FakeHttpxClient):
    def stream(self, method, url, headers=None, json=None):
        return _FakeStreamResponse([], status_code=500)


class MessageSendErrorTests(TestCase):
    def setUp(self):
        self.user = _create_user("sse-err@example.com")
        self.session = _create_session(self.user)
        self.client.force_login(self.user)

    @patch("chat.api_views.httpx.Client", _FakeErrorHttpxClient)
    def test_fastapi_error_returns_sse_error_event(self):
        response = self.client.post(
            f"/api/chat/sessions/{self.session.session_id}/messages/",
            data='{"message":"hello"}',
            content_type="application/json",
        )

        payload = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn('"type":', payload)
        self.assertIn('error', payload)
