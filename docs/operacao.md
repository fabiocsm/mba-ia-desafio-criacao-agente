# Operação da API — sessões, reservas, visitantes e confirmação

Este manual cobre a base da spec 001, as reservas com confirmação da spec 002
e a autorização de visitantes da spec 003. O README do enunciado permanece na
raiz. A restauração explícita de reservas e visitantes, e o manual final de
entrega, ficam para a spec 005. Subir a API não restaura dados nem apaga
sessões, visitas, decisões ou eventos. Não há serviço auxiliar além deste
processo.

## Pré-requisitos

- Python 3.12 ou superior
- [uv](https://docs.astral.sh/uv/)
- Chave própria do Google AI Studio

Não há banco externo, fila ou outro serviço local para subir.

## Configuração

Na raiz do repositório:

```bash
uv sync
cp .env.example .env
```

Abra `.env` no editor e preencha `GOOGLE_API_KEY`. Não cole a chave no
terminal e não versione `.env`.

| Variável | Papel |
| --- | --- |
| `GOOGLE_API_KEY` | Chave do Google AI Studio. Obrigatória para conversar com o modelo. |
| `GEMINI_MODEL` | Opcional. Vazio usa `gemini-3.5-flash-lite`. |
| `AURORA_DATA_DIR` | Opcional. Vazio usa `var/` na raiz do repositório. Caminho relativo é resolvido a partir dessa raiz. |

`.env.example` traz somente os nomes, sem valores. `.env` e `var/` ficam fora do Git.

## Modelo

Antes do roteiro conversacional, confira no AI Studio os limites ativos do
projeto da chave (RPM, TPM e RPD) para o modelo escolhido. O script abaixo só
prova que a chave alcança o modelo e que uma chamada de função simples funciona.
Ele não imprime a chave e não mede a quota.

```bash
uv run python scripts/check_model.py
```

Se o modelo estiver indisponível, troque `GEMINI_MODEL` para uma alternativa
já conferida no projeto, como `gemini-3.8-flash`, e repita o script. Não há
troca automática.

O probe limita cada chamada HTTP a 120 segundos. Na API, cada execução do
Runner tem prazo total de 120 segundos, incluindo as chamadas ao modelo e
tools. Se esse prazo expirar, a API cancela a execução, libera a sessão para
novas mensagens e devolve `504` em JSON com
`{"detail":"Tempo limite de atendimento excedido."}`. Eventos já persistidos
continuam disponíveis integralmente em `/sessoes/{session_id}/eventos`;
o prazo não apaga nem desfaz esses registros. Mensagens da mesma sessão são
serializadas; o prazo de execução começa após a espera pela mensagem anterior.

## Subida

```bash
uv run aurora serve
```

O comando executa Uvicorn em `0.0.0.0:8000` com um worker e sem reload. A API
responde em `http://localhost:8000`.

No primeiro uso de um diretório de dados ainda sem a marca de inicialização, a
API cria `aurora.sqlite3` e `adk.sqlite3` e importa, numa única transação, os
cadastros de `dados/`. Os arquivos de `dados/` não são alterados. Um diretório
já inicializado é reaberto como está: reiniciar não reaplica o seed nem desfaz
reservas, cancelamentos, visitantes, autorizações, sessões, pendências,
decisões ou eventos. O startup também não chama o modelo e não acrescenta
eventos. Ele só publica uma proposta cujo evento de confirmação já estava
gravado e ainda não tinha sido correlacionado. Não restaura visitantes.

Para repetir uma carga inicial sem apagar um diretório já usado, aponte
`AURORA_DATA_DIR` para uma pasta vazia e suba de novo.

## O que esta versão atende

- `POST /sessoes`
- `POST /sessoes/{session_id}/mensagens`
- `POST /sessoes/{session_id}/confirmacoes`
- `GET /sessoes/{session_id}/eventos`
- `GET /apartamentos/{apartamento}/reservas`
- `GET /apartamentos/{apartamento}/visitantes`

A quadra, de taxa zero, é reservada na hora. Salão, churrasqueira e autorização
de visitante ficam pendentes até `POST /sessoes/{session_id}/confirmacoes` com
`id` e `confirmado` booleano. Cancelamento de reserva própria não pede
confirmação. Consulta ao regulamento ainda não está disponível.

## Confirmação e recuperação

Uma frase no chat não aprova nem nega. A decisão fica no banco de negócio,
junto com um despacho. A rota então retoma o Runner na invocação original.
Se o processo cair depois da decisão e antes de concluir a retomada, reenviar
o mesmo `id` responde `409` e não executa de novo. A retomada ocorre na
próxima `POST /sessoes/{session_id}/mensagens` da mesma sessão, antes do texto
novo, reutilizando a decisão já gravada. `GET /sessoes/{session_id}/eventos` só
lê. Depois de uma confirmação `200`, o despacho está concluído e um reinício
não cria eventos nem repete o efeito.

O ADK 2.2.0 escolhe o agente antes da mensagem de retomada. Quando o último
evento é do principal, `src/aurora/runtime/runner.py` devolve o especialista
que pediu a confirmação, só nessa retomada. O mecanismo e o limite oficial do
`DatabaseSessionService` estão em `docs/arquitetura.md`.

Para repetir o roteiro sem mexer em `var/` já usado, suba com outro diretório:

```bash
AURORA_DATA_DIR=var/validacao-003 uv run aurora serve
```

Pare com Ctrl+C e suba de novo o mesmo comando, no mesmo diretório, sem
restaurar. A pendência de visitante ou de reserva sobrevive, e a aprovação
depois do reinício grava o efeito uma vez. Reenviar a mesma decisão responde
`409`. Não existe comando de restauração nesta entrega. A spec 005 deve apagar
as autorizações antes das propostas, invalidar sessões e pendências, reimportar
os visitantes iniciais e preservar o ledger e o contador de códigos.

## Limite observado nesta validação

Em 2026-10-23, `uv run python scripts/check_model.py` respondeu
`modelo=gemini-3.5-flash-lite` e `chamada_de_funcao=sim`, sem imprimir a chave.
No mesmo dia, a API respondeu `429` com o limite do free tier: 15 requisições
por minuto para `gemini-3.5-flash-lite`. TPM e RPD não vieram nessa resposta.
Uma mensagem com transferência entre agentes gasta várias chamadas. Com esse
teto, vale espaçar as mensagens ou ampliar a quota do projeto. O número não
vale para outra chave. Se a cota estoura depois que a tool já gravou o efeito
e o evento de retorno, a confirmação conclui com `200` e não repete a gravação.

## Parar

Interrompa o processo com Ctrl+C. Subir outra vez com o mesmo comando e o mesmo
`AURORA_DATA_DIR` continua a mesma base.
