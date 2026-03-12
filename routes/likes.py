from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import Like
from schemas import LikeToggle, LikeResponse

router = APIRouter(prefix="/posts/{slug}/likes", tags=["likes"])


def _count(db: Session, slug: str) -> int:
    return db.query(Like).filter(Like.post_slug == slug).count()


@router.get("", response_model=LikeResponse)
def get_likes(slug: str, client_id: str, db: Session = Depends(get_db)):
    """좋아요 수 및 현재 클라이언트의 좋아요 여부 조회"""
    liked = (
        db.query(Like)
        .filter(Like.post_slug == slug, Like.client_id == client_id)
        .first()
        is not None
    )
    return LikeResponse(liked=liked, count=_count(db, slug))


@router.post("", response_model=LikeResponse)
def toggle_like(slug: str, body: LikeToggle, db: Session = Depends(get_db)):
    """좋아요 토글 — 이미 눌렀으면 취소, 아니면 추가"""
    existing = (
        db.query(Like)
        .filter(Like.post_slug == slug, Like.client_id == body.client_id)
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        return LikeResponse(liked=False, count=_count(db, slug))

    try:
        like = Like(post_slug=slug, client_id=body.client_id)
        db.add(like)
        db.commit()
    except IntegrityError:
        db.rollback()

    return LikeResponse(liked=True, count=_count(db, slug))
