"""SMTP 메일 발송 + 도메인별 메일 빌더 모음.
subscribe.py / comments.py 등에서 공유.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
BLOG_URL = os.environ.get("BLOG_URL", "https://koala.ai.kr")
API_URL = os.environ.get("API_URL", "https://api.koala.ai.kr")


def send_email(to: str, subject: str, html: str) -> None:
    """SMTP로 단일 HTML 메일 발송. SMTP 미설정 시 ValueError."""
    if not SMTP_USER or not SMTP_PASSWORD:
        raise ValueError("SMTP_USER/SMTP_PASSWORD가 설정되지 않았습니다.")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"코알라 오딧세이 <{SMTP_USER}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.sendmail(SMTP_USER, to, msg.as_string())


# ── 메일 템플릿 ────────────────────────────────────────────


def render_confirm_html(email: str, confirm_url: str) -> str:
    return f"""<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:480px;margin:40px auto;color:#18181b">
<h2>🐨 구독 확인</h2>
<p><b>{email}</b>으로 코알라 오딧세이 구독 신청이 들어왔습니다.</p>
<p>아래 버튼을 눌러 구독을 완료하세요.</p>
<a href="{confirm_url}" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#7c3aed;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">구독 확인하기</a>
<p style="margin-top:24px;font-size:12px;color:#71717a">본인이 신청하지 않았다면 이 메일을 무시하세요.</p>
</body></html>"""


def render_new_post_html(title: str, post_url: str, unsubscribe_url: str) -> str:
    return f"""<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:480px;margin:40px auto;color:#18181b">
<h2>🐨 새 글이 올라왔어요!</h2>
<h3 style="color:#7c3aed">{title}</h3>
<a href="{post_url}" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#7c3aed;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">글 읽으러 가기</a>
<p style="margin-top:32px;font-size:12px;color:#71717a">
  <a href="{unsubscribe_url}" style="color:#71717a">구독 취소</a>
</p>
</body></html>"""


def render_admin_comment_html(post_slug: str, nickname: str, content: str, comment_id: int) -> str:
    post_url = f"{BLOG_URL}/posts/{post_slug}#comment-{comment_id}"
    safe_content = (content[:300] + "…") if len(content) > 300 else content
    # HTML escape 최소 처리
    safe_content = (safe_content
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))
    return f"""<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:520px;margin:40px auto;color:#18181b">
<h2>🐨 새 댓글이 달렸어요!</h2>
<p style="color:#71717a;font-size:13px;margin-bottom:8px;margin-top:24px">글</p>
<p style="font-weight:600;margin-top:0;font-family:monospace">{post_slug}</p>
<p style="color:#71717a;font-size:13px;margin-bottom:8px;margin-top:24px">작성자</p>
<p style="font-weight:600;margin-top:0">{nickname}</p>
<p style="color:#71717a;font-size:13px;margin-bottom:8px;margin-top:24px">내용</p>
<blockquote style="border-left:3px solid #a78bfa;padding:8px 12px;background:#f4f4f5;margin:0;color:#27272a;white-space:pre-wrap;border-radius:0 4px 4px 0">{safe_content}</blockquote>
<a href="{post_url}" style="display:inline-block;margin-top:24px;padding:12px 24px;background:#7c3aed;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">바로 가기</a>
</body></html>"""


def render_digest_html(week_label: str, posts: list[dict], unsubscribe_url: str) -> str:
    """주간 다이제스트 — 여러 글 모음."""
    items = []
    for p in posts:
        tldr_block = ""
        if p.get("tldr"):
            tldr_lines = [line for line in p["tldr"].split("\n") if line.strip()][:3]
            tldr_html = "".join(f'<li style="margin-bottom:4px">{line}</li>' for line in tldr_lines)
            tldr_block = f'<ul style="margin:8px 0 0 0;padding-left:18px;font-size:13px;color:#52525b">{tldr_html}</ul>'
        cat = p.get("category") or ""
        cat_html = (
            f'<span style="font-size:11px;color:#a78bfa;text-transform:uppercase;letter-spacing:0.05em;font-weight:600">{cat}</span>'
            if cat else ""
        )
        items.append(f"""
<div style="border:1px solid #e4e4e7;border-radius:12px;padding:16px;margin-bottom:12px;background:#fff">
  {cat_html}
  <h3 style="margin:4px 0 4px 0;font-size:16px"><a href="{p['url']}" style="color:#18181b;text-decoration:none">{p['title']}</a></h3>
  {tldr_block}
  <a href="{p['url']}" style="display:inline-block;margin-top:12px;padding:6px 14px;background:#7c3aed;color:#fff;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600">읽기 →</a>
</div>""")
    items_html = "".join(items)

    return f"""<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:560px;margin:40px auto;color:#18181b;background:#fafafa;padding:24px">
<h2>🐨 코알라 오딧세이 — {week_label}</h2>
<p style="color:#52525b;font-size:14px">최근 새로 올라온 글 {len(posts)}개를 모아 보내드려요.</p>
<div style="margin-top:24px">{items_html}</div>
<p style="margin-top:32px;font-size:12px;color:#a1a1aa;text-align:center">
  <a href="{unsubscribe_url}" style="color:#a1a1aa">구독 취소</a>
</p>
</body></html>"""


def notify_admin_comment(post_slug: str, nickname: str, content: str, comment_id: int) -> None:
    """새 댓글 알림 — ADMIN_EMAIL 미설정 시 무시. 예외 삼킴(댓글 작성 차단 방지)."""
    if not ADMIN_EMAIL:
        return
    try:
        html = render_admin_comment_html(post_slug, nickname, content, comment_id)
        subject = f"[코알라 오딧세이] 새 댓글: {post_slug[:60]}"
        send_email(ADMIN_EMAIL, subject, html)
    except Exception as e:
        print(f"[email_utils] notify_admin_comment failed: {e}")
