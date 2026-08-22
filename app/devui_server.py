"""Sobe o DevUI (Microsoft Agent Framework) com o coordenador de triagem NimbusFlow.

Uso: uv run app/devui_server.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from agent_framework.devui import serve  # noqa: E402

from maf_demo.agents import build_coordinator_agent  # noqa: E402

# Token fixo pra não caçar o token auto-gerado nos logs durante a apresentação;
# DevUI só aceita bind em loopback sem token, então não é exposição de rede.
DEVUI_TOKEN = "nimbusflow-demo"


def main() -> None:
    agent = build_coordinator_agent()
    print(f"Subindo DevUI em http://localhost:8080 — abrindo o navegador... (token: {DEVUI_TOKEN})")
    serve(
        entities=[agent],
        port=8080,
        auto_open=True,
        instrumentation_enabled=True,
        auth_token=DEVUI_TOKEN,
    )


if __name__ == "__main__":
    main()
