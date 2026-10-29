"""Schemas das categorias de despesa."""

from typing import Annotated

from pydantic import Field

from schemas.comum import BaseModel

NomeCategoria = Annotated[str, Field(min_length=1, max_length=60)]


class CategoriaEntrada(BaseModel):
    nome: NomeCategoria


class CategoriaSaida(BaseModel):
    id: int
    nome: str
    despesas: int = 0  # contas cadastradas nesta categoria
    gastos: int = 0  # gastos avulsos no cartão
    protegida: bool = False  # "Outros": usada como padrão, não pode sair nem mudar de nome
