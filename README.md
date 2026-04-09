# Blog API

코알라 오딧세이 블로그의 백엔드 API 서버입니다. 댓글, 좋아요, 리액션, 구독, 조회수, 지식 그래프 등 블로그 인터랙션 기능을 제공합니다.

## 기술 스택

- **Framework**: FastAPI
- **ORM**: SQLAlchemy (SQLite)
- **모니터링**: Prometheus (prometheus-fastapi-instrumentator)
- **배포**: Docker

## API 엔드포인트

| 기능 | 엔드포인트 |
|------|-----------|
| 댓글 (대댓글 지원) | `/comments` |
| 좋아요 | `/likes` |
| 리액션 (이모지) | `/reactions` |
| 이메일 구독 | `/subscribe` |
| 조회수 | `/views` |
| 지식 그래프 | `/knowledge-graph` |

## 프로젝트 구조

```text
api/
├── main.py          # FastAPI 앱 진입점 + CORS 설정
├── database.py      # SQLAlchemy 엔진/세션 관리
├── models.py        # ORM 모델 (Comment, Like, Reaction, Subscriber, PostView, PostGraphCache)
├── schemas.py       # Pydantic 스키마
├── routes/
│   ├── comments.py
│   ├── likes.py
│   ├── reactions.py
│   ├── subscribe.py
│   ├── views.py
│   └── knowledge_graph.py
├── Dockerfile
└── docker-compose.yml
```

## 실행

```bash
# 개발
uvicorn main:app --reload

# Docker
docker compose up -d
```

## 관련 프로젝트

- [blog](https://github.com/dlekdns08/blog) — Next.js 프론트엔드
<!-- trigger -->
