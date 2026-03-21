from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from database import get_db
from models import PostView

router = APIRouter(prefix="/posts", tags=["views"])


@router.post("/{slug:path}/view")
def increment_view(slug: str, db: Session = Depends(get_db)) -> dict:
    """조회수 1 증가 (없으면 새로 생성)"""
    stmt = (
        insert(PostView)
        .values(post_slug=slug, views=1)
        .on_conflict_do_update(
            index_elements=["post_slug"],
            set_={"views": PostView.views + 1},
        )
    )
    db.execute(stmt)
    db.commit()
    row = db.query(PostView).filter(PostView.post_slug == slug).first()
    return {"slug": slug, "views": row.views if row else 1}


@router.get("/views/bulk")
def get_views_bulk(
    slugs: str = Query(..., description="쉼표로 구분된 슬러그 목록"),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """여러 포스트의 조회수 한번에 조회"""
    slug_list = [s.strip() for s in slugs.split(",") if s.strip()]
    if not slug_list:
        return {}
    rows = db.query(PostView).filter(PostView.post_slug.in_(slug_list)).all()
    result = {slug: 0 for slug in slug_list}
    for row in rows:
        result[row.post_slug] = row.views
    return result


@router.get("/views/top")
def get_top_views(
    limit: int = Query(default=5, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    """조회수 상위 포스트 목록"""
    rows = (
        db.query(PostView)
        .order_by(PostView.views.desc())
        .limit(limit)
        .all()
    )
    return [{"slug": r.post_slug, "views": r.views} for r in rows]
