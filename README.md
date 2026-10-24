# Residencial Aurora

Assistente do condomínio em `http://localhost:8000`. O morador conversa com um
agente principal; reservas, visitantes e regulamento ficam com especialistas.
O modelo conduz a conversa. O código decide o que pode ser lido, cobrado ou
gravado.

O enunciado do desafio está preservado em
[docs/desafio-original.md](docs/desafio-original.md).

## Arquitetura

Há quatro agentes `LlmAgent` em modo `chat`, no modelo de `GEMINI_MODEL`
(padrão `gemini-3.5-flash-lite`). `src/aurora/runtime/app.py` monta um `App`
resumível cuja raiz é `aurora_principal`. Esse principal declara `sub_agents`:
`reservas`, `visitantes` e `regulamento`. Não há sessão filha. Os três
especialistas usam `disallow_transfer_to_parent=False` e
`disallow_transfer_to_peers=True`: devolvem a conversa ao principal e não se
transferem entre si.

| Agente | Responsabilidade | Acionamento | Motivo da divisão |
| --- | --- | --- | --- |
| `aurora_principal` | Entende o pedido e responde. Não lê o banco e não recebe o texto do regulamento. | Raiz do `App`. | Um interlocutor só encaminha. |
| `reservas` | Lista, reserva, cancela e informa se a data está livre ou ocupada. | O principal transfere para ele. | Agenda de área, com efeito e disputa de data. |
| `visitantes` | Lista nome e data e pede autorização de entrada. | O principal transfere para ele. | Acesso de pessoas, distinto da reserva. |
| `regulamento` | Responde a dúvida com os trechos já autorizados para aquela mensagem. | O principal transfere para ele. | A norma não entra no prompt do principal. |

A divisão separa agenda, acesso e norma. Cada especialista só recebe as
próprias tools, em `src/aurora/tools/reservas.py`,
`src/aurora/tools/visitantes.py` e `src/aurora/tools/regulamento.py`.

`src/aurora/runtime/service.py` sobe um `AuroraRunner`
(`src/aurora/runtime/runner.py`) com `OrderedDatabaseSessionService`. Cada
execução usa o `session_id` também como `user_id`. O cliente não envia agente,
estado nem apartamento. Há dois SQLite no diretório de dados, por padrão
`var/`: `aurora.sqlite3` (cadastro, identidade, reservas, visitantes, ledger,
propostas e decisões) e `adk.sqlite3` (sessões e eventos do ADK).

O detalhe dos fluxos está em [docs/arquitetura.md](docs/arquitetura.md).

## Garantias

Cada regra abaixo é imposta por código. Uma frase do morador ou uma decisão do
modelo não a substitui.

### 1. Cobrança ou acesso só com confirmação

Reserva com taxa maior que zero e autorização de visitante chamam
`request_confirmation` e não gravam o efeito. A pendência nasce quando o
evento `adk_request_confirmation` é persistido. Só
`POST /sessoes/{session_id}/confirmacoes` decide.

A rota confere a sessão antes de aceitar o corpo. ID inexistente, de outra
sessão ou já respondido recebe `409` sem efeito
(`src/aurora/api_routes/confirmacoes.py`, `confirmar`). `AuroraRuntime.confirmar`
grava a decisão e só então retoma o `Runner` na invocação original
(`src/aurora/runtime/service.py`). `AuroraRunner._find_agent_to_run` devolve o
especialista que pediu a confirmação quando a retomada canônica está ativa;
fora disso, vale a escolha do ADK (`src/aurora/runtime/runner.py`).

O executor da reserva paga insere a linha com área, data e taxa já congeladas
na proposta (`executar_reserva_paga` em `src/aurora/storage/reservas.py`).
Argumentos novos da reentrada não trocam esse snapshot. Negar não chama o
executor. Quadra (taxa zero) e cancelamento de reserva própria não pedem
confirmação. As tools não recebem um parâmetro de “já confirmei”.

### 2. Identidade imutável e isolamento por apartamento

O apartamento é gravado uma vez em `session_identity`. O trigger
`session_identity_imutavel` aborta qualquer `UPDATE`
(`src/aurora/storage/schema.py`). As tools obtêm o apartamento por
`resolve_identity`, a partir de `tool_context.session.id`
(`src/aurora/tools/context.py`). Elas não declaram apartamento. Listagem,
reserva e cancelamento filtram esse vínculo antes de montar o resultado.
A agenda devolve só livre ou ocupada. As rotas `GET /apartamentos/...` leem o
banco direto para o avaliador e não são tools do agente.

### 3. Persistência e identificadores únicos

Sessões e eventos ficam em `adk.sqlite3`.
`OrderedDatabaseSessionService.append_event` grava chamada, resultado e
transferência sem filtrar o histórico (`src/aurora/runtime/sessions.py`).
Subir a API chama `initialize_storage` só no banco ainda sem a marca
`inicializado` e não chama `executar_restauracao` (`AuroraRuntime.start` e
`_serve` em `src/aurora/cli.py`). `GET /sessoes/{session_id}/eventos` apenas lê.

Códigos novos saem de `emitir_codigo` (`src/aurora/storage/codigos.py`), que
grava o ledger e avança `sequencia_codigo` na mesma transação. Cancelar não
apaga o código. A restauração explícita também não apaga o ledger nem reduz o
contador (`src/aurora/storage/reset.py`).

`uv run aurora restaurar` exige a API parada. Apaga sessões, eventos,
propostas, decisões e despachos, e repõe reservas e visitantes a partir de
`dados/`, sem editar esses arquivos. Se a restauração parar no meio, o
marcador `var/reset-in-progress.json` permanece e `aurora serve` recusa
iniciar até um `aurora restaurar` concluir as duas bases.

### 4. Consulta seletiva ao regulamento

A instrução de `aurora_principal` diz que ele não tem o texto do regulamento
(`INSTRUCAO` em `src/aurora/agents/principal.py`). O texto de
`dados/regulamento.md` não é copiado para esse prompt.

Antes do `Runner`, `autorizar_mensagem` escolhe as unidades da mensagem HTTP
original (`src/aurora/regulamento/selection.py`). `consultar_regulamento` não
aceita tema nem capítulo: `consultar` só materializa o escopo já autorizado
(`src/aurora/tools/regulamento.py`). Sem escopo, o retorno não traz trecho.
Os eventos guardam a chamada e o resultado dessa consulta, não os outros
capítulos. A rota de eventos não remove conteúdo.

### 5. Exclusividade no instante da gravação

O índice único parcial `reserva_ativa_area_data` em `(area, data) WHERE
cancelada = 0` (`src/aurora/storage/schema.py`) é a autoridade no `INSERT`.
Consultar a agenda antes não ocupa a data. `executar_reserva_paga` usa um
savepoint: violação do índice vira recusa `indisponivel`, sem ler a reserva
vencedora (`src/aurora/storage/reservas.py`). As duas aprovações válidas
respondem `200`; só uma linha ativa permanece.

## Como rodar

### Pré-requisitos

- Python 3.12 ou superior
- [uv](https://docs.astral.sh/uv/)
- Chave própria do Google AI Studio

Não há banco, fila ou outro serviço local para subir. Os dois SQLite nascem
no diretório de dados.

### Configuração

Na raiz do repositório:

```bash
uv sync
cp .env.example .env
```

Abra `.env` no editor e preencha somente na sua máquina. Não cole a chave no
terminal e não versione `.env`.

| Variável | Papel |
| --- | --- |
| `GOOGLE_API_KEY` | Chave do Google AI Studio. Obrigatória para conversar com o modelo. |
| `GEMINI_MODEL` | Opcional. Vazio usa `gemini-3.5-flash-lite`. |
| `AURORA_DATA_DIR` | Opcional. Vazio usa `var/` na raiz. Caminho relativo resolve a partir dessa raiz. |

`.env.example` traz só os nomes, sem valores. O projeto fixa `google-adk==2.2.0`.

Antes do roteiro, confira na documentação do Gemini e no AI Studio do projeto
da chave os limites ativos (RPM, TPM e RPD) do modelo escolhido. O fluxo do
avaliador gasta várias chamadas por mensagem. Este repositório não presume
quota. Em 2026-10-23 a API deste projeto respondeu `429` com 15 requisições
por minuto no free tier de `gemini-3.5-flash-lite`; TPM e RPD não vieram nessa
resposta e podem ser outros na sua chave.

```bash
uv run python scripts/check_model.py
```

O script mostra o modelo e se uma chamada de função simples funcionou. Não
imprime a chave e não mede a quota. Se o modelo estiver indisponível, troque
`GEMINI_MODEL` para uma alternativa já conferida, como `gemini-3.8-flash`, e
repita o script.

### Subida

Com a restauração já feita, ou no primeiro uso de um diretório vazio:

```bash
uv run aurora serve
```

A API fica em `http://localhost:8000`, um worker, sem reload. Subir não
restaura dados, não apaga sessões e não cria eventos. Pare com Ctrl+C e
aguarde o processo encerrar. Subir de novo com o mesmo diretório continua a
mesma base.

### Restauração

Com a API parada:

```bash
uv run aurora restaurar
```

O comando volta reservas e visitantes ao conteúdo de `dados/` e não altera
esses arquivos. Apaga sessões, eventos, pendências, decisões e despachos:
sessão antiga passa a responder `404` e nenhuma confirmação antiga executa.
O ledger e o contador de códigos permanecem; código inicial, cancelado ou
emitido antes não é reutilizado.

Se `aurora serve` estiver no ar, `restaurar` termina com erro e não escreve.
Se o processo cair no meio, `var/reset-in-progress.json` fica no diretório de
dados e `aurora serve` recusa iniciar. Pare todos os processos e repita
`uv run aurora restaurar` até a mensagem de conclusão. Não há commit único
entre os dois arquivos SQLite; o marcador é o que impede servir um estado pela
metade. Apague o marcador só por um `restaurar` concluído, não na mão.

A operação longa está em [docs/operacao.md](docs/operacao.md).
