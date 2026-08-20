import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import requests
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient, FoundryChatOptions
from azure.identity import AzureCliCredential
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from maf_demo.config import load_settings
from maf_demo.prompts import load_prompt
from maf_demo.search_client import retrieve

settings = load_settings()
console = Console()

SEVERITY_STYLE = {
    "SEV-1": "bold red",
    "SEV-2": "bold yellow",
    "SEV-3": "bold green",
}
SEVERITY_LED_COLOR = {"SEV-1": "red", "SEV-2": "yellow", "SEV-3": "green"}
INDETERMINADO = "indeterminado"
LED_SEVERITIES = {*SEVERITY_LED_COLOR, INDETERMINADO}


def query_manual(questions: str) -> str:
    chunks = retrieve(questions, top_k=5)
    return "\n\n".join(f"[Source: {c.source} — {c.section_title}]\n{c.content}" for c in chunks)


def trigger_led(severity: str) -> None:
    if severity == INDETERMINADO:
        swatch = "".join(f"[on {c}]  [/on {c}]" for c in SEVERITY_LED_COLOR.values())
        label = "todos os LEDs (severidade indeterminada)"
    else:
        color = SEVERITY_LED_COLOR[severity]
        swatch = f"[on {color}]   [/on {color}]"
        label = color

    if not settings.esp32_host:
        console.print(f"  {swatch} [dim]LED simulado (ESP32_HOST não configurado) → {label}[/dim]")
        return

    try:
        response = requests.get(f"http://{settings.esp32_host}/severity/{severity}", timeout=3)
        response.raise_for_status()
        console.print(f"  {swatch} [dim]LED físico acionado em {settings.esp32_host} → {label}[/dim]")
    except requests.RequestException as e:
        console.print(f"  [bold red][ERRO][/bold red] Falha ao acionar LED no ESP32 ({settings.esp32_host}): {e}")


def parse_response(text: str) -> dict[str, Any] | None:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def build_agent() -> Agent[FoundryChatOptions]:
    client = FoundryChatClient(
        project_endpoint=settings.foundry_endpoint,
        model=settings.chat_deployment,
        credential=AzureCliCredential(),
    )

    return client.as_agent(
        name="NimbusFlowTriage",
        instructions=load_prompt("triage"),
        tools=[query_manual],
    )


def print_banner() -> None:
    if settings.esp32_host:
        mode = f"[bold green][LED FÍSICO][/bold green] ESP32 em [cyan]{settings.esp32_host}[/cyan]"
    else:
        mode = "[bold yellow][LED SIMULADO][/bold yellow] nenhum ESP32 configurado (ESP32_HOST)"

    console.print(
        Panel.fit(
            "[bold]Assistente de triagem NimbusFlow[/bold]\n"
            f"{mode}\n"
            "[dim]Descreva o incidente e pressione Enter (Ctrl+C para sair)[/dim]",
            border_style="cyan",
        )
    )


def print_result(data: dict[str, Any]) -> None:
    severity = data.get("severity", "")
    style = SEVERITY_STYLE.get(severity, "bold white")
    border = style.split()[-1] if severity in SEVERITY_STYLE else "white"

    body = Text()
    body.append("Justificativa: ", style="bold")
    body.append(f"{data.get('justification', '—')}\n\n")

    if data.get("recommended_action"):
        body.append("Ação recomendada: ", style="bold")
        body.append(f"{data.get('recommended_action')}\n\n")

    evidences = data.get("evidences", [])
    if evidences:
        body.append("Evidências:\n", style="bold")
        for ev in evidences:
            body.append(f"  • {ev.get('source')} — ", style="dim")
            body.append(f"{ev.get('snippet')}\n")

    console.print(
        Panel(
            body,
            title=f"[{style}]SEVERIDADE: {severity or 'DESCONHECIDA'}[/{style}]",
            title_align="left",
            border_style=border,
        )
    )

    if severity in LED_SEVERITIES:
        trigger_led(severity)
    else:
        console.print(f"[dim][AVISO] Severidade desconhecida ({severity}) — LED não acionado[/dim]")


async def main() -> None:
    agent = build_agent()
    session = agent.create_session()

    print_banner()

    while True:
        try:
            question = console.input("\n[bold cyan]>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Encerrando...[/dim]")
            break

        if not question:
            continue

        with console.status("[dim]Consultando agente...[/dim]", spinner="dots"):
            response = await agent.run(question, session=session, options={"reasoning": {"effort": "low"}})

        data = parse_response(str(response))

        if data is None:
            console.print(
                Panel(str(response), title="[bold red]Resposta inválida (não é JSON)[/bold red]", border_style="red")
            )
            continue

        print_result(data)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[dim]Encerrando...[/dim]")
