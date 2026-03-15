from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routes import comments, likes

# 테이블 자동 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(title="코알라 오딧세이 Blog API", version="1.0.0"
# CORS — Next.js 개발 서버 및 프로덕션 도메인 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://koala.ai.kr"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(comments.router)
app.include_router(likes.router)


@app.get("/health")
def health():
    return {"status": "ok"}
