"""
SkillForge AI — OpenSearch Client
Semantic vector search for skills, courses, and job postings.
"""

import logging
from typing import Any, Optional

from opensearchpy import AsyncOpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

from src.config import settings

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """
    Async OpenSearch client for vector similarity search.
    Used for semantic skills matching, course retrieval, and job matching.
    """

    def __init__(self):
        credentials = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region,
        ).get_credentials()

        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            settings.aws_default_region,
            "es",
            session_token=credentials.token,
        )

        self.client = AsyncOpenSearch(
            hosts=[{"host": self._parse_host(), "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30,
        )

    def _parse_host(self) -> str:
        """Extract hostname from OpenSearch endpoint URL."""
        endpoint = settings.opensearch_endpoint
        return endpoint.replace("https://", "").replace("http://", "").rstrip("/")

    async def ensure_index(self, index: str, mapping: dict) -> None:
        """Create OpenSearch index with KNN mapping if it doesn't exist."""
        exists = await self.client.indices.exists(index=index)
        if not exists:
            await self.client.indices.create(
                index=index,
                body={
                    "settings": {
                        "index": {
                            "knn": True,
                            "knn.algo_param.ef_search": 100,
                        }
                    },
                    "mappings": mapping,
                },
            )
            logger.info(f"Created OpenSearch index: {index}")

    async def index_document(
        self,
        index: str,
        doc_id: str,
        document: dict,
        embedding: list[float],
    ) -> None:
        """Index a document with its embedding vector."""
        await self.client.index(
            index=index,
            id=doc_id,
            body={**document, "embedding": embedding},
            refresh=True,
        )

    async def semantic_search(
        self,
        index: str,
        query_vector: list[float],
        filters: Optional[dict] = None,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Perform KNN semantic vector search with optional filters.

        Args:
            index: OpenSearch index name
            query_vector: Nova embedding vector for the query
            filters: Optional metadata filters
            top_k: Number of results to return

        Returns:
            List of matching documents with scores
        """
        knn_query: dict[str, Any] = {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": top_k,
                }
            }
        }

        # Add metadata filters if provided
        if filters:
            filter_clauses = []
            for key, value in filters.items():
                if isinstance(value, list):
                    filter_clauses.append({"terms": {key: value}})
                elif isinstance(value, dict) and "gte" in value:
                    filter_clauses.append({"range": {key: value}})
                elif key == "max_cost_usd":
                    filter_clauses.append({"range": {"cost_usd": {"lte": value}}})
                else:
                    filter_clauses.append({"term": {key: value}})

            if filter_clauses:
                knn_query = {
                    "bool": {
                        "must": [knn_query],
                        "filter": filter_clauses,
                    }
                }

        try:
            response = await self.client.search(
                index=index,
                body={
                    "size": top_k,
                    "query": knn_query,
                    "_source": {"excludes": ["embedding"]},
                },
            )

            return [
                {**hit["_source"], "_score": hit["_score"], "_id": hit["_id"]}
                for hit in response["hits"]["hits"]
            ]
        except Exception as e:
            logger.warning(f"OpenSearch query failed on index {index}: {e}")
            return []

    async def get_document(self, index: str, doc_id: str) -> Optional[dict]:
        """Retrieve a specific document by ID."""
        try:
            response = await self.client.get(index=index, id=doc_id)
            return response.get("_source")
        except Exception:
            return None

    async def bulk_index(
        self,
        index: str,
        documents: list[dict],
        embeddings: list[list[float]],
    ) -> int:
        """Bulk index a batch of documents with their embeddings."""
        actions = []
        for doc, embedding in zip(documents, embeddings):
            actions.append({"index": {"_index": index, "_id": doc.get("id", "")}})
            actions.append({**doc, "embedding": embedding})

        if not actions:
            return 0

        response = await self.client.bulk(body=actions, refresh=True)
        errors = [item for item in response["items"] if "error" in item.get("index", {})]
        if errors:
            logger.warning(f"Bulk index had {len(errors)} errors in {index}")

        return len(documents) - len(errors)

    async def close(self):
        await self.client.close()