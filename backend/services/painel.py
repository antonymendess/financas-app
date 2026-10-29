"""Monta as respostas do dashboard e da projeção a partir de uma carga única do banco."""

from dataclasses import asdict

from sqlalchemy.orm import Session

from core.erros import ErroNegocio
from repositories.consultas import carregar_dados_financeiros
from services.calculos import Mes, hoje
from services.projecao import TODOS, projetar, resumo_do_mes, resumo_periodo

MAXIMO_MESES_PERIODO = 36


def ler_responsavel(valor: str | None):
    """Filtro da URL: vazio = todos, "conjunto" = sem pessoa, número = id da pessoa."""
    if valor is None or not valor.strip():
        return TODOS
    if valor == "conjunto":
        return None
    if valor.isdigit():
        return int(valor)
    raise ErroNegocio("Filtro de pessoa inválido.")


def ler_mes(texto: str) -> Mes:
    """ "AAAA-MM" -> Mes (o formato já é validado na rota)."""
    ano, mes = texto.split("-")
    return Mes(int(ano), int(mes))


def dashboard(sessao: Session, ano: int, mes: int, responsavel: str | None = None) -> dict:
    dados = carregar_dados_financeiros(sessao)
    return asdict(resumo_do_mes(dados, Mes(ano, mes), hoje(), ler_responsavel(responsavel)))


def projecao(
    sessao: Session, meses: int, ano: int | None = None, mes: int | None = None,
    responsavel: str | None = None,
) -> list[dict]:
    dados = carregar_dados_financeiros(sessao)
    data_hoje = hoje()
    inicio = Mes(ano, mes) if ano and mes else Mes.de(data_hoje)
    return projetar(dados, inicio, meses, data_hoje, ler_responsavel(responsavel))


def periodo(sessao: Session, inicio: str, fim: str, responsavel: str | None = None) -> dict:
    de, ate = ler_mes(inicio), ler_mes(fim)
    if ate < de:
        raise ErroNegocio("O mês final não pode ser antes do inicial.")
    if de.meses_ate(ate) + 1 > MAXIMO_MESES_PERIODO:
        raise ErroNegocio(f"Escolha um período de até {MAXIMO_MESES_PERIODO} meses.")
    dados = carregar_dados_financeiros(sessao)
    return resumo_periodo(dados, de, ate, hoje(), ler_responsavel(responsavel))
