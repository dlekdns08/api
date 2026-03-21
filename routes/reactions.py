from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import Reaction
from schemas import ReactionToggle, ReactionResponse, ReactionCount, ALLOWED_EMOJIS

router = APIRouter(prefix="/posts", tags=["reactions"])


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
