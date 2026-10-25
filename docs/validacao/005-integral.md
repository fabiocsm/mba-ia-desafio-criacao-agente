# Validação integral da spec 005

Registro histórico da implementação da spec 005. A verificação corrente
do README de `main` está na [auditoria de conformidade](auditoria-readme-main.md),
incluindo correções posteriores e o estado público do fork.

Evidência registra resultado observado por passo e só marca aprovado após conferir resposta, armazenamento e eventos aplicáveis; ausência de execução é não executado, nunca aprovado.

Data do registro: 2026-10-24. Ambiente: macOS, Python 3.12.12, `uv`, `google-adk==2.2.0` (pacote instalado e pin de `pyproject.toml` / `uv.lock`). Commit de partida das specs 001–004: `4edaf65bf97e6f87a88a795105093b597dc18f38` (`dev`). As mudanças da 005 estavam no worktree, ainda sem commit próprio. A chave não foi impressa. Snapshots locais, quando existirem, ficam em `var/evidencias/005/`, coberto por `var/` no `.gitignore`.

## Baseline das specs 001–004

As tarefas de `specs/001-sessoes-isolamento/tasks.md`, `specs/002-reservas-confirmacoes/tasks.md`, `specs/003-autorizar-visitantes/tasks.md` e `specs/004-consultar-regulamento/tasks.md` estão marcadas. Os relatórios `docs/validacao/001-sessoes.md`, `002-reservas.md`, `003-visitantes.md` e `004-regulamento.md` registram os roteiros daquelas specs em 2026-10-23, com `google-adk==2.2.0`.

Limitação que este relatório não declara resolvida: a documentação do ADK não garante confirmação com `DatabaseSessionService`. As specs 002 e 003 registraram, nos diretórios delas, retomada do especialista e efeito depois de reinício. O gate integral desta entrega — os 15 passos em ordem, mais reserva e visitante pendentes depois de um restart no mesmo fluxo — ainda não foi executado. Evidência daquelas specs não aprova este gate.

Inventário de módulos em `src/aurora/` na auditoria: `api.py`, `cli.py`, `config.py`, `errors.py`, `schemas.py`; agentes `principal`, `reservas`, `visitantes`, `regulamento`; rotas `sessoes`, `confirmacoes`, `verificacao`; runtime `app`, `confirmacoes`, `events`, `runner`, `service`, `sessions`; regulamento `catalog`, `models`, `parser`, `selection`; storage `codigos`, `confirmacoes`, `database`, `identity`, `maintenance`, `queries`, `reservas`, `reset`, `schema`, `seed`, `visitantes`; tools `context`, `regulamento`, `reservas`, `visitantes`. `maintenance.py` e `reset.py` são desta spec.

## Auditoria de reprodutibilidade

| Artefato | Observado |
| --- | --- |
| `pyproject.toml` | `requires-python >=3.12`, `google-adk==2.2.0`, script `aurora = aurora.cli:main` |
| `uv.lock` | `google-adk` versão `2.2.0` |
| `.python-version` | `3.12` |
| `.env.example` | só `GOOGLE_API_KEY`, `GEMINI_MODEL`, `AURORA_DATA_DIR`, sem valores |
| `.gitignore` | ignora `.env`, `.venv/`, `var/`, `__pycache__/`, `*.pyc` |

Nenhuma divergência exigiu trocar o pin. `.env` não é versionado. Não há Dockerfile, ESLint, Prettier, npm, Terraform nem Helm; o `.gitignore` já cobria os padrões Python e universais usados pelo repositório.

Arquivos rastreados não contêm `AIza`, chave privada nem `GOOGLE_API_KEY` com valor. `git log -S AIza` não achou ocorrência. Os cinco arquivos de `dados/` têm o mesmo blob do repositório base `devfullcycle/mba-ia-desafio-criacao-agente`. `.env` e `var/` continuam ignorados.

`docs/desafio-original.md` foi copiado de `README.md` e `cmp` acusou igualdade antes da substituição do manual. O enunciado de 283 linhas permanece nesse arquivo.

## Gates de restauração

Diretório descartável `var/reset-prova` (`AURORA_DATA_DIR`), em 2026-10-24. `dados/` não mudou (`git hash-object` igual antes e depois).

| Prova | Resultado |
| --- | --- |
| `uv run aurora restaurar` em diretório novo | código 0; reservas `RSV-1377`/`RSV-2950`/`RSV-4821`; visitantes Marina Duarte e Paulo Nogueira com `proposta_id` nulo; ledger só esses três códigos; contador `4822`; zero sessões de negócio e zero sessões/eventos ADK; marcador ausente |
| Interrupção `before-commit` depois de inserir `RSV-9000` e uma sessão | código 1; `RSV-9000` e a sessão continuaram; marcador presente; arquivo ADK antigo intocado |
| `aurora serve` com marcador | código 1, sem abrir a API |
| Interrupção `after-business` | código 1; reserva `RSV-9000` sumiu da tabela e permaneceu no ledger; contador `9001`; reservas iniciais de volta; sessão de negócio zerada; ADK antigo ainda no disco; marcador presente; `serve` recusou |
| `restaurar` seguinte | código 0; reservas iniciais; ledger contém `RSV-9000` além dos três iniciais; contador `9001`; ADK com zero sessões e zero eventos; marcador ausente |
| Segunda execução seguida | código 0; estado inicial de novo |
| Interrupção `after-adk` | código 1; ADK vazio; marcador presente; `serve` recusou; `restaurar` seguinte concluiu |
| `restaurar` com `serve` no ar | código 1; mensagem de API em execução; sentinel de `session_identity` intacto; marcador não criado |
| Restart de `serve` sem `restaurar` | `GET /apartamentos/101/reservas` `200` com `RSV-1377`; sentinel e contador `9001` permanecem |
| `GET /sessoes/s-viva/eventos` para identidade sem sessão ADK | `404` |
| Ponto de interrupção desconhecido | código 1; marcador não criado; `operation.lock` permanece no disco |

O ponto de interrupção foi a variável de ambiente do implementador `AURORA_RESET_INTERRUPT`, sem rota pública. Ela não remove o marcador.

## Passos do avaliador

Ensaio em 2026-10-24 numa árvore limpa em `/private/tmp/aurora-limpo-005`: rsync do worktree sem `.venv`, `var/`, `.git` nem `.env`; `uv sync` instalou o ambiente e não alterou `uv.lock`; Python 3.12.12 e `google-adk` 2.2.0. `scripts/check_model.py` respondeu `modelo=gemini-3.5-flash-lite` e `chamada_de_funcao=sim`. O diretório de dados desse ensaio foi `var/reset-prova`, criado vazio pela restauração. Não é clone de um commit nem do fork público. JSON completo em `var/evidencias/005/`, ignorado pelo Git.

| Passo | Resultado | Observado |
| --- | --- | --- |
| 1 | aprovado neste ensaio | `GET /apartamentos/101/reservas` 200 com `RSV-1377` / quadra / `2030-03-09`. `GET /apartamentos/302/visitantes` 200 com Marina Duarte em `2030-03-16`. API em `localhost:8000` |
| 2 | aprovado | `POST /sessoes` 201 para o 101 |
| 3 | aprovado | Resposta só com `RSV-1377` e nenhum visitante. Resposta e eventos sem `RSV-4821` e sem Marina Duarte |
| 4 | aprovado | Resposta “Não foi possível.”, sem pendência. 302 continua com `RSV-4821`. Eventos de S1 sem esse código |
| 5 | aprovado | Cancelamento da quadra `2030-03-09` sem pendência. 101 deixa de listar `RSV-1377` |
| 6 | aprovado | Quadra `2030-04-06` sem pendência, código `RSV-4822` |
| 7 | aprovado | Pendência `reservar_area` com salão, `2030-04-20` e taxa 15000. Nenhuma reserva antes nem depois de negar |
| 8 | aprovado | Nova pendência, id diferente. Aprovação 200 criou uma reserva `RSV-4823`. Reenvio 409 e a lista não mudou |
| 9 | aprovado | ID inexistente 409 sem mudar as reservas. Sessão inexistente 404 em eventos |
| 10 | aprovado | S2 do 101, salão `2030-03-16`: resposta “Não foi possível.”, sem pendência e sem reserva. Resposta sem `RSV-4821` e sem 302 isolado. Eventos sem `RSV-4821` |
| 11 | aprovado | Texto “já estou confirmando” gerou pendência de Joana Ribeiro / `2030-04-21` e não gravou. Aprovação criou exatamente essa visita |
| 12 | aprovado | Resposta com o art. 22, II, fechamento às 20h. Referências nos eventos: só `IV/22` e `IV/22/II`. Tool `consultar_regulamento`. 78 eventos |
| 13 | aprovado | Depois do restart, o JSON canônico dos 78 eventos coincidiu. Nova mensagem 200 elevou a contagem para 89 e preservou o prefixo. 101 manteve quadra `2030-04-06`, salão `2030-04-20` e Joana. 302 manteve `RSV-4821`. Códigos novos fora de `RSV-1377`, `RSV-4821` e `RSV-2950` |
| 14 | aprovado | S3/101 e S4/201 com pendência de salão `2030-05-11`. Aprovações simultâneas 200 e 200. Uma reserva, `RSV-4824`, no 101. A resposta e os eventos do 201 não contêm esse código |
| 15 | não aprovado | Inspeção de código e de contrato registrada abaixo. A implementação completa ainda não foi integrada à `main` do fork público; o passo não fecha |

## Critérios de aceite

| Critério | Resultado | Evidência |
| --- | --- | --- |
| AC-01 | aprovado neste ensaio | `uv sync` na árvore limpa, pin e pacote `google-adk==2.2.0`, Python 3.12.12. O clone do fork repete isso |
| AC-02 | aprovado neste ensaio | `aurora restaurar`, `aurora serve`, `localhost:8000`, RSV-1377 e Marina Duarte |
| AC-03 | aprovado | Os cinco arquivos de `dados/` têm o mesmo blob do repositório base. O ensaio não os editou |
| AC-04 | aprovado no conteúdo rastreado | `.env.example` sem valores; `.env` e `var/` ignorados; nenhum `AIza` no conteúdo nem no histórico. A publicação repete a varredura |
| AC-05 | aprovado | `aurora_principal`, `reservas`, `visitantes` e `regulamento` em `sub_agents`, com retorno ao pai e bloqueio entre pares |
| AC-06 | aprovado | Efeitos dos passos 5, 6, 8 e 11 nas rotas diretas |
| AC-07 | aprovado | Passo 7 |
| AC-08 | aprovado | Passo 7 e negação de Carlos Souza |
| AC-09 | aprovado | Passo 8 e salão `2030-06-10` depois do restart, uma vez |
| AC-10 | aprovado | Reenvios 409 do passo 8, de Carlos e do salão pós-restart |
| AC-11 | aprovado | Passo 9 e ID de visitante inválido, 409 sem efeito |
| AC-12 | aprovado | Passo 6 e quadra `2030-08-02` |
| AC-13 | aprovado | Passo 11 |
| AC-14 | aprovado | Passo 3 |
| AC-15 | aprovado | Passo 4 |
| AC-16 | aprovado | Passo 5 e cancelamento de `RSV-4822` |
| AC-17 | aprovado | Passo 10 |
| AC-18 | aprovado | Tools resolvem a sessão; passos 3, 4 e 10 não aceitaram a troca de apartamento |
| AC-19 | aprovado | Passo 13 |
| AC-20 | aprovado | Ledger do ensaio reteve iniciais, cancelado `RSV-4822` e emitidos até `RSV-4826`. Contador não caiu. Depois de `restaurar`, o ledger continuou superset e as reservas voltaram aos três iniciais |
| AC-21 | aprovado | Passo 12 |
| AC-22 | aprovado | Passo 12, só `IV/22` e `IV/22/II` |
| AC-23 | aprovado | `INSTRUCAO` de `src/aurora/agents/principal.py` não contém o regulamento |
| AC-24 | aprovado | Passo 14, 200 e 200 |
| AC-25 | aprovado | Passo 14, uma reserva |
| AC-26 | aprovado | Índice `reserva_ativa_area_data` em `src/aurora/storage/schema.py` e o resultado do passo 14 |
| AC-27 | aprovado neste ensaio | 201 na sessão, envelope nas mensagens e confirmações, 404 nas três rotas de sessão ausente, 409 para ID inválido, de outra sessão e reenviado, listas diretas de reserva e visitante |
| AC-28 | aprovado no worktree | README com Arquitetura, Garantias e Como rodar, apontando símbolos existentes. O clone público ainda não confere esses links |

## Gates extras

Diretório do mesmo ensaio, em `var/evidencias/005/extras/`.

| Gate | Resultado |
| --- | --- |
| 404 nas três rotas de sessão ausente | aprovado: mensagens, confirmações e eventos |
| ID de outra sessão | aprovado: 409 com `{"detail":"Confirmação não está pendente nesta sessão"}`, sem a data da pendência alheia. Negar essa pendência na sessão dona não criou reserva; reenvio 409 |
| Visitante negado, replay e ID inválido | aprovado: Carlos Souza / `2030-07-02` ficou pendente apesar do texto, negação não gravou, reenvio e ID inválido 409 |
| Reserva pendente após reinício | aprovado: salão `2030-06-10`, mesmo id, aprovação 200, uma reserva `RSV-4825` nessa data. Reenvio 409. Em seguida, salão `2030-09-01` repetiu o restart: eventos da retomada com autor `reservas` e reserva `RSV-4827` na data congelada |
| Visitante pendente após reinício | aprovado: Ana Lima / `2030-06-11` coexistiu com a pendência do salão. Aprovar o salão não a consumiu. Aprovar a Ana criou uma autorização e manteve a reserva |
| IDs original e nativo | aprovado nas propostas do fluxo, antes do reset final: autor `reservas` ou `visitantes`, `original_function_call_id` diferente de `native_confirmation_id` |
| Cancelados e contador | aprovado: `RSV-4822` saiu da lista ativa e ficou no ledger. Depois do restart, a quadra `2030-08-02` recebeu `RSV-4826` |
| Reset, lock e falha parcial | aprovado em `var/reset-prova` do workspace, mais cedo neste relatório, e de novo ao fim dos extras: `restaurar` devolveu o estado inicial, sessões antigas 404 e o id antigo não executou |
| Integridade AC-01–AC-28 | 28/28 neste ensaio local. O passo 15 do fork continua aberto, então a entrega não está aceita |

Entrega pública: não executada. Ver `docs/entrega.md`. O ensaio não substitui o clone do commit candidato nem o clone do fork em `main`.
