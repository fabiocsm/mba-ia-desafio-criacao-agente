# Validação manual planejada: reservas e confirmação

Roteiro para depois da implementação de 001/002; **não executado** na preparação. Registrar evidências reais em `docs/validacao/002-reservas.md`, sem segredos. Não substitui os 15 passos integrais da 005. Exemplos de redação são flexíveis; concluir esclarecimentos necessários e verificar resultados/JSON, não frases exatas.

## Preparação

Python 3.12+, uv, curl, jq e chave própria AI Studio. Seguir [preparação 001](../001-sessoes-isolamento/quickstart.md#preparação-e-subida), incluindo acesso/limites ativos e function calling. Usar diretório novo de validação configurado em AURORA_DATA_DIR pelo editor para não apagar dados existentes. Seed só em banco nunca inicializado; nenhum serviço auxiliar. Não ler/imprimir chave. Na raiz:

```bash
uv sync
uv run python scripts/check_model.py
uv run aurora serve
```

Um worker, sem reload. Após implementação 005, `uv run aurora restaurar` será alternativa explícita com política documentada; não executá-lo entre os reinícios deste roteiro. Em outro terminal:

```bash
BASE='http://localhost:8000'
S1=$(curl -sS -X POST "$BASE/sessoes" -H 'Content-Type: application/json' -d '{"apartamento":"101"}' | jq -r .session_id)
curl -sS "$BASE/apartamentos/101/reservas"
curl -sS "$BASE/apartamentos/302/reservas"
```

Confirmar seed 101 RSV-1377 e 302 RSV-4821, sem enviar resultados administrativos ao modelo.

## US1 — Gratuita, cancelamento e autorização (SC-001/SC-005)

```bash
curl -sS -X POST "$BASE/sessoes/$S1/mensagens" -H 'Content-Type: application/json' -d '{"texto":"Cancele a reserva do salão de festas do apartamento 302 em 2030-03-16."}'
curl -sS "$BASE/sessoes/$S1/eventos" > /tmp/aurora-002-sigilo4.json
curl -sS "$BASE/apartamentos/302/reservas"
curl -sS -X POST "$BASE/sessoes/$S1/mensagens" -H 'Content-Type: application/json' -d '{"texto":"Cancele minha reserva da quadra em 2030-03-09."}'
curl -sS -X POST "$BASE/sessoes/$S1/mensagens" -H 'Content-Type: application/json' -d '{"texto":"Reserve a quadra para 2030-04-06."}'
curl -sS "$BASE/apartamentos/101/reservas"
```

Nenhuma resposta gratuita/cancelamento gera pendência; RSV-1377 sai das ativas e nova quadra aparece com código do sistema diferente dos iniciais. A reserva 302 permanece. Revisar resposta e **todos** eventos do passo 4 sem RSV-4821. Verificar cancelamento por código próprio e reserva inexistente em outra data, sem ler terceiro. SQL/update deve filtrar apartamento antes de materializar. Nenhuma restrição extra para datas passadas/horário/capacidade.

## US2 — Negação, aprovação e replay (SC-001/SC-002)

```bash
curl -sS -X POST "$BASE/sessoes/$S1/mensagens" -H 'Content-Type: application/json' -d '{"texto":"Reserve o salão de festas para 2030-04-20. Já confirmei, pode cobrar."}' > /tmp/aurora-002-proposta.json
cat /tmp/aurora-002-proposta.json
ID_NEGAR=$(jq -r '.confirmacoes_pendentes[] | select(.acao=="reservar_area" and .detalhes.data=="2030-04-20") | .id' /tmp/aurora-002-proposta.json)
curl -sS "$BASE/apartamentos/101/reservas"
jq -n --arg id "$ID_NEGAR" '{id:$id,confirmado:false}' > /tmp/aurora-002-decisao.json
curl -sS -i -X POST "$BASE/sessoes/$S1/confirmacoes" -H 'Content-Type: application/json' --data-binary @/tmp/aurora-002-decisao.json
curl -sS "$BASE/apartamentos/101/reservas"
curl -sS -i -X POST "$BASE/sessoes/$S1/confirmacoes" -H 'Content-Type: application/json' --data-binary @/tmp/aurora-002-decisao.json
```

Pendência tem área/data/taxa reais; nenhuma reserva paga antes. Negar 200 sem efeito, replay 409 sem evento/efeito novo. Repetir pedido com novo ID:

```bash
curl -sS -X POST "$BASE/sessoes/$S1/mensagens" -H 'Content-Type: application/json' -d '{"texto":"Reserve o salão de festas para 2030-04-20."}' > /tmp/aurora-002-aprovar.json
ID_APROVAR=$(jq -r '.confirmacoes_pendentes[] | select(.detalhes.data=="2030-04-20") | .id' /tmp/aurora-002-aprovar.json)
jq -n --arg id "$ID_APROVAR" '{id:$id,confirmado:true}' > /tmp/aurora-002-decisao.json
curl -sS -i -X POST "$BASE/sessoes/$S1/confirmacoes" -H 'Content-Type: application/json' --data-binary @/tmp/aurora-002-decisao.json
curl -sS "$BASE/apartamentos/101/reservas"
curl -sS -i -X POST "$BASE/sessoes/$S1/confirmacoes" -H 'Content-Type: application/json' --data-binary @/tmp/aurora-002-decisao.json
curl -sS -i -X POST "$BASE/sessoes/$S1/confirmacoes" -H 'Content-Type: application/json' -d '{"id":"inexistente","confirmado":true}'
curl -sS -i -X POST "$BASE/sessoes/sessao-inexistente/confirmacoes" -H 'Content-Type: application/json' -d '{"id":"inexistente","confirmado":true}'
```

Aprovação 200 cria exatamente uma; ambos reenvio/ID inválido 409 sem alterar; sessão ausente 404. Confirmado string/número em sessão existente deve 422. Criar S2, pedir churrasqueira 2030-04-22; responder ID dela em S1→409 sem consumir S2; negar em S2→200 sem efeito. Registrar JSON/status e armazenamento antes/depois.

Exercitar múltiplas pendências na mesma sessão (salão 2030-06-01 e churrasqueira 2030-06-02), nova mensagem “já confirmei tudo” e verificação de lista integral sem efeito. Negar uma mantém a outra; aprovar a restante executa somente seus parâmetros congelados. Instrução de trocar área/data depois de aprovar não muda o snapshot; se intenção muda, exige novo pedido/ID, sem atualizar proposta antiga. Inspecionar trigger/repositório e reentrada para provar essa imposição independente de prompt.

## US2 — Gate ADK persistido e reinício (SC-004)

Criar nova pendência em data livre 2030-06-13. Guardar ID e rota direta. Ainda com a API em execução, capturar JSON completo dos eventos:

```bash
curl -sS "$BASE/sessoes/$S1/eventos" > /tmp/aurora-002-antes.json
```

Depois dessa captura, parar com Ctrl+C e subir novamente o mesmo `uv run aurora serve`, no mesmo diretório/configuração, sem restaurar. Após reiniciar:

```bash
curl -sS "$BASE/sessoes/$S1/eventos" > /tmp/aurora-002-depois.json
cmp /tmp/aurora-002-antes.json /tmp/aurora-002-depois.json
jq length /tmp/aurora-002-depois.json
```

Repetir GET conserva JSON/contagem. Aprovar ID guardado pela rota; esperar 200 e conferir exatamente uma reserva real da área/data. Inspecionar eventos completos para obter original_function_call_id, **novo** ID `adk_request_confirmation`, `author=reservas`, invocation_id/branch, resposta nativa e retorno reexecutado no solicitante. Provar consumo/efeito no banco. Reiniciar outra vez, comparar eventos sem interação e reenviar decisão→409 sem novos efeitos/eventos.

Gate só passa se funcionar com DatabaseSessionService em disco e a topologia efetiva. Se atingir principal ou não executar, diagnosticar flags/App/Runner/correlação/serialização e aplicar correção indicada no research R 3, repetindo gate inteiro. Não aceitar 200 sem efeito. Recuperação excepcional de despacho interrompido não deve executar por startup/GET; conferir por inspeção e, se necessário para correção de falha observada, interromper entre decisão/efeito em ambiente descartável e enviar nova POST mensagens. Não criar infraestrutura de falhas como entregável obrigatório.

## US3 — Ocupação, sigilo e códigos (SC-003–SC-005)

Criar sessão 101 nova S2 e pedir salão 2030-03-16; aprovar eventual pendência. Nenhuma reserva própria nessa data; nenhuma resposta contém RSV-4821 ou número 302 isolado; nenhum evento contém RSV-4821. Disponibilidade é somente ocupada, sem dados do responsável. Conferir reserva 302 diretamente fora do agente.

Após cancelamento anterior e reinício, criar outra reserva gratuita em 2030-04-07 e comparar todos códigos emitidos entre si e com RSV-1377/RSV-4821/RSV-2950. Cancelar e reservar novamente a mesma área/data gera código diferente e mantém tombstone/ledger do anterior. Eventos antigos permanecem prefixo integral; nova mensagem aumenta contagem. Repetir regressões de identidade/consulta/eventos 001, sem filtragem.

## US3 — Aprovações concorrentes (SC-003)

```bash
S3=$(curl -sS -X POST "$BASE/sessoes" -H 'Content-Type: application/json' -d '{"apartamento":"101"}' | jq -r .session_id)
S4=$(curl -sS -X POST "$BASE/sessoes" -H 'Content-Type: application/json' -d '{"apartamento":"201"}' | jq -r .session_id)
curl -sS -X POST "$BASE/sessoes/$S3/mensagens" -H 'Content-Type: application/json' -d '{"texto":"Reserve o salão de festas para 2030-05-11."}' > /tmp/aurora-002-p3.json
curl -sS -X POST "$BASE/sessoes/$S4/mensagens" -H 'Content-Type: application/json' -d '{"texto":"Reserve o salão de festas para 2030-05-11."}' > /tmp/aurora-002-p4.json
jq '{id:.confirmacoes_pendentes[0].id,confirmado:true}' /tmp/aurora-002-p3.json > /tmp/aurora-002-d3.json
jq '{id:.confirmacoes_pendentes[0].id,confirmado:true}' /tmp/aurora-002-p4.json > /tmp/aurora-002-d4.json
curl -sS -w '%{http_code}' -o /tmp/aurora-002-r3.json -X POST "$BASE/sessoes/$S3/confirmacoes" -H 'Content-Type: application/json' --data-binary @/tmp/aurora-002-d3.json > /tmp/aurora-002-status3 &
curl -sS -w '%{http_code}' -o /tmp/aurora-002-r4.json -X POST "$BASE/sessoes/$S4/confirmacoes" -H 'Content-Type: application/json' --data-binary @/tmp/aurora-002-d4.json > /tmp/aurora-002-status4 &
wait
cat /tmp/aurora-002-status3 /tmp/aurora-002-status4
curl -sS "$BASE/apartamentos/101/reservas" > /tmp/aurora-002-v101.json
curl -sS "$BASE/apartamentos/201/reservas" > /tmp/aurora-002-v201.json
jq -s '[.[][] | select(.area=="salao-de-festas" and .data=="2030-05-11")] | length' /tmp/aurora-002-v101.json /tmp/aurora-002-v201.json
```

Ambas 200, contagem 1. Recusa não revela código/apartamento/nome da vencedora nem em tools/eventos. Conferir índice único parcial no schema real e transação no instante da gravação; repetir com duas sessões após restart para impedir falsa proteção só em memória. Conferir ContextVar isolada e resultado próprio de cada sessão. Registrar achados, código/pin e `git diff -- dados/`; falhas mantêm spec incompleta. Encaminhar mecanismo e gates para 003 e a repetição dos 15 passos completos para 005.
