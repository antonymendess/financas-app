"""Utilidades puras de datas e dinheiro usadas pelas regras de negócio."""

import calendar
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_DOWN, Decimal
from zoneinfo import ZoneInfo

CENTAVO = Decimal("0.01")
# O servidor roda em UTC; "hoje" deve ser o dia no Brasil
FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")


def hoje() -> date:
    return datetime.now(FUSO_HORARIO).date()


@dataclass(frozen=True, order=True)
class Mes:
    """Um mês de calendário (ano + mês), com aritmética que respeita a virada do ano."""

    ano: int
    mes: int

    @classmethod
    def de(cls, data: date) -> "Mes":
        return cls(data.year, data.month)

    @property
    def indice(self) -> int:
        """Número sequencial do mês, útil para contar meses entre duas datas."""
        return self.ano * 12 + (self.mes - 1)

    def somar(self, quantidade: int) -> "Mes":
        ano, mes = divmod(self.indice + quantidade, 12)
        return Mes(ano, mes + 1)

    def meses_ate(self, outro: "Mes") -> int:
        return outro.indice - self.indice

    @property
    def ultimo_dia(self) -> int:
        return calendar.monthrange(self.ano, self.mes)[1]

    def data(self, dia: int) -> date:
        """Data neste mês; dias inexistentes (ex.: 31/02) viram o último dia do mês."""
        return date(self.ano, self.mes, min(dia, self.ultimo_dia))

    def contem(self, data: date | None) -> bool:
        return data is not None and data.year == self.ano and data.month == self.mes

    def __str__(self) -> str:
        return f"{self.ano:04d}-{self.mes:02d}"


def dividir_valor(total: Decimal, partes: int) -> list[Decimal]:
    """Divide igualmente; a diferença de centavos fica na última parcela.

    Ex.: 100,00 em 3 -> 33,33 + 33,33 + 33,34
    """
    if partes < 1:
        raise ValueError("A quantidade de parcelas deve ser maior que zero.")
    base = (total / partes).quantize(CENTAVO, rounding=ROUND_DOWN)
    return [base] * (partes - 1) + [total - base * (partes - 1)]
