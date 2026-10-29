"""Endpoints das categorias de despesa."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.db import obter_sessao
from schemas.categorias import CategoriaEntrada, CategoriaSaida
from services import categorias as servico

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.get("", response_model=list[CategoriaSaida])
def listar(sessao: Session = Depends(obter_sessao)):
    """Categorias com quantos lançamentos usam cada uma."""
    return servico.listar(sessao)


@router.post("", response_model=CategoriaSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: CategoriaEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.criar(sessao, entrada)


@router.put("/{categoria_id}", response_model=CategoriaSaida)
def atualizar(categoria_id: int, entrada: CategoriaEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.atualizar(sessao, categoria_id, entrada)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    categoria_id: int,
    mover_para: int | None = Query(default=None, description="Categoria que recebe os lançamentos"),
    sessao: Session = Depends(obter_sessao),
):
    servico.excluir(sessao, categoria_id, mover_para)
