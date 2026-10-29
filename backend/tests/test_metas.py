"""Testes das metas no formato cofrinho (funções puras, sem banco)."""

from datetime import date
from decimal import Decimal

from schemas.metas import MetaEntrada
from services.calculos import Mes
from services.metas import MetaDados, montar_painel, resumo_meta

D = Decimal
OUT = Mes(2026, 10)


def test_cofrinho_so_precisa_do_nome():
    meta = MetaEntrada(nome="Viagem")
    assert meta.valor_alvo is None and meta.data_alvo is None and meta.ativa


def test_progresso_falta_e_marco():
    meta = MetaDados(1, "Viagem", valor_alvo=D("1000"))
    r = resumo_meta(meta, [(date(2026, 9, 5), D("300")), (date(2026, 10, 5), D("260"))], OUT)
    assert r["guardado"] == D("560")
    assert r["guardado_no_mes"] == D("260")
    assert r["falta"] == D("440")
    assert r["progresso"] == 0.56
    assert r["marco"] == 50
    assert not r["concluida"]


def test_retirada_desconta_do_guardado():
    meta = MetaDados(1, "Reserva", valor_alvo=D("1000"))
    r = resumo_meta(meta, [(date(2026, 9, 5), D("500")), (date(2026, 10, 1), D("-200"))], OUT)
    assert r["guardado"] == D("300")
    assert r["retirado_no_mes"] == D("200")


def test_retirada_nao_estraga_o_mes_o_ritmo_nem_a_sequencia():
    meta = MetaDados(1, "Reserva")
    movimentos = [(date(2026, 9, 5), D("500")), (date(2026, 10, 1), D("500")),
                  (date(2026, 10, 20), D("-500"))]
    r = resumo_meta(meta, movimentos, OUT)
    assert r["guardado"] == D("500")
    assert r["guardado_no_mes"] == D("500")  # guardou em outubro, mesmo tendo tirado
    assert r["retirado_no_mes"] == D("500")
    assert r["ritmo"] == D("500.00")
    assert r["sequencia"] == 2


def test_ritmo_e_previsao_pela_media_desde_o_primeiro_valor():
    meta = MetaDados(1, "Viagem", valor_alvo=D("1000"))
    # ago, set e out: 300 em 3 meses = 100/mês; faltam 700 -> 7 meses depois de out
    movimentos = [(date(2026, 8, 1), D("100")), (date(2026, 9, 1), D("100")),
                  (date(2026, 10, 1), D("100"))]
    r = resumo_meta(meta, movimentos, OUT)
    assert r["ritmo"] == D("100.00")
    assert r["previsao"] == "2027-05"
    assert r["sequencia"] == 3


def test_ritmo_usa_no_maximo_os_ultimos_6_meses():
    meta = MetaDados(1, "Reserva")
    movimentos = [(date(2025, 1, 1), D("6000")), (date(2026, 10, 1), D("600"))]
    assert resumo_meta(meta, movimentos, OUT)["ritmo"] == D("100.00")


def test_quanto_precisa_por_mes_para_a_data():
    meta = MetaDados(1, "Reserva", valor_alvo=D("1200"), data_alvo=date(2027, 3, 1))
    r = resumo_meta(meta, [], OUT)
    assert r["precisa_por_mes"] == D("200.00")  # out a mar = 6 meses
    assert r["ritmo"] is None
    assert r["no_ritmo"] is False


def test_sequencia_nao_quebra_se_ainda_nao_guardou_no_mes_atual():
    meta = MetaDados(1, "Reserva")
    movimentos = [(date(2026, 8, 1), D("50")), (date(2026, 9, 1), D("50"))]
    assert resumo_meta(meta, movimentos, OUT)["sequencia"] == 2


def test_meta_concluida():
    meta = MetaDados(1, "Celular", valor_alvo=D("500"))
    r = resumo_meta(meta, [(date(2026, 10, 1), D("600"))], OUT)
    assert r["concluida"] and r["falta"] == D("0") and r["progresso"] == 1.0 and r["marco"] == 100


def test_painel_soma_metas_e_historico():
    metas = [MetaDados(1, "Viagem", valor_alvo=D("1000")),
             MetaDados(2, "Reserva", valor_alvo=D("3000"))]
    movimentos = [(1, date(2026, 10, 2), D("250")), (1, date(2026, 10, 9), D("-50")),
                  (2, date(2026, 9, 2), D("800"))]
    painel = montar_painel(metas, movimentos, OUT)
    assert painel["guardado_total"] == D("1000")
    assert painel["guardado_no_mes"] == D("250")
    assert painel["retirado_no_mes"] == D("50")
    assert painel["alvo_total"] == D("4000")
    assert painel["progresso_total"] == 0.25
    assert len(painel["historico"]) == 12
    assert painel["historico"][-1] == {"ano": 2026, "mes": 10, "guardado": D("250"), "retirado": D("50")}
