import sys

from dataclasses import dataclass

from openai import AzureOpenAI

from maf_demo.config import Settings, load_settings


@dataclass
class ChatResponse:
    text: str
    model: str


def _client(settings: Settings) -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=settings.foundry_endpoint,
        api_version=settings.foundry_api_version,
        api_key=settings.foundry_api_key
    )

def chat(prompt: str, deployment: str | None = None, system: str | None = None) -> ChatResponse:
    settings = load_settings()
    model = deployment or settings.chat_deployment

    messages = []

    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = _client(settings).chat.completions.create(
        model=model,
        messages=messages
    )

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("Model response contained no text content")

    return ChatResponse(
        text=content,
        model=model
    )

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else (
        "Um cliente reportou que o checkout está instável e 15% das tentativas de compra estão falhando. Que severidade isso deveria receber?"
    )
    resultado = chat(query)
    print(f"[{resultado.model}]")
    print(resultado.text)