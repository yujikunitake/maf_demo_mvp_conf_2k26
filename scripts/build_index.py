import sys
from pathlib import Path
from uuid import uuid4

import tiktoken
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from chonkie import RecursiveChunker
from openai import AzureOpenAI

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from maf_demo.config import load_settings

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "manual"
settings = load_settings()

def build_index(index_client: SearchIndexClient, index_name: str) -> None:

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.STRING, key=True),
        SearchableField(name="content", type=SearchFieldDataType.STRING),
        SimpleField(
            name="source", type=SearchFieldDataType.STRING, filterable=True, facetable=True
        ),
        SearchableField(name="section_title", type=SearchFieldDataType.STRING),
        SearchField(
            name="content_vector",
            type=f"Collection({SearchFieldDataType.SINGLE.value})",            searchable=True,
            vector_search_dimensions=settings.embedding_dimensions,
            vector_search_profile_name=settings.vector_profile_name,
        ),
    ]
 
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=settings.hnsw_config_name,
                parameters=HnswParameters(metric="cosine"),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=settings.vector_profile_name,
                algorithm_configuration_name=settings.hnsw_config_name,
            )
        ],
    )
 
    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=settings.semantic_config_name,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="section_title"),
                    content_fields=[SemanticField(field_name="content")],
                ),
            )
        ]
    )
 
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )
 
    index_client.create_or_update_index(index)
    print(f"Index '{index_name}' created/updated.")

def generate_chunks(file_path: Path) -> list[dict]:
    tokenizer = tiktoken.get_encoding("cl100k_base")

    chunker = RecursiveChunker.from_recipe(
        "markdown", chunk_size=400, tokenizer=tokenizer  # type: ignore[arg-type]
    )
    text = file_path.read_text(encoding="utf-8")
    chunks = chunker.chunk(text)

    result = []
    for chunk in chunks:
        first_line = chunk.text.strip().split("\n", 1)[0].lstrip("#").strip()

        result.append(
            {
                "id": str(uuid4()),
                "content": chunk.text,
                "source": file_path.name,
                "section_title": first_line[:200],
            }
        )

    return result

def embed_chunks(client: AzureOpenAI, deployment: str, chunks: list[dict]) -> None:
    texts = [c["content"] for c in chunks]
    response = client.embeddings.create(model=deployment, input=texts)

    for chunk, data in zip(chunks, response.data):
        chunk["content_vector"] = data.embedding


def main() -> None:
    credential = AzureKeyCredential(settings.search_api_key)

    index_client = SearchIndexClient(settings.search_endpoint, credential)
    build_index(index_client, settings.search_index_name)
    search_client = SearchClient(settings.search_endpoint, settings.search_index_name, credential)
    embedding_client = AzureOpenAI(
        azure_endpoint=settings.foundry_endpoint,
        api_version=settings.foundry_api_version,
        api_key=settings.foundry_api_key,
    )

    files = sorted(DATA_DIR.glob("*.md"))
    if not files:
        raise SystemExit(f"No markdown files found in {DATA_DIR}")

    total_chunks = 0
    for file_path in files:
        print(f"Processing file: {file_path.name}")
        chunks = generate_chunks(file_path)
        embed_chunks(embedding_client, settings.embedding_deployment, chunks)
        search_client.upload_documents(documents=chunks)
        total_chunks += len(chunks)
        print(f"Uploaded {len(chunks)} chunks from {file_path.name}")

if __name__ == "__main__":
    main()