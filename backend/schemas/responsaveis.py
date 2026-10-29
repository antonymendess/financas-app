"""Schemas das pessoas da casa (responsáveis)."""

from schemas.comum import BaseModel, Texto


class ResponsavelEntrada(BaseModel):
    nome: Texto


class ResponsavelSaida(BaseModel):
    id: int
    nome: str
