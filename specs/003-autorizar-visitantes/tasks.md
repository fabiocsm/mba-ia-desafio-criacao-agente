# Tarefas: autorização de visitantes

**Entrada**: [spec](spec.md), [plano](plan.md), [pesquisa](research.md), [modelo](data-model.md), [contrato](contracts/visitantes.md), [validação](quickstart.md). Dependências de produto: 001 e 002 implementadas e seus gates aprovados. Estas caixas representam trabalho futuro; nenhum efeito/runtime foi validado nesta preparação.

**Validação**: manual reproduzível, sem suíte automatizada/evals obrigatórios. Caminhos relativos à raiz. IDs locais à spec; [P] somente para arquivos distintos e dependências anteriores já concluídas. Campos com constraints repetem literalmente C301–C304; regras herdadas não são dispensadas.

## Fase 1 — Setup

Objetivo: confirmar a base compartilhada e os gates operacionais antes da extensão.

- [ ] T001 Conferir Python>=3.12/uv e pin google-adk==2.2.0 em pyproject.toml/uv.lock, topologia/App/serviço da 001 e conclusão funcional da 002; registrar pendências e evidências em docs/validacao/003-visitantes.md, sem alegar runtime aprovado pelos artefatos (FR-004, FR-006, FR-011).
- [ ] T002 Conferir acesso ao modelo e limites ativos no projeto AI Studio conforme pesquisa 001, sem ler/expor segredo em evidências; registrar data/modelo/margem para dezenas de chamadas e confirmar caminhos estáveis dos dois SQLite em docs/validacao/003-visitantes.md (FR-006, FR-011).

## Fase 2 — Fundação

Objetivo: esquema durável e ponto único de consumo; bloqueia todas as histórias.

- [ ] T003 Estender visitante existente e migração em src/aurora/storage/schema.py: “id é obrigatório, único e gerado pelo sistema; apartamento, nome e data são obrigatórios; nome não pode ser vazio; data usa AAAA-MM-DD e é uma data civil válida”; “proposta_id é nulo para dados iniciais e obrigatório para novas autorizações; proposta_id não nulo é único e referencia proposta da mesma sessão e ação autorizar_visitante”; preservar seed/dados e não criar UNIQUE nome/data (FR-001, FR-004, FR-006).
- [ ] T004 Confirmar e completar o ponto de registro de executor em src/aurora/runtime/confirmacoes.py e src/aurora/storage/confirmacoes.py herdados: somente ações permitidas, transação/conexão recebida e identidade/proposta canônicas, sem novo coordenador ou rota; preservar C207–C211 e correlação ID original/nativo da 002 (FR-002–FR-007).

## Fase 3 — US1: revisar e aprovar entrada (P1, MVP)

Objetivo: pendência nativa com detalhes e efeito único após aprovação. Critério independente: frase do passo 11 produz zero visita antes e delta um após200, com autoria correta; replay 409 não duplica.

- [ ] T005 [P] [US1] Implementar fase inicial de autorizar_visitante em src/aurora/tools/visitantes.py: nome/data somente no schema LLM e ToolContext injetado; “nome e data são obrigatórios no snapshot de autorizar_visitante e imutáveis; apartamento executado vem da SessionIdentity imutável vinculada à proposta”; dados ausentes pedem esclarecimento, data civil inválida não prepara ação; request_confirmation nativa sem efeito, sem aceitar consentimento textual (FR-001–FR-003).
- [ ] T006 [P] [US1] Implementar executor em src/aurora/storage/visitantes.py: “nova autorização só é inserida com decisão canônica confirmada; consumo da decisão, resultado e inserção usam a mesma conexão e transação; negação não insere visitante”; INSERT com proposta_id/identidade/snapshot canônicos, resultado próprio e nenhum commit/transação independente (FR-004, FR-008).
- [ ] T007 [US1] Registrar executor e integrar reentrada da tool em src/aurora/runtime/confirmacoes.py e src/aurora/tools/visitantes.py; conferir decisão/correlação canônicas no consumo002, executar snapshot imutável, reaproveitar resultado já consumido e não expor executor como tool (FR-002–FR-005).
- [ ] T008 [US1] Adicionar autorização às tools do especialista em src/aurora/agents/visitantes.py e conferir registro/flags em src/aurora/runtime/app.py: modo chat, parent transfer permitido, peers bloqueados, App resumível; preservar principal e especialista reservas (FR-004, FR-009).
- [ ] T009 [US1] Integrar projeção autorizar_visitante em src/aurora/schemas.py e src/aurora/runtime/confirmacoes.py com id/acao/detalhes nome/data, string resposta e todas pendências atuais; não incluir metadados internos nem alterar rota/envelope comuns (FR-003, FR-007, FR-011).
- [ ] T010 [US1] Executar US1 do quickstart.md pela API com SQLite persistido: frase completa do avaliador, GET direto antes/depois, confirmação 200 e replay 409; registrar delta zero/um e calls/results/IDs/author/invocation completos em docs/validacao/003-visitantes.md; diagnosticar e corrigir seleção/retomada na integração herdada se falhar (FR-002–FR-005, FR-009, SC-001).
- [ ] T011 [US1] Validar falta de nome/data, “confirmado” no texto, mudança de argumentos após proposta e duas propostas distintas com mesmo nome/data; registrar que snapshot original é executado e que apenas replay do mesmo ID é bloqueado em docs/validacao/003-visitantes.md (FR-001–FR-005).
- [ ] T012 [US1] Verificar e ajustar consulta própria em src/aurora/tools/visitantes.py e rota direta herdada em src/aurora/api_routes/verificacao.py para refletir autorizações reais com nome/data, mantendo filtro canônico antes de materializar e lista vazia sem fallback (FR-008, FR-009).

## Fase 4 — US2: negar e impedir consentimento indevido (P1)

Objetivo: negação e IDs incorretos sem efeito, identidade imutável e isolamento entre propostas. Critério independente: snapshots iguais após negar/replay/ID inválido/alheio e nenhum dado de302 em 101.

- [ ] T013 [P] [US2] Conferir e completar em src/aurora/tools/visitantes.py a recusa de troca de apartamento pelo texto/state/payload e acesso só por resolve_identity; nenhuma leitura administrativa ou materialização alheia e nenhuma negação que apague autorização existente (FR-001, FR-008–FR-010).
- [ ] T014 [P] [US2] Verificar e ajustar src/aurora/api_routes/confirmacoes.py para identidade da sessão antes do ID, CAS e booleano estrito herdados; ID inválido/alheio/respondido409 sem Runner/efeito e sessão inexistente404; não criar regra exclusiva de consentimento para visitantes (FR-005, FR-011).
- [ ] T015 [US2] Validar negação 200, reenvio 409, ID inexistente e ID de outra sessão 409, preservando autorização anterior e pendência alheia; registrar snapshots antes/depois em docs/validacao/003-visitantes.md (FR-004, FR-005, SC-002).
- [ ] T016 [US2] Validar tentativa101→302, consultas próprias e conteúdo integral de resposta/tool/eventos; GET administrativo deve provar zero nova autorização 302 e Marina Duarte intacta, sem trazer seus dados à sessão 101; registrar em docs/validacao/003-visitantes.md (FR-008–FR-010, SC-004).
- [ ] T017 [US2] Validar visita e reserva paga pendentes juntas, lista completa e resposta de um ID preservando o outro, além de 404 em todas rotas com sessão inexistente e rejeição de booleano string sem decisão; registrar em docs/validacao/003-visitantes.md (FR-005, FR-007, FR-011).
- [ ] T018 [US2] Conferir src/aurora/runtime/sessions.py e eventos de autorização/negação: append integral herdado, ordem imutável e calls/results/actions completos; corrigir ausência na origem sem filtrar GET/eventos e registrar evidência em docs/validacao/003-visitantes.md (FR-009, SC-002, SC-004).

## Fase 5 — US3: persistir autorizações e pendências (P2)

Objetivo: mesma sessão/efeito/decisão sobrevivem a restart; critério independente: pendência anterior aprovada após reinício gera uma visita, outro reinício conserva visita/eventos e replay 409.

- [ ] T019 [US3] Verificar persistência do registro e da correlação de autorizar_visitante em src/aurora/storage/visitantes.py e src/aurora/storage/confirmacoes.py: campos/snapshot imutáveis e C207–C211, sem reset ao iniciar; corrigir divergências herdadas antes do aceite (FR-006).
- [ ] T020 [US3] Conferir recuperação em src/aurora/runtime/service.py e src/aurora/runtime/confirmacoes.py para visitante: startup só reconcilia metadados, GET não chama Runner; nova POST mensagens retoma despacho decidido incompleto antes do texto, replay 409 nunca recupera; ContextVar confiável isolada/resetada, agente original e resultado consumido reutilizado (FR-004–FR-006).
- [ ] T021 [US3] Executar dois reinícios do quickstart.md com bancos reais: pendência anterior aprovada, visita preservada, GET/eventos idênticos antes de nova interação, replay 409 e mensagem200 acrescentando eventos sem mudar prefixo; registrar autoria/topologia/flags/App/ADK/serviço e efeito em docs/validacao/003-visitantes.md (FR-006, FR-009, SC-003).
- [ ] T022 [US3] Executar falhas controladas depois de decidir e depois do efeito antes dos eventos finais; comprovar recuperação somente por nova POST mensagens, um efeito total, replay 409 sem Runner e despacho concluído antes de 200; corrigir integração herdada se necessário e registrar em docs/validacao/003-visitantes.md (FR-004–FR-006, SC-003).
- [ ] T023 [US3] Documentar em docs/operacao.md que reinício conserva visitantes/decisões/eventos e não restaura; alinhar remoção explícita das autorizações com FK/propostas e invalidação de sessões/pendências na restauração 005, preservando ledger de reservas (FR-006).

## Fase 6 — Acabamento transversal

Objetivo: documentação coerente e regressões sem ampliar escopo.

- [ ] T024 [P] Documentar em docs/arquitetura.md papel/acionamento do especialista visitantes e motivo da separação, snapshot, identidade, executor sem commit próprio e garantias independentes do LLM, com referências reais ao código implementado (FR-001, FR-004, FR-009, FR-010).
- [ ] T025 [P] Atualizar docs/operacao.md com comando de subida herdado, variáveis apenas por nome, modelo/limites como gates e validação da confirmação persistida, sem substituir README nem exigir novos serviços/suíte/evals (FR-006, FR-011).
- [ ] T026 Executar quickstart.md e regressões 001/002 afetadas, incluindo reservas gratuitas/pagas/cancelamento/disputa e sigilo exato dos passos 3/4/10; confirmar dados/ intactos, registrar falhas reais ou todos os gates em docs/validacao/003-visitantes.md e encaminhar repetição dos 15 passos à 005 (FR-001–FR-011, SC-001–SC-004).

## Dependências e paralelismo

```text
001 + 002 funcionais → T001 → T002 → T003 → T004
→ US1 (T005/T006 → T007 → T008 → T009 → T010 → T011 → T012)
→ US2 (T013/T014 → T015 → T016 → T017 → T018)
→ US3 (T019 → T020 → T021 → T022 → T023)
→ T024/T025 → T026
```

A ordem é deliberadamente incremental: US2 e US3 validam autorização entregue na US1. Cada história tem cenário isolado reproduzível, mas não é implementável antes da base compartilhada. T004 estabelece contrato do executor; T006 o implementa e T007 o registra.

Exemplo US1: T005 (`tools/visitantes.py`) e T006 (`storage/visitantes.py`) podem avançar juntas após T004, só integrar em T007. Exemplo US2: T013 (`tools/visitantes.py`) e T014 (`api_routes/confirmacoes.py`) podem avançar juntas após US1. US3 não tem paralelismo seguro: recuperação precede evidência e todas as evidências usam o mesmo arquivo. Acabamento: T024 e T025 em arquivos distintos após T023; T026 aguarda ambos. Não paralelizar validações que alterem os mesmos bancos.

## Mapa de cobertura

| Requisito | Tarefas |
| --- | --- |
| FR-001 | T003, T005, T011, T013, T024, T026 |
| FR-002 | T004, T005, T007, T010, T011, T026 |
| FR-003 | T004, T005, T009, T010, T026 |
| FR-004 | T001, T003, T004, T006, T007, T008, T010, T015, T020, T022, T024, T026 |
| FR-005 | T004, T007, T010, T011, T014, T015, T017, T020, T022, T026 |
| FR-006 | T001, T002, T003, T004, T019–T023, T025, T026 |
| FR-007 | T004, T009, T017, T026 |
| FR-008 | T006, T012, T013, T016, T026 |
| FR-009 | T008, T010, T012, T013, T016, T018, T021, T024, T026 |
| FR-010 | T013, T016, T024, T026 |
| FR-011 | T001, T002, T009, T014, T017, T025, T026 |
| SC-001 | T010, T026 |
| SC-002 | T015, T018, T026 |
| SC-003 | T021, T022, T026 |
| SC-004 | T016, T018, T026 |

## Estratégia e checkpoints

MVP = US1 após gates001/002, com visita real no armazenamento; nenhuma declaração funcional somente pela resposta 200. US2 fecha negação/isolamento, US3 fecha reinício/recuperação, acabamento repete regressões. Todas as histórias e gates são obrigatórios para concluir003;005 conserva aceite integral dos 15 passos. Não executar restore automaticamente nem reduzir a garantia para evitar falha do ADK.

**Contagem**: 26 tarefas; setup2, fundação2, US1=8, US2=6, US3=5, acabamento3; 6 marcadas [P]. Formato obrigatório: checkbox, ID sequencial, rótulo US nas fases de história, caminho concreto e requisito. Constraints C301/C302 em T003, C303 em T005 e C304 em T006 são literais.
