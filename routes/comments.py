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


@router.get("/{slug:path}/comments", response_model=list[CommentResponse])
def get_comments(slug: str, db: Session = Depends(get_db)):
    """특정 포스트의 댓글 목록 조회"""
    return (
        db.query(Comment)
        .filter(Comment.post_slug == slug)
        .order_by(Comment.created_at.asc())
        .all()
    )


@router.post("/{slug:path}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(slug: str, body: CommentCreate, db: Session = Depends(get_db)):
    """댓글 작성"""
    comment = Comment(
        post_slug=slug,
        nickname=body.nickname,
        password_hash=_hash_password(body.password),
        content=body.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/{slug:path}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    slug: str,
    comment_id: int,
    body: CommentDelete,
    db: Session = Depends(get_db),
):
    """비밀번호 확인 후 댓글 삭제"""
    comment = (
        db.query(Comment)
        .filter(Comment.id == comment_id, Comment.post_slug == slug)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")

    if not _verify_password(body.password, comment.password_hash):
        raise HTTPException(status_code=403, detail="비밀번호가 올바르지 않습니다.")

    db.delete(comment)
    db.commit()
