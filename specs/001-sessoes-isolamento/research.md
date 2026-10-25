# Pesquisa: runtime, identidade, persistência e modelos

**Data**: 2026-10-23. Pesquisa por fontes oficiais e leitura do wheel ADK 2.2.0, incluindo subagente de pesquisa pontual. Não houve instalação da aplicação, execução de Runner/Gemini, consulta autenticada das quotas nem validação de efeitos de negócio.

## R1 — ADK e topologia persistida

**Decisão**: fixar `google-adk==2.2.0`; configurar `App(name="aurora", root_agent=principal, resumability_config=ResumabilityConfig(is_resumable=True))`, `Runner(app=app, session_service=...)` e `DatabaseSessionService` SQLite. Principal e especialistas são `LlmAgent(mode="chat")`, especialistas em `sub_agents`, com `disallow_transfer_to_parent=False` e `disallow_transfer_to_peers=True`. Principal permite transferência aos filhos e retorno destes. Modo não streaming, sem compactação de histórico.

**Justificativa**: versão da série exigida, código exato inspecionado e topologia estável. A seleção do agente no Runner ocorre antes de anexar a nova mensagem; bloquear transferência ao pai pode desviar a retomada ao principal. A configuração escolhida permite ao Runner reencontrar o último especialista executado.

**Alternativas consideradas**: AgentTool foi descartado para os especialistas de negócio: em 2.2.0 cria Runner filho com `InMemorySessionService`, sem a mesma trilha durável. Memória volátil como serviço principal viola reinício. Não usar modo task/single_turn nem bloquear transferência ao pai como otimização.

**Fontes**: [PyPI da versão](https://pypi.org/project/google-adk/2.2.0/), [Runner v2.2.0](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/runners.py), [AgentTool v2.2.0](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/tools/agent_tool.py). Código também conferido no [wheel oficial](https://files.pythonhosted.org/packages/64/f5/44a3b20b17bac130497f2d1dde8b93c90cfc026983cd94f24488d540ea70/google_adk-2.2.0-py3-none-any.whl).

## R2 — Confirmação: decisão herdada pela 002 e limite da pesquisa

**Decisão**: usar o mecanismo nativo `tool_context.request_confirmation` e persistir correlação entre ID público, ID da function call `adk_request_confirmation`, chamada original, invocation, author solicitante e parâmetros congelados. A rota de confirmações da 002 valida sessão/pendência antes de criar `FunctionResponse(name="adk_request_confirmation", id=id_adk, response={"confirmed": booleano})`; retoma o Runner com o `invocation_id` original. A tool reentra e a camada transacional autoriza o efeito somente pela decisão canônica consumível uma vez. Texto de conversa não cria essa autorização.

**Justificativa**: a serialização v1 retém `actions.requested_tool_confirmations` e conteúdo; o processador encontra a chamada original nos eventos e reexecuta a tool. Isso define uma integração testável, sem executar a ação diretamente na rota HTTP. A idempotência do negócio continua necessária, pois retomada não oferece exatamente uma execução.

**Limitação documental**: a [documentação de confirmação](https://adk.dev/tools-custom/confirmation/#known-limitations) declara que DatabaseSessionService não é suportado. A leitura do código não comprova compatibilidade de runtime nem remove essa restrição. O README do desafio exige demonstrar SQLite, agente correto e efeito real; isso é gate obrigatório na 002, incluindo reinício entre solicitação e aprovação. Em caso de falha, não substituir por memória nem aceitar somente HTTP 200. Investigar autoria, `invocation_id`, eventos de confirmação, flags da árvore e configuração do App; se o diagnóstico demonstrar falha exclusivamente na seleção, usar fallback estreito versionado em `runtime/runner.py`: sobrescrever `_find_agent_to_run(self, session, root_agent)` somente durante retomada validada, lendo `session_id`, `invocation_id` e `author` da pendência canônica via ContextVar isolada por requisição. Conferir sessão e resolver `root_agent.find_agent(author)`; sem contexto confiável chamar super. Não aceitar author do cliente/modelo, não manter atributo global mutável e não executar tool diretamente. Manter App/Runner/processador de confirmação nativos; repetir autoria, reinício e efeito. Outras falhas de persistência exigem diagnóstico e correção da integração antes do aceite, sem alegar que esse fallback as resolve. A implementação da 002 deve resolver qualquer falha antes de declarar a funcionalidade pronta.

**Alternativas consideradas**: consentimento textual, ação na rota fora do Runner, trocar parâmetros após aprovação ou registrar sucesso sem efeito real foram rejeitados por violar a constituição.

**Fontes**: [processador v2.2.0](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/flows/llm_flows/request_confirmation.py), [retomada e idempotência](https://adk.dev/runtime/resume/), [schema v1](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/sessions/schemas/v1.py).

## R3 — Identidade independente do modelo

**Decisão**: tabela `session_identity` imutável no banco de negócio, chave `session_id`, apartamento gravado apenas pela criação HTTP. Tool resolve `tool_context.session.id` público para essa tabela. Assinaturas não incluem apartamento ou session_id. Nada em `state_delta`, output_key, mensagem, transferência ou argumento do modelo redefine a autorização.

**Justificativa**: state ADK é contexto mutável e não deve ser autoridade de identidade. Um state adulterado não muda o predicado do SQL. Todos os agentes compartilham apenas a identidade autorizada e ferramentas limitadas.

**Alternativas consideradas**: confiar em prompt, parâmetro apartamento livre ou state ADK isoladamente falha sob prompt injection. Rotas de verificação não viram tools.

**Fonte**: [Context v2.2.0, propriedade session](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/agents/context.py).

## R4 — SQLite e histórico integral

**Decisão**: negócio em `var/aurora.sqlite3`, ADK em `var/adk.sqlite3`, caminhos estáveis absolutos. Carga inicial em uma transação identificada por metadado de inicialização, somente se estado nunca inicializado. SQL de consulta própria filtra apartamento antes de materializar resultados. Agenda usa EXISTS e só devolve disponibilidade. Negócio com FK habilitada, WAL e busy_timeout; 002 acrescenta transações curtas e índice único parcial de reserva ativa, sem manter transação aberta durante chamada Gemini.

**Eventos**: `DatabaseSessionService` é a única fonte canônica do histórico. Seu schema v1 serializa o evento completo e ações; o Runner também persiste a entrada do usuário, que não aparece necessariamente no generator. GET consulta o serviço, não só eventos yielded. A consulta do serviço ordena somente timestamp; adaptar `append_event` em `runtime/sessions.py` para timestamp estritamente crescente por sessão, passo mínimo 1 ms, inicializado pelo maior timestamp persistido e protegido por lock próprio. Executar com um worker, serializar as operações da mesma sessão e não readquirir o lock interno do ADK, evitando deadlock. Não alterar eventos já gravados, não compactar e não usar `temp:*` para dados auditáveis; `partial` não é gravado pelo ADK, portanto usar geração não streaming e registrar todos os eventos completos persistidos.

**Alternativas consideradas**: journal espelho foi descartado por criar duas autoridades e risco de commit parcial; JSON nos arquivos iniciais viola integridade/concorrência; banco externo acrescenta serviço desnecessário nesta escala.

**Fontes**: [DatabaseSessionService v2.2.0](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/sessions/database_session_service.py), [schema v1](https://github.com/google/adk-python/blob/v2.2.0/src/google/adk/sessions/schemas/v1.py), [índices únicos parciais SQLite](https://www.sqlite.org/partialindex.html), [transações SQLite](https://www.sqlite.org/lang_transaction.html).

## R5 — Modelo Gemini e gate operacional de quotas

**Decisão**: `gemini-3.5-flash-lite` em todos os três agentes, com configuração opcional `GEMINI_MODEL`; alternativa `gemini-3.8-flash` se acesso/qualidade/limites requererem, após registrar escolha e revalidar fluxos. Usar chave Google AI Studio em `GOOGLE_API_KEY`. Não escolher 2.5 como default para clone novo: a documentação consultada restringe acesso dessa família a usuários que já a utilizavam.

**Justificativa**: modelo estável com function calling e custo/latência adequados a consultas e delegação simples. Reutilizar o modelo evita multiplicar decisões operacionais. A API remota é dependência; um pedido HTTP pode causar múltiplas chamadas ao modelo.

**Gate operacional, ainda não executado**: o implementador seleciona o projeto da chave no [AI Studio](https://aistudio.google.com/rate-limit), confere disponibilidade e RPM/TPM/RPD ativos para o modelo, registra data/modelo/limites sem chave em `docs/validacao/001-sessoes.md`, estima o fluxo de algumas dezenas de chamadas e reserva margem baseada no número observado de chamadas por interação. Executa `uv run python scripts/check_model.py` com chamada de função simples e depois o roteiro real. Se o projeto não permitir o modelo ou não comportar o fluxo, escolher a alternativa disponível documentada, espaçar requisições de acordo com limites ativos ou adequar quota pelo titular do projeto; repetir a validação. Não assumir free tier, quotas fixas, disponibilidade universal ou consentimento de cobrança para alterar conta.

**Alternativas consideradas**: Pro para consultas simples não foi necessário; modelos 2.5 legados e previews como default aumentam risco de disponibilidade. Retry de falha do modelo não pode repetir efeito de negócio sem deduplicação, tratada na 002.

**Fontes**: [catálogo oficial](https://ai.google.dev/gemini-api/docs/models), [3.5 Flash-Lite: function calling e versão estável](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [limites ativos e escopo por projeto](https://ai.google.dev/gemini-api/docs/rate-limits). Consultados em 2026-10-23; nada aqui declara quotas autenticadas verificadas.

## R6 — Instalação, API e extensão

**Decisão**: pacote `aurora`, FastAPI/Uvicorn, projeto uv com lock versionado, CLI `uv run aurora serve`. Nenhum serviço externo local. Documentar comandos de desenvolvimento em `docs/operacao.md`, preservando o README do enunciado até 005. Só nomes de variáveis sem valores em `.env.example`; defaults seguros e caminhos ficam no código/manual. Spec005 entregará `uv run aurora restaurar`, com política de invalidar sessões/pendências explicitamente.

**Justificativa**: instalação em clone limpo, um comando de subida e arquitetura mínima auditável. `uv sync` usa o lock para ambiente reproduzível.

**Alternativas consideradas**: containers e PostgreSQL não são necessários para dois SQLite locais; não adicionar UI/autenticação real.

**Fontes**: [uv: lock e sincronização](https://docs.astral.sh/uv/concepts/projects/sync/), [FastAPI: resposta e status](https://fastapi.tiangolo.com/tutorial/response-status-code/).
