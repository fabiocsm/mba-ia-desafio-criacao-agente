# Pesquisa: confirmação, códigos e exclusividade

**Data**: 2026-10-23. Reutiliza decisões da 001; pesquisa auxiliar consultou código do wheel oficial ADK 2.2.0 e fontes primárias, encerrada antes de concluir. Nenhuma aplicação, chamada Gemini, quota autenticada ou cenário de aceitação foi executado.

## R 1 — Stack e desconhecidos herdados

**Decisão**: manter Python>=3.12/uv/FastAPI, ADK==2.2.0, dois SQLite, SessionIdentity canônica e topologia/App resumível da [001](../001-sessoes-isolamento/research.md). Modelo e checagem de acesso/quota continuam configuráveis e operacionais; não escolher novo modelo ou presumir limites ativos. Não há dúvida normativa pendente.

**Justificativa**: evita redesenhar dependência concluída e mantém identidade, eventos e ambiente reproduzíveis.

**Alternativas**: trocar banco/SDK/topologia sem evidência obrigaria revalidar a 001 e não resolve automaticamente confirmação persistida. Pesquisa pontual desta spec foi limitada aos IDs e retomada, crash e atomicidade.

## R 2 — Confirmação ADK e correlação dos IDs

**Decisão**: `tool_context.request_confirmation(hint=texto, payload=detalhes_json)` e retorno intermediário sem efeito. Persistir ID original da tool, ID novo da function call `adk_request_confirmation`, `invocation_id`, `author` e branch do evento. O evento gerado contém `originalFunctionCall` e `toolConfirmation`; adapter correlaciona a pendência com esses campos depois de persistir o evento. Publicar pendência somente após correlação durável, reconciliada no restart.

Na aprovação, rota gera `Content(role="user", parts=[Part(function_response=FunctionResponse(name="adk_request_confirmation", id=native_confirmation_id, response={"confirmed": booleano}))])`, passa `invocation_id` original ao `Runner.run_async` e mantém App resumível. A tool reexecutada recebe `tool_context.function_call_id` original. Payload serve à exibição; somente banco canônico fornece parâmetros/consentimento.

**Justificativa**: o processador nativo localiza a chamada original nos eventos; os dois IDs têm funções distintas. Confundi-los pode produzir HTTP 200 sem execução.

**Alternativas**: interpretar “já confirmei”, executar diretamente na rota, confiar só no `ToolConfirmation.confirmed` ou usar sessão filha foram rejeitados. Dedup do ADK por eventos não garante exatamente um efeito.

**Fontes**: [Context v 2.2.0](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/agents/context.py), [geração do evento](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/flows/llm_flows/functions.py), [processador de confirmação](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/flows/llm_flows/request_confirmation.py).

## R 3 — Seleção do agente e limite do serviço de sessão

**Decisão**: manter árvore `aurora_principal` → especialistas reservas/visitantes, modo chat, parent transfer permitido e peers bloqueados nos especialistas, App com `ResumabilityConfig(is_resumable=True)`, DatabaseSessionService SQLite. Primeiro validar caminho nativo. Se diagnóstico comprovar divergência apenas na seleção do solicitante, implementar `AuroraRunner._find_agent_to_run(self, session, root_agent)` em runtime/runner.py, restringindo override à retomada canônica: ContextVar por requisição contém sessão/invocation/author da pendência validada, confere sessão e resolve agente existente na árvore. Sem contexto confiável usa super. ContextVar é instalada/resetada por token em try/finally, compatível com Python 3.12; nenhum atributo global mutável.

**Justificativa**: em ADK 2.2.0 o agente é escolhido antes da nova mensagem; uma resposta pode atingir o principal em vez do especialista. ContextVar impede que sessões concorrentes troquem author. Contrato define fronteiras e gate, sem substituir processador nativo.

**Limitação**: a [documentação oficial](https://adk.dev/tools-custom/confirmation/#known-limitations) declara DatabaseSessionService não suportado para confirmação. Leitura do código e o fallback não provam suporte. Validar antes/depois do restart com SQLite real, autoria, retorno da tool e efeito nas rotas diretas; investigar serialização/retomada/persistência se a seleção não explicar falha. Funcionalidade permanece incompleta até esses gates passarem, sem fallback para memória volátil.

**Alternativas**: forçar o agente por argumento do usuário/modelo ou compartilhar variável entre requisições rompe a fronteira de autorização; usar só prompts não corrige roteamento do Runner.

**Fontes**: [Runner v 2.2.0](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/runners.py), [retomada](https://adk.dev/runtime/resume/), [ContextVar Python 3.12](https://docs.python.org/3.12/library/contextvars.html).

## R 4 — Decisão, efeito e intervalo entre bancos

**Decisão**: rota grava decisão e despacho recuperável em uma transação; tool consome decisão e grava efeito/recusa/negação em outra transação única de negócio, com resultado persistido. HTTP replay encontra decisão já registrada e retorna 409. Reentrada técnica do mesmo Runner recupera resultado sem repetir efeito. Startup apenas reconcilia metadados sem eventos; uma nova POST de mensagens recupera despachos incompletos pelo mesmo caminho nativo antes de processar o texto, inclusive se o efeito foi commitado antes de persistir o evento ADK. Se a invocation já terminou, conferir evento final e resultado antes de encerrar despacho. Não afirmar commit distribuído entre os dois bancos.

**Justificativa**: falha de processo pode ocorrer entre dois commits; persistir job e resultado impede reexecução indevida e permite completar eventos. Recuperação em nova interação mutável acrescenta eventos reais quando necessária e nunca reescreve anteriores. Startup e GET não executam Runner, não alteram eventos e mantêm a mesma contagem; após HTTP 200 não resta despacho a recuperar. Replay 409 não recupera nem executa efeito.

**Alternativas**: consumir antes de executar sem recuperação pode perder ação aprovada; consumir depois do efeito em outro commit permite duplicidade; aceitar novo POST como recuperação quebra replay 409; journal espelho de eventos cria autoridade duplicada.

**Fontes**: [transações SQLite](https://www.sqlite.org/lang_transaction.html), [processador ADK](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/flows/llm_flows/request_confirmation.py).

## R 5 — Exclusividade, códigos e autorização

**Decisão**: índice único parcial `(area,data) WHERE cancelada=0`, `BEGIN IMMEDIATE`, WAL/busy_timeout e serialização curta das escritas no worker local. Tratar especificamente violação de área/data como resultado indisponível, nunca devolver registro vencedor nem converter em 409 HTTP. Após conflito, finalizar consumo e recusa no mesmo escopo transacional válido; usar savepoint se a camada SQL exigir rollback do statement. Não manter transação durante Gemini. Não confundir violação do índice de códigos com indisponibilidade.

Códigos usam contador durável iniciado acima do maior sufixo inicial e ledger único permanente; reservar código e inserir reserva no mesmo commit. Cancelar conserva linha/tombstone e ledger. Restauração da 005 preservará ledger/contador mesmo se recriar os dados iniciais. Cancelamento usa predicado de proprietário na consulta/update; disponibilidade só EXISTS.

**Justificativa**: consulta anterior fica obsoleta; índice protege inclusive concorrência. Identificadores são do sistema e sobrevivem à remoção da projeção ativa. SQL filtrado impede dados alheios em resultados antes dos eventos.

**Alternativas**: lock de processo como única exclusividade, `MAX(codigo)+1` sobre apenas reservas ativas e consultar dono para redigir recusa foram rejeitados.

**Fontes**: [índices parciais](https://www.sqlite.org/partialindex.html), [transações](https://www.sqlite.org/lang_transaction.html), [constraints](https://www.sqlite.org/lang_createtable.html).
