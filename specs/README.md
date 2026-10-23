# Especificações do assistente do Residencial Aurora

Criadas em 2026-10-23 a partir do [enunciado](../README.md) e da
[constituição 1.0.0](../.specify/memory/constitution.md).

## Divisão e ordem de execução

São **cinco specs**, organizadas por entregas observáveis. Cada uma segue o template ativo e
possui seu próprio checklist de qualidade. Reservas, consentimento de cobrança e concorrência
ficam juntos: separar essas partes deixaria a operação sem uma garantia obrigatória.
Visitantes reaproveitam o mesmo ciclo de consentimento. Regulamento tem fluxo próprio.
A última spec valida o conjunto e a reprodução por alguém sem o ambiente do autor.

| Spec | Entrega | Dependências | Tarefas | Artefatos |
| --- | --- | --- | --- | --- |
| 001 | Sessões persistentes, identidade, consultas e histórico completo | Nenhuma | 30 | [Spec](001-sessoes-isolamento/spec.md) · [Checklist](001-sessoes-isolamento/checklists/requirements.md) · [Plano](001-sessoes-isolamento/plan.md) · [Tarefas](001-sessoes-isolamento/tasks.md) · [Análise](001-sessoes-isolamento/analysis-summary.md) |
| 002 | Reservas, cancelamento, confirmação compartilhada e exclusividade | 001 | 36 | [Spec](002-reservas-confirmacoes/spec.md) · [Checklist](002-reservas-confirmacoes/checklists/requirements.md) · [Plano](002-reservas-confirmacoes/plan.md) · [Tarefas](002-reservas-confirmacoes/tasks.md) · [Análise](002-reservas-confirmacoes/analysis-summary.md) |
| 003 | Autorização de visitantes com confirmação | 001, 002 | 26 | [Spec](003-autorizar-visitantes/spec.md) · [Checklist](003-autorizar-visitantes/checklists/requirements.md) · [Plano](003-autorizar-visitantes/plan.md) · [Tarefas](003-autorizar-visitantes/tasks.md) · [Análise](003-autorizar-visitantes/analysis-summary.md) |
| 004 | Consulta seletiva ao regulamento | 001 | 21 | [Spec](004-consultar-regulamento/spec.md) · [Checklist](004-consultar-regulamento/checklists/requirements.md) · [Plano](004-consultar-regulamento/plan.md) · [Tarefas](004-consultar-regulamento/tasks.md) · [Análise](004-consultar-regulamento/analysis-summary.md) |
| 005 | Execução reproduzível, restauração, README final e validação completa | 001–004 | 29 | [Spec](005-entrega-validacao/spec.md) · [Checklist](005-entrega-validacao/checklists/requirements.md) · [Plano](005-entrega-validacao/plan.md) · [Tarefas](005-entrega-validacao/tasks.md) · [Análise](005-entrega-validacao/analysis-summary.md) |

Ordem sugerida: **001 → 002 → 003 → 004 → 005**. A 004 também pode ser planejada após a 001.
Isso descreve dependências do produto, sem solicitar execução por agentes em paralelo.

Isolamento, persistência, registro de eventos e imposição de regras em código são transversais:
001 estabelece a base; cada spec de operação deve preservá-la. Comandos e documentação devem
acompanhar as entregas desde 001; 005 consolida, audita e valida o conjunto, sem adiar a
persistência ou as garantias até o final.

## Restrições obrigatórias para os planos

Estas são imposições do enunciado, não decisões de implementação tomadas pelas specs:

- Python 3.12 ou superior; gerenciamento por `uv`; `pyproject.toml` e `uv.lock` versionados.
- Google ADK série 2, versão igual ou superior a 2.2.0, com versão exata fixada no projeto.
  Integração da execução personalizada com Runner e App e confirmação de tools no serviço real.
- Modelos Gemini com chave do Google AI Studio. Escolher modelos consultando documentação
  oficial e limites ativos do projeto, considerando algumas dezenas de chamadas na avaliação.
- Um agente principal e pelo menos dois especialistas; explicação de suas responsabilidades,
  formas de acionamento e motivos no README. A distribuição exata será definida no plano.
- Reservas e visitantes lidos e gravados por tools; o apartamento vem da sessão, sem aceitar
  identidade escolhida pelo modelo sem validar. Prompts não são a única barreira de negócio.
- Framework web e armazenamento livres; serviços externos necessários sobem com comando
  documentado. Exclusividade deve ser garantida no instante da gravação, não só na consulta.
- Dados de `dados/` idênticos ao repositório base; mudanças fora dos arquivos originais.
- `.env` fora do Git, nenhuma chave versionada e `.env.example` versionado com nomes sem valores.
- Serviço acessível em `http://localhost:8000`; um comando de subida e outro de restauração,
  com eventuais serviços auxiliares e política de restauração das sessões documentados.
- Fork público de `https://github.com/devfullcycle/mba-ia-desafio-criacao-agente`, entrega em
  `main`; README final substitui o enunciado com Arquitetura, Garantias e Como rodar.

O plano deve decidir mecanismos internos e verificar confirmação com a topologia, versão,
configuração de retomada e persistência escolhidas. Resposta normal sem efetivação não prova
sucesso. A aprovação precisa funcionar com sessão persistida e após reinício.

## Contrato externo comum

O contrato é parte do requisito de integração com o avaliador e não pode ser redesenhado.
Todas as rotas recebem, quando houver corpo, e devolvem JSON. Em toda rota com `{session_id}`,
sessão inexistente recebe `404`, inclusive mensagens, confirmações e eventos. Datas nas rotas
de verificação têm formato `AAAA-MM-DD`.

| Rota | Entrada | Saída | Responsável |
| --- | --- | --- | --- |
| `POST /sessoes` | `apartamento` string | `201` com `session_id` | 001 |
| `POST /sessoes/{session_id}/mensagens` | `texto` string | `200` com `resposta` e `confirmacoes_pendentes` | 001; capacidades estendidas por 002–004 |
| `POST /sessoes/{session_id}/confirmacoes` | `id` e `confirmado` booleano | `200` no formato de mensagens; `409` para ID não pendente na sessão | 002; acesso de visitante em 003 |
| `GET /sessoes/{session_id}/eventos` | Sem corpo | `200` com lista de todos os eventos completos em ordem | 001; cada operação registra seus eventos |
| `GET /apartamentos/{apartamento}/reservas` | Sem corpo | `200` com lista de objetos com `codigo`, `area`, `data` | 001; efeitos de 002 |
| `GET /apartamentos/{apartamento}/visitantes` | Sem corpo | `200` com lista de objetos com `nome`, `data` | 001; efeitos de 003 |

`resposta` é string, podendo ser vazia ao aguardar confirmação. `confirmacoes_pendentes` lista
**todas** as pendências atuais da sessão, com `id`, `acao` e `detalhes`, ou `[]` se não houver.
Os nomes internos de `detalhes` e o conteúdo de `acao` são livres, mas os detalhes precisam
incluir área/data para reserva paga e nome/data para visitante. Aprovar vale uma vez; negar
não efetiva a ação. ID inexistente, de outra sessão ou já respondido recebe `409` sem efeito.

As rotas de verificação consultam o estado diretamente sem modelo. Sua leitura entre
apartamentos é destinada à avaliação e não autoriza o assistente a revelar dados alheios.
O histórico inclui chamadas de tools; não pode ser filtrado para esconder violações.

## Cobertura dos passos do avaliador

A execução final segue a ordem do enunciado, não a ordem isolada das specs.

| Passo | Resultado obrigatório | Spec responsável |
| --- | --- | --- |
| 1 | Clone limpo, chave própria, instalação, serviços, restauração e subida; 101 tem `RSV-1377`, 302 tem Marina Duarte | 001, 005 |
| 2 | Criar S1 do 101 com `201` e identificador utilizável | 001 |
| 3 | Alegar ser 302 não revela `RSV-4821` ou Marina Duarte nas respostas e eventos | 001 |
| 4 | Cancelamento alheio não altera `RSV-4821` nem a revela em resposta ou eventos de S1 | 002 |
| 5 | Cancelar quadra própria de `2030-03-09` sem pendência e remover `RSV-1377` | 002 |
| 6 | Reservar quadra em `2030-04-06` para 101 sem pendência | 002 |
| 7 | Salão em `2030-04-20` fica pendente com detalhes; negar não grava | 002 |
| 8 | Novo pedido aprovado cria exatamente uma reserva; reenvio recebe `409` sem duplicar | 002 |
| 9 | ID inexistente recebe `409` sem efeito; eventos de sessão inexistente recebem `404` | 001, 002 |
| 10 | Salão ocupado em `2030-03-16` não gera reserva do 101; nenhuma resposta revela `RSV-4821` ou 302 isolado; eventos não revelam `RSV-4821` | 002 |
| 11 | Joana Ribeiro em `2030-04-21` exige confirmação sistêmica apesar da frase de consentimento; só aprovar grava | 003 |
| 12 | Piscina aos domingos fecha às 20h; eventos completos incluem tools anteriores e não incluem capítulos alheios; anotar contagem | 001, 004 |
| 13 | Reiniciar sem restaurar mantém eventos, dados e cancelamentos; nova mensagem em S1 funciona e aumenta eventos; códigos novos não repetem iniciais ou cancelados; 302 mantém reserva | 001, 002, 003 |
| 14 | Duas sessões de 101 e 201 recebem pendência de salão em `2030-05-11`; aprovações simultâneas recebem `200` e criam uma única reserva entre ambas | 002 |
| 15 | Inspecionar versão fixa, dados, segredos, agentes, tools, identidade da sessão, instruções do principal, exclusividade na gravação e referências do README | 001–005 |

A spec 005 verifica novamente os **15 passos completos** como condição final de entrega.
Além deles, 002 e 003 validam negação, ID de outra sessão e aprovação depois de reinício,
conforme as garantias gerais e as dicas do enunciado.

## Rastreabilidade dos critérios de aceite

IDs AC-01 a AC-28 identificam os critérios na ordem em que aparecem no enunciado original.
A responsabilidade inclui os cenários correspondentes da spec e a validação final da 005.

| Critério | Exigência | Requisitos responsáveis |
| --- | --- | --- |
| AC-01 | Instalação e ADK exato permitido | 005 FR-001, FR-004, FR-012; restrições deste índice |
| AC-02 | Subida, restauração, endereço e estado inicial | 001 FR-008; 005 FR-001–FR-003 |
| AC-03 | Dados originais intactos | 001 FR-008; 004 FR-009; 005 FR-002, FR-012 |
| AC-04 | Sem chaves; configuração de exemplo versionada | 005 FR-005, FR-012 |
| AC-05 | Principal e pelo menos dois especialistas | 001 FR-011; 005 FR-006, FR-012 |
| AC-06 | Tools e efeitos nas verificações | 001 FR-003, FR-007; 002 FR-014; 003 FR-008–FR-009; restrições deste índice |
| AC-07 | Reserva paga pendente com área/data sem efeito antecipado | 002 FR-003, FR-006–FR-008 |
| AC-08 | Negação sem gravação | 002 FR-008–FR-009 |
| AC-09 | Aprovação executa uma vez | 002 FR-008 |
| AC-10 | Reenvio respondido recebe 409 sem execução | 002 FR-009, FR-015 |
| AC-11 | ID não pendente recebe 409 sem efeito | 002 FR-009, FR-015 |
| AC-12 | Área gratuita sem pendência | 002 FR-003 |
| AC-13 | Visitante pendente mesmo com alegação de consentimento | 003 FR-001–FR-005 |
| AC-14 | Consulta cruzada sem dados de 302 em resposta ou eventos | 001 FR-002–FR-005, FR-012 |
| AC-15 | Cancelamento alheio impedido sem vazamento | 002 FR-004, FR-014 |
| AC-16 | Cancelamento próprio sem pendência | 002 FR-004 |
| AC-17 | Ocupação não cria reserva nem revela responsável | 002 FR-002, FR-013–FR-014; User Story 3, cenário 2 |
| AC-18 | Identidade das tools obtida ou validada pela sessão | 001 FR-002, FR-004, FR-012; 002 FR-001; 003 FR-001 |
| AC-19 | Mesmos eventos e continuidade após reinício | 001 FR-006 |
| AC-20 | Efeitos persistidos e códigos sem reutilização | 002 FR-005, FR-011; 003 FR-006 |
| AC-21 | Fechamento dominical correto | 004 FR-001, FR-004 |
| AC-22 | Eventos com tools sem capítulos alheios | 001 FR-007; 004 FR-002, FR-005 |
| AC-23 | Principal sem regulamento nas instruções | 004 FR-003 |
| AC-24 | Duas aprovações concorrentes respondem 200 | 002 FR-012, FR-015; contrato deste índice |
| AC-25 | Disputa resulta em uma única reserva | 002 FR-002, FR-012 |
| AC-26 | Exclusividade no instante de gravação | 002 FR-002, FR-013; restrições deste índice |
| AC-27 | Contrato completo | 001 FR-009–FR-010; 002 FR-010, FR-015; 003 FR-007, FR-011; 005 FR-012 |
| AC-28 | Três seções e referências reais no README | 005 FR-006–FR-007 |

## Limites e prontidão

Não se acrescentam interface, autenticação real, pagamento/estorno, deploy, suíte automatizada
ou evals obrigatórios, nem bloqueios novos de antecedência, datas passadas, horários e capacidade.
O apartamento de criação representa o morador autenticado. Duas respostas simultâneas ao mesmo
ID, apartamento inexistente e nova mensagem durante pendência mantêm a liberdade permitida no
enunciado, preservadas as garantias; reenvio sequencial continua obrigatoriamente protegido.
O avaliador pode reformular as mensagens e esclarecer informações para completar os fluxos.

O setup foi concluído em 2026-10-23 por cinco subagentes em sequência: cada um executou
`$speckit-plan` → `$speckit-tasks` → `$speckit-analyze`, aplicou as correções autorizadas em
etapa separada e repetiu a análise. Cada diretório contém plano, pesquisa, modelo de dados,
contratos, guia de validação, tarefas e resumo da análise final. As cinco análises encerraram
sem achados residuais, com **142 tarefas** e cobertura documental dos **83 requisitos FR/SC**.

Os planos definem FastAPI, Google ADK `2.2.0`, dois SQLite locais, identidade canônica
imutável, confirmação compartilhada com consumo transacional e recuperação seletiva do
regulamento. Detalhes e fontes estão nos respectivos planos e pesquisas; as specs continuam
definindo os requisitos, sem substituir as garantias por decisões de arquitetura.

As cinco specs estão prontas para implementação, respeitando suas dependências. Todas as
tarefas permanecem desmarcadas. Checklists e análises atestam **qualidade e coerência dos
artefatos**, não funcionamento da aplicação. Acesso e quotas ativos do Gemini, confirmação
ADK com SQLite e aprovação após reinício, demais fluxos de runtime, os 15 passos completos,
os 28 critérios e publicação do fork em `main` ainda exigem execução e evidências reais.
O README do enunciado permanece preservado; sua substituição é tarefa futura da 005.

O seletor `.specify/feature.json` aponta para **001-sessoes-isolamento**, primeira da sequência.
Para trabalhar em outra spec, indicar explicitamente seu diretório absoluto como
`SPECIFY_FEATURE_DIRECTORY` e usar `SPECIFY_FEATURE_NO_PERSIST=1` para preservar o seletor,
ou atualizar o seletor intencionalmente. Nomes de diretório não criam branches.
