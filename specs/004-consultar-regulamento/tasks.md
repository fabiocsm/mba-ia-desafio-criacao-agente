# Tarefas: consulta seletiva ao regulamento

**Entrada**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contrato](contracts/regulamento.md), [quickstart.md](quickstart.md).
**Estado**: implementação concluída em 2026-10-23. Depende da 001; regressões de mutação usaram 002/003. Validação manual em `docs/validacao/004-regulamento.md`.

## Fase 1 — Setup

- [X] T001 Conferir a base001 em `pyproject.toml`, `uv.lock`, `src/aurora/runtime/app.py`, `src/aurora/runtime/service.py` e `src/aurora/tools/context.py`, preservando Python>=3.12, uv, google-adk==2.2.0, identidade canônica, dois SQLite, Runner/App resumível e flags de transferência; registrar baseline em `docs/validacao/004-regulamento.md` (FR-003, FR-008).
- [X] T002 Preparar pacote de leitura em `src/aurora/regulamento/__init__.py` e diretório de evidências ignorado em `.gitignore`, sem acrescentar dependência/serviço de busca nem editar `dados/regulamento.md`; confirmar hash/comparação com base em `docs/validacao/004-regulamento.md` (FR-009).

## Fase 2 — Fundação: fronteira seletiva antes de qualquer história

Nenhuma história inicia antes desta fase. Leitura completa para indexar ocorre só fora do contexto/eventos; a proteção não depende de prompt.

- [X] T003 Definir tipos internos em `src/aurora/regulamento/models.py` com constraints literais: “`path` é fixo em `dados/regulamento.md`, somente leitura”; “`id` é referência estrutural única de capítulo/artigo/subunidade existente”; “`texto` preserva literalmente apenas a unidade selecionada da fonte”; “`session_id` vem da identidade canônica e é obrigatório”; “`execution_nonce` é aleatório, próprio da execução HTTP e obrigatório, distinto do invocation_id ADK”; “`unidades` contém somente IDs autorizados pelo texto original; pode ser vazio”; “`status` pertence a `ok`, `esclarecer`, `sem_base`”; “`trechos` é vazio para `esclarecer` e `sem_base`” (FR-001, FR-002, FR-007–FR-009).
- [X] T004 Implementar parser estrutural em `src/aurora/regulamento/parser.py`, lendo fonte fixa somente fora de Runner/prompts/tool results/eventos, separando capítulo/artigo/inciso/parágrafo com referências existentes e preservando literalidade; índice reconstruível sem gravação normativa, erros sem texto integral (FR-001, FR-002, FR-009).
- [X] T005 Implementar autorização de leitura em `src/aurora/regulamento/selection.py` e integração em `src/aurora/runtime/service.py`: mensagem HTTP original + identidade canônica + nonce aleatório próprio da execução HTTP (distinto do invocation_id ADK, que o SDK gera; não passar como ID de retomada), ContextVar confiável por execução/reset por token em finally, conjunto fechado antes do Runner e verificação antes de materializar trecho; sem scope válido, confirmação sem pergunta e referência vaga retornam esclarecimento sem texto; não usar query/state/args LLM como autoridade nem ampliar com chamadas sucessivas (FR-002, FR-006–FR-009).

## Fase 3 — US1 P1: saber horário correto da piscina (MVP)

**Objetivo**: pergunta/paráfrase piscina domingo →20h derivado da fonte.
**Critério independente**: Q1 do quickstart, response200 e artigo22II sem horários contraditórios; nenhuma outra unidade alheia.

- [X] T006 [US1] Criar catálogo de assunto/intenção em `src/aurora/regulamento/catalog.py`, normalizando acentos/caixa e aliases portugueses para piscina+horário+domingo/feriado, autorizando somente art22 caput estritamente necessário/incisoII, referências validadas pelo parser; não duplicar20h no prompt/catálogo, usar literal da fonte (FR-001, FR-004).
- [X] T007 [US1] Implementar `consultar_regulamento(tool_context)` em `src/aurora/tools/regulamento.py`, sem parâmetros LLM e com schema estrito: resolver identidade da001, conferir sessão canônica e scope/nonce da execução corrente instalado ao redor do Runner e só então recuperar conjunto mínimo autorizado; retorno ok com referências/texto ou fallback com trechos vazios, sem leitura administrativa/escrita/consentimento (FR-001, FR-002, FR-004, FR-006–FR-007).
- [X] T008 [US1] Criar especialista em `src/aurora/agents/regulamento.py` e registrá-lo via `src/aurora/agents/principal.py` e `src/aurora/runtime/app.py`, preservando sub_agents/mode chat/parent permitido/peers bloqueados e App resumível; somente tool de leitura, instruções sem corpo do documento, respostas baseadas na fonte e encaminhamento de retorno pelo principal (FR-001, FR-003–FR-004).
- [X] T009 [US1] Integrar resultado e fallback determinístico em `src/aurora/runtime/service.py`: status esclarecer pede tema e sem_base informa ausência sem norma inventada, preservar envelope/200 e todas pendências do banco; sessão inexistente404 antes do Runner em `src/aurora/api_routes/sessoes.py` (FR-004, FR-006–FR-007).
- [X] T010 [US1] Executar Q1 e paráfrases com sessão real via API, conferir20h art22II e tool result mínimo, anotar status/IDs/fontes sem chave em `docs/validacao/004-regulamento.md`; se acesso/quota do modelo impedir, registrar bloqueio sem marcar sucesso (FR-001, FR-004; SC-001).

## Fase 4 — US2 P1: consultar sem carregar capítulos alheios

**Objetivo**: demonstrar pertinência em todos eventos e ampliar catálogo sem expandir autoridade.
**Critério independente**: Q2, histórico com todas calls anteriores, zero capítulos alheios em consulta piscina; casos vagos/sem fonte/injeção não carregam tudo.

- [X] T011 [US2] Ampliar `src/aurora/regulamento/catalog.py` com assuntos/intentos e referências estruturais dos14 capítulos, sem respostas duplicadas: unir só unidades de perguntas específicas múltiplas; intenção insuficiente pede foco, tema claro sem regra produz sem_base; sem busca global, expansão por remissão ou capítulo inteiro (FR-001, FR-002, FR-007, FR-009).
- [X] T012 [US2] Endurecer política em `src/aurora/regulamento/selection.py`: pedido genérico/integral e comandos técnicos de topics/path/tool não autorizam temas, correspondência incerta/tema só em comando de controle pede esclarecimento; rejeitar tentativa de forjar scope/args ou ampliar consultas sucessivas, sem texto normativo em erro (FR-002, FR-007, FR-009).
- [X] T013 [US2] Integrar calls/results/transfers completos ao adaptador existente em `src/aurora/runtime/sessions.py` e `src/aurora/runtime/events.py`, sem log do índice inteiro, sem compactação e sem filtro na persistência/GET para esconder violação; fonte completa não entra no state ou instruções (FR-002, FR-003, FR-005).
- [X] T014 [US2] Executar Q2 em sessões reais, inspecionar todos eventos anteriores e novos, instruções, vários temas/ambiguidade/sem fonte/injeção, duas consultas concorrentes com escopos diferentes e erro de argumentos extras; registrar igualdade de GETs repetidos e zero vazamento em `docs/validacao/004-regulamento.md` (FR-002–FR-003, FR-005, FR-007, FR-009; SC-002).

## Fase 5 — US3 P2: voltar a consultas próprias após dúvida

**Objetivo**: preservar estado, pendências, identidade e histórico em retorno/reinício.
**Critério independente**: Q3, snapshots de negócio iguais; JSON integral idêntico depois do restart e nova mensagem na sessão original.

- [X] T015 [US3] Integrar retorno do regulamento ao principal/reservas/visitantes em `src/aurora/agents/regulamento.py` e `src/aurora/runtime/service.py`, preservando identidade imutável e listagem própria; consulta não cria/decide pendência, não modifica negócio nem acrescenta bloqueios de horário/prazo/data passada/capacidade (FR-006, FR-008).
- [X] T016 [US3] Garantir reconstrução isolada do índice no startup em `src/aurora/runtime/app.py` e scope novo somente por nova mensagem em `src/aurora/runtime/service.py`, sem Runner/eventos novos por startup ou GET, sem scope herdado na confirmação e sem restaurar dados; conservar dois bancos/caminhos e prefixo integral do histórico (FR-005, FR-008–FR-009).
- [X] T017 [US3] Executar Q3 comparando reservas/visitantes/pendências/identidade antes/depois da consulta, retorno às próprias, tentativa cruzada e reinício sem restaurar; comparar JSON/contagem integral e nova mensagem bem-sucedida, registrando evidências em `docs/validacao/004-regulamento.md` (FR-005–FR-006, FR-008; SC-003–SC-004).
- [X] T018 [US3] Revalidar após acrescentar terceiro especialista os fluxos de reserva paga e visitante com001–003 implementadas, usando `src/aurora/runtime/confirmacoes.py`, `src/aurora/runtime/runner.py` e rotas diretas: autor correto, aprovação com efeito real antes/depois de restart, negação, replay/inválido/alheio e pendências preservadas; registrar resultados/impedimentos em `docs/validacao/004-regulamento.md` (FR-006, FR-008).

## Fase 6 — Acabamento transversal

- [X] T019 [P] Documentar responsabilidades, acionamento, motivo do especialista, parser fora do contexto e fronteira de seleção com referências reais em `docs/arquitetura.md`; não substituir README enunciado nesta feature (FR-002–FR-003, FR-005).
- [X] T020 [P] Atualizar `docs/operacao.md` com fluxo de consulta, esclarecimentos, modelo herdado/limites operacionais, reinício persistente e preservação das pendências; nenhuma restauração automática ou serviço externo novo (FR-006–FR-009).
- [X] T021 Executar checklist final do `specs/004-consultar-regulamento/quickstart.md`, verificar fonte idêntica à base, contrato, eventos íntegros e regressões de sigilo dos passos3/4/10; consolidar evidência e pendências em `docs/validacao/004-regulamento.md`, entregando à005 os gates para repetir os15 passos completos (FR-001–FR-009; SC-001–SC-004).

## Dependências e oportunidades de paralelo

001 funcional → T001–T002 → T003–T005 → US1(T006–T010) → US2(T011–T014) → US3(T015–T018) → T019/T020 → T021. 002/003 são necessárias para T018 e parte de Q3; não para provar recuperação somente leitura. Dentro de cada fase, ordem sequencial por dependência explícita, não marcar [P] em arquivos compartilhados.

US1: catálogo → tool → agente → resposta → validação, sem paralelo seguro nesta decomposição. US2: expansão → endurecimento → eventos → verificação, também sequencial. US3: retorno → restart → estado → regressões; evidências compartilham arquivo e são sequenciais. Exemplo de paralelismo real: após histórias completas, T019 em `docs/arquitetura.md` e T020 em `docs/operacao.md` são independentes, antes de T021. [P] é oportunidade futura, não solicitação de execução paralela deste setup.

## Estratégia e cobertura

MVP=setup/fundação+US1, já com seletividade antes de contexto. Acrescentar US2 e US3 e só então concluir feature. Para cada história, executar critério independente; não marcar tarefas concluídas por existir plano/análise. Corrigir falha de gate e repetir fluxos afetados;005 valida conjunto integral.

| Requisito/critério | Tarefas |
| --- | --- |
| FR-001 | T003, T004, T006–T008, T010, T011, T021 |
| FR-002 | T003–T005, T007, T011–T014, T019, T021 |
| FR-003 | T001, T008, T013, T014, T019, T021 |
| FR-004 | T006–T010, T021 |
| FR-005 | T013, T014, T016, T017, T019, T021 |
| FR-006 | T005, T007, T009, T015, T017, T018, T020, T021 |
| FR-007 | T003, T005, T007, T009, T011, T012, T014, T020, T021 |
| FR-008 | T001, T003, T005, T015–T018, T020, T021 |
| FR-009 | T002–T005, T011, T012, T014, T016, T020, T021 |
| SC-001 | T010, T021 |
| SC-002 | T014, T021 |
| SC-003 | T017, T021 |
| SC-004 | T017, T021 |

Total21: setup2, fundação3, US1=5, US2=4, US3=4, acabamento3. P1 histórias1/2; P2 história3. Duas tarefas [P], cada uma em arquivo independente. Formato: caixas, IDsT001–T021, labels US somente nas fases correspondentes e caminhos de destino explícitos.
