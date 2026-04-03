import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import PostGraphCache
from schemas import GraphBuildRequest, GraphEdge, GraphNode, GraphResponse

router = APIRouter(prefix="/posts/graph", tags=["knowledge-graph"])


def _compute_graph(posts: list) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes = [
        GraphNode(
            id=p.slug,
            title=p.title,
            category=p.category,
            subcategory=p.subcategory,
            tags=p.tags,
            date=p.date,
        )
        for p in posts
    ]

    edges: list[GraphEdge] = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            w = 0.0
            if a.category and a.category == b.category:
                w += 0.4
            if a.subcategory and a.subcategory == b.subcategory:
                w += 0.6
            shared = set(a.tags) & set(b.tags)
            w += len(shared) * 0.5
            if w >= 0.4:
                edges.append(GraphEdge(source=a.id, target=b.id, weight=min(w, 2.0)))

    return nodes, edges


@router.post("/build", response_model=GraphResponse, summary="그래프 빌드 및 저장")
def build_and_store(req: GraphBuildRequest, db: Session = Depends(get_db)):
    nodes, edges = _compute_graph(req.posts)
    now = datetime.now(timezone.utc)

    nodes_json = json.dumps([n.model_dump() for n in nodes], ensure_ascii=False)
    edges_json = json.dumps([e.model_dump() for e in edges])

    cache = db.query(PostGraphCache).filter_by(id=1).first()
    if cache:
        cache.nodes_json = nodes_json
        cache.edges_json = edges_json
        cache.built_at = now
    else:
        cache = PostGraphCache(id=1, nodes_json=nodes_json, edges_json=edges_json, built_at=now)
        db.add(cache)
    db.commit()

    return GraphResponse(nodes=nodes, edges=edges, built_at=now)


@router.get("", response_model=GraphResponse, summary="저장된 그래프 조회")
def get_graph(db: Session = Depends(get_db)):
    cache = db.query(PostGraphCache).filter_by(id=1).first()
    if not cache:
        raise HTTPException(status_code=404, detail="그래프가 아직 빌드되지 않았습니다. POST /posts/graph/build를 먼저 호출하세요.")
    return GraphResponse(
        nodes=json.loads(cache.nodes_json),
        edges=json.loads(cache.edges_json),
        built_at=cache.built_at,
    )
