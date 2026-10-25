"""Parser estrutural. Lê a fonte fora de prompt, tool result e evento.

Erros citam só a posição e o tipo do bloco. O corpo não entra na exceção,
no log nem na representação do índice.
"""

from __future__ import annotations

import logging
import re

from aurora.config import repo_root
from aurora.regulamento.models import FONTE_RELATIVA
from aurora.regulamento.models import Indice
from aurora.regulamento.models import Unidade

logger = logging.getLogger(__name__)

_CAPITULOS_ESPERADOS = 14
_ARTIGOS_ESPERADOS = 96

_CAPITULO = re.compile(r"^## Capítulo ([IVXLCDM]+): .+$")
_ARTIGO = re.compile(r"^\*\*Art\. (\d+)(?:º|\.)?\*\*(?:\s(.*))?$", re.DOTALL)
_PARAGRAFO_UNICO = re.compile(r"^Parágrafo único\.\s*(.*)$", re.DOTALL)
_PARAGRAFO = re.compile(r"^§ (\d+)º\s*(.*)$", re.DOTALL)
_INCISO = re.compile(r"^([IVXLCDM]+)\. (.+)$", re.DOTALL)
_TITULO = re.compile(r"^# .+$")

_indice: Indice | None = None


class RegulamentoEstruturaError(Exception):
    """Diagnóstico estrutural, sem o corpo do regulamento."""


def caminho_fonte():
    return (repo_root() / FONTE_RELATIVA).resolve()


def indice_atual() -> Indice:
    if _indice is None:
        raise RegulamentoEstruturaError("Índice não reconstruído.")
    return _indice


def reconstruir_indice() -> Indice:
    """Reconstrói o índice em memória. Não grava evento nem altera a fonte."""
    global _indice
    caminho = caminho_fonte()
    if caminho != (repo_root().resolve() / FONTE_RELATIVA):
        raise RegulamentoEstruturaError("Caminho da fonte divergente.")
    if not caminho.is_file():
        raise RegulamentoEstruturaError("Fonte do regulamento ausente.")
    texto = caminho.read_text(encoding="utf-8")
    indice = analisar(texto)
    from aurora.regulamento.catalog import validar_referencias

    validar_referencias(indice)
    _indice = indice
    logger.info(
        "Regulamento indexado: %s capítulos, %s artigos, %s unidades.",
        indice.capitulos,
        indice.artigos,
        len(indice.unidades),
    )
    return indice


def analisar(texto: str) -> Indice:
    unidades: list[Unidade] = []
    capitulos: list[str] = []
    artigos: list[str] = []
    capitulo_atual = ""
    artigo_atual = ""
    vistos: set[str] = set()

    for posicao, bloco in enumerate(_blocos(texto), start=1):
        if _TITULO.match(bloco) and not bloco.startswith("## "):
            continue
        capitulo = _CAPITULO.match(bloco)
        if capitulo:
            numero = capitulo.group(1)
            if numero in capitulos:
                raise RegulamentoEstruturaError(
                    f"Capítulo repetido na posição {posicao}."
                )
            capitulos.append(numero)
            capitulo_atual = numero
            artigo_atual = ""
            continue
        if not capitulo_atual:
            raise RegulamentoEstruturaError(
                f"Bloco fora de capítulo na posição {posicao}."
            )
        artigo = _ARTIGO.match(bloco)
        if artigo:
            numero = artigo.group(1)
            artigo_id = f"{capitulo_atual}/{numero}"
            _registrar(unidades, vistos, artigo_id, bloco, posicao)
            artigos.append(artigo_id)
            artigo_atual = artigo_id
            continue
        if not artigo_atual:
            raise RegulamentoEstruturaError(
                f"Subunidade fora de artigo na posição {posicao}."
            )
        inciso = _INCISO.match(bloco)
        if inciso:
            _registrar(
                unidades,
                vistos,
                f"{artigo_atual}/{inciso.group(1)}",
                bloco,
                posicao,
            )
            continue
        if _PARAGRAFO_UNICO.match(bloco):
            _registrar(
                unidades,
                vistos,
                f"{artigo_atual}/paragrafo-unico",
                bloco,
                posicao,
            )
            continue
        paragrafo = _PARAGRAFO.match(bloco)
        if paragrafo:
            _registrar(
                unidades,
                vistos,
                f"{artigo_atual}/p{paragrafo.group(1)}",
                bloco,
                posicao,
            )
            continue
        raise RegulamentoEstruturaError(f"Bloco não reconhecido na posição {posicao}.")

    if len(capitulos) != _CAPITULOS_ESPERADOS or len(artigos) != _ARTIGOS_ESPERADOS:
        raise RegulamentoEstruturaError(
            f"Estrutura divergente: {len(capitulos)} capítulos, {len(artigos)} artigos."
        )
    return Indice(
        unidades=tuple(unidades),
        capitulos=len(capitulos),
        artigos=len(artigos),
    )


def materializar(ids: frozenset[str] | set[str]) -> list[dict[str, str]]:
    """Devolve só as unidades pedidas, na ordem da fonte."""
    indice = indice_atual()
    escolhidas = [unidade for unidade in indice.unidades if unidade.id in ids]
    if len(escolhidas) != len(ids):
        raise RegulamentoEstruturaError("Autorização com referência ausente.")
    return [
        {"referencia": unidade.id, "texto": unidade.texto} for unidade in escolhidas
    ]


def expandir_artigo(artigo_id: str) -> tuple[str, ...]:
    """Subunidades de um artigo. Não segue remissão nem o restante do capítulo."""
    indice = indice_atual()
    prefixo = artigo_id + "/"
    ids = tuple(
        unidade.id
        for unidade in indice.unidades
        if unidade.id == artigo_id or unidade.id.startswith(prefixo)
    )
    if not ids:
        raise RegulamentoEstruturaError("Artigo ausente no índice.")
    return ids


def _registrar(
    unidades: list[Unidade],
    vistos: set[str],
    unidade_id: str,
    texto: str,
    posicao: int,
) -> None:
    if unidade_id in vistos:
        raise RegulamentoEstruturaError(f"Referência repetida na posição {posicao}.")
    vistos.add(unidade_id)
    unidades.append(Unidade(id=unidade_id, texto=texto))


def _blocos(texto: str) -> list[str]:
    blocos: list[str] = []
    atual: list[str] = []
    for linha in texto.splitlines():
        if not linha.strip():
            if atual:
                blocos.append("\n".join(atual))
                atual = []
            continue
        atual.append(linha)
    if atual:
        blocos.append("\n".join(atual))
    return blocos
