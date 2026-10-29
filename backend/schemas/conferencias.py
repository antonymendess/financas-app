"""Schemas da conferência com o saldo real do banco."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import Field, model_validator

from schemas.comum import BaseModel, DinheiroSaida
from services.calculos import hoje

# Saldo de conta pode ser negativo (cheque especial)
Saldo = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]
ChaveReceita = Annotated[str, Field(max_length=40)]


class SaldoPessoa(BaseModel):
    responsavel_id: int
    valor: Saldo


class ConferenciaEntrada(BaseModel):
    data: date = Field(default_factory=hoje)
    junto: bool = False  # true = um saldo só para a casa (em `total`)
    total: Saldo | None = None
    saldos: list[SaldoPessoa] = Field(default_factory=list, max_length=20)
    # Receitas que já caíram antes da data prevista ("receita:3", "comissao:7")
    ja_entrou: list[ChaveReceita] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def _validar(self):
        if self.junto and self.total is None:
            raise ValueError("Informe o saldo da conta.")
        if not self.junto:
            if not self.saldos:
                raise ValueError("Informe o saldo de cada pessoa.")
            ids = [s.responsavel_id for s in self.saldos]
            if len(ids) != len(set(ids)):
                raise ValueError("Cada pessoa só pode aparecer uma vez.")
        return self


class SaldoSaida(BaseModel):
    responsavel_id: int
    valor: DinheiroSaida


class ConferenciaSaida(BaseModel):
    id: int
    data: date
    junto: bool
    total: DinheiroSaida
    saldos: list[SaldoSaida]
    ja_entrou: list[str]
