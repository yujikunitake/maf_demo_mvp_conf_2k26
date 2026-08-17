# Guia de Decisão para Casos-Limite — NimbusFlow

**Propósito:** complementar o runbook principal com raciocínio aplicado a situações que não se encaixam claramente numa regra única — a maioria dos incidentes reais cai em algum ponto cinzento entre duas categorias, e este guia existe para reduzir a dependência de "perguntar pro sênior" a cada caso ambíguo.

## Como pensar quando duas regras parecem se aplicar ao mesmo tempo

Quando uma situação parece se encaixar em mais de uma regra do runbook principal ao mesmo tempo, a orientação geral é: **a regra que resulta na severidade mais alta prevalece**, exceto quando uma exceção específica e mais recente contradiz diretamente a regra geral (como a exceção de horário noturno reduzindo a severidade, mesmo com todas as outras condições apontando para cima). Na dúvida entre aplicar uma regra geral e uma exceção específica, a exceção específica sempre vence — ela existe justamente para cobrir o caso que a regra geral erraria.

## "Não sei se isso é o sistema X ou o sistema Y"

É comum um sintoma reportado pelo cliente não indicar claramente qual sistema técnico está envolvido. Um bom hábito é seguir o sintoma até o efeito mais próximo do cliente, não até a causa técnica mais provável — a classificação de severidade depende do que o cliente está impedido de fazer, não de qual serviço internamente está com bug. Por exemplo, "não consigo finalizar minha compra" pode ter causa em Checkout Service, Payment Gateway, ou até Inventory Service (produto ficou indisponível no meio do processo) — mas para efeitos de severidade inicial, o que importa é que o fluxo de checkout está impedido, o que já é suficiente para aplicar as faixas percentuais de impacto do runbook principal, independente de qual sistema acabar sendo identificado como causa raiz.

## "O volume ainda é baixo, mas está crescendo rápido"

Situações onde o volume de relatos está claramente em trajetória ascendente (dobrando a cada 5-10 minutos, por exemplo) merecem ser tratadas com a severidade que o volume projetado indicaria em 20-30 minutos, não a severidade que o volume atual, isoladamente, indicaria. Esperar o volume "confirmar" antes de escalar costuma custar tempo de resposta precioso exatamente nos incidentes que mais importam.

## "Um cliente grande específico está reclamando, mas o volume geral é baixo"

Volume de relatos não é a única métrica que importa. Se o cliente afetado representa uma fração desproporcional da receita (contas empresariais grandes, por exemplo), a triagem deve considerar isso como um fator de peso equivalente a um aumento no volume percentual — não existe uma fórmula fixa para essa conversão, e esse é um dos poucos casos em que se recomenda envolver o plantão secundário mesmo com volume geral baixo, só para uma segunda opinião.

## "O problema já parou sozinho, ainda preciso classificar?"

Sim. Um problema que se resolveu sozinho antes de qualquer intervenção humana ainda deve ser classificado e registrado com a severidade que teria recebido enquanto estava ativo, porque o histórico desses casos (ver Postmortems de Incidentes Anteriores) é o que permite identificar padrões recorrentes antes que eles se tornem incidentes maiores e persistentes.

## "É feriado / fim de semana, isso muda alguma coisa além do horário noturno?"

A exceção de horário comercial do runbook principal se refere estritamente à faixa de horário do dia (antes das 8h, depois das 20h), não ao dia da semana. Finais de semana em horário comercial (entre 8h e 20h, sábado ou domingo) seguem as regras normais de horário comercial, com uma ressalva: o volume de tráfego de finais de semana no comércio da NimbusFlow costuma ser 15-20% maior que dias úteis, então a barra de "volume real do horário" para decisões que dependem disso deve ser ajustada para cima proporcionalmente, e não comparada diretamente ao volume médio de um dia útil.

## "O manual não cobre exatamente esse caso"

Quando nenhuma regra explícita, exceção ou postmortem anterior cobre exatamente a situação, a orientação é classificar pelo princípio mais próximo — geralmente a combinação entre qual fluxo de negócio está impedido (ver Catálogo de Sistemas Críticos) e a faixa percentual de impacto (ver Runbook de Triagem) — e, em seguida, registrar o caso como um novo precedente assim que resolvido, para que o próximo incidente parecido já tenha uma referência direta e não precise passar pelo mesmo raciocínio do zero.
