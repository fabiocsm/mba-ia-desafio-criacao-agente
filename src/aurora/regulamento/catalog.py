"""Assuntos e intenções. Aponta referências estruturais, sem copiar a norma.

`unidades` lista só os trechos necessários. `artigos` pede o artigo inteiro,
caput e subunidades, sem puxar o capítulo nem seguir remissão.
"""

from __future__ import annotations

from dataclasses import dataclass

from aurora.regulamento.models import Indice
from aurora.regulamento.parser import RegulamentoEstruturaError


@dataclass(frozen=True)
class Assunto:
    id: str
    aliases: tuple[str, ...]
    ausencias: tuple[str, ...] = ()


@dataclass(frozen=True)
class Intencao:
    assunto: str
    grupos: tuple[tuple[str, ...], ...]
    unidades: tuple[str, ...] = ()
    artigos: tuple[str, ...] = ()


ASSUNTOS: tuple[Assunto, ...] = (
    Assunto("sindico", ("sindico", "subsindico", "conselho consultivo")),
    Assunto("aplicativo", ("aplicativo do condominio", "aplicativo")),
    Assunto(
        "uso_unidade",
        ("atividade comercial", "trabalho remoto", "home office", "temporada"),
    ),
    Assunto(
        "definicoes",
        ("definicao de morador", "definicao de condomino", "definicao de convidado"),
    ),
    Assunto("direitos", ("direitos dos moradores", "meus direitos")),
    Assunto("deveres", ("deveres dos moradores", "meus deveres")),
    Assunto("vedacoes_morador", ("fachada", "pelicula", "toldos")),
    Assunto("cota", ("cota condominial", "cota", "boleto")),
    Assunto("elevador", ("elevador", "elevadores")),
    Assunto("silencio", ("silencio", "barulho", "ruido", "sossego")),
    Assunto(
        "piscina",
        ("piscina", "piscinas", "nadar", "nado"),
        ("aula de mergulho", "aula de natacao", "hidroginastica"),
    ),
    Assunto("academia", ("academia",)),
    Assunto("brinquedoteca", ("brinquedoteca",)),
    Assunto("playground", ("playground",)),
    Assunto("salao", ("salao de festas", "salao")),
    Assunto("churrasqueira", ("churrasqueira",)),
    Assunto("quadra", ("quadra poliesportiva", "quadra")),
    Assunto("portaria", ("portaria", "encomenda", "encomendas", "entregador")),
    Assunto("camera", ("camera de monitoramento", "cameras", "monitoramento")),
    Assunto(
        "animais",
        (
            "cao",
            "cachorro",
            "animal de estimacao",
            "animais",
            "gato",
            "pet",
            "coleira",
        ),
    ),
    Assunto("mudanca", ("mudanca", "mudancas", "icamento")),
    Assunto("obra", ("obra", "reforma", "entulho")),
    Assunto(
        "garagem",
        ("garagem", "vaga de garagem", "bicicletario", "carregador"),
    ),
    Assunto("lixo", ("lixo", "reciclagem", "coleta seletiva", "residuo")),
    Assunto("penalidade", ("multa", "penalidade", "advertencia", "infracao")),
    Assunto(
        "vigencia",
        ("vigencia do regulamento", "alterar o regulamento", "entra em vigor"),
    ),
)


def _artigo(
    assunto: str, artigo: str, *grupos: tuple[str, ...]
) -> Intencao:
    return Intencao(assunto, grupos, artigos=(artigo,))


def _trechos(
    assunto: str, unidades: tuple[str, ...], *grupos: tuple[str, ...]
) -> Intencao:
    return Intencao(assunto, grupos, unidades=unidades)


_SINAIS_HORA = ("horario", "horas", "funciona", "abre", "fecha", "quando")
_DIAS_SEMANA = (
    "segunda",
    "terca",
    "quarta",
    "quinta",
    "sexta",
    "sabado",
    "dia de semana",
    "dias uteis",
)
_DIAS_DOMINGO = ("domingo", "feriado")
_HORAS_SEMANA = tuple(
    (dia, sinal) for dia in _DIAS_SEMANA for sinal in _SINAIS_HORA
)
_HORAS_DOMINGO = tuple(
    (dia, sinal) for dia in _DIAS_DOMINGO for sinal in _SINAIS_HORA
)

INTENCOES: tuple[Intencao, ...] = (
    _artigo("sindico", "I/3", ("atribuicao",), ("eleicao",), ("sindico",)),
    _artigo("aplicativo", "I/6", ("comunicacao",), ("aviso",), ("aplicativo",)),
    _artigo("uso_unidade", "I/2", ("comercial",), ("remoto",), ("temporada",)),
    _trechos("definicoes", ("I/4", "I/4/III"), ("morador",)),
    _trechos("definicoes", ("I/4", "I/4/II"), ("condomino",)),
    _trechos("definicoes", ("I/4", "I/4/VI"), ("convidado",)),
    _artigo("direitos", "II/8", ("direito",)),
    _artigo("deveres", "II/9", ("dever",)),
    _artigo("vedacoes_morador", "II/10", ("fachada",), ("pelicula",), ("toldo",)),
    _artigo("cota", "II/11", ("cota",), ("boleto",)),
    _artigo("elevador", "II/14", ("lotacao",), ("elevador social",), ("elevador",)),
    _artigo("silencio", "III/16", ("horario",), ("periodo",), ("silencio",)),
    _artigo("silencio", "III/15", ("sossego",), ("barulho",), ("ruido",)),
    _artigo("silencio", "III/17", ("festa",), ("reuniao",)),
    _trechos("piscina", ("IV/22", "IV/22/II"), *_HORAS_DOMINGO),
    _trechos("piscina", ("IV/22", "IV/22/I"), *_HORAS_SEMANA),
    _artigo("piscina", "IV/23", ("exame",), ("dermatologico",)),
    _artigo("piscina", "IV/24", ("crianca",), ("menor",), ("doze anos",)),
    _artigo("piscina", "IV/25", ("traje",), ("maio",), ("ducha",)),
    _artigo(
        "piscina", "IV/26", ("proibido",), ("nao posso",), ("nao pode",),
        ("vidro",), ("alimento",),
    ),
    _artigo("piscina", "IV/27", ("convidado",), ("convidados",)),
    _artigo("piscina", "IV/28", ("quimico",), ("tratamento",), ("filtro",)),
    _artigo("academia", "V/29", ("horario",), ("horas",), ("funciona",), ("idade",)),
    _artigo("academia", "V/30", ("roupa",), ("toalha",), ("tenis",)),
    _artigo("academia", "V/31", ("personal",), ("treinador",)),
    _artigo("academia", "V/32", ("alimento",), ("comer",), ("som",), ("peso no chao",)),
    _artigo("brinquedoteca", "V/33", ("horario",), ("horas",), ("crianca",), ("idade",)),
    _artigo("playground", "V/34", ("horario",), ("horas",), ("idade",)),
    _artigo("playground", "V/35", ("proibido",), ("brinquedo",)),
    _artigo("salao", "VI/36", ("reserva",), ("reservar",), ("evento",)),
    _artigo("salao", "VI/39", ("som",), ("volume",), ("musica",)),
    _artigo("salao", "VI/41", ("decoracao",), ("balao",)),
    _artigo("churrasqueira", "VI/36", ("reserva",), ("reservar",)),
    _artigo("churrasqueira", "VI/39", ("som",), ("volume",)),
    _artigo("quadra", "VI/36", ("reserva",), ("reservar",)),
    _artigo("quadra", "VI/42", ("bola",), ("rede",)),
    _artigo("portaria", "VII/44", ("acesso",), ("identificar",)),
    _artigo("portaria", "VII/45", ("visitante",), ("autorizacao",), ("autorizar",)),
    _artigo("portaria", "VII/47", ("encomenda",), ("entrega",), ("entregador",)),
    _artigo("camera", "VII/49", ("imagem",), ("gravacao",), ("camera",)),
    _artigo("portaria", "VII/51", ("emergencia",), ("incendio",), ("gas",)),
    _trechos(
        "animais",
        ("VIII/54",),
        ("transportar",),
        ("transporte",),
        ("circular",),
        ("coleira",),
        ("guia",),
        ("areas comuns",),
        ("focinheira",),
    ),
    _trechos("animais", ("IV/26", "IV/26/VI"), ("piscina",)),
    _artigo("animais", "VIII/55", ("elevador",)),
    _artigo(
        "animais", "VIII/56", ("salao",), ("academia",), ("jardim",),
        ("churrasqueira",), ("quadra",), ("brinquedoteca",), ("playground",),
    ),
    _artigo("animais", "VIII/57", ("dejeto",), ("xixi",), ("coco",)),
    _artigo("animais", "VIII/52", ("porte",), ("vacina",)),
    _artigo("animais", "VIII/53", ("cadastrar",), ("cadastro",), ("registrar",)),
    _artigo("animais", "VIII/60", ("espaco pet",)),
    _artigo("mudanca", "IX/61", ("antecedencia",), ("agendar",), ("agendamento",)),
    _artigo("mudanca", "IX/62", ("horario",), ("horas",), ("quando",)),
    _artigo("mudanca", "IX/63", ("elevador",)),
    _artigo("mudanca", "IX/65", ("embrulho",), ("embrulhar",), ("plastico",), ("bolha",)),
    _artigo("mudanca", "IX/68", ("icamento",), ("fachada",)),
    _artigo("obra", "X/69", ("comunicar",), ("projeto",), ("engenheiro",)),
    _artigo("obra", "X/70", ("horario",), ("horas",), ("barulho",)),
    _artigo("obra", "X/72", ("entulho",), ("material",), ("lona",)),
    _artigo("garagem", "XI/77", ("vaga",), ("estacionar",)),
    _artigo("garagem", "XI/78", ("velocidade",), ("km",), ("buzina",)),
    _artigo("garagem", "XI/79", ("proibido",), ("lavar",), ("oleo",)),
    _artigo("garagem", "XI/81", ("carregador",), ("eletrico",)),
    _artigo("garagem", "XI/82", ("bicicleta",), ("bicicletario",)),
    _artigo("lixo", "XII/83", ("saco",), ("lixeira",), ("depositar",)),
    _artigo("lixo", "XII/84", ("seletiva",), ("separar",), ("reciclagem",)),
    _artigo("lixo", "XII/85", ("pilha",), ("oleo",), ("lampada",), ("entulho",)),
    _artigo("lixo", "XII/87", ("eletronico",), ("celular",)),
    _artigo("penalidade", "XIII/88", ("multa",), ("advertencia",), ("penalidade",)),
    _artigo("penalidade", "XIII/90", ("defesa",), ("notificacao",)),
    _artigo("penalidade", "XIII/91", ("recurso",)),
    _artigo("vigencia", "XIV/93", ("alterar",), ("assembleia",)),
    _artigo("vigencia", "XIV/94", ("copia",), ("desconhecimento",)),
    _artigo("vigencia", "XIV/96", ("vigor",), ("vigencia",)),
)


def validar_referencias(indice: Indice) -> None:
    conhecidos = indice.ids()
    faltando: list[str] = []
    assuntos = {assunto.id for assunto in ASSUNTOS}
    for item in INTENCOES:
        if item.assunto not in assuntos:
            raise RegulamentoEstruturaError(
                f"Intenção sem assunto cadastrado ({item.assunto})."
            )
        if not item.unidades and not item.artigos:
            raise RegulamentoEstruturaError(
                f"Intenção sem referência ({item.assunto})."
            )
        for unidade_id in item.unidades:
            if unidade_id not in conhecidos:
                faltando.append(unidade_id)
        for artigo_id in item.artigos:
            if artigo_id not in conhecidos:
                faltando.append(artigo_id)
    if faltando:
        raise RegulamentoEstruturaError(
            "Referência de catálogo ausente: " + ", ".join(sorted(set(faltando)))
        )
