"""Fluxos de ponta a ponta contra o banco real (services + ORM + SQL)."""

from datetime import date
from decimal import Decimal

import pytest

from core.erros import ErroNegocio
from schemas.conferencias import ConferenciaEntrada
from schemas.despesas import DespesaEntrada, QuemPagaEntrada
from schemas.metas import MetaEntrada, MovimentoEntrada
from schemas.receitas import ReceitaEntrada
from schemas.responsaveis import ResponsavelEntrada
from services import conferencias, despesas, metas, painel, receitas, responsaveis
from repositories.modelos import Categoria, FormaPagamento
from services.calculos import Mes


def test_cadastros_aparecem_no_dashboard(sessao):
    carla = responsaveis.criar(sessao, ResponsavelEntrada(nome="Carla"))
    receitas.criar(sessao, ReceitaEntrada(
        descricao="Salário Carla", valor=Decimal("2000"), dia_recebimento=6,
        data_inicio=date(2026, 1, 1), responsavel_id=carla.id,
    ))
    casa = sessao.query(Categoria).filter_by(nome="Casa").one()
    pix = sessao.query(FormaPagamento).filter_by(nome="Pix").one()
    despesas.criar(sessao, DespesaEntrada(
        descricao="Aluguel", categoria_id=casa.id, forma_pagamento_id=pix.id,
        valor_mensal=Decimal("800"), primeira_cobranca=date(2026, 1, 10),
    ))
    conferencias.criar(sessao, ConferenciaEntrada(
        data=date(2026, 10, 6), saldos=[{"responsavel_id": carla.id, "valor": "1500"}],
    ))

    resumo = painel.dashboard(sessao, 2026, 10)
    assert resumo["total_receitas"] == Decimal("2000.00")
    assert resumo["total_despesas"] == Decimal("800.00")
    assert resumo["por_responsavel"][0]["nome"] == "Carla"
    assert resumo["conferencia"]["saldo_real"] == Decimal("1500.00")
    assert painel.periodo(sessao, "2026-09", "2026-10")["total_receitas"] == Decimal("4000.00")


def test_retirada_da_meta_nao_passa_do_guardado(sessao):
    meta = metas.criar(sessao, MetaEntrada(nome="Viagem"))
    metas.movimentar(sessao, meta.id, MovimentoEntrada(valor="300", data=date(2026, 10, 1)))
    metas.movimentar(sessao, meta.id, MovimentoEntrada(
        tipo="retirar", valor="100", data=date(2026, 10, 2), descricao="Emergência",
    ))
    with pytest.raises(ErroNegocio):
        metas.movimentar(sessao, meta.id, MovimentoEntrada(tipo="retirar", valor="200.01"))
    resumo = metas.painel(sessao, 2026, 10)["metas"][0]
    assert (resumo["guardado"], resumo["guardado_no_mes"], resumo["retirado_no_mes"]) == (
        Decimal("200.00"), Decimal("300.00"), Decimal("100.00"))


def test_trocar_quem_paga_nao_mexe_nos_meses_anteriores(sessao):
    ela = responsaveis.criar(sessao, ResponsavelEntrada(nome="Ela"))
    eu = responsaveis.criar(sessao, ResponsavelEntrada(nome="Eu"))
    casa = sessao.query(Categoria).filter_by(nome="Casa").one()
    pix = sessao.query(FormaPagamento).filter_by(nome="Pix").one()
    aluguel = despesas.criar(sessao, DespesaEntrada(
        descricao="Aluguel", categoria_id=casa.id, forma_pagamento_id=pix.id,
        valor_mensal=Decimal("1500"), primeira_cobranca=date(2026, 1, 10), responsavel_id=ela.id,
    ))

    def quem_paga(ano, mes):
        return despesas.obter(sessao, aluguel["id"], Mes(ano, mes))["responsavel_no_mes"]

    # Só novembro: dezembro volta para ela
    despesas.definir_quem_paga(sessao, aluguel["id"], QuemPagaEntrada(
        ano=2026, mes=11, responsavel_id=eu.id, so_este_mes=True))
    assert [quem_paga(2026, m) for m in (10, 11, 12)] == [ela.id, eu.id, ela.id]

    # De janeiro em diante: eu
    despesas.definir_quem_paga(sessao, aluguel["id"], QuemPagaEntrada(
        ano=2027, mes=1, responsavel_id=eu.id))
    assert [quem_paga(2026, 12), quem_paga(2027, 1), quem_paga(2027, 6)] == [ela.id, eu.id, eu.id]

    # Dezembro também eu, dali em diante: as trocas se juntam numa só
    resultado = despesas.definir_quem_paga(sessao, aluguel["id"], QuemPagaEntrada(
        ano=2026, mes=11, responsavel_id=eu.id))
    assert resultado["trocas"] == [{"a_partir_de": date(2026, 11, 1), "responsavel_id": eu.id}]
    assert quem_paga(2026, 10) == ela.id  # outubro (já pago por ela) não muda

    resumo = painel.dashboard(sessao, 2026, 10)
    assert {p["nome"]: p["despesas"] for p in resumo["por_responsavel"]}["Ela"] == Decimal("1500.00")

    # Voltar tudo para ela apaga as trocas
    resultado = despesas.definir_quem_paga(sessao, aluguel["id"], QuemPagaEntrada(
        ano=2026, mes=11, responsavel_id=ela.id))
    assert resultado["trocas"] == []
