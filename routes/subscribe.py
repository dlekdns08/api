import os
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from models import Subscriber

router = APIRouter(prefix="/subscribe", tags=["subscribe"])

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
BLOG_URL = os.environ.get("BLOG_URL", "https://koala.ai.kr")
API_URL = os.environ.get("API_URL", "https://api.koala.ai.kr")
NOTIFY_API_KEY = os.environ.get("NOTIFY_API_KEY", "")


def _send_email(to: str, subject: str, html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"코알라 오딧세이 <{SMTP_USER}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.sendmail(SMTP_USER, to, msg.as_string())


def _confirm_html(email: str) -> str:
    return f"""<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:480px;margin:40px auto;color:#18181b">
<h2>🐨 구독 확인</h2>
<p><b>{email}</b>으로 코알라 오딧세이 구독 신청이 들어왔습니다.</p>
<p>아래 버튼을 눌러 구독을 완료하세요.</p>
<a href="{{confirm_url}}" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#7c3aed;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">구독 확인하기</a>
<p style="margin-top:24px;font-size:12px;color:#71717a">본인이 신청하지 않았다면 이 메일을 무시하세요.</p>
</body></html>"""


def _notify_html(title: str, post_url: str, unsubscribe_url: str) -> str:
    return f"""<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:480px;margin:40px auto;color:#18181b">
<h2>🐨 새 글이 올라왔어요!</h2>
<h3 style="color:#7c3aed">{title}</h3>
<a href="{post_url}" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#7c3aed;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">글 읽으러 가기</a>
<p style="margin-top:32px;font-size:12px;color:#71717a">
  <a href="{unsubscribe_url}" style="color:#71717a">구독 취소</a>
</p>
</body></html>"""


class SubscribeRequest(BaseModel):
    email: EmailStr


class NotifyRequest(BaseModel):
    title: str
    slug: str
    url: str
    api_key: str


@router.post("")
def subscribe(req: SubscribeRequest, db: Session = Depends(get_db)):
    existing = db.query(Subscriber).filter(Subscriber.email == req.email).first()
    if existing:
        if existing.confirmed:
            return {"message": "이미 구독 중입니다."}
        # 미확인 상태면 확인 메일 재발송
        confirm_url = f"{API_URL}/subscribe/confirm/{existing.confirm_token}"
        _send_email(req.email, "[코알라 오딧세이] 구독 확인 메일", _confirm_html(req.email).replace("{confirm_url}", confirm_url))
        return {"message": "확인 메일을 재발송했습니다."}

    confirm_token = secrets.token_urlsafe(32)
    unsubscribe_token = secrets.token_urlsafe(32)
    sub = Subscriber(email=req.email, confirm_token=confirm_token, unsubscribe_token=unsubscribe_token)
    db.add(sub)
    db.commit()

    confirm_url = f"{API_URL}/subscribe/confirm/{confirm_token}"
    _send_email(req.email, "[코알라 오딧세이] 구독 확인 메일", _confirm_html(req.email).replace("{confirm_url}", confirm_url))
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
    if not NOTIFY_API_KEY or req.api_key != NOTIFY_API_KEY:
        raise HTTPException(status_code=401, detail="인증 실패")

    subscribers = db.query(Subscriber).filter(Subscriber.confirmed == True).all()
    if not subscribers:
        return {"message": "구독자 없음", "sent": 0}

    sent = 0
    for sub in subscribers:
        try:
            unsubscribe_url = f"{API_URL}/subscribe/unsubscribe/{sub.unsubscribe_token}"
            _send_email(
                sub.email,
                f"[코알라 오딧세이] 새 글: {req.title}",
                _notify_html(req.title, req.url, unsubscribe_url),
            )
            sent += 1
        except Exception:
            pass

    return {"message": f"{sent}명에게 발송 완료", "sent": sent}
