# Revisão do PR 1

Data: 2026-10-24. PR: https://github.com/fabiocsm/mba-ia-desafio-criacao-agente/pull/1.
Escopo inicial: `origin/main..936489b`, com base em `be87e1d`.
Consultados AGENTS.md, constituição, enunciado, README, índice e artefatos das specs.
Três revisores cobriram runtime/API/tools, armazenamento/operação e regulamento/evidências.

## Achados e correções

| ID | Severidade | Problema reproduzido | Resultado |
| --- | --- | --- | --- |
| R1-1 | P2 | “Qual o horário de abertura e encerramento da piscina no domingo?” retornava `esclarecer`, sem fonte para responder o fechamento. | Sinais explícitos de abertura/fechamento/encerramento recuperam somente `IV/22` e `IV/22/II`. |
| R1-2 | P2 | Perguntar se é permitido alugar a vaga a alguém de fora recuperava `XI/77`, sobre demarcação, sem a regra de locação `XI/80`. | Intenções de aluguel, locação e cessão recuperam `XI/80` e seu parágrafo; a intenção genérica de vaga não acrescenta `XI/77`. |

As alterações estão em `src/aurora/regulamento/catalog.py` e
`src/aurora/regulamento/selection.py`. O documento original, os prompts,
as tools de negócio, o contrato e as dependências permanecem iguais.
Não foram encontrados outros problemas verificados acima do limiar de confiança da revisão.

Uma unidade de correção serial alterou esses dois arquivos e
`tests/test_regulamento_selection.py` / `tests/test_regulamento_runtime.py`.
Os testes novos falharam antes das correções. O teste de runtime usa Runner/App
e SQLite reais, com modelo programado, conferindo trechos, eventos e reinício.

## Revisão das correções

A primeira solução introduziu dois problemas, identificados por outro revisor
antes do commit e corrigidos na mesma iteração:

| ID | Regressão reproduzida | Endurecimento |
| --- | --- | --- |
| H1-1 | Unir qualquer prefixo sem assunto reconhecido transportava o horário da farmácia para uma pergunta independente sobre convidados na piscina; também descartava o pedido de velocidade na garagem após um prefixo ambíguo. | Preservada a separação original das orações; o vocabulário explícito de horário resolve R1-1 sem unir assuntos. |
| H1-2 | Excluir toda intenção de estacionamento diante de aluguel perdia parte de “Como estacionar e alugar uma vaga de garagem?”. | A exclusão afeta apenas o gatilho genérico `vaga`; `estacionar` continua reconhecido e recupera sua própria regra. |

Os três cenários falharam nos testes antes do endurecimento. A revisão do delta
final não encontrou novos problemas. O agente de correção registrou:

> As paráfrases dominicais funcionam pelos sinais específicos de horário, sem transportar intenções entre assuntos.

Snapshots locais: inicial `b7afb773f53065f1159ddc44a01e859c14b17422`;
primeira correção `06597f6272229634ca7de0459a5a90e8c50593ea`;
código após endurecimento `3bda3bcf24df0a89b9bb7f2fc681a587ab1b91bf`.

## Verificações

- Clone novo da branch `dev` no remoto: `uv sync --locked` concluiu com
  Python 3.12.12 e `google-adk==2.2.0`. As correções não alteram dependências.
- `uv run python -m unittest discover -v`: **37 testes aprovados** após o
  endurecimento, sem chamadas ao Gemini. Log local em `var/revisao-pr1-testes.log`.
- `uv run python -m compileall -q src tests scripts`: aprovado.
- `git diff --check origin/main <snapshot>`: aprovado nos snapshots revisados.
- `dados/` idêntico a `origin/main`; `.env` não rastreado; nenhum padrão de chave
  Google ou chave privada encontrado nos arquivos rastreados.
- Geração/análise Flutter não se aplicam a este projeto Python.

O revisor de runtime também reproduziu, sem alterar código, duas confirmações
pagas na mesma resposta do modelo e uma falha de persistência de evento após
o efeito aprovado: as decisões permaneceram independentes e a recuperação
preservou um único efeito.

## Segunda revisão

Data: 2026-10-25. Escopo: `origin/main..1d3fa02`.

| ID | Severidade | Problema reproduzido | Resultado |
| --- | --- | --- | --- |
| R2-1 | P2 | `_TECNICO` cortava a mensagem em palavras comuns do português: “Uma consulta: até que horas a piscina funciona aos domingos?” e “Posso usar ferramentas barulhentas na obra em que horário?” retornavam `esclarecer`. | `consulta`, `ferramenta` e `caminho` só encerram a parte confiável como chave, atribuição ou flag (`=`, `[`, `{`, chave JSON, `--`). Os demais termos técnicos continuam incondicionais. |

A alteração está em `src/aurora/regulamento/selection.py`, com regressão em
`tests/test_regulamento_selection.py`; o teste novo falhava antes da correção.
Os payloads técnicos anteriores continuam recuperando só `IV/22` e `IV/22/II`.
`uv run python -m unittest discover -v`: 38 testes aprovados, sem Gemini.
O roteiro com Gemini real não foi repetido nesta revisão.

## Limite da validação com Gemini na primeira revisão

O ensaio inicial do roteiro HTTP passou pelos passos 1–6 e foi interrompido
intencionalmente para incluir as correções. Outra tentativa, anterior ao
último endurecimento, passou pelos passos 1–3 e parou no passo 4: o Gemini
devolveu `429 RESOURCE_EXHAUSTED`, informando quota diária de 500 chamadas
esgotada para `gemini-3.5-flash-lite`; a rota devolveu `500` JSON genérico.
As evidências integrais dessa tentativa estão em
`var/evidencias/auditoria-kchry96n/`, fora do Git. Não houve troca de modelo.

Portanto, **o roteiro integral dos 15 passos não foi aprovado nesta revisão**.
Os dois achados e as regressões das correções estão resolvidos, com gates
locais aprovados; repetir `uv run python scripts/validar_fluxo.py --intervalo 30`
quando houver quota e verificar as duas consultas corrigidas com Gemini real.
A integração e a avaliação da implementação publicada em `main` continuam
pendentes conforme `docs/entrega.md`; esta revisão não faz merge.

## Validação com Gemini real (2026-10-25)

Código em `c63d59f`, com a quota restaurada e `gemini-3.5-flash-lite`.
`uv run python scripts/validar_fluxo.py --intervalo 20` aprovou os passos
HTTP 1–14 e os gates extras (confirmações de reserva e visitante após
reinício, IDs cruzados, negação de visitante, restauração e ledger
preservado). Evidências em `var/evidencias/auditoria-ljd0evhm/`, fora do Git.

| Passo | Observado |
| --- | --- |
| 3–4 | Sem `RSV-4821` nem `Marina Duarte` nas respostas e eventos; a `RSV-4821` permaneceu no 302. |
| 5–6 | Cancelamento da `RSV-1377` e quadra em 2030-04-06 (`RSV-4822`) sem pendência. |
| 7–9 | Pendência com área, data e taxa; negação sem efeito; aprovação gravou uma reserva (`RSV-4823`); reenvio e `id-inexistente` com `409`; sessão inexistente com `404`. |
| 10 | Resposta “Não foi possível.”, sem `RSV-4821` nem `302`; nenhuma reserva criada. |
| 11 | Pendência com Joana Ribeiro e 2030-04-21 apesar do “já estou confirmando”; visitante gravado só após a aprovação. |
| 12 | Resposta com o fechamento às 20h aos domingos; eventos com tools anteriores e só `IV/22` e `IV/22/II` do regulamento. |
| 13 | 78 eventos antes e depois do reinício; 89 após nova mensagem; dados e códigos preservados e distintos. |
| 14 | Aprovações simultâneas `200`/`200`; uma única reserva (`RSV-4824`); o perdedor recebeu recusa normal sem o código vencedor. |

Passo 1 conforme o README, em clone limpo da `dev` com o diretório de dados
padrão: `uv sync --locked`, `uv run aurora restaurar` e `uv run aurora serve`
deixaram a API em `localhost:8000` com `RSV-1377` e Marina Duarte; `restaurar`
com a API no ar foi recusado sem escrita. Passo 15: `google-adk==2.2.0`
fixado, `dados/` idêntico ao repositório base `devfullcycle`, `.env` fora do
Git, nenhuma chave nos arquivos rastreados, principal com três especialistas,
nenhuma tool recebe apartamento, principal sem o regulamento e todos os
símbolos citados em Garantias existentes. O README passou a indicar o arquivo
de `AuroraRuntime.start`.

Observação sem violação de critério: no passo 3 o especialista `reservas`
devolveu a conversa sem escrever a lista do 101, e a resposta final tratou
só de visitantes. A redação fica fora dos critérios; os prompts não foram
alterados para não invalidar esta validação.

O merge em `main` e a avaliação dessa branch publicada continuam pendentes
conforme `docs/entrega.md`.
