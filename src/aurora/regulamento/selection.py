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
    r"\b(?:topics?|topicos?|paths?|caminhos?|tools?|ferramentas?|"
    r"quer(?:y|ies)|consultas?|capitulos?|chapters?|args|argumentos)"
    r"\s*[:=]\s*[^\s,;]+",
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

_GENERICOS = frozenset(
    {
        "a",
        "o",
        "os",
        "as",
        "um",
        "uma",
        "de",
        "do",
        "da",
        "dos",
        "das",
        "e",
        "ou",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "para",
        "por",
        "com",
        "que",
        "qual",
        "quais",
        "como",
        "onde",
        "me",
        "meu",
        "minha",
        "meus",
        "minhas",
        "se",
        "ao",
        "aos",
        "sobre",
        "regra",
        "regras",
        "norma",
        "normas",
        "regulamento",
        "diz",
        "fala",
        "fale",
        "explique",
        "duvida",
        "duvidas",
        "pode",
        "posso",
        "poder",
        "ha",
        "tem",
        "existe",
        "existem",
        "quero",
        "saber",
        "informe",
        "informa",
        "favor",
        "gentileza",
        "interno",
        "interna",
        "condominio",
        "residencial",
        "aurora",
        "artigo",
        "capitulo",
        "ate",
        "sao",
        "esta",
        "esse",
        "essa",
        "isso",
        "meu",
        "sua",
        "seu",
    }
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
    util = _preparar(texto)
    if util is None:
        return Autorizacao("esclarecer", ())
    norm = normalizar(util)
    if not norm:
        return Autorizacao("esclarecer", ())

    assuntos = [
        assunto
        for assunto in ASSUNTOS
        if any(_tem(norm, alias) for alias in assunto.aliases)
    ]
    if not assuntos:
        return Autorizacao("esclarecer", ())

    escolhidos: set[str] = set()
    algum_completo = False
    algum_parcial = False
    algum_sem_regra = False
    for assunto in assuntos:
        intencoes = [item for item in INTENCOES if item.assunto == assunto.id]
        completas = [item for item in intencoes if _completa(norm, item)]
        if completas:
            algum_completo = True
            for item in completas:
                escolhidos.update(item.unidades)
                for artigo_id in item.artigos:
                    escolhidos.update(expandir_artigo(artigo_id))
            continue
        if any(_tem(norm, ausencia) for ausencia in assunto.ausencias):
            algum_sem_regra = True
            continue
        if any(_parcial(norm, item) for item in intencoes):
            algum_parcial = True
            continue
        if _sobra_especifica(norm, assunto):
            algum_sem_regra = True

    if not algum_completo:
        if algum_sem_regra and not algum_parcial:
            return Autorizacao("sem_base", ())
        return Autorizacao("esclarecer", ())

    ordenadas = tuple(
        unidade.id for unidade in indice_atual().unidades if unidade.id in escolhidos
    )
    if not ordenadas:
        return Autorizacao("sem_base", ())
    return Autorizacao("ok", ordenadas)


def normalizar(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(caractere for caractere in nfkd if not unicodedata.combining(caractere))
    sem_acento = sem_acento.lower().replace("º", " ").replace("ª", " ")
    sem_acento = re.sub(r"[^a-z0-9]+", " ", sem_acento)
    return re.sub(r"\s+", " ", sem_acento).strip()


def _preparar(texto: str) -> str | None:
    sem_tecnico = _TECNICO.sub(" ", texto)
    frases = [frase.strip() for frase in re.split(r"[.!?\n;]+", sem_tecnico) if frase.strip()]
    if not frases:
        return None
    uteis = [frase for frase in frases if not _eh_controle(normalizar(frase))]
    if not uteis:
        return None
    return " ".join(uteis)


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


def _parcial(texto: str, intencao: Intencao) -> bool:
    if _completa(texto, intencao):
        return False
    for grupo in intencao.grupos:
        presentes = [_tem(texto, sinal) for sinal in grupo]
        if any(presentes) and not all(presentes):
            return True
    return False


def _sobra_especifica(texto: str, assunto: Assunto) -> bool:
    aliases: set[str] = set()
    for alias in assunto.aliases:
        aliases.update(normalizar(alias).split())
    for token in texto.split():
        if token in _GENERICOS or token in aliases:
            continue
        if token.endswith("s") and token[:-1] in aliases:
            continue
        return True
    return False
