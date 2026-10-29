"""Pessoas da casa: separam de quem é cada receita e cada conta.

Sem responsável = "Conjunto" (dinheiro ou conta do casal). Ao excluir uma
pessoa, o banco limpa as referências (on delete set null): tudo dela volta
para o Conjunto, sem apagar nenhum lançamento.
"""

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from core.erros import ErroNegocio
from repositories.base import Repositorio
from repositories.modelos import Comissao, Receita, Responsavel
from schemas.responsaveis import ResponsavelEntrada


def _repo(sessao: Session) -> Repositorio[Responsavel]:
    return Repositorio(sessao, Responsavel, "Pessoa")


def validar(sessao: Session, responsavel_id: int | None) -> None:
    """Aceita vazio (Conjunto) ou uma pessoa cadastrada."""
    if responsavel_id is not None and not _repo(sessao).existe(responsavel_id):
        raise ErroNegocio("Pessoa inválida.")


def _nome_em_uso(sessao: Session, nome: str, ignorar_id: int | None = None) -> bool:
    existente = sessao.scalar(
        select(Responsavel).where(func.lower(Responsavel.nome) == nome.lower())
    )
    return existente is not None and existente.id != ignorar_id


def listar(sessao: Session) -> list[Responsavel]:
    return _repo(sessao).listar(Responsavel.nome)


def criar(sessao: Session, entrada: ResponsavelEntrada) -> Responsavel:
    if _nome_em_uso(sessao, entrada.nome):
        raise ErroNegocio("Já existe uma pessoa com esse nome.", 409)
    return _repo(sessao).salvar(Responsavel(nome=entrada.nome))


def atualizar(sessao: Session, responsavel_id: int, entrada: ResponsavelEntrada) -> Responsavel:
    repo = _repo(sessao)
    responsavel = repo.obter(responsavel_id)
    if _nome_em_uso(sessao, entrada.nome, ignorar_id=responsavel_id):
        raise ErroNegocio("Já existe uma pessoa com esse nome.", 409)
    responsavel.nome = entrada.nome
    return repo.salvar(responsavel)


def assumir_comissoes(sessao: Session, responsavel_id: int) -> dict:
    """Passa para a pessoa as comissões SEM responsável e as receitas lançadas delas.

    Só preenche o que está vazio: nada que já tem dono é alterado.
    """
    _repo(sessao).obter(responsavel_id)
    comissoes = sessao.execute(
        update(Comissao)
        .where(Comissao.responsavel_id.is_(None))
        .values(responsavel_id=responsavel_id)
    ).rowcount
    receitas = sessao.execute(
        update(Receita)
        .where(
            Receita.responsavel_id.is_(None),
            or_(Receita.comissao_parcela_id.is_not(None), Receita.tipo == "Comissão"),
        )
        .values(responsavel_id=responsavel_id)
    ).rowcount
    sessao.commit()
    return {"comissoes": comissoes, "receitas": receitas}


def excluir(sessao: Session, responsavel_id: int) -> None:
    repo = _repo(sessao)
    repo.excluir(repo.obter(responsavel_id))
