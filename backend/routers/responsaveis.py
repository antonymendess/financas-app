"""Endpoints das pessoas da casa (responsáveis)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.db import obter_sessao
from schemas.responsaveis import ResponsavelEntrada, ResponsavelSaida
from services import responsaveis as servico

router = APIRouter(prefix="/responsaveis", tags=["responsáveis"])


@router.get("", response_model=list[ResponsavelSaida])
def listar(sessao: Session = Depends(obter_sessao)):
    return servico.listar(sessao)


@router.post("", response_model=ResponsavelSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: ResponsavelEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.criar(sessao, entrada)


@router.put("/{responsavel_id}", response_model=ResponsavelSaida)
def atualizar(
    responsavel_id: int, entrada: ResponsavelEntrada, sessao: Session = Depends(obter_sessao)
):
    return servico.atualizar(sessao, responsavel_id, entrada)


@router.post("/{responsavel_id}/assumir-comissoes")
def assumir_comissoes(responsavel_id: int, sessao: Session = Depends(obter_sessao)):
    """Comissões (e receitas de comissão) sem pessoa passam a ser desta pessoa."""
    return servico.assumir_comissoes(sessao, responsavel_id)


@router.delete("/{responsavel_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(responsavel_id: int, sessao: Session = Depends(obter_sessao)):
    servico.excluir(sessao, responsavel_id)
