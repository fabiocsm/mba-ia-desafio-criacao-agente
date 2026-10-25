# Contrato interno de tools e runtime

Este contrato limita acesso **antes** dos dados entrarem em retorno de ferramenta/eventos. Nenhuma filtragem posterior da rota de eventos é uma barreira de autorização.

## Identidade e consulta

`resolve_identity(tool_context)` usa a propriedade pública `tool_context.session.id`, busca `session_identity` canônica e retorna identidade confiável apenas internamente. Sessão ausente ou correlação inválida falha sem consultar dados de moradores. Não aceitar apartamento, session_id ou author como argumentos escolhidos pelo LLM; não usar state ADK como autoridade.

| Tool/arquivo | Argumentos expostos ao modelo | Resultado | Agente |
| --- | --- | --- | --- |
| listar_minhas_reservas, tools/reservas.py | nenhum | array `{codigo,area,data}` filtrado por apartamento canônico e reservas ativas | reservas |
| consultar_disponibilidade, tools/reservas.py | area ID, data civil AAAA-MM-DD | objeto `{"disponibilidade":"livre"}` ou `{"disponibilidade":"ocupada"}` | reservas |
| listar_meus_visitantes, tools/visitantes.py | nenhum | array `{nome,data}` filtrado por apartamento canônico | visitantes |

`ToolContext` é injetado pelo SDK, não faz parte do schema de argumentos do modelo. Disponibilidade consulta somente EXISTS, sem materializar codigo/apartamento/morador. Área inexistente ou data inválida produz erro de entrada genérico sem dados alheios; não aplicar regras de data passada/horário/capacidade. As funções de verificação por apartamento não são registradas no catálogo de tools.

## Agentes

- **aurora_principal**: interlocutor, esclarece intenção e encaminha aos especialistas; não lê dados brutos nem recebe regulamento completo.
- **reservas**: consultas de reservas próprias e disponibilidade, tools acima. Em 002 também recebe criação/cancelamento/confirmacão mediante código de autorização. Separação concentra agenda e regras de exclusividade.
- **visitantes**: consulta própria de visitantes, tool acima. Em 003 recebe autorização de entrada confirmada. Separação evita misturar cobrança de reserva com acesso de pessoas.

Usar sub_agents da mesma árvore, não AgentTool com sessão filha. `LlmAgent(mode="chat")`; especialistas `disallow_transfer_to_parent=False`, `disallow_transfer_to_peers=True`; App `ResumabilityConfig(is_resumable=True)`. Principal permite transferências aos filhos. Uma mensagem que combina reservas e visitantes deve ser atendida em encaminhamentos sucessivos/retorno ao principal sem trocar identidade. Nenhuma descrição de tool anuncia operações futuras como já disponíveis.

## Execução e persistência

`runtime/service.py` resolve sessão canônica e sessão ADK, serializa interações da mesma sessão e executa Runner com `user_id=session_id`, `session_id=session_id`. O cliente não escolhe esses campos. `runtime/sessions.py` adapta DatabaseSessionService em disco:

1. Antes de persistir e publicar qualquer novo evento, atribui timestamp maior que o máximo da mesma sessão, passo mínimo 1ms, sob lock próprio curto; restaura referência do maior timestamp persistido após restart. Não reusar lock interno do SDK nem manter lock SQLite durante chamada Gemini.
2. Chama a persistência nativa, preservando JSON integral de Event e actions; não manter journal duplicado. Usar RunConfig não streaming e sem compactação. Não usar deltas `temp:*` para informação auditável, pois SDK os remove.
3. Uvicorn roda com um worker. A serialização é por sessão; interações de sessões distintas continuam possíveis em paralelo. A disputa de negócio da 002 depende de restrição atômica do SQLite e não desse lock em memória.
4. Retorno de mensagens coleta texto final de eventos destinados ao usuário; GET/eventos obtém a lista canônica do serviço, inclusive mensagens de usuário que o generator do Runner não entrega. Ler não chama append/Runner nem altera eventos antigos.
5. Startup inicializa esquema/seed só se necessário e recupera sessões/eventos existentes; nunca faz restauração implícita.

## Compatibilidade com confirmação futura

Persistir e verificar agente solicitante/invocation/ID da solicitação ADK na 002; resposta sistêmica gera FunctionResponse nativa e Runner retoma a invocação. Ver o risco documental e o fallback estrito para seleção em [research.md](../research.md#r2--confirmação-decisão-herdada-pela-002-e-limite-da-pesquisa). Não executar mutação diretamente na rota, nem registrar confirmação por mensagem. A 001 valida continuidade de consultas; a 002 precisa provar aprovação com efeitos reais antes/depois de restart, incluindo identidade correta e eventos integrais.
