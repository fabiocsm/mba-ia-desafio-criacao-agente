"""Erros de fronteira da API. Não carregam dados de outros moradores."""


class ApartamentoInexistente(Exception):
    """O apartamento informado não está no cadastro."""


class SessaoInexistente(Exception):
    """Não há vínculo canônico utilizável para o identificador."""


class ExecucaoExpirada(Exception):
    """O atendimento excedeu o prazo de execução do runtime."""
