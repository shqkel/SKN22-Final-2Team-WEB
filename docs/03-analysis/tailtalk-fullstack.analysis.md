# TailTalk Fullstack Gap Analysis

> **Feature**: tailtalk-fullstack
> **Design**: `docs/02-design/features/tailtalk-fullstack.design.md`
> **Date**: 2026-03-25
> **Match Rate**: 72%

---

## Overall Scores

| Category | Items | Match | Partial | Missing | Rate |
|---|:---:|:---:|:---:|:---:|:---:|
| Authentication | 12 | 8 | 2 | 2 | 75% |
| Chat API Endpoints | 7 | 1 | 1 | 5 | 21% |
| Chat Frontend | 14 | 9 | 3 | 2 | 75% |
| Cart/Order API | 8 | 8 | 0 | 0 | 100% |
| Cart/Order Frontend | 6 | 3 | 2 | 1 | 67% |
| Data Model | 15 | 15 | 0 | 0 | 100% |
| LangGraph State | 8 | 8 | 0 | 0 | 100% |
| File Structure | 8 | 5 | 1 | 2 | 69% |
| **Overall** | **78** | **57** | **9** | **12** | **72%** |

---

## Critical Gaps

### Gap 1: FastAPI Session CRUD 엔드포인트 부재 (Critical)

Django 프록시(`chat/api_views.py`)가 세션 CRUD를 FastAPI로 전달하지만, FastAPI에는 `POST /api/chat/` 하나만 존재. 세션 목록/생성/수정/삭제, 메시지 조회 모두 FastAPI에서 404 반환.

**해결 방향**: Django에서 세션 CRUD를 직접 처리 (Django ORM), SSE 메시지 전송만 FastAPI 프록시 유지 (하이브리드 방식).

### Gap 2: 프론트엔드 장바구니 서버 미연동 (High)

`addRecommendedToCart()`, `adjustCartQuantity()`, `removeCartItem()`은 DOM만 조작. `POST /api/cart/items/` 등 서버 API 미호출. 새로고침 시 장바구니 초기화.

### Gap 3: 상품 상세 모달 미구현 (High)

카드 클릭 시 상세 정보(영양성분, 원료, 리뷰 요약) 모달 미존재.

### Gap 4: Interaction 로깅 프론트엔드 미연동 (Medium)

백엔드 API 구현 완료, 프론트에서 클릭/장바구니 이벤트 시 API 호출 없음.

---

## Changed from Design

| # | Item | Design | Implementation |
|---|---|---|---|
| 1 | 프론트엔드 인증 | JWT Bearer + localStorage | Session Cookie + CSRF |
| 2 | Access Token 수명 | 30분 | 1시간 |
| 3 | 추천 질문 칩 | 펫 프로필 기반 동적 | 하드코딩 3개 고정 |
| 4 | 제목 자동 생성 | SSE done 후 PATCH | 세션 생성 시 truncate만 |
| 5 | AI 응답 렌더링 | 마크다운 지원 | plain text only |

---

## Recommended Actions (Priority Order)

1. **세션 CRUD를 Django 직접 처리로 전환** — 프록시 제거, Django ORM 사용
2. **프론트엔드 장바구니 API 연동** — DOM 조작에 서버 API 호출 추가
3. **상품 상세 모달 구현** — 카드 클릭 이벤트 처리
4. **Interaction 로깅 프론트 연동** — 클릭/장바구니 이벤트 `POST /api/interactions/`
5. **마크다운 렌더링** — marked.js 등 적용
