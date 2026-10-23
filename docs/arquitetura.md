# Arquitetura da base de sessões

Esta nota descreve o atendimento entregue na spec 001. Confirmação de tools,
mutação de reservas, autorização de visitantes e consulta ao regulamento não
fazem parte desta base e não foram validadas aqui.

## Agentes

Os três agentes são `LlmAgent` em modo `chat`, com o mesmo modelo configurável
(`GEMINI_MODEL`, default `gemini-3.5-flash-lite`). Estão na mesma árvore do
ADK: `aurora_principal` tem `sub_agents` `reservas` e `visitantes`. Não há
`AgentTool` nem sessão filha.

| Agente | Responsabilidade nesta entrega | Como é acionado |
| --- | --- | --- |
| `aurora_principal` | Entende o pedido e responde ao morador. Não lê o regulamento e não acessa o banco. | É a raiz do `App`. O `Runner` começa por ele. |
| `reservas` | Lista reservas ativas da sessão e informa se uma área está livre ou ocupada. | O principal transfere para ele. As tools são `listar_minhas_reservas` e `consultar_disponibilidade`. |
| `visitantes` | Lista nome e data dos visitantes da sessão. | O principal transfere para ele. A tool é `listar_meus_visitantes`. |

A divisão separa agenda de áreas e acesso de pessoas. Cada especialista só
recebe as tools da sua consulta, então um encaminhamento não abre a função do
outro. Os especialistas usam `disallow_transfer_to_parent=False` e
`disallow_transfer_to_peers=True`: podem devolver a conversa ao principal e
não se transferem entre si. O retorno ao principal permanece permitido para a
retomada que a spec 002 vai precisar conferir.

## Execução

`src/aurora/runtime/app.py` monta `App(name="aurora", resumability_config=ResumabilityConfig(is_resumable=True))` sem compactação de eventos.
`src/aurora/runtime/service.py` cria o `Runner` com esse app e com o
`OrderedDatabaseSessionService`. Cada mensagem usa `user_id=session_id` e
`session_id=session_id`. O cliente não envia agente, state nem apartamento.
`RunConfig` fica sem streaming. Interações da mesma sessão são serializadas
por um lock local; sessões diferentes não compartilham esse lock.

## Identidade

O apartamento é gravado uma vez em `session_identity`, no `POST /sessoes`.
Um trigger rejeita qualquer `UPDATE` dessa tabela. As tools chamam
`resolve_identity` em `src/aurora/tools/context.py`, que lê somente
`tool_context.session.id` e busca o vínculo. O state do ADK e os argumentos
do modelo não escolhem o apartamento: as funções de consulta não declaram
esse parâmetro. A consulta SQL filtra o apartamento canônico antes de montar
o resultado. A agenda usa `EXISTS` e devolve só `livre` ou `ocupada`.

As rotas `GET /apartamentos/...` leem o banco direto, sem `Runner` e sem
entrar no catálogo de tools.

## Persistência

Há dois arquivos SQLite no diretório de dados, por default `var/`:

- `aurora.sqlite3`: cadastro, identidade, reservas e visitantes
- `adk.sqlite3`: sessões e eventos do ADK

A carga inicial de `dados/` ocorre numa transação só enquanto o banco não tem
a marca `inicializado`. Reiniciar a API não restaura nem apaga esse estado.
`GET /sessoes/{session_id}/eventos` devolve os eventos do serviço persistido,
na ordem, inclusive a mensagem do usuário, sem projeção que esconda chamadas
ou resultados. O adaptador de sessão atribui timestamp estritamente crescente,
com passo mínimo de 1 ms, e recupera o maior timestamp gravado ao subir.

## Limite herdado pela spec 002

O `App` resumível e os especialistas na mesma sessão deixam a confirmação
nativa do ADK possível na próxima spec. Esta entrega não registra tool de
mutação, não publica `POST /sessoes/{session_id}/confirmacoes` e não afirma
que uma aprovação sobrevive ao `DatabaseSessionService`. A spec 002 precisa
provar isso no armazenamento real, antes e depois de reiniciar.
