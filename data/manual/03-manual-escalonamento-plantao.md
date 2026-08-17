# Manual de Escalonamento e Plantão — NimbusFlow

**Propósito:** definir quem é acionado, por qual canal, e com qual prazo, uma vez que um incidente já foi classificado por severidade.

## Estrutura de plantão

A NimbusFlow mantém dois níveis de plantão simultâneos, cobrindo turnos de 24 horas divididos entre três squads regionais:

- **Plantão primário:** um engenheiro generalista, responsável por qualquer sistema, que atua como primeiro respondente. Recebe alertas automáticos de monitoramento e reports manuais do time de suporte ao cliente.
- **Plantão secundário:** um especialista por área (Pagamentos, Autenticação, Catálogo/Busca, Infraestrutura), acionado quando o plantão primário identifica que o problema está fora da sua capacidade de resolver sozinho, ou automaticamente para qualquer incidente classificado como SEV-2 ou superior.

## Prazos de resposta por severidade

- **SEV-3:** sem prazo de resposta imediata. O plantão primário registra e prioriza junto com o backlog normal do time responsável pelo sistema.
- **SEV-2:** o plantão secundário da área correspondente deve confirmar recebimento do alerta em até 15 minutos. Se não houver confirmação nesse prazo, o sistema de plantão escala automaticamente para o próximo da lista de rotação, e depois para o gestor da área.
- **SEV-1:** war room aberto imediatamente pelo plantão primário, sem esperar confirmação de ninguém. O Incident Commander de plantão (função rotativa, separada da escala técnica) deve entrar na chamada em até 5 minutos.

## Protocolo de war room

Ao abrir um war room, três papéis são preenchidos, nessa ordem de prioridade:

1. **Incident Commander (IC):** coordena a resposta, decide se e quando escalar mais gente, e é a única pessoa autorizada a declarar o incidente encerrado. O IC não precisa (e idealmente não deve) ser a pessoa mexendo no código durante o incidente — a função é de coordenação, não de execução técnica.
2. **Comms Lead:** responsável por manter um canal de status atualizado a cada 15 minutos, tanto internamente (canal de incidentes) quanto, se o IC decidir que é necessário, numa página de status pública. Isso existe especificamente para que engenheiros técnicos não percam tempo respondendo pergunta de status repetidamente.
3. **Responsável técnico da área afetada:** a pessoa (ou pessoas) efetivamente investigando e corrigindo o problema, puxada da escala de plantão secundário correspondente ao sistema envolvido, conforme o Catálogo de Sistemas Críticos.

Nenhum desses três papéis precisa ser preenchido por gestão — a estrutura é deliberadamente técnica. Liderança é apenas notificada, não convocada automaticamente, exceto no caso descrito abaixo.

## Quando liderança é convocada ativamente

Liderança (Diretoria de Engenharia e, dependendo do caso, Jurídico ou Comunicação) é chamada ativamente para dentro do war room, e não apenas notificada, em três situações específicas: incidente classificado como SEV-1 que já dura mais de 45 minutos sem sinal de resolução iminente; qualquer incidente envolvendo risco de vazamento de dados de cliente, independentemente da duração; e qualquer incidente que já gerou menção pública nas redes sociais com volume relevante (mais de 50 menções identificadas pelo time de Comms em uma hora).

## Escalonamento fora do horário comercial

Fora do horário comercial, a escala de plantão secundário se reduz: em vez de um especialista por área, existe um único "plantão sênior noturno" cobrindo todas as áreas ao mesmo tempo, com autoridade para decidir sozinho se um incidente noturno justifica acordar mais gente ou pode esperar até o horário comercial. Essa pessoa tem autonomia explícita para reclassificar a severidade de um incidente à luz do volume de tráfego real do momento — alinhado com a exceção de horário descrita no runbook principal — sem precisar de aprovação de ninguém para isso.

## Encerramento de incidente e pós-morte

Um incidente só é considerado formalmente encerrado quando o IC declara explicitamente, com o sistema afetado estável por pelo menos 15 minutos consecutivos (30 minutos para incidentes que envolveram Payment Gateway ou Auth Gateway, dado o histórico de recorrência rápida nesses dois sistemas especificamente). Todo incidente classificado como SEV-1, e qualquer SEV-2 que tenha demorado mais de duas horas para resolver, gera obrigatoriamente um documento de postmortem em até 3 dias úteis — o acervo desses documentos está reunido no arquivo de Postmortems de Incidentes Anteriores, e deve ser consultado antes de julgar um incidente novo como "inédito", porque boa parte dos incidentes que parecem novos já têm um precedente direto registrado ali.
