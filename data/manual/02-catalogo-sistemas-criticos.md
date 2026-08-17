# Catálogo de Sistemas Críticos — NimbusFlow

**Propósito:** dar contexto sobre o que cada sistema interno faz, pra quem está triando um incidente conseguir mapear a descrição de um problema (muitas vezes vaga, na fala de quem reporta) para o sistema técnico correto e seu nível de criticidade real.

## Tier 0 — Caminho crítico de compra

Sistemas cuja falha total impede diretamente uma venda de acontecer. Qualquer indisponibilidade completa aqui é, por definição, SEV-1.

**Auth Gateway** — responsável por login, criação de conta, recuperação de senha e emissão de tokens de sessão. Fica na frente de praticamente todo o resto: se ele cai, o cliente não consegue nem ver o próprio carrinho salvo, mesmo que todo o resto do sistema esteja saudável. Sintomas típicos de falha aqui incluem "não consigo entrar", "esqueci minha senha e o email de recuperação não chega", "fui deslogado no meio da compra sem motivo".

**Checkout Service** — orquestra o processo de finalização de compra: valida o carrinho, aplica cupons e descontos, calcula frete, e dispara a cobrança pro Payment Gateway. É o sistema com mais dependências internas de todo o catálogo, o que faz dele o ponto onde problemas de outros sistemas mais frequentemente aparecem primeiro, mesmo quando a causa raiz é externa a ele.

**Payment Gateway** — integração com as adquirentes de cartão e demais meios de pagamento. Processa a autorização e a captura da transação. Uma falha aqui pode se manifestar como "cartão recusado" mesmo quando o cartão do cliente está perfeitamente válido — esse é um dos sintomas mais enganosos do catálogo, porque a mensagem de erro que o cliente vê é idêntica à de um cartão realmente sem limite.

**Order Confirmation Service** — grava o pedido definitivamente após o pagamento ser aprovado, e dispara a nota fiscal e o email de confirmação. Uma falha isolada aqui é particularmente perigosa: o cliente pode ser cobrado com sucesso pelo Payment Gateway, mas o pedido nunca é registrado — o pior tipo de incidente do ponto de vista de confiança do cliente, mesmo afetando um volume pequeno de transações.

## Tier 1 — Suporte direto à conversão

Sistemas importantes para a experiência de compra, mas cuja indisponibilidade total não impede a venda de acontecer — só torna a jornada pior.

**Search Service** — busca de produtos por texto livre e filtros. Uma falha aqui empurra o cliente a navegar por categoria manualmente; irritante, mas não bloqueante.

**Recommendation Engine** — sugestões de produtos relacionados, "quem comprou isso também comprou aquilo", e personalização de vitrine. É o sistema mais mencionado erroneamente como "crítico" pelo próprio time de produto, porque tem impacto mensurável em receita ao longo de semanas — mas do ponto de vista de triagem de incidente, uma queda total dele nunca justifica, sozinha, mais que SEV-2.

**Inventory Service** — controla estoque em tempo real. Uma falha pode causar overselling (vender mais do que existe em estoque) ou, no sentido oposto, mostrar produtos como indisponíveis quando na verdade existe estoque — os dois sintomas parecem completamente diferentes na hora de reportar, mas têm a mesma causa raiz possível.

## Tier 2 — Suporte operacional e interno

Sistemas cuja falha não é percebida pelo cliente final em tempo real, mas afeta operação, comunicação ou times internos.

**Notification Service** — dispara emails e notificações push: confirmação de pedido, atualização de status de entrega, campanhas de marketing. Uma fila atrasada aqui é desconfortável mas raramente urgente — a única exceção relevante é quando o atraso afeta o email de recuperação de senha, que tecnicamente passa por esse serviço mas está semanticamente ligado ao Auth Gateway (Tier 0) para efeitos de triagem.

**Analytics Pipeline** — agrega dados de comportamento de navegação e compra para dashboards internos e relatórios de negócio. Uma falha aqui nunca afeta o cliente final diretamente; o pior cenário é perda de dados históricos, que só se qualifica como SEV-1 sob a regra de "risco de perda de dados" descrita no runbook principal.

**Admin Dashboard** — painel interno usado pelo time de operações para gerenciar pedidos, estoque e atendimento manual. Uma falha aqui impede o time interno de trabalhar, mas não impede o cliente de comprar — o que frequentemente gera pressão desproporcional pra escalar como incidente grave, apesar de tecnicamente se enquadrar como SEV-3 na maioria dos casos.

## Dependências que atravessam tiers

Vale registrar explicitamente: o Checkout Service (Tier 0) faz uma chamada síncrona ao Recommendation Engine (Tier 1) para popular a seção "compre também" na tela de confirmação. Em condições normais essa chamada tem timeout curto e falha silenciosamente sem travar o checkout — mas sob picos de tráfego muito acima do normal, esse timeout pode se acumular e causar lentidão perceptível no fluxo de compra, mesmo o Recommendation Engine não sendo, ele mesmo, um sistema de Tier 0. Esse é o cenário descrito no runbook principal como exceção que eleva um problema de sistema não-essencial a SEV-1.
