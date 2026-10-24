# Arquitetura — sessões, reservas, visitantes, confirmação e regulamento

O morador fala com `aurora_principal`. O código, não o texto do modelo, decide
identidade, cobrança, cancelamento, autorização de entrada, exclusividade e
quais trechos do regulamento podem ser lidos. Esta nota cobre a base da spec
001, as reservas da spec 002, a autorização de visitantes da spec 003, a
consulta seletiva da spec 004 e a restauração da spec 005.

## Agentes

Os quatro agentes são `LlmAgent` em modo `chat`, com o modelo de `GEMINI_MODEL`
(default `gemini-3.5-flash-lite`). Estão na mesma árvore: `aurora_principal`
tem `sub_agents` `reservas`, `visitantes` e `regulamento`. Não há `AgentTool`
nem sessão filha.

| Agente | Responsabilidade | Como é acionado | Motivo da divisão |
| --- | --- | --- | --- |
| `aurora_principal` | Entende o pedido e responde. Não lê o banco e não recebe o texto do regulamento. | É a raiz do `App`. | Um interlocutor só encaminha. |
| `reservas` | Lista, reserva e cancela o que é do apartamento da sessão, e informa livre ou ocupada. | O principal transfere para ele. | Agenda de área, com efeito e disputa de data. |
| `visitantes` | Lista nome e data e pede autorização de entrada. A gravação só ocorre depois da confirmação do sistema. | O principal transfere para ele. | Acesso de pessoas, com efeito diferente da reserva. |
| `regulamento` | Responde dúvida de regra com os trechos já autorizados para aquela mensagem. | O principal transfere para ele. | A norma não pode entrar no prompt do principal nem ser escolhida pelo modelo. |

A divisão separa agenda, acesso e norma. Cada especialista só recebe as
próprias tools. Os três usam `disallow_transfer_to_parent=False` e
`disallow_transfer_to_peers=True`: devolvem a conversa ao principal e não se
transferem entre si. O de regulamento não chama executor de reserva nem de
visitante.

Tools de reserva, em `src/aurora/tools/reservas.py`:

- `listar_minhas_reservas` — ativas do apartamento canônico
- `consultar_disponibilidade` — só `livre` ou `ocupada`
- `reservar_area` — taxa zero grava na hora; taxa positiva pede confirmação
- `cancelar_minha_reserva` — código próprio ou área e data, sem confirmação

Nenhuma delas declara apartamento, sessão, taxa ou decisão. A identidade sai
de `tool_context.session.id` em `src/aurora/tools/context.py`.

Tools de visitante, em `src/aurora/tools/visitantes.py`:

- `listar_meus_visitantes` — nome e data do apartamento canônico, ou lista vazia
- `autorizar_visitante` — recebe só nome e data; pede confirmação e não grava

A separação existe porque agenda de área, acesso de pessoas e norma têm
efeitos diferentes. O especialista de visitantes não cancela reserva, o de
reservas não autoriza entrada e o de regulamento não grava negócio. Reservas
e visitantes usam o mesmo coordenador de confirmação. A consulta não cria
pendência e não impõe horário, prazo, data passada ou capacidade à reserva.

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

`autorizar_visitante` está no mesmo mapa, registrado por
`registrar_executor_visitante` em `src/aurora/runtime/confirmacoes.py`. O
executor em `src/aurora/storage/visitantes.py` recebe a conexão já aberta, o
apartamento da sessão, o snapshot, a proposta e a sessão. Ele não abre
transação, não faz commit e não decide o consentimento. A negação não chama o
executor. A aprovação insere o visitante com `proposta_id` na mesma transação
que grava o consumo. O apartamento vem de `session_identity`, não do texto.
Nome e data executados são os da proposta, não os argumentos da reentrada.

A rota, o `409` e o despacho continuam os mesmos. Uma falha do modelo depois
que o efeito e o retorno da tool já estão persistidos conclui o despacho e
responde `200`, em `src/aurora/runtime/service.py`. Não repete a visita nem a
reserva. Se os eventos ainda não fecharam, o despacho segue `recuperar` e a
próxima mensagem da sessão retoma antes do texto novo.

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
O processador nativo de confirmação não foi substituído. A evidência das
reservas está em `docs/validacao/002-reservas.md`. A autorização de visitante
repetiu o caminho: a retomada saiu de `visitantes`, antes e depois de reiniciar,
com a visita gravada. A evidência está em `docs/validacao/003-visitantes.md`.

## Consulta seletiva

`dados/regulamento.md` continua somente leitura. `src/aurora/runtime/app.py`
chama `reconstruir_indice` ao montar o `App`. O parser em
`src/aurora/regulamento/parser.py` separa capítulo, artigo, inciso e parágrafo
fora do Runner. O índice fica em memória, não entra em instrução, state,
evento ou log de corpo. Erro de estrutura cita posição, não o texto.

`src/aurora/regulamento/catalog.py` associa assunto e intenção a referências
como `IV/22/II`. Não copia horário nem resposta. `src/aurora/regulamento/selection.py`
lê a mensagem original da API, antes do Runner, e fecha o conjunto.
`src/aurora/runtime/service.py` instala um `ConsultaScope` num `ContextVar`:
sessão canônica, nonce aleatório da execução HTTP e os IDs autorizados. Esse
nonce não é passado como `invocation_id`. O token é desfeito no `finally`.
Confirmação e `GET /eventos` não instalam escopo. Startup não gera evento.

`consultar_regulamento`, em `src/aurora/tools/regulamento.py`, não declara
parâmetro para o modelo. Argumento extra devolve erro sem trecho. A tool
confere a identidade da sessão e o escopo corrente; só então
`materializar` devolve o texto literal daquelas unidades. Sem escopo, a
resposta é esclarecimento com lista vazia. Chamada repetida na mesma
mensagem não amplia o conjunto. Comando `topics=`, `path=` ou pedido de
carga integral não autoriza outro capítulo.

Status `esclarecer` ou `sem_base` faz o serviço trocar a resposta HTTP por
uma frase fixa, sem norma inventada. O histórico em
`src/aurora/runtime/sessions.py` e `src/aurora/runtime/events.py` guarda a
chamada, o resultado e a transferência por completo. A rota de eventos não
filtra trecho. Consulta anterior legítima permanece.

## Persistência

Dois SQLite no diretório de dados, por default `var/`:

- `aurora.sqlite3` — cadastro, identidade, reservas, visitantes, ledger, propostas e decisões
- `adk.sqlite3` — sessões e eventos

A carga inicial de `dados/` ocorre uma vez, enquanto não existe a marca
`inicializado`. Visitantes do seed ficam com `proposta_id` nulo. Autorizações
novas exigem proposta. Reiniciar não restaura negócio nem apaga sessões,
visitas, decisões ou eventos. Um banco anterior ganha `proposta_id` e as
restrições de nome e chave sem apagar as linhas já gravadas. Subir a API não
faz a restauração explícita.

## Restauração

`uv run aurora serve` adquire lock compartilhado em `operation.lock`, no
diretório de dados, antes de o processo abrir banco. O descritor fica aberto
até o Uvicorn encerrar. O arquivo de lock não é apagado.
`uv run aurora restaurar` pede o mesmo caminho em lock exclusivo e não
bloqueante. Se o serviço estiver ativo, o comando sai com erro antes de criar
o marcador e antes de escrever.

O marcador `reset-in-progress.json` é gravado e sincronizado no disco antes
de qualquer alteração dos bancos. Enquanto ele existe, `serve` recusa
iniciar, tanto na CLI quanto em `AuroraRuntime.start`, e essa recusa não abre
o SQLite de negócio. A transação de negócio, em `src/aurora/storage/reset.py`,
apaga nesta ordem, que é a das chaves estrangeiras do schema: visitantes,
reservas, despachos, decisões, propostas e identidades. Cadastros de
apartamento e área permanecem. Reservas e visitantes iniciais voltam de
`dados/`, com `proposta_id` nulo. `ledger_codigo` e `sequencia_codigo` não são
apagados; o contador só sobe.

Não há commit distribuído com o banco do ADK. Depois do commit de negócio, as
conexões de negócio são fechadas e `recriar_banco_vazio` remove o arquivo do
ADK, o WAL e o SHM, e cria um banco vazio com o `DatabaseSessionService` da
versão fixada. Sessões antigas deixam de existir. O marcador só sai depois
que as duas bases foram conferidas. Falha no meio mantém o marcador; repetir
`restaurar` com a API parada é idempotente. `serve` nunca chama essa rotina.
