"""Endpoints de anotações."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.db import obter_sessao
from schemas.anotacoes import AnotacaoEntrada, AnotacaoSaida, ConclusaoAnotacao
from services import anotacoes as servico
from services.anotacoes import FiltroStatus

router = APIRouter(prefix="/anotacoes", tags=["anotações"])


@router.get("", response_model=list[AnotacaoSaida])
def listar(
    status: FiltroStatus = "pendentes",
    pessoa: str | None = None,
    sessao: Session = Depends(obter_sessao),
):
    return servico.listar(sessao, status, pessoa)


@router.get("/pessoas", response_model=list[str])
def pessoas(sessao: Session = Depends(obter_sessao)):
    return servico.pessoas(sessao)


@router.post("", response_model=AnotacaoSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: AnotacaoEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.criar(sessao, entrada)


@router.put("/{anotacao_id}", response_model=AnotacaoSaida)
def atualizar(anotacao_id: int, entrada: AnotacaoEntrada, sessao: Session = Depends(obter_sessao)):
    return servico.atualizar(sessao, anotacao_id, entrada)


@router.patch("/{anotacao_id}/concluir", response_model=AnotacaoSaida)
def concluir(
    anotacao_id: int, entrada: ConclusaoAnotacao, sessao: Session = Depends(obter_sessao)
):
    return servico.concluir(sessao, anotacao_id, entrada.concluida)


@router.delete("/{anotacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(anotacao_id: int, sessao: Session = Depends(obter_sessao)):
    servico.excluir(sessao, anotacao_id)
