"""Regras das anotações (lembretes e dívidas informais)."""

from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from repositories.base import Repositorio
from repositories.modelos import Anotacao
from schemas.anotacoes import AnotacaoEntrada

FiltroStatus = Literal["pendentes", "concluidas", "todas"]


def _repo(sessao: Session) -> Repositorio[Anotacao]:
    return Repositorio(sessao, Anotacao, "Anotação")


def listar(sessao: Session, status: FiltroStatus = "pendentes", pessoa: str | None = None):
    consulta = select(Anotacao).order_by(
        Anotacao.data.asc().nulls_last(), Anotacao.id.desc()
    )
    if status == "pendentes":
        consulta = consulta.where(Anotacao.concluida.is_(False))
    elif status == "concluidas":
        consulta = consulta.where(Anotacao.concluida.is_(True))
    if pessoa:
        consulta = consulta.where(Anotacao.pessoa.ilike(f"%{pessoa.strip()}%"))
    return list(sessao.scalars(consulta))


def pessoas(sessao: Session) -> list[str]:
    """Nomes já usados, para o filtro e o autocompletar do front."""
    consulta = select(Anotacao.pessoa).where(Anotacao.pessoa.is_not(None)).distinct()
    return sorted(sessao.scalars(consulta), key=str.lower)


def criar(sessao: Session, entrada: AnotacaoEntrada) -> Anotacao:
    return _repo(sessao).salvar(Anotacao(**entrada.model_dump()))


def atualizar(sessao: Session, anotacao_id: int, entrada: AnotacaoEntrada) -> Anotacao:
    repo = _repo(sessao)
    anotacao = repo.obter(anotacao_id)
    for campo, valor in entrada.model_dump().items():
        setattr(anotacao, campo, valor)
    return repo.salvar(anotacao)


def concluir(sessao: Session, anotacao_id: int, concluida: bool) -> Anotacao:
    repo = _repo(sessao)
    anotacao = repo.obter(anotacao_id)
    anotacao.concluida = concluida
    return repo.salvar(anotacao)


def excluir(sessao: Session, anotacao_id: int) -> None:
    repo = _repo(sessao)
    repo.excluir(repo.obter(anotacao_id))
