"""Operações genéricas de acesso ao banco, reaproveitadas por todas as tabelas."""

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.erros import NaoEncontrado
from repositories.modelos import Base

Modelo = TypeVar("Modelo", bound=Base)


class Repositorio(Generic[Modelo]):
    def __init__(self, sessao: Session, modelo: type[Modelo], nome_amigavel: str):
        self.sessao = sessao
        self.modelo = modelo
        self.nome_amigavel = nome_amigavel

    def listar(self, *ordem) -> list[Modelo]:
        consulta = select(self.modelo).order_by(*ordem or (self.modelo.id,))
        return list(self.sessao.scalars(consulta))

    def obter(self, id_: int) -> Modelo:
        """Busca pelo id ou devolve 404 com mensagem em português."""
        objeto = self.sessao.get(self.modelo, id_)
        if objeto is None:
            raise NaoEncontrado(self.nome_amigavel)
        return objeto

    def existe(self, id_: int | None) -> bool:
        return id_ is not None and self.sessao.get(self.modelo, id_) is not None

    def salvar(self, objeto: Modelo) -> Modelo:
        self.sessao.add(objeto)
        self.sessao.commit()
        self.sessao.refresh(objeto)
        return objeto

    def excluir(self, objeto: Modelo) -> None:
        self.sessao.delete(objeto)
        self.sessao.commit()
