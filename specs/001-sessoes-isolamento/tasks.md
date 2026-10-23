# Tarefas: Sessões persistentes e isolamento por apartamento

**Entrada**: spec.md, plan.md, research.md, data-model.md e contracts/ em `specs/001-sessoes-isolamento/`.
**Estado**: tarefas planejadas, nenhuma implementação concluída. Branch Git `dev`; diretório selecionado explicitamente, sem alteração de branch/seletor.
**Validação**: manual reproduzível pelo quickstart; não criar suíte/evals como entregável obrigatório. IDs FR/SC referem-se exclusivamente à spec 001. Constraints citadas literalmente do modelo; nomes de arquivos são relativos à raiz.

## Formato e convenções

`- [ ] Tnnn [P opcional] [USn quando história] descrição com caminho`. [P] só indica execução simultânea **depois das dependências indicadas** e em arquivos distintos. Nenhuma tarefa cria reserva, cancela, autoriza visitante ou consulta regulamento; isso é 002–004.

## Fase 1 — Setup

Objetivo: pacote instalável, configuração sem segredos e procedimento básico.

- [ ] T001 Criar pacote `src/aurora/__init__.py`, `pyproject.toml`, `.python-version` e `uv.lock` com Python >=3.12, `google-adk==2.2.0`, FastAPI/Uvicorn/SQLAlchemy/aiosqlite/pydantic-settings compatíveis, entrypoint aurora e resolução por uv; conferir `uv sync` sem atualizar o pin ADK (FR-009, FR-011; restrições técnicas).
- [ ] T002 [P] Configurar `src/aurora/config.py`, `.env.example` e `.gitignore` com nomes GOOGLE_API_KEY, GEMINI_MODEL e AURORA_DATA_DIR sem valores no exemplo; defaults documentados, caminhos absolutos estáveis, `.env` e `var/` ignorados; após T001 (FR-008, FR-009; sigilo).
- [ ] T003 [P] Escrever `docs/operacao.md` com uv sync, chave própria via editor, subida em localhost:8000 com um worker, ausência de serviços auxiliares, seed inicial e aviso de não restaurar ao reiniciar; preservar README do enunciado; após T001 (FR-008, FR-009).
- [ ] T004 Criar `scripts/check_model.py` para confirmar acesso ao modelo configurado e uma chamada de função simples sem expor chave; registrar em `docs/validacao/001-sessoes.md` modelo, data e RPM/TPM/RPD reais consultados no projeto AI Studio antes de validar o runtime; considerar múltiplas chamadas por interação e dezenas no avaliador; se inacessíveis, manter evidência pendente sem inventar quota; após T002 (FR-011; gate operacional de modelos).

## Fase 2 — Fundação bloqueante

Objetivo: persistência e fronteira de autorização existem antes das histórias. Concluir esta fase antes da US1; US2 não adia durabilidade.

- [ ] T005 Configurar conexões SQLite em `src/aurora/storage/database.py`, `src/aurora/runtime/sessions.py` e diretório de runtime ignorado, com bancos negócio/ADK distintos, FK no negócio, WAL/busy_timeout e fechamento correto; não manter transação durante chamada Gemini; após T001–T002 (FR-006, FR-008).
- [ ] T006 Criar schema e trigger em `src/aurora/storage/schema.py` impondo “numero é obrigatório e único; morador reproduz o cadastro inicial”, “id é obrigatório e único; nome e taxa reproduzem dados/areas.json; taxa zero significa ausência de cobrança” e “session_id é obrigatório e único; apartamento é obrigatório, definido uma vez e imutável”; FK no vínculo e nenhum UPDATE de identidade permitido; após T005 (FR-001, FR-002, FR-008, FR-012).
- [ ] T007 Implementar tabelas de reserva/visitante e importação transacional em `src/aurora/storage/schema.py` e `src/aurora/storage/seed.py` com “codigo é obrigatório e único; apartamento e area são obrigatórios e referenciam cadastros; data usa AAAA-MM-DD e é uma data civil válida”, “codigo nunca é reutilizado; cancelamentos preservam o registro”, “apartamento, nome e data são obrigatórios; data usa AAAA-MM-DD e é uma data civil válida” e “carga inicial ocorre em uma transação somente no banco nunca inicializado; reiniciar não restaura dados”; importar todos cadastros/áreas/reservas/visitantes de dados/ sem alterá-los; após T006 (FR-003, FR-008, SC-003).
- [ ] T008 [P] Adaptar DatabaseSessionService em `src/aurora/runtime/sessions.py` para “eventos persistidos são integrais, imutáveis e retornados na ordem de gravação; ler não altera nem cria eventos” e “timestamp de novo evento é estritamente maior que o anterior da sessão, com passo mínimo de 1 ms, inclusive após reinício”; append nativo sob lock próprio curto sem deadlock com lock ADK, referência restaurada do máximo persistido; um worker, sem compaction, sem dados auditáveis temp:* e sem streaming; após T005, independente T006–T007 (FR-006, FR-007, SC-002).
- [ ] T009 [P] Definir DTOs JSON em `src/aurora/schemas.py` segundo `specs/001-sessoes-isolamento/contracts/api.md`: apartamento/texto strings, resposta string inclusive vazia, confirmacoes_pendentes lista, reservas codigo/area/data e visitantes nome/data; sem envelope nas listas; após T005, independente T006–T008 (FR-009, FR-010).
- [ ] T010 Implementar repositório em `src/aurora/storage/identity.py` com “a API só devolve 201 após persistir vínculo canônico e sessão ADK; falha parcial não deixa sessão utilizável” e “a autorização usa somente SessionIdentity resolvida por tool_context.session.id; state e argumentos do modelo não mudam apartamento”; criação coordenada com compensação, lookup canônico e nenhuma mutação de apartamento; após T006 e T008 (FR-001, FR-002, FR-004, FR-006, FR-012).

Checkpoint: schema, seed, DTOs, identidade e serviço persistente disponíveis; não há capacidades de negócio fictícias.

## Fase 3 — US1: Consultar meus dados sem expor outros moradores (P1, MVP)

**Objetivo**: criar sessão, consultar reservas/visitantes próprios, resistir a mudança de identidade por mensagem e consultar apenas ocupação.
**Critério independente**: quickstart US1, incluindo tentativa do passo 3, zero RSV-4821/Marina Duarte na resposta e em todos os eventos, agenda sem responsável, mesmas informações próprias do banco.

- [ ] T011 [P] [US1] Implementar POST /sessoes em `src/aurora/api_routes/sessoes.py`, gerando session_id e sessão ADK com app_name aurora/user_id=session_id, preservando criação coordenada e 201 somente após persistência; apartamento inexistente 422 JSON; após T010 e T009 (FR-001, FR-002, FR-009).
- [ ] T012 [P] [US1] Implementar consultas de negócio em `src/aurora/storage/queries.py` com “consulta própria filtra apartamento antes de materializar resultado; disponibilidade retorna somente livre ou ocupada”; reservas ativas e visitantes em projeções autorizadas; agenda EXISTS por área/data sem selecionar código, apartamento ou morador; após T007, independente T011 (FR-003, FR-004, FR-005, FR-012).
- [ ] T013 [US1] Implementar `src/aurora/tools/context.py` com resolve_identity pelo `tool_context.session.id` público e vínculo canônico; falha segura antes do SQL se sessão/correlação inválida; não confiar em state ou argumentos do modelo; após T010 (FR-002, FR-004, FR-012).
- [ ] T014 [P] [US1] Implementar listar_minhas_reservas e consultar_disponibilidade em `src/aurora/tools/reservas.py`, usando T012/T013, sem argumento apartamento/session_id e somente dados autorizados; validar área/data sem impor antecedência/horário/capacidade; não retornar dados do ocupante nem oferecer mutações (FR-003, FR-004, FR-005, FR-012).
- [ ] T015 [P] [US1] Implementar listar_meus_visitantes em `src/aurora/tools/visitantes.py`, usando T012/T013 e projeção nome/data apenas do apartamento canônico; sem argumento apartamento/session_id nem acesso administrativo (FR-003, FR-004, FR-005, FR-012).
- [ ] T016 [P] [US1] Criar LlmAgent de reservas em `src/aurora/agents/reservas.py`, modo chat, tools T014, disallow_transfer_to_parent=False e disallow_transfer_to_peers=True; descrição limita-se a consultas/disponibilidade entregues; após T014 (FR-011, FR-012).
- [ ] T017 [P] [US1] Criar LlmAgent de visitantes em `src/aurora/agents/visitantes.py`, modo chat, tool T015 e os mesmos flags de transferência; sem anunciar autorização futura; após T015 (FR-011, FR-012).
- [ ] T018 [US1] Criar principal em `src/aurora/agents/principal.py` e App/Runner em `src/aurora/runtime/app.py` com T016/T017 como sub_agents, retorno ao principal permitido e ResumabilityConfig(is_resumable=True); modelo configurável, sem AgentTool/sessão filha e sem regulamento nas instruções; depois T016/T017 (FR-002, FR-011, FR-012).
- [ ] T019 [US1] Implementar execução e API em `src/aurora/runtime/service.py`, `src/aurora/runtime/events.py`, `src/aurora/api_routes/sessoes.py`, `src/aurora/api.py` e `src/aurora/cli.py`: POST mensagens via Runner com identidade interna e lock por sessão, 200 com resposta textual e [] de pendências, GET eventos completo do serviço persistido incluindo user events, 404 JSON antes do modelo, CLI serve com um worker; após T011/T018/T008 (FR-006, FR-007, FR-009, FR-010, SC-001, SC-004).
- [ ] T020 [US1] Executar os passos conversacionais do cenário US1 de `specs/001-sessoes-isolamento/quickstart.md` e registrar evidência real em `docs/validacao/001-sessoes.md`, comparando consultas próprias com seed pelo banco até T024 disponibilizar as rotas diretas; T027 executa o roteiro HTTP integral, testando consulta combinada, tentativa de identidade, listas vazias e agenda livre/ocupada; inspecionar todos eventos sem filtrar achados; após T019 e gate T004 (FR-002–FR-005, FR-012, SC-001, SC-003, SC-004).

Checkpoint: MVP conversacional de leitura disponível, com persistência desde a fundação. Não declarar spec inteira aceita ainda.

## Fase 4 — US2: Continuar a mesma conversa após reiniciar (P1)

**Objetivo**: provar recuperação sem recriar identidade ou alterar eventos anteriores.
**Critério independente**: sessão com N eventos → reinício pelo mesmo comando → mesmo JSON completo e N; nova mensagem 200 acrescenta eventos mantendo o prefixo anterior.

- [ ] T021 [US2] Integrar recuperação de sessão em `src/aurora/runtime/service.py` e startup em `src/aurora/api.py` para buscar sessão ADK/vínculo existentes, inicializar somente esquema/seed necessários e recuperar referência temporal do adapter sem regravar eventos; não criar sessão substituta se ID já existe; após T019 (FR-002, FR-006, FR-008, SC-002, SC-004).
- [ ] T022 [US2] Executar reinício sem restauração descrito em `specs/001-sessoes-isolamento/quickstart.md` e registrar em `docs/validacao/001-sessoes.md` igualdade integral/contagem/ordem antes/depois, resposta normal e aumento com prefixo preservado, repetindo GET sem interação e mantendo dados iniciais; após T021 (FR-006, FR-008, SC-002, SC-004).
- [ ] T023 [US2] Conferir duas sessões do mesmo apartamento, estados/históricos distintos, retomada sem mudança de identidade e nenhum state compartilhado por morador em `src/aurora/runtime/sessions.py` e `src/aurora/storage/identity.py`; corrigir qualquer falha observada e registrar resultado em `docs/validacao/001-sessoes.md`; após T022 (FR-001, FR-002, FR-006, SC-002, SC-004).

Checkpoint: nenhuma nova leitura ou reinício muda eventos antigos; a mesma sessão segue utilizável.

## Fase 5 — US3: Conferir estado e histórico completos (P2)

**Objetivo**: avaliador verifica estado real e estrutura sem depender do modelo.
**Critério independente**: rotas diretas reproduzem todos dados iniciais, GET eventos inclui consultas e transferências, sessões desconhecidas dão 404, há principal e dois especialistas reais.

- [ ] T024 [US3] Implementar consultas diretas do avaliador em `src/aurora/api_routes/verificacao.py` e registrar no `src/aurora/api.py`, GET reservas/visitantes por apartamento com projeções externas e [] para inexistente/sem registros; ler banco sem Runner, sem registrar rotas como tools ou injetar resultados administrativos no histórico; após T012/T019 (FR-007, FR-009, SC-003).
- [ ] T025 [US3] Auditar `src/aurora/runtime/events.py` e `src/aurora/api_routes/sessoes.py` para retorno de todos eventos persistidos do SDK sem projeção, incluindo entradas, chamadas, resultados, actions, author e invocation_id; verificar sessão vazia e 404 de mensagem/eventos inexistentes; registrar evidências em `docs/validacao/001-sessoes.md`; após T024 (FR-006, FR-007, FR-009, SC-001, SC-002).
- [ ] T026 [P] [US3] Documentar agentes, responsabilidades, transferência, motivação, identidade canônica e limites futuros em `docs/arquitetura.md`, incluindo App/Runner/serviço persistido e a configuração candidata de confirmação herdada pela 002; não afirmar mutações ou confirmação já validadas; após T018, independente T025 (FR-011, FR-012).
- [ ] T027 [US3] Executar quickstart US3 e repetir US1 usando rotas diretas em `specs/001-sessoes-isolamento/quickstart.md`; registrar em `docs/validacao/001-sessoes.md` todas reservas/visitantes iniciais comparados com dados/, catálogo sem rotas administrativas, ADK 2.2.0, 404s, tools e retornos completos; após T024–T026 (FR-003, FR-007, FR-008, FR-009, FR-011, SC-001, SC-003, SC-004).

## Fase 6 — Acabamento transversal

- [ ] T028 Atualizar `docs/operacao.md` com comandos e limites efetivamente implementados, inclusive seed sem restauração no startup, um worker e dependência Google AI Studio; manter README do enunciado e indicar que restauração completa e manual final serão 005; após US1–US3 (FR-008, FR-009, FR-011).
- [ ] T029 Conferir instalação por `uv sync`, pin em `pyproject.toml`/`uv.lock`, `.env`/var ignorados, `.env.example` sem valores e `dados/` sem mudanças; registrar comandos/resultados em `docs/validacao/001-sessoes.md` sem segredos; após T028 (FR-008, FR-009; constituição e SC-003).
- [ ] T030 Reexecutar os fluxos afetados por ajustes de identidade, tools, topologia ou serviço de sessão e preencher `docs/validacao/001-sessoes.md` com cobertura FR-001–FR-012/SC-001–SC-004, falhas e gates ainda abertos; encaminhar à 002 a validação obrigatória de confirmação persistida após restart e à 005 os 15 passos completos; após T029, sem marcar validação não executada como aprovada (FR-001–FR-012, SC-001–SC-004).

## Dependências e ordem de execução

Setup T001 → T002/T003 → T004; fundação T005 → T006 → T007, em paralelo com T008/T009 após T005; T010 após T006/T008. Todas histórias aguardam fundação e configuração. US1: T011 e T012 independentes → T013 → T014/T015 → T016/T017 → T018 → T019 → T020. T011 deve terminar antes de T019. US2 T021–T023 depende da API US1; pode ser validada com consultas apenas. US3 T024–T027 depende das leituras/Runner US1 e usa persistência já entregue; não depende de mutações das specs seguintes. Sequência recomendada: **Setup → Fundação → US1 P1 → US2 P1 → US3 P2 → Acabamento**.

Entre specs: 001 não depende de outra. 002 herda identidade/eventos/App/Runner e acrescenta negócio/pendências; 003 herda 002; 004 herda 001; 005 consolida todas. A validação de confirmação com SQLite é gate de implementação na 002, não afirmação de runtime nesta lista.

## Exemplos de paralelismo por história

- **US1**: após T013/T012, T014 em tools/reservas.py e T015 em tools/visitantes.py; depois T016/T017 em arquivos de agentes diferentes. Não editar principal/app em paralelo com integração T018/T019.
- **US2**: execução intencionalmente sequencial (T021→T022→T023), pois restart e comparação usam a mesma API e registro de evidências; nenhuma oportunidade segura marcada [P].
- **US3**: T026 em docs/arquitetura.md pode executar enquanto T025 revisa eventos/rotas e registra evidências. T027 aguarda ambos.
- Setup permite T002/T003 após T001; fundação permite T008/T009 ao lado de schema/seed depois T005. Nenhum [P] autoriza ignorar pré-requisitos.

## Estratégia de implementação

MVP = Setup + Fundação + US1, com isolamento e persistência reais desde o início. Validar US1 e então continuar US2/US3; nenhuma história P1 isolada substitui a spec completa. Incrementos não exigem deploy. Registrar fatos observados e falhas; não criar mocks de estado como comprovação de consultas reais.

## Cobertura dos requisitos

| Requisito | Tarefas de construção/validação |
| --- | --- |
| FR-001 | T006, T010, T011, T023 |
| FR-002 | T006, T010, T013, T018, T020, T021, T023 |
| FR-003 | T007, T012, T014, T015, T020, T027 |
| FR-004 | T010, T012–T015, T020 |
| FR-005 | T012, T014, T015, T020 |
| FR-006 | T005, T008, T010, T019, T021–T023, T025 |
| FR-007 | T008, T019, T024, T025, T027 |
| FR-008 | T002, T003, T005–T007, T021, T022, T027–T029 |
| FR-009 | T001–T003, T009, T011, T019, T024, T025, T027–T029 |
| FR-010 | T009, T019 |
| FR-011 | T001, T004, T016–T018, T026–T028 |
| FR-012 | T006, T010, T012–T018, T020, T026 |
| SC-001 | T019, T020, T025, T027 |
| SC-002 | T008, T021–T023, T025 |
| SC-003 | T007, T020, T024, T027, T029 |
| SC-004 | T019–T023, T027 |

**Contagem**: 30 tarefas; Setup 4, Fundação 6, US1 10 (P1), US2 3 (P1), US3 4 (P2), Acabamento 3. Onze tarefas marcadas [P]. Todos os itens ficam desmarcados até execução real.
