import asyncio
import re
import sys
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from maf_demo.agents import build_coordinator_agent

console = Console()

SEVERITY_STYLE = {
    "SEV-1": "bold red",
    "SEV-2": "bold yellow",
    "SEV-3": "bold green",
}
VALID_SEVERITIES = {*SEVERITY_STYLE, "indeterminado"}

# Coordenador responde em texto simples (não JSON): legível cru tanto no terminal
# quanto no chat do DevUI. Só a severidade (1ª linha) é extraída via regex.
SEVERITY_LINE_RE = re.compile(r"^SEVERIDADE:\s*(SEV-1|SEV-2|SEV-3|indeterminado)\s*$", re.MULTILINE)
LABEL_LINE_RE = re.compile(r"^(Justificativa|Ação recomendada|Evidências):\s?(.*)$")


def extract_severity(text: str) -> str | None:
    match = SEVERITY_LINE_RE.search(text)
    return match.group(1) if match else None


def format_body(text: str) -> str:
    lines = []
    for line in text.strip().splitlines():
        if line.startswith("SEVERIDADE:"):
            continue  # já vira o título do painel, não repete no corpo
        label_match = LABEL_LINE_RE.match(line)
        if label_match:
            label, rest = label_match.groups()
            lines.append(f"[bold]{label}:[/bold] {escape(rest)}" if rest else f"[bold]{label}:[/bold]")
        elif line.startswith("- "):
            lines.append(f"  [dim]•[/dim] {escape(line[2:])}")
        else:
            lines.append(escape(line))
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines)


async def run_with_progress(agent: Any, question: str, session: Any) -> Any:
    """Roda o coordenador em streaming, narrando cada chamada a especialista ao vivo em
    vez de um spinner parado. Não streama a síntese final token a token — só avisa quando
    ela começa.
    """
    call_names: dict[str, str] = {}
    call_start: dict[str, float] = {}
    synthesizing = False

    console.print("[dim]Coordenador pensando...[/dim]")

    stream = agent.run(question, session=session, options={"reasoning": {"effort": "low"}}, stream=True)
    async for update in stream:
        for c in update.contents:
            if c.type == "function_call" and c.call_id not in call_names:
                call_names[c.call_id] = c.name
                call_start[c.call_id] = time.time()
                console.print(f"[dim]  > {c.name}...[/dim]")
            elif c.type == "function_result":
                name = call_names.get(c.call_id, "especialista")
                elapsed = time.time() - call_start.get(c.call_id, time.time())
                console.print(f"[dim]  [OK] {name} respondeu ({elapsed:.1f}s)[/dim]")
            elif c.type == "text" and not synthesizing:
                synthesizing = True
                console.print("[dim]Sintetizando resposta final...[/dim]")

    return await stream.get_final_response()


def print_banner() -> None:
    console.print(
        Panel.fit(
            "[bold]Assistente de triagem NimbusFlow[/bold]\n"
            "[dim]Descreva o incidente e pressione Enter (Ctrl+C para sair)[/dim]",
            border_style="cyan",
        )
    )


def print_result(text: str) -> None:
    severity = extract_severity(text)
    style = SEVERITY_STYLE.get(severity, "bold white")
    border = style.split()[-1] if severity in SEVERITY_STYLE else "white"

    console.print(
        Panel(
            format_body(text),
            title=f"[{style}]SEVERIDADE: {severity or 'DESCONHECIDA'}[/{style}]",
            title_align="left",
            border_style=border,
        )
    )

    if severity not in VALID_SEVERITIES:
        console.print("[dim][AVISO] Severidade desconhecida ou ausente na resposta[/dim]")


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
            response = await asyncio.wait_for(
                run_with_progress(agent, question, session),
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
            # Filtro de conteúdo do Azure: a lib quebra com ValueError em vez de propagar
            # algo catável — captura genérico pra não derrubar o REPL no meio da demo.
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

        text = str(response)

        if extract_severity(text) is None:
            console.print(
                Panel(
                    escape(text),
                    title="[bold red]Resposta sem severidade identificável[/bold red]",
                    border_style="red",
                )
            )
            continue

        print_result(text)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[dim]Encerrando...[/dim]")
