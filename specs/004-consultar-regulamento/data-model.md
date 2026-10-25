# Modelo de dados: consulta seletiva

Nenhuma tabela de negócio nova. Sessões/identidade, reservas, visitantes, pendências e eventos mantêm os modelos001–003. Fonte normativa única: `dados/regulamento.md`, aberta somente para leitura; índice derivado e reconstruível, fora de prompts/eventos.

## Entidades internas

| Entidade/campo | Tipo e restrição literal | Relações/uso |
| --- | --- | --- |
| Regulamento.path | `path` é fixo em `dados/regulamento.md`, somente leitura | Não aceitar caminho LLM/HTTP; arquivo original nunca editado |
| Trecho.id | `id` é referência estrutural única de capítulo/artigo/subunidade existente | Catálogo aponta para unidades; nunca inventar artigo |
| Trecho.texto | `texto` preserva literalmente apenas a unidade selecionada da fonte | Materializado no retorno só após autorização |
| ConsultaScope.session_id | `session_id` vem da identidade canônica e é obrigatório | Conferir ToolContext/session da001 |
| ConsultaScope.execution_nonce | `execution_nonce` é aleatório, próprio da execução HTTP e obrigatório, distinto do invocation_id ADK | Criado no serviço antes do Runner, nunca argumento LLM/state; não fornecido como invocation_id de retomada |
| ConsultaScope.unidades | `unidades` contém somente IDs autorizados pelo texto original; pode ser vazio | Conjunto fechado; várias chamadas não o ampliam |
| Resultado.status | `status` pertence a `ok`, `esclarecer`, `sem_base` | Ausência de escopo válido nunca permite texto |
| Resultado.trechos | `trechos` é vazio para `esclarecer` e `sem_base` | Para ok: referências e textos mínimos autorizados |

Catálogo contém aliases normalizados por assunto, padrões de intenção e referências estruturais. Não contém respostas/hora duplicadas; valida referências contra índice ao construir. Comandos técnicos topics/path/tool não autorizam temas; se inseparáveis da pergunta, esclarecer sem trecho. Reconhecimento incerto → esclarecer, assunto claro sem unidade suficiente → sem_base. Pedido integral/genérico nunca cria autorização ilimitada; remissão a outro capítulo não o expande. Catálogo pode cobrir vários temas numa pergunta específica, sem carregar todos os artigos do capítulo.

## Transições e persistência

Mensagem original → scope fechado → consulta tool → resultado seletivo/fallback → resposta e eventos ADK integrais. Scope existe somente na execução e é removido em finally; restart ou confirmação sem pergunta não reutiliza autorização. Índice reconstrói no startup sem gravar eventos ou alterar estado de negócio. Chamadas/resultados/referências ficam nos eventos canônicos, conteúdo completo e ordem preservados.

Não persistir cópia do regulamento no state/histórico. A identidade não é editada; consultas não criam/decidem pendências. Nova consulta pode autorizar tema novo, sem apagar os trechos legitimamente consultados anteriormente. Histórico da sessão do avaliador só contém conteúdos pertinentes aos pedidos efetivamente feitos.
