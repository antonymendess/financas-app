"""Schemas de comissões e suas parcelas."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field

from schemas.comum import (
    BaseModel, DataOpcional, Dinheiro, DinheiroOpcional, DinheiroPositivoOpcional,
    DinheiroSaida, DinheiroSaidaOpcional, Parcelas, ResponsavelOpcional, Texto, TextoOpcional,
)
from services.calculos import hoje


class ComissaoEntrada(BaseModel):
    cliente: Texto
    telefone: TextoOpcional
    mes_fechamento: date = Field(default_factory=lambda: hoje().replace(day=1))
    valor_implantacao: Dinheiro
    mensalidade: DinheiroOpcional  # só informativa, não entra em cálculo
    percentual: Decimal = Field(default=Decimal("25"), gt=0, le=100, decimal_places=2)
    num_parcelas: Parcelas = 1
    data_primeira_parcela: date = Field(default_factory=hoje)
    observacao: TextoOpcional
    responsavel_id: ResponsavelOpcional  # quem recebe a comissão


class ParcelaSaida(BaseModel):
    id: int
    numero: int
    data_prevista: date
    valor: DinheiroSaida
    paga: bool
    paga_em: date | None
    receita_id: int | None  # receita lançada a partir desta parcela


class ComissaoSaida(BaseModel):
    id: int
    cliente: str
    telefone: str | None
    mes_fechamento: date
    valor_implantacao: DinheiroSaida
    mensalidade: DinheiroSaidaOpcional
    percentual: DinheiroSaida
    valor_comissao: DinheiroSaida
    num_parcelas: int
    data_primeira_parcela: date
    observacao: str | None
    responsavel_id: int | None
    total_recebido: DinheiroSaida
    total_a_receber: DinheiroSaida
    status: str  # Quitado | Em andamento | A iniciar
    pagas: int
    em_aberto: int
    valor_parcela: DinheiroSaida
    parcelas: list[ParcelaSaida]


class PagamentoParcela(BaseModel):
    paga: bool
    paga_em: DataOpcional  # se marcar como paga sem data, usa hoje
    lancar_receita: bool = False  # ao receber, cria a receita correspondente


class DataParcela(BaseModel):
    data_prevista: date


# ----------------------------------------------------------------- negociações
EtapaNegociacao = Literal[
    "Contato inicial", "Proposta enviada", "Em negociação", "Aguardando assinatura",
    "Fechado", "Perdido",
]
Probabilidade = Literal[10, 25, 50, 75, 90]


class NegociacaoEntrada(BaseModel):
    cliente: Texto
    telefone: TextoOpcional
    etapa: EtapaNegociacao = "Contato inicial"
    probabilidade: Probabilidade | None = None
    valor_implantacao: DinheiroPositivoOpcional
    mensalidade: DinheiroOpcional
    percentual: Decimal = Field(default=Decimal("25"), gt=0, le=100, decimal_places=2)
    num_parcelas: Parcelas = 1
    previsao_fechamento: DataOpcional
    ultimo_contato: DataOpcional
    proxima_acao: TextoOpcional
    observacao: TextoOpcional


class NegociacaoSaida(BaseModel):
    id: int
    cliente: str
    telefone: str | None
    etapa: str
    probabilidade: int | None
    valor_implantacao: DinheiroSaidaOpcional
    mensalidade: DinheiroSaidaOpcional
    percentual: DinheiroSaida
    num_parcelas: int
    previsao_fechamento: date | None
    ultimo_contato: date | None
    proxima_acao: str | None
    observacao: str | None
    comissao_id: int | None
    transferido_em: date | None
    comissao_prevista: DinheiroSaidaOpcional  # implantação × percentual
    comissao_ponderada: DinheiroSaidaOpcional  # prevista × probabilidade


class FechamentoNegociacao(BaseModel):
    data_primeira_parcela: DataOpcional  # padrão: próximo dia 15 ou 30
