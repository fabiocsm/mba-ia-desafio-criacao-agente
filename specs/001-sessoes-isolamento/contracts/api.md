# Contrato HTTP da spec 001

Base: `http://localhost:8000`. Corpos e respostas JSON; `Content-Type: application/json`. Contrato externo consolidado em [specs/README.md](../../README.md). Sem envelope adicional nas listas. Datas de dados: AAAA-MM-DD; `area` é ID em dados/areas.json. Sessão inexistente recebe 404 em toda rota com session_id, antes de invocar Gemini.

| Método/caminho | Entrada | Sucesso | Erros relevantes |
| --- | --- | --- | --- |
| POST /sessoes | `{"apartamento":"101"}` | 201 `{"session_id":"identificador-gerado"}` | Apartamento inexistente: 422 JSON, escolha permitida |
| POST /sessoes/{session_id}/mensagens | `{"texto":"Quais são minhas reservas?"}` | 200 `{"resposta":"texto","confirmacoes_pendentes":[]}` | 404 sessão ausente; schema inválido: 422 JSON |
| GET /sessoes/{session_id}/eventos | sem corpo | 200 array de eventos ADK completos na ordem persistida | 404 sessão ausente |
| GET /apartamentos/{apartamento}/reservas | sem corpo | 200 `[{"codigo":"RSV-1377","area":"quadra","data":"2030-03-09"}]` para 101 inicial | Apartamento sem registros/inexistente: [] |
| GET /apartamentos/{apartamento}/visitantes | sem corpo | 200 `[{"nome":"Marina Duarte","data":"2030-03-16"}]` para 302 inicial | Apartamento sem registros/inexistente: [] |

## Tipos e invariantes

- Entrada da sessão: apartamento string; não aceitar campos adicionais como autoridade para state, user_id ou nome do agente.
- Entrada de mensagem: texto string; qualquer identidade citada é somente texto sem efeito sobre vínculo canônico.
- Saída: resposta string, podendo ser vazia; confirmacoes_pendentes array de **todas** as pendências correntes, cada uma com id/acao/detalhes. Nesta spec não há mutações/pendências, portanto [] é correto. A 002 substitui a fonte da lista por consulta ao armazenamento de pendências, sem alterar envelope.
- Reserva externa contém somente codigo, area, data; visitante somente nome, data. Não renomear campos nem retornar objetos internos/ORM inteiros.
- GET/eventos retorna todos os campos persistidos de cada Event, incluindo author, invocation_id, timestamp, conteúdo e actions; sem projeção redutora. O contrato não fixa a lista de campos internos do SDK, mas exige conteúdo completo consistente com a versão fixada. Pode haver zero eventos numa sessão recém-criada; não fabricar evento de abertura ou leitura.
- Rotas diretas são do avaliador: consultam banco sem modelo; sua capacidade de leitura não é oferecida por tools.

## Extensão obrigatória pela 002

`POST /sessoes/{session_id}/confirmacoes` recebe `{"id":"...","confirmado":true}` com booleano estrito; retorna 200 no mesmo envelope ou 409 para ID inexistente, de outra sessão ou já respondido; sessão inexistente recebe 404. A rota será implementada na 002; não publicar um stub que retorne sucesso sem ação. Este contrato reserva os nomes exigidos, sem antecipar entrega.
