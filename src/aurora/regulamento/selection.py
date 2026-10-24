"""Autorização fechada a partir do texto HTTP original.

A tool não escolhe tema. Comando técnico, pedido integral e pergunta vaga
não ampliam o conjunto. O escopo vive só na execução e sai no finally.
"""

from __future__ import annotations

import re
import unicodedata
from contextvars import ContextVar
from contextvars import Token

from aurora.regulamento.catalog import ASSUNTOS
from aurora.regulamento.catalog import INTENCOES
from aurora.regulamento.catalog import Assunto
from aurora.regulamento.catalog import Intencao
from aurora.regulamento.models import Autorizacao
from aurora.regulamento.models import ConsultaScope
from aurora.regulamento.parser import expandir_artigo
from aurora.regulamento.parser import indice_atual

_consulta: ContextVar[ConsultaScope | None] = ContextVar(
    "aurora_consulta_regulamento",
    default=None,
)

_TECNICO = re.compile(
    r"\b(?:topics?|t[oó]picos?|paths?|caminhos?|tools?|ferramentas?|"
    r"quer(?:y|ies)|consultas?|cap[ií]tulos?|chapters?|args|argumentos)\b",
    re.IGNORECASE,
)

_FRASES_CONTROLE = (
    "ignore as instrucoes",
    "ignore instrucoes",
    "esquec a as instrucoes",
    "esqueca as instrucoes",
    "desconsidere as instrucoes",
    "modo desenvolvedor",
    "jailbreak",
)

_FRASES_INTEGRAL = (
    "regulamento inteiro",
    "regulamento completo",
    "documento inteiro",
    "documento completo",
    "todos os capitulos",
    "todos os artigos",
    "na integra",
    "inteiro teor",
    "mostre tudo",
    "carregue tudo",
)

_VERBOS_CARGA = ("carregue", "carregar", "transcreva", "transcrever")

_EXCLUSAO = re.compile(
    r"\b(?:nao (?:(?:me )?(?:fale|comente|inclua|mencione|consulte|busque|traga|responda)|"
    r"quero|preciso|desejo)|"
    r"sem (?:falar|comentar|comentarios|mencionar|consultar)|evite (?:falar|comentar|mencionar)|"
    r"ignore|exclua|exceto)\b"
)


def consulta_atual() -> ConsultaScope | None:
    return _consulta.get()


def instalar_consulta(scope: ConsultaScope) -> Token:
    return _consulta.set(scope)


def reset_consulta(token: Token) -> None:
    _consulta.reset(token)


def autorizar_mensagem(texto: str) -> Autorizacao:
    """Decide o conjunto fechado. Não devolve texto da fonte."""
    indice_atual()
    escolhidos: set[str] = set()
    algum_sem_regra = False
    algum_incerto = False
    for norm in _preparar(texto):
        assuntos = _assuntos_da_clausula(norm)
        if not assuntos:
            algum_incerto = True
        for assunto in assuntos:
            if any(_tem(norm, ausencia) for ausencia in assunto.ausencias):
                algum_sem_regra = True
                continue
            completas = [
                item for item in INTENCOES
                if item.assunto == assunto.id and _completa(norm, item)
            ]
            if not completas:
                algum_incerto = True
            for item in completas:
                escolhidos.update(item.unidades)
                for artigo_id in item.artigos:
                    escolhidos.update(expandir_artigo(artigo_id))

    ordenadas = tuple(
        unidade.id for unidade in indice_atual().unidades if unidade.id in escolhidos
    )
    if not ordenadas:
        status = "sem_base" if algum_sem_regra and not algum_incerto else "esclarecer"
        return Autorizacao(status, ())
    return Autorizacao("ok", ordenadas)


def normalizar(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(caractere for caractere in nfkd if not unicodedata.combining(caractere))
    sem_acento = sem_acento.lower().replace("º", " ").replace("ª", " ")
    sem_acento = re.sub(r"[^a-z0-9]+", " ", sem_acento)
    return re.sub(r"\s+", " ", sem_acento).strip()


def _preparar(texto: str) -> list[str]:
    # Depois de um argumento técnico, todo o restante é não confiável:
    # valores JSON/listas podem conter pontuação e novas linhas. Não tentar
    # reinterpretá-los como perguntas. O prefixo independente continua válido.
    texto = unicodedata.normalize("NFC", texto)
    tecnico = _TECNICO.search(texto)
    if tecnico:
        texto = texto[:tecnico.start()]
    uteis: list[str] = []
    for frase in re.split(r"[.!?\n;]+", texto):
        norm = normalizar(frase)
        if _eh_controle(norm):
            continue
        exclusao = _EXCLUSAO.search(norm)
        if exclusao:
            norm = norm[:exclusao.start()].strip()
        # Intenções não atravessam a conjunção que inicia outro pedido.
        clausulas: list[str] = []
        for clausula in re.split(r"\s+e\s+", norm):
            if not clausula:
                continue
            if clausulas and not _assuntos_da_clausula(clausula):
                # Coordenação do mesmo assunto: "domingo e segunda".
                clausulas[-1] += " e " + clausula
            else:
                clausulas.append(clausula)
        uteis.extend(clausulas)
    return uteis


def _assuntos_da_clausula(texto: str) -> list[Assunto]:
    assuntos = [
        assunto for assunto in ASSUNTOS
        if any(_tem(texto, alias) for alias in assunto.aliases)
    ]
    ids = {assunto.id for assunto in assuntos}
    # Nestas construções, a área/elevador é complemento da pergunta sobre
    # o animal ou a mudança; não autoriza as regras gerais daquele local.
    incidentais: set[str] = set()
    if "animais" in ids:
        incidentais.update({
            "piscina", "academia", "brinquedoteca", "playground", "salao",
            "churrasqueira", "quadra", "elevador", "garagem",
        })
    if "mudanca" in ids:
        incidentais.update({"elevador", "vedacoes_morador"})
    if "obra" in ids:
        incidentais.update({"silencio", "vedacoes_morador"})
    pertinentes = [assunto for assunto in assuntos if assunto.id not in incidentais]
    # Sem uma relação conhecida ou cláusulas independentes, não aplicar
    # a intenção de um tema aos demais apenas por compartilharem palavras.
    return pertinentes if len(pertinentes) <= 1 else []


def _eh_controle(frase: str) -> bool:
    if any(padrao in frase for padrao in _FRASES_CONTROLE):
        return True
    if any(padrao in frase for padrao in _FRASES_INTEGRAL):
        return True
    return any(_tem(frase, verbo) for verbo in _VERBOS_CARGA)


def _tem(texto: str, sinal: str) -> bool:
    alvo = normalizar(sinal)
    if not alvo:
        return False
    if " " in alvo:
        return f" {alvo} " in f" {texto} "
    return re.search(rf"(?:^| ){re.escape(alvo)}s?(?: |$)", texto) is not None


def _completa(texto: str, intencao: Intencao) -> bool:
    return any(all(_tem(texto, sinal) for sinal in grupo) for grupo in intencao.grupos)
