# Modelo de dados: autorização de visitantes

Extensão das entidades 001 e confirmação 002, sem tabela paralela de consentimento. `dados/visitantes.json` permanece fonte inicial somente leitura. Banco mutável: `var/aurora.sqlite3`; histórico canônico: `var/adk.sqlite3`.

## Entidades e constraints literais

| Entidade | Campos e relações | Constraints |
| --- | --- | --- |
| Visitante/Autorizacao | `id` PK interno herdado; `apartamento` FK cadastro; `nome` TEXT; `data` TEXT; `proposta_id` nullable UNIQUE FK PropostaConfirmacao.id | C301: “id é obrigatório, único e gerado pelo sistema; apartamento, nome e data são obrigatórios; nome não pode ser vazio; data usa AAAA-MM-DD e é uma data civil válida”. C302: “proposta_id é nulo para dados iniciais e obrigatório para novas autorizações; proposta_id não nulo é único e referencia proposta da mesma sessão e ação autorizar_visitante”. Não criar UNIQUE nome/data |
| PropostaConfirmacao (herdada) | Todos os campos 002, sessão canônica e metadados ADK; `acao=autorizar_visitante`; `parametros_json` com nome/data | C303: “nome e data são obrigatórios no snapshot de autorizar_visitante e imutáveis; apartamento executado vem da SessionIdentity imutável vinculada à proposta”. C207–C209 da 002 continuam válidas, incluindo correlação distinta original/nativa e fase preparando/pendente |
| Decisao e Despacho (herdados) | FK proposta, booleano estrito, consumo/resultado e estado de recuperação | C304: “nova autorização só é inserida com decisão canônica confirmada; consumo da decisão, resultado e inserção usam a mesma conexão e transação; negação não insere visitante”. C210–C211 da 002 preservados, sem novos estados |

C302 é validada pelo executor canônico no mesmo escopo do consumo, além da FK/UNIQUE; nunca permitir INSERT de nova autorização por uma rota/tool alternativa. Nome é preservado conforme snapshot validado, sem nova exigência de documento ou tamanho máximo. Nome/data ausentes não originam proposta executável. Não impor bloqueios de datas passadas, horários ou capacidade.

## Relações e transições

- SessionIdentity 1:N propostas; proposta de autorização 0:1 decisão; decisão 1:1 despacho; proposta aprovada consumida 1:1 nova autorização. Propostas distintas podem gerar linhas com mesmo apartamento/nome/data. Visitante inicial tem proposta_id nulo.
- Proposta preparando → evento nativo persistido/correlação durável → pendente pública, sem visita. Responder somente após publicação; inicialização não converte proposta sem evento em autorização.
- Pendente → rota CAS decide e cria despacho; não é mais listada. Negada → Runner/tool → consumo+resultado sem visita. Aprovada → Runner/tool → consumo+resultado+visitante atômicos.
- Decisão consumida → reentrada técnica recupera resultado, sem segunda visita; confirmação HTTP repetida →409 sem Runner/efeito. Não consumir outras propostas de visita ou reserva.
- Queda após decisão ou efeito → despacho recuperar; startup/GET não executam Runner nem criam eventos. Nova POST mensagens recupera pelo mesmo caminho nativo antes do texto. Depois de 200 despacho concluído; restart mantém a mesma contagem de eventos até nova interação.

## Projeções e restauração

Consulta própria filtra `apartamento` canônico antes de materializar e devolve somente `{nome,data}`. GET administrativo existente consulta estado real por apartamento e não é tool. Pendências usam `{id,acao,detalhes:{nome,data}}`, sem campos internos ou dados alheios. Eventos mantêm chamadas/resultados completos da própria sessão, sem filtragem posterior.

A política 001/002 para restauração explícita da 005 invalida sessões/pendências; deve remover autorizações/propostas em ordem compatível com FK e reimportar visitantes iniciais com proposta_id nulo. Ledger/contador de reservas continuam preservados. Startup não executa essa operação. Não criar comando concorrente de restauração nesta spec.
