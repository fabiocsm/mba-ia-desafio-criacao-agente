# Contrato de operação e entrega futura

## Comandos

Todos futuros, a implementar/validar antes da entrega. Executar da raiz, usando caminhos runtime absolutos resolvidos por config; nenhum serviço de banco externo local.

| Comando | Pré-condição | Resultado |
| --- | --- | --- |
| `uv sync` | Python >=3.12 e uv; lock versionado | ambiente compatível com `google-adk==2.2.0` |
| `uv run python scripts/check_model.py` | `.env` privado com chave AI Studio e modelo permitido | acesso e function call simples; não comprova quotas ativas ou fluxo completo |
| `uv run aurora restaurar` | API parada; exclusivo de `var/operation.lock` | código 0 somente após reset/checagem dos dois bancos; dados/ intacto; sessões/pendências/decisões/eventos descartados; ledger/contador preservados |
| `uv run aurora serve` | compartilhado no mesmo lock; sem marcador de reset | API em `http://localhost:8000`, um worker; nunca resetar por subir |

Erro de pré-condição/lock/arquivo/schema/reset retorna código diferente de zero com diagnóstico sem segredo. Se API estiver ativa, `restaurar` falha antes de escrever. Se marcador existir, serve falha sem abrir serviço; orientar repetir restaurar após parar todos processos. Reset interrompido conserva marcador e só reabre após repetição idempotente completa. Não remover banco ADK/WAL/SHM com conexões vivas. Não remover arquivo de lock durante operação. Detalhes/fases em [plano](../plan.md) e [modelo](../data-model.md).

## Configuração

Herdar nomes necessários da config001: `GOOGLE_API_KEY`, `GEMINI_MODEL` e eventuais caminhos de banco configuráveis efetivamente implementados. Conferir config final antes de publicar `.env.example`; cada variável listada sem valor. Defaults seguros/caminhos no código e manual, nunca preencher chave de exemplo. `.env`, `var/` e snapshots privados ignorados. Avaliador fornece a chave; conferir limites ativos no AI Studio, sem registrar credencial nem presumir quota.

## HTTP invariável

Reutilizar integralmente [contrato comum](../../README.md#contrato-externo-comum) e [API 001](../../001-sessoes-isolamento/contracts/api.md), [confirmação 002](../../002-reservas-confirmacoes/contracts/api.md), sem novas rotas ou formatos. Sessão ausente →404 em mensagens/confirmações/eventos; ID não pendente da sessão →409; aprovações válidas concorrentes →200/200 com uma reserva total; respostas JSON e listas diretas sem envelope extra.

## Manual e entrega

Antes da futura substituição do README, copiar integralmente enunciado para `docs/desafio-original.md` e apontar as referências normativas permanentes a ele. README final tem Arquitetura (quatro agentes, responsabilidades, acionamento, motivos, Runner/App/persistência), Garantias (cinco regras com código/trechos reais e por que modelo não contorna) e Como rodar (pré-requisitos, variáveis, uv sync, modelo/quota, subida, restauração, política de sessões/falha parcial). Código inexistente não serve como referência.

Entrega futura: fork público do repositório base, conteúdo final completo em main e link registrado em `docs/entrega.md`/mensagem final. Antes de fornecer link, conferir visibilidade, branch, commit, clone limpo, dados idênticos, ausência de segredos e gates integrais. Este contrato não executa publicação, merge ou implantação.
