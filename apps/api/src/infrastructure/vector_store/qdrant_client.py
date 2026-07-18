from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


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
