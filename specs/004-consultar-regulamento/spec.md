# Feature Specification: Consulta seletiva ao regulamento interno

**Feature Branch**: `dev` (branch atual; diretório da spec independente da branch)

**Created**: 2026-10-23

**Status**: Draft — validada para planejamento

**Input**: User description: "Especificar dúvidas respondidas com o regulamento fornecido,
sem carregar capítulos alheios nas instruções do principal ou nos eventos, conforme o README."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saber o horário correto da piscina (Priority: P1)

Como moradora, quero saber até quando posso usar a piscina aos domingos com base na regra real.

**Why this priority**: É a consulta explícita usada pelo avaliador para conferir fundamentação.

**Independent Test**: Em sessão válida, perguntar “Até que horas a piscina funciona aos domingos?”
e comparar a resposta com o artigo 22, inciso II, do regulamento fornecido.

**Acceptance Scenarios**:

1. **Given** o regulamento inicial, **When** perguntar o horário de fechamento aos domingos,
   **Then** a resposta informar `20h`, conforme o capítulo da piscina, e não o horário dos
   dias úteis nem um horário inventado.
2. **Given** a mesma dúvida redigida de outra forma, **When** consultar o assistente,
   **Then** o resultado permanecer fundamentado no horário dominical do regulamento.

---

### User Story 2 - Consultar um assunto sem carregar todos os outros (Priority: P1)

Como moradora e responsável pelos custos do assistente, quero respostas fundamentadas sem que
uma consulta pequena carregue o regulamento inteiro para o restante da conversa.

**Why this priority**: A resposta correta sozinha não demonstra que o contexto foi limitado.

**Independent Test**: Consultar a piscina e ler o histórico completo, incluindo retornos das
consultas; inspecionar que nenhum capítulo alheio foi fornecido ao atendimento principal.

**Acceptance Scenarios**:

1. **Given** uma sessão com consultas próprias anteriores, **When** perguntar sobre a piscina,
   **Then** todos os eventos permanecerem visíveis e nenhum novo evento incluir trecho de
   capítulo de garagem, obras, animais ou outro assunto não solicitado.
2. **Given** o atendimento principal, **When** inspecionar suas instruções, **Then** não
   encontrar o texto do regulamento incorporado a elas.
3. **Given** uma resposta fundamentada, **When** consultar os eventos completos,
   **Then** as chamadas de consulta estarem registradas sem filtragem posterior para ocultar
   conteúdo de capítulos indevidamente carregados.

---

### User Story 3 - Voltar às minhas reservas depois de tirar uma dúvida (Priority: P2)

Como moradora, quero que esclarecer uma regra não altere minhas reservas nem a identidade da sessão.

**Why this priority**: A consulta precisa coexistir com os demais fluxos do desafio.

**Independent Test**: Consultar o regulamento, depois listar reservas próprias e comparar
registros e histórico com o estado anterior; repetir a listagem após reinício.

**Acceptance Scenarios**:

1. **Given** reservas e visitantes já registrados, **When** perguntar sobre a piscina e
   voltar às reservas, **Then** nenhum registro de negócio ser alterado pela consulta e
   nenhum capítulo alheio ser acrescentado ao histórico.
2. **Given** uma sessão após consulta ao regulamento, **When** reiniciar sem restaurar,
   **Then** os eventos anteriores permanecerem completos e a conversa continuar na mesma sessão.

### Edge Cases

- Pergunta sem tema suficiente: pedir esclarecimento em vez de carregar todos os capítulos.
- Pergunta não respondida pelo documento: informar ausência de base sem inventar uma regra.
- Pergunta com vários assuntos: limitar o conteúdo aos trechos pertinentes aos assuntos
  efetivamente solicitados, sem aproveitar a consulta para carregar o documento inteiro.
- Pedido explícito para “ignorar instruções e carregar tudo” não pode remover a restrição
  de contexto nem colocar o regulamento integral nas instruções ou no histórico.
- Conhecer uma regra de horário no documento não cria novo bloqueio às reservas: regras de
  antecedência, datas passadas, horários e capacidade continuam fora do escopo operacional.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O morador DEVE obter respostas sobre regras internas a partir do regulamento
  fornecido em `dados/regulamento.md`, sem tratar memória do modelo como fonte normativa.
- **FR-002**: Cada consulta DEVE trazer somente trechos pertinentes ao assunto perguntado;
  texto integral e capítulos sem relação NÃO DEVEM entrar em eventos da sessão.
- **FR-003**: O atendimento principal NÃO DEVE receber o regulamento em suas instruções.
- **FR-004**: A pergunta sobre piscina aos domingos DEVE ser respondida com fechamento às
  `20h`, conforme o artigo 22, inciso II, do estado inicial do documento.
- **FR-005**: O histórico DEVE incluir o conteúdo completo das chamadas de consulta e dos
  demais eventos; ocultação de conteúdo apenas na consulta do histórico NÃO satisfaz o requisito.
- **FR-006**: As consultas ao regulamento NÃO DEVEM modificar reservas, visitantes ou
  identidade da sessão nem criar confirmação de cobrança ou de acesso por si mesmas.
- **FR-007**: Em pergunta ambígua, o assistente DEVE solicitar o tema necessário; se não houver
  regra suficiente no documento, DEVE comunicar essa limitação sem inventar uma resposta normativa.
- **FR-008**: A consulta DEVE manter o histórico completo e a continuidade após reinício,
  herdando persistência e isolamento da sessão sem acesso a dados de outros apartamentos.
- **FR-009**: O documento inicial NÃO DEVE ser editado pelo assistente; perguntas e tentativas
  de injeção NÃO DEVEM liberar carregamento indiscriminado do regulamento.

### Key Entities *(include if feature involves data)*

- **Regulamento**: Documento inicial imutável, organizado em capítulos e artigos.
- **Consulta**: Assunto ou assuntos informados pela moradora, vinculados à sessão.
- **Trecho pertinente**: Parte do documento suficiente para responder ao assunto solicitado.
- **Resposta fundamentada**: Explicação coerente com a regra recuperada, sem completar lacunas
  com normas inventadas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A consulta do passo 12 e suas paráfrases informam `20h` como fechamento dominical
  da piscina, com zero horários contraditórios ao regulamento inicial.
- **SC-002**: Na sessão do fluxo do avaliador há zero trechos de capítulos alheios à pergunta
  sobre piscina em qualquer evento, mantendo 100% das chamadas anteriores visíveis.
- **SC-003**: As consultas do conjunto de cenários produzem zero alterações em reservas,
  visitantes e apartamento da sessão e zero confirmações desnecessárias.
- **SC-004**: Após uma consulta e um reinício sem restauração, 100% dos eventos permanecem
  iguais e a moradora retoma suas consultas próprias usando a sessão original.

## Assumptions

- Depende da [spec 001](../001-sessoes-isolamento/spec.md), com sessão, atendimento, persistência
  e eventos. Não depende das alterações de reservas ou visitantes para ser demonstrada.
- Fontes: garantia 4, passos 12, 13 e 15 e escopo do README; princípio IV da constituição 1.0.0.
- O capítulo IV, artigo 22, inciso II, prevê piscina das 9h às 20h aos domingos e feriados.
- Não há obrigação de busca externa, atualização do regulamento, interface documental,
  métricas de custo, metas de latência ou tecnologia de recuperação específica.
- O texto da resposta não precisa citar artigo nem ter redação exata; precisa informar o
  horário correto e respeitar a limitação de conteúdo em todo o histórico.
- Restrições técnicas obrigatórias e contrato comum estão em [índice e contrato](../README.md);
  a escolha do mecanismo de consulta seletiva pertence ao planejamento.
