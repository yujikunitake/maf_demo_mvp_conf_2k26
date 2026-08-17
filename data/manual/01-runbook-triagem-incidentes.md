# Runbook de Triagem de Incidentes — NimbusFlow

**Equipe responsável:** SRE / Plataforma
**Última revisão:** por este documento, mantido pela equipe de confiabilidade
**Propósito:** definir como qualquer pessoa de plantão classifica um incidente reportado e decide a resposta inicial, antes mesmo de um engenheiro sênior olhar o caso.

## Visão geral dos níveis de severidade

A NimbusFlow classifica incidentes em três níveis operacionais, cada um com uma resposta padrão associada:

- **SEV-3 (monitorar):** o problema existe, é real, mas não bloqueia nenhum fluxo essencial de negócio no momento. Resposta padrão: abrir ticket de acompanhamento, sem acionar ninguém fora do time responsável pelo sistema afetado.
- **SEV-2 (escalar):** o problema afeta parcialmente um fluxo essencial, ou afeta totalmente um fluxo não essencial mas com risco de virar essencial se não for contido. Resposta padrão: acionar o engenheiro de plantão secundário do sistema afetado, com prazo de resposta de até 15 minutos.
- **SEV-1 (war room):** o problema afeta totalmente um fluxo essencial de negócio, ou tem risco concreto de causar perda de dados. Resposta padrão: abrir war room imediatamente, acionar Incident Commander, notificar liderança.

A classificação não é feita por um checklist rígido de "se X, então Y" — ela depende de julgamento sobre impacto real, e é exatamente por isso que este runbook traz tanto exemplo e tanta exceção: a decisão certa quase sempre depende de mais de um fator ao mesmo tempo.

## O que conta como "fluxo essencial de negócio"

Um fluxo é considerado essencial quando sua interrupção impede diretamente um cliente de comprar, pagar, ou acessar a própria conta. Isso inclui, mas não se limita a: autenticação e login, checkout e finalização de compra, processamento de pagamento, e confirmação de pedido. Fluxos de suporte à experiência — como recomendações de produto, busca avançada, notificações por email, ou o painel administrativo interno — não são considerados essenciais por si só, mesmo quando o time responsável por eles os trate como prioridade alta no dia a dia.

Uma armadilha comum na triagem é confundir "sistema importante para o negócio" com "fluxo essencial". O sistema de recomendações, por exemplo, tem impacto real em receita ao longo do tempo, mas sua queda total não impede ninguém de comprar — portanto, mesmo uma falha completa nele nunca passa de SEV-2, salvo a exceção descrita abaixo sobre picos de tráfego promocional.

## Regras de escalonamento por impacto parcial

Quando um sistema essencial está degradado mas não totalmente fora, a regra geral é: se menos de 5% das tentativas falham, é SEV-3; entre 5% e 30%, é SEV-2; acima de 30%, é SEV-1, mesmo que o sistema não esteja "totalmente fora" no sentido literal. Essa faixa de 30% não é arbitrária — ela reflete o ponto em que o volume de reclamações de suporte historicamente começa a crescer de forma não-linear.

Existe uma exceção importante a essa regra: se a falha parcial afeta especificamente o método de pagamento mais usado (atualmente cartão de crédito, responsável por cerca de 70% do volume), o incidente sobe automaticamente um nível de severidade em relação ao que a porcentagem sozinha indicaria — porque a concentração num único método amplifica o impacto percebido pelo cliente, mesmo que o número absoluto de usuários afetados seja parecido.

## Exceções ligadas a horário e sazonalidade

Fora do horário comercial (antes das 8h ou depois das 20h, horário de Brasília), a barra para abrir SEV-1 sobe: um problema que durante o dia seria classificado como SEV-1 por afetar checkout parcialmente pode, à noite, ser tratado como SEV-2 se o volume de tráfego real no momento for baixo o suficiente para que o impacto absoluto (não percentual) seja pequeno. A pessoa de plantão deve olhar o volume de transações da última hora antes de decidir.

Durante períodos de campanha promocional divulgados previamente pelo time de marketing (Black Friday, datas comemorativas com campanha ativa), essa lógica se inverte: qualquer degradação em checkout, mesmo abaixo de 5%, deve ser tratada como SEV-2 no mínimo, porque o volume de transações nesses períodos é tipicamente 8 a 10 vezes maior que o normal, e problemas que pareceriam pequenos em dia comum representam um volume absoluto de clientes afetados muito maior.

## Quando um problema não-essencial vira SEV-1

Existem três situações em que um sistema fora da lista de "fluxo essencial" ainda justifica SEV-1:

1. **Risco de perda de dados**, mesmo que o sistema afetado seja de suporte (por exemplo, uma falha de escrita no banco de dados de histórico de pedidos, mesmo que a leitura ainda funcione).
2. **Vazamento potencial de dados de cliente**, independentemente de qual sistema esteja envolvido — isso inclui logs expondo informação sensível por engano, não apenas invasões confirmadas.
3. **Picos de tráfego promocional afetando o sistema de recomendações a ponto de causar timeout em cascata no checkout** — aqui a causa raiz está num sistema não-essencial, mas o efeito colateral está no fluxo essencial, e a triagem deve seguir o efeito, não a causa.

## Casos que geram confusão recorrente

Vale reforçar dois padrões que o time de plantão erra com frequência:

- Um erro que aparece "só para alguns usuários" não é automaticamente SEV-3. Se esses usuários compartilham uma característica em comum (mesmo país, mesmo método de pagamento, mesmo tipo de dispositivo), pode ser sintoma de um problema que vai se espalhar, e merece ser tratado com mais cautela do que o volume atual sozinho indicaria.
- Lentidão não é a mesma coisa que indisponibilidade, mas lentidão severa e sustentada (tempo de resposta acima de 8 segundos por mais de 10 minutos consecutivos) em qualquer fluxo essencial deve ser tratada como se fosse uma queda parcial, seguindo as mesmas faixas percentuais de abandono de sessão como proxy de impacto.

Este runbook deve ser lido em conjunto com o Catálogo de Sistemas Críticos (para saber o que é "essencial") e com o Manual de Escalonamento e Plantão (para saber quem acionar depois de classificar).
