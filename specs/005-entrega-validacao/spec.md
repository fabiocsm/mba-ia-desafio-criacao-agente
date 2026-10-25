# Feature Specification: Entrega reproduzível e validação integral

**Feature Branch**: `dev` (branch atual; diretório da spec independente da branch)

**Created**: 2026-10-23

**Status**: Draft — validada para planejamento

**Input**: User description: "Especificar a preparação, restauração, documentação e validação
final do fork público segundo todos os critérios e passos do avaliador no README."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rodar o projeto a partir de um clone limpo (Priority: P1)

Como avaliador, quero preparar o ambiente com minha própria chave e iniciar a entrega seguindo
somente as instruções do repositório.

**Why this priority**: Nenhuma garantia é avaliável se a entrega não puder ser executada.

**Independent Test**: Em clone limpo, seguir os pré-requisitos e comandos documentados, restaurar
os dados e conferir os dois registros de referência do passo 1.

**Acceptance Scenarios**:

1. **Given** clone limpo e chave própria, **When** seguir as instruções de instalação, subida
   dos serviços necessários, restauração e início, **Then** o serviço responder no endereço
   exigido e listar `RSV-1377` para 101 e `Marina Duarte` para 302.
2. **Given** estado alterado pelos fluxos, **When** executar a restauração documentada,
   **Then** reservas e visitantes corresponderem aos arquivos iniciais, os arquivos de origem
   permanecerem intactos e a política publicada para sessões e pendências ser cumprida.
3. **Given** dados alterados sem restauração solicitada, **When** iniciar novamente o serviço,
   **Then** as alterações permanecerem e nenhuma carga inicial destrutiva ser executada.

---

### User Story 2 - Auditar todas as garantias no uso real (Priority: P1)

Como avaliador, quero percorrer o fluxo completo e verificar efeitos e histórico, inclusive
reinício e concorrência, para decidir se o desafio está concluído.

**Why this priority**: Passar em verificações isoladas não demonstra as garantias combinadas.

**Independent Test**: Executar os 15 passos, na ordem, em ambiente limpo, registrar resultados
observáveis e confrontá-los com as specs de comportamento.

**Acceptance Scenarios**:

1. **Given** as specs 001–004 entregues, **When** executar os 15 passos do avaliador,
   **Then** todos os resultados exigidos serem comprovados e qualquer divergência manter
   a entrega declarada incompleta.
2. **Given** aprovação de reserva ou visitante, **When** a resposta indicar conclusão,
   **Then** a consulta direta comprovar o efeito; receber resposta normal sem executar
   a ação NÃO conta como aprovação bem-sucedida.
3. **Given** confirmação pendente em sessão persistida, **When** reiniciar e responder,
   **Then** a ação funcionar no serviço da entrega e não apenas no ambiente de demonstração.

---

### User Story 3 - Entender arquitetura e localizar as regras no código (Priority: P2)

Como revisor, quero uma entrega pública com instruções e referências reais para cada garantia.

**Why this priority**: A avaliação exige demonstrar que as regras estão no código e não no prompt.

**Independent Test**: Ler as três seções obrigatórias do manual e seguir cada referência no fork.

**Acceptance Scenarios**:

1. **Given** a entrega final, **When** ler Arquitetura, **Then** entender cada agente,
   responsabilidade, forma de acionamento e motivo da divisão, incluindo dois especialistas
   no mínimo além do principal.
2. **Given** a seção Garantias, **When** conferir cada uma das cinco referências,
   **Then** encontrar arquivos e trechos existentes e explicação do mecanismo independente
   da decisão do modelo.
3. **Given** o link entregue, **When** abrir o fork público e sua branch principal exigida,
   **Then** encontrar a entrega completa, dados originais, dependências fixadas, exemplo de
   configuração sem valores e nenhum segredo versionado.

### Edge Cases

- Serviço externo necessário sem instrução de subida: instalação incompleta, mesmo que o
  ambiente do autor funcione.
- Restauração pode apagar sessões, conforme permitido pelo enunciado; a política precisa ser
  explícita e não pode deixar pendências antigas aptas a efetivar ações indevidas.
- A arquitetura ou versão usada pode funcionar somente em memória: aprovação precisa ser
  verificada com persistência e após reinício no serviço entregue.
- A contagem de eventos deve ser anotada antes de parar o serviço; reiniciar não pode adicionar
  eventos à sessão por mera leitura ou descartar conteúdo anterior.
- Aceitar frases exatas do exemplo e falhar quando o avaliador reformula não satisfaz os fluxos.
- Referências a arquivos inexistentes ou trechos que não impõem a regra reprovam a documentação.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Um avaliador DEVE conseguir instalar, restaurar e iniciar a entrega de um clone
  limpo com sua própria chave, usando os comandos publicados e o endereço exigido no enunciado.
- **FR-002**: A restauração DEVE voltar reservas e visitantes ao estado inicial sem editar
  os arquivos originais e DEVE documentar seu efeito sobre sessões e pendências.
- **FR-003**: A reinicialização comum DEVE conservar dados e sessões, sem executar restauração.
- **FR-004**: O repositório DEVE manter dependências e configuração de execução reproduzíveis,
  com a versão exata permitida do runtime de agentes e os arquivos obrigatórios do desafio.
- **FR-005**: O exemplo de configuração DEVE listar todas as variáveis necessárias sem valores;
  configuração privada e chaves NÃO DEVEM ser versionadas.
- **FR-006**: O README final DEVE substituir o enunciado e conter Arquitetura, Garantias e Como
  rodar, com todos os conteúdos descritos nos cenários desta spec.
- **FR-007**: Cada garantia DEVE apontar arquivos e trechos existentes que a impõem em código,
  explicando por que mensagens ou decisões do modelo não conseguem contorná-la.
- **FR-008**: A entrega DEVE ser disponibilizada em fork público do repositório base, com tudo
  na branch `main` e seu link fornecido como entregável.
- **FR-009**: Todos os 15 passos do fluxo original DEVEM ser validados integralmente; uma falha
  em qualquer verificação DEVE impedir a declaração de entrega completa.
- **FR-010**: A validação DEVE conferir dados e eventos completos, não apenas a resposta textual,
  e DEVE preservar os critérios específicos de sigilo nas respostas dos passos 3, 4 e 10.
- **FR-011**: Aprovações DEVEM ser verificadas com sessões persistidas e após reinício,
  confirmando execução efetiva na operação que solicitou o consentimento.
- **FR-012**: A inspeção final DEVE comprovar cada restrição técnica e de arquitetura do README,
  além do contrato integral consolidado no índice das specs.
- **FR-013**: A validação DEVE ser reproduzível e registrar resultado por passo; pode ser manual,
  sem criar obrigação de suíte automatizada, evals, deploy ou interface visual.

### Key Entities *(include if feature involves data)*

- **Estado inicial**: Apartamentos, áreas, reservas, visitantes e regulamento originais imutáveis.
- **Procedimento de execução**: Pré-requisitos, configuração e comandos suficientes ao avaliador.
- **Evidência de validação**: Passo, ação realizada, resultado esperado e resultado observado.
- **Referência de garantia**: Correspondência entre regra, trecho real e justificativa do bloqueio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um clone limpo reproduz os registros de referência seguindo 100% das instruções
  publicadas, sem etapas privadas ou ajustes não documentados.
- **SC-002**: A entrega satisfaz os 15 de 15 passos de avaliação, com zero violações das cinco
  garantias nos resultados observáveis.
- **SC-003**: As cinco garantias têm referências verificáveis e as três seções obrigatórias do
  manual permitem localizar responsáveis, mecanismos e comandos sem conhecimento prévio do autor.
- **SC-004**: Há zero alterações nos arquivos iniciais e zero chaves ou configurações privadas
  versionadas no repositório entregue.
- **SC-005**: Uma restauração reproduz 100% dos registros iniciais de reservas e visitantes,
  enquanto um reinício comum conserva 100% das alterações e eventos previamente registrados.

## Assumptions

- Depende das specs [001](../001-sessoes-isolamento/spec.md),
  [002](../002-reservas-confirmacoes/spec.md), [003](../003-autorizar-visitantes/spec.md)
  e [004](../004-consultar-regulamento/spec.md). Comandos básicos devem surgir durante a 001
  e ser atualizados com cada entrega; esta spec consolida e valida a experiência final.
- Fontes: Objetivo, Tecnologias obrigatórias e restrições, Fluxo do avaliador, Critérios de
  aceite, Entregável e Dicas finais do README; governança e validações da constituição 1.0.0.
- Restrições obrigatórias de tecnologia e contrato estão em [índice e contrato](../README.md),
  incluindo Python, uv, Google ADK, Gemini, endereço local e arquivos de dependências.
- A política inicial proposta para restauração é descartar sessões e pendências junto com
  a reposição dos dados de negócio, evitando consentimentos antigos sobre estado restaurado.
  O plano pode optar por preservá-las se documentar a decisão e manter as garantias.
- Não há pontuação parcial prevista: qualquer verificação falha deixa a entrega incompleta.
- Publicar o fork e entregar em `main` são requisitos da entrega futura; esta especificação
  não executa publicação, merge, implantação nem alteração dos dados iniciais.
