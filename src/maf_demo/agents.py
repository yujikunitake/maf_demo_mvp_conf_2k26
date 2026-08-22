"""Agente coordenador de triagem + especialistas por documento do manual.

Desenho: o coordenador (gpt-5-mini, com tool-calling real) decide quais especialistas
consultar para cada incidente. Cada especialista é escopado em UM documento do manual —
o retrieval é determinístico em código (sempre roda, filtrado por `source`), e o modelo
só interpreta o contexto já injetado.

Nota: os especialistas não usam tool-calling interno de propósito — o retrieval de cada um
é sempre o mesmo (buscar no seu documento), então não há decisão nenhuma a delegar pro modelo
ali; só o coordenador precisa decidir algo, e só ele usa tools.

Nota 2: testamos usar Phi-4-mini-instruct (CHAT_DEPLOYMENT_ALT) nos especialistas pra ganhar
custo/latência, mas esse deployment (a) rejeita requisições com `tools` via Responses API
(erro 400) e (b) travou por >90s sem responder em teste isolado, mesmo sem tools — não é
confiável o bastante pra demo ao vivo. Os especialistas também rodam em gpt-5-mini.

Nota 3: o recurso Foundry (tier gratuito/estudante) trava (sem erro, sem timeout) quando recebe
muitas chamadas concorrentes ao gpt-5-mini — testado e reproduzido com 4 chamadas simultâneas.
Por isso as chamadas aos especialistas passam por um semáforo (`_LLM_CONCURRENCY`) limitando
quantas rodam ao mesmo tempo, com timeout por chamada pra falhar rápido em vez de travar a demo.
"""

import asyncio
from dataclasses import dataclass

from agent_framework import Agent, FunctionTool, tool
from agent_framework.foundry import FoundryChatClient, FoundryChatOptions
from azure.identity import AzureCliCredential

from maf_demo.config import load_settings
from maf_demo.prompts import load_prompt
from maf_demo.search_client import aretrieve

settings = load_settings()

# Limite de chamadas concorrentes ao Foundry (ver Nota 3 acima) e timeout de segurança
# por chamada de especialista, pra um travamento não derrubar a demo inteira.
_LLM_CONCURRENCY = asyncio.Semaphore(2)
_SPECIALIST_TIMEOUT_SECONDS = 45

# Uma única credencial compartilhada por todos os clients (coordenador + 5 especialistas).
# `AzureCliCredential` cacheia o token por instância — usar uma por client (6 no total)
# significa até 6 chamadas redundantes a `az account get-access-token` (~1,6s cada, medido)
# em vez de reaproveitar o mesmo token.
_CREDENTIAL = AzureCliCredential()


@dataclass(frozen=True)
class Specialist:
    doc_file: str
    tool_name: str
    tool_description: str
    prompt_name: str


SPECIALISTS = [
    Specialist(
        doc_file="01-runbook-triagem-incidentes.md",
        tool_name="consultar_runbook",
        tool_description="Regras de escalonamento por percentual de falha e exceções de horário/sazonalidade.",
        prompt_name="specialist_runbook",
    ),
    Specialist(
        doc_file="02-catalogo-sistemas-criticos.md",
        tool_name="consultar_catalogo_sistemas",
        tool_description="Quais sistemas existem, seus tiers e o que uma falha total representa.",
        prompt_name="specialist_catalogo",
    ),
    Specialist(
        doc_file="03-manual-escalonamento-plantao.md",
        tool_name="consultar_escalonamento",
        tool_description="Para quem escalar e sob quais critérios/prazos.",
        prompt_name="specialist_escalonamento",
    ),
    Specialist(
        doc_file="04-postmortems-incidentes-anteriores.md",
        tool_name="consultar_postmortems",
        tool_description="Precedentes históricos parecidos e causa raiz real registrada.",
        prompt_name="specialist_postmortems",
    ),
    Specialist(
        doc_file="05-guia-decisao-casos-limite.md",
        tool_name="consultar_casos_limite",
        tool_description="Desambiguação quando o sintoma é confuso ou não bate com regra óbvia.",
        prompt_name="specialist_casos_limite",
    ),
]


def _build_foundry_client(model: str) -> FoundryChatClient:
    return FoundryChatClient(
        project_endpoint=settings.foundry_endpoint,
        model=model,
        credential=_CREDENTIAL,
    )


def _build_specialist_tool(spec: Specialist) -> FunctionTool:
    client = _build_foundry_client(settings.chat_deployment)
    agent = client.as_agent(
        name=f"specialist-{spec.doc_file}",
        instructions=load_prompt(spec.prompt_name),
    )

    async def run_specialist(pergunta: str) -> str:
        chunks = await aretrieve(pergunta, top_k=5, source=spec.doc_file)
        if not chunks:
            return "Nenhum trecho relevante encontrado neste documento."

        context = "\n\n".join(f"[{c.source} — {c.section_title}]\n{c.content}" for c in chunks)
        message = f"Pergunta: {pergunta}\n\nContexto:\n{context}"

        async with _LLM_CONCURRENCY:
            try:
                response = await asyncio.wait_for(
                    agent.run(message, options={"reasoning": {"effort": "low"}}),
                    timeout=_SPECIALIST_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                return f"[{spec.tool_name} não respondeu a tempo — ignore esta fonte.]"
            except Exception as e:
                # Cobre, entre outros, o filtro de conteúdo/jailbreak do Azure OpenAI: a lib
                # agent_framework_openai quebra com um ValueError ao tentar montar a exceção
                # própria (`'ContentFiltered' is not a valid ContentFilterCodes`), então captura
                # genérico aqui em vez de depender do tipo de exceção "certo".
                return f"[{spec.tool_name} falhou ({e}) — ignore esta fonte.]"

        return str(response)

    return tool(run_specialist, name=spec.tool_name, description=spec.tool_description)


def build_coordinator_agent() -> Agent[FoundryChatOptions]:
    specialist_tools = [_build_specialist_tool(spec) for spec in SPECIALISTS]

    client = _build_foundry_client(settings.chat_deployment)
    return client.as_agent(
        name="NimbusFlowCoordinator",
        instructions=load_prompt("triage"),
        tools=specialist_tools,
    )
