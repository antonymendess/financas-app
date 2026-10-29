"""Listas usadas nos formulários (categorias, formas de pagamento, cartões, pessoas)."""

from schemas.comum import BaseModel


class Opcao(BaseModel):
    id: int
    nome: str


class FormaSaida(Opcao):
    cartao_id: int | None


class CartaoOpcao(Opcao):
    responsavel_id: int | None  # dono do cartão
    dia_fechamento: int | None  # para a tela mostrar em qual fatura o gasto cai
    dia_vencimento: int | None


class OpcoesSaida(BaseModel):
    categorias: list[Opcao]
    formas_pagamento: list[FormaSaida]
    cartoes: list[CartaoOpcao]
    responsaveis: list[Opcao]
