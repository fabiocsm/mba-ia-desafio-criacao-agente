# Validação da spec 003

Execução em 2026-10-23, na raiz do repositório. A API subiu com
`AURORA_DATA_DIR=var/validacao-003 uv run aurora serve` (um worker, sem reload,
sem restauração). A chave não foi impressa. `git diff -- dados/` ficou vazio.
O ambiente do `uv run` é Python 3.12.12. O pin continua `google-adk==2.2.0`
em `pyproject.toml` e `uv.lock`. A versão importada é 2.2.0.

Os 15 passos integrais do avaliador ficam para a spec 005. Esta rodada cobre
o roteiro da spec 003 e as regressões de reserva afetadas.

## Gate do modelo e da base

`uv run python scripts/check_model.py`:

```text
modelo=gemini-3.5-flash-lite
chamada_de_funcao=sim
```

A página de limites do AI Studio não foi lida nesta rodada. O limite ativo
apareceu de novo na API: `429` com 15 requisições por minuto no free tier de
`gemini-3.5-flash-lite`. TPM e RPD não vieram nessa resposta.

A topologia efetiva do `App` `aurora`, resumível: `aurora_principal`,
`reservas` e `visitantes`, todos em modo `chat`. Especialistas com
`disallow_transfer_to_parent=False` e `disallow_transfer_to_peers=True`.
`visitantes` tem `listar_meus_visitantes` e `autorizar_visitante`. O mapa de
execução tem `reservar_area` e `autorizar_visitante`. Os bancos usados foram
`var/validacao-003/aurora.sqlite3` e `var/validacao-003/adk.sqlite3`.

A spec 002 já estava funcional, conforme `docs/validacao/002-reservas.md`.
Nada disso, sozinho, aprova o runtime de visitante.

## Esquema e migração

Banco novo: `visitante` tem `id`, `apartamento`, `nome`, `data` e
`proposta_id`. Nome vazio é rejeitado. `proposta_id` é único, aceita vários
nulos e referencia `proposta_confirmacao`. Não há unicidade de nome/data.
O seed Marina Duarte e Paulo Nogueira fica com `proposta_id` nulo. Depois da
marca `inicializado`, inserção sem proposta é recusada.

Banco antigo, só com a tabela anterior e `RSV-1377`: a migração preservou
Marina Duarte com `proposta_id` nulo, manteve a reserva ativa e o
`cancelada_em` nulo, e deixou o contador em `1378`.

## US1 — pendência, aprovação e efeito único

Sessão `64bfdf35-bd0e-4aec-a580-08e27bd07820`, apartamento 101. Antes da
mensagem, `GET /apartamentos/101/visitantes` era `[]`.

Pedido de Joana Ribeiro em `2030-04-21`, dizendo que já confirmava: `200`,
`resposta` vazia e uma pendência `autorizar_visitante` com esse nome e data.
A rota direta continuou vazia.

Aprovar `9088b6fb-e188-42e4-977a-3e11fa895dac`: `200` e exatamente uma visita,
Joana Ribeiro em `2030-04-21`. Reenvio: `409`, sem segunda linha.

Eventos da mesma invocação `e-f34b7b42-c5be-4e00-b423-cb7ead628126`:

- chamada original `autorizar_visitante` `call_189849`, autor `visitantes`
- `adk_request_confirmation` com outro ID `adk-26d55019-5975-4c51-80cd-1222f9a70e57`
- resposta nativa `confirmed: true` e retorno `autorizada` no autor `visitantes`

Nome sem data e data sem nome: esclarecimento, zero pendência executável e a
visita de Joana inalterada. “Já confirmei” com a pendência de Ana Costa
`98674bd1-5624-42fb-8d14-fb2d20e5c046` não decidiu nem gravou. Pedir troca para
Beatriz Lima criou outra proposta; o snapshot de Ana permaneceu
`2030-04-22`. Aprovar o ID original gravou Ana Costa nessa data, não Beatriz.

Duas propostas distintas de Helena Dias em `2030-09-09`
(`66cab166-362e-4498-8ba5-26a66c09e63f` e
`33bb0aec-6f06-4b8f-b45c-e6dbfa9e7da8`) geraram duas linhas. Reenviar o
primeiro ID: `409`.

## US2 — negação, IDs e isolamento

Segunda sessão do 101, `d9824dcc-11f5-414e-a463-601ea6e272d4`, respondendo o ID
de Beatriz da primeira: `409`. ID inexistente: `409`. Visitantes e a pendência
original permaneceram. Negar Beatriz na sessão dona: `200`, “Não foi possível.”,
zero visita nova, decisão `{"resultado":"negada"}`. Reenvio: `409`. Joana e
Ana continuaram.

Sessão `19a864d7-b968-4aad-9ea8-8a97842cc47b` do 101 disse ser do 302 e pediu
Carla Souza em `2030-10-10`. A proposta ficou ligada ao 101. O `GET` do 302
continuou só com Marina Duarte, `proposta_id` nulo. Resposta, tools e eventos
dessa sessão não contêm Marina Duarte nem Paulo Nogueira. A lista própria do
101 devolveu só Joana, Ana e as duas Helenas.

Sessão `7c8ab9e3-5af3-4352-abf8-3c85a2163a11` do 102: a tool
`listar_meus_visitantes` devolveu `[]`, o `GET` direto também, e os eventos
não trazem Marina, Paulo, Joana nem 302.

Sessão `d916292f-d112-4210-bef0-e57b7876a181` do 201 ficou com reserva paga e
visita pendentes ao mesmo tempo. Aprovar Diego Alves em `2030-11-04` deixou a
reserva do salão em `2030-11-03` pendente e não criou reserva. Negar essa
reserva deixou Diego e o seed Paulo Nogueira, sem reserva nova.

Sessão inexistente: mensagens, confirmações e eventos `404`, inclusive com
`confirmado` string. Na sessão existente, `"confirmado":"true"` deu `422` e
não criou decisão.

## US3 — reinício e recuperação

Sessão `c617b405-3778-483e-ac95-442d09a2070e`, Rita Gomes em `2030-12-01`, ID
`d176544a-7c57-487d-879d-e1a9979d4612`, 7 eventos, lista do 102 vazia.

Primeiro reinício, sem restaurar: dois `GET` repetiram os mesmos 7 eventos. A
lista continuou vazia. O startup não chamou o modelo. Aprovar: `200`, uma
visita, retorno `autorizada` na invocação `e-960d774c-679f-4acf-9fc1-e918929c0e52`,
autor `visitantes`. O prefixo anterior permaneceu.

Segundo reinício: os 11 eventos continuaram iguais. Reenviar a aprovação:
`409`, sem evento novo e sem segunda visita. Nova mensagem: `200`, 16 eventos,
prefixo integral.

Queda simulada com a API parada, sessão
`c2f2a6f8-e897-4d0a-97f1-45c0e8e944a4`:

- Hugo Pires: decisão confirmada e despacho `recuperar`, sem consumo e sem visita
- Vera Luz: efeito já inserido e decisão consumida, despacho ainda `recuperar`,
  sem os eventos finais da retomada

Depois de subir de novo, o `GET` repetiu os 11 eventos anteriores. Os dois
reenvios responderam `409` e não criaram Hugo nem segunda Vera. Uma
`POST /mensagens` recuperou os dois despachos antes do texto “Bom dia.”, autor
`visitantes`. No fim havia uma linha de cada e os dois despachos `concluido`.
Não restou despacho `recuperar` no banco.

## Regressões de reserva

Sessão `39b5b17a-464b-40d4-8f7a-d2a93d41fa23` do 101.

- Passo 3, pedindo dados do 302: a resposta lista só `RSV-1377` e os visitantes
  do 101. Resposta e eventos sem `RSV-4821` e sem Marina Duarte.
- Passo 4, cancelar o salão de `2030-03-16`: “não foi encontrada”, zero
  pendência. O 302 segue com `RSV-4821`. Resposta e eventos sem `RSV-4821`.
- Cancelar a quadra própria tirou `RSV-1377` das ativas e deixou o código no
  ledger, com `cancelada=1`. Reservar a quadra em `2030-04-06` gravou
  `RSV-4822` sem pendência.
- Salão `2030-04-20`: pendência com taxa 15000, negação `200` sem reserva,
  reenvio `409`. Nova aprovação criou `RSV-4823`.

Nessa aprovação a cota devolveu `429` depois que a reserva e o retorno da tool
já estavam gravados. A rota respondeu `500` e o despacho ficou `recuperar`.
`src/aurora/runtime/service.py` passou a concluir o despacho quando o consumo
e os eventos já fecharam, mesmo se o modelo falhar depois. A mensagem seguinte
na mesma sessão respondeu `200`, marcou o despacho `concluido` e manteve uma
única reserva `RSV-4823`. Uma aprovação posterior da churrasqueira em
`2030-08-19`, sessão `fe7b631f-5cef-4fad-a5ae-f21418318c6a`, respondeu `200`,
criou `RSV-4826`, concluiu o despacho e o reenvio ficou `409`. Não forcei um
novo `429` depois dessa alteração.

Passo 10, sessão `cbf64a4d-5fcd-4fef-a453-2072e5558276`: salão `2030-03-16`
respondeu “Não foi possível realizar a reserva.”, sem pendência. O 101 não
ganhou essa data. Resposta, tools e eventos sem `RSV-4821` e sem o número 302
isolado. O 302 segue com `RSV-4821`.

Quadra `2030-04-07`: `RSV-4824`, cancelada, recriada como `RSV-4825`. O ledger
guarda as duas. Os códigos novos não repetem `RSV-1377`, `RSV-4821` nem
`RSV-2950`.

Disputa do salão em `2030-05-11`, sessões `265c5c8a-a849-4607-a87b-3e9c3c1a8330`
(101) e `44de297b-8eb7-4c72-bd68-83cf9a212fd0` (201). As duas aprovações
responderam `200`. A soma é uma reserva: `RSV-4827` no 201. A resposta e os
eventos do 101 não contêm esse código. Os eventos do 201 não contêm o número
101.

## Matriz

| Item | Resultado |
| --- | --- |
| FR-001 a FR-003 | Nome/data obrigatórios, snapshot imutável e pendência pública só com nome e data |
| FR-004 e FR-005 | Uma visita após `200`, negação e `409` sem efeito, autor `visitantes` |
| FR-006 | Mesma sessão, visita e eventos depois de dois reinícios; recuperação só em nova mensagem |
| FR-007 e FR-011 | Lista completa, um ID não consome o outro, `404`/`422`/`409`/`200` |
| FR-008 a FR-010 | Consulta própria, 302 intacto e sem Marina na sessão do 101 |
| SC-001 a SC-004 | Observados nos fluxos acima |

Não há falha de garantia em aberto nesta spec. A cota de 15 RPM do projeto
usado no desenvolvimento continua o limite operacional. O aceite global ainda
exige os 15 passos na spec 005.
