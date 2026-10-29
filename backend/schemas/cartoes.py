"""Schemas de cartões e gastos avulsos no cartão."""

from datetime import date

from pydantic import Field

from schemas.comum import (
    BaseModel, Dia, Dinheiro, DinheiroSaida, Parcelas, ResponsavelOpcional, Texto,
)
from services.calculos import hoje


class CartaoEntrada(BaseModel):
    nome: Texto
    dia_fechamento: Dia
    dia_vencimento: Dia
    responsavel_id: ResponsavelOpcional  # dono do cartão


class CartaoSaida(BaseModel):
    id: int
    nome: str
    dia_fechamento: int | None
    dia_vencimento: int | None
    responsavel_id: int | None


class GastoCartaoEntrada(BaseModel):
    descricao: Texto
    cartao_id: int
    valor_total: Dinheiro
    num_parcelas: Parcelas = 1
    data_compra: date = Field(default_factory=hoje)
    categoria_id: int | None = None
    responsavel_id: ResponsavelOpcional  # vazio = dono do cartão


class ContaFixaCartaoEntrada(BaseModel):
    """Conta que se repete todo mês no cartão (assinatura, serviço...), sem data de fim."""

    descricao: Texto
    valor_mensal: Dinheiro
    data_inicio: date = Field(default_factory=hoje)  # data da 1ª compra/cobrança no cartão
    categoria_id: int | None = None
    responsavel_id: ResponsavelOpcional  # vazio = dono do cartão


class GastoCartaoSaida(BaseModel):
    id: int
    descricao: str
    cartao_id: int
    cartao: str
    valor_total: DinheiroSaida
    num_parcelas: int
    data_compra: date
    categoria_id: int | None
    categoria: str | None
    responsavel_id: int | None
    primeira_fatura: str  # "AAAA-MM": mês em que a 1ª parcela é paga
    sem_dias: bool  # cartão sem dias cadastrados (fatura estimada)
