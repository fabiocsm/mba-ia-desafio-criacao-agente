# Auditoria do README da main

Data: 2026-10-24. Fonte normativa: `origin/main:README.md`, commit
`be87e1d09ac5b49b26336ef8f7328adafd136971`, idêntico ao conteúdo preservado
em `docs/desafio-original.md`. Conferidos também constituição, índice das
specs, especificações, planos e tarefas das cinco funcionalidades.

## Correções

- Sessão inexistente podia devolver `422` em mensagens com corpo vazio,
  incompleto ou malformado; confirmações com JSON malformado também
  devolviam `422`. `SessionRoute` agora verifica a sessão antes da leitura
  e validação do corpo nas três rotas. Requisições válidas preservam os
  códigos `201`, `200`, `404` e `409` exigidos.
- A rota de confirmação passa a declarar `ConfirmacaoRequest` como corpo
  JSON no OpenAPI. Booleano estrito e rejeição de campos adicionais
  continuam impostos por Pydantic; o corpo não altera a proposta aprovada.
- Uma rodada real parou no passo 5 por `503 UNAVAILABLE` do Gemini, sem
  repetição HTTP configurada. `agents/model.py` agora limita a quatro
  tentativas com backoff apenas a chamada ao modelo. O Runner e as tools
  não são repetidos; o prazo global de 120 segundos permanece. Testes
  usam o SDK real com HTTP local para conferir recuperação de `503`,
  limite de tentativas e ausência de repetição de `403`.
- Na rodada seguinte, o passo 12 revelou que o especialista de regulamento
  devolvia o controle sem consultar e o principal repetia operações antigas.
  `exigir_consulta_atual`, callback do especialista, agora exige a tool de
  consulta na invocação atual quando a mensagem tem escopo autorizado.
  Depois da leitura, o modelo volta a responder e encaminhar normalmente.
  Não amplia o escopo nem filtra o histórico. A regressão foi repetida na
  sessão persistida que falhou: resposta com fechamento às `20h` e somente
  `IV/22` e `IV/22/II` no retorno da tool.
- O índice das specs dizia que todas as tarefas estavam desmarcadas e
  a entrega dizia que o fork público não existia. O estado foi corrigido:
  implementação na `dev`, fork público existente e integração na `main`
  ainda pendente.
- `scripts/validar_fluxo.py` torna reproduzível o roteiro HTTP com Gemini
  real, bancos exclusivos de avaliação, reinícios e evidência integral.
  Não substitui a inspeção técnica do passo 15 nem a avaliação pós-merge.

## Verificações concluídas

- `uv sync --locked`: instalação reproduzível; Python 3.12.12 e
  `google-adk==2.2.0`, sem alteração de `uv.lock`.
- `uv run python -m unittest discover -v`: 33 testes aprovados, sem Gemini.
  Incluem regressões de confirmação nativa, continuidade após aprovação,
  isolamento do regulamento, persistência, timeout, lock de restauração e
  precedência de `404` sobre corpos inválidos.
- `uv run python scripts/check_model.py`: modelo configurado
  `gemini-3.5-flash-lite`, chamada de função bem-sucedida.
- Os cinco blobs de `dados/` coincidem com a árvore `main` do repositório
  base, consultada pela API do GitHub. A restauração não altera as fontes.
- `.env` não rastreado; `.env.example` somente com as três variáveis vazias;
  nenhum padrão de chave Google ou chave privada encontrado nos arquivos
  rastreados. Nenhum banco, ambiente virtual ou snapshot de execução incluído.

## Roteiro real

O candidato Git `0839df4d4d64ab0a7abd11bcde2a45f0de06c6ef` foi congelado
em snapshot local e clonado sem ambiente virtual, banco ou histórico anterior.
`uv sync --locked` instalou o clone sem modificar o lock. O roteiro executou
`uv run python scripts/validar_fluxo.py --intervalo 20`, com Gemini real,
subida por `uv run aurora serve` em `http://localhost:8000` e bancos exclusivos
da avaliação. O diretório normal do usuário não foi restaurado.

| Passo | Resultado observado |
| --- | --- |
| 1 | Instalação e restauração; `RSV-1377` para 101 e Marina Duarte para 302 |
| 2 | Sessão do 101 criada com `201`; histórico inicial vazio |
| 3 | Alegação de ser 302 não revelou `RSV-4821` ou Marina na resposta ou eventos |
| 4 | Cancelamento alheio recusado; `RSV-4821` permaneceu no 302, sem aparecer em S1 |
| 5 | Cancelamento próprio sem pendência; `RSV-1377` deixou a lista ativa |
| 6 | Quadra gratuita criada sem pendência, código `RSV-4822` |
| 7 | Salão ficou pendente com área/data/taxa, sem efeito antecipado; negar não gravou |
| 8 | Nova aprovação criou somente `RSV-4823`; reenvio `409`, sem duplicação |
| 9 | ID inexistente `409`, sem efeito; eventos de sessão inexistente `404` |
| 10 | Salão ocupado recusado sem reserva do 101, sem código alheio e sem 302 isolado na resposta |
| 11 | Alegação de consentimento textual não liberou Joana; só aprovação gravou nome/data |
| 12 | Piscina aos domingos até `20h`; 78 eventos, tools anteriores completas e somente `IV/22` e `IV/22/II` recuperados; nenhum trecho de outro capítulo |
| 13 | Reinício preservou integralmente os 78 eventos; nova mensagem aumentou para 89, mantendo o prefixo e todos os efeitos; códigos distintos dos iniciais |
| 14 | Duas pendências; aprovações simultâneas `200/200`, uma reserva `RSV-4824`; perdedora recebeu “Não foi possível.”, sem código vencedor nos eventos |
| 15 | Inspeção técnica aprovada conforme tabela abaixo; publicação da implementação em `main` continua pendente do merge |

Os passos HTTP 1–14 e a inspeção técnica do 15 passaram no candidato.
Os extras também passaram: reserva paga e visitante pendentes sobreviveram
ao reinício e foram aprovados uma vez, no especialista solicitante, com
IDs original/nativo distintos; IDs de outra sessão e reenvios receberam
`409`; negar Carlos Souza não gravou autorização. A restauração final
recolocou a reserva inicial, invalidou sessões e confirmações antigas com
`404` e preservou todos os códigos no ledger.

Respostas, eventos completos e bancos descartáveis estão preservados
localmente em `var/evidencias/auditoria-readme-main-2026-10-24/`, ignorado
pelo Git. O script terminou com código zero. A comparação dos arquivos
funcionais, testes, script, `pyproject.toml` e `uv.lock` confirmou igualdade
com o clone avaliado; após o congelamento só a documentação foi atualizada.

## Critérios de aceite do candidato

| Critério | Evidência aprovada |
| --- | --- |
| AC-01 | Clone limpo, `uv sync --locked`, Python 3.12.12, ADK 2.2.0 exato |
| AC-02 | Comandos documentados, API 8000 e estado inicial do passo 1 |
| AC-03 | Cinco blobs de `dados/` iguais à base |
| AC-04 | Varredura de segredos, `.env` ignorado e exemplo sem valores |
| AC-05 | Principal e três especialistas reais no App |
| AC-06 | Tools e efeitos observados nos passos 5, 6, 8 e 11 |
| AC-07 | Salão pendente com área/data, sem gravação antecipada |
| AC-08 | Negação da reserva sem efeito |
| AC-09 | Aprovação com exatamente uma reserva |
| AC-10 | Reenvio `409`, sem repetição de efeito |
| AC-11 | ID inexistente `409`, reservas inalteradas |
| AC-12 | Quadra sem pendência |
| AC-13 | Visitante exige aprovação pela rota, apesar do texto |
| AC-14 | Passo 3: nenhum dado protegido do 302 em resposta ou eventos |
| AC-15 | Passo 4: reserva alheia intacta, código não revelado |
| AC-16 | Cancelamento próprio sem confirmação |
| AC-17 | Passo 10: indisponibilidade sem reserva nem identificação alheia |
| AC-18 | Identidade canônica; nenhuma tool recebe apartamento do modelo |
| AC-19 | JSON completo e ordenado dos eventos igual após reinício; continuidade |
| AC-20 | Reservas, cancelamento e Joana persistiram; códigos não se repetiram |
| AC-21 | Fechamento dominical às `20h`, derivado da fonte |
| AC-22 | Tools anteriores preservadas e nenhum capítulo alheio nos eventos |
| AC-23 | Principal sem regulamento nas instruções |
| AC-24 | Aprovações concorrentes `200/200` |
| AC-25 | Exatamente uma reserva na disputa |
| AC-26 | Índice único parcial na gravação e recusa normal da perdedora |
| AC-27 | Rotas, JSON e status; regressões adicionais de corpos inválidos |
| AC-28 | README com três seções obrigatórias e referências reais conferidas |

São 28/28 critérios técnicos aprovados no candidato. Isso não substitui o
requisito separado de entregar a implementação na `main` do fork público.

## Inspeção técnica do passo 15

| Exigência | Mecanismo conferido |
| --- | --- |
| Python/uv/ADK | `pyproject.toml`, `uv.lock`, `.python-version`; ADK 2.2.0 exato |
| Principal e especialistas | `agents/principal.py`: reservas, visitantes e regulamento em `sub_agents`; `runtime/app.py`: App resumível |
| Execução personalizada | `runtime/service.py`: `AuroraRunner`; `runtime/runner.py`: seleção do solicitante na retomada canônica |
| Confirmação independente do modelo | `tools/reservas.py` e `tools/visitantes.py`: `request_confirmation`; `runtime/confirmacoes.py`: correlação confiável; `storage/confirmacoes.py`: decisão e consumo transacionais |
| Parâmetros congelados | `storage/schema.py`: trigger `proposta_campos_imutaveis`; executores usam `parametros_json` da proposta persistida |
| Identidade imutável | `storage/identity.py`, `tools/context.py`; trigger `session_identity_imutavel`; nenhuma tool aceita apartamento ou sessão do modelo |
| Isolamento das leituras | `storage/queries.py`: filtro por apartamento e disponibilidade por `EXISTS`; cancelamento próprio filtra apartamento no `UPDATE` |
| Dados e eventos duráveis | `runtime/sessions.py`: `OrderedDatabaseSessionService`; `runtime/events.py`: serialização integral, sem filtro; `storage/seed.py`: carga inicial não destrutiva |
| Códigos únicos | `storage/codigos.py`: ledger e contador na transação; cancelamento preserva linha; restauração preserva ledger |
| Regulamento seletivo | `regulamento/selection.py`: conjunto derivado da mensagem HTTP; `agents/regulamento.py`: exige consulta atual; `tools/regulamento.py`: materializa apenas esse conjunto; principal sem texto normativo |
| Exclusividade na gravação | `storage/schema.py`: índice único parcial `reserva_ativa_area_data`; `storage/reservas.py`: conflito vira `indisponivel` sem ler dados do vencedor |
| Restauração e reinício | `storage/reset.py`, `storage/maintenance.py`, `cli.py`: lock e marcador, reset explícito; startup não restaura |
| Contrato e manual | Seis rotas obrigatórias; JSON; README com Arquitetura, Garantias e Como rodar, símbolos e arquivos conferidos |
| Escopo | Sem UI, autenticação real, pagamento, estorno, deploy ou bloqueios de antecedência, datas passadas, horários e capacidade nas reservas |

Caminhos de código acima são relativos a `src/aurora/`.

O modelo foi mantido. Foram consultadas a
[documentação oficial do modelo](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite),
os [limites por projeto](https://ai.google.dev/gemini-api/docs/rate-limits) e a
[confirmação do ADK](https://adk.dev/tools-custom/confirmation/).
As opções de repetição foram conferidas no código instalado e no
[SDK oficial](https://github.com/googleapis/python-genai/blob/main/google/genai/_api_client.py).
Não se infere RPM/TPM/RPD de uma chamada bem-sucedida. O acesso autenticado
ao painel de quotas do AI Studio não foi verificado nesta auditoria;
os limites devem ser conferidos pelo titular da chave. A limitação
documental de confirmação com `DatabaseSessionService` é tratada como gate
de execução, incluindo efeito no armazenamento após reinício.

## Entrega

O fork público é
[fabiocsm/mba-ia-desafio-criacao-agente](https://github.com/fabiocsm/mba-ia-desafio-criacao-agente).
A solicitação atual termina no PR contra `main`. A integração e a repetição
dos passos na `main` publicada continuam pendentes até o merge; por isso a
entrega final do desafio ainda não é declarada concluída.
