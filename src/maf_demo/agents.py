import asyncio
from dataclasses import dataclass

from agent_framework import Agent, FunctionTool, tool
from agent_framework.foundry import FoundryChatClient, FoundryChatOptions
from azure.identity import AzureCliCredential

from maf_demo.config import load_settings
from maf_demo.prompts import load_prompt
from maf_demo.search_client import aretrieve

settings = load_settings()

_LLM_CONCURRENCY = asyncio.Semaphore(2)
_SPECIALIST_TIMEOUT_SECONDS = 45

# Credencial única compartilhada por todos os clients — evita repetir
# `az account get-access-token` (~1,6s) por client.
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
                # Filtro de conteúdo do Azure faz a lib agent_framework_openai quebrar com
                # ValueError em vez de propagar algo catável — captura genérico aqui.
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
