"""Regras do cadastro de receitas."""

from sqlalchemy.orm import Session

from repositories.base import Repositorio
from repositories.modelos import Receita
from schemas.receitas import ReceitaEntrada
from services import responsaveis


def _repo(sessao: Session) -> Repositorio[Receita]:
    return Repositorio(sessao, Receita, "Receita")


def listar(sessao: Session) -> list[Receita]:
    return _repo(sessao).listar(Receita.recorrente.desc(), Receita.data_inicio.desc())


def criar(sessao: Session, entrada: ReceitaEntrada) -> Receita:
    responsaveis.validar(sessao, entrada.responsavel_id)
    return _repo(sessao).salvar(Receita(**entrada.model_dump()))


def atualizar(sessao: Session, receita_id: int, entrada: ReceitaEntrada) -> Receita:
    repo = _repo(sessao)
    receita = repo.obter(receita_id)
    responsaveis.validar(sessao, entrada.responsavel_id)
    for campo, valor in entrada.model_dump().items():
        setattr(receita, campo, valor)
    return repo.salvar(receita)


def excluir(sessao: Session, receita_id: int) -> None:
    repo = _repo(sessao)
    repo.excluir(repo.obter(receita_id))
