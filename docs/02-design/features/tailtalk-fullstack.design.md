# TailTalk Fullstack Design

> **Feature**: tailtalk-fullstack
> **Plan**: `docs/01-plan/features/tailtalk-fullstack.plan.md`
> **Date**: 2026-03-25

---

## 1. 인증 아키텍처

### 1.1 전체 인증 흐름

```
[Browser]
  │
  ├── Page 요청 (GET /chat/) ─── Django Session Cookie ──> [Django MVT]
  │
  └── API 요청 (POST /api/chat/) ── JWT Access Token ──> [Django API]
                                                              │
                                                     JWT 검증 (simplejwt)
                                                              │
                                                  X-Internal-Service-Token
                                                  X-User-Id
                                                              │
                                                              v
                                                         [FastAPI]
                                                    verify_internal_token()
```

### 1.2 이중 인증 구조

| 레이어 | 방식 | 용도 |
|---|---|---|
| Page (MVT) | Django Session Cookie | 템플릿 렌더링, `request.user` |
| API | JWT (simplejwt) | AJAX/fetch 요청 인증 |
| 내부 통신 | `X-Internal-Service-Token` | Django -> FastAPI 프록시 |

### 1.3 JWT 토큰 관리

| 항목 | 값 |
|---|---|
| 발급 엔드포인트 | `POST /api/auth/token/` (email + password) |
| 갱신 엔드포인트 | `POST /api/auth/token/refresh/` |
| Access Token 수명 | 30분 (설정 가능) |
| Refresh Token 수명 | 7일 |
| 저장 위치 (프론트) | `localStorage` (Access), `httpOnly cookie` 검토 |

### 1.4 프론트엔드 인증 전략

```javascript
// 모든 API 요청에 JWT 첨부
async function apiRequest(url, options = {}) {
    const token = localStorage.getItem("accessToken");
    const headers = {
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
    };
    const response = await fetch(url, { ...options, headers });

    // 401 -> Refresh 시도
    if (response.status === 401) {
        const refreshed = await refreshToken();
        if (refreshed) return apiRequest(url, options);  // 재시도
        window.location.href = "/login/";                // 실패 시 로그인
    }
    return response;
}
```

---

## 2. Sprint 1 설계: 챗봇 핵심 인터랙션

### 2.1 API 명세

#### 2.1.1 채팅 API (Django 프록시 -> FastAPI)

**세션 목록 조회**
```
GET /api/chat/sessions/
Authorization: Bearer <token>

Response 200:
[
  {
    "session_id": "uuid",
    "title": "콩이 피부 가려움 상담",
    "target_pet_id": "uuid | null",
    "created_at": "2026-03-25T10:00:00Z",
    "updated_at": "2026-03-25T10:30:00Z"
  }
]
```

**세션 생성**
```
POST /api/chat/sessions/
Authorization: Bearer <token>
Body: { "title": "새 대화", "target_pet_id": "uuid | null" }

Response 201:
{ "session_id": "uuid", "title": "새 대화", ... }
```

**세션 수정 / 삭제**
```
PATCH /api/chat/sessions/<session_id>/
Body: { "title": "변경된 제목" }

DELETE /api/chat/sessions/<session_id>/
Response 204
```

**메시지 조회**
```
GET /api/chat/sessions/<session_id>/messages/
Response 200:
[
  { "message_id": "uuid", "role": "user", "content": "...", "created_at": "..." },
  { "message_id": "uuid", "role": "assistant", "content": "...", "created_at": "..." }
]
```

**메시지 전송 (SSE 스트리밍)**
```
POST /api/chat/sessions/<session_id>/messages/
Authorization: Bearer <token>
Body:
{
  "message": "우리 콩이 피부에 좋은 사료 추천해줘",
  "pet_profile": { "species": "dog", "breed": "말티즈", "age": "2년 3개월", "gender": "male", "weight": "5.2" },
  "health_concerns": ["skin", "dental"],
  "allergies": ["chicken"],
  "food_preferences": ["dry"]
}

Response: text/event-stream
data: {"type":"token","content":"말티즈"}
data: {"type":"token","content":" 2살"}
data: {"type":"token","content":" 피부가"}
...
data: {"type":"products","cards":[{...}]}
data: {"type":"done"}
```

#### 2.1.2 SSE 이벤트 타입

| type | payload | 설명 |
|---|---|---|
| `token` | `{ content: string }` | LLM 응답 토큰 (단어 단위) |
| `products` | `{ cards: ProductCard[] }` | 추천 상품 카드 배열 |
| `error` | `{ message: string }` | 오류 메시지 |
| `done` | `{}` | 스트리밍 완료 |

#### 2.1.3 ProductCard 스키마

```typescript
interface ProductCard {
  goods_id:      string;
  goods_name:    string;
  brand_name:    string;
  price:         number;
  discount_price: number;
  rating:        number;        // 5점 만점
  review_count:  number;
  thumbnail_url: string;
  product_url:   string;
  pet_type:      string[];
  category:      string[];
  health_concern_tags: string[];
  // 상세 모달용 (optional)
  main_ingredients?:  string[];
  nutrition_info?:    object;
  sentiment_avg?:     number;
  repeat_rate?:       number;
}
```

### 2.2 프론트엔드 컴포넌트 구조

```
templates/chat/index.html
├── [사이드바]
│   ├── 새 대화 버튼 + 펫 프로필 선택 드롭다운
│   ├── 대화 히스토리 목록 (날짜 그룹)
│   │   ├── 오늘
│   │   ├── 어제
│   │   ├── 7일 이내
│   │   └── 이전
│   └── 설정 / 로그아웃
│
├── [메인 채팅 영역]
│   ├── 메시지 목록 (스크롤)
│   │   ├── 사용자 메시지 (우측 정렬)
│   │   └── AI 메시지 (좌측 정렬, 마크다운 렌더링)
│   ├── 추천 질문 칩 (대화 시작 시)
│   └── 입력 영역
│       ├── textarea (Shift+Enter 줄바꿈)
│       ├── 전송 버튼 / 중단 버튼 (토글)
│       └── 이미지 첨부 버튼 (P2)
│
└── [우측 상품 패널]
    ├── 탭: [추천 상품] / [장바구니] (Sprint 2)
    ├── 상품 카드 리스트 (슬라이드)
    │   ├── 썸네일 이미지
    │   ├── 상품명 / 브랜드
    │   ├── 가격 (할인가 표시)
    │   ├── 평점 + 리뷰수
    │   └── [+장바구니] 버튼
    └── 상품 상세 모달
        ├── 큰 이미지
        ├── 상세 정보 (원료, 영양성분)
        ├── 리뷰 요약 (감성 분석)
        └── [장바구니 담기] / [어바웃펫에서 보기]
```

### 2.3 데이터 흐름: 메시지 전송

```
1. 사용자가 입력창에 메시지 작성 → [전송] 클릭
2. JS: 입력창 비활성화, 중단 버튼 표시
3. JS: 사용자 메시지를 채팅 영역에 즉시 렌더링 (낙관적 UI)
4. JS: POST /api/chat/sessions/<id>/messages/ (SSE)
   ├── Header: Authorization: Bearer <JWT>
   └── Body: { message, pet_profile, health_concerns, allergies, food_preferences }

5. Django: JWT 검증 → request.user 확인
6. Django: httpx로 FastAPI에 프록시
   ├── Header: X-Internal-Service-Token, X-User-Id
   └── Body: 그대로 전달

7. FastAPI: Internal Token 검증
8. FastAPI: LangGraph 실행 (intent → recommend/domain_qa → merge → respond)
9. FastAPI: SSE 스트리밍 (token → products → done)

10. Django: StreamingHttpResponse로 SSE 중계
11. JS: EventSource로 수신
    ├── type=token  → AI 메시지 버블에 점진적 추가
    ├── type=products → 우측 패널에 상품 카드 렌더링
    └── type=done   → 입력창 활성화, 전송 버튼 복귀
```

### 2.4 데이터 흐름: 새 대화 시작

```
1. 사용자: 사이드바 [새 대화] 클릭
2. JS: 펫 프로필 선택 드롭다운 표시 (member_pets 데이터)
3. 사용자: 펫 선택 (또는 프로필 없이)
4. JS: 채팅 영역 초기화 + 추천 질문 칩 표시
5. 사용자: 메시지 입력 또는 칩 클릭
6. JS: POST /api/chat/sessions/ (Lazy 생성)
   └── Body: { title: 메시지 앞 30자, target_pet_id: 선택된 펫 }
7. Response: { session_id: "새 UUID" }
8. JS: 이후 메시지는 POST /api/chat/sessions/<새 session_id>/messages/
9. JS: 사이드바 목록에 새 세션 추가
```

### 2.5 대화 히스토리 사이드바

#### 날짜 그룹 로직

```javascript
function groupSessions(sessions) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today - 86400000);
    const week = new Date(today - 7 * 86400000);

    return {
        today:     sessions.filter(s => new Date(s.updated_at) >= today),
        yesterday: sessions.filter(s => new Date(s.updated_at) >= yesterday && new Date(s.updated_at) < today),
        week:      sessions.filter(s => new Date(s.updated_at) >= week && new Date(s.updated_at) < yesterday),
        older:     sessions.filter(s => new Date(s.updated_at) < week),
    };
}
```

#### 세션 항목 인터랙션

| 동작 | 트리거 | 액션 |
|---|---|---|
| 대화 로드 | 클릭 | `GET /api/chat/sessions/<id>/messages/` → 채팅 영역 렌더링 |
| 제목 변경 | 더블클릭 또는 연필 아이콘 | inline edit → `PATCH /api/chat/sessions/<id>/` |
| 삭제 | 휴지통 아이콘 (hover 시 노출) | 확인 모달 → `DELETE /api/chat/sessions/<id>/` |

### 2.6 제목 자동 생성 (FR-CHAT-02)

| 항목 | 설계 |
|---|---|
| 트리거 | 첫 메시지 전송 후 SSE `done` 수신 시 |
| 방식 | 클라이언트에서 사용자 첫 메시지 텍스트를 30자로 truncate |
| 저장 | `PATCH /api/chat/sessions/<id>/` |
| 표시 | 사이드바 + 대화 상단에 제목과 날짜(YY-MM-DD) 표시 |

> LLM 기반 제목 생성은 P2에서 검토. 프로토타입에서는 클라이언트 truncate로 충분.

### 2.7 추천 질문 칩 (FR-CHAT-04)

프로필 기반 고정 질문. 펫 프로필에 따라 동적 조합.

```javascript
const CHIP_TEMPLATES = {
    dog: [
        "{breed} {age}에게 맞는 사료 추천해줘",
        "{name}가 피부를 자꾸 긁어, 사료 문제일까?",
        "소화가 잘 안 되는 것 같은데 도움 되는 간식 있어?",
        "{breed} 체중 관리에 좋은 사료 뭐가 있어?",
    ],
    cat: [
        "{breed} {age}에게 맞는 사료 추천해줘",
        "헤어볼 관리에 좋은 간식 있을까?",
        "{name}가 습식을 안 먹는데 입문용 추천해줘",
        "요로 건강에 도움 되는 사료 알려줘",
    ],
};
```

### 2.8 스트리밍 중단 (FR-CHAT-06)

```javascript
let abortController = null;

function sendMessage(message) {
    abortController = new AbortController();

    fetch(url, {
        method: "POST",
        signal: abortController.signal,
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    // ... SSE 처리
}

function stopGeneration() {
    if (abortController) {
        abortController.abort();
        abortController = null;
        // UI: 중단 버튼 → 전송 버튼, 입력창 활성화
    }
}
```

> `fetch` + `ReadableStream` 방식 사용. `EventSource`는 POST 미지원이므로 `fetch` SSE 파싱 구현.

---

## 3. Sprint 2 설계: 장바구니 + 구매

### 3.1 장바구니 API (Django 직접 처리)

장바구니는 Django 모델(Cart/CartItem)을 직접 사용. FastAPI 프록시 불필요.

**장바구니 조회**
```
GET /api/cart/
Authorization: Bearer <token>

Response 200:
{
  "cart_id": "uuid",
  "items": [
    {
      "cart_item_id": "uuid",
      "product": { "goods_id": "GI001", "goods_name": "...", "thumbnail_url": "...", "discount_price": 39800, ... },
      "quantity": 2,
      "added_at": "2026-03-25T10:00:00Z"
    }
  ],
  "total_price": 79600,
  "item_count": 2
}
```

**상품 추가**
```
POST /api/cart/items/
Body: { "goods_id": "GI001", "quantity": 1 }
Response 201: { "cart_item_id": "uuid", ... }
```

**수량 변경**
```
PATCH /api/cart/items/<cart_item_id>/
Body: { "quantity": 3 }
Response 200
```

**상품 삭제**
```
DELETE /api/cart/items/<cart_item_id>/
Response 204
```

### 3.2 주문 API (Django 직접 처리)

**주문 생성**
```
POST /api/orders/
Body: { "recipient_name": "홍길동", "delivery_address": "서울시 강남구..." }
Response 201:
{
  "order_id": "uuid",
  "items": [...],
  "total_price": 79600,
  "status": "pending",
  "created_at": "..."
}
```
> 장바구니 전체를 주문으로 전환. CartItem -> OrderItem 복사 후 Cart 비우기.

**주문 목록**
```
GET /api/orders/
Response 200: [{ "order_id": "uuid", "total_price": 79600, "status": "pending", "created_at": "..." }]
```

**주문 상세**
```
GET /api/orders/<order_id>/
Response 200: { ..., "items": [{ "product": {...}, "quantity": 2, "price_at_order": 39800 }] }
```

### 3.3 우측 패널 탭 구조

```
[우측 패널]
├── 탭 헤더: [추천 상품 (3)] | [장바구니 (2)]
│
├── [추천 상품 탭 — 활성]
│   └── 상품 카드 리스트
│       ├── 카드: 이미지 | 이름 | 가격 | 평점 | [+]
│       └── ...
│
└── [장바구니 탭]
    ├── 장바구니 아이템 리스트
    │   ├── 아이템: 이미지 | 이름 | 가격 | [-] 수량 [+] | [X]
    │   └── ...
    ├── 합계: ₩79,600
    └── [주문하기] 버튼
```

### 3.4 UserInteraction 로깅

Day 1부터 상호작용 데이터 수집 (Phase 2 CF 준비).

| 이벤트 | 트리거 | interaction_type | weight |
|---|---|---|---|
| 상품 카드 클릭 | 카드 클릭 or 상세 모달 오픈 | `click` | 1 |
| 장바구니 담기 | (+) 버튼 클릭 | `cart` | 3 |
| 구매 완료 | 주문 생성 | `purchase` | 5 |
| 거절 | "이거 말고 다른 거" 감지 (P2) | `reject` | -1 |

```
POST /api/interactions/
Body: { "goods_id": "GI001", "session_id": "uuid", "interaction_type": "click" }
```

---

## 4. 파일별 변경사항

### 4.1 Sprint 1 변경 파일

| 파일 | 변경 | 설명 |
|---|---|---|
| `services/fastapi/core/auth.py` | 신규 (완료) | Internal Token 검증 디펜던시 |
| `services/fastapi/main.py` | 수정 (완료) | 전역 `verify_internal_token` 적용 |
| `infra/nginx/nginx.conf` | 수정 (완료) | 모든 `/api/*` Django 경유로 통합 |
| `services/django/chat/api_views.py` | 수정 | JWT 인증 데코레이터 적용, `request.user.is_authenticated` → JWT 검증 |
| `services/django/chat/page_views.py` | 수정 | 프리뷰 데이터 제거, 실제 API 연동 로직 |
| `templates/chat/index.html` | 대규모 수정 | SSE 스트리밍, 상품 카드, 히스토리, 칩 등 전체 인터랙션 |
| `static/js/chat.js` | 신규 | 채팅 JS 로직 분리 (SSE, 카드 렌더링, 모달, 히스토리) |
| `static/css/chat.css` | 신규 | 채팅 전용 스타일 (카드, 모달, 애니메이션) |

### 4.2 Sprint 2 변경 파일

| 파일 | 변경 | 설명 |
|---|---|---|
| `services/django/orders/views.py` | 수정 | Cart CRUD API, Order 생성 API 구현 |
| `services/django/orders/urls.py` | 수정 | cart/order 엔드포인트 추가 |
| `services/django/orders/serializers.py` | 신규 | Cart, CartItem, Order, OrderItem 시리얼라이저 |
| `templates/chat/index.html` | 수정 | 우측 패널 탭 (추천/장바구니), 장바구니 인터랙션 |
| `templates/orders/list.html` | 수정 | 주문 목록 실제 데이터 연동 |
| `templates/orders/detail_modal.html` | 신규 | 주문 상세 모달 |
| `templates/base.html` | 수정 | Navbar 정비 (로그인 상태별 버튼) |

---

## 5. 구현 순서 (의존성 기반)

```
Phase A: 인프라 정비 (완료)
  ✅ FastAPI Internal Token 검증
  ✅ Nginx 라우팅 통합

Phase B: 채팅 백엔드
  B1. Django chat/api_views.py JWT 인증 전환
  B2. FastAPI chat SSE 엔드포인트가 session_id 기반으로 동작하도록 확인
  B3. Django 프록시 → FastAPI 메시지/세션 API 연동 테스트

Phase C: 채팅 프론트엔드
  C1. SSE 스트리밍 수신 + AI 메시지 렌더링 (fetch + ReadableStream)
  C2. 사용자 메시지 전송 + 중단 버튼
  C3. 상품 카드 렌더링 (우측 패널)
  C4. 상품 상세 모달
  C5. 대화 히스토리 사이드바 (CRUD)
  C6. 새 대화 + 펫 프로필 선택 + Lazy 세션 생성
  C7. 추천 질문 칩
  C8. 제목 자동 생성

Phase D: 장바구니
  D1. Cart/CartItem CRUD API (Django)
  D2. 우측 패널 탭 (추천/장바구니)
  D3. 상품 카드 [+] 버튼 → 장바구니 담기
  D4. 장바구니 수량 조절/삭제

Phase E: 주문
  E1. Order 생성 API (장바구니 → 주문 전환)
  E2. 주문 Modal (결제 Stub)
  E3. 주문 목록/상세 페이지
  E4. Navbar 정비

Phase F: 상호작용 로깅
  F1. UserInteraction API
  F2. 카드 클릭/장바구니/구매 이벤트 로깅
```

---

## 6. 주요 설계 결정

| 결정 | 근거 |
|---|---|
| `fetch` + `ReadableStream` (SSE) | `EventSource`는 POST 미지원. 커스텀 헤더(JWT)도 불가 |
| 세션 Lazy 생성 | UX: 빈 세션 방지. 첫 메시지 전송 시에만 세션 생성 |
| 제목은 클라이언트 truncate | LLM 호출 비용 절감. 프로토타입에서 충분 |
| 장바구니는 Django 직접 처리 | Cart/Order 모델이 Django에 있음. FastAPI 프록시 불필요 |
| UserInteraction Day 1 로깅 | Phase 2 CF 학습 데이터 준비 (Plan 문서 명시) |
| 상품 상세는 모달 | 페이지 이동 없이 빠른 확인. 3패널 레이아웃 유지 |
