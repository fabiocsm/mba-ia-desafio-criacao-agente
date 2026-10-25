# Plano de implementação: entrega reproduzível e validação integral

**Branch Git**: `dev` | **Data**: 2026-10-23 | **Spec**: [spec.md](spec.md)
**Diretório selecionado**: `specs/005-entrega-validacao`; o BRANCH do setup identifica a feature, sem criar/trocar branch. **Estado**: desenho concluído; aplicação, comandos, publicação e aceite funcional futuros.

## Resumo

Consolidar as entregas 001–004, implementar restauração explícita segura, produzir manual final e comprovar os 15 passos e 28 critérios do desafio. Preservar primeiro o enunciado em `docs/desafio-original.md`; somente na implementação substituir README por Arquitetura, Garantias e Como rodar. O README atual permanece intacto neste setup.

## Contexto técnico

- **Linguagem/versão**: Python >=3.12; uv com `pyproject.toml`, `uv.lock` e `.python-version` herdados.
- **Dependências**: FastAPI/Uvicorn, SQLAlchemy/aiosqlite, pydantic-settings e `google-adk==2.2.0`; nenhuma nova infraestrutura externa local. Runner/App resumível e DatabaseSessionService; confirmação nativa, correlação original/nativa distinta e executor transacional das specs 002/003.
- **Armazenamento**: `var/aurora.sqlite3` para negócio/identidade e `var/adk.sqlite3` para sessões/eventos; `var/` ignorado. Ledger e contador permanentes. `dados/` somente leitura. Lock de operação e marcador de restauração em `var/`, sem duplicar histórico conversacional.
- **Agentes**: principal → reservas, visitantes e regulamento; especialistas em chat permitem retorno ao pai e bloqueiam peers. Identidade canônica da sessão; tool de regulamento seletiva da 004; nenhuma rota de verificação como tool.
- **Modelo**: configuração Gemini herdada da 001; escolha/alternativa sujeitas a acesso e limites reais do projeto AI Studio e documentação oficial no momento da validação. Nenhuma quota fixa ou consulta autenticada presumida.
- **Validação**: roteiro manual [quickstart.md](quickstart.md), evidências completas e inspeção do código, sem obrigação de suíte/evals. Nenhum SLA novo; dimensionar algumas dezenas de chamadas considerando múltiplas chamadas por interação.
- **Plataforma/tipo**: API local Linux/macOS, `http://localhost:8000`, um worker, sem reload no teste de reinício. Lock de arquivo interprocesso com biblioteca padrão `fcntl`.
- **Escopo**: comandos/README/aceite final; sem UI, autenticação real, pagamentos, deploy ou novas restrições de reservas. Fork público/main/link é tarefa de entrega futura, não ação deste setup.

## Verificação da constituição

Gates avaliados antes da pesquisa e novamente após o desenho. Nenhuma exceção normativa.

| Regra | Mecanismo herdado/consolidado | Gate futuro |
| --- | --- | --- |
| I — consentimento | Decisão exclusiva da rota, snapshot imutável, retomada Runner no solicitante e consumo+efeito transacional | Passos 7–11; extras de negação/replay/IDs cruzados e aprovação de reserva/visita depois de restart; 200 exige efeito ou recusa real |
| II — identidade | SessionIdentity imutável; consultas filtradas antes de materializar; agenda livre/ocupada | Passos 3,4,10 com sigilo exato; inspeção calls/results e código |
| III — durabilidade | Dois bancos estáveis; startup/GET sem Runner/eventos novos; ledger/contador permanentes; reset offline explícito | Passos 1,12,13; reset idempotente e interrompido sem reuso de códigos |
| IV — seletividade | Fonte real, scope confiável e seleção antes de retornar trechos; eventos integrais | Passo 12: 20h domingo e zero capítulos alheios; passo 15 inspeciona instruções |
| V — exclusividade | Índice único parcial no instante de INSERT; perdedora consumida com recusa normal | Passo 14: duas aprovações 200 e uma reserva, sem dados vencedores |
| Stack/contrato/segredos/entrega | uv+pin ADK, API JSON, Gemini, manual com referências reais, dados intactos, fork público em main | Clone limpo; inspeção dos 28 critérios e seis rotas; nenhuma chave/configuração privada no Git |

A limitação documental do DatabaseSessionService para confirmação continua gate real: diagnóstico/ajuste de integração deve preservar Runner/App, autoria, eventos e efeito persistido. Não aceitar apenas resposta HTTP normal ou demonstração em memória.

## Arquitetura operacional

1. `uv run aurora serve` adquire lock compartilhado de `var/operation.lock` antes de abrir qualquer banco, mantém pelo processo inteiro e recusa inicialização se existir marcador de restauração. Processos de serviço usam o mesmo caminho absoluto; não apagar/recriar arquivo de lock enquanto em uso. CLI `restaurar` exige lock exclusivo não bloqueante: API ativa → recusa sem tocar estado. Tratar API parada como pré-condição, documentar Ctrl+C e aguardar término.
2. `uv run aurora restaurar` valida arquivos iniciais e caminhos, cria marcador durável atomicamente (`fsync` arquivo/diretório) antes de alterar bancos e mantém lock exclusivo. Fecha serviços/conexões antes de manipular arquivos ADK. Nunca é chamado pelo startup. Na transação de negócio, remover autorizações/visitantes e reservas, depois despachos, decisões, propostas e identidades (ordem FK efetiva conferida no schema), reimportar reservas/visitantes iniciais. Preservar cadastros, ledger de todos códigos emitidos/iniciais/cancelados e contador monotônico. Reimportar códigos iniciais já conhecidos sem apagar ledger ou reduzir contador.
3. Depois do commit de negócio, recriar somente o banco ADK, vazio, pelo serviço da versão fixada (conexões fechadas; remover também arquivos WAL/SHM pertencentes a esse banco). Todas sessões, state e eventos ADK são apagados. Sessões antigas retornam 404, pendências/decisões/despachos antigos desaparecem e nenhuma autorização antiga é executável. Política de reset elimina histórico de sessões explicitamente; reinício comum conserva tudo.
4. Não há commit distribuído entre negócio e ADK. Se qualquer fase falhar ou o processo cair, o marcador permanece e `serve` recusa abrir a API; o mesmo comando de restauração repete de forma idempotente sob lock até as duas bases corresponderem ao reset. Em particular, negócio já restaurado/ADK antigo nunca é servido. Somente após verificar estado inicial, ausência de sessões e integridade ledger/contador, remover marcador com sincronização do diretório e liberar lock. Falha após apagar marcador implica que ambas bases já foram verificadas. Não alegar recuperação automática por startup nem manter backups com segredos versionados.
5. Manual final explica responsabilidades/acionamento/justificativa dos quatro agentes e referências reais de cada regra. Caminhos planejados são destinos, não evidências existentes; durante implementação localizar trecho efetivo e verificar cada link e o bloqueio independente do modelo.
6. Validar clone limpo e executar 15 passos em ordem; guardar ações/status/efeitos/eventos e limitações em `docs/validacao/005-integral.md`, sem chaves. Repetir gates afetados por correções e, antes do aceite final, os 15 completos no estado final. Checklist de artefatos não aprova runtime.

## Fases e estrutura

Fase 0: [research.md](research.md) reaproveita pesquisa oficial 001–004; nenhuma incógnita nova requer agente auxiliar. Fase 1: [data-model.md](data-model.md), [contrato de operação/entrega](contracts/operacao.md) e [quickstart.md](quickstart.md). Fase 2: tarefas por história, com mapa FR/SC.

```text
specs/005-entrega-validacao/
  spec.md plan.md research.md data-model.md quickstart.md tasks.md
  contracts/operacao.md analysis-summary.md
src/aurora/
  cli.py config.py storage/maintenance.py storage/reset.py
  storage/database.py storage/schema.py storage/seed.py
  runtime/sessions.py runtime/service.py runtime/runner.py runtime/confirmacoes.py
  agents/principal.py agents/reservas.py agents/visitantes.py agents/regulamento.py
scripts/check_model.py
README.md docs/desafio-original.md docs/arquitetura.md docs/operacao.md
  docs/validacao/005-integral.md docs/entrega.md
pyproject.toml uv.lock .python-version .env.example .gitignore
var/operation.lock var/reset-in-progress.json var/aurora.sqlite3 var/adk.sqlite3
```

Código/documentos operacionais acima são destinos futuros. Sem alteração ao enunciado, dados ou publicação nesta etapa. A estrutura herda módulos adicionais das dependências sem renomeá-los.

## Estratégia e complexidade

Setup/fundação → US1 (clone/restauração) → US2 (evidências integrais) → US3 (manual/público) → ensaio em clone candidato → publicação futura → avaliação integral em clone público/main e entrega. US2 pode preparar roteiro antes do manual final, mas gates finais dependem do README completo. MVP US1 não constitui entrega aceita. Não existe exceção constitucional; lock e marcador são a coordenação mínima para reset em dois bancos sem atomicidade distribuída. Não armazenar segunda cópia de eventos nem estender regras do condomínio.
