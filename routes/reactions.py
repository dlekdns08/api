from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import Reaction
from schemas import ReactionToggle, ReactionResponse, ReactionCount, ALLOWED_EMOJIS

router = APIRouter(prefix="/posts", tags=["reactions"])


@router.get("/reactions/bulk")
def get_reactions_bulk(
    slugs: str = Query(..., description="쉼표로 구분된 슬러그 목록"),
    db: Session = Depends(get_db),
) -> dict[str, dict[str, int]]:
    """여러 포스트의 반응 수를 한번에 조회 — { slug: { emoji: count } } 반환"""
    slug_list = [s.strip() for s in slugs.split(",") if s.strip()]
    if not slug_list:
        return {}

    rows = (
        db.query(Reaction.post_slug, Reaction.emoji, func.count(Reaction.id).label("cnt"))
        .filter(Reaction.post_slug.in_(slug_list))
        .group_by(Reaction.post_slug, Reaction.emoji)
        .all()
    )

    result: dict[str, dict[str, int]] = {slug: {} for slug in slug_list}
    for slug, emoji, cnt in rows:
        result[slug][emoji] = cnt
    return result


def _get_reaction_state(slug: str, client_id: str, db: Session) -> ReactionResponse:
    rows = (
        db.query(Reaction.emoji, func.count(Reaction.id).label("cnt"))
        .filter(Reaction.post_slug == slug)
        .group_by(Reaction.emoji)
        .all()
    )
    counts = {r.emoji: r.cnt for r in rows}

    reacted_set = {
        r.emoji
        for r in db.query(Reaction.emoji)
        .filter(Reaction.post_slug == slug, Reaction.client_id == client_id)
        .all()
    }

    return ReactionResponse(
        reactions=[
            ReactionCount(emoji=e, count=counts.get(e, 0), reacted=e in reacted_set)
            for e in ALLOWED_EMOJIS
        ]
    )


@router.get("/{slug:path}/reactions", response_model=ReactionResponse)
def get_reactions(
    slug: str,
    client_id: str = Query(...),
    db: Session = Depends(get_db),
):
    return _get_reaction_state(slug, client_id, db)


@router.post("/{slug:path}/reactions", response_model=ReactionResponse)
def toggle_reaction(slug: str, body: ReactionToggle, db: Session = Depends(get_db)):
    existing = (
        db.query(Reaction)
        .filter(
            Reaction.post_slug == slug,
            Reaction.client_id == body.client_id,
            Reaction.emoji == body.emoji,
        )
        .first()
    )

    if existing:
        db.delete(existing)
    else:
        try:
            db.add(Reaction(post_slug=slug, client_id=body.client_id, emoji=body.emoji))
        except IntegrityError:
            db.rollback()
            return _get_reaction_state(slug, body.client_id, db)

    db.commit()
    return _get_reaction_state(slug, body.client_id, db)
