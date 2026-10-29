"""Endpoints de comissões e pagamento de parcelas."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.db import obter_sessao
from schemas.comissoes import (
    ComissaoEntrada, ComissaoSaida, DataParcela, FechamentoNegociacao, NegociacaoEntrada,
    NegociacaoSaida, PagamentoParcela, ParcelaSaida,
)
from services import comissoes as servico
from services import negociacoes

router = APIRouter(prefix="/comissoes", tags=["comissões"])
router_negociacoes = APIRouter(prefix="/negociacoes", tags=["negociações"])


@router.get("", response_model=list[ComissaoSaida])
def listar(sessao: Session = Depends(obter_sessao)):
    return servico.listar(sessao)


@router.get("/{comissao_id}", response_model=ComissaoSaida)
def obter(comissao_id: int, sessao: Session = Depends(obter_sessao)):
    return servico.obter(sessao, comissao_id)


@router.post("", response_model=ComissaoSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: ComissaoEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.criar(sessao, entrada)


@router.put("/{comissao_id}", response_model=ComissaoSaida)
def atualizar(comissao_id: int, entrada: ComissaoEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.atualizar(sessao, comissao_id, entrada)


@router.delete("/{comissao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(comissao_id: int, sessao: Session = Depends(obter_sessao)):
    servico.excluir(sessao, comissao_id)


@router.patch("/parcelas/{parcela_id}", response_model=ParcelaSaida)
def marcar_pagamento(
    parcela_id: int, entrada: PagamentoParcela, sessao: Session = Depends(obter_sessao)
):
    """Marca ou desmarca uma parcela como recebida."""
    return servico.marcar_pagamento(sessao, parcela_id, entrada)


@router.patch("/parcelas/{parcela_id}/data", response_model=ParcelaSaida)
def alterar_data_parcela(
    parcela_id: int, entrada: DataParcela, sessao: Session = Depends(obter_sessao)
):
    """Ajusta a data prevista de uma parcela."""
    return servico.alterar_data(sessao, parcela_id, entrada.data_prevista)


# ----------------------------------------------------------------- negociações
@router_negociacoes.get("", response_model=list[NegociacaoSaida])
def listar_negociacoes(sessao: Session = Depends(obter_sessao)):
    return negociacoes.listar(sessao)


@router_negociacoes.post("", response_model=NegociacaoSaida, status_code=status.HTTP_201_CREATED)
def criar_negociacao(entrada: NegociacaoEntrada, sessao: Session = Depends(obter_sessao)):
    return negociacoes.criar(sessao, entrada)


@router_negociacoes.put("/{negociacao_id}", response_model=NegociacaoSaida)
def atualizar_negociacao(
    negociacao_id: int, entrada: NegociacaoEntrada, sessao: Session = Depends(obter_sessao)
):
    return negociacoes.atualizar(sessao, negociacao_id, entrada)


@router_negociacoes.delete("/{negociacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_negociacao(negociacao_id: int, sessao: Session = Depends(obter_sessao)):
    negociacoes.excluir(sessao, negociacao_id)


@router_negociacoes.post("/{negociacao_id}/fechar", response_model=ComissaoSaida)
def fechar_negociacao(
    negociacao_id: int, entrada: FechamentoNegociacao, sessao: Session = Depends(obter_sessao)
):
    """Cliente fechou: cria a comissão com as parcelas e marca como transferida."""
    return negociacoes.fechar(sessao, negociacao_id, entrada)
