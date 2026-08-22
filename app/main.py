import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from maf_demo.agents import build_coordinator_agent

console = Console()

SEVERITY_STYLE = {
    "SEV-1": "bold red",
    "SEV-2": "bold yellow",
    "SEV-3": "bold green",
}
VALID_SEVERITIES = {*SEVERITY_STYLE, "indeterminado"}


def parse_response(text: str) -> dict[str, Any] | None:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def print_banner() -> None:
    console.print(
        Panel.fit(
            "[bold]Assistente de triagem NimbusFlow[/bold]\n"
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

    if severity not in VALID_SEVERITIES:
        console.print(f"[dim][AVISO] Severidade desconhecida ({severity})[/dim]")


async def main() -> None:
    agent = build_coordinator_agent()
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

        try:
            with console.status("[dim]Coordenador consultando especialistas...[/dim]", spinner="dots"):
                response = await asyncio.wait_for(
                    agent.run(question, session=session, options={"reasoning": {"effort": "low"}}),
                    timeout=90,
                )
        except asyncio.TimeoutError:
            console.print(
                Panel(
                    "O coordenador demorou mais que o esperado (>90s) — provavelmente o recurso Azure "
                    "está sobrecarregado no momento. Tenta de novo em alguns segundos.",
                    title="[bold red]Timeout[/bold red]",
                    border_style="red",
                )
            )
            continue
        except Exception as e:
            # Cobre, entre outros, o filtro de conteúdo/jailbreak do Azure OpenAI: a lib
            # agent_framework_openai quebra com um ValueError ao montar a exceção própria
            # em vez de propagar algo específico e catável — captura genérico aqui pra não
            # derrubar o REPL no meio de uma demo.
            console.print(
                Panel(
                    f"A pergunta não pôde ser processada ({e}). Isso pode ser o filtro de "
                    "conteúdo do Azure (ex.: tentativa de jailbreak) ou um erro transitório. "
                    "Tenta reformular a pergunta.",
                    title="[bold red]Erro[/bold red]",
                    border_style="red",
                )
            )
            continue

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
