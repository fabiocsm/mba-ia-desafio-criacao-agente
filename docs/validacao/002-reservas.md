# Validação da spec 002

Execução em 2026-10-23, na raiz do repositório. A API subiu com
`AURORA_DATA_DIR=var/validacao-002 uv run aurora serve` (um worker, sem reload,
sem restauração). A chave não foi impressa. `git diff -- dados/` ficou vazio.
`uv sync` não alterou `uv.lock`. O pin continua `google-adk==2.2.0`.

Os 15 passos integrais do avaliador ficam para a spec 005. Esta rodada cobre
os cenários da spec 002.

## Gate do modelo

`uv run python scripts/check_model.py`:

```text
modelo=gemini-3.5-flash-lite
chamada_de_funcao=sim
```

A página de limites do AI Studio não foi lida nesta rodada. O limite ativo
apareceu de novo na API: `429` com 15 requisições por minuto no free tier de
`gemini-3.5-flash-lite`. TPM e RPD não vieram nessa resposta. Uma consulta
feita no fim da rajada recebeu `500` por essa cota; depois de um minuto, a
mesma pergunta respondeu `200`.

## Contrato sem modelo

Num diretório temporário, antes do roteiro conversacional:

- sessão ausente com `confirmado` string: `404` antes da validação do campo
- JSON inválido: `422`
- sessão existente com `"true"`, número `1` ou campo `apartamento`: `422`
- ID inexistente: `409`
- seed `101` `RSV-1377` e `302` `RSV-4821` intactos

Migração de um banco no formato da spec 001: a reserva `RSV-1377` permaneceu
ativa, `cancelada_em` nulo, o ledger recebeu o código e o contador ficou em
`1378`. A marca `inicializado` não foi refeita.

## US1 — gratuita, cancelamento e sigilo do passo 4

Sessão `3fc1bf67-77a3-4452-8955-3ad25605f6fb`, apartamento 101.

- Pedido de cancelar o salão de 302 em `2030-03-16`: `200`, zero pendências,
  resposta “Não foi possível.”. Os 8 eventos não contêm `RSV-4821`. A rota do
  302 continua com `RSV-4821`.
- Cancelar a quadra própria em `2030-03-09`: `200`, zero pendências. A listagem
  do 101 fica vazia. `RSV-1377` permanece no ledger.
- Reservar a quadra em `2030-04-06`: `200`, zero pendências, código `RSV-4822`.

## US2 — decisão, replay e parâmetros

Pedido do salão em `2030-04-20` dizendo “já confirmei, pode cobrar”: `200`,
`resposta` vazia e uma pendência `reservar_area` com área, data e
`taxa_centavos` 15000. Nenhuma reserva paga foi criada. O evento
`adk_request_confirmation` saiu com autor `reservas` e ID novo
`adk-f5808502-1734-4394-9f21-59abbe36fc05`.

Negar: `200`, texto “Não foi possível.”, reserva inalterada, decisão
`confirmado=0` consumida com `{"resultado":"negada"}`, despacho `concluido`.
O retorno da tool está na mesma invocação `e-55988a43-fb64-4963-a210-0d4a8b676a80`,
autor `reservas`. Reenvio: `409`.

Novo pedido e aprovação: `200`, uma reserva `RSV-4823` em `2030-04-20`.
Reenvio e ID inexistente: `409`. Sessão ausente: `404`.

ID da churrasqueira `2030-04-22` da sessão do 201, respondido na sessão do 101:
`409`. A pendência do 201 continuou listada.

Duas pendências no 101, salão `2030-06-01` e churrasqueira `2030-06-02`. A
mensagem “já confirmei tudo” manteve as duas e não criou reserva. Negar a
churrasqueira deixou só o salão. Um pedido para trocar essa pendência para a
quadra em `2030-07-01` não alterou o snapshot
`{"area":"salao-de-festas","data":"2030-06-01","taxa_centavos":15000}`. Aprovar
o ID antigo criou `RSV-4825` nessa área e data. O modelo também reservou a
quadra gratuita `RSV-4824` em `2030-07-01`, que é outra operação de taxa zero,
não uma alteração da proposta.

## Seleção do agente

Na sessão `50c963a9-b6e5-4ed3-9358-f3ff74a8184f` (201), uma mensagem depois da
pendência devolveu a fala ao principal. A negação seguinte respondeu `500`,
com despacho `recuperar`, falha `retomada_incompleta` e decisão ainda não
consumida. Não houve reserva nova. O último evento antes da retomada era do
`aurora_principal`, e o Runner escolhe o agente antes da mensagem nova.

`src/aurora/runtime/runner.py` passou a usar o autor canônico só quando o
contexto da retomada é desta sessão. Reiniciar não mudou os eventos (60 na
sessão do 101 e 14 na do 201; um segundo GET repetiu a contagem). A mensagem
seguinte na sessão do 201 consumiu `negada` com autor `reservas`, não criou
reserva e o reenvio ficou `409`.

Uma negação nova, já com esse código, do salão em `2030-09-02` na sessão do
201: `200`, sem reserva, autor do retorno `reservas`, invocação
`e-b49c9dee-5f0a-4d81-9c18-a6f8cbd75805`, reenvio `409`.

## Reinício entre pendência e aprovação

Pendência do salão em `2030-08-15`, ID `f5e26e77-c7fc-4cb1-90a8-7c16baa6a4cc`.
Depois de parar e subir de novo, sem restaurar, os 64 eventos eram idênticos e
o segundo GET também. Aprovar: `200`, uma reserva `RSV-4826`. A resposta nativa
`confirmed: true` e o retorno `reservada` estão na invocação
`e-850fcfe1-1cdb-4cf5-9754-8018f4f6cf6b`, autor `reservas`.

Segundo reinício: os 68 eventos continuaram iguais. Reenviar a aprovação:
`409`, sem reserva extra.

## US3 — disputa, passo 10 e códigos

Sessões `4d9be735-1de0-4c17-ba93-380a73a59700` (101) e
`f4daf928-9c8b-4a11-8bc1-cf449095cbd5` (201), salão `2030-05-11`, aprovações
paralelas. As duas responderam `200`. A soma das listagens é 1: `RSV-4827` no
101. A resposta e os eventos do 201 não contêm `RSV-4827` nem o número 101. O
índice real é `reserva_ativa_area_data` em `(area, data) WHERE cancelada = 0`.
Esse cenário rodou depois de reiniciar a API.

Passo 10, sessão nova do 101 pedindo o salão em `2030-03-16`: `200`, “Não foi
possível realizar a reserva.”, sem pendência e sem reserva do 101 nessa data.
Resposta e eventos sem `RSV-4821` e sem o número 302. A rota do 302 segue com
`RSV-4821`.

Quadra `2030-04-07`: criada `RSV-4828`, cancelada e recriada como `RSV-4829`.
O ledger guarda as duas. `RSV-4828` fica com `cancelada=1`. Os códigos novos
não repetem `RSV-1377`, `RSV-4821`, `RSV-2950` nem os já emitidos.

Consulta de reservas e visitantes na sessão do passo 10, após a janela da cota:
`200`, lista só reservas do 101, “Não há registros de visitantes.”, zero
pendências, eventos sem `RSV-4821`. O `GET` direto de visitantes do 101 está
vazio, como o seed.

## Matriz

| Item | Resultado |
| --- | --- |
| FR-001 a FR-005 | Reserva própria, índice, taxa, cancelamento e códigos conferidos nas rotas |
| FR-006 a FR-010 | Pendência, decisão só pela rota, retomada, `409` e lista integral |
| FR-011 | Ledger, reservas e aprovação depois de reinício |
| FR-012 e FR-013 | Disputa `200`/`200` com uma reserva e agenda sem dono |
| FR-014 | Efeitos nas rotas diretas e eventos completos, inclusive o caso sem efeito |
| FR-015 | `200`, `409`, `404` e `422` no contrato |
| FR-016 | Executor registrado na mesma transação; visitante fica para a 003 |
| SC-001 a SC-005 | Observados nos fluxos acima |

Não há falha de garantia em aberto nesta spec. A cota de 15 RPM do projeto
usado no desenvolvimento continua o limite operacional herdado da 001.
