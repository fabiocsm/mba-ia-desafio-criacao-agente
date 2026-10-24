# Operação da API

Manual de subida, restauração e limites. O README da raiz resume o mesmo
caminho. O enunciado do desafio está em `docs/desafio-original.md`. Não há
serviço auxiliar além deste processo.

## Pré-requisitos

- Python 3.12 ou superior
- [uv](https://docs.astral.sh/uv/)
- Chave própria do Google AI Studio

Não há banco externo, fila ou outro serviço local para subir. Os dois SQLite
ficam no diretório de dados.

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

Os nomes vêm de `src/aurora/config.py`. `.env.example` traz somente esses
nomes, sem valores. `.env` e `var/` ficam fora do Git. O pin é
`google-adk==2.2.0`.

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

Em 2026-10-23, `uv run python scripts/check_model.py` respondeu
`modelo=gemini-3.5-flash-lite` e `chamada_de_funcao=sim`, sem imprimir a chave.
No mesmo dia, a API respondeu `429` com o limite do free tier: 15 requisições
por minuto para `gemini-3.5-flash-lite`. TPM e RPD não vieram nessa resposta.
Uma mensagem com transferência entre agentes gasta várias chamadas. Com esse
teto, vale espaçar as mensagens. O número não vale para outra chave.

## Subida

```bash
uv run aurora serve
```

O comando executa Uvicorn em `0.0.0.0:8000` com um worker e sem reload. A API
responde em `http://localhost:8000`.

O processo pega o lock compartilhado de `operation.lock` antes de abrir
qualquer banco e o segura até encerrar. Não chama `restaurar`. No primeiro uso
de um diretório ainda sem a marca de inicialização, cria `aurora.sqlite3` e
`adk.sqlite3` e importa, numa única transação, os cadastros de `dados/`. Os
arquivos de `dados/` não são alterados. Um diretório já inicializado é
reaberto como está: reiniciar não reaplica o seed nem desfaz reservas,
cancelamentos, visitantes, autorizações, sessões, pendências, decisões ou
eventos. O startup também não chama o modelo e não acrescenta eventos. Ele
reconstrói o índice do regulamento em memória, a partir de
`dados/regulamento.md`, e só publica uma proposta cujo evento de confirmação
já estava gravado e ainda não tinha sido correlacionado.

Se existir `reset-in-progress.json`, `serve` termina com erro e não abre a
API. Repita a restauração com todos os processos parados.

## Restauração

Com a API parada e o processo anterior já encerrado:

```bash
uv run aurora restaurar
```

Sucesso só depois de conferir os dois bancos. O comando:

- não edita `dados/`
- apaga sessões, eventos, propostas, decisões e despachos
- elimina pendências; nenhuma confirmação antiga volta a executar
- repõe reservas e visitantes iniciais, estes com `proposta_id` nulo
- preserva apartamentos, áreas, o ledger de todos os códigos emitidos e o
  contador monotônico

Sessão antiga responde `404`. Código inicial, cancelado ou emitido antes do
reset não é reutilizado.

Se `serve` ainda estiver ativo, `restaurar` retorna código diferente de zero
antes de criar o marcador e antes de escrever nos bancos.

Não há transação única entre `aurora.sqlite3` e `adk.sqlite3`. O marcador
`reset-in-progress.json` é criado antes da primeira alteração. Se o processo
cair depois disso, o marcador fica e `serve` continua recusando a subida,
mesmo que o banco de negócio já tenha voltado ao início e o do ADK ainda não.
Pare tudo e execute `uv run aurora restaurar` de novo. A repetição é
idempotente: no fim, as duas bases correspondem ao reset e o marcador sai.
Não apague o marcador nem o arquivo de lock à mão. Não remova o banco do ADK
com a API no ar.

Para repetir um roteiro sem mexer no diretório padrão, use outro caminho:

```bash
AURORA_DATA_DIR=var/ensaio uv run aurora restaurar
AURORA_DATA_DIR=var/ensaio uv run aurora serve
```

Os dois comandos precisam do mesmo `AURORA_DATA_DIR`, porque o lock e o
marcador ficam nesse diretório.

## Rotas

- `POST /sessoes`
- `POST /sessoes/{session_id}/mensagens`
- `POST /sessoes/{session_id}/confirmacoes`
- `GET /sessoes/{session_id}/eventos`
- `GET /apartamentos/{apartamento}/reservas`
- `GET /apartamentos/{apartamento}/visitantes`

A quadra, de taxa zero, é reservada na hora. Salão, churrasqueira e autorização
de visitante ficam pendentes até `POST /sessoes/{session_id}/confirmacoes` com
`id` e `confirmado` booleano. Cancelamento de reserva própria não pede
confirmação. Dúvida sobre o regulamento usa a mesma rota de mensagens.

## Consulta ao regulamento

Uma pergunta de regra segue o agente `regulamento`. A seleção usa o texto
recebido pela API, não uma paráfrase do modelo. Horário de piscina no domingo
sai do artigo 22, inciso II, da fonte. Pergunta vaga, pedido do documento
inteiro ou tema sem regra respondem `200`, com esclarecimento ou ausência,
e não criam pendência.

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
que pediu a confirmação, só nessa retomada. A limitação oficial do
`DatabaseSessionService` continua um gate de execução: a evidência válida é o
efeito nas rotas diretas, com a sessão persistida, inclusive depois de
reiniciar. Resposta HTTP sem efeito não conta.

## Parar

Interrompa o processo com Ctrl+C e aguarde o encerramento. Só então rode
`restaurar`, se for o caso. Subir outra vez com o mesmo comando e o mesmo
`AURORA_DATA_DIR`, sem `restaurar`, continua a mesma base.
