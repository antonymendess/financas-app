"""Schemas de despesas (contas fixas e parceladas)."""

from datetime import date

from pydantic import Field

from schemas.comum import (
    BaseModel, DataOpcional, Dia, Dinheiro, DinheiroSaida, DinheiroSaidaOpcional,
    ParcelasOpcional, ResponsavelOpcional, Texto, TextoOpcional,
)
from services.calculos import hoje


class DespesaEntrada(BaseModel):
    descricao: Texto
    categoria_id: int
    forma_pagamento_id: int
    valor_mensal: Dinheiro
    num_parcelas: ParcelasOpcional  # vazio = conta fixa
    primeira_cobranca: date = Field(default_factory=hoje)
    cancelada_em: DataOpcional
    dia_vencimento: Dia
    observacao: TextoOpcional
    responsavel_id: ResponsavelOpcional  # vazio = conjunto (ou o dono do cartão)


class QuemPagaEntrada(BaseModel):
    """Quem paga a conta a partir de um mês (os meses anteriores não mudam)."""

    ano: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    responsavel_id: ResponsavelOpcional  # vazio = conjunto
    so_este_mes: bool = False  # True = no mês seguinte volta quem pagava antes


class TrocaSaida(BaseModel):
    a_partir_de: date
    responsavel_id: int | None


class SituacaoSaida(BaseModel):
    status: str
    pagas: int | None
    faltam: int | None
    ainda_devo: DinheiroSaidaOpcional
    termina_em: str | None


class DespesaSaida(BaseModel):
    id: int
    descricao: str
    categoria_id: int
    categoria: str
    forma_pagamento_id: int
    forma: str
    cartao_id: int | None
    valor_mensal: DinheiroSaida
    num_parcelas: int | None
    primeira_cobranca: date
    cancelada_em: date | None
    dia_vencimento: int | None
    observacao: str | None
    responsavel_id: int | None
    situacao: SituacaoSaida
    # Referentes ao mês consultado (padrão: o atual)
    vencimento_mes_atual: date | None  # None = não cobra neste mês
    pago_mes_atual: bool  # no cartão: a fatura do mês foi paga
    parcela_no_mes: int | None
    responsavel_no_mes: int | None  # quem paga no mês consultado
    trocas: list[TrocaSaida]  # trocas de quem paga, por mês
