"""Endpoints de despesas."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.db import obter_sessao
from schemas.despesas import DespesaEntrada, DespesaSaida, QuemPagaEntrada
from schemas.pagamentos import Pagamento
from services import despesas as servico
from services import pagamentos
from services.calculos import Mes

router = APIRouter(prefix="/despesas", tags=["despesas"])


@router.get("", response_model=list[DespesaSaida])
def listar(
    ano: int | None = Query(default=None, ge=2000, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
    sessao: Session = Depends(obter_sessao),
):
    """Todas as despesas; vencimento/pagamento referentes ao mês `ano`/`mes` (padrão: atual)."""
    return servico.listar(sessao, Mes(ano, mes) if ano and mes else None)


@router.get("/{despesa_id}", response_model=DespesaSaida)
def obter(despesa_id: int, sessao: Session = Depends(obter_sessao)):
    return servico.obter(sessao, despesa_id)


@router.post("", response_model=DespesaSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: DespesaEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.criar(sessao, entrada)


@router.put("/{despesa_id}", response_model=DespesaSaida)
def atualizar(despesa_id: int, entrada: DespesaEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.atualizar(sessao, despesa_id, entrada)


@router.delete("/{despesa_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(despesa_id: int, sessao: Session = Depends(obter_sessao)):
    servico.excluir(sessao, despesa_id)


@router.put("/{despesa_id}/quem-paga", response_model=DespesaSaida)
def quem_paga(despesa_id: int, entrada: QuemPagaEntrada, sessao: Session = Depends(obter_sessao)):
    """Troca quem paga a conta a partir de um mês (só nele ou dele em diante)."""
    return servico.definir_quem_paga(sessao, despesa_id, entrada)


@router.patch("/{despesa_id}/pagamento")
def marcar_pagamento(despesa_id: int, entrada: Pagamento, sessao: Session = Depends(obter_sessao)):
    """Marca/desmarca a conta como paga no mês informado."""
    return pagamentos.marcar_despesa(
        sessao, despesa_id, entrada.ano, entrada.mes, entrada.pago, entrada.pago_em
    )
