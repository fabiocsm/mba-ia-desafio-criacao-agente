# Modelo de dados: base de sessões e consultas

`dados/` é fonte inicial somente leitura, nunca estado mutável. Os nomes abaixo são internos; a projeção externa consta em contracts/api.md. Constraints C01–C12 são literais para rastrear implementação em tasks.md.

## Banco de negócio: var/aurora.sqlite3

| Entidade | Campos e relações | Regras |
| --- | --- | --- |
| Apartamento | `numero` TEXT PK; `morador` TEXT | C01: “numero é obrigatório e único; morador reproduz o cadastro inicial”. Sem exposição do cadastro completo ao agente |
| Área | `id` TEXT PK; `nome` TEXT; `taxa` decimal | C02: “id é obrigatório e único; nome e taxa reproduzem dados/areas.json; taxa zero significa ausência de cobrança”. Conversão monetária exata em centavos se necessária, sem float como decisão de cobrança |
| SessionIdentity | `session_id` TEXT PK; `apartamento` TEXT FK Apartamento.numero; `created_at` UTC | C03: “session_id é obrigatório e único; apartamento é obrigatório, definido uma vez e imutável”. INSERT permitido pela criação de sessão; não disponibilizar UPDATE da identidade; trigger de bloqueio no banco |
| Reserva inicial/consulta | `codigo` TEXT PK; `apartamento` FK; `area` FK; `data` TEXT; `cancelada` booleano default false | C04: “codigo é obrigatório e único; apartamento e area são obrigatórios e referenciam cadastros; data usa AAAA-MM-DD e é uma data civil válida”. C05: “codigo nunca é reutilizado; cancelamentos preservam o registro”. 001 só importa e consulta; 002 gera novos códigos e cancela |
| Visitante inicial/consulta | `id` interno PK; `apartamento` FK; `nome` TEXT; `data` TEXT | C06: “apartamento, nome e data são obrigatórios; data usa AAAA-MM-DD e é uma data civil válida”. Sem nova regra de unicidade nome/data; não inventar limites de tamanho |
| Metadado inicialização | `chave` PK; `valor` | C07: “carga inicial ocorre em uma transação somente no banco nunca inicializado; reiniciar não restaura dados”. Metadado impede que uma lista legitimamente vazia seja repovoada |

Apartamento inexistente em criação será rejeitado com 422 JSON, escolha local permitida. A consulta administrativa de apartamento inexistente retorna [] com 200. Nenhum bloqueio de datas passadas, horário, capacidade ou antecedência é introduzido.

Reserva ativa é projeção `cancelada=false`. 002 acrescenta índice único parcial `(area,data) WHERE cancelada=false`, gerador durável e pendências consumíveis. O desenho não permite apagar tombstones para reutilizar códigos. Pendências e decisões não são entidades implementadas por 001; seu contrato público já está reservado, sem registros fictícios.

## Banco ADK: var/adk.sqlite3

Usar schema gerenciado pelo DatabaseSessionService da versão fixada, sem atualizar o schema do SDK manualmente.

- **Sessão ADK**: `app_name=aurora`, `user_id=session_id`, `id=session_id`, state e metadados do ADK. Relação lógica 1:1 com SessionIdentity. C08: “a API só devolve 201 após persistir vínculo canônico e sessão ADK; falha parcial não deixa sessão utilizável”. Sem compartilhar user state de um apartamento entre sessões.
- **Evento ADK**: identificador, timestamp, author, invocation_id, branch, conteúdo completo e ações do SDK, incluindo chamadas e respostas de ferramentas. C09: “eventos persistidos são integrais, imutáveis e retornados na ordem de gravação; ler não altera nem cria eventos”. C10: “timestamp de novo evento é estritamente maior que o anterior da sessão, com passo mínimo de 1 ms, inclusive após reinício”. Adapter de append garante ordem com um worker e serialização por sessão, sem journal espelho. Não streaming, sem compactação e sem `temp:*` para informação auditável.
- O state do SDK pode mudar durante execução; C11: “a autorização usa somente SessionIdentity resolvida por tool_context.session.id; state e argumentos do modelo não mudam apartamento”.

## Projeções autorizadas

C12: “consulta própria filtra apartamento antes de materializar resultado; disponibilidade retorna somente livre ou ocupada”. Tools próprias retornam reserva `{codigo,area,data}` e visitante `{nome,data}`, sem apartamento de terceiros, morador, código alheio ou enumeração de cadastros. Disponibilidade usa EXISTS do par área/data ativa, sem selecionar identidade do ocupante. Rotas de verificação podem escolher apartamento porque são exclusivas do avaliador; não são ferramentas.

## Transições e consistência

- Banco novo → esquema → seed transacional → inicializado. Startup de banco inicializado conserva dados.
- Sessão inexistente → criação coordenada em dois bancos → ativa. Falha de criação → compensação do lado criado; nenhum 201 parcial.
- Sessão ativa → entrada pelo Runner → consultas autorizadas → eventos persistidos → resposta. Reinício → recuperar mesma sessão e identidade → novas entradas acrescentam eventos.
- GET/eventos e verificação são somente leitura. Sessões diferentes têm históricos distintos mesmo com o mesmo apartamento.
- Mutação de negócio, confirmação e restauração são extensões posteriores; não simular seus efeitos em 001.
