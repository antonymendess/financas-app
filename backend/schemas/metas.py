"""Schemas das metas de economia e dos valores guardados nelas."""

from datetime import date
from typing import Literal

from pydantic import Field

from schemas.comum import (
    BaseModel, DataOpcional, Dinheiro, DinheiroPositivoOpcional, DinheiroSaida,
    DinheiroSaidaOpcional, Texto, TextoOpcional,
)


class MetaEntrada(BaseModel):
    """Cofrinho: nome, quanto quero juntar e até quando (os dois opcionais)."""

    nome: Texto
    valor_alvo: DinheiroPositivoOpcional  # vazio = guardar sem um valor final
    data_alvo: DataOpcional
    ativa: bool = True


class MetaSaida(BaseModel):
    id: int
    nome: str
    valor_alvo: DinheiroSaidaOpcional
    data_alvo: date | None
    ativa: bool


class MovimentoEntrada(BaseModel):
    tipo: Literal["guardar", "retirar"] = "guardar"
    valor: Dinheiro
    data: DataOpcional  # vazio = hoje
    descricao: TextoOpcional
    # Guardou menos que a regra e não quer deixar a diferença pendente no mês
    fechar_mes: bool = False


class FechamentoMes(BaseModel):
    ano: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    fechado: bool = True


class MovimentoSaida(BaseModel):
    id: int
    meta_id: int
    data: date
    valor: DinheiroSaida  # negativo = retirada
    descricao: str | None
