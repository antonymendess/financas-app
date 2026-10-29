"""Schemas de anotações (lembretes e dívidas informais)."""

from datetime import date
from typing import Literal

from schemas.comum import (
    BaseModel, DataOpcional, DinheiroPositivoOpcional, DinheiroSaidaOpcional, Texto,
    TextoOpcional,
)

TipoAnotacao = Literal["A pagar", "A receber", "Lembrete"]


class AnotacaoEntrada(BaseModel):
    texto: Texto  # único campo obrigatório
    data: DataOpcional
    valor: DinheiroPositivoOpcional
    pessoa: TextoOpcional
    tipo: TipoAnotacao = "Lembrete"
    concluida: bool = False
    entra_no_saldo: bool = False


class AnotacaoSaida(BaseModel):
    id: int
    texto: str
    data: date | None
    valor: DinheiroSaidaOpcional
    pessoa: str | None
    tipo: str
    concluida: bool
    entra_no_saldo: bool


class ConclusaoAnotacao(BaseModel):
    concluida: bool = True
