"""Dados da demonstração: recriados por inteiro sem tocar nas outras casas."""

import uuid
from datetime import date

from sqlalchemy import func, select

from repositories.modelos import Base, Casa, ComCasa, Despesa, Membro, Receita
from services import demo, metas, painel

HOJE = date(2026, 10, 18)


def test_todas_as_tabelas_da_casa_sao_limpas():
    com_casa = {m.class_.__tablename__ for m in Base.registry.mappers if issubclass(m.class_, ComCasa)}
    assert set(demo.TABELAS) == com_casa


def test_recriar_troca_os_dados_e_preserva_as_outras_casas(abrir, sessao, casa_legado):
    sessao.add(Receita(descricao="Da casa real", tipo="Salário", valor=1000, recorrente=True,
                       dia_recebimento=5, data_inicio=date(2026, 1, 1), casa_id=casa_legado))
    sessao.commit()
    sistema = abrir()
    usuario = uuid.uuid4()

    casa_id = demo.recriar(sistema, usuario, "demo@exemplo.com", HOJE)
    contagem = sistema.scalar(select(func.count()).select_from(Despesa).where(Despesa.casa_id == casa_id))
    da_demo = abrir(casa_id)
    da_demo.add(Despesa(descricao="Criada por visitante", categoria_id=1, forma_pagamento_id=1,
                        valor_mensal=10, primeira_cobranca=HOJE, casa_id=casa_id))
    da_demo.flush()
    da_demo.get(Casa, casa_id).nome = "Renomeada"

    assert demo.recriar(sistema, usuario, "demo@exemplo.com", HOJE) == casa_id
    depois = abrir(casa_id)
    assert depois.scalar(select(func.count()).select_from(Despesa)) == contagem
    assert depois.get(Casa, casa_id).nome == demo.NOME_CASA
    assert depois.scalar(select(Membro.papel).where(Membro.usuario_id == usuario)) == "dono"
    assert [r.descricao for r in sessao.scalars(select(Receita))] == ["Da casa real"]


def test_painel_da_demo_tem_movimento(abrir):
    casa_id = demo.recriar(abrir(), uuid.uuid4(), "demo@exemplo.com", HOJE)
    da_demo = abrir(casa_id)
    resumo = painel.dashboard(da_demo, HOJE.year, HOJE.month)
    assert resumo["total_receitas"] > 0 and resumo["total_despesas"] > 0
    assert len(metas.painel(da_demo, HOJE.year, HOJE.month)["metas"]) == 2
