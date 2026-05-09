import os
import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from models import Subscriber
from email_utils import (
    send_email,
    render_confirm_html,
    render_new_post_html,
    render_digest_html,
    BLOG_URL,
    API_URL,
)

router = APIRouter(prefix="/subscribe", tags=["subscribe"])

NOTIFY_API_KEY = os.environ.get("NOTIFY_API_KEY", "")


class SubscribeRequest(BaseModel):
    email: EmailStr


class NotifyRequest(BaseModel):
    title: str
    slug: str
    url: str
    api_key: str


class DigestPost(BaseModel):
    title: str
    url: str
    tldr: str | None = None
    date: str | None = None
    category: str | None = None


class DigestRequest(BaseModel):
    api_key: str
    week_label: str
    posts: list[DigestPost]


@router.post("")
def subscribe(req: SubscribeRequest, db: Session = Depends(get_db)):
    existing = db.query(Subscriber).filter(Subscriber.email == req.email).first()
    if existing:
        if existing.confirmed:
            return {"message": "이미 구독 중입니다."}
        # 미확인 상태면 확인 메일 재발송
        confirm_url = f"{API_URL}/subscribe/confirm/{existing.confirm_token}"
        send_email(
            req.email,
            "[코알라 오딧세이] 구독 확인 메일",
            render_confirm_html(req.email, confirm_url),
        )
        return {"message": "확인 메일을 재발송했습니다."}

    confirm_token = secrets.token_urlsafe(32)
    unsubscribe_token = secrets.token_urlsafe(32)
    sub = Subscriber(email=req.email, confirm_token=confirm_token, unsubscribe_token=unsubscribe_token)
    db.add(sub)
    db.commit()

    confirm_url = f"{API_URL}/subscribe/confirm/{confirm_token}"
    send_email(
        req.email,
        "[코알라 오딧세이] 구독 확인 메일",
        render_confirm_html(req.email, confirm_url),
    )
    return {"message": "확인 메일을 발송했습니다. 메일함을 확인해주세요."}


@router.get("/confirm/{token}", response_class=HTMLResponse)
def confirm(token: str, db: Session = Depends(get_db)):
    sub = db.query(Subscriber).filter(Subscriber.confirm_token == token).first()
    if not sub:
        raise HTTPException(status_code=404, detail="유효하지 않은 토큰입니다.")
    sub.confirmed = True
    db.commit()
    return HTMLResponse(f"""<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:480px;margin:80px auto;text-align:center;color:#18181b">
<div style="font-size:48px">🐨</div>
<h2>구독 완료!</h2>
<p>새 글이 올라오면 <b>{sub.email}</b>로 알려드릴게요.</p>
<a href="{BLOG_URL}" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#7c3aed;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">블로그 구경하기</a>
</body></html>""")


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
def unsubscribe(token: str, db: Session = Depends(get_db)):
    sub = db.query(Subscriber).filter(Subscriber.unsubscribe_token == token).first()
    if not sub:
        raise HTTPException(status_code=404, detail="유효하지 않은 토큰입니다.")
    db.delete(sub)
    db.commit()
    return HTMLResponse(f"""<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:480px;margin:80px auto;text-align:center;color:#18181b">
<div style="font-size:48px">👋</div>
<h2>구독 취소 완료</h2>
<p>더 이상 메일을 받지 않습니다.</p>
<a href="{BLOG_URL}" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#7c3aed;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">블로그 방문하기</a>
</body></html>""")


@router.post("/notify")
def notify(req: NotifyRequest, db: Session = Depends(get_db)):
    """단일 새 글 알림 — 즉시성 발송 (deploy workflow에서 호출)."""
    if not NOTIFY_API_KEY or req.api_key != NOTIFY_API_KEY:
        raise HTTPException(status_code=401, detail="인증 실패")

    subscribers = db.query(Subscriber).filter(Subscriber.confirmed == True).all()
    if not subscribers:
        return {"message": "구독자 없음", "sent": 0}

    sent = 0
    for sub in subscribers:
        try:
            unsubscribe_url = f"{API_URL}/subscribe/unsubscribe/{sub.unsubscribe_token}"
            send_email(
                sub.email,
                f"[코알라 오딧세이] 새 글: {req.title}",
                render_new_post_html(req.title, req.url, unsubscribe_url),
            )
            sent += 1
        except Exception:
            pass

    return {"message": f"{sent}명에게 발송 완료", "sent": sent}


@router.post("/digest")
def send_digest(req: DigestRequest, db: Session = Depends(get_db)):
    """주간/기간별 다이제스트 발송 — 여러 글을 한 통에 모음."""
    if not NOTIFY_API_KEY or req.api_key != NOTIFY_API_KEY:
        raise HTTPException(status_code=401, detail="인증 실패")
    if len(req.posts) == 0:
        return {"message": "보낼 글 없음", "sent": 0}

    subscribers = db.query(Subscriber).filter(Subscriber.confirmed == True).all()
    if not subscribers:
        return {"message": "구독자 없음", "sent": 0}

    sent = 0
    posts_dict = [p.model_dump() for p in req.posts]
    for sub in subscribers:
        try:
            unsubscribe_url = f"{API_URL}/subscribe/unsubscribe/{sub.unsubscribe_token}"
            html = render_digest_html(req.week_label, posts_dict, unsubscribe_url)
            send_email(
                sub.email,
                f"[코알라 오딧세이] {req.week_label} 다이제스트",
                html,
            )
            sent += 1
        except Exception:
            pass

    return {"message": f"{sent}명에게 발송 완료", "sent": sent, "posts": len(req.posts)}
