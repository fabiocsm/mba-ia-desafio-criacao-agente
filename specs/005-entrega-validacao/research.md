# Pesquisa e decisões de consolidação

**Data**: 2026-10-23. Pesquisa tecnológica herdada, sem novo teste de runtime/Gemini, quotas autenticadas ou publicação.

## R1 — Reutilização da arquitetura

**Decisão**: preservar [pesquisa 001](../001-sessoes-isolamento/research.md), [confirmação 002](../002-reservas-confirmacoes/contracts/confirmation-runtime.md), [modelo 003](../003-autorizar-visitantes/data-model.md) e [seleção 004](../004-consultar-regulamento/plan.md). Python/uv, FastAPI, ADK exato 2.2.0, Runner/App, SQLite separado e identidade canônica não são decisões reabertas pela entrega.
**Justificativa**: uma única arquitetura integrada, sem nova topologia que invalide autoria/retomada. A limitação documentada do DatabaseSessionService exige prova real nas tarefas, não conclusão por leitura.
**Alternativas consideradas**: recriar ferramentas/runtime em 005 ou trocar para memória volátil foram rejeitados. Não há incógnita nova que justifique agente auxiliar de pesquisa.

## R2 — Restauração offline recuperável

**Decisão**: serviço retém lock compartilhado, restauração exige exclusivo; marcador durável precede alterações; transação de negócio preserva ledger/contador e elimina dependências por FK; ADK é recriado vazio com conexões fechadas. Falha parcial bloqueia subida até repetir reset idempotente com sucesso.
**Justificativa**: não prometer commit entre bancos independentes. Invalidar sessões antigas evita consentimentos sobre estado restaurado. Manter códigos emitidos impede reuso mesmo após reset.
**Alternativas consideradas**: apagar `var/` inteiro elimina ledger; reset com API ativa admite gravações concorrentes; preservar sessões exigiria reconciliação adicional sem benefício no desafio.
**Fontes oficiais herdadas**: [transações SQLite](https://www.sqlite.org/lang_transaction.html), [WAL e arquivos associados](https://www.sqlite.org/wal.html), [fcntl.flock](https://docs.python.org/3.12/library/fcntl.html#fcntl.flock). A implementação deve conferir a ordem FK e fechamento de conexões da versão fixada; esta decisão não declara reset já validado.

## R3 — Evidência manual e modelo

**Decisão**: roteiro dos 15 passos com dados/eventos completos e tabela AC-01–AC-28, mais testes manuais de aprovação persistida após reinício e falha parcial de reset. Documentação oficial Gemini e limites ativos AI Studio são gate operacional herdado antes de executar; nada presume quotas disponíveis.
**Justificativa**: respostas textuais e documentação coerente não provam execução nem sigilo. Fluxo deve tolerar reformulação e esclarecimentos necessários.
**Alternativas consideradas**: suíte/evals obrigatórios extrapolam escopo; ocultar conteúdo em eventos viola rastreabilidade.

## R4 — Manual e entrega

**Decisão**: preservar enunciado integral em `docs/desafio-original.md` antes de futura troca do README. Manual com Arquitetura, Garantias e Como rodar, links a código existente conferidos no estado final. Fork público/main/link somente na futura implementação/entrega.
**Justificativa**: mantém fonte normativa e viabiliza auditoria após a troca; não confundir planos com evidência de código.
**Alternativas consideradas**: remover enunciado sem preservação ou publicar durante preparação foram rejeitados por escopo.
