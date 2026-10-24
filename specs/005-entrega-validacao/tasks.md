# Tarefas: entrega reproduzível e validação integral

**Entrada**: [spec.md](spec.md), [plan.md](plan.md), [pesquisa](research.md), [modelo](data-model.md), [contrato](contracts/operacao.md), [guia](quickstart.md). Dependências 001–004 implementadas e validadas antes dos gates desta entrega. Todas tarefas futuras e desmarcadas; não implementar nesta preparação.

**Validação**: manual reproduzível; sem suíte automatizada/evals obrigatórios. [P] somente em arquivos distintos após pré-requisitos. Caminhos são relativos à raiz.

## Fase 1 — Setup

- [X] T001 Conferir fechamento das specs 001–004 e registrar versões, limitações reais, commit e inventário dos módulos em `docs/validacao/005-integral.md`, sem declarar resolvida limitação de confirmação persistida sem evidência (FR-009, FR-011, FR-012).
- [X] T002 Auditar `pyproject.toml`, `uv.lock`, `.python-version`, `.env.example` e `.gitignore`: Python >=3.12, `google-adk==2.2.0`, pacote/entrypoint aurora, lock compatível, exemplo só nomes sem valores, `.env`/`var/` ignorados; corrigir divergências sem trocar pin ou versionar segredo (FR-004, FR-005).

## Fase 2 — Fundação

- [X] T003 [P] Implementar lock interprocesso estável em `src/aurora/storage/maintenance.py` com caminhos absolutos e compartilhado de serviço/exclusivo não bloqueante para reset, retido por toda operação; arquivo não é removido e nenhuma conexão abre antes do lock (FR-002, FR-003).
- [X] T004 [P] Preservar enunciado integral de `README.md` em `docs/desafio-original.md` e conferir igualdade antes de qualquer futura substituição; manter fonte normativa dos 15 passos e 28 critérios acessível (FR-006, FR-009).
- [X] T005 Estabelecer formato de evidência e tabela AC-01–AC-28 em `docs/validacao/005-integral.md`, copiando referências normativas do índice: “evidência registra resultado observado por passo e só marca aprovado após conferir resposta, armazenamento e eventos aplicáveis; ausência de execução é não executado, nunca aprovado”; guardar snapshots privados ignorados sem chaves (C504; FR-009, FR-010, FR-013).

## Fase 3 — US1: clone limpo, restauração e subida (P1, MVP)

**Objetivo**: avaliador instala e executa somente com instruções públicas e chave própria. **Critério independente**: clone limpo/uv sync, dados iniciais completos, reset explícito e restart comum com estados distintos; lock/falha parcial sem estado intermediário servido.

- [X] T006 [US1] Integrar lock compartilhado e recusa por marcador em `src/aurora/cli.py`/`src/aurora/storage/maintenance.py`: “marcador durável é criado antes de qualquer alteração; enquanto existir, serve recusa iniciar; removê-lo exige as duas bases restauradas e verificadas”; manter startup/GET sem reset, Runner ou eventos novos (C501; FR-001, FR-003).
- [X] T007 [US1] Implementar transação de negócio em `src/aurora/storage/reset.py` usando schema/seed existentes: “restauração exige API parada e lock exclusivo; apaga sessões e eventos, elimina pendências e decisões, repõe reservas e visitantes iniciais sem editar dados/”; remover filhos antes de pais na ordem FK real (autorizações/reservas, despachos, decisões, propostas, identidade), reimportar visitantes iniciais com proposta_id nulo, preservar cadastros (C502; FR-002).
- [X] T008 [US1] Preservar ledger/contador no reset de `src/aurora/storage/reset.py`: “restauração preserva todos códigos emitidos e o contador monotônico; nenhum código inicial, cancelado ou anterior ao reinício é reutilizado”; reimportar códigos iniciais por referência ao ledger existente, sem diminuir contador nem apagar códigos emitidos (C503; FR-002, FR-003).
- [X] T009 [US1] Orquestrar reset idempotente em `src/aurora/storage/reset.py` e fechamento ADK em `src/aurora/runtime/sessions.py`: validar fontes, marcador durável com fsync antes de alterações, commit de negócio e recriação ADK vazio com conexões fechadas/WAL/SHM tratados; após validar duas bases remover marcador; falha deixa marcador e bloqueio, sem promessa de commit distribuído (C501–C503; FR-002).
- [X] T010 [US1] Expor `uv run aurora restaurar` em `src/aurora/cli.py` e conferir `uv run aurora serve`: reset com serviço ativo retorna não zero antes de tocar dados; sucesso só depois das verificações; erro diagnóstico sem chave; startup nunca chama restaurar (FR-001–FR-003).
- [X] T011 [US1] Consolidar instruções em `docs/operacao.md` com pré-requisitos/uv sync/configuração privada/nenhum serviço de banco externo, comandos/endereço, política de sessões+pendências+decisões+eventos apagados, ledger preservado, API parada, falha parcial e recuperação; conferir nomes reais de variáveis de `src/aurora/config.py` (FR-001–FR-005).
- [X] T012 [US1] Executar passo1 do `specs/005-entrega-validacao/quickstart.md` em clone limpo e registrar em `docs/validacao/005-integral.md`: uv sync, pin real, chave própria, acesso/function call via `scripts/check_model.py`, documentação Gemini e limites ativos AI Studio sem chaves, API8000 e todos registros iniciais, incluindo RSV-1377/Marina Duarte (FR-001, FR-004, FR-005, FR-012; SC-001).
- [X] T013 [US1] Validar reset repetido/lock/falha entre bancos e reinício comum conforme gates extras de `specs/005-entrega-validacao/quickstart.md`; registrar em `docs/validacao/005-integral.md` estado inicial completo, originais intactos, sessões antigas404, nenhuma pendência antiga executável, ledger/contador preservados e startup bloqueado até reset completo após falha parcial (FR-002, FR-003, FR-013; SC-004, SC-005).

## Fase 4 — US2: auditoria integral do uso real (P1)

**Objetivo**: provar garantias pelo contrato real e histórico completo. **Critério independente**: passos1–15, na ordem, efeitos e eventos, duas aprovações concorrentes200/200 e uma reserva, pendências aprovadas depois de restart. Qualquer falha mantém entrega incompleta.

- [X] T014 [US2] Preparar execução manual na ordem integral de `specs/005-entrega-validacao/quickstart.md` e campos de resultado por passo em `docs/validacao/005-integral.md`; realizar restauração inicial no próprio passo1, sem reset extra entre passos, permitir esclarecimentos/reformulações sem depender de frase exata e guardar cada resposta/status/JSON completo, sem filtrar histórico (FR-009, FR-010, FR-013).
- [X] T015 [US2] Executar passos2–6 e registrar em `docs/validacao/005-integral.md`:201, identidade101 imutável, passo3 sem RSV-4821/Marina na resposta e eventos, passo4 preserva reserva302 e não revela RSV-4821, cancelamento próprio e quadra gratuita sem qualquer pendência; comprovar tools/rotas reais (FR-009, FR-010, FR-012).
- [X] T016 [US2] Executar passos7–11 e registrar em `docs/validacao/005-integral.md`:snapshots área/data e nome/data, nada antes da rota, negação sem efeito, aprovação exatamente uma vez, replay/ID inválido409, sessão ausente404; no passo10 nenhuma resposta contém RSV-4821 nem302 isolado fora de números/códigos e eventos não contêm RSV-4821; visitante exige confirmação apesar do texto (FR-009–FR-012).
- [X] T017 [US2] Executar passos12–13 e registrar em `docs/validacao/005-integral.md`:piscina domingo20h derivada da fonte, zero trechos de capítulos alheios em todos eventos, calls/results anteriores completos; salvar contagem/JSON antes de Ctrl+C, restart sem reset mantém JSON/ordem, mesma sessão aceita200 e aumenta eventos, efeitos/cancelamentos persistem e códigos novos distintos dos três iniciais (FR-003, FR-009, FR-010, FR-012; SC-005).
- [X] T018 [US2] Executar passo14 conforme `specs/005-entrega-validacao/quickstart.md` e registrar em `docs/validacao/005-integral.md`:S3/101 e S4/201 com duas pendências antes dos disparos simultâneos, aprovações200/200, soma exatamente uma reserva por área/data, recusa perdedora sem erro/dado alheio e inspeção dos dois históricos completos (FR-009, FR-010, FR-012; SC-002).
- [X] T019 [US2] Executar inspeção técnica do passo15 em `docs/validacao/005-integral.md`: seis rotas/JSON, versões/pin/lock, dados intactos, segredos, principal/especialistas, tools reais, identidade canônica, instruções sem regulamento, seletividade, índice atômico e ledger; deixar referências do README para fechamento apósT024, sem marcar passo15 aprovado parcialmente (FR-004, FR-005, FR-009, FR-012; SC-004).
- [X] T020 [US2] Executar gates adicionais de reserva e visitante pendentes após restart de `specs/005-entrega-validacao/quickstart.md` e registrar em `docs/validacao/005-integral.md`:autoria/IDs original e nativo/topologia/Runner/App/serviço/ADK2.2.0, retorno no solicitante, parâmetros congelados, efeito real uma vez, negação/reenvio/ID cruzado e coexistência sem consumo cruzado; diagnosticar/corrigir integração se necessário antes de aprovação (FR-010, FR-011; SC-002).
- [X] T021 [US2] Validar erros404 nas três rotas de sessão, envelope integral, visitante negado/replay/ID inválido, códigos cancelados antes/depois de restart/reset e tabela28critérios; registrar em `docs/validacao/005-integral.md` com evidências e pendências reais, sem declarar gate não executado como aprovado (FR-002, FR-003, FR-009–FR-013; SC-002, SC-004, SC-005).

## Fase 5 — US3: manual auditável e entrega pública (P2)

**Objetivo**: revisor entende agentes/regras e localiza código real no fork. **Critério independente**: manual com três seções, cinco referências efetivas, pré-requisitos/comandos suficientes e preparação de publicação sem segredos. Entrega pública só se conclui emT028/T029 após gate final.

- [X] T022 [US3] Atualizar `docs/arquitetura.md` com principal e especialistas reservas/visitantes/regulamento, responsabilidades, acionamento via sub_agents/retorno ao pai/bloqueio peers e justificativa; explicar Runner/App, identidade canônica, dois bancos e confirmação/seleção sem usar prompts como única barreira (FR-006, FR-012; SC-003).
- [X] T023 [US3] Substituir enunciado de `README.md` somente apósT004/T011/T022 por Arquitetura, Garantias e Como rodar completos; para as cinco regras cumprir “cada uma das cinco garantias aponta trecho existente e efetivo no código final; caminho planejado não é evidência”; incluir comandos/reset/variáveis/limites/modelo e link ao enunciado preservado (C505; FR-006, FR-007; SC-003).
- [X] T024 [US3] Conferir no código final todos arquivos/símbolos/trechos linkados no `README.md`, provar imposição independente do modelo, atualizar referências normativas que apontavam ao enunciado antigo e concluir passo15 no relatório `docs/validacao/005-integral.md`, sem referenciar implementação inexistente (FR-006, FR-007, FR-009, FR-012; SC-003).
- [X] T025 [US3] Auditar conteúdo/histórico entregue, `dados/`, `.env.example`, `.gitignore`, `pyproject.toml` e `uv.lock`; comparar todos arquivos iniciais a checkout confiável da base, conferir nenhuma chave/configuração privada/runtime versionados e registrar resultado em `docs/validacao/005-integral.md` sem imprimir segredos (FR-004, FR-005, FR-012; SC-004).
- [X] T026 [US3] Preparar `docs/entrega.md` com proveniência do repositório base, checklist de fork público/main, pré-requisitos de publicação e política de aceite; manter status não entregue atéT027–T029, sem tratar publicação planejada como requisito já cumprido (FR-008, FR-013).

## Fase 6 — Fechamento transversal

- [ ] T027 Ensaiar em clone limpo do commit candidato pelo README final os fluxos dos15 passos, gates extras e28critérios, registrando `docs/validacao/005-integral.md`; como fork/main público ainda não existem, manter esse item do passo15/FR-008 pendente e não declarar entrega aceita; correção exige revalidação afetada e rodada integral final emT029, sem suíte/evals/deploy/UI obrigatórios (FR-001, FR-009–FR-013; SC-001–SC-005).
- [ ] T028 Após gates funcionais deT027 aprovados (entrega pública ainda pendente), disponibilizar entrega completa em fork público do repositório base com tudo em `main`; registrar URL/commit e verificar branch/visibilidade/conteúdo em `docs/entrega.md`, sem publicar chaves, sem deploy e sem confundir setup atual com publicação executada (FR-008; SC-004).
- [ ] T029 Clonar fork público/main entregue e executar obrigatoriamente os15 passos completos, extras e28critérios pelo README final, mesmo sem mudança funcional; verificar link/referências/dados/lock/ausência de segredos e registrar resultados em `docs/validacao/005-integral.md`; qualquer falha exige correção e nova rodada final; completar `docs/entrega.md` e fornecer URL pública somente com evidências de15/15,28/28, extras e zero falhas (FR-001, FR-006–FR-013; SC-001–SC-005).

## Dependências e ordem

001–004 funcionais → T001/T002 → fundaçãoT003–T005 → US1T006–T013 → US2T014–T021 → US3T022–T026 → T027 → T028 → T029. Dentro de cada bloco seguir IDs, salvo paralelos explícitosT003/T004 (arquivos distintos, ambos apósT002). T005 dependeT004 para a fonte preservada; T009 dependeT007/T008 e não promete reset antes do fechamentoADK; T010 dependeT006/T009. T012/T013 consomem comandos/documentação deT010/T011. T019 prepara inspeção técnica, mas sóT024 fecha passo15 com manual real. T027 ensaia os fluxos e deixa publicação pendente; T029 repete avaliação integral em clone público/main, sem usar ensaio como aprovação final.

## Paralelismo por história

- US1: sequencial; reset, CLI e evidência dependem dos passos anteriores. Não paralelizar resets com API/validação.
- US2: sequencial na mesma sessão/histórico; somente aprovações distintas no passo14 são deliberadamente concorrentes como cenário de negócio, não tarefas[P].
- US3: sequencial; manual/referências dependem do conteúdo final. Exemplo seguro de trabalho paralelo restrito à fundação: T003 `storage/maintenance.py` e T004 `docs/desafio-original.md`, depoisT002.

## Estratégia incremental

MVP=setup/fundação+US1 reproduzível; não significa entrega aceita. US2 prova comportamento com manual operacional; US3 consolida README; fechamento ensaia antes de publicar o candidato e repete a avaliação integral no fork público/main antes de fornecer link e declarar aceite. Não trocar memória persistida por volátil para passar demonstração; resolver a integraçãoADK ou manter gate falho.

## Mapa de cobertura FR/SC

| Requisito | Tarefas principais |
| --- | --- |
| FR-001 | T006,T010–T012,T027,T029 |
| FR-002 | T003,T007–T011,T013,T021 |
| FR-003 | T003,T006,T008,T010,T013,T017,T021 |
| FR-004 | T002,T011,T012,T019,T025 |
| FR-005 | T002,T011,T012,T019,T025 |
| FR-006 | T004,T022–T024,T029 |
| FR-007 | T023,T024,T029 |
| FR-008 | T026,T028,T029 |
| FR-009 | T001,T004,T005,T014–T019,T021,T024,T027,T029 |
| FR-010 | T005,T014–T018,T020,T021,T027,T029 |
| FR-011 | T001,T016,T020,T021,T027,T029 |
| FR-012 | T001,T012,T015–T019,T021,T022,T024,T025,T027,T029 |
| FR-013 | T005,T013,T014,T021,T026,T027,T029 |
| SC-001 | T012,T027,T029 |
| SC-002 | T018,T020,T021,T027,T029 |
| SC-003 | T022–T024,T027,T029 |
| SC-004 | T013,T019,T021,T025,T027–T029 |
| SC-005 | T013,T017,T021,T027,T029 |

13FR+5SC=18itens, todos exigem trabalho verificável. Nenhuma tarefa sem requisito/história. ConstraintsC501–C505 citadas literalmente emT006/T007/T008/T005/T023. Nenhuma tarefa de produto concluída por gerar estes artefatos.
