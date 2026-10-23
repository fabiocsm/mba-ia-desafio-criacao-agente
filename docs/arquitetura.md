# Arquitetura — sessões, reservas e confirmação

O morador fala com `aurora_principal`. O código, não o texto do modelo, decide
identidade, cobrança, cancelamento e exclusividade. Esta nota cobre a base da
spec 001 e as reservas da spec 002. Visitantes continuam só em consulta. O
regulamento não entra nesta entrega.

## Agentes

Os três agentes são `LlmAgent` em modo `chat`, com o modelo de `GEMINI_MODEL`
(default `gemini-3.5-flash-lite`). Estão na mesma árvore: `aurora_principal`
tem `sub_agents` `reservas` e `visitantes`. Não há `AgentTool` nem sessão filha.

| Agente | Responsabilidade | Como é acionado |
| --- | --- | --- |
| `aurora_principal` | Entende o pedido e responde. Não lê o banco nem o regulamento. | É a raiz do `App`. |
| `reservas` | Lista, reserva e cancela o que é do apartamento da sessão, e informa livre ou ocupada. | O principal transfere para ele. |
| `visitantes` | Lista nome e data dos visitantes da sessão. Ainda não autoriza. | O principal transfere para ele. |

A divisão separa agenda de áreas e acesso de pessoas. Cada especialista só
recebe as próprias tools. Os especialistas usam `disallow_transfer_to_parent=False`
e `disallow_transfer_to_peers=True`: devolvem a conversa ao principal e não se
transferem entre si.

Tools de reserva, em `src/aurora/tools/reservas.py`:

- `listar_minhas_reservas` — ativas do apartamento canônico
- `consultar_disponibilidade` — só `livre` ou `ocupada`
- `reservar_area` — taxa zero grava na hora; taxa positiva pede confirmação
- `cancelar_minha_reserva` — código próprio ou área e data, sem confirmação

Nenhuma delas declara apartamento, sessão, taxa ou decisão. A identidade sai
de `tool_context.session.id` em `src/aurora/tools/context.py`.

## Execução

`src/aurora/runtime/app.py` monta `App` resumível, sem compactar eventos.
`src/aurora/runtime/service.py` cria `AuroraRunner` com
`OrderedDatabaseSessionService`. Cada execução usa `user_id=session_id` e
`session_id=session_id`. O cliente não envia agente, state nem apartamento.
`RunConfig` fica sem streaming. A mesma sessão é serializada por um lock
local; sessões diferentes não compartilham esse lock. Escritas de negócio usam
outro lock, curto, só em volta do `BEGIN IMMEDIATE`.

## Identidade e sigilo

O apartamento é gravado uma vez em `session_identity`. Um trigger rejeita
`UPDATE`. Cancelamento e listagem filtram esse apartamento antes de montar o
resultado. Reserva alheia e reserva inexistente devolvem a mesma recusa, sem
código. A agenda usa `EXISTS`. As rotas `GET /apartamentos/...` leem o banco
direto e não são tools.

## Reservas, códigos e exclusividade

O cadastro de área guarda `taxa_centavos`. Zero dispensa confirmação. Valor
maior que zero congela área, data e taxa na proposta e não insere a reserva.

`src/aurora/storage/codigos.py` mantém `ledger_codigo` e `sequencia_codigo`.
O contador começa acima do maior sufixo inicial e o código `RSV-{numero}` entra
no ledger na mesma transação da reserva. Cancelar só muda `cancelada` e
`cancelada_em`; a linha e o código permanecem. Um trigger impede reabrir a
reserva ou trocar código, apartamento, área ou data.

O índice único parcial `reserva_ativa_area_data` em
`(area, data) WHERE cancelada = 0` é a autoridade no instante da gravação.
Conflito vira `indisponivel`, sem ler a reserva vencedora. A transação usa
savepoint para não transformar outro erro em ocupação e para não publicar um
código cuja reserva não entrou.

## Confirmação

O contrato interno está em
`specs/002-reservas-confirmacoes/contracts/confirmation-runtime.md`.

1. A tool paga chama `prepare` e `request_confirmation`. A proposta fica
   `preparando` até o evento `adk_request_confirmation` ser gravado.
2. `OrderedDatabaseSessionService.append_event` publica a pendência com o ID
   novo do ADK, a invocação e o autor. Startup só repete essa correlação. Não
   chama o Runner e não cria eventos.
3. `POST /sessoes/{session_id}/confirmacoes` confere a sessão antes do corpo,
   grava a decisão e o despacho `recuperar` e só então chama
   `ConfirmationCoordinator.resume`.
4. A retomada manda `FunctionResponse` de `adk_request_confirmation` ao Runner,
   com a invocação original. Um `ContextVar` leva sessão, invocação, autor e
   proposta, e é desfeito no `finally`. A tool só consome a decisão se essa
   correlação bate com o banco. Texto, state e `ToolConfirmation` sozinhos não
   gravam reserva.
5. Consumo, código e reserva — ou a recusa — acontecem num único commit. A
   reentrada devolve o resultado já gravado. O despacho vai para `concluido`
   quando o resultado está consumido e o retorno da tool está nos eventos.

`GET /sessoes/{session_id}/eventos` só lê. Reenviar uma decisão já gravada
responde `409` e não recupera. Se o processo cair no meio, a próxima
`POST /sessoes/{session_id}/mensagens` retoma o despacho antes do texto novo.

A spec 003 registra `autorizar_visitante` no mesmo mapa de
`src/aurora/storage/confirmacoes.py`, com `registrar_executor`. O executor
recebe a conexão da transação de consumo e não faz commit próprio. A rota, o
`409` e o despacho continuam os mesmos.

## Limite do ADK 2.2.0

A documentação do ADK não garante confirmação com `DatabaseSessionService`.
Com a sessão ainda no especialista, a seleção nativa retomou `reservas`,
gravou a reserva e sobreviveu a reinício. Depois que o principal respondia no
fim da conversa, `_find_agent_to_run` escolhia a raiz antes da mensagem nova e
a tool não reexecutava: a decisão ficava sem consumo e a rota respondia falha,
sem reserva.

`src/aurora/runtime/runner.py` só troca essa escolha quando o `ContextVar` da
retomada pertence à sessão atual e o autor existe na árvore. Nos outros
casos chama a implementação do ADK. Duas sessões não compartilham o contexto.
O processador nativo de confirmação não foi substituído. A evidência está em
`docs/validacao/002-reservas.md`.

## Persistência

Dois SQLite no diretório de dados, por default `var/`:

- `aurora.sqlite3` — cadastro, identidade, reservas, ledger, propostas e decisões
- `adk.sqlite3` — sessões e eventos

A carga inicial de `dados/` ocorre uma vez, enquanto não existe a marca
`inicializado`. Reiniciar não restaura negócio nem apaga sessões. Um banco da
spec 001 ganha coluna, ledger e índice sem apagar as reservas já gravadas. A
restauração explícita fica para a spec 005 e deve preservar ledger e contador.
