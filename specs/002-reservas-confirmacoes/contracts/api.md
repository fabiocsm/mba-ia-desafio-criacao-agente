# Contrato HTTP: reservas e confirmação

Base localhost:8000, JSON. Mantém integralmente o [contrato 001](../../001-sessoes-isolamento/contracts/api.md) e [índice](../../README.md). Não oferecer rotas administrativas ao modelo.

| Método/rota | Entrada | Resultado |
| --- | --- | --- |
| POST /sessoes/{session_id}/confirmacoes | `{"id":"uuid-publico","confirmado":true}`; confirmado booleano estrito, não string/número | 200 envelope abaixo para aprovação permitida, indisponível ou negação;409 ID inexistente/alheio/respondido;404 sessão ausente antes de validar o ID |
| POST /sessoes/{session_id}/mensagens | `{"texto":"Reserve a quadra para 2030-04-06"}` | 200 `resposta` string e lista integral de pendências atuais;404 sessão ausente |
| GET /apartamentos/{apartamento}/reservas | sem corpo | 200 array de reservas ativas, objetos codigo/area/data, estado real sem modelo |
| GET /sessoes/{session_id}/eventos | sem corpo | 200 array de eventos ADK completos e ordenados, sem filtragem;404 sessão ausente |

```json
{
  "resposta": "Aguardo a confirmação da reserva.",
  "confirmacoes_pendentes": [
    {
      "id": "uuid-publico",
      "acao": "reservar_area",
      "detalhes": {"area": "salao-de-festas", "data": "2030-04-20", "taxa_centavos": 15000}
    }
  ]
}
```

`resposta` pode ser vazia. Detalhes vêm da proposta canônica congelada, nunca do cliente. Lista contém todas propostas publicadas da sessão sem decisão, inclusive as não relacionadas à última resposta. Aprovar/negá-la remove apenas aquela pendência. Resposta de aprovação ou negação aceita é 200 no mesmo envelope; se não houver outras, lista[]. A disputa de disponibilidade também é 200, sem código/apartamento/responsável vencedor. Reserva efetivada aparece nas rotas diretas antes de declarar sucesso; negação não aparece.

ID ausente/alheio/respondido em sessão existente é 409 e não consome outra pendência, chama Runner ou altera negócio. Sessão inexistente é 404 antes do lookup do ID. Schema inválido com sessão existente é 422 JSON; strings `"true"` e números não são booleanos. Verificar ordem de validação com sessão ausente e corpo JSON estruturalmente válido:404 tem precedência sobre semântica dos campos.

Nova mensagem durante pendência não aprova nada. Pode esclarecer, consultar e criar outra proposta; confirmações existentes continuam todas listadas. Mensagens não podem fornecer ID/author/session_id confiáveis ao runtime. Consentimento textual não produz DecisaoConfirmacao.

Startup e GET não criam eventos. Depois de confirmação 200 o despacho está concluído, e restart mantém eventos idênticos até nova interação. Se queda excepcional interrompe POST após gravar decisão, replay desse ID continua 409 sem executar; uma nova POST mensagens na mesma sessão recupera primeiro o despacho decidido pelo Runner e depois processa o texto. Trata-se de recuperação da decisão sistêmica já registrada, não de consentimento pelo texto. GET não dispara essa recuperação.

## Sigilo verificável

No passo 4, pedir cancelamento do salão de 2030-03-16 por sessão 101 não altera reserva alheia nem traz RSV-4821 em resposta/eventos. No passo 10, pedir a mesma data ocupada não cria reserva 101; nenhuma resposta contém RSV-4821 ou o número 302 isolado; nenhum evento contém RSV-4821. Tools devem fornecer somente ocupação/recusa genérica antes da geração; revisar também instruções/aviso de recusa para não ecoar apartamento citado. Não filtrar eventos para ocultar falha. Os textos originais do avaliador não fornecem o código secreto, permitindo verificar sua ausência no histórico completo.
