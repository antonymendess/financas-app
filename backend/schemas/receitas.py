"""Schemas de receitas."""

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from schemas.comum import (
    BaseModel, DataOpcional, Dia, Dinheiro, DinheiroSaida, ResponsavelOpcional, Texto,
)
from services.calculos import hoje

TipoReceita = Literal["Salário", "Extra", "Comissão", "Outros"]


class ReceitaEntrada(BaseModel):
    descricao: Texto
    tipo: TipoReceita = "Salário"
    valor: Dinheiro
    recorrente: bool = True
    dia_recebimento: Dia
    data_inicio: date = Field(default_factory=hoje)
    data_fim: DataOpcional
    responsavel_id: ResponsavelOpcional

    @model_validator(mode="after")
    def _validar_periodo(self):
        if self.data_fim and self.data_fim < self.data_inicio:
            raise ValueError("A data de fim não pode ser antes da data de início.")
        return self


class ReceitaSaida(BaseModel):
    id: int
    descricao: str
    tipo: str
    valor: DinheiroSaida
    recorrente: bool
    dia_recebimento: int | None
    data_inicio: date
    data_fim: date | None
    comissao_parcela_id: int | None  # receita lançada a partir de uma comissão
    responsavel_id: int | None
