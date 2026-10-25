# Plano de implementação: Sessões persistentes e isolamento por apartamento

**Branch Git**: `dev` | **Data**: 2026-10-23 | **Spec**: [spec.md](spec.md)
**Diretório selecionado**: `specs/001-sessoes-isolamento`; o identificador retornado pelo script não representa criação de branch.
**Estado**: desenho concluído; implementação e validação de runtime ainda não executadas.

## Resumo

Entregar a base da API do Residencial Aurora: sessão durável com apartamento imutável, consultas reais próprias, disponibilidade sem identificação de terceiros e eventos completos. Python 3.12, uv, FastAPI, Google ADK `2.2.0` e SQLite. O principal encaminha consultas a dois especialistas reais na mesma árvore ADK. O código resolve autorização pelo vínculo canônico da sessão, fora do state mutável do modelo.

Nenhuma mutação de reservas/visitantes nem consulta ao regulamento é anunciada como disponível nesta entrega. As specs 002, 003 e 004 acrescentam essas capacidades sem trocar identidade, serviço de sessão ou contrato. Não substituir o README do enunciado nesta fase.

## Contexto técnico

- **Linguagem/versão**: Python >=3.12, `.python-version` com 3.12, projeto `aurora` em `src/`.
- **Dependências principais**: `google-adk==2.2.0`, FastAPI, Uvicorn, SQLAlchemy, aiosqlite, pydantic-settings; resolução compatível e transitivas em `uv.lock`, instalado com `uv sync`. Falha de resolução deve ser corrigida sem remover o pin ADK.
- **Modelo**: `gemini-3.5-flash-lite` para principal e especialistas, configurável em `GEMINI_MODEL`; alternativa explícita `gemini-3.8-flash`, somente após checar acesso, quota e fluxos. Sem fallback silencioso ou quota presumida. Ver [research.md](research.md).
- **Armazenamento**: `var/aurora.sqlite3` para cadastro, identidade e negócio; `var/adk.sqlite3` via `DatabaseSessionService` para sessão/state/eventos. Caminhos absolutos resolvidos a partir da raiz; SQLite local dispensa serviços auxiliares. `var/` fora do Git.
- **Validação**: roteiro manual [quickstart.md](quickstart.md), inspeção do código e comparação JSON integral; sem suíte automatizada obrigatória.
- **Plataforma/tipo**: API HTTP local em Linux/macOS, `http://localhost:8000`; Uvicorn com um worker, sem reload no procedimento de reinício.
- **Desempenho/escala**: sem SLA inventado; algumas dezenas de chamadas Gemini no fluxo completo. Sessões distintas podem executar concorrentemente; serializar interações de uma mesma sessão para preservar ordem, sem lock global durante chamadas ao modelo.
- **Restrições**: nenhum segredo ou dado runtime versionado; `dados/` somente leitura; sem UI, autenticação real, pagamentos, deploy ou bloqueios adicionais de reserva.

## Verificação da constituição

Gates avaliados antes da pesquisa e novamente após o desenho; nenhum desvio normativo aceito.

| Regra | Mecanismo planejado | Evidência e responsável | Gate de desenho |
| --- | --- | --- | --- |
| I — confirmação sistêmica | Nesta spec só leitura; App resumível e sub_agents na mesma sessão preparam 002. Nenhuma tool de mutação registrada | Inspecionar catálogo em `agents/`; 002 comprovará aprovação/negação/reenvio/retomada após restart no armazenamento real | Conforme no escopo; runtime de confirmação não validado |
| II — identidade e isolamento | Tabela canônica imutável; ferramentas sem parâmetro apartamento; SQL próprio filtrado; disponibilidade por EXISTS | US1: resposta, function calls/results e eventos não contêm dados alheios | Conforme |
| III — durabilidade | Dois SQLite em disco; carga inicial transacional só em banco novo; ADK persistente; nenhum reset no startup | US2: JSON anterior igual após reinício e nova mensagem; 002/003 ampliam às mutações e códigos | Conforme |
| IV — seletividade e rastreabilidade | Nenhum regulamento injetado nesta spec; ler todos os eventos completos do serviço persistido | US3: eventos íntegros; 004 implementa recuperação seletiva | Conforme |
| V — exclusividade atômica | Modelo de reservas preserva registros cancelados e planeja índice único parcial área/data ativa | 002 implementa e valida concorrência; não há criação de reserva em 001 | Conforme |
| Stack, contrato, segredos | Pin ADK, uv, API nas cinco rotas desta spec, `.env.example` sem valores, modelo com checagem operacional | US1/US3 e inspeção; 002 acrescenta sexta rota; 005 consolida 15 passos | Conforme |

A compatibilidade da confirmação com o serviço persistido é risco explícito, com tarefa executável na 002. A documentação atual contém limitação; leitura de código não a substitui por promessa de suporte. Se a combinação falhar, ajustar a integração/topologia e repetir os gates afetados, sem aceitar resposta 200 sem efeito e sem trocar por memória volátil. A verificação de limites ativos exige acesso ao projeto AI Studio e permanece gate operacional antes de validar o runtime, com instruções e responsável em research/quickstart.

## Arquitetura e fluxo

1. `POST /sessoes` gera identificador no sistema, cria vínculo canônico único com apartamento e sessão ADK com `app_name=aurora`, `user_id=session_id`, `session_id=session_id`. `user_id` opaco por sessão evita partilhar state de usuário entre conversas. Retornar 201 somente após ambos persistirem. Falha parcial é compensada antes de retornar, sem identidade utilizável incompleta.
2. `POST /mensagens` resolve a sessão no repositório, obtém lock por sessão, envia `Content(role=user, parts=[Part(text=texto)])` pelo `Runner(app=app, session_service=...)`. Não aceita nome do agente, state, user_id ou apartamento do cliente. Os eventos são persistidos pelo serviço do Runner antes de responder.
3. `aurora_principal` tem `sub_agents=[reservas, visitantes]`. `reservas` lista reservas próprias e disponibilidade; `visitantes` lista visitantes próprios. Transferências entre agentes na árvore preservam a sessão e eventos. Não usar AgentTool com sessão filha. Não bloquear retorno ao principal nem encaminhamento aos especialistas. 002 verifica novamente os flags efetivos e o agente solicitante durante confirmação; 004 acrescenta especialista `regulamento`.
4. Cada tool resolve o identificador confiável do `ToolContext` para `session_identity` no banco, nunca o apartamento em mensagens, argumentos livres ou state. Não expor o repositório de verificação administrativa ao modelo. Um DTO próprio delimita os campos retornados; agenda retorna somente `livre` ou `ocupada` via consulta que não seleciona código/apartamento/responsável. A fronteira impede leitura alheia antes do resultado da tool, sem mascarar eventos.
5. A resposta agrega texto final destinado ao usuário, sem raciocínio interno, e `confirmacoes_pendentes=[]` neste incremento. O formato já admite a lista integral persistida da 002; não inferir pendências do texto do modelo.
6. `GET /eventos` lê os eventos canônicos persistidos, incluindo entrada, transferências, chamadas, resultados, ações ADK e metadados. Não cria evento por leitura nem altera conteúdo. Não filtra o histórico para corrigir vazamentos. Mesmo JSON e ordem entre leituras e reinício; desenho de ordenação detalhado no contrato runtime.
7. Rotas `/apartamentos/...` consultam negócio diretamente e não passam pelo Runner. Seus resultados não são injetados no histórico da conversa.

## Fases do desenho e artefatos

- **Fase 0 — pesquisa**: [research.md](research.md), decisões com fontes oficiais e alternativa avaliada; pesquisa auxiliar do ADK encerrada antes de concluir.
- **Fase 1 — modelo e contratos**: [data-model.md](data-model.md), [API](contracts/api.md), [tools/runtime](contracts/runtime-tools.md), [quickstart.md](quickstart.md).
- **Fase 2 — decomposição**: [tasks.md](tasks.md), gerado por speckit-tasks; setup → fundação → US1 P1 → US2 P1 → US3 P2 → acabamento. Persistência faz parte da fundação; US2 prova a continuidade, não adia sua implementação.

## Estrutura do projeto

```text
specs/001-sessoes-isolamento/
  spec.md  plan.md  research.md  data-model.md  quickstart.md  tasks.md
  contracts/api.md  contracts/runtime-tools.md
src/aurora/
  __init__.py  config.py  api.py  schemas.py  cli.py
  storage/database.py  storage/schema.py  storage/seed.py
  storage/identity.py  storage/queries.py
  runtime/app.py  runtime/service.py  runtime/sessions.py  runtime/events.py
  agents/principal.py  agents/reservas.py  agents/visitantes.py
  tools/context.py  tools/reservas.py  tools/visitantes.py
  api_routes/sessoes.py  api_routes/verificacao.py
scripts/check_model.py
docs/arquitetura.md  docs/operacao.md  docs/validacao/001-sessoes.md
pyproject.toml  uv.lock  .python-version  .env.example  .gitignore
var/aurora.sqlite3  var/adk.sqlite3  # runtime, ignorados
```

Um pacote, duas bases locais com responsabilidades distintas e nenhuma infraestrutura externa. `cli.py` suporta subida em 001; restauração explícita completa fica em 005. `check_model.py` valida acesso ao modelo e uma chamada de função simples sem registrar credenciais; não afirma quotas ativas. O pacote e esses arquivos ainda são destinos de implementação, não código existente.

## Rastreabilidade e estratégia de entrega

US1 cobre FR-001–FR-005, FR-009–FR-012 e SC-001/SC-003/SC-004. US2 cobre FR-006/FR-008 e SC-002/SC-004. US3 cobre FR-007–FR-011 e SC-003, usando a base durável desde a fundação. O mapeamento exato de tarefas está em tasks.md e no relatório final. A primeira entrega demonstrável é US1 completa com duas consultas especializadas e isolamento; a spec só termina com US2 e US3 verificadas. Validação integral de 15 passos e README final pertencem à 005.

## Controle de complexidade

Sem violações constitucionais ou exceções. Não duplicar histórico em outro journal; ADK é a fonte canônica dos eventos, e o repositório de identidade é a fonte canônica da autorização. Falha de compatibilidade deve ser resolvida na implementação e registrada como bloqueio de aceite até o fluxo real funcionar.
