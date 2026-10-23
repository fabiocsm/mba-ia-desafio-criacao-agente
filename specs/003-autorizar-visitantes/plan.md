# Plano de implementação: autorização de visitantes

**Branch Git**: `dev` | **Data**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Diretório selecionado**: `specs/003-autorizar-visitantes`. O script resolve BRANCH como identificador da feature; isso não muda a branch Git. Dependências: artefatos e futura implementação das specs [001](../001-sessoes-isolamento/plan.md) e [002](../002-reservas-confirmacoes/plan.md).

## Resumo

Adicionar `autorizar_visitante` ao especialista de visitantes já existente. A tool prepara proposta com nome/data congelados e identidade canônica, pede confirmação nativa ADK e só grava o acesso na reentrada autorizada pelo Runner. Reutilizar integralmente o coordenador 002: decisão exclusiva da rota, consumo e efeito em uma transação, despacho durável e replay 409. A leitura própria e a rota administrativa já pertencem à 001.

## Contexto técnico

- **Linguagem e dependências**: Python >=3.12, uv, `google-adk==2.2.0`, FastAPI/Uvicorn, SQLAlchemy/aiosqlite, Pydantic. Manter `pyproject.toml`/`uv.lock` herdados; não trocar versões nesta extensão.
- **Runtime**: App `aurora` resumível, Runner, DatabaseSessionService; principal `aurora_principal` com especialistas reservas e visitantes, todos modo chat; parent transfer permitido e peers bloqueados nos especialistas. Confirmar flags efetivos ao implementar.
- **Armazenamento**: negócio em `var/aurora.sqlite3`; sessões e eventos canônicos em `var/adk.sqlite3`, caminhos estáveis. Sem memória como autoridade, journal espelho ou commit distribuído. `dados/` somente leitura.
- **Modelo**: manter configuração Gemini da [pesquisa 001](../001-sessoes-isolamento/research.md), sem nova escolha. Acesso, limites ativos e chamadas reais continuam gates operacionais, não verificados nesta preparação; nunca ler/expor a chave em evidências.
- **Plataforma e escala**: API local Linux/macOS em `http://localhost:8000`, um worker, não streaming, mesma sessão serializada e transações de escrita curtas. Considerar dezenas de chamadas na avaliação, sem SLA/quota inventados. Nenhum serviço local adicional.
- **Validação**: roteiro manual reproduzível; sem suíte/evals obrigatórios. Cobrir FR-001–FR-011, SC-001–SC-004 e passos 3, 11, 13, 15 afetados; 005 repete os 15 passos completos.
- **Escopo**: autorização de acesso e consulta própria, sem catraca, documento civil, horários, capacidade ou deduplicação de propostas distintas por nome/data. Não implementar aplicação nesta fase de artefatos.

## Verificação da constituição

Gates avaliados antes da pesquisa e novamente após o desenho; sem exceção normativa.

| Princípio | Mecanismo planejado | Evidência requerida |
| --- | --- | --- |
| I — confirmação | Ação registrada no coordenador 002; request_confirmation nativa; rota CAS decide; callback só executa dentro do consumo transacional | Nome/data na pendência, zero visita antes, uma após; negar/replay/inválido/alheio; autor solicitante e efeito real após restart |
| II — identidade | SessionIdentity por tool_context.session.id; nenhuma identidade no schema LLM; SELECT próprio antes de materializar | Troca textual de apartamento sem efeito cruzado nem dados alheios em resposta/tool/evento |
| III — persistência | Proposta/decisão/despacho e visitante duráveis; proposta_id único no registro novo; resultado idempotente | Mesma sessão, eventos iguais após GET/restart, aprovação recuperada, nova mensagem e replay 409 |
| IV — rastreabilidade | Append ADK integral da 001, calls/results/actions e ordem; nenhum regulamento carregado nesta extensão | Eventos completos, sem filtragem posterior ou conteúdo de terceiros |
| V — exclusividade | Preservar índice/transações de reservas da 002; callback visitante usa a mesma conexão de negócio | Regressão de reservas pagas/gratuitas, cancelamento e disputa sem alteração da proteção |
| Stack/contrato/segredos | Reutilizar uv, ADK pin, App/Runner e rotas existentes; sem nova rota/consentimento | Contratos e 404/409/200 corretos; sem segredo em artefatos |

**Gate bloqueante da implementação**: a limitação documental de confirmação com DatabaseSessionService persiste. Os artefatos 001/002 especificam diagnóstico e eventual fallback restrito de seleção do agente; não provam funcionamento. Provar especialista visitantes como autor, reentrada nativa, resultado e visita real com SQLite, antes/depois de restart. HTTP 200 isolado não passa. Seleção, persistência ou serialização que falhem precisam ser corrigidas antes do aceite, sem abandonar Runner/mecanismo nativo.

## Fluxo e fronteiras

1. Principal transfere ao especialista visitantes para autorizar/consultar. Tool recebe somente nome/data e ToolContext injetado; falta de informação pede esclarecimento, data inválida não prepara ação. Identidade vem exclusivamente do banco canônico da sessão.
2. `autorizar_visitante` prepara `acao=autorizar_visitante` com nome/data imutáveis e vínculo à sessão. Chama request_confirmation e retorna sem autorização. Adapter 002 persiste evento completo, correlaciona ID público, ID original da tool e ID nativo novo, invocation/author/branch; só então publica pendência.
3. A rota comum verifica sessão primeiro (404), decide pendência própria via CAS e grava despacho. Mensagem “confirmado” não decide. ID inválido/alheio/respondido retorna 409 sem retomar Runner, consumir outra pendência ou alterar visitantes. Booleano estrito conforme contrato.
4. Runtime 002 envia FunctionResponse `adk_request_confirmation` com ID nativo e invocation original pelo Runner no autor canônico, ContextVar confiável isolada/resetada. A tool reentra, confere correlação e decisão persistidas, nunca troca parâmetros pelo payload ou argumentos reexecutados.
5. Coordenador abre a transação curta de negócio e chama executor registrado de visitante com a **mesma conexão/transação**. Aprovação insere visitante com proposta_id; consumo da decisão, resultado e efeito são um commit. Negação consome e salva resultado sem inserir. Executor não abre transação nem commit próprios, não recebe apartamento do LLM e não decide consentimento. Reentrada técnica consumida apenas devolve resultado salvo.
6. Após eventos persistidos e despacho concluído, responder 200 com string e todas pendências atuais, inclusive reservas; uma resposta não consome outra proposta. Duplicatas de propostas diferentes são permitidas; somente a mesma confirmação tem efeito único.
7. Recuperação idêntica à 002: startup reconcilia metadados, GET é leitura, ambos sem Runner/eventos novos. Despacho já decidido incompleto só recupera em nova POST mensagens antes do texto; replay 409 nunca dispara recuperação. Concluir invocation já terminada exige conferir resultado/eventos. Dois bancos não têm atomicidade conjunta; conservar histórico anterior sem reescrever. Após 200 não resta despacho incompleto.

## Fases e estrutura

Fase 0: [research.md](research.md), decisões herdadas sem nova incógnita. Fase 1: [data-model.md](data-model.md), [contrato](contracts/visitantes.md), [quickstart.md](quickstart.md). Fase 2: [tasks.md](tasks.md), setup/fundação → US1 → US2 → US3 → acabamento. Análise somente leitura e resumo registrado em etapa documental posterior.

```text
specs/003-autorizar-visitantes/
  spec.md plan.md research.md data-model.md quickstart.md tasks.md
  contracts/visitantes.md analysis-summary.md
src/aurora/
  storage/schema.py storage/visitantes.py storage/confirmacoes.py
  tools/visitantes.py tools/context.py agents/visitantes.py
  runtime/app.py runtime/confirmacoes.py runtime/runner.py
  runtime/sessions.py runtime/service.py
  api_routes/confirmacoes.py api_routes/sessoes.py api_routes/verificacao.py
  schemas.py
docs/arquitetura.md docs/operacao.md docs/validacao/003-visitantes.md
```

Arquivos de código são destinos futuros; reutilizar os já planejados. Não criar outro coordenador ou serviço de sessão. MVP: US1 após 001/002 funcionais; US2 e US3 são obrigatórias para aceite completo. Complexidade adicional limita-se à correlação proposta→visitante; sem violação constitucional ou exceção a justificar.
