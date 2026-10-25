# Plano de implementação: Reservas com confirmação e exclusividade

**Branch Git**: `dev` | **Data**: 2026-10-23 | **Spec**: [spec.md](spec.md)
**Diretório**: `specs/002-reservas-confirmacoes`, selecionado por ambiente sem persistir seletor. O nome retornado pelo script não cria branch.
**Estado**: desenho concluído; aplicação, confirmação real e concorrência ainda não executadas.

## Resumo

Acrescentar ao especialista `reservas` operações gratuitas, cancelamento próprio e propostas pagas. A aprovação usa confirmação nativa do ADK e retoma o Runner no agente solicitante. SQLite mantém parâmetros congelados, decisão exclusivamente sistêmica e resultado consumido; uma transação une consumo, código novo e efeito. Índice único parcial protege área/data ativa no instante da gravação. A spec 003 reutiliza o ciclo para visitantes.

## Contexto técnico

- **Linguagem/versão**: Python >=3.12 e uv; pacote `src/aurora`, herdado da 001.
- **Dependências**: `google-adk==2.2.0`, FastAPI/Uvicorn, SQLAlchemy/aiosqlite e Pydantic; manter pin exato e uv.lock. Nenhum serviço local adicional.
- **Modelo**: configuração Gemini definida na [pesquisa 001](../001-sessoes-isolamento/research.md#r 5--modelo-gemini-e-gate-operacional-de-quotas). Antes do runtime, checar acesso e limites ativos do projeto no AI Studio; não presumir quota nem disponibilidade. Nenhuma nova seleção nesta spec.
- **Armazenamento**: negócio e pendências em `var/aurora.sqlite3`; eventos/sessão ADK em `var/adk.sqlite3`, caminhos estáveis. `dados/` somente leitura; var ignorado.
- **Plataforma/tipo**: API local Linux/macOS em localhost:8000, um worker e geração não streaming. Mesma sessão serializada; sessões distintas executam modelos concorrentemente. Lock curto de escrita de negócio, nunca durante Runner/Gemini.
- **Validação**: manual reproduzível em [quickstart.md](quickstart.md); sem suíte/evals obrigatórios. Dezenas de chamadas previstas no avaliador; sem SLA ou capacidade inventados.
- **Escopo**: FR-001–FR-016 e SC-001–SC-005. Sem pagamento/estorno, UI, autenticação real, deploy ou novos bloqueios de data, antecedência, horário e capacidade.

## Verificação da constituição

Gates verificados antes da pesquisa e após o desenho; não há exceções normativas.

| Regra | Mecanismo de código planejado | Evidência exigida |
| --- | --- | --- |
| I — confirmação sistêmica | Rota decide; tool nativa pede/retoma; parâmetros imutáveis; consumo+efeito na mesma transação | US2: negar, aprovar, replay 409, ID alheio/inválido, consentimento textual sem efeito, aprovação após restart e agente solicitante correto |
| II — identidade e sigilo | SessionIdentity canônica; SQL filtrado antes de materializar; tools sem apartamento; agenda EXISTS; cancelamento próprio | US1/US3: rotas reais e eventos completos nos passos 4/10, inclusive ausência do número 302 isolado nas respostas do passo 10 |
| III — durabilidade e códigos | Pendência/decisão/resultado em disco, recuperação do despacho, ledger e contador duráveis; tombstones de cancelamento | US2/US3: reinício antes/depois de aprovação, prefixo de eventos igual, códigos não reutilizados |
| IV — rastreabilidade | Eventos ADK canônicos completos e ordenados, sem compactação/filtro; nenhum regulamento nesta spec | Conferir function calls/results/author/invocation no GET; repetir regressões 001 |
| V — exclusividade atômica | UNIQUE(area,data) WHERE cancelada=0; transação curta trata conflito como indisponível | US3: duas aprovações 200, exatamente uma reserva, recusa sem dados da vencedora |
| Stack/contrato/segredos | Herdar uv, ADK pin, App/Runner/SQLite; sexta rota no contrato existente | Instalação/regressões e inspeção sem expor chave; 005 fará 15 passos integrais |

A documentação oficial declara limitação do DatabaseSessionService para confirmação. O desenho mantém o mecanismo nativo e um fallback estreito para seleção do agente, descritos em [research.md](research.md). A comprovação com SQLite real e reinício é gate bloqueante da implementação, não resultado desta preparação. Não declarar conclusão funcional se houver HTTP 200 sem efeito ou se faltar a autoria correta.

## Fluxo de execução e recuperação

1. A tool `reservar_area(area,data,tool_context)` resolve identidade canônica, valida cadastro/data e obtém taxa real. Taxa zero executa imediatamente a transação de reserva, sem confirmação. Taxa positiva grava proposta imutável com ID público e correlação original, chama `request_confirmation` e devolve apenas pendência; nenhuma reserva efetiva é inserida.
2. Adapter observa o evento nativo persistido `adk_request_confirmation`, correlaciona seu ID novo com o ID da tool original e grava `author`/`invocation_id`. A proposta só vira pendente pública após correlação durável. Reconciliar evento persistido sem correlação no restart; publicação não depende apenas de eventos yielded. Não duplicar journal ADK nem alterar eventos anteriores.
3. `POST /confirmacoes` primeiro verifica sessão; sob lock da sessão, faz compare-and-set de pendente para decidida e persiste booleano estrito, instante e despacho a recuperar. Só essa rota grava decisão. ID alheio, ausente ou já decidido recebe 409 sem eventos de retomada/efeito. Listas consultam somente pendências públicas ainda sem decisão, incluindo todas as demais da sessão.
4. A rota monta `FunctionResponse(name="adk_request_confirmation", id=native_confirmation_id, response={"confirmed": decisão})` e executa Runner com invocation original. Contexto confiável por ContextVar contém correlação da decisão canônica; cliente/modelo não escolhe agente/identidade/parâmetros. O processador ADK retoma a tool original no especialista. Ver [contrato](contracts/confirmation-runtime.md).
5. Na reentrada, a tool confere identidade, IDs e decisão persistida; não confia no booleano/payload em tool_context sozinho. Em `BEGIN IMMEDIATE`, consome a decisão e insere reserva ou recusa por ocupação, ou registra negação sem efeito. Preserva resultado próprio serializável. Parâmetros executados são os congelados no banco. Consumo e efeito são um único commit; chamada repetida recupera resultado sem duplicar a gravação.
6. Ao concluir Runner e persistir eventos, marca despacho concluído e só então retorna 200 com texto e todas pendências restantes. Indisponibilidade é resultado de negócio 200; não gera 409 nem dados do ocupante. Não manter transação aberta durante modelo. Lock curto de escrita e busy_timeout previnem disputa local virando erro de servidor; índice continua autoridade atômica.
7. Dois bancos não têm commit distribuído. Queda após decisão, efeito ou evento é tratada por recuperação do despacho durável: startup apenas reconcilia metadados sem criar eventos; uma nova POST de mensagens na mesma sessão recupera primeiro o despacho, reenviando a mesma resposta nativa pelo Runner, no agente original. A tool devolve resultado persistido se já consumido; não cria novo efeito. Preservar todos eventos realmente gravados, mesmo se retomada técnica acrescentar eventos; nunca apagar/reescrever histórico. Se Runner já completou a invocation, verificar eventos e resultado antes de encerrar despacho, sem forçar nova execução. Depois de HTTP 200 o despacho já está concluído e não é retomado no restart. Startup e GET nunca invocam Runner nem acrescentam eventos. Replay HTTP sequencial continua 409 mesmo após falha/restart e não dispara recuperação; apenas uma nova POST de mensagens pode recuperar despacho decidido incompleto antes de processar seu texto. Falha técnica não pode ser anunciada como sucesso sem comprovação; corrigir e repetir gate.
8. Cancelamento usa código próprio ou resolução por área/data em SQL já filtrado pelo apartamento. Atualiza `cancelada=1`, sem confirmação, preservando código e liberando o par área/data. Ausente/alheio produz recusa genérica equivalente, sem ler a reserva alheia.

## Fases e artefatos

Fase0: [research.md](research.md), decisões fechadas e pesquisa auxiliar encerrada. Fase 1: [data-model.md](data-model.md), [HTTP](contracts/api.md), [tools/retomada](contracts/confirmation-runtime.md) e [quickstart.md](quickstart.md). Fase 2: [tasks.md](tasks.md), setup → fundação → US1 → US2 → US3 → acabamento. Nenhuma implementação é produzida por estes artefatos.

## Estrutura do projeto

```text
specs/002-reservas-confirmacoes/
  spec.md plan.md research.md data-model.md quickstart.md tasks.md
  contracts/api.md contracts/confirmation-runtime.md analysis-summary.md
src/aurora/
  storage/schema.py storage/reservas.py storage/confirmacoes.py
  storage/codigos.py storage/database.py
  tools/reservas.py tools/context.py
  runtime/confirmacoes.py runtime/runner.py runtime/sessions.py runtime/service.py
  agents/reservas.py runtime/app.py schemas.py api.py
  api_routes/confirmacoes.py
  api_routes/sessoes.py api_routes/verificacao.py
  cli.py
docs/arquitetura.md docs/operacao.md docs/validacao/002-reservas.md
```

Reutilizar arquivos e identidade da 001; arquivos novos são destinos planejados. Não criar scripts de teste obrigatórios. A extensão 003 registra novo executor de ação no mesmo coordenador, sem nova rota ou novo critério de consentimento.

## Estratégia e complexidade

MVP é US1 com persistência real e código não reutilizado; US2 entrega confirmação reutilizável; US3 comprova disputa e sigilo. Todas P1 precisam ser concluídas para aceitar a spec. A única adaptação privada candidata é `_find_agent_to_run` fixada ao ADK 2.2.0, quando a seleção nativa divergir do solicitante canônico; não substituir processador de confirmação, sessão durável ou Runner. Justificativa técnica e gates em research/contrato. Não há violação constitucional a justificar; modelo e quota são gates operacionais herdados, sem fatos presumidos.
