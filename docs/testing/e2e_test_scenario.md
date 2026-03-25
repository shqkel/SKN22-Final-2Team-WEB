# E2E 테스트 시나리오

> 로컬 환경에서 TailTalk 전체 기능을 수동 검증하는 가이드

---

## 0. 환경 준비

### 0-1. .env 파일 설정

```bash
cp .env.example infra/.env
```

`infra/.env` 편집:

```env
POSTGRES_DB=tailtalk
POSTGRES_USER=tailtalk
POSTGRES_PASSWORD=changeme
DJANGO_SECRET_KEY=test-secret-key-for-local-dev-only
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost
OPENAI_API_KEY=sk-your-openai-key    # 챗봇 테스트 시 필수
INTERNAL_SERVICE_TOKEN=dev-internal-token
```

### 0-2. Docker Compose 실행

```bash
cd infra
docker compose up -d --build
```

빌드 완료까지 수 분 소요. 상태 확인:

```bash
docker compose ps
# nginx, django, fastapi, postgres 모두 running 확인
docker compose logs -f django   # migrate 완료 확인
```

### 0-3. DB 데이터 복원

```bash
# 팀 공유 드라이브에서 dump 파일을 backup/ 에 복사 후:
./scripts/restore_postgres.sh
```

> 상품/리뷰 데이터가 없으면 챗봇 추천이 동작하지 않음

### 0-4. 슈퍼유저 생성

```bash
docker compose run --rm django python manage.py createsuperuser
```

### 0-5. 접속

- 메인: http://localhost
- Admin: http://localhost/admin/
- FastAPI Health: `curl http://localhost:8001/health` (Docker 내부에서만 접근 가능)

---

## 1. 인증 플로우

### TC-1.1: 이메일 회원가입

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | http://localhost 접속 | 랜딩/로그인 페이지 표시 |
| 2 | [회원가입] 클릭 | 회원가입 폼 표시 |
| 3 | 이메일 + 비밀번호 입력 후 가입 | 가입 완료 -> 온보딩(/pets/add/) 자동 이동 |

### TC-1.2: 이메일 로그인

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | /login/ 접속 | 로그인 폼 표시 |
| 2 | 등록한 이메일 + 비밀번호 입력 | 로그인 성공 -> 챗봇 메인 이동 |

### TC-1.3: 소셜 로그인 (OAuth 키 설정 시)

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | 로그인 페이지에서 Google/Kakao/Naver 버튼 클릭 | OAuth 인증 페이지 이동 |
| 2 | 인증 완료 | 콜백 -> 프로필 설정 or 챗봇 메인 |

### TC-1.4: 비로그인 차단

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | 로그아웃 상태에서 /chat/ 접속 | 채팅 Input disabled, "로그인이 필요한 서비스입니다." 표시 |

---

## 2. 반려동물 프로필

### TC-2.1: 온보딩 플로우

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | /pets/add/ 접속 | Step 1: 종류 선택 (강아지/고양이/예비 집사) |
| 2 | 강아지 선택 -> 다음 | Step 2: 기본 정보 (이름, 품종, 성별, 나이) |
| 3 | 정보 입력 -> 다음 | Step 3: 건강/식이 (관심사, 알레르기, 사료 선호) |
| 4 | 완료 | 챗봇 메인 리다이렉트 |

### TC-2.2: 프로필 목록/수정

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | /pets/ 접속 | 등록된 반려동물 목록 |
| 2 | 펫 선택 -> 수정 | 정보 수정 폼 -> 저장 성공 |

---

## 3. 챗봇 핵심 (Sprint 1)

### TC-3.1: 새 대화 + 펫 선택

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | /chat/ 접속 (로그인 상태) | 3패널 레이아웃 (사이드바 + 채팅 + 우측 패널) |
| 2 | 좌측 펫 드롭다운 클릭 | 등록된 펫 목록 표시 |
| 3 | 펫 선택 (예: "콩이") | 드롭다운에 선택된 펫 이름/요약 표시 |
| 4 | 사이드바 [새 대화] 클릭 | 채팅 영역 초기화, 추천 질문 칩 표시 |

### TC-3.2: 메시지 전송 + SSE 스트리밍

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | 입력창에 "우리 콩이 피부에 좋은 사료 추천해줘" 입력 | 전송 아이콘 활성화 |
| 2 | Enter 또는 전송 버튼 클릭 | (a) 사용자 메시지 즉시 표시 (파란 버블, 우측) |
| | | (b) 입력창 비활성화, 중단(■) 버튼 표시 |
| | | (c) AI 응답 토큰 단위 스트리밍 (흰 버블, 좌측) |
| 3 | 스트리밍 완료 대기 | (a) 입력창 재활성화, 전송 버튼 복귀 |
| | | (b) 사이드바에 새 세션 항목 추가 (제목: 메시지 앞 18자) |

### TC-3.3: 상품 카드 렌더링

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | TC-3.2 완료 후 | 우측 패널 [추천 상품] 탭에 상품 카드 표시 |
| 2 | 카드 확인 | 썸네일, 상품명, 브랜드, 가격(할인가), 평점, [+장바구니] 버튼 |
| 3 | 카드 클릭 | 어바웃펫 상품 페이지 새 탭 오픈 |
| 4 | [+장바구니] 클릭 | 장바구니 탭에 해당 상품 추가 |

### TC-3.4: 스트리밍 중단

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | 메시지 전송 직후 | AI 응답 스트리밍 시작 + 중단(■) 버튼 표시 |
| 2 | 중단 버튼 클릭 | (a) 스트리밍 즉시 중지 |
| | | (b) 현재까지 받은 텍스트 유지 |
| | | (c) 입력창 재활성화 |

### TC-3.5: 대화 히스토리

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | TC-3.2로 여러 대화 생성 | 사이드바에 대화 목록 표시 |
| 2 | 다른 대화 클릭 | 해당 대화의 메시지 히스토리 로드 |
| 3 | 대화 항목 호버 -> 연필 아이콘 클릭 | 제목 인라인 편집 -> Enter로 저장 |
| 4 | 대화 항목 호버 -> 휴지통 아이콘 클릭 | 삭제 확인 모달 -> 확인 -> 대화 삭제 |

### TC-3.6: 멀티턴 대화

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | 첫 메시지: "피부에 좋은 사료 추천해줘" | AI 응답 + 상품 카드 |
| 2 | 후속 메시지: "그중에서 가격이 저렴한 거 알려줘" | 이전 맥락 유지한 응답 |
| 3 | 후속 메시지: "원료 성분도 알려줘" | 대화 흐름 이어감 |

---

## 4. 장바구니 (Sprint 2)

### TC-4.1: 상품 추가

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | 추천 상품 카드의 [+장바구니] 클릭 | 장바구니 탭에 상품 추가 |
| 2 | 같은 상품 다시 [+장바구니] 클릭 | 수량 +1 증가 (중복 아이템 X) |
| 3 | [장바구니] 탭 클릭 | 담은 상품 목록, 수량, 합계 표시 |

### TC-4.2: 수량 조절 / 삭제

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | 장바구니 아이템 [+] 버튼 | 수량 증가, 합계 갱신 |
| 2 | [-] 버튼 (최소 1) | 수량 감소, 1 이하로 안 내려감 |
| 3 | [X] 버튼 | 아이템 삭제, 합계 갱신 |

### TC-4.3: 서버 동기화 확인

| Step | 동작 | 기대 결과 |
|:---:|---|---|
| 1 | 상품 몇 개 장바구니에 담기 | 장바구니 탭에 표시 |
| 2 | 페이지 새로고침 (F5) | 장바구니 데이터 유지 (서버에서 복원) |

> 현재 구현: 서버 API 연동 완료. 단, 페이지 초기 로딩 시 서버 장바구니 불러오기는 추가 프론트 작업 필요 (page_views.py에서 context로 전달 또는 JS fetch).

---

## 5. 주문 (Sprint 2)

### TC-5.1: 주문 생성 (API)

```bash
# JWT 토큰 발급
TOKEN=$(curl -s -X POST http://localhost/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"your-password"}' | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

# 장바구니에 상품 추가
curl -X POST http://localhost/api/cart/items/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"goods_id":"GI00001","quantity":2}'

# 장바구니 확인
curl http://localhost/api/cart/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 주문 생성
curl -X POST http://localhost/api/orders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"recipient_name":"홍길동","delivery_address":"서울시 강남구"}'

# 주문 목록 확인
curl http://localhost/api/orders/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

---

## 6. Interaction 로깅

### TC-6.1: 로깅 확인 (DB)

```bash
# Django shell 접속
docker compose exec django python manage.py shell

>>> from orders.models import UserInteraction
>>> UserInteraction.objects.all().values('interaction_type', 'weight', 'product__goods_name')
```

| 동작 | 기대 로그 |
|---|---|
| 상품 카드 클릭 | `interaction_type=click, weight=1` |
| [+장바구니] 클릭 | `interaction_type=cart, weight=3` |
| 주문 완료 | `interaction_type=purchase, weight=5` |

---

## 7. 인증 보안

### TC-7.1: Internal Token 검증

```bash
# FastAPI 직접 호출 (Nginx 우회) — Docker 내부에서만 가능
docker compose exec django curl http://fastapi:8001/api/chat/ \
  -X POST -H "Content-Type: application/json" \
  -d '{"message":"test"}'
# 기대: 403 (Internal Token 없음)

docker compose exec django curl http://fastapi:8001/api/chat/ \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Token: dev-internal-token" \
  -d '{"message":"test","thread_id":"t1"}'
# 기대: 200 SSE 스트리밍

# Health check — 토큰 불필요
docker compose exec django curl http://fastapi:8001/health
# 기대: {"status":"ok"}
```

### TC-7.2: 외부에서 FastAPI 직접 접근 불가

```bash
# 로컬 브라우저에서 http://localhost:8001 접속
# 기대: 연결 거부 (Nginx가 FastAPI를 외부에 노출하지 않음)
```

---

## 8. 단위 테스트 실행

```bash
# PostgreSQL 실행 (이미 docker compose up -d 했다면 생략)
# 포트 매핑 필요: docker-compose.yml에 ports: "15432:5432" 추가하거나
# 별도 컨테이너:
docker run -d --name tailtalk-test-pg \
  -e POSTGRES_DB=tailtalk \
  -e POSTGRES_USER=tailtalk \
  -e POSTGRES_PASSWORD=testpass \
  -p 15432:5432 \
  pgvector/pgvector:pg16

# 테스트 실행 (44개)
cd services/django
DJANGO_SECRET_KEY=test-secret \
POSTGRES_DB=tailtalk \
POSTGRES_USER=tailtalk \
POSTGRES_PASSWORD=testpass \
POSTGRES_HOST=localhost \
POSTGRES_PORT=15432 \
FASTAPI_INTERNAL_CHAT_URL=http://fastapi:8001/api/chat/ \
INTERNAL_SERVICE_TOKEN=test-token \
python manage.py test chat orders --settings=config.test_settings -v2

# 기대: Ran 44 tests in ~1.5s — OK

# 정리
docker rm -f tailtalk-test-pg
```

---

## 9. 체크리스트

| # | 영역 | 테스트 | Pass |
|:---:|---|---|:---:|
| 1 | 인증 | 회원가입 -> 온보딩 자동 이동 | [ ] |
| 2 | 인증 | 로그인 -> 챗봇 메인 이동 | [ ] |
| 3 | 인증 | 비로그인 시 Input disabled | [ ] |
| 4 | 펫 | 온보딩 3단계 완료 | [ ] |
| 5 | 챗봇 | 펫 선택 후 메시지 전송 | [ ] |
| 6 | 챗봇 | SSE 스트리밍 응답 표시 | [ ] |
| 7 | 챗봇 | 상품 카드 우측 패널 표시 | [ ] |
| 8 | 챗봇 | 중단 버튼 동작 | [ ] |
| 9 | 챗봇 | 대화 히스토리 클릭 -> 로드 | [ ] |
| 10 | 챗봇 | 대화 제목 수정/삭제 | [ ] |
| 11 | 챗봇 | 멀티턴 대화 맥락 유지 | [ ] |
| 12 | 장바구니 | [+장바구니] -> 탭에 추가 | [ ] |
| 13 | 장바구니 | 수량 조절/삭제 | [ ] |
| 14 | 주문 | API로 주문 생성 | [ ] |
| 15 | 보안 | FastAPI 외부 접근 차단 | [ ] |
| 16 | 보안 | Internal Token 없이 FastAPI 403 | [ ] |
| 17 | 단위 테스트 | 44개 전부 Pass | [ ] |
