"""Erros de fronteira da API. Não carregam dados de outros moradores."""


class ApartamentoInexistente(Exception):
    """O apartamento informado não está no cadastro."""


class SessaoInexistente(Exception):
    """Não há vínculo canônico utilizável para o identificador."""


class ExecucaoExpirada(Exception):
    """O atendimento excedeu o prazo de execução do runtime."""


class ConfirmacaoConflito(Exception):
    """O ID não está pendente nesta sessão. Não carrega dados de outra sessão."""


class RetomadaIncompleta(Exception):
    """A decisão foi registrada, mas a retomada não gravou o efeito e os eventos."""
