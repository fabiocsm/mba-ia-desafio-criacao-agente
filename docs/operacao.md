# Operação da API — sessões e consultas

Este manual cobre a base da spec 001. O README do enunciado permanece na raiz.
A restauração explícita de reservas e visitantes, e o manual final de entrega,
ficam para a spec 005. Subir a API não restaura dados nem apaga sessões.

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
reservas, visitantes, sessões ou eventos.

Para repetir uma carga inicial sem apagar um diretório já usado, aponte
`AURORA_DATA_DIR` para uma pasta vazia e suba de novo.

## O que esta versão atende

- `POST /sessoes`
- `POST /sessoes/{session_id}/mensagens`
- `GET /sessoes/{session_id}/eventos`
- `GET /apartamentos/{apartamento}/reservas`
- `GET /apartamentos/{apartamento}/visitantes`

Não há rota de confirmação nesta entrega. Reserva com cobrança, cancelamento,
autorização de visitante e consulta ao regulamento não estão disponíveis.

## Limite observado nesta validação

Em 2026-10-23, a chave usada no desenvolvimento respondeu `429` com o limite
do free tier: 15 requisições por minuto para `gemini-3.5-flash-lite`. TPM e
RPD não vieram nessa resposta, e a página de limites do AI Studio pediu login.
Uma mensagem com transferência entre agentes gasta várias chamadas. Com esse
teto, vale espaçar as mensagens ou ampliar a quota do projeto. O número não
vale para outra chave.

## Parar

Interrompa o processo com Ctrl+C. Subir outra vez com o mesmo comando e o mesmo
`AURORA_DATA_DIR` continua a mesma base.
