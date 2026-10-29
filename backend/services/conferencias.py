"""Conferências com o saldo real do banco (o cálculo da previsão fica em projecao.py)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from repositories.base import Repositorio
from repositories.modelos import Conferencia, ConferenciaSaldo
from schemas.conferencias import ConferenciaEntrada
from services import responsaveis


def _repo(sessao: Session) -> Repositorio[Conferencia]:
    return Repositorio(sessao, Conferencia, "Conferência")


def listar(sessao: Session, limite: int = 24) -> list[Conferencia]:
    consulta = select(Conferencia).order_by(Conferencia.data.desc(), Conferencia.id.desc())
    return list(sessao.scalars(consulta.limit(limite)))


def criar(sessao: Session, entrada: ConferenciaEntrada) -> Conferencia:
    if entrada.junto:
        saldos, total = [], entrada.total
    else:
        for saldo in entrada.saldos:
            responsaveis.validar(sessao, saldo.responsavel_id)
        saldos = [ConferenciaSaldo(responsavel_id=s.responsavel_id, valor=s.valor)
                  for s in entrada.saldos]
        total = sum(s.valor for s in entrada.saldos)
    return _repo(sessao).salvar(Conferencia(
        data=entrada.data, junto=entrada.junto, total=total, saldos=saldos,
        ja_entrou=sorted(set(entrada.ja_entrou)),
    ))


def excluir(sessao: Session, conferencia_id: int) -> None:
    repo = _repo(sessao)
    repo.excluir(repo.obter(conferencia_id))
