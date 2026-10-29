"""Endpoints de cartões e de gastos avulsos no cartão."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.db import obter_sessao
from schemas.cartoes import (
    CartaoEntrada, CartaoSaida, ContaFixaCartaoEntrada, GastoCartaoEntrada, GastoCartaoSaida,
)
from schemas.despesas import DespesaSaida
from schemas.pagamentos import Pagamento
from services import cartoes as servico
from services import pagamentos

router = APIRouter(tags=["cartões"])


@router.get("/cartoes", response_model=list[CartaoSaida])
def listar(sessao: Session = Depends(obter_sessao)):
    return servico.listar(sessao)


@router.post("/cartoes", response_model=CartaoSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: CartaoEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.criar(sessao, entrada)


@router.put("/cartoes/{cartao_id}", response_model=CartaoSaida)
def atualizar(cartao_id: int, entrada: CartaoEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.atualizar(sessao, cartao_id, entrada)


@router.delete("/cartoes/{cartao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(cartao_id: int, sessao: Session = Depends(obter_sessao)):
    servico.excluir(sessao, cartao_id)


@router.patch("/cartoes/{cartao_id}/pagamento")
def marcar_pagamento_fatura(
    cartao_id: int, entrada: Pagamento, sessao: Session = Depends(obter_sessao)
):
    """Marca/desmarca a fatura do cartão como paga no mês informado."""
    return pagamentos.marcar_fatura(
        sessao, cartao_id, entrada.ano, entrada.mes, entrada.pago, entrada.pago_em
    )


@router.post(
    "/cartoes/{cartao_id}/contas-fixas",
    response_model=DespesaSaida,
    status_code=status.HTTP_201_CREATED,
)
def criar_conta_fixa(
    cartao_id: int, entrada: ContaFixaCartaoEntrada, sessao: Session = Depends(obter_sessao)
):
    """Assinatura/conta que se repete todo mês no cartão."""
    return servico.criar_conta_fixa(sessao, cartao_id, entrada)


@router.get("/gastos-cartao", response_model=list[GastoCartaoSaida])
def listar_gastos(cartao_id: int | None = None, sessao: Session = Depends(obter_sessao)):
    return servico.listar_gastos(sessao, cartao_id)


@router.get("/gastos-cartao/{gasto_id}", response_model=GastoCartaoSaida)
def obter_gasto(gasto_id: int, sessao: Session = Depends(obter_sessao)):
    return servico.obter_gasto(sessao, gasto_id)


@router.post("/gastos-cartao", response_model=GastoCartaoSaida, status_code=status.HTTP_201_CREATED)
def criar_gasto(entrada: GastoCartaoEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.criar_gasto(sessao, entrada)


@router.put("/gastos-cartao/{gasto_id}", response_model=GastoCartaoSaida)
def atualizar_gasto(
    gasto_id: int, entrada: GastoCartaoEntrada, sessao: Session = Depends(obter_sessao)
):
    return servico.atualizar_gasto(sessao, gasto_id, entrada)


@router.delete("/gastos-cartao/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_gasto(gasto_id: int, sessao: Session = Depends(obter_sessao)):
    servico.excluir_gasto(sessao, gasto_id)
