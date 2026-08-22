import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()



def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable not set: {name}. Please set it in the .env file")
    return value

@dataclass(frozen=True)
class Settings:
    foundry_endpoint: str
    foundry_api_key: str
    foundry_api_version: str
    embedding_deployment: str
    chat_deployment: str
    chat_deployment_alt: str
    embedding_dimensions: int
    search_endpoint: str
    search_api_key: str
    search_index_name: str
    vector_profile_name: str
    hnsw_config_name: str
    semantic_config_name: str


def load_settings() -> Settings:
    return Settings(
        foundry_endpoint=_require("FOUNDRY_ENDPOINT"),
        foundry_api_key=_require("FOUNDRY_API_KEY"),
        foundry_api_version=_require("FOUNDRY_API_VERSION"),
        embedding_deployment=_require("EMBEDDING_DEPLOYMENT"),
        chat_deployment=_require("CHAT_DEPLOYMENT"),
        chat_deployment_alt=_require("CHAT_DEPLOYMENT_ALT"),
        embedding_dimensions=int(_require("EMBEDDING_DIMENSIONS")),
        search_endpoint=_require("SEARCH_ENDPOINT"),
        search_api_key=_require("SEARCH_API_KEY"),
        search_index_name=_require("SEARCH_INDEX_NAME"),
        vector_profile_name=_require("VECTOR_PROFILE_NAME"),
        hnsw_config_name=_require("HNSW_CONFIG_NAME"),
        semantic_config_name=_require("SEMANTIC_CONFIG_NAME"),
    )
