# Tarefas: Reservas com confirmação e exclusividade

**Entrada**: spec, plan, research, data-model, contracts e quickstart de `specs/002-reservas-confirmacoes/`.
**Pré-requisito de implementação**: 001 concluída; **estado atual**: tarefas executadas em 2026-10-23. Branch dev, diretório escolhido explicitamente.
**Validação**: manual reproduzível; não criar suíte/evals obrigatórios. FR/SC referem-se à 002. Constraints entre aspas reproduzem literalmente data-model.md. Caminhos relativos à raiz são destinos de implementação.

## Fase 1 — Setup

- [X] T001 Conferir `pyproject.toml`, `uv.lock` e `src/aurora/runtime/app.py` herdados da 001, mantendo Python>=3.12, uv, google-adk==2.2.0, App resumível, Runner/DatabaseSessionService e um worker; revalidar acesso/limites ativos do modelo conforme `docs/validacao/001-sessoes.md` antes de executar cenários, sem ler/expor chave ou presumir quota (FR-008, FR-011; restrições constitucionais).
- [X] T002 [P] Atualizar `docs/operacao.md` com comandos de subida/reinício e roteiro 002, banco persistente fora de dados/, nenhuma restauração no startup, nenhum serviço auxiliar e política de recuperação somente em nova POST mensagens; após T001 (FR-011, FR-015).
- [X] T003 [P] Preparar registro manual em `docs/validacao/002-reservas.md` com matriz FR/SC, campos para status HTTP/efeitos/eventos/agente/invocation e achados; deixar não executado até evidência real; após T001, independente T002 (FR-014; SC-001–SC-005).

## Fase 2 — Fundação bloqueante

Concluir antes das histórias: dados iniciais preservados, transação curta, códigos duráveis e DTOs comuns. Identidade e eventos já são duráveis desde 001.

- [X] T004 Criar ledger/contador e gerador em `src/aurora/storage/schema.py` e `src/aurora/storage/codigos.py`, impondo “codigo do ledger é obrigatório e único; códigos iniciais, cancelados e emitidos permanecem reservados, inclusive após reinício ou restauração” e “proximo é inteiro maior que os sufixos iniciais e avança atomicamente com a emissão; nenhum código emitido é reutilizado”; inicializar acima do maior sufixo dos códigos seed, reservar iniciais e gerar RSV-{numero} no mesmo commit da reserva; após T001 (FR-005, FR-011; SC-004).
- [X] T005 Estender `src/aurora/storage/schema.py` com “codigo é obrigatório, único e gerado pelo sistema; apartamento e area são obrigatórios e referenciam cadastros; data usa AAAA-MM-DD e é uma data civil válida”, “cancelada é booleano não nulo com default false; cancelar preserva a linha e o codigo; cancelada_em é nulo enquanto ativa e preenchido ao cancelar”, “há no máximo uma reserva ativa por area e data, imposta por índice único parcial WHERE cancelada=0” e “taxa é lida do cadastro, representada exatamente em centavos; taxa zero dispensa confirmação e taxa maior que zero exige confirmação”; migração não apaga seed/tombstones nem dados/; após T004 (FR-001–FR-005, FR-011, FR-013).
- [X] T006 [P] Implementar limite de transação em `src/aurora/storage/database.py`: BEGIN IMMEDIATE, WAL/FK/busy_timeout, serialização curta de escritas locais e tratamento de contenção sem atravessar chamada ao modelo; índice único continua autoridade entre sessões; após T001, independente T004/T005 (FR-002, FR-012, FR-013).
- [X] T007 [P] Estender `src/aurora/schemas.py` com confirmação id e booleano estrito, pendências id/acao/detalhes e envelope resposta string/lista integral segundo `specs/002-reservas-confirmacoes/contracts/api.md`; não aceitar author/apartamento/parâmetros da proposta na confirmação; após T001, independente T004–T006 (FR-006, FR-010, FR-015).

## Fase 3 — US1: Gratuita e cancelamento próprio (P1, MVP)

**Objetivo**: reservar quadra e cancelar somente própria, sem pendência.
**Critério independente**: cancelar 2030-03-09, reservar 2030-04-06, conferir rotas diretas/códigos; tentativa de cancelamento alheio não altera 302 nem revela RSV-4821 em resposta/eventos.

- [X] T008 [US1] Implementar reserva gratuita em `src/aurora/storage/reservas.py` com identidade canônica, taxa real zero, índice atômico e código/ledger no mesmo commit; validar cadastro/data sem bloqueios de passado, antecedência, horário ou capacidade; retorno próprio ou indisponível genérico; após T004–T006 (FR-001–FR-003, FR-005, FR-013; SC-001).
- [X] T009 [US1] Implementar cancelamento e disponibilidade em `src/aurora/storage/reservas.py` com “disponibilidade expõe somente livre ou ocupada; consultas e cancelamentos próprios filtram apartamento antes de materializar dados”; selecionar por código ou área/data somente no apartamento canônico, UPDATE cancelada/timestamp sem apagar registro ou pedir confirmação; tratar ausente/alheio igual sem revelar existência; após T008 (FR-004, FR-013, FR-014; SC-005).
- [X] T010 [US1] Estender `src/aurora/tools/reservas.py` com reservar_area/cancelar_minha_reserva usando `src/aurora/tools/context.py` e contratos, sem argumento apartamento/session_id/taxa/decisão do LLM; tools chamam banco real; até US2, taxa positiva deve recusar capacidade indisponível sem gravar nem simular confirmação; após T008/T009 (FR-001, FR-003, FR-004, FR-014).
- [X] T011 [US1] Registrar tools e atualizar responsabilidade do especialista em `src/aurora/agents/reservas.py`, preservando mode chat/sub_agents/flags e retorno ao principal de 001; instruções não devem ecoar código ou apartamento de terceiros nem anunciar cobrança disponível antes de US2; após T010 (FR-004, FR-013, FR-014).
- [X] T012 [US1] Integrar efeitos e eventos em `src/aurora/runtime/service.py`, `src/aurora/api_routes/sessoes.py` e `src/aurora/api_routes/verificacao.py`: projeção ativa direta, mensagens via Runner, chamadas/resultados integrais, sem alterar histórico passado e sem expor rotas administrativas como tools; após T011/T007 (FR-004, FR-010, FR-014; SC-001, SC-005).
- [X] T013 [US1] Executar US1 do `specs/002-reservas-confirmacoes/quickstart.md` e registrar em `docs/validacao/002-reservas.md` cancelamento próprio/gratuita sem pendências, tentativa alheia sem RSV-4821 em resposta/eventos, preservação da reserva 302 e novo código único; após T012 e gate operacional T001 (FR-001–FR-005, FR-013, FR-014; SC-001, SC-005).
- [X] T014 [P] [US1] Atualizar `docs/arquitetura.md` com tools reais de reserva/cancelamento, predicados de proprietário, índice parcial e códigos duráveis, deixando confirmação como gate da US2; após T011, independente T012/T013 (FR-001–FR-005, FR-013, FR-014).

Checkpoint: MVP observável de operação sem cobrança; nenhuma aprovação fictícia. US2/US3 continuam obrigatórias.

## Fase 4 — US2: Decisão sistêmica da cobrança (P1)

**Objetivo**: proposta paga congelada, decisão consumível e retomada nativa no solicitante, inclusive após restart.
**Critério independente**: pedir/negação, repetir/aprovação, conferir efeitos, replay 409, ID inválido/alheio 409, consentimento textual sem efeito, pendência aprovada após reinício e eventos íntegros.

- [X] T015 [US2] Criar proposta/decisão/despacho em `src/aurora/storage/schema.py` com “id, session_id, acao, parametros_json, original_function_call_id, invocation_id e author são obrigatórios e imutáveis; branch pode ser nulo”, “acao pertence a reservar_area ou autorizar_visitante; fase pertence a preparando ou pendente; native_confirmation_id é obrigatório e único ao publicar pendente”, “parametros_json contém area e data válidas para reservar_area, mais taxa_centavos congelada; autorizar_visitante conterá nome e data na spec 003; nenhum parâmetro congelado pode ser atualizado”, “proposta_id é obrigatório e único; confirmado é booleano estrito e imutável gravado somente pela rota sistêmica; decidida_em é obrigatório; consumida_em e resultado_json são ambos nulos antes do consumo e ambos preenchidos após” e “proposta_id é obrigatório e único; estado pertence a recuperar ou concluido; concluir exige resultado consumido e eventos de retomada persistidos”; triggers/repositório impedem alteração de snapshot/decisão; unique sessão/invocation/chamada original; após fundação (FR-006–FR-011, FR-016).
- [X] T016 [US2] Implementar prepare/decide/list_pending em `src/aurora/storage/confirmacoes.py`: preparação idempotente, publicação correlata, CAS/INSERT de decisão somente pendência da sessão, despacho recuperável no mesmo commit; ID ausente/alheio/respondido 409 sem alteração, lista de todas pendências sem decisão e sem remover outras; após T015 (FR-006, FR-007, FR-009–FR-011, FR-015, FR-016).
- [X] T017 [P] [US2] Adaptar append/reconciliação em `src/aurora/runtime/sessions.py` para observar evento ADK completo já persistido e vincular novo ID adk_request_confirmation à originalFunctionCall, invocation/author/branch na proposta antes de publicar; reconciliar somente metadados no restart, nunca criar/regravar eventos; preservar ordenação 001; após T016, independente T018/T019 (FR-006, FR-008, FR-011, FR-014).
- [X] T018 [US2] Implementar executor transacional em `src/aurora/storage/reservas.py` e consumo em `src/aurora/storage/confirmacoes.py`: mesma conexão/commit para decisão consumida+resultado+reserva/ledger/contador; executar parâmetros congelados; negar sem efeito; tratar UNIQUE área/data como indisponível consumida 200 com savepoint se necessário; reentrada técnica devolve resultado próprio persistido sem novo código/efeito; após T016/T008/T006 (FR-002, FR-005, FR-008, FR-011–FR-013, FR-016).
- [X] T019 [US2] Implementar ramo pago da tool em `src/aurora/tools/reservas.py`: prepare snapshot da área/data/taxa reais, tool_context.request_confirmation com hint/payload e retorno intermediário sem reserva; na reentrada resolver decisão canônica pela identidade/ID original e executar T018; ignorar autorização apenas textual, state ou ToolConfirmation sem decisão persistida; após T018/T010 (FR-003, FR-006–FR-008).
- [X] T020 [US2] Criar coordenador em `src/aurora/runtime/confirmacoes.py`: FunctionResponse nativa com ID ADK novo e booleano da decisão, Runner.run_async com invocation original e identidade interna; ContextVar de sessão/invocation/author validada com token/reset try/finally; marcar despacho concluído somente após resultado consumido e eventos persistidos; não chamar executor diretamente na rota; após T017–T019 (FR-007, FR-008, FR-011, FR-016).
- [X] T021 [US2] Implementar `src/aurora/api_routes/confirmacoes.py` e registrar em `src/aurora/api.py`: sessão 404 primeiro, schema booleano estrito, decide sob lock por sessão antes de Runner, IDs inválidos/alheios/respondidos 409 sem execução,200 para negação/aprovação permitida/indisponível no envelope comum com pendências integrais; após T020/T007 (FR-007–FR-010, FR-012, FR-015).
- [X] T022 [US2] Substituir [] fixo por consulta real de pendências em `src/aurora/runtime/service.py` e `src/aurora/api_routes/sessoes.py`, mantendo mensagens 200/404, lista integral e nenhuma autorização por texto; atualizar `src/aurora/agents/reservas.py` para anunciar cobrança somente com confirmação sistêmica implementada; após T021 (FR-003, FR-006, FR-007, FR-010, FR-014).
- [X] T023 [US2] Implementar recuperação em `src/aurora/runtime/confirmacoes.py` e `src/aurora/runtime/service.py`: startup só reconcilia metadados sem Runner/eventos; GET é leitura pura; nova POST mensagens recupera despacho decidido incompleto antes do texto pelo mesmo Runner/decisão, conferindo invocation já concluída e resultado; replay 409 não recupera; após 200 não sobra job; após T022 (FR-008, FR-009, FR-011, FR-014; SC-004).
- [X] T024 [US2] Verificar com API/SQLite real autoria, IDs, topologia e retomada em `src/aurora/runtime/app.py` e `src/aurora/runtime/confirmacoes.py`; se diagnóstico comprovar desvio só da seleção, criar `src/aurora/runtime/runner.py` com fallback estreito _find_agent_to_run baseado na ContextVar canônica e super fora da retomada; nunca aceitar author do cliente/LLM; registrar limitação oficial e evidência em `docs/validacao/002-reservas.md`; após T023, corrigir demais causas antes do aceite (FR-008, FR-011, FR-014).
- [X] T025 [US2] Executar casos US2 de consentimento textual, negar, novo pedido/aprovar, reenvio aprovado/negado, ID inválido, ID de outra sessão e 404 da sessão ausente do `specs/002-reservas-confirmacoes/quickstart.md`; comparar banco/rotas/eventos antes/depois e registrar em `docs/validacao/002-reservas.md`; após T024 (FR-003, FR-006–FR-010, FR-014, FR-015; SC-001, SC-002).
- [X] T026 [US2] Executar aprovação de pendência após restart sem reset conforme `specs/002-reservas-confirmacoes/quickstart.md`, comprovando IDs/author solicitante, reentrada da tool, efeito real uma vez, replay 409 após segundo restart e eventos integralmente iguais sem interação; confirmar startup/GET sem eventos novos; registrar em `docs/validacao/002-reservas.md`, sem aceitar 200 sem efeito; após T025 (FR-005, FR-008, FR-009, FR-011, FR-014; SC-002, SC-004).
- [X] T027 [US2] Validar múltiplas pendências/nova mensagem durante pendência e imutabilidade de parâmetros, conferindo que negar uma não remove outra nem troca snapshot, com inspeção de `src/aurora/storage/confirmacoes.py` e evidências em `docs/validacao/002-reservas.md`; após T026 (FR-006–FR-010; SC-001, SC-002).
- [X] T028 [P] [US2] Documentar contrato de registro de executor e compartilhamento da transação para visitante 003 em `docs/arquitetura.md`, referenciando `specs/002-reservas-confirmacoes/contracts/confirmation-runtime.md`; mesma rota/decisão/replay e nenhum commit independente de callback; após T020/T014, independente T025–T027 (FR-016).

Checkpoint: confirmação só está aceita quando solicitante/Runner/SQLite/efeito após restart funcionam; leitura de código isolada não passa o gate.

## Fase 5 — US3: Disputa sem duplicidade ou vazamento (P1)

**Objetivo**: duas decisões válidas terminam 200, uma única reserva, recusa sem dados da vencedora e códigos duráveis.
**Critério independente**: duas sessões 101/201, salão 2030-05-11, ambas pendentes/aprovações simultâneas; somar listagens=1. Verificar ocupação 2030-03-16 e códigos/cancelamento após restart.

- [X] T029 [US3] Integrar/revisar tratamento de perda por disponibilidade em `src/aurora/storage/reservas.py` e `src/aurora/runtime/confirmacoes.py`: decisão consumida e recusa normal 200, sem SELECT da vencedora, sem converter em 409/500 ou reutilizar código; lock curto por escrita, sem lock global do Runner; após US2 (FR-002, FR-008, FR-012, FR-013; SC-003).
- [X] T030 [US3] Auditar sigilo do passo 10 em `src/aurora/tools/reservas.py`, `src/aurora/agents/reservas.py` e `src/aurora/storage/reservas.py`: somente livre/ocupada/recusa, nenhuma resposta com RSV-4821 ou número 302 isolado e nenhum evento com RSV-4821; manter também passo 4 e não filtrar histórico; executar cenário em sessão 101 nova e registrar em `docs/validacao/002-reservas.md`; após T029 (FR-004, FR-013, FR-014; SC-005).
- [X] T031 [US3] Executar persistência/códigos do `specs/002-reservas-confirmacoes/quickstart.md`: cancelamento efetivo após restart, novas reservas/códigos distintos dos iniciais/cancelados/anteriores e mesma área liberada após cancelar; conferir ledger/contador duráveis em `src/aurora/storage/codigos.py` e registrar efeitos reais em `docs/validacao/002-reservas.md`; após T030 (FR-004, FR-005, FR-011; SC-004).
- [X] T032 [US3] Executar aprovações concorrentes e inspeção do índice no `specs/002-reservas-confirmacoes/quickstart.md`, ambas 200 e soma exatamente 1, recusa sem dados vencedores em resposta/tools/eventos, contextos confiáveis separados; repetir cenário em data livre equivalente após restart e registrar em `docs/validacao/002-reservas.md`; após T031 (FR-002, FR-008, FR-012–FR-015; SC-003).
- [X] T033 [US3] Reexecutar regressões 001 e fluxos 002 afetados por mudanças em identidade/topologia/tools/armazenamento/confirmação, comparando eventos integrais e listagens reais, registrando falhas e correções em `docs/validacao/002-reservas.md`; após T032, nenhuma falha de garantia pode ficar aprovada (FR-001–FR-016; SC-001–SC-005).

## Fase 6 — Acabamento transversal

- [X] T034 Atualizar `docs/arquitetura.md` e `docs/operacao.md` com mecanismos efetivos, referências reais, topologia e recuperação sem eventos no startup/GET, garantias do ledger na restauração 005 e limites ADK constatados; preservar README enunciado/constituição/dados; após US1–US3 e T028 (FR-005, FR-008, FR-011, FR-014, FR-016).
- [X] T035 Conferir `pyproject.toml`, `uv.lock`, `.gitignore` e `.env.example`, rodar uv sync e diff de dados/ sem expor segredos, confirmar pin exato e nenhum estado runtime versionado; registrar em `docs/validacao/002-reservas.md`; após T034 (FR-011; restrições constitucionais).
- [X] T036 Consolidar matriz FR-001–FR-016/SC-001–SC-005 em `docs/validacao/002-reservas.md`, com resultados reais, falhas/gates abertos e decisões para 003; encaminhar 15 passos completos à 005; não chamar planejamento de aceite funcional; após T035 (FR-001–FR-016; SC-001–SC-005).

## Dependências e paralelismo

**Ordem**:001 → setup → fundação → US1 → US2 → US3 → acabamento. US1 independe de confirmação; US2 reaproveita executor da US1; US3 prova disputa sobre o fluxo completo. Todas são P1, a ordem respeita dependências técnicas, não reduz prioridade.

Setup T001→T002/T003; fundação T004→T005, T006/T007 independentes após T001. US1 T008→T009→T010→T011→T012→T013; T014 após T011 em documentação separada. US2 T015→T016; T017/T018 após T016, T019 após T018/T010; T020 aguarda T017–T019; T021→T022→T023→T024→T025→T026→T027. T028 pode ocorrer após T020 em arquivo separado do registro de validação, aguarda T014. US3 T029→T030→T031→T032→T033. Acabamento T034→T035→T036.

**Exemplos por história**:

- US1: T014 documenta docs/arquitetura.md enquanto T012 integra API/runtime e T013 registra validação em outro arquivo; não editar tools/reservas.py em paralelo entre T010/T011.
- US2: T017 modifica runtime/sessions.py enquanto T018 modifica storage/reservas.py/confirmacoes.py; T019 modifica tools/reservas.py depois de T018; só T017 é marcada[P], pois as restantes têm integração dependente. T028 documenta interface durante T025–T027 em docs/validacao/002-reservas.md, após T014. T023/T024/T026 não executam em paralelo contra a mesma API.
- US3: sequência intencional; os curl simultâneos deT032 são cenário de negócio, não autorização para editar arquivos compartilhados ou reiniciar serviço durante outra validação.

Nenhuma tarefa[P] ignora pré-requisitos. Startup/GET nunca disparam Runner; mesmas interações de sessão continuam serializadas, sessões distintas concorrentes.

## Estratégia de implementação

MVP=setup+fundação+US1, sem anunciar cobranças. Entregar US2 com confirmação persistida testada e depois US3 com disputa/sigilo; cada história tem critério observável, mas a spec inteira só é aceita com todas. Não há deploy ou suíte obrigatória. Registrar resultados reais e corrigir falhas antes de concluir, especialmente limitação documentada ADK/SQLite. O usuário desta preparação solicitou somente os artefatos.

## Cobertura

| Requisito | Tarefas |
| --- | --- |
| FR-001 | T005, T008, T010, T013 |
| FR-002 | T005, T006, T008, T018, T029, T032 |
| FR-003 | T005, T008, T010, T019, T022, T025 |
| FR-004 | T009–T013, T030, T031 |
| FR-005 | T004, T005, T008, T018, T026, T031 |
| FR-006 | T007, T015–T017, T019, T022, T025, T027 |
| FR-007 | T016, T019, T020–T022, T025, T027 |
| FR-008 | T017–T021, T023–T026, T029, T032 |
| FR-009 | T016, T021, T023, T025–T027 |
| FR-010 | T007, T016, T021, T022, T027 |
| FR-011 | T001, T004–T006, T015–T017, T018, T020, T023, T024, T026, T031 |
| FR-012 | T006, T018, T021, T029, T032 |
| FR-013 | T005, T006, T008, T009, T029, T030, T032 |
| FR-014 | T003, T009–T013, T017, T022, T024–T026, T030, T032, T033 |
| FR-015 | T007, T016, T021, T025, T032 |
| FR-016 | T015, T016, T018, T020, T028, T034 |
| SC-001 | T008, T013, T025, T027 |
| SC-002 | T025–T027 |
| SC-003 | T029, T032 |
| SC-004 | T004, T026, T031 |
| SC-005 | T009, T013, T030 |

**Contagem**:36 tarefas; setup 3, fundação 4, US1 sete(P1), US2 catorze(P1), US3 cinco(P1), acabamento 3. Sete tarefas[P]. IDs sequenciais, checkbox desmarcado, label nas fases de história e caminho concreto em todos itens. Todas as 12 constraints novas são citadas literalmente; constraints herdadas 001 continuam aplicáveis.
