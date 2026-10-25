# Residencial Aurora Constitution

## Core Principles

O modelo conduz a conversa; o código decide o que é permitido. As cinco garantias abaixo
DEVEM valer independentemente de prompt injection, redação da mensagem ou decisão do modelo.
Prompts NÃO DEVEM ser a única barreira para qualquer regra crítica.

### I. Confirmação sistêmica para cobrança e acesso

- Toda reserva de área com taxa maior que zero e toda autorização de visitante DEVEM ficar
  pendentes, sem efetivar a reserva ou liberar o acesso, até aprovação pela rota de confirmações.
- A pendência DEVE pertencer à sessão e identificar a ação e seus parâmetros: área e data para
  reservas; nome e data para visitantes. Os parâmetros aprovados DEVEM corresponder à ação
  executada; o modelo NÃO DEVE poder substituir os detalhes após a aprovação.
- Somente `POST /sessoes/{session_id}/confirmacoes` pode aprovar ou negar uma pendência.
  Frases como “já confirmei”, instruções do modelo ou mensagens comuns NÃO constituem aprovação.
- Aprovar DEVE executar a ação uma única vez, sujeita às regras de negócio no momento da gravação.
  Negar NÃO DEVE produzir o efeito de negócio. ID inexistente, de outra sessão ou já respondido
  DEVE receber `409`, sem executar ação nem alterar reservas ou visitantes.
- Reserva de área com taxa zero e cancelamento de reserva própria NÃO DEVEM pedir confirmação.
- A API DEVE integrar a confirmação de tools do ADK e retomar a execução pelo Runner no agente
  que a solicitou. Aceitar a resposta HTTP sem executar a ação aprovada NÃO satisfaz a garantia.

Justificativa: consentimento que gera cobrança ou libera entrada precisa ser verificável pelo
sistema, mesmo quando a conversa tenta antecipá-lo ou contorná-lo.

### II. Identidade imutável da sessão e isolamento por apartamento

- O apartamento DEVE ser definido uma única vez em `POST /sessoes` e persistido na sessão,
  representando o morador autenticado. Mensagens posteriores NÃO DEVEM alterar essa identidade.
- Tools de reservas e visitantes DEVEM obter o apartamento da sessão. Qualquer parâmetro de
  apartamento exposto ao modelo DEVE ser validado contra essa identidade antes de acessar dados.
- Leituras, reservas, cancelamentos e autorizações realizados pelo assistente DEVEM se limitar
  ao apartamento da sessão. A propriedade da reserva DEVE ser validada em código no cancelamento.
- Dados de outros apartamentos NÃO DEVEM alcançar respostas, retornos de tools ou eventos da
  conversa. A consulta da agenda de uma área DEVE expor apenas disponibilidade ou ocupação,
  sem código da reserva, apartamento ou identidade de quem a ocupa.
- Reservas e visitantes DEVEM ser lidos e gravados por tools que acessam o armazenamento real;
  memória ou conteúdo inventado pelo modelo NÃO DEVEM ser fonte desses dados.
- As rotas diretas de verificação são a exceção explícita de leitura entre apartamentos exigida
  pelo avaliador. Elas NÃO DEVEM ser usadas pelo agente para contornar o isolamento da sessão.

Justificativa: o vínculo estabelecido na criação da sessão é a fronteira de autorização;
afirmar ser outro morador na conversa não concede acesso aos dados dele.

### III. Persistência integral e códigos de reserva únicos

- Sessões, vínculo com apartamento, histórico completo de eventos, reservas e visitantes DEVEM
  sobreviver ao reinício da API. Cancelamentos DEVEM continuar efetivos depois do reinício.
- A mesma sessão DEVE aceitar novas mensagens após reiniciar, preservando os eventos anteriores,
  seu conteúdo e sua ordem. Sem novas interações, a quantidade de eventos DEVE permanecer igual.
- Pendências e seu estado de resposta DEVEM ser persistidos para permitir aprovação após reinício
  e impedir que uma confirmação já respondida volte a executar uma ação.
- O sistema DEVE gerar os códigos das novas reservas. Um código NÃO DEVE se repetir, inclusive
  entre reservas iniciais, canceladas e criadas após reinício; o histórico necessário para impedir
  reutilização DEVE sobreviver ao cancelamento.
- Os arquivos de `dados/` DEVEM permanecer idênticos aos do repositório base. Alterações do
  assistente DEVEM ser armazenadas fora deles.
- Um comando documentado DEVE restaurar reservas e visitantes ao estado dos arquivos iniciais.
  A decisão de também apagar sessões DEVE ser documentada; iniciar a API NÃO DEVE restaurar
  automaticamente o estado nem descartar dados persistidos.

Justificativa: reiniciar o processo não pode desfazer efeitos, esquecer a conversa ou permitir
reutilização de identificadores e confirmações consumidas.

### IV. Consulta seletiva ao regulamento e rastreabilidade

- Dúvidas sobre regras DEVEM ser respondidas a partir de `dados/regulamento.md`, consultado
  conforme o assunto da pergunta. O agente principal NÃO DEVE receber o regulamento nas instruções.
- Recuperação, retorno de tools e eventos persistidos DEVEM conter somente trechos pertinentes
  à consulta. Nenhum evento da sessão pode incluir trechos de capítulos sobre outros assuntos.
  Carregar o texto integral e ocultá-lo apenas da resposta final NÃO satisfaz a garantia.
- `GET /sessoes/{session_id}/eventos` DEVE devolver todos os eventos gravados na sessão, em ordem,
  com conteúdo completo, incluindo chamadas de tools. A aplicação NÃO DEVE mascarar violações
  removendo conteúdo apenas na rota de eventos.
- O fluxo da piscina aos domingos DEVE retornar o fechamento previsto no regulamento: `20h`
  no estado inicial, conforme o artigo 22, inciso II, sem incorporar capítulos não relacionados.

Justificativa: consulta seletiva mantém a resposta fundamentada e evita que capítulos alheios
contaminem o histórico e aumentem o custo das próximas chamadas ao modelo.

### V. Exclusividade atômica das reservas

- Cada par área/data DEVE admitir no máximo uma reserva ativa em qualquer instante.
- A exclusividade DEVE ser imposta atomicamente pelo armazenamento no momento da gravação,
  por restrição de unicidade, transação ou mecanismo equivalente com a mesma garantia.
  Consulta prévia de disponibilidade, isoladamente, NÃO atende ao requisito.
- Duas sessões podem manter pendências para a mesma área/data. Na aprovação concorrente,
  apenas uma reserva DEVE ser efetivada; a execução perdedora DEVE produzir recusa de negócio
  normal, sem erro de servidor nem exposição dos dados da reserva vencedora.
- No fluxo de disputa do avaliador, as duas aprovações válidas DEVEM responder `200` e os dois
  apartamentos DEVEM somar exatamente uma reserva da área/data disputada.

Justificativa: decisões tomadas antes da gravação podem ficar obsoletas; o armazenamento é
responsável por manter a exclusividade mesmo entre execuções simultâneas.

## Restrições técnicas, contrato e escopo

- A entrega DEVE ser uma API Python `3.12` ou superior, gerenciada por `uv`, com
  `pyproject.toml` e `uv.lock` versionados, acessível em `http://localhost:8000`.
- Google ADK DEVE estar na série `2`, em versão igual ou superior a `2.2.0`, com a versão exata
  fixada no projeto. O runtime DEVE usar Runner e App na integração com a API.
- O assistente DEVE usar modelos Gemini com chave do Google AI Studio e ter um agente principal
  e no mínimo dois especialistas. Responsabilidades, acionamento e razões da divisão DEVEM ser
  documentados. A escolha dos modelos DEVE consultar documentação oficial e limites ativos do
  projeto no AI Studio, considerando as algumas dezenas de chamadas do fluxo de avaliação.
- Framework web e armazenamento são livres. Dependências de serviços externos DEVEM ter comando
  de subida documentado. Nenhuma escolha pode enfraquecer as cinco garantias.
- Chaves de API NÃO DEVEM ser versionadas. `.env` DEVE ficar fora do Git e `.env.example` DEVE
  ser versionado com os nomes das variáveis necessárias, sem valores.
- Reserva com taxa maior que zero gera cobrança; taxa zero não gera. Autorização de visitante
  libera entrada e DEVE registrar nome e data. Pagamento e estorno NÃO fazem parte da entrega.

O contrato abaixo é obrigatório. Todas as rotas DEVEM receber, quando houver corpo, e devolver
JSON. Toda rota com `{session_id}` DEVE responder `404` se a sessão não existir.

| Rota | Entrada e saída obrigatórias |
|------|-----------------------------|
| `POST /sessoes` | Recebe `apartamento`; responde `201` com `session_id`. |
| `POST /sessoes/{session_id}/mensagens` | Recebe `texto`; responde `200` com `resposta` e `confirmacoes_pendentes`. |
| `POST /sessoes/{session_id}/confirmacoes` | Recebe `id` e `confirmado` booleano; responde `200` no formato de mensagens ou `409` para ID não pendente na sessão. |
| `GET /sessoes/{session_id}/eventos` | Responde `200` com a lista completa e ordenada dos eventos persistidos. |
| `GET /apartamentos/{apartamento}/reservas` | Responde `200` com lista de objetos com `codigo`, `area` e `data`. |
| `GET /apartamentos/{apartamento}/visitantes` | Responde `200` com lista de objetos com `nome` e `data`. |

`resposta` é uma string e pode ser vazia enquanto a execução aguarda confirmação.
`confirmacoes_pendentes` DEVE listar todas as pendências atuais da sessão, cada uma com `id`,
`acao` e `detalhes`, ou ser uma lista vazia quando não houver pendências. `acao` e os nomes
internos de `detalhes` são livres, mantendo os detalhes exigidos no princípio I. Datas nas
rotas de verificação DEVEM usar `AAAA-MM-DD`; `area` identifica o `id` em `dados/areas.json`.
As rotas de verificação DEVEM ler o armazenamento diretamente, sem passar pelo modelo.

Interface visual, autenticação real, pagamento, estorno, deploy, testes automatizados e evals
estão fora de escopo. Regras de antecedência, datas passadas, horários de uso e capacidade NÃO
DEVEM ser acrescentadas como bloqueios às operações de reserva do contrato. Isso não impede
responder perguntas sobre horários consultando o regulamento.

O comportamento é livre para apartamento inexistente, respostas simultâneas à mesma confirmação
e nova mensagem durante pendência, desde que as garantias aplicáveis sejam preservadas. Reenvio
sequencial de confirmação respondida continua obrigatoriamente sujeito a `409`. Tom e redação
das respostas são livres, exceto pelas verificações expressas no fluxo do avaliador.

## Fluxo de desenvolvimento e validação

Especificações, planos e tarefas DEVEM mapear as cinco garantias a mecanismos em código e a
evidências observáveis. Antes de declarar a entrega completa, o fluxo de 15 passos do README
vigente nesta adoção DEVE ser executado integralmente; qualquer falha impede o aceite. Validação
manual reproduzível é suficiente; testes automatizados e evals não são entregáveis obrigatórios.

| Passos do avaliador | Evidência necessária para aceite |
|--------------------|---------------------------------|
| 1 | Em clone limpo: copiar `.env.example`, preencher chave própria, executar `uv sync`, subir serviços necessários, restaurar e iniciar API. As rotas listam `RSV-1377` para 101 e Marina Duarte para 302. |
| 2 | Criar S1 para 101 com `201` e `session_id` utilizável. |
| 3–4 | Alegar ser do 302 e pedir dados ou cancelamento não revela `RSV-4821` nem Marina Duarte no fluxo de consulta e não revela `RSV-4821` no de cancelamento, inclusive em eventos; a reserva do 302 permanece. |
| 5–6 | Cancelar `RSV-1377` e reservar quadra em `2030-04-06` para 101 sem qualquer confirmação pendente no fluxo. |
| 7–8 | Salão em `2030-04-20`: pendência com área/data sem gravação antecipada; negar não cria reserva; repetir e aprovar cria exatamente uma; reenviar o ID respondido recebe `409` sem duplicação. |
| 9 | ID inexistente recebe `409` sem alterar reservas; eventos de sessão inexistente recebem `404`. |
| 10 | Em S2 do 101, tentar salão em `2030-03-16` não cria reserva nem revela `RSV-4821` nas respostas ou eventos; respostas também não revelam o número 302 isolado. Aprovar eventual pendência não muda isso. |
| 11 | Pedido de Joana Ribeiro em `2030-04-21`, mesmo com alegação de confirmação textual, gera pendência com nome/data; só a aprovação pela rota grava a visita. |
| 12 | Piscina aos domingos fecha às `20h`; eventos incluem chamadas de tools anteriores e nenhum trecho de capítulo alheio. Registrar a contagem de eventos de S1. |
| 13 | Reiniciar sem restaurar mantém a contagem; nova mensagem em S1 responde `200` e aumenta os eventos. Quadra, salão, cancelamento e Joana persistem; 302 mantém `RSV-4821`; códigos novos são distintos entre si e de `RSV-1377`, `RSV-4821` e `RSV-2950`. |
| 14 | S3 do 101 e S4 do 201 pedem salão em `2030-05-11`; ambas recebem pendência. Aprovações disparadas simultaneamente respondem `200` e produzem exatamente uma reserva entre os apartamentos. |
| 15 | Inspeção comprova ADK fixado, dados originais, ausência de chaves, principal e dois especialistas, acesso por tools, isolamento pela sessão, consulta seletiva, exclusividade na gravação e referências reais no README. |

A validação DEVE incluir aprovação com sessão persistida e aprovação de pendência após reinício,
conferindo o efeito nas rotas diretas. Funcionamento apenas em memória ou no `adk web` NÃO
comprova a integração. Topologia dos agentes, bloqueios de transferência, configuração de
retomada do App, versão do ADK e serviço de sessão DEVEM ser verificados quando afetarem a
retomada. Relatos de suporte ou limitação NÃO substituem a execução no runtime escolhido.

A entrega DEVE disponibilizar o link de um fork público do repositório base
`https://github.com/devfullcycle/mba-ia-desafio-criacao-agente`, com tudo na branch `main`.
O README final na raiz DEVE substituir o enunciado e conter as três seções exigidas:

- **Arquitetura**: cada agente, responsabilidade, acionamento e justificativa da organização.
- **Garantias**: para cada uma das cinco, arquivos e trechos existentes que a implementam e
  explicação de por que o mecanismo independe das decisões do modelo.
- **Como rodar**: pré-requisitos, variáveis do `.env`, comandos para serviços necessários,
  subida da API e restauração dos dados, incluindo a política de restauração das sessões.

## Governance

Esta constituição formaliza o enunciado do README na adoção inicial. Ela rege especificações,
planos, tarefas e revisões; decisões locais NÃO DEVEM dispensar requisitos obrigatórios do
desafio. Substituir o README pelo manual de entrega NÃO revoga as regras aqui registradas.

Toda proposta de emenda DEVE registrar motivação, regras afetadas, impacto no contrato e nas
cinco garantias, validações necessárias e eventual migração. O mantenedor DEVE revisar e aprovar
a emenda antes de sua incorporação. Uma emenda NÃO DEVE declarar a entrega conforme ao desafio
se remover ou enfraquecer uma exigência do enunciado sem mudança expressa desse requisito.

O versionamento DEVE seguir SemVer: MAJOR para remoção ou redefinição incompatível de princípio
ou governança; MINOR para novo princípio, seção ou ampliação material; PATCH para esclarecimento
sem alteração normativa. A data de ratificação original DEVE ser preservada; a data da última
emenda DEVE refletir alterações efetivas, no formato ISO `YYYY-MM-DD`.

Toda revisão de especificação, plano, tarefa ou alteração de código DEVE verificar conformidade
com os princípios aplicáveis. Mudanças em tools, estado, persistência, confirmação, topologia
dos agentes ou contrato DEVEM revalidar os fluxos afetados; o aceite final exige todos os 15
passos, evidências reproduzíveis e referências atualizadas no README. Pendência sem evidência
DEVE permanecer declarada como incompleta.

**Version**: 1.0.0 | **Ratified**: 2026-10-23 | **Last Amended**: 2026-10-23
