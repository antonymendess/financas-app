"""Regra de datas e valores das parcelas de comissão.

Isolada aqui para ser fácil de alterar.

A comissão só é paga quando o cliente paga a parcela dele, ou seja, uma parcela
por mês:
- 1ª parcela: na data informada (sugestão: o próximo dia 15 ou 30 depois do
  fechamento, os dias em que a empresa paga).
- Seguintes: no DIA_PARCELAS_SEGUINTES de cada mês seguinte.
  Ex.: 1ª em 30/10 -> 2ª em 15/11 -> 3ª em 15/12.
As datas são previsões; cada parcela pode ter a data ajustada na tela.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from services.calculos import Mes, dividir_valor

# Dias em que a empresa paga comissões (usados para sugerir a 1ª parcela)
DIAS_DE_PAGAMENTO = (15, 30)
# Dia do mês em que caem as parcelas a partir da 2ª
DIA_PARCELAS_SEGUINTES = 15


@dataclass(frozen=True)
class ParcelaGerada:
    numero: int
    data_prevista: date
    valor: Decimal


def proxima_data_pagamento(depois_de: date) -> date:
    """Primeiro dia de pagamento (15 ou 30) estritamente posterior à data.

    Quando o mês não tem o dia 30 (fevereiro), usa o último dia do mês.
    """
    mes = Mes.de(depois_de)
    for _ in range(2):  # procura no mês atual e, se preciso, no seguinte
        for dia in DIAS_DE_PAGAMENTO:
            candidata = mes.data(dia)
            if candidata > depois_de:
                return candidata
        mes = mes.somar(1)
    raise AssertionError("inalcançável: sempre há um dia de pagamento no mês seguinte")


def data_parcela_seguinte(anterior: date) -> date:
    """Parcela seguinte: no dia fixo do mês seguinte ao da parcela anterior."""
    return Mes.de(anterior).somar(1).data(DIA_PARCELAS_SEGUINTES)


def gerar_parcelas(total: Decimal, num_parcelas: int, primeira: date) -> list[ParcelaGerada]:
    """Gera as parcelas de uma comissão (valores iguais, centavos na última)."""
    valores = dividir_valor(total, num_parcelas)
    parcelas = []
    data_atual = primeira
    for numero, valor in enumerate(valores, start=1):
        if numero > 1:
            data_atual = data_parcela_seguinte(data_atual)
        parcelas.append(ParcelaGerada(numero, data_atual, valor))
    return parcelas
