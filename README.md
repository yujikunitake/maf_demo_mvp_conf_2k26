# NimbusFlow — RAG com MAF

> Repositório de apoio da palestra **"RAG com MAF"**, apresentada por **Yuji Kunitake** na
> **MVP CONF Curitiba 2026**. Aqui está o código-fonte completo de tudo o que é mostrado ao
> vivo no palco.

## Sobre a talk

A pergunta da palestra é: **RAG "na mão" resolve, mas em que ponto vale a pena trocar um
pipeline hardcoded por um agente que decide sozinho quando e o quê buscar?** Para responder,
o repo constrói o mesmo problema em camadas crescentes de autonomia, usando o
[Microsoft Agent Framework (MAF)](https://github.com/microsoft/agent-framework):

| Camada | Onde está | O que muda |
|---|---|---|
| 1. Baseline sem RAG | `notebooks/02_generation.ipynb` | Pergunta direto pro modelo: sem contexto do manual, resposta genérica. |
| 2. RAG na mão | `notebooks/03_rag.ipynb` | Busca + contexto colado manualmente no prompt, já resolve, mas cada passo é hardcoded em Python. |
| 3. RAG como tool de um agente | *(substituído pela camada 4, não existe mais como script isolado)* | O agente decide *se* e *quando* chama a busca — function-calling nativo do MAF. |
| 4. Coordenador + especialistas | `app/main.py`, `src/maf_demo/agents.py` | Um agente orquestra outros 5 agentes, cada um restrito a um documento do manual, e sintetiza a decisão final. |
| 5. DevUI ao vivo | `app/devui_server.py` | O mesmo agente da camada 4, com trace de execução visual, de graça, sem infra extra. |

O cenário fictício: a **NimbusFlow**, um e-commerce, tem um manual interno de triagem de
incidentes (`data/manual/`, 5 documentos) e o objetivo é montar um assistente que leia um
relato de incidente em linguagem natural e devolva a severidade certa (`SEV-1` / `SEV-2` /
`SEV-3` / `indeterminado`), sempre citando em qual regra do manual se baseou.

## Visão geral da arquitetura (camada 4 — o coordenador)

```
pergunta do usuário
      │
      ▼
┌─────────────────────────┐
│  Coordenador             │  prompts/triage.yaml
│  (NimbusFlowCoordinator) │  decide QUAIS especialistas chamar
└─────────────────────────┘
      │  function-calling (0 a 5 tools)
      ├─── consultar_runbook            → data/manual/01-runbook-triagem-incidentes.md
      ├─── consultar_catalogo_sistemas  → data/manual/02-catalogo-sistemas-criticos.md
      ├─── consultar_escalonamento      → data/manual/03-manual-escalonamento-plantao.md
      ├─── consultar_postmortems        → data/manual/04-postmortems-incidentes-anteriores.md
      └─── consultar_casos_limite       → data/manual/05-guia-decisao-casos-limite.md
      │
      ▼
síntese final em texto simples:
SEVERIDADE / Justificativa / Ação recomendada / Evidências
```

- **Ingestão** (`scripts/build_index.py`): os 5 documentos de `data/manual/` são divididos em
  chunks markdown-aware (`chonkie.RecursiveChunker`, ~400 tokens, tokenizer `cl100k_base`),
  embeddados (Azure OpenAI, deployment de embedding) e indexados no Azure AI Search com busca
  híbrida (vetorial HNSW/cosine + semântica).
- **Coordenador** (`src/maf_demo/agents.py::build_coordinator_agent`): um agente Foundry
  instruído pelo prompt `prompts/triage.yaml`. Ele **não tem acesso direto ao manual**, só
  decide quais dos 5 especialistas chamar e sintetiza as respostas deles.
- **Especialistas**: cada um é outro agente Foundry, exposto ao coordenador como uma
  `FunctionTool`, instruído por `prompts/specialist_*.yaml` e restrito a um único documento,
  a busca (`aretrieve`) é sempre filtrada por `source`. Cada chamada de especialista tem timeout
  de 45s e a concorrência de LLM entre eles é limitada por um semáforo (2 simultâneas).
- **Interfaces**:
  - `app/main.py`, REPL de terminal (rich), narra as chamadas de tool ao vivo via streaming,
    timeout de 90s por pergunta, extrai a severidade da 1ª linha da resposta por regex.
  - `app/devui_server.py`, sobe o [DevUI](https://github.com/microsoft/agent-framework) em
    `http://localhost:8080` com trace de execução ao vivo (instrumentação habilitada).

## Estrutura de pastas

```
app/               REPL de terminal e servidor DevUI
data/manual/        os 5 documentos-fonte (a "verdade" do sistema)
notebooks/           camadas 1 e 2 da talk: baseline sem RAG e RAG na mão
prompts/             prompt do coordenador + prompt de cada especialista (YAML)
scripts/build_index.py   ingestão: chunking + embeddings + upload pro índice
src/maf_demo/
  agents.py          monta o coordenador e os 5 agentes-especialista (camada 4)
  config.py          carrega variáveis de ambiente (.env)
  foundry_client.py  chamada simples de chat, sem agente (usado nos notebooks)
  prompts.py         helper pra ler prompts/*.yaml
  search_client.py   busca híbrida (retrieve/aretrieve) no Azure AI Search
```

## Pré-requisitos

- **Python 3.12+** e [uv](https://docs.astral.sh/uv/)
- **Azure CLI logado** (`az login`) — a credencial (`AzureCliCredential`) é compartilhada por
  todos os clients do Foundry para autenticar sem precisar de chave de API do modelo
- Um projeto **Azure AI Foundry** com dois deployments:
  - um de chat (ex.: `gpt-5-mini`)
  - um de embedding (ex.: `text-embedding-3-small`, 1536 dimensões)
- Um serviço **Azure AI Search** com um índice vetorial+semântico configurado (ou criado pelo
  próprio `scripts/build_index.py`, ver abaixo)

Sem conta Azure? Veja "Caminhos alternativos para infra própria" mais abaixo: os três pontos
de acoplamento são isolados e trocáveis.

## Como rodar

```bash
# 1. instalar dependências
uv sync

# 2. copiar e preencher as variáveis de ambiente
cp .env.example .env
# preencher: FOUNDRY_ENDPOINT, FOUNDRY_API_KEY, FOUNDRY_API_VERSION,
#            SEARCH_ENDPOINT, SEARCH_API_KEY, SEARCH_INDEX_NAME,
#            VECTOR_PROFILE_NAME, HNSW_CONFIG_NAME, SEMANTIC_CONFIG_NAME,
#            EMBEDDING_DEPLOYMENT, EMBEDDING_DIMENSIONS, CHAT_DEPLOYMENT, CHAT_DEPLOYMENT_ALT

# 3. logar no Azure (necessário pro FoundryChatClient)
az login

# 4. popular o índice de busca (uma vez, ou sempre que data/manual/ mudar)
uv run scripts/build_index.py

# 5a. rodar no terminal (camada 4)
uv run app/main.py

# 5b. ou subir o DevUI (camada 5 — http://localhost:8080, token "nimbusflow-demo")
uv run app/devui_server.py
```

## As 10 perguntas de teste

A palestra tem um bloco de "bastidores de confiabilidade": LLM é não-determinístico, então uma
resposta certa numa única execução não prova nada — só rodando a mesma pergunta várias vezes,
em sessões novas, dá pra falar de taxa de acerto de verdade. Estas são as 10 perguntas usadas
nessa bateria (5 execuções cada, sessão nova por execução):

1. login caiu, ninguém consegue entrar no sistema
2. 25% dos pagamentos com cartão de crédito estão sendo recusados
3. checkout lento durante a Black Friday, é grave mesmo sendo pouco volume?
4. qual o protocolo pra convocar a diretoria pra dentro do war room?
5. um estagiário viu o número completo de um cartão de cliente aparecendo num log interno
6. o sistema de recomendações caiu inteiro, isso é grave?
7. durante um lançamento vendemos mais unidades do que tínhamos em estoque
8. um cliente empresarial grande está reclamando de lentidão, mas o volume geral de relatos é baixo
9. a fila de emails de marketing está uns 10 minutos atrasada, é urgente?
10. timeout no serviço de recomendações durante uma campanha grande, o checkout está ficando lento por causa disso

Elas cobrem os casos "de manual" (regras diretas do runbook), exceções (sazonalidade, método de
pagamento predominante, vazamento de dados) e casos-limite propositalmente ambíguos (perguntas
4 e 8), pra observar tanto acerto quanto variância de julgamento entre execuções.

## Caminhos alternativos para infra própria (sem depender do Azure)

O projeto está acoplado ao Azure em três pontos independentes, cada um pode ser trocado sem
mexer nos outros, porque o Agent Framework abstrai o "client de chat" e o resto do código só
depende da interface `Chunk` / `retrieve` / `aretrieve`:

| Peça | Implementação atual | Alternativas |
|---|---|---|
| **Client de chat** (coordenador + especialistas) | `FoundryChatClient` (`agent_framework.foundry`), autenticado via `AzureCliCredential` — ver `_build_foundry_client` em `src/maf_demo/agents.py` | O Agent Framework já traz `agent_framework.openai.OpenAIChatClient` (qualquer endpoint compatível com a API da OpenAI — inclui servidores locais como **vLLM** ou **LM Studio**), `agent_framework.ollama` (**Ollama** local) e `agent_framework.anthropic` (Claude). A troca é local: `client.as_agent(...)` tem a mesma interface nos três, então `agents.py` muda só na função que constrói o client. |
| **Embeddings** | `AzureOpenAI().embeddings.create(...)` em `search_client.py` e `scripts/build_index.py` | Qualquer client compatível com a API de embeddings da OpenAI (Ollama expõe um endpoint compatível; ou um modelo local via `sentence-transformers`/`fastembed`). Só toca `_embed_query`/`aretrieve` e `embed_chunks`. |
| **Busca vetorial** | Azure AI Search (SDK `azure-search-documents`, HNSW + busca semântica) | Como o código usa o SDK do Azure diretamente (não uma abstração do framework), trocar por **Qdrant**, **Chroma**, **pgvector** ou **Weaviate** exige reescrever `search_client.py` e a criação/upload de índice em `scripts/build_index.py` — mas como o resto do sistema só conhece o dataclass `Chunk` e as funções `retrieve`/`aretrieve`, a superfície a reescrever é pequena e isolada. |
| **Autenticação** | `AzureCliCredential` compartilhada (evita repetir `az account get-access-token` por client) | Trocar por API key direta, managed identity, ou o mecanismo de auth do provider escolhido acima. |

O `app/devui_server.py` não é Azure-specific — `agent_framework.devui.serve()` funciona com
qualquer `Agent` do framework, então continua funcionando igual depois de qualquer uma dessas
trocas.

---

Dúvidas, sugestões ou quer bater um papo depois da talk? Abre uma issue ou chama o
[Yuji Kunitake](https://github.com/yujikunitake).
