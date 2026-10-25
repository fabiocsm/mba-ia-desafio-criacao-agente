# Contrato interno: operações, confirmação e retomada

Herda identidade e eventos da [001](../../001-sessoes-isolamento/contracts/runtime-tools.md). `ToolContext` é injetado, não argumento do schema LLM. Nenhuma assinatura aceita apartamento, sessão, author, decisão ou taxa escolhidos pelo modelo.

| Tool | Argumentos LLM | Comportamento/retorno autorizado | Agente |
| --- | --- | --- | --- |
| reservar_area | area ID, data AAAA-MM-DD | Taxa real zero: reserva própria confirmada ou indisponível. Taxa positiva: proposta/confirmacão nativa sem efeito, depois resultado próprio ou recusa genérica na reentrada | reservas |
| cancelar_minha_reserva | codigo opcional; area/data opcionais para identificar própria | Exigir codigo ou area+data; SELECT/UPDATE filtrado pelo apartamento; cancelada ou não encontrada/permitida genérica, sem confirmação | reservas |
| listar_minhas_reservas | nenhum | Somente ativas próprias com codigo/area/data | reservas |
| consultar_disponibilidade | area, data | Apenas livre/ocupada por EXISTS, nunca identidade do ocupante | reservas |

Validar área existente, data civil e informação suficiente sem novas regras de elegibilidade. Códigos fornecidos pelo modelo são seletores, não autorização. Quando o pedido não identifica uma reserva própria, esclarecer sem enumerar reservas de terceiros. Prompts evitam ecoar identificadores/apartamentos de terceiros; código impede que dados reais alheios entrem nas ferramentas. Não realizar busca administrativa para confirmar se reserva alheia existe.

## Interface reutilizável de confirmação

`ConfirmationCoordinator` em runtime/confirmacoes.py e repositório storage/confirmacoes.py oferecem:

- `prepare(identity, action, frozen_parameters, original_call_id, invocation_id, author, branch)`: insert idempotente de proposta preparando. Só admite ações registradas; parâmetros imutáveis e validados pela ação.
- `publish_from_event(event)`: após append ADK persistido, encontra `adk_request_confirmation.args.originalFunctionCall.id` e `toolConfirmation`; vincula ID nativo, invocation/author/branch canônicos e publica. Sem misturar chamadas de sessões/branches diferentes. Reconciliar metadados pelo histórico persistido, sem criar/regravar eventos.
- `decide(session_id, public_id, confirmed)`: somente chamada pela rota sistêmica, sob lock da sessão. Confere SessionIdentity, pendência e booleano; grava decisão imutável e despacho. ID inválido/alheio/respondido→409, sessão ausente→404. Não registrar esta função como tool nem aceitar decisão em parâmetros LLM/state.
- `resume(decision)`: cria FunctionResponse nativa usando ID ADK novo; chama Runner com user_id/session_id internos e invocation_id original, ContextVar confiável instalada/resetada em try/finally. Usa contexto também na recuperação de despacho já autorizado. Não chama executor de negócio diretamente.
- `consume_in_tool(tool_context)`: resolve identidade canônica e original function_call_id; confere sessão/invocation/author da correlação e decisão registrada. Sem decisão válida não há efeito mesmo se ToolConfirmation alegar confirmed. Transação consome decisão+executa ação registrada ou nega+salva resultado. Resultado próprio reaproveitável após repetição técnica. Nenhum parâmetro da reentrada substitui o snapshot do banco.
- `list_pending(session_id)`: projeção pública de todas as propostas pendentes sem decisão, em ordem estável; lê banco, sem inferir do texto/evento isolado.

A reserva paga congela area/data/taxa; visitante 003 congelará nome/data e usará `acao=autorizar_visitante`. Executor da 003 será registrado no mesmo consumo transacional, com seu repositório usando a mesma conexão/transação de negócio; não fazer commit independente na callback. O contrato de decisão é o mesmo, sem nova rota.

## Caminho ADK 2.2.0

A primeira tool chama `tool_context.request_confirmation(hint=..., payload=snapshot_exibicao)` e retorna sem mutação. O ADK gera novo `adk_request_confirmation` e pausa o fluxo conforme App resumível. O adapter grava todos eventos completos e publica correlação depois do append. Na retomada:

```text
Content(role=user,
  parts=[Part(function_response=FunctionResponse(
    name=adk_request_confirmation,
    id=native_confirmation_id,
    response={confirmed: decisão_booleana}
  ))])
Runner.run_async(user_id=session_id, session_id=session_id,
  invocation_id=invocation_original, new_message=conteúdo_acima)
```

O processador ADK resolve chamada original e reexecuta a tool; `tool_context.function_call_id` é o ID original, não o novo. Preservar agent author/branch/invocation nas correlações. Principal e especialistas seguem topologia 001, mode chat, parent transfer permitido e peers bloqueados nos especialistas. Validar flags efetivos, não só texto de instruções.

Se seleção nativa não atingir author canônico, diagnosticar e usar fallback versionado somente nessa seleção em runtime/runner.py, conforme research R 3. `_find_agent_to_run(session,root_agent)` deve chamar super fora da retomada confiável; na retomada confere sessão e author da árvore, nunca author do cliente/state/LLM. ContextVar isolada por tarefa e resetada por token; duas sessões simultâneas não compartilham contexto. Não substituir processador nativo, não usar AgentTool/sessão filha/memória volátil.

## Atomicidade, contenção e recuperação

- Negócio: BEGIN IMMEDIATE curto, conexão com FK/WAL/busy_timeout; serializar escritas locais apenas durante transação. Reserva ativa protegida por índice único parcial. Conflito específico vira resultado indisponível consumido na mesma transação; savepoint se necessário. Outros erros não podem ser traduzidos falsamente em ocupação.
- Nenhuma transação/lock de escrita atravessa chamada ao modelo. HTTP de ambas aprovações válidas concorrentes termina 200, uma reserva total, recusa sem dados vencedores.
- Decisão+despacho e consumo+efeito são commits distintos recuperáveis. Dois SQLite não oferecem atomicidade conjunta. Decisão registrada deixa de ser pendência e replay HTTP é 409. Após tool completar e eventos persistirem, marcar despacho concluido;200 exige resultado consumido/efeito ou recusa coerente.
- Startup reconcilia somente metadados, sem Runner/eventos novos. GET é leitura pura. Nova POST mensagens pode recuperar despacho decidido incompleto pelo Runner antes do texto. Se o ADK já terminou invocation, conferir eventos/resultado antes de encerrar job. Se já consumido, tool retorna resultado armazenado sem novo efeito. Após 200 nada retoma no restart. Recuperação não apaga nem modifica eventos anteriores.

## Gates de implementação

Provar com API real, ADK==2.2.0 e SQLite persistido: solicitação pelo especialista, resposta nativa correlata, retorno no mesmo especialista e efeito no armazenamento; repetir após restart entre pedido/aprovação. Conferir negação/replay/ID de outra sessão/parâmetros congelados, múltiplas pendências e consentimento textual. Conferir dois contextos simultâneos e indisponibilidade 200. Documentação declara limitação de DatabaseSessionService; gate só passa por evidência real, sem concluir sucesso pela ausência de exceção. Validar reinício/GET com mesma contagem integral de eventos.
