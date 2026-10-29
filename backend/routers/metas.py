"""Endpoints das metas de economia."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.db import obter_sessao
from schemas.metas import FechamentoMes, MetaEntrada, MetaSaida, MovimentoEntrada, MovimentoSaida
from services import metas as servico
from services.calculos import hoje

router = APIRouter(prefix="/metas", tags=["metas"])


@router.get("/painel")
def painel(
    ano: int | None = Query(default=None, ge=2000, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
    sessao: Session = Depends(obter_sessao),
):
    """Metas com progresso, quanto guardar no mês e histórico de 12 meses."""
    data_hoje = hoje()
    return servico.painel(sessao, ano or data_hoje.year, mes or data_hoje.month)


@router.post("", response_model=MetaSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: MetaEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.criar(sessao, entrada)


@router.put("/{meta_id}", response_model=MetaSaida)
def atualizar(meta_id: int, entrada: MetaEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.atualizar(sessao, meta_id, entrada)


@router.delete("/{meta_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(meta_id: int, sessao: Session = Depends(obter_sessao)):
    servico.excluir(sessao, meta_id)


@router.put("/{meta_id}/mes", status_code=status.HTTP_204_NO_CONTENT)
def fechar_mes(meta_id: int, entrada: FechamentoMes, sessao: Session = Depends(obter_sessao)):
    """Fecha o mês com o que deu para guardar (a diferença não fica pendente) ou reabre."""
    servico.fechar_mes(sessao, meta_id, entrada)


@router.get("/{meta_id}/movimentos", response_model=list[MovimentoSaida])
def movimentos(meta_id: int, sessao: Session = Depends(obter_sessao)):
    return servico.movimentos(sessao, meta_id)


@router.post(
    "/{meta_id}/movimentos", response_model=MovimentoSaida, status_code=status.HTTP_201_CREATED
)
def movimentar(meta_id: int, entrada: MovimentoEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.movimentar(sessao, meta_id, entrada)


@router.delete("/movimentos/{movimento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_movimento(movimento_id: int, sessao: Session = Depends(obter_sessao)):
    servico.excluir_movimento(sessao, movimento_id)
