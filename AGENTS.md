# Orientações para agentes de desenvolvimento

## Objetivo e fontes

Construir o assistente do Residencial Aurora: conversar com moradores, gerenciar reservas,
autorizar visitantes e responder dúvidas sobre o regulamento, expondo somente uma API.
**O modelo conduz a conversa; o código decide o que é permitido.**

Antes de especificar, planejar, implementar ou revisar, consultar:

- [Constituição](.specify/memory/constitution.md): princípios, restrições e governança.
- [README](README.md): enunciado, contrato, critérios de aceite e fluxo do avaliador;
  na entrega final, será substituído pelo manual de execução.
- [Índice das specs](specs/README.md): dependências, contrato consolidado, cobertura dos
  28 critérios de aceite e dos 15 passos do avaliador.
- A spec da funcionalidade e seus artefatos de planejamento e tarefas, quando existentes.

Este arquivo resume as fontes; não dispensa requisitos nem altera a constituição.
Substituir o README pelo manual final não revoga as exigências do desafio.

## Tecnologias e arquitetura obrigatórias

- Usar Python 3.12 ou superior e `uv`. Versionar `pyproject.toml` e `uv.lock`;
  a instalação em clone limpo deve funcionar com `uv sync`.
- Usar Google ADK série 2, versão igual ou superior a 2.2.0, com versão exata fixada.
  Integrar a execução da API com Runner e App e a confirmação de tools do ADK.
- Usar modelos Gemini com chave do Google AI Studio. Ao escolher modelos, consultar a
  documentação oficial e os limites ativos do projeto; considerar algumas dezenas de
  chamadas no fluxo do avaliador, sem assumir disponibilidade ou quotas fixas.
- Implementar um agente principal e no mínimo dois especialistas. Documentar as
  responsabilidades, como cada um é acionado e o motivo da divisão.
- Ler e gravar reservas e visitantes por tools que acessam o estado real. Não usar
  lembranças ou dados inventados pelo modelo como fonte de registros do condomínio.
- Framework web e armazenamento são livres. Serviços externos necessários devem ter
  comando de subida documentado. A API deve responder em `http://localhost:8000`.

## Cinco garantias inegociáveis

### 1. Cobrança ou acesso somente com confirmação sistêmica

- Reserva com taxa maior que zero e autorização de visitante ficam pendentes, sem efeito
  de negócio, até resposta em `POST /sessoes/{session_id}/confirmacoes`.
- A pendência pertence à sessão e apresenta os detalhes que serão executados: área/data
  para reserva e nome/data para visitante. Não substituir os parâmetros após a aprovação.
- Mensagem como “já confirmei” ou instrução do modelo não constitui consentimento.
- Aprovar executa uma única vez, se a ação ainda for permitida. Negar não efetiva a ação.
  ID inexistente, de outra sessão ou já respondido recebe `409`, sem efeitos.
- Reserva de área com taxa zero e cancelamento de reserva própria não pedem confirmação.
- Retomar a execução no agente que solicitou a confirmação. Responder `200` sem executar
  a ação aprovada não demonstra funcionamento. Conferir o efeito no armazenamento real.

### 2. Identidade imutável e isolamento por apartamento

- Definir o apartamento uma única vez na criação da sessão, representando o morador
  autenticado. Nada que ele escrever depois pode alterar esse vínculo.
- As tools obtêm a identidade da sessão. Se aceitarem apartamento como parâmetro,
  validar contra a sessão antes de acessar os dados; nunca confiar na escolha do modelo.
- Permitir leitura e alteração somente dos dados próprios; validar a propriedade ao
  cancelar. Não revelar reservas ou visitantes alheios em respostas, tools ou eventos.
- Na consulta da agenda de uma área, informar apenas livre/ocupada, sem código,
  apartamento ou identidade do responsável pela ocupação.
- As rotas diretas de verificação existem para o avaliador. Não expor sua capacidade
  de leitura entre apartamentos ao assistente como forma de contornar o isolamento.

### 3. Persistência e identificadores únicos

- Persistir sessões, apartamento, eventos completos e ordenados, reservas, cancelamentos,
  visitantes, pendências e decisões já consumidas entre reinícios.
- Reiniciar sem restaurar conserva o mesmo histórico e permite novas mensagens na mesma
  sessão. Ler eventos não pode apagar, alterar ou inventar registros anteriores.
- Gerar os códigos das reservas no sistema, sem repetir códigos iniciais, cancelados
  ou criados antes do reinício. Cancelar não permite reutilizar o identificador.
- Manter `dados/` idêntico ao repositório base. Armazenar mudanças fora dos arquivos iniciais.
- Disponibilizar comando explícito para restaurar reservas e visitantes. Documentar se
  também apaga sessões e como trata pendências. Subir a API não deve restaurar dados.

### 4. Consulta seletiva ao regulamento

- Responder dúvidas a partir de `dados/regulamento.md`, recuperando somente conteúdo
  pertinente ao assunto perguntado. Não colocar o regulamento nas instruções do principal.
- Nenhum evento pode incluir trechos de capítulos alheios à consulta. Carregar tudo e
  ocultar apenas na resposta final ou na rota de eventos não atende à garantia.
- Preservar eventos completos, incluindo chamadas de tools e seus resultados; não filtrar
  o histórico para esconder violações. No estado inicial, a piscina fecha às 20h aos domingos.

### 5. Exclusividade no instante da gravação

- Garantir no máximo uma reserva ativa por área/data em qualquer instante, com mecanismo
  atômico do armazenamento. Conferir disponibilidade antes de gravar, sozinho, não basta.
- Duas sessões podem ter pendências para a mesma data. Na aprovação simultânea, uma vence
  e a outra recebe recusa normal, sem erro de servidor ou dados da reserva vencedora.
- No fluxo concorrente do avaliador, ambas as aprovações válidas respondem `200` e há
  exatamente uma reserva somando os dois apartamentos.

## Contrato externo obrigatório

Não alterar caminhos, campos, formatos ou resultados definidos no enunciado. Todas as rotas
recebem, quando houver corpo, e devolvem JSON. Sessão inexistente recebe `404` em qualquer
rota com `{session_id}`. Datas nas verificações usam `AAAA-MM-DD`.

| Rota | Entrada e resultado |
| --- | --- |
| `POST /sessoes` | `apartamento`; `201` com `session_id`. |
| `POST /sessoes/{session_id}/mensagens` | `texto`; `200` com `resposta` e `confirmacoes_pendentes`. |
| `POST /sessoes/{session_id}/confirmacoes` | `id`, `confirmado` booleano; `200` no formato de mensagens ou `409` se o ID não estiver pendente nesta sessão. |
| `GET /sessoes/{session_id}/eventos` | `200` com todos os eventos completos, em ordem. |
| `GET /apartamentos/{apartamento}/reservas` | `200` com lista de objetos com `codigo`, `area`, `data`. |
| `GET /apartamentos/{apartamento}/visitantes` | `200` com lista de objetos com `nome`, `data`. |

`resposta` é string e pode ser vazia enquanto aguarda confirmação. `confirmacoes_pendentes`
lista todas as pendências atuais, com `id`, `acao` e `detalhes`, ou `[]` quando não houver.
Os nomes internos de `detalhes` são livres, mantendo as informações exigidas da ação.
As rotas de verificação leem o estado diretamente, sem passar pelo modelo.

## Desenvolvimento e validação

- Seguir as dependências do [índice](specs/README.md): 001 sessões; 002 reservas e
  confirmações; 003 visitantes; 004 regulamento; 005 entrega e validação integral.
  Persistência e isolamento devem acompanhar cada operação desde sua implementação.
- Confirmar o diretório da spec antes de executar comandos Spec Kit. O seletor local
  `.specify/feature.json` e `SPECIFY_FEATURE_DIRECTORY` são independentes do nome da branch.
- Mapear requisitos a mecanismos em código e evidências observáveis. Um checklist de
  qualidade da spec aprovado não significa funcionalidade implementada ou validada.
- Ao alterar tools, identidade, armazenamento, confirmação, topologia dos agentes ou
  contrato, revalidar os fluxos afetados. Antes do aceite final, executar os 15 passos
  completos do avaliador; qualquer falha mantém a entrega incompleta.
- Validar aprovação com sessão persistida e após reinício da API, não apenas em memória
  ou no `adk web`. Conferir Runner, agente solicitante, topologia, bloqueios de transferência,
  retomada do App, serviço de sessão e versão do ADK quando afetarem esse fluxo.
- Verificar efeitos nas rotas diretas e nos eventos completos. Aceitar variações de redação
  das mensagens e esclarecimentos necessários, sem depender de frases exatas do exemplo.
- Conferir especialmente as tentativas de acessar/cancelar dados do 302 pela sessão do 101,
  negação, reenvio, ID inválido, área gratuita, visitante, reinício e aprovações concorrentes.
  Preservar os critérios exatos de sigilo dos passos 3, 4 e 10, inclusive a proibição de
  revelar o número 302 isolado nas respostas do passo 10.
- Validação manual reproduzível é suficiente. Testes automatizados e evals não são
  entregáveis obrigatórios. Relatar verificações realizadas e pendências com precisão.

## Segredos, escopo e entrega

- Nunca versionar chaves de API ou `.env`. Versionar `.env.example` somente com nomes das
  variáveis necessárias, sem valores. O avaliador usa a própria chave.
- Não acrescentar interface visual, autenticação real, pagamento, estorno ou deploy ao
  escopo obrigatório, nem bloqueios de antecedência, datas passadas, horários ou capacidade
  às reservas. Isso não impede responder dúvidas sobre horários do regulamento.
- O comportamento é livre para apartamento inexistente, duas respostas simultâneas à
  mesma confirmação e nova mensagem durante pendência, preservadas as garantias. Reenvio
  sequencial de confirmação respondida continua obrigatoriamente sujeito a `409`.
- A entrega final é um fork público do repositório base, com tudo em `main` e link fornecido.
  Substituir o enunciado no README por **Arquitetura**, **Garantias** e **Como rodar**.
- Documentar cada agente e sua justificativa; para cada garantia, apontar arquivos e trechos
  reais e explicar a imposição independente do modelo. Publicar pré-requisitos, variáveis,
  comandos de serviços externos, subida e restauração, com política de sessões.
- Alterações da constituição seguem sua governança e SemVer: MAJOR para mudança incompatível,
  MINOR para ampliação material e PATCH para esclarecimento sem mudança normativa.
  Não enfraquecer uma exigência do desafio nem tratar uma regra como opcional por conveniência.
