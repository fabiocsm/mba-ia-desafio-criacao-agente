"""Reservas próprias, cancelamento e efeito pago na mesma transação.

A identidade vem da sessão. A taxa vem do cadastro. O índice único parcial
decide a exclusividade no instante da gravação. Conflito de área/data vira
indisponibilidade, sem ler a reserva vencedora.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from aurora.storage.codigos import emitir_codigo
from aurora.storage.database import get_engine
from aurora.storage.database import transacao_escrita

_INDISPONIVEL = "indisponivel"


def data_civil(valor: str) -> bool:
    if len(valor) != 10 or valor[4] != "-" or valor[7] != "-":
        return False
    try:
        datetime.strptime(valor, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _ocupacao(exc: IntegrityError) -> bool:
    texto = str(exc.orig).lower()
    return "reserva.area" in texto or "reserva_ativa_area_data" in texto


def taxa_da_area(area_id: str) -> int | None:
    with get_engine().connect() as connection:
        valor = connection.execute(
            text("SELECT taxa_centavos FROM area WHERE id = :id"),
            {"id": area_id},
        ).scalar()
    if valor is None:
        return None
    return int(valor)


def _taxa(connection: Connection, area_id: str) -> int | None:
    valor = connection.execute(
        text("SELECT taxa_centavos FROM area WHERE id = :id"),
        {"id": area_id},
    ).scalar()
    if valor is None:
        return None
    return int(valor)


def reservar_gratuita(apartamento: str, area_id: str, data: str) -> dict[str, str]:
    """Efetiva reserva de taxa zero. Não cria proposta nem pendência."""
    if not data_civil(data):
        return {"erro": "Área ou data inválida."}
    with transacao_escrita() as connection:
        taxa = _taxa(connection, area_id)
        if taxa is None:
            return {"erro": "Área ou data inválida."}
        if taxa != 0:
            return {"resultado": "nao_autorizada"}
        connection.exec_driver_sql("SAVEPOINT reserva_gratuita")
        try:
            codigo = emitir_codigo(connection)
            connection.execute(
                text(
                    """
                    INSERT INTO reserva (
                        codigo, apartamento, area, data, cancelada, cancelada_em
                    ) VALUES (
                        :codigo, :apartamento, :area, :data, 0, NULL
                    )
                    """
                ),
                {
                    "codigo": codigo,
                    "apartamento": apartamento,
                    "area": area_id,
                    "data": data,
                },
            )
            connection.exec_driver_sql("RELEASE SAVEPOINT reserva_gratuita")
        except IntegrityError as exc:
            connection.exec_driver_sql("ROLLBACK TO SAVEPOINT reserva_gratuita")
            connection.exec_driver_sql("RELEASE SAVEPOINT reserva_gratuita")
            if _ocupacao(exc):
                return {"resultado": _INDISPONIVEL}
            raise
    return {
        "resultado": "reservada",
        "codigo": codigo,
        "area": area_id,
        "data": data,
    }


def cancelar_propria(
    apartamento: str,
    *,
    codigo: str | None = None,
    area_id: str | None = None,
    data: str | None = None,
) -> dict[str, str]:
    """UPDATE filtrado pelo apartamento. Ausente e alheio têm o mesmo retorno.

    C212: consultas e cancelamentos próprios filtram apartamento antes de
    materializar dados.
    """
    agora = datetime.now(timezone.utc).isoformat()
    with transacao_escrita() as connection:
        if codigo:
            consulta = text(
                """
                UPDATE reserva
                SET cancelada = 1, cancelada_em = :agora
                WHERE codigo = :codigo
                  AND apartamento = :apartamento
                  AND cancelada = 0
                RETURNING codigo, area, data
                """
            )
            parametros = {
                "agora": agora,
                "codigo": codigo,
                "apartamento": apartamento,
            }
        elif area_id and data and data_civil(data):
            consulta = text(
                """
                UPDATE reserva
                SET cancelada = 1, cancelada_em = :agora
                WHERE area = :area
                  AND data = :data
                  AND apartamento = :apartamento
                  AND cancelada = 0
                RETURNING codigo, area, data
                """
            )
            parametros = {
                "agora": agora,
                "area": area_id,
                "data": data,
                "apartamento": apartamento,
            }
        else:
            return {"resultado": "nao_encontrada"}
        linha = connection.execute(consulta, parametros).mappings().first()
    if linha is None:
        return {"resultado": "nao_encontrada"}
    return {
        "resultado": "cancelada",
        "codigo": linha["codigo"],
        "area": linha["area"],
        "data": linha["data"],
    }


def validar_parametros_reserva(parametros: dict) -> dict[str, str | int]:
    """Congela área, data e taxa real. Taxa zero não entra em confirmação."""
    area = parametros.get("area")
    data = parametros.get("data")
    taxa = parametros.get("taxa_centavos")
    if (
        not isinstance(area, str)
        or not area
        or not isinstance(data, str)
        or not data_civil(data)
        or isinstance(taxa, bool)
        or not isinstance(taxa, int)
        or taxa <= 0
    ):
        raise ValueError("Parâmetros de reserva inválidos.")
    real = taxa_da_area(area)
    if real is None or real != taxa:
        raise ValueError("Parâmetros de reserva inválidos.")
    return {"area": area, "data": data, "taxa_centavos": taxa}


def executar_reserva_paga(
    connection: Connection,
    apartamento: str,
    parametros: dict,
    proposta_id: str,
    session_id: str,
) -> dict[str, str]:
    """Insere a reserva com os parâmetros já congelados. Não faz commit.

    A violação do índice de área/data desfaz só o savepoint da emissão.
    Outros erros sobem sem serem tratados como ocupação. proposta_id e
    session_id são a correlação canônica do consumo; a reserva não os grava.
    """
    if not proposta_id or not session_id or not apartamento:
        raise RuntimeError("Proposta ausente no consumo.")
    area = str(parametros["area"])
    data = str(parametros["data"])
    connection.exec_driver_sql("SAVEPOINT reserva_paga")
    try:
        codigo = emitir_codigo(connection)
        connection.execute(
            text(
                """
                INSERT INTO reserva (
                    codigo, apartamento, area, data, cancelada, cancelada_em
                ) VALUES (
                    :codigo, :apartamento, :area, :data, 0, NULL
                )
                """
            ),
            {
                "codigo": codigo,
                "apartamento": apartamento,
                "area": area,
                "data": data,
            },
        )
        connection.exec_driver_sql("RELEASE SAVEPOINT reserva_paga")
    except IntegrityError as exc:
        connection.exec_driver_sql("ROLLBACK TO SAVEPOINT reserva_paga")
        connection.exec_driver_sql("RELEASE SAVEPOINT reserva_paga")
        if _ocupacao(exc):
            return {"resultado": _INDISPONIVEL}
        raise
    return {
        "resultado": "reservada",
        "codigo": codigo,
        "area": area,
        "data": data,
    }
