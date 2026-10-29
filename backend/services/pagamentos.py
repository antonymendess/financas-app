"""Marcar/desmarcar contas e faturas como pagas em um mês."""

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core.erros import ErroNegocio
from repositories.base import Repositorio
from repositories.modelos import Cartao, Despesa, DespesaPagamento, FaturaPagamento
from services.calculos import Mes, hoje


def _competencia(ano: int, mes: int) -> date:
    if not 1 <= mes <= 12:
        raise ErroNegocio("Mês inválido.")
    return Mes(ano, mes).data(1)


def _alternar(sessao: Session, modelo, coluna, id_: int, ano: int, mes: int, pago: bool,
              pago_em: date | None) -> dict:
    competencia = _competencia(ano, mes)
    existente = sessao.scalar(
        select(modelo).where(coluna == id_, modelo.competencia == competencia)
    )
    if pago and existente is None:
        sessao.add(modelo(**{coluna.key: id_}, competencia=competencia, pago_em=pago_em or hoje()))
    elif not pago and existente is not None:
        sessao.execute(delete(modelo).where(modelo.id == existente.id))
    sessao.commit()
    return {"id": id_, "ano": ano, "mes": mes, "pago": pago}


def marcar_despesa(sessao: Session, despesa_id: int, ano: int, mes: int, pago: bool,
                   pago_em: date | None = None) -> dict:
    Repositorio(sessao, Despesa, "Despesa").obter(despesa_id)
    return _alternar(sessao, DespesaPagamento, DespesaPagamento.despesa_id, despesa_id,
                     ano, mes, pago, pago_em)


def marcar_fatura(sessao: Session, cartao_id: int, ano: int, mes: int, pago: bool,
                  pago_em: date | None = None) -> dict:
    Repositorio(sessao, Cartao, "Cartão").obter(cartao_id)
    return _alternar(sessao, FaturaPagamento, FaturaPagamento.cartao_id, cartao_id,
                     ano, mes, pago, pago_em)


def despesas_pagas_no_mes(sessao: Session, mes: Mes) -> set[int]:
    consulta = select(DespesaPagamento.despesa_id).where(
        DespesaPagamento.competencia == mes.data(1)
    )
    return set(sessao.scalars(consulta))


def faturas_pagas_no_mes(sessao: Session, mes: Mes) -> set[int]:
    consulta = select(FaturaPagamento.cartao_id).where(
        FaturaPagamento.competencia == mes.data(1)
    )
    return set(sessao.scalars(consulta))
