# Plano de implementação: consulta seletiva ao regulamento

**Branch Git**: `dev` | **Data**: 2026-10-23 | **Spec**: [spec.md](spec.md)
**Diretório selecionado**: `specs/004-consultar-regulamento`; BRANCH retornado pelo script identifica a feature, sem criar ou trocar branch. **Estado**: desenho concluído, runtime não implementado/validado.

## Resumo

Adicionar especialista `regulamento` ao principal e recuperação local determinística por assunto/intenção antes de qualquer conteúdo alcançar modelo, tool result ou evento. A fonte continua `dados/regulamento.md`; nenhum texto normativo vai às instruções. Pergunta sobre piscina no domingo seleciona artigo 22, inciso II, que informa 20h. Um índice estrutural interno não é contexto do agente. A tool não aceita consultas livres nem capítulos escolhidos pelo LLM.

## Contexto técnico

- **Linguagem/dependências**: Python >=3.12, uv, FastAPI/Uvicorn, SQLAlchemy/aiosqlite, Pydantic e `google-adk==2.2.0`, pin/lock herdados da 001. Parser de Markdown com biblioteca padrão, sem serviço de busca externo nem nova dependência.
- **Runtime**: Runner e App resumível; DatabaseSessionService em `var/adk.sqlite3`, negócio/identidade canônica em `var/aurora.sqlite3`; árvore `aurora_principal` → reservas, visitantes, regulamento, modo chat. Especialistas permitem retorno ao principal e bloqueiam transferência direta a peers, preservando a 001.
- **Modelo**: reutilizar configuração Gemini e pesquisa 001, sem escolher novo modelo. Acesso/limites ativos continuam gate operacional antes de chamadas reais; nenhuma quota presumida.
- **Armazenamento**: fonte original somente leitura; índice em memória reconstruível, sem persistência normativa duplicada. Eventos completos e sua ordem no ADK, sem compactação/filtragem; nenhum novo banco ou esquema de negócio.
- **Tipo/plataforma**: API local Linux/macOS em `http://localhost:8000`, um worker; interações da mesma sessão serializadas; sessões distintas independentes.
- **Escala/desempenho**: regulamento local de 14 capítulos/96 artigos; dezenas de chamadas no fluxo integral, sem SLA ou métricas inventadas. Recuperar unidades suficientes, sem expandir automaticamente capítulos referenciados.
- **Validação**: roteiro manual reproduzível, comparação JSON integral e inspeção da fronteira de contexto. Sem suíte automatizada/evals obrigatórios. Passos 12, 13, 15 e regressões afetadas; 005 repete os 15 passos.
- **Restrições**: sem UI, atualização documental, busca externa, autenticação, pagamento, deploy ou novas regras operacionais de reservas por horário/capacidade/prazo/data passada.

## Verificação da constituição

Gates examinados antes da pesquisa e novamente após desenho. Sem exceção normativa.

| Princípio | Mecanismo planejado | Evidência requerida | Gate do desenho |
| --- | --- | --- | --- |
| I — consentimento | Tool só leitura, sem coordenador de mutação; envelope preserva pendências reais | Consultar não cria/decide pendência; confirmar reserva/visita ainda retoma autor correto | Conforme; runtime pendente |
| II — identidade | Resolver SessionIdentity da 001; escopo por requisição confiável, sem identidade LLM; nenhuma tool administrativa | Alternar consulta e reservas próprias sem identidade/dados alheios | Conforme |
| III — persistência | Eventos ADK integrais; startup/GET sem novos eventos; índice reconstruído fora do contexto | Mesmo JSON/contagem após restart e nova mensagem na sessão original | Conforme |
| IV — seletividade | Catálogo assunto/intenção → unidades autorizadas pela mensagem original, tool sem query, validação anterior a retorno | 20h art22II; zero capítulos alheios nos eventos e nas instruções; injeções falham fechadas | Conforme |
| V — exclusividade | Nenhuma escrita de negócio nem alteração no índice único 002 | Rotas diretas preservadas, reservas continuam protegidas na gravação | Conforme |
| Stack/contrato/segredos | Nenhuma rota nova; versões e configuração herdadas; sem chave em evidências | 200/404/envelope/eventos completos; modelo e limites verificados ao validar | Conforme |

Limitação herdada: confirmar tools em DatabaseSessionService requer comprovação real antes/depois de reinício, não promessa documental. Acrescentar o terceiro especialista exige regressão da autoria, seleção e retomada das confirmações 002/003. Nenhum gate de runtime foi executado nesta preparação.

## Arquitetura e fluxo

1. Parser local lê arquivo inteiro **fora** de prompts, Runner, tool args/results e eventos; separa capítulo/artigo/inciso/parágrafo em unidades com posição de origem. Índice não é serializável pelo schema da tool, não vira instrução e não é logado em evento/erro. Erros expõem só diagnóstico estrutural, nunca documento integral.
2. `regulamento/catalog.py` associa assuntos e intenções às unidades por referências estruturais, sem copiar respostas. Catálogo cobre os assuntos do documento e aliases portugueses, normalizando acentos/caixa. Cada entrada exige assunto e intenção compatíveis (por exemplo piscina+horário+domingo → art22II). Comandos técnicos de topics/path/tool e pedidos de carga/controle não contam como perguntas temáticas; se não for possível separar com segurança a pergunta desses comandos, esclarecer sem trecho. Termos genéricos, correspondência incerta ou pedido de todo documento pedem foco; pedidos sem fonte retornam ausência. Não usar busca semântica global nem fallback para capítulo inteiro. Assuntos múltiplos específicos autorizam a união mínima correspondente; remissões não expandem outros capítulos automaticamente.
3. `runtime/service.py` deriva `ConsultaScope` da **mensagem original recebida pela API**, sob lock da sessão, antes do Runner; não da pergunta reescrita, state, payload ou args do modelo. ContextVar confiável contém sessão, nonce aleatório próprio da execução HTTP e conjunto fechado de unidades. Esse nonce não é invocation_id ADK: o SDK gera a invocação nova; não fornecer invocation_id de retomada para fabricar uma nova execução. Instalar o contexto somente ao redor do Runner correspondente; a tool confere sessão canônica e presença desse contexto corrente. Token resetado em finally, inclusive exceções; scopes de sessões concorrentes não se misturam. Retomada de confirmação sem nova pergunta não herda escopo anterior. Referência ambígua em nova mensagem pede esclarecimento, sem ampliar por histórico.
4. `consultar_regulamento(tool_context)` não tem parâmetros LLM. Confere sessão canônica, scope confiável e nonce da execução corrente, aplica catálogo e só então materializa trechos autorizados. Retorna somente seleção mínima e referências, ou status `esclarecer`/`sem_base`. Sem scope válido não devolve texto normativo. Chamadas adicionais na mesma mensagem não podem acumular capítulos diferentes. Alterar nome de tool, tentar listar capítulos ou forjar query/tema não amplia o conjunto.
5. Especialista interpreta resultado suficiente e responde com base nos trechos retornados; domingo fecha 20h derivado da fonte, nunca constante normativa em prompt. Status sem fonte ou ambíguo produz mensagem determinística de limitação/esclarecimento na montagem da resposta, sem norma inventada. Prompts instruem a não completar lacunas; a proteção de seleção é código. Principal faz encaminhamento e retorno, sem texto da fonte nas instruções.
6. Serviço herdado persiste todos eventos completos e ordenados, inclusive calls/results/transfers. Escopo apenas autoriza leitura, nunca remove eventos nem altera os existentes. `GET /eventos` continua leitura integral. Respostas de tool contêm referências/trechos da consulta atual; consultas anteriores legitimamente solicitadas não são removidas.
7. Voltar a reservas/visitantes passa pelo principal mantendo a sessão original. Especialista regulamento recebe somente tool de leitura; não chama executores de negócio. A resposta lista todas pendências existentes do banco, nunca zera por tratar-se de dúvida. A consulta, por si, não altera registros/identidade nem decide consentimento.

## Fases e artefatos

Fase 0: [research.md](research.md), decisões locais e stack herdada, sem incógnita técnica que requeira novo agente de pesquisa. Fase 1: [data-model.md](data-model.md), [contrato](contracts/regulamento.md), [quickstart.md](quickstart.md). Fase 2: [tasks.md](tasks.md), setup → fundação segura → US1 P1 → US2 P1 → US3 P2 → acabamento. A seletividade é fundação, não correção posterior da US2. Análise read-only; registro de resumo e correções em etapa separada autorizada.

## Estrutura do projeto

```text
specs/004-consultar-regulamento/
  spec.md plan.md research.md data-model.md quickstart.md tasks.md
  contracts/regulamento.md analysis-summary.md
src/aurora/
  regulamento/models.py regulamento/parser.py regulamento/catalog.py
  regulamento/selection.py tools/regulamento.py agents/regulamento.py
  agents/principal.py runtime/app.py runtime/service.py
  runtime/events.py runtime/sessions.py tools/context.py
  api_routes/sessoes.py api_routes/confirmacoes.py
  api_routes/verificacao.py storage/identity.py
  runtime/confirmacoes.py runtime/runner.py
docs/arquitetura.md docs/operacao.md docs/validacao/004-regulamento.md
```

Os caminhos de código são destinos futuros. Não implementar aplicação nesta fase nem trocar README enunciado. Depende da 001; integração com mutações usa 002/003 quando presentes na sequência. MVP US1 já inclui fronteira seletiva e eventos íntegros; aceite completo exige US2/US3. Complexidade: apenas índice reconstruível, catálogo explícito e scope confiável; sem violação constitucional ou exceção.
