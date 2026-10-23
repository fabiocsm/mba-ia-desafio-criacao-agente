# Contrato: visitantes no runtime e API comuns

Extensão dos contratos [HTTP 001](../../001-sessoes-isolamento/contracts/api.md) e [confirmação 002](../../002-reservas-confirmacoes/contracts/confirmation-runtime.md). Nenhuma rota adicional.

## Tools e executor

| Interface | Argumentos | Resultado e autoridade |
| --- | --- | --- |
| `autorizar_visitante(nome,data,tool_context)` | LLM escolhe somente nome/data; ToolContext injetado | Nome/data ausentes pedem esclarecimento; validar data civil; resolver SessionIdentity. Inicial: preparar snapshot, request_confirmation nativa e retorno sem acesso. Reentrada: consumir via coordenador a decisão correlata; retornar autorização própria/negação ou resultado já salvo |
| `listar_meus_visitantes(tool_context)` | Nenhum argumento LLM | SELECT filtrado pelo apartamento da sessão antes de materializar; lista `{nome,data}`, inclusive vazia; nunca fallback administrativo |
| Executor `autorizar_visitante` | conexão/transação do coordenador, identidade e snapshot/proposta canônicos | Só chamado durante consumo aprovado; INSERT com proposta_id, retorna resultado próprio. Não abre transação nem commit, não decide consentimento e não consulta outro apartamento |

Nenhuma tool aceita apartamento, sessão, ID público/nativo, author, confirmed ou invocation escolhidos pelo modelo. A proposta pertence à SessionIdentity; alterar state ou argumentos reexecutados não altera o efeito. Não expor executor como tool autônoma. Uma proposta de visita não autoriza nem nega a reserva paga da mesma sessão.

## Confirmação nativa e HTTP

1. Congelar nome/data; `prepare` idempotente pela chamada original. `request_confirmation(hint=...,payload={nome,data})`; não inserir visita. Persistir evento nativo integral antes de correlacionar/publish. ID da tool original e ID novo de `adk_request_confirmation` são distintos.
2. `POST /sessoes/{session_id}/confirmacoes`, JSON `{id,confirmado}`: primeiro sessão existente, depois CAS apenas de pendência própria. ID inexistente/alheio/respondido →409 sem mutação/Runner; sessão ausente →404. Booleano estrito, sem coerção de string. Somente esta rota decide.
3. Runtime envia FunctionResponse nativa com `name=adk_request_confirmation`, ID novo e `response={confirmed:booleano}`, invocation original, ContextVar confiável e Runner no especialista autor. Manter App resumível, serviço persistido e flags 001/002. Validar correlação canônica na reentrada; ToolConfirmation isolada não concede autorização.
4. Consumo e inserção/negação/resultado no mesmo commit de negócio. Depois de eventos persistidos, concluir despacho; somente então 200. Reentrada técnica retorna resultado salvo; replay HTTP continua409, inclusive depois de restart.
5. Startup só reconcilia metadados; GET apenas lê. Despacho decidido incompleto recupera somente em nova POST mensagens, antes do texto, pelo Runner. Não reescrever eventos ou afirmar atomicidade entre bancos.

`POST /sessoes/{session_id}/mensagens` recebe `{texto}` e retorna 200 com `resposta` string (pode ser vazia) e lista completa `confirmacoes_pendentes`. Confirmações válidas usam o mesmo envelope. Projeção de uma pendência de acesso:

```json
{"id":"uuid-gerado-pelo-sistema","acao":"autorizar_visitante","detalhes":{"nome":"Joana Ribeiro","data":"2030-04-21"}}
```

`GET /apartamentos/{apartamento}/visitantes` retorna 200 com lista de `{nome,data}` diretamente do banco; antes da aprovação não contém a nova visita, depois contém o efeito. Permanece exclusivamente administrativo, fora das ferramentas. `GET /sessoes/{session_id}/eventos` retorna todos os eventos completos, em ordem, sem modificar histórico; sessão ausente recebe 404 em todas as rotas de sessão.

## Gates observáveis

Mensagens alegando consentimento ou apartamento diferente não produzem decisão nem acesso. Negar/ID inválido/alheio/replay preservam visitantes existentes. Validar isolamento nas respostas, retornos de tools e eventos integrais. Propostas distintas com mesmo nome/data podem produzir duas autorizações após duas aprovações; não confundir com replay da mesma confirmação. Demonstrar nome/data originais e agente solicitante correto com SQLite e restart; 200 sem visita correspondente falha o gate.
