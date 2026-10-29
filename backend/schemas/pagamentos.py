"""Schema para marcar uma conta ou fatura como paga em um mês."""

from pydantic import Field

from schemas.comum import BaseModel, DataOpcional


class Pagamento(BaseModel):
    ano: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    pago: bool = True
    pago_em: DataOpcional  # padrão: hoje
