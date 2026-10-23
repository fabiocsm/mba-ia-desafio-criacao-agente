# Pesquisa: extensão do consentimento para visitantes

**Data**: 2026-10-23. Reutilização explícita da pesquisa oficial e leitura do ADK 2.2.0 da [001](../001-sessoes-isolamento/research.md) e [002](../002-reservas-confirmacoes/research.md). Nenhuma nova tecnologia ou incógnita exige pesquisa auxiliar; nenhum runtime, quota autenticada, modelo ou efeito foi testado nesta preparação.

## R1 — Mecanismo único de consentimento

**Decisão**: registrar `autorizar_visitante` no ConfirmationCoordinator 002. A tool inicial chama request_confirmation; a rota existente decide; o Runner retorna ao especialista solicitante. Distinguir ID público, ID original da tool e ID nativo da confirmação. Payload é exibição; identidade e parâmetros congelados do banco são autoridade.

**Justificativa**: FR-002–FR-005 e FR-007 exigem o mesmo canal e proteção consumível de reservas. Reutilizar a correlação e despacho evita consentimentos divergentes.

**Alternativas consideradas**: confirmação textual, segunda rota, gravação direta pela rota ou confiar só em ToolConfirmation.confirmed violam o desenho constitucional.

**Referências herdadas**: [processador nativo v2.2.0](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/flows/llm_flows/request_confirmation.py), [Context v2.2.0](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/agents/context.py); detalhes em 002 R2/R3 e [contrato comum](../002-reservas-confirmacoes/contracts/confirmation-runtime.md). Não reavaliados remotamente nesta extensão.

## R2 — Efeito idempotente na mesma transação

**Decisão**: acrescentar proveniência nullable `proposta_id` única ao visitante existente: importados não têm proposta; novos registros de autorização têm proposta canônica. Callback recebe conexão/transação aberta pelo consumo 002, insere visita e retorna resultado próprio; o coordenador salva resultado e consumo no mesmo commit. Não deduplicar nome/data de propostas diferentes.

**Justificativa**: a unicidade da proveniência protege o efeito da mesma decisão sem inventar unicidade civil. Negação não insere, replay HTTP retorna 409, reentrada técnica consumida devolve resultado durável. Datas e nome são os apresentados, apartamento é o vínculo imutável da sessão.

**Alternativas consideradas**: commit independente no callback permite efeito sem consumo; chave nome/data impediria propostas válidas; confiar em memória perderia proteção no restart.

**Referência herdada**: [transações SQLite](https://www.sqlite.org/lang_transaction.html), 002 R4 e data-model. Sem transação distribuída entre ADK e negócio.

## R3 — Persistência, topologia e gate real

**Decisão**: preservar App resumível, DatabaseSessionService e árvore de agentes 001/002, incluindo flags de transferência e ContextVar de retomada. Provar nova tool no especialista visitantes com sessão persistida e após reinício. Recuperação de despacho incompleto apenas numa nova POST mensagens antes do texto, nunca startup/GET/replay 409.

**Justificativa**: executar nova ação exige validar a autoria e o efeito novamente; documentação e código não demonstram o gate de integração. Modelo Gemini e limites ativos mantêm gate operacional herdado, sem acesso à chave nesta tarefa.

**Alternativas consideradas**: AgentTool/sessão filha, memória volátil ou HTTP 200 sem visita real não satisfazem as garantias. Fallback de seleção versionado da 002 só é admissível após diagnóstico e contexto canônico; outras falhas exigem correção do runtime.

**Referências herdadas**: [limitação oficial DatabaseSessionService](https://adk.dev/tools-custom/confirmation/#known-limitations), [Runner v2.2.0](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/runners.py), [retomada](https://adk.dev/runtime/resume/). Gates operacionais pendentes, nenhuma alegação de suporte comprovado.
