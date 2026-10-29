"""Tipos reutilizados pelos schemas (dinheiro, dias, textos)."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BeforeValidator, ConfigDict, Field, PlainSerializer
from pydantic import BaseModel as _BaseModel


def _vazio_para_none(valor):
    """O front pode mandar "" em campos opcionais; tratamos como não informado."""
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


# Dinheiro sai no JSON como número (o front formata em R$)
_como_numero = PlainSerializer(float, return_type=float, when_used="json")
_como_numero_ou_nulo = PlainSerializer(
    lambda v: None if v is None else float(v), when_used="json"
)

# Nos tipos opcionais, os limites (ge, le, max_length...) ficam DENTRO do tipo
# não nulo. Assim um campo enviado como null é aceito como "não informado"
# em vez de quebrar a validação.
_Valor = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]

Dinheiro = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2), _como_numero]
DinheiroOpcional = Annotated[
    Annotated[_Valor, Field(ge=0)] | None,
    BeforeValidator(_vazio_para_none),
    Field(default=None),
    _como_numero_ou_nulo,
]
DinheiroPositivoOpcional = Annotated[
    Annotated[_Valor, Field(gt=0)] | None,
    BeforeValidator(_vazio_para_none),
    Field(default=None),
    _como_numero_ou_nulo,
]
DinheiroSaida = Annotated[Decimal, _como_numero]
DinheiroSaidaOpcional = Annotated[Decimal | None, _como_numero_ou_nulo]

Dia = Annotated[
    Annotated[int, Field(ge=1, le=31)] | None,
    BeforeValidator(_vazio_para_none),
    Field(default=None),
]
Parcelas = Annotated[int, Field(ge=1, le=600)]
ParcelasOpcional = Annotated[Parcelas | None, BeforeValidator(_vazio_para_none), Field(default=None)]
DataOpcional = Annotated[date | None, BeforeValidator(_vazio_para_none), Field(default=None)]
# Pessoa da casa; vazio = "Conjunto"
ResponsavelOpcional = Annotated[int | None, BeforeValidator(_vazio_para_none), Field(default=None)]
Texto = Annotated[str, Field(min_length=1, max_length=300)]
TextoOpcional = Annotated[
    Annotated[str, Field(max_length=2000)] | None,
    BeforeValidator(_vazio_para_none),
    Field(default=None),
]


class BaseModel(_BaseModel):
    """Base comum: remove espaços das pontas dos textos e lê objetos do ORM."""

    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)
