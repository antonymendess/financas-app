"""Endpoints de receitas."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.db import obter_sessao
from schemas.receitas import ReceitaEntrada, ReceitaSaida
from services import receitas as servico

router = APIRouter(prefix="/receitas", tags=["receitas"])


@router.get("", response_model=list[ReceitaSaida])
def listar(sessao: Session = Depends(obter_sessao)):
    return servico.listar(sessao)


@router.post("", response_model=ReceitaSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: ReceitaEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.criar(sessao, entrada)


@router.put("/{receita_id}", response_model=ReceitaSaida)
def atualizar(receita_id: int, entrada: ReceitaEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.atualizar(sessao, receita_id, entrada)


@router.delete("/{receita_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(receita_id: int, sessao: Session = Depends(obter_sessao)):
    servico.excluir(sessao, receita_id)
