from datetime import datetime
from pydantic import BaseModel, field_validator


# ── Comments ──────────────────────────────────────────────

class CommentCreate(BaseModel):
    nickname: str
    password: str
    content: str
    parent_id: int | None = None

    @field_validator("nickname")
    @classmethod
    def nickname_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("닉네임을 입력해주세요.")
        if len(v) > 50:
            raise ValueError("닉네임은 50자 이하여야 합니다.")
        return v

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("비밀번호는 4자 이상이어야 합니다.")
        return v

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("댓글 내용을 입력해주세요.")
        if len(v) > 1000:
            raise ValueError("댓글은 1000자 이하여야 합니다.")
        return v


class CommentResponse(BaseModel):
    id: int
    post_slug: str
    nickname: str
    content: str
    created_at: datetime
    parent_id: int | None = None
    replies: list["CommentResponse"] = []

    model_config = {"from_attributes": True}


class CommentDelete(BaseModel):
    password: str


# ── Likes ──────────────────────────────────────────────────

class LikeToggle(BaseModel):
    client_id: str  # localStorage에 저장된 UUID

    @field_validator("client_id")
    @classmethod
    def valid_uuid(cls, v: str) -> str:
        import re
        pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        if not re.match(pattern, v, re.IGNORECASE):
            raise ValueError("유효하지 않은 client_id입니다.")
        return v


class LikeResponse(BaseModel):
    liked: bool
    count: int


# ── Reactions ───────────────────────────────────────────────

ALLOWED_EMOJIS = ["❤️", "👍", "😄", "🤔", "🚀", "🎉"]


class ReactionToggle(BaseModel):
    client_id: str
    emoji: str

    @field_validator("client_id")
    @classmethod
    def valid_uuid(cls, v: str) -> str:
        import re
        pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        if not re.match(pattern, v, re.IGNORECASE):
            raise ValueError("유효하지 않은 client_id입니다.")
        return v

    @field_validator("emoji")
    @classmethod
    def valid_emoji(cls, v: str) -> str:
        if v not in ALLOWED_EMOJIS:
            raise ValueError("허용되지 않은 이모지입니다.")
        return v


class ReactionCount(BaseModel):
    emoji: str
    count: int
    reacted: bool


class ReactionResponse(BaseModel):
    reactions: list[ReactionCount]


# ── Post Knowledge Graph ─────────────────────────────────────

class PostInput(BaseModel):
    slug: str
    title: str
    category: str
    subcategory: str | None = None
    tags: list[str] = []
    date: str


class GraphBuildRequest(BaseModel):
    posts: list[PostInput]


class GraphNode(BaseModel):
    id: str
    title: str
    category: str
    subcategory: str | None
    tags: list[str]
    date: str


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    built_at: datetime
