"""Endpoints de leitura: dashboard, projeção e listas para formulários."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db import obter_sessao
from repositories.modelos import Cartao, Categoria, FormaPagamento, Responsavel
from schemas.opcoes import OpcoesSaida
from services import painel as servico
from services.calculos import hoje

router = APIRouter(tags=["painel"])


@router.get("/dashboard")
def dashboard(
    ano: int | None = Query(default=None, ge=2000, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
    responsavel: str | None = Query(default=None, max_length=20),
    sessao: Session = Depends(obter_sessao),
):
    """Resumo completo de um mês (padrão: mês atual). `responsavel`: id, "conjunto" ou vazio."""
    data_hoje = hoje()
    return servico.dashboard(sessao, ano or data_hoje.year, mes or data_hoje.month, responsavel)


@router.get("/projecao")
def projecao(
    meses: int = Query(default=12, ge=1, le=36),
    ano: int | None = Query(default=None, ge=2000, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
    responsavel: str | None = Query(default=None, max_length=20),
    sessao: Session = Depends(obter_sessao),
):
    """Totais do mês inicial (padrão: atual) + `meses` seguintes."""
    return servico.projecao(sessao, meses, ano, mes, responsavel)


@router.get("/periodo")
def periodo(
    inicio: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    fim: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    responsavel: str | None = Query(default=None, max_length=20),
    sessao: Session = Depends(obter_sessao),
):
    """Soma dos meses de `inicio` a `fim` ("AAAA-MM"), opcionalmente de uma pessoa."""
    return servico.periodo(sessao, inicio, fim, responsavel)


@router.get("/opcoes", response_model=OpcoesSaida)
def opcoes(sessao: Session = Depends(obter_sessao)):
    """Categorias, formas de pagamento, cartões e pessoas para preencher os formulários."""
    return {
        "categorias": sessao.scalars(select(Categoria).order_by(Categoria.nome)).all(),
        "formas_pagamento": sessao.scalars(
            select(FormaPagamento).order_by(FormaPagamento.cartao_id.is_not(None), FormaPagamento.id)
        ).all(),
        "cartoes": sessao.scalars(select(Cartao).order_by(Cartao.nome)).all(),
        "responsaveis": sessao.scalars(select(Responsavel).order_by(Responsavel.nome)).all(),
    }
