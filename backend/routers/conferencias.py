"""Endpoints da conferência com o saldo real do banco."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.db import obter_sessao
from schemas.conferencias import ConferenciaEntrada, ConferenciaSaida
from services import conferencias as servico

router = APIRouter(prefix="/conferencias", tags=["conferências"])


@router.get("", response_model=list[ConferenciaSaida])
def listar(sessao: Session = Depends(obter_sessao)):
    """Últimas conferências (a mais recente primeiro)."""
    return servico.listar(sessao)


@router.post("", response_model=ConferenciaSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: ConferenciaEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.criar(sessao, entrada)


@router.delete("/{conferencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(conferencia_id: int, sessao: Session = Depends(obter_sessao)):
    servico.excluir(sessao, conferencia_id)
