from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import Like
from schemas import LikeToggle, LikeResponse

router = APIRouter(prefix="/posts", tags=["likes"])


def _count(db: Session, slug: str) -> int:
    return db.query(Like).filter(Like.post_slug == slug).count()


@router.get("/likes/bulk")
def get_likes_bulk(
    slugs: str = Query(..., description="쉼표로 구분된 슬러그 목록"),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """여러 포스트의 좋아요 수를 한번에 조회 — { slug: count } 딕셔너리 반환"""
    slug_list = [s.strip() for s in slugs.split(",") if s.strip()]
    if not slug_list:
        return {}
    rows = (
        db.query(Like.post_slug, func.count(Like.id).label("cnt"))
        .filter(Like.post_slug.in_(slug_list))
        .group_by(Like.post_slug)
        .all()
    )
    counts: dict[str, int] = {slug: 0 for slug in slug_list}
    for slug, cnt in rows:
        counts[slug] = cnt
    return counts


@router.get("/{slug:path}/likes", response_model=LikeResponse)
def get_likes(slug: str, client_id: str, db: Session = Depends(get_db)):
    """좋아요 수 및 현재 클라이언트의 좋아요 여부 조회"""
    liked = (
        db.query(Like)
        .filter(Like.post_slug == slug, Like.client_id == client_id)
        .first()
        is not None
    )
    return LikeResponse(liked=liked, count=_count(db, slug))


@router.post("/{slug:path}/likes", response_model=LikeResponse)
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
