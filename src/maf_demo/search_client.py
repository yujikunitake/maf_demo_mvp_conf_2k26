from dataclasses import dataclass

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.aio import SearchClient as AsyncSearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AsyncAzureOpenAI, AzureOpenAI

from maf_demo.config import load_settings


@dataclass
class Chunk:
    content: str
    source: str
    section_title: str
    reranker_score: float


def _embed_query(client: AzureOpenAI, deployment: str, query: str) -> list[float]:
    response = client.embeddings.create(
        model=deployment,
        input=[query]
    )
    return response.data[0].embedding

def retrieve(query: str, top_k: int = 5, source: str | None = None) -> list[Chunk]:
    """Busca híbrida (vetorial + semântica) no manual; `source` filtra a um único arquivo."""
    settings = load_settings()

    embedding_client = AzureOpenAI(
        azure_endpoint=settings.foundry_endpoint,
        api_version=settings.foundry_api_version,
        api_key=settings.foundry_api_key
    )
    search_client = SearchClient(
        endpoint=settings.search_endpoint,
        index_name=settings.search_index_name,
        credential=AzureKeyCredential(settings.search_api_key)
    )

    vector_question = _embed_query(
        embedding_client,
        settings.embedding_deployment,
        query
    )
    vector_query = VectorizedQuery(
        vector=vector_question,
        k_nearest_neighbors=top_k,
        fields="content_vector"
    )
    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name=settings.semantic_config_name,
        top=top_k,
        select=["content", "source", "section_title"],
        filter=f"source eq '{source}'" if source else None
    )

    chunks = []
    for r in results:
        chunks.append(
            Chunk(
                content=r["content"],
                source=r["source"],
                section_title=r["section_title"],
                reranker_score=r.get("@search.rerankerScore") or r.get("@search.score", 0.0)
            )
        )
    return chunks


async def aretrieve(query: str, top_k: int = 5, source: str | None = None) -> list[Chunk]:
    """Igual a `retrieve`, mas assíncrona — usada onde buscas rodam em paralelo (especialistas)."""
    settings = load_settings()

    async with (
        AsyncAzureOpenAI(
            azure_endpoint=settings.foundry_endpoint,
            api_version=settings.foundry_api_version,
            api_key=settings.foundry_api_key,
        ) as embedding_client,
        AsyncSearchClient(
            endpoint=settings.search_endpoint,
            index_name=settings.search_index_name,
            credential=AzureKeyCredential(settings.search_api_key),
        ) as search_client,
    ):
        embedding_response = await embedding_client.embeddings.create(
            model=settings.embedding_deployment,
            input=[query],
        )
        vector_query = VectorizedQuery(
            vector=embedding_response.data[0].embedding,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )
        results = await search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            query_type="semantic",
            semantic_configuration_name=settings.semantic_config_name,
            top=top_k,
            select=["content", "source", "section_title"],
            filter=f"source eq '{source}'" if source else None,
        )

        return [
            Chunk(
                content=r["content"],
                source=r["source"],
                section_title=r["section_title"],
                reranker_score=r.get("@search.rerankerScore") or r.get("@search.score", 0.0),
            )
            async for r in results
        ]


if __name__ == "__main__":
    query = "cartão sendo recusado sem motivo aparente"
    for chunk in retrieve(query, top_k=5):
        print(f"[{chunk.reranker_score:.2f}] {chunk.source} — {chunk.section_title}")
        print(chunk.content[:200].replace("\n", " "))
        print()
