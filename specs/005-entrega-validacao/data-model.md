# Modelo operacional e evidências

Não cria novas entidades de condomínio. Herda [001](../001-sessoes-isolamento/data-model.md), [002](../002-reservas-confirmacoes/data-model.md) e [003](../003-autorizar-visitantes/data-model.md); mantém eventos canônicos somente no ADK. As constraints abaixo são literais para tarefas.

| Entidade/artefato | Campos/relações | Constraint literal |
| --- | --- | --- |
| Marcador de restauração | `var/reset-in-progress.json`, versão de formato e identificação da operação local; não é sessão/proposta | C501: “marcador durável é criado antes de qualquer alteração; enquanto existir, serve recusa iniciar; removê-lo exige as duas bases restauradas e verificadas”. Não conter chave, mensagem ou dados de moradores |
| Estado restaurado | Reservas/visitantes iniciais; sessões/pendências/decisões/despachos/autorizações anteriores eliminados | C502: “restauração exige API parada e lock exclusivo; apaga sessões e eventos, elimina pendências e decisões, repõe reservas e visitantes iniciais sem editar dados/”. Autorizações iniciais importadas com proposta_id nulo; ordem FK conferida no schema |
| Ledger/contador permanentes | Entidades C205/C206 herdadas; todas emissões, mesmo canceladas, sobrevivem | C503: “restauração preserva todos códigos emitidos e o contador monotônico; nenhum código inicial, cancelado ou anterior ao reinício é reutilizado” |
| Evidência de validação | Passo/gate, data, commit, ambiente, ação, status, esperado, observado, caminhos dos snapshots e conclusão | C504: “evidência registra resultado observado por passo e só marca aprovado após conferir resposta, armazenamento e eventos aplicáveis; ausência de execução é não executado, nunca aprovado”. Sem credenciais/configuração privada no Git |
| Referência de garantia | Regra, arquivo real, símbolo/trecho e justificativa independente do modelo | C505: “cada uma das cinco garantias aponta trecho existente e efetivo no código final; caminho planejado não é evidência” |

## Ciclo de restauração

API parada → lock exclusivo → validar fontes → marcador durável → commit reset de negócio em ordem FK (filhos antes de pais; preservar ledger/contador) → ADK vazio → verificar ambas bases → remover marcador → liberar lock. Qualquer falha após marcador mantém bloqueio, permite repetir o comando e não é tratada como sucesso. Nenhum commit distribuído é alegado; startup nunca restaura nem executa Runner/acrescenta eventos. API retém lock compartilhado por toda sua vida; todos comandos usam o mesmo arquivo estável. A política se aplica a todos os dados runtime, sem tocar originais.

## Evidências e entrega

Evidência planejada → executada → aprovada ou falhou. Falha exige correção e reexecução afetada; aceite final exige 15/15 no estado final, todos AC-01–AC-28, gates adicionais e manual conferidos. Arquivos de snapshots locais com dados próprios são ignorados; relatório versionável contém apenas resultados/snapshots necessários sem segredos. Sessões de reset não são sessões preservadas; no reinício comum, comparar JSON completo e ordem sem remover eventos anteriores.
