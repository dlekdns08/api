import bcrypt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Comment
from schemas import CommentCreate, CommentResponse, CommentDelete

router = APIRouter(prefix="/posts", tags=["comments"])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _build_response(comment: Comment, replies: list[Comment]) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        post_slug=comment.post_slug,
        nickname=comment.nickname,
        content=comment.content,
        created_at=comment.created_at,
        parent_id=comment.parent_id,
        replies=[
            CommentResponse(
                id=r.id,
                post_slug=r.post_slug,
                nickname=r.nickname,
                content=r.content,
                created_at=r.created_at,
                parent_id=r.parent_id,
                replies=[],
            )
            for r in replies
        ],
    )


@router.get("/{slug:path}/comments", response_model=list[CommentResponse])
def get_comments(slug: str, db: Session = Depends(get_db)):
    """특정 포스트의 댓글 목록 조회 (대댓글 포함 중첩 구조)"""
    all_comments = (
        db.query(Comment)
        .filter(Comment.post_slug == slug)
        .order_by(Comment.created_at.asc())
        .all()
    )

    replies_map: dict[int, list[Comment]] = {}
    top_level: list[Comment] = []

    for c in all_comments:
        if c.parent_id is None:
            top_level.append(c)
            replies_map[c.id] = []
        else:
            replies_map.setdefault(c.parent_id, []).append(c)

    return [_build_response(c, replies_map.get(c.id, [])) for c in top_level]


@router.post("/{slug:path}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(slug: str, body: CommentCreate, db: Session = Depends(get_db)):
    """댓글/대댓글 작성"""
    if body.parent_id is not None:
        parent = db.query(Comment).filter(
            Comment.id == body.parent_id,
            Comment.post_slug == slug,
            Comment.parent_id == None,  # noqa: E711  대댓글의 대댓글 방지
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="원댓글을 찾을 수 없습니다.")

    comment = Comment(
        post_slug=slug,
        nickname=body.nickname,
        password_hash=_hash_password(body.password),
        content=body.content,
        parent_id=body.parent_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _build_response(comment, [])


@router.delete("/{slug:path}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    slug: str,
    comment_id: int,
    body: CommentDelete,
    db: Session = Depends(get_db),
):
    """비밀번호 확인 후 댓글 삭제 (대댓글도 함께 삭제)"""
    comment = (
        db.query(Comment)
        .filter(Comment.id == comment_id, Comment.post_slug == slug)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")

    if not _verify_password(body.password, comment.password_hash):
        raise HTTPException(status_code=403, detail="비밀번호가 올바르지 않습니다.")

    # 원댓글이면 대댓글도 함께 삭제
    if comment.parent_id is None:
        db.query(Comment).filter(Comment.parent_id == comment_id).delete()

    db.delete(comment)
    db.commit()
