"""Schemas de casa, membros e convites."""

from datetime import datetime
from typing import Annotated

from pydantic import Field

from schemas.comum import BaseModel, Texto

# Validação simples de formato (o e-mail é confirmado de verdade pelo Supabase no cadastro)
Email = Annotated[str, Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


class MembroSaida(BaseModel):
    id: int
    email: str
    papel: str


class EuSaida(BaseModel):
    email: str
    admin: bool
    papel: str
    casa_id: int
    casa_nome: str
    membros: list[MembroSaida]
    limite_membros: int


class CasaEntrada(BaseModel):
    nome: Texto


class ConviteMembroEntrada(BaseModel):
    email: Email


class ConviteClienteEntrada(BaseModel):
    email: Email
    nome_casa: str | None = Field(default=None, max_length=80)


class ConviteSaida(BaseModel):
    id: int
    token: str
    tipo: str
    email: str
    nome_casa: str | None
    criado_em: datetime
    expira_em: datetime
    aceito_em: datetime | None


class ConvitePublico(BaseModel):
    tipo: str
    email: str
    nome_casa: str | None
    situacao: str  # pendente | aceito | expirado
