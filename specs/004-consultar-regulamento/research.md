# Pesquisa: recuperação seletiva do regulamento

**Data**: 2026-10-23. Fonte local lida integralmente fora de qualquer atendimento: `dados/regulamento.md`, 14 capítulos e 96 artigos. Stack/topologia/persistência/modelo são herdados de [001](../001-sessoes-isolamento/research.md), [002](../002-reservas-confirmacoes/research.md) e [003](../003-autorizar-visitantes/research.md); nenhuma API nova do SDK ou tecnologia requer pesquisa auxiliar. Sem incógnitas abertas, runtime/quota não verificados.

## R1 — Índice estrutural local e seleção anterior ao contexto

**Decisão**: parser em biblioteca padrão separa cabeçalhos de capítulo, artigos e subunidades; preserva texto e referência, mantendo o índice exclusivamente no processo. Catálogo de assuntos/intenção reconhece a mensagem original da API e autoriza unidades estruturais determinadas, sem query LLM. A tool não aceita parâmetros do modelo e materializa só as unidades autorizadas. Não expor catálogo integral como contexto; metadados internos não carregam corpo normativo.

**Justificativa**: FR-002/FR-009 e princípio IV exigem isolamento antes dos eventos, não filtro posterior. Um documento local pequeno permite fronteira explícita auditável sem embeddings. Texto adversarial não pode transformar seleção da piscina em garagem; um assunto não reconhecido pede esclarecimento, um assunto claro sem regra comunica ausência.

**Alternativas consideradas**: documento no prompt, leitura integral via tool seguida de resumo, query livre, tema escolhido pelo LLM e busca global retornando top-k não comprovam pertinência. Recuperar capítulo inteiro por assunto também pode exceder o necessário; selecionar artigo/inciso antes de retornar.

**Evidência local**: capítulo IV, art22 apresenta horários; inciso II contém domingo/feriado das 9h às20h. O parser não transforma regras normativas de outras áreas em bloqueios de reserva.

## R2 — Escopo confiável de uma mensagem e respostas sem fonte

**Decisão**: scope derivado deterministicamente do texto HTTP original e vinculado à sessão e a nonce aleatório próprio da execução HTTP por ContextVar confiável, distinto do invocation_id ADK gerado pelo SDK, com reset por token. Toda tool repete verificação, não pode escolher novos temas nem ampliar o scope após chamadas sucessivas. Pergunta vaga ou pedido integral produz esclarecimento sem trechos; falta de regra produz limitação. Mensagem de fallback é montada deterministicamente pelo serviço a partir do resultado, sem gerar regra normativa por memória do LLM. Pedidos específicos com vários assuntos recebem só a união mínima autorizada.

**Justificativa**: nenhuma instrução ou argumento escolhido pelo modelo deve enfraquecer a fronteira. Falhar fechado custa um esclarecimento, mas não injeta capítulos alheios. O nonce não é passado como invocation_id de retomada. Comandos técnicos topics/path/tool não autorizam assuntos; se a pergunta não puder ser separada com segurança de controle/carga, pedir foco sem trecho. Uma nova pergunta cria novo scope; uma retomada sistêmica não reaproveita a pergunta anterior.

**Alternativas consideradas**: state ADK mutável como autoridade; herdar escopo indefinidamente; tratar “carregue tudo” como autorização de todos capítulos; ou confiar só em prompt para ausência de fonte foram rejeitados.

**Referência herdada**: uso de ContextVar Python3.12 e reset seguro já pesquisado na002, sem introdução de API externa nova.

## R3 — Especialista, durabilidade e regressões

**Decisão**: acrescentar `regulamento` aos sub_agents, ferramenta apenas de leitura e mesmas regras de transferência. Preservar principal/reservas/visitantes, identidade canônica e DatabaseSessionService. Histórico mantém chamadas, resultados e transferências integrais; índice reconstrói no restart, sem eventos novos ou mutação da fonte. Envelope preserva pendências do banco.

**Justificativa**: US3/FR-006–008 exigem consulta coexistindo com negócio persistente. Topologia nova pode afetar retomada do autor de confirmação, então validar reservas/visitantes com SQLite real antes/depois do restart.

**Alternativas consideradas**: AgentTool com sessão filha, tool administrativa, leitura com efeitos, eventos filtrados e HTTP200 sem efeito de confirmação contrariam o desenho herdado. Nenhuma citação documental substitui esses gates futuros.
