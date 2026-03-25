# TailTalk Fullstack Plan

> **Feature**: tailtalk-fullstack
> **Version**: v1.0
> **Date**: 2026-03-25
> **Author**: PDCA Plan

---

## Executive Summary

| Perspective | Description |
|---|---|
| **Problem** | 반려동물 맞춤 상품 추천 챗봇 서비스(TailTalk)의 인증/프로필/데이터 파이프라인은 구현 완료되었으나, 핵심인 챗봇 UI 인터랙션, 상품 추천 카드, 장바구니/주문 플로우, 어드민 페이지가 미구현 상태 |
| **Solution** | 기존 설계 문서(21개)와 구현 코드를 기반으로, 미구현 기능을 우선순위별 3개 스프린트로 나눠 점진적 구현 |
| **Function UX Effect** | 사용자가 반려동물 프로필 기반으로 자연어 대화를 통해 상품을 추천받고, 장바구니에 담아 구매까지 완료하는 E2E 플로우 달성 |
| **Core Value** | 기획 문서-설계 문서-코드 간 정합성을 유지하며, 프로토타입 수준의 완전한 사용자 경험 제공 |

---

## 1. 현재 프로젝트 상태 분석

### 1.1 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 프로젝트명 | TailTalk - 반려동물 맞춤 상품 추천 대화형 챗봇 |
| 팀 | SKN22 Final Project 2팀 |
| 데이터 소스 | 어바웃펫(aboutpet.co.kr) 크롤링 상품 3,618건 + 리뷰 |
| 아키텍처 | Django(Auth/MVT) + FastAPI(챗봇/추천) + PostgreSQL(pgvector) + Nginx |
| AI 파이프라인 | LangGraph 멀티에이전트 + pgvector Hybrid Search (Dense + Kiwi tsvector + RRF) |

### 1.2 기존 문서 현황 (21개)

| 디렉토리 | 문서 | 내용 |
|---|---|---|
| `docs/planning/` | 01_project_overview | 프로젝트 목적, 범위, UX 레퍼런스 (3-패널 구조) |
| | 02_system_architecture | 전체 시스템 아키텍처 (Mermaid), 데이터 파이프라인, 인프라 |
| | 03_requirements_spec | 요구사항 명세 테이블 (FR-AUTH ~ FR-ADMIN, NFR 포함) |
| | 04_data_model_detail | ERD, 엔티티별 컬럼 상세 (16개 테이블) |
| | 05_user_flow | 전체 흐름, 온보딩, 챗봇 인터페이스 흐름 |
| | 06_dev_convention | Git 브랜치, 커밋, PR, 코드 컨벤션, 마일스톤 |
| | 07_recommendation_architecture | LangGraph State, Phase 1 추천 흐름, Hybrid Search, 재랭킹, Phase 2 CF |
| `docs/data/` | 01~05 | 크롤링 스펙, Medallion 스키마, Ingest 파이프라인, Feature Engineering, pgvector 마이그레이션 |
| `docs/domain/` | 01~02 | 도메인 전처리, 도메인 RAG 파이프라인 |
| `docs/eda/` | 01~02 | Gold 데이터 EDA, DB EDA |
| `docs/infra/` | 00~03 | 온보딩 가이드, 로컬 셋업, 데이터 복원, Django 모델 |

### 1.3 구현 완료 항목 (요구사항 기준)

| 영역 | 구현 완료 항목 | 상태 |
|---|---|---|
| **인증** | 이메일 회원가입, 소셜 로그인 (Google/Kakao/Naver), 일반 로그인, JWT 발급, 로그아웃 | ✅ |
| **사용자 프로필** | 정보 등록/수정, OAuth 프로필 연동 | ✅ |
| **반려동물 프로필** | 종류 선택, 기본정보/건강/식이 입력, 프로필 목록/수정 | ✅ |
| **비로그인 차단** | 챗봇 Input Disabled + 로그인 유도 | ✅ |
| **데이터 파이프라인** | Bronze -> Silver -> Gold 전처리, pgvector 마이그레이션, Hybrid Search | ✅ |
| **AI 파이프라인** | LangGraph 멀티에이전트 (intent/recommend/domain_qa/clarify/merge/respond) | ✅ |
| **E2E 연결** | Django -> FastAPI -> LangGraph 프록시 챗봇 파이프라인 | ✅ |
| **UI 기초** | 3패널 레이아웃, 사이드바, 챗봇 메인 페이지 | ✅ |
| **인프라** | Docker Compose (Nginx + Django + FastAPI + PostgreSQL), CI/CD, EB 배포 | ✅ |

### 1.4 미구현 항목 (요구사항 기준)

| 우선순위 | 영역 | 미구현 기능 | 기능 ID |
|---|---|---|---|
| **P0 (필수)** | 챗봇 인터페이스 | 새 대화 시작 + 펫 프로필 선택 | FR-CHAT-01 |
| **P0** | 챗봇 인터페이스 | 제목 자동 생성 | FR-CHAT-02 |
| **P0** | 챗봇 인터페이스 | 컨텍스트 유지 (프로필 시스템 프롬프트 주입) | FR-CHAT-03 |
| **P0** | 챗봇 인터페이스 | 추천 질문 칩 | FR-CHAT-04 |
| **P0** | 챗봇 인터페이스 | 대화 히스토리 (사이드바 목록) | FR-CHAT-05 |
| **P0** | 챗봇 인터페이스 | 스트리밍 출력 + 중단 버튼 | FR-CHAT-06 |
| **P0** | 상품 추천 | 상품 카드 렌더링 (우측 패널) | FR-REC-01 |
| **P0** | 상품 추천 | 상품 카드 클릭 -> 모달 상세 | FR-REC-02 |
| **P0** | 상품 추천 | 추천 근거 표시 | FR-REC-04 |
| **P1 (중요)** | 장바구니 | 상품 담기 (+) 버튼 | FR-CART-01 |
| **P1** | 장바구니 | 추천/장바구니 탭 구성 | FR-CART-02 |
| **P1** | 장바구니 | 수량 조절 및 삭제 | FR-CART-03 |
| **P1** | 장바구니 | 주문하기 진입 | FR-CART-04 |
| **P1** | 구매 | 구매 플로우 (Stub) | FR-ORDER-01~04 |
| **P2 (후순위)** | 인증 | 회원 탈퇴 | FR-AUTH-06 |
| **P2** | 챗봇 | 이미지 업로드 | FR-CHAT-07 |
| **P2** | 챗봇 | 토큰 관리 | FR-CHAT-09 |
| **P2** | 챗봇 | PII 마스킹 | FR-CHAT-10 |
| **P2** | 상품 추천 | 추천 개수 슬라이드 | FR-REC-03 |
| **P2** | 상품 추천 | 조건 기반 추천 (가격/브랜드) | FR-REC-05 |
| **P2** | 상품 추천 | 랭킹 로직 (어드민 가중치) | FR-REC-06 |
| **P2** | 설정 | 테마 설정 (다크/라이트) | FR-PREF-01 |
| **P2** | 설정 | 데이터 초기화 | FR-PREF-02 |
| **P3 (TBD)** | 어드민 | 대시보드, 추천 관리, 품질 관리, 로깅 | FR-ADMIN-01~04 |
| **P3** | 멀티모달 | 음성 입출력 (STT/TTS) | FR-CHAT-08 |

---

## 2. 구현 계획

### 2.1 스프린트 구성

```
[Sprint 1] 챗봇 핵심 인터랙션 (P0)
  │  목표: 사용자가 대화를 통해 상품을 추천받는 E2E 경험
  │
  ├── FR-CHAT-01  새 대화 시작 + 펫 프로필 선택
  ├── FR-CHAT-03  컨텍스트 유지 (시스템 프롬프트)
  ├── FR-CHAT-05  대화 히스토리 사이드바
  ├── FR-CHAT-06  스트리밍 출력 + 중단 버튼
  ├── FR-REC-01   상품 카드 렌더링
  ├── FR-REC-02   상품 카드 클릭 -> 모달
  ├── FR-REC-04   추천 근거 표시
  ├── FR-CHAT-02  제목 자동 생성
  └── FR-CHAT-04  추천 질문 칩
  │
  ▼
[Sprint 2] 장바구니 + 구매 (P1)
  │  목표: 추천받은 상품을 장바구니에 담고 주문까지 완료
  │
  ├── FR-CART-01~04  장바구니 전체 플로우
  ├── FR-ORDER-01~04 구매 플로우 (Stub)
  └── FR-ORDER-04    Navbar 정비
  │
  ▼
[Sprint 3] 고도화 + 어드민 (P2/P3)
  │  목표: 사용자 경험 향상 및 관리 기능
  │
  ├── FR-AUTH-06   회원 탈퇴
  ├── FR-CHAT-07   이미지 업로드
  ├── FR-CHAT-09   토큰 관리
  ├── FR-REC-03/05/06  추천 고도화
  ├── FR-PREF-01/02    설정 기능
  └── FR-ADMIN-01~04   어드민 페이지
```

### 2.2 Sprint 1 상세: 챗봇 핵심 인터랙션

#### 2.2.1 새 대화 시작 + 펫 프로필 선택 (FR-CHAT-01)

| 항목 | 내용 |
|---|---|
| 위치 | 사이드바 상단 [새 대화] 버튼 |
| 동작 | 클릭 -> 펫 프로필 선택 드롭다운/모달 -> 선택 후 새 세션 준비 (Lazy: 첫 메시지 전송 시 실제 생성) |
| 백엔드 | `chat/api_views.py` - 세션 생성 API (`POST /api/chat/sessions/`) |
| 프론트 | `templates/chat/index.html` - 사이드바 이벤트, 펫 목록 fetch |
| 관련 모델 | `ChatSession.target_pet_id` (nullable FK -> Pet) |

#### 2.2.2 컨텍스트 유지 (FR-CHAT-03)

| 항목 | 내용 |
|---|---|
| 동작 | 선택된 펫 프로필(species, breed, age, weight, health_concerns, allergies, food_preferences)을 FastAPI 요청 페이로드에 포함 |
| 구현 | Django 프록시 -> FastAPI 전달 시 `pet_profile` dict 주입. LangGraph State에서 이미 `pet_profile` 필드 정의됨 |
| 멀티턴 | `chat_history` (이전 메시지 목록)를 함께 전송하여 맥락 유지 |

#### 2.2.3 대화 히스토리 (FR-CHAT-05)

| 항목 | 내용 |
|---|---|
| 위치 | 사이드바 목록 (날짜 그룹: 오늘/어제/7일/이전) |
| API | `GET /api/chat/sessions/` - 사용자 세션 목록 |
| 동작 | 클릭 -> 해당 세션 메시지 로드, 이름 변경/삭제 지원 |

#### 2.2.4 스트리밍 출력 (FR-CHAT-06)

| 항목 | 내용 |
|---|---|
| 프로토콜 | SSE (Server-Sent Events) 또는 chunked response |
| FastAPI | LangGraph respond 노드 -> LLM 스트리밍 -> SSE yield |
| Django 프록시 | `httpx` 스트리밍 프록시 또는 직접 FastAPI SSE 연결 |
| 프론트 | `EventSource` API로 토큰 단위 렌더링, 중단 버튼으로 AbortController 호출 |

#### 2.2.5 상품 카드 렌더링 (FR-REC-01, 02, 04)

| 항목 | 내용 |
|---|---|
| 위치 | 우측 패널 |
| 데이터 | LangGraph `product_cards` 필드 (이미지, 가격, 평점, 리뷰수) |
| 카드 클릭 | 내부 모달로 상세 정보 표시 (영양성분, 원료, 리뷰 요약) |
| 추천 근거 | AI 메시지(채팅 영역)에 프로필 맥락 기반 추천 이유 포함 |

### 2.3 Sprint 2 상세: 장바구니 + 구매

| 기능 | 구현 포인트 |
|---|---|
| 장바구니 담기 | 상품 카드 (+) 버튼 -> `POST /api/cart/items/` -> Cart/CartItem 모델 |
| 탭 구성 | 우측 패널 [추천 상품] / [장바구니] 탭 토글 |
| 수량 조절 | increase/decrease 버튼 + X 삭제 |
| 주문 플로우 | Cart Detail -> 주문 Modal (결제 Stub) -> 완료 페이지 -> Order/OrderItem 저장 |
| Navbar | 로그인 상태별 버튼 구성 (프로필/펫/장바구니/구매이력) |

---

## 3. 기술적 주요 결정사항

### 3.1 아키텍처 확정 사항 (기존 문서 기반)

| 항목 | 결정 |
|---|---|
| 프론트엔드 | Django Template (MVT) + Tailwind CSS + Vanilla JS |
| 백엔드 분리 | Django (Auth/User/Pet/Order) + FastAPI (챗봇/추천) |
| DB | PostgreSQL 16 + pgvector (Qdrant 제거 완료) |
| 검색 | pgvector Dense (1024d) + Kiwi tsvector + RRF Hybrid Search |
| AI | LangGraph 멀티에이전트, GPT-4o-mini |
| 인프라 | Docker Compose, Nginx, AWS EC2 (EB), GitHub Actions CI/CD |
| 서비스 간 통신 | Django -> FastAPI HTTP 프록시 (INTERNAL_SERVICE_TOKEN 검증) |

### 3.2 인증 아키텍처

```
[브라우저] ── JWT (Access Token) ──> [Nginx] ──> [Django]
                                                    │
                                              JWT 검증 (사용자 식별)
                                                    │
                                     X-Internal-Service-Token (공유 시크릿)
                                     X-User-Id (Django 유저 ID)
                                                    │
                                                    v
                                               [FastAPI]
                                          Internal Token 검증
                                          (외부 직접 접근 차단)
```

**브라우저 <-> Django (JWT)**

| 항목 | 내용 |
|---|---|
| 인증 방식 | JWT (Access Token + Refresh Token) |
| Access Token | 로그인 시 발급, 요청 헤더 `Authorization: Bearer <token>` |
| Refresh Token | Access Token 만료 시 갱신용 |
| 세션 병행 | Django 세션 쿠키도 유지 (Template 렌더링 시 사용) |

**Django <-> FastAPI (Internal Service Token)**

| 항목 | 내용 |
|---|---|
| 인증 방식 | `X-Internal-Service-Token` 헤더 (환경변수 공유 시크릿) |
| 사용자 전달 | `X-User-Id` 헤더로 Django 유저 ID 전달 |
| FastAPI 검증 | `core/auth.py` — 토큰 불일치 시 403 거부 |
| Nginx 라우팅 | 모든 `/api/*` 요청을 Django 경유. FastAPI는 외부 미노출 (expose only) |
| `/health` | Internal Token 불필요 (Docker healthcheck / LB용) |

### 3.3 서브모듈 구조

```
SKN22-Final-2Team-WEB/          (이 레포)
  services/django/              (Django 서비스, 이 레포 직접 관리)
  services/fastapi/             (submodule -> SKN22-Final-2Team-AI 레포)
```

- FastAPI/AI 코드는 별도 레포(SKN22-Final-2Team-AI)에서 관리
- 이 레포에서는 Django + 프론트엔드 + 인프라 + 문서를 관리

### 3.4 데이터 현황

| 테이블 | 건수 | 비고 |
|---|---|---|
| product | 3,618 | 상품 데이터 (pgvector 임베딩 적재 완료) |
| review | ~100,000+ | 감성분석/ABSA 완료 |
| domain_qna | TBD | 도메인 QA 데이터 (pgvector 적재 완료) |
| breed_meta | TBD | 품종별 메타데이터 |

---

## 4. 리스크 및 의존성

| 리스크 | 영향 | 대응 |
|---|---|---|
| FastAPI 서브모듈 동기화 | AI 팀 변경사항 반영 지연 | 주기적 submodule update, API 계약 문서화 |
| 스트리밍 프록시 복잡도 | Django -> FastAPI SSE 중계 시 지연/에러 | 프론트엔드에서 직접 FastAPI SSE 연결 검토 (Nginx 라우팅) |
| LLM 비용 | GPT-4o-mini 호출 비용 | 토큰 제한(FR-CHAT-09), 캐싱 전략 |
| 프로토타입 범위 | 기능 과다로 완성도 저하 | P0/P1 집중, P2/P3은 시간 여유 시 |

---

## 5. 성공 기준

| 기준 | 목표 |
|---|---|
| E2E 플로우 | 로그인 -> 펫 등록 -> 챗봇 대화 -> 상품 추천 -> 장바구니 -> 주문 완료 |
| 스트리밍 응답 | 첫 토큰 3초 이내 |
| 동시 사용자 | 10명 처리 (프로토타입 기준) |
| 추천 품질 | 펫 프로필 기반 맥락적합 상품 추천 (Hybrid Search + 재랭킹) |
| 배포 | AWS EB 라이브 데모 가능 |
