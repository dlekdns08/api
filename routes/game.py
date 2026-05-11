from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import GameRanking
from schemas import GameScoreSubmit, GameRankingItem

router = APIRouter(prefix="/game", tags=["game"])

GAME_KEY = "koala"


@router.get("/koala/rankings", response_model=list[GameRankingItem])
def get_koala_rankings(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(GameRanking)
        .filter(GameRanking.game == GAME_KEY)
        .order_by(GameRanking.score.desc(), GameRanking.created_at.asc())
        .limit(limit)
        .all()
    )
    return rows


@router.post("/koala/rankings")
def submit_koala_score(body: GameScoreSubmit, db: Session = Depends(get_db)):
    existing = (
        db.query(GameRanking)
        .filter(
            GameRanking.game == GAME_KEY,
            GameRanking.client_id == body.client_id,
        )
        .order_by(GameRanking.score.desc())
        .first()
    )

    if existing and existing.score >= body.score:
        existing.nickname = body.nickname
        db.commit()
        return {"ok": True, "id": existing.id, "score": existing.score, "best": True}

    if existing:
        existing.nickname = body.nickname
        existing.score = body.score
        db.commit()
        db.refresh(existing)
        return {"ok": True, "id": existing.id, "score": existing.score, "best": False}

    entry = GameRanking(
        game=GAME_KEY,
        nickname=body.nickname,
        score=body.score,
        client_id=body.client_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id, "score": entry.score, "best": False}
