from typing import cast

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Condition,
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from src.application.ai.ports import VectorFilter, VectorSearchResult


def _build_filter(query_filter: VectorFilter | None) -> Filter | None:
    if query_filter is None:
        return None
    conditions: list[Condition] = []
    for key, value in query_filter.equals.items():
        match_value = cast("bool | int | str", value)
        conditions.append(FieldCondition(key=key, match=MatchValue(value=match_value)))
    for key, value in query_filter.gte.items():
        conditions.append(FieldCondition(key=key, range=Range(gte=value)))
    for key, value in query_filter.lte.items():
        conditions.append(FieldCondition(key=key, range=Range(lte=value)))
    if not conditions:
        return None
    return Filter(must=conditions)


class QdrantVectorStore:
    def __init__(self, url: str) -> None:
        self._client = QdrantClient(url=url)
        self._known_collections: set[str] = set()

    def ensure_collection(self, collection: str, vector_size: int) -> None:
        if collection in self._known_collections:
            return
        if not self._client.collection_exists(collection):
            self._client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        self._known_collections.add(collection)

    def upsert(
        self, collection: str, point_id: str, vector: list[float], payload: dict[str, object]
    ) -> None:
        self._client.upsert(
            collection_name=collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    def delete(self, collection: str, point_id: str) -> None:
        self._client.delete(collection_name=collection, points_selector=[point_id])

    def get_vector(self, collection: str, point_id: str) -> list[float] | None:
        points = self._client.retrieve(
            collection_name=collection, ids=[point_id], with_vectors=True
        )
        if not points:
            return None
        vector = points[0].vector
        if isinstance(vector, list) and (not vector or isinstance(vector[0], float)):
            return cast("list[float]", vector)
        return None

    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int,
        query_filter: VectorFilter | None = None,
    ) -> list[VectorSearchResult]:
        hits = self._client.query_points(
            collection_name=collection,
            query=query_vector,
            query_filter=_build_filter(query_filter),
            limit=limit,
        ).points
        return [
            VectorSearchResult(point_id=str(hit.id), score=hit.score, payload=hit.payload or {})
            for hit in hits
        ]
