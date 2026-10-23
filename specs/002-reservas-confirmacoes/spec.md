# Feature Specification: Reservas com confirmação e exclusividade

**Feature Branch**: `dev` (branch atual; diretório da spec independente da branch)

**Created**: 2026-10-23

**Status**: Draft — validada para planejamento

**Input**: User description: "Especificar reservas, cancelamentos, confirmação sistêmica,
identificadores únicos e disputa simultânea de acordo com o README."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reservar área gratuita e cancelar minhas reservas (Priority: P1)

Como moradora, quero reservar a quadra e cancelar reservas próprias sem confirmar ações que
não geram cobrança nem liberam acesso.

**Why this priority**: Entrega operações completas com efeito observável e autorização própria.

**Independent Test**: Em sessão do 101 e estado inicial, cancelar a quadra de `2030-03-09`,
reservar `2030-04-06` e comparar as listagens antes e depois, sem aprovar pendências.

**Acceptance Scenarios**:

1. **Given** a reserva própria `RSV-1377`, **When** pedir seu cancelamento, **Then** ela deixa
   de estar ativa e nenhuma resposta desse fluxo contém confirmação pendente.
2. **Given** a quadra livre em `2030-04-06`, **When** pedir a reserva, **Then** ela aparece
   para 101 com código novo, sem confirmação pendente em qualquer resposta do fluxo.
3. **Given** a sessão do 101, **When** pedir cancelamento do salão em `2030-03-16`, **Then**
   `RSV-4821` permanece para 302 e não aparece na resposta nem nos eventos da sessão do 101.

---

### User Story 2 - Decidir uma cobrança por confirmação do sistema (Priority: P1)

Como moradora, quero conhecer os detalhes da reserva paga antes de aceitar sua execução.

**Why this priority**: Cobrança não pode decorrer de uma interpretação de consentimento no chat.

**Independent Test**: Pedir salão em `2030-04-20`, negar a primeira pendência, repetir o pedido,
aprovar a segunda e reenviar a mesma aprovação; conferir os efeitos a cada etapa.

**Acceptance Scenarios**:

1. **Given** salão livre em `2030-04-20`, **When** pedir a reserva, mesmo dizendo “confirmei”,
   **Then** receber pendência com área e data, sem reserva criada para o 101.
2. **Given** essa pendência, **When** negá-la pelo canal de confirmação, **Then** nenhuma
   reserva é criada e a pendência deixa de ser respondível.
3. **Given** novo pedido para a mesma área/data, **When** aprovar a nova pendência pelo canal
   de confirmação, **Then** existir exatamente uma reserva para 101 e a pendência ser consumida.
4. **Given** uma confirmação já aprovada ou negada, **When** reenviar sequencialmente sua
   resposta, **Then** receber conflito, sem executar a ação novamente.
5. **Given** ID inexistente ou pendente em outra sessão, **When** responder em S1, **Then**
   receber conflito, sem alterar reservas nem consumir a pendência de outra sessão.
6. **Given** uma pendência persistida, **When** reiniciar sem restaurar e aprová-la na mesma
   sessão, **Then** a reserva ser efetivada uma única vez; reiniciar e reenviar retorna conflito.

---

### User Story 3 - Disputar uma data sem duplicidade nem vazamento (Priority: P1)

Como moradora, quero uma resposta normal quando outra pessoa obtém a data antes de mim.

**Why this priority**: A confirmação não garante que a área continuará livre até a execução.

**Independent Test**: Criar sessões para 101 e 201, obter duas pendências do salão em
`2030-05-11` e aprová-las simultaneamente, comparando as duas listagens.

**Acceptance Scenarios**:

1. **Given** duas pendências para a mesma área/data livre, **When** as aprovações ocorrem ao
   mesmo tempo, **Then** ambas recebem resposta normal, há uma única reserva ativa e a recusa
   não revela o apartamento, código ou identidade de quem conseguiu a data.
2. **Given** S2 do 101, **When** pedir salão em `2030-03-16` e aprovar eventual pendência,
   **Then** não surgir reserva para 101, nenhuma resposta conter `RSV-4821` ou o número 302
   isolado e nenhum evento conter `RSV-4821`.
3. **Given** reservas criadas e uma cancelada, **When** reiniciar e criar outra reserva,
   **Then** os códigos serem diferentes entre si, dos iniciais e dos cancelados, e o
   cancelamento anterior continuar efetivo.

### Edge Cases

- Uma área pode ficar ocupada entre a proposta e a aprovação: aprovar não ignora a ocupação.
- Reservar data ocupada pode ser recusado antes de gerar pendência ou após sua aprovação;
  nenhum desses caminhos cria reserva duplicada ou expõe a reserva alheia.
- Cancelar reserva própria libera a área/data para novo pedido, preservando a não reutilização
  do código cancelado. Cancelar reserva inexistente não altera registros de terceiros.
- Negar, aprovar ou reenviar uma pendência não responde outras pendências da mesma sessão.
- Múltiplas pendências DEVEM aparecer integralmente nas respostas enquanto estiverem ativas.
- Respostas simultâneas ao mesmo ID têm comportamento livre; o reenvio sequencial exige conflito.
- Uma nova mensagem durante pendência não pode efetivar cobrança por consentimento textual.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O morador DEVE reservar áreas comuns informando área e data; a reserva DEVE
  pertencer exclusivamente ao apartamento definido na sessão.
- **FR-002**: Cada área DEVE ter no máximo uma reserva ativa por data, em qualquer instante,
  inclusive quando pedidos ou aprovações de sessões diferentes forem simultâneos.
- **FR-003**: Área com taxa zero DEVE ser reservada sem confirmação; taxa maior que zero DEVE
  gerar cobrança e exigir confirmação sistêmica prévia, sem implementar pagamento ou estorno.
- **FR-004**: O morador DEVE cancelar somente reservas próprias, sem confirmação; o sistema
  DEVE validar a propriedade e não revelar códigos ou dados da reserva de terceiros.
- **FR-005**: Cada reserva nova DEVE receber código gerado pelo sistema que nunca se repete,
  inclusive frente a registros iniciais, cancelados e após reinício.
- **FR-006**: A proposta paga DEVE produzir uma pendência identificada, pertencente à sessão,
  com área e data nos detalhes, sem gravar antecipadamente a reserva efetiva.
- **FR-007**: Somente a resposta pelo canal de confirmações DEVE aprovar ou negar a pendência;
  mensagens comuns, instruções do modelo e alegações de aprovação NÃO DEVEM substituí-la.
- **FR-008**: Aprovação válida DEVE retomar a ação solicitante e efetivar uma única reserva se
  ainda permitida; negação NÃO DEVE criar reserva. Os detalhes executados DEVEM ser os aprovados.
- **FR-009**: ID inexistente, de outra sessão ou já respondido DEVE produzir conflito sem efeito;
  tanto aprovações quanto negações DEVEM deixar de ser pendentes após a resposta.
- **FR-010**: Cada resposta de mensagem ou confirmação DEVE listar todas as pendências atuais
  da sessão e eliminar as já respondidas, sem remover pendências não relacionadas.
- **FR-011**: Pendências, respostas consumidas, reservas e cancelamentos DEVEM persistir entre
  reinícios, preservando a possibilidade de aprovar depois do reinício e impedindo reexecução.
- **FR-012**: Quando duas aprovações disputarem a mesma área/data, uma DEVE vencer e a outra
  ser recusada normalmente; o conflito de disponibilidade NÃO DEVE virar erro de servidor.
- **FR-013**: Consultar disponibilidade DEVE revelar somente ocupação, sem identidade alheia;
  validar apenas antes da gravação NÃO satisfaz a exclusividade no instante de efetivação.
- **FR-014**: Todos os efeitos DEVEM aparecer nas consultas diretas do avaliador e todas as
  chamadas de operação DEVEM integrar o histórico completo, sem dados de terceiros.
- **FR-015**: Confirmar DEVE obedecer ao contrato do README: corpo com ID e decisão booleana,
  resposta normal no formato de mensagens e conflito para ID não pendente nessa sessão;
  sessão inexistente DEVE receber o resultado de não encontrada antes da validação do ID.
- **FR-016**: A confirmação DEVE ser reutilizável pela autorização de visitantes da spec 003,
  mantendo vínculo de sessão, persistência, recusa e proteção contra reenvio aqui definidos.

### Key Entities *(include if feature involves data)*

- **Reserva**: Código irrepetível, apartamento proprietário, área, data e estado ativo/cancelado.
- **Área e taxa**: Cadastro inicial que determina se a proposta gera cobrança.
- **Confirmação**: ID, sessão, ação proposta, detalhes e estado pendente/aprovada/negada;
  uma resposta consumida não volta a ser autorização válida.
- **Disponibilidade**: Condição livre/ocupada de um par área/data, sem dados do responsável.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nos fluxos dos passos 5–8, 100% das operações gratuitas ou cancelamentos próprios
  não pedem confirmação, e nenhuma reserva paga existe antes de aprovação válida.
- **SC-002**: Negação, ID inválido, ID de outra sessão e reenvio sequencial geram zero novas
  reservas; cada aprovação permitida produz exatamente uma reserva.
- **SC-003**: Na disputa entre 101 e 201 por `2030-05-11`, há exatamente uma reserva ativa,
  duas respostas normais e zero revelações de dados da outra moradora.
- **SC-004**: Depois de reiniciar, 100% das reservas e cancelamentos concluídos permanecem,
  a aprovação pendente funciona e nenhum código novo coincide com anterior ou cancelado.
- **SC-005**: Nos passos 4 e 10, 302 mantém `RSV-4821`, não ocorre reserva indevida para 101
  e respostas e histórico satisfazem todas as restrições de sigilo desses passos.

## Assumptions

- Depende da [spec 001](../001-sessoes-isolamento/spec.md): sessão persistida, identidade,
  consultas diretas, mensagens e eventos. Entrega o fluxo de confirmação usado pela spec 003.
- Fontes: regras de negócio 1, 2, 4 e 5; garantias 1, 2, 3 e 5; passos 4–10 e 13–15 do README;
  princípios I, II, III e V da constituição 1.0.0.
- Salão custa R$ 150, churrasqueira R$ 80 e quadra tem taxa zero no cadastro fornecido.
  As regras valem para todas as áreas cadastradas, não apenas para os exemplos do avaliador.
- O contrato público está consolidado em [índice e contrato](../README.md). A confirmação é
  parte obrigatória do sistema, e não interpretação de intenção na conversa.
- Sem restrições adicionais de antecedência, datas passadas, horário ou capacidade.
- Não inclui autorização de visitante, pagamento real, estorno, interface, autenticação real,
  obrigação de testes automatizados ou deploy. A aprovação persistida DEVE ser validada
  no serviço real, inclusive após reinício, conforme a constituição.
