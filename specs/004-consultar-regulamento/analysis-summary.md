# Resultado da preparação e análise:004 regulamento

**Data**:2026-10-23. **Estado final**: artefatos de planejamento/tarefas consistentes e prontos para implementação; produto/API/modelo não implementados nem validados nesta execução.

## Procedimento e artefatos

Aplicadas as skills locais `speckit-plan` → `speckit-tasks` → `speckit-analyze`. Executados setup-plan, setup-tasks e check-prerequisites com `--json --require-spec --require-tasks --include-tasks` para análise; sempre `SPECIFY_FEATURE_DIRECTORY` absoluto da004 e `SPECIFY_FEATURE_NO_PERSIST=1`. Branch Git continua `dev`; seletor local não persistido. `.specify/extensions.yml` não existe, portanto nenhum hook before/after registrado nas três etapas.

Gerados [plano](plan.md), [pesquisa](research.md), [modelo](data-model.md), [contrato](contracts/regulamento.md), [guia manual](quickstart.md) e [tarefas](tasks.md). Este resumo foi escrito **após** a análise, em etapa documental separada; análise não gravou arquivos. Correções já estavam expressamente autorizadas pelo usuário e foram feitas fora da operação read-only, sem nova solicitação de aprovação.

## Specification Analysis Report — rodada inicial

| ID | Categoria | Severidade | Localização inicial | Resumo | Correção recomendada/aplicada depois da análise |
| --- | --- | --- | --- | --- | --- |
| I1 | Inconsistência técnica | HIGH | plan.md:40, data-model.md:13, tasks.md:17 | Scope exigia invocação antes de o SDK criar invocation_id da execução nova | Usar nonce aleatório próprio da execução HTTP, distinto do invocation_id ADK; instalar scope só ao redor do Runner correspondente e resetar em finally. Não passar ID de retomada para fabricar execução nova. Propagado a plano/modelo/contrato/pesquisa/guia/tarefas |
| I2 | Subespecificação da seleção | MEDIUM | tasks.md:36 e quickstart.md Q2 versus plan.md:39 | Tarefa/guia exigiam que comandos topics/path/tool não autorizassem tema, mas política não estava explícita nos demais artefatos | Alinhar política conservadora: comandos técnicos não são pergunta temática; dúvida na separação pede esclarecimento sem trecho, sem depender de query/tema do LLM |

Nenhuma violação constitucional, tarefa sem requisito ou duplicação material. Cobertura inicial13/13.

## Specification Analysis Report — reanálise final

| ID | Categoria | Severidade | Localização | Resultado | Próximo passo |
| --- | --- | --- | --- | --- | --- |
| — | — | — | spec/plan/tasks e artefatos derivados | Zero inconsistências remanescentes identificadas no escopo documental | Implementar tarefas e executar gates manuais |

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
| --- | --- | --- | --- |
| FR-001 | Sim | T003,T004,T006–T008,T010,T011,T021 | Fonte real e referência estrutural |
| FR-002 | Sim | T003–T005,T007,T011–T014,T019,T021 | Seleção em código antes de materializar trechos |
| FR-003 | Sim | T001,T008,T013,T014,T019,T021 | Instruções sem regulamento |
| FR-004 | Sim | T006–T010,T021 | Domingo20h,art22II |
| FR-005 | Sim | T013,T014,T016,T017,T019,T021 | Todos eventos integrais,sem filtragem posterior |
| FR-006 | Sim | T005,T007,T009,T015,T017,T018,T020,T021 | Leitura sem efeito;preserva pendências |
| FR-007 | Sim | T003,T005,T007,T009,T011,T012,T014,T020,T021 | Fallback conservador/sem norma inventada |
| FR-008 | Sim | T001,T003,T005,T015–T018,T020,T021 | Identidade,durabilidade,retorno/continuidade |
| FR-009 | Sim | T002–T005,T011,T012,T014,T016,T020,T021 | Fonte imutável,injecção sem ampliar seleção |
| SC-001 | Sim | T010,T021 | Validação manual de resposta/fonte |
| SC-002 | Sim | T014,T021 | Inspeção de eventos e contexto |
| SC-003 | Sim | T017,T021 | Snapshots de negócio/identidade/pendências |
| SC-004 | Sim | T017,T021 | JSON integral antes/depois do restart |

**Constitution Alignment Issues**:nenhuma remanescente. **Unmapped Tasks**:nenhuma.

**Métricas finais**:9FR+4SC=13 itens;21tarefas;100% com cobertura;ambiguidades remanescentes0;duplicações0;críticos0;altos0;médios0;baixos0. US1=5tarefas(P1),US2=4(P1),US3=4(P2);setup2,fundação3,acabamento3;2tarefas[P] independentes de documentação. Nenhuma tarefa de produto marcada concluída.

## Verificações realizadas e limites

Checados IDsT001–T021 sequenciais/únicos,checklist/labels/caminhos em todas tarefas,mapeamentoFR/SC completo,links locais e ausência de placeholders. Conferido art22II da fonte local:domingo/feriado9h–20h. Pesquisa local e stack001–003 reaproveitadas;sem incógnita nova ou agente auxiliar necessário.

Mecanismos desenhados:parser fora do contexto;catálogo determinístico sobre POST atual;tool sem query/tema/path LLM;scope de sessão+nonce próprio;fallback conservador para tema vago,ausência e pedidos indiscriminados;terceiro especialista;histórico integral e persistência herdados. “E aos domingos?” sem assunto explícito pede esclarecimento,não reutiliza state livre nem exige NLP ilimitado.

**Gates ainda não executados**:uv sync/API real/Gemini/limites ativos,Q1–Q3,eventos reais,isolamento e JSON após restart,efeitos/pendências preservados e regressão de confirmações com nova topologia/autor antes/depois do restart. Confirmar com DatabaseSessionService continua risco operacional herdado;200 sem efeito real falha.005 repetirá os15 passos completos e entrega final.

## Next Actions

Pode seguir para `speckit-implement` da004 após001 funcional;T018 requer002/003 integradas. MVP=setup/fundação+US1;aceite completo dependeUS2/US3 e gates reais. Não há nova remediação documental pendente a aprovar;cumprir somente os artefatos não demonstra funcionalidade implementada.
