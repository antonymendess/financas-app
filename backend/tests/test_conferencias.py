"""Testes da conferência com o saldo real do banco (funções puras, sem banco)."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas.conferencias import ConferenciaEntrada
from services.calculos import Mes
from services.dominio import (
    ConferenciaDados, DadosFinanceiros, DespesaDados, ParcelaComissaoDados, ReceitaDados,
    ResponsavelDados,
)
from services.projecao import calcular_mes

D = Decimal
OUT = Mes(2026, 10)
HOJE = date(2026, 10, 9)
CARLA, BRUNO = ResponsavelDados(1, "Carla"), ResponsavelDados(2, "Bruno")


def conta(id_, descricao, valor, dia=10, responsavel_id=None):
    return DespesaDados(id_, descricao, D(valor), date(2026, 1, dia), dia_vencimento=dia,
                        responsavel_id=responsavel_id)


def dados(*conferencias, pagas_em=None):
    pagas_em = pagas_em or {}
    return DadosFinanceiros(
        responsaveis=[CARLA, BRUNO],
        receitas=[
            ReceitaDados(1, "Salário Carla", D("2000.00"), date(2026, 1, 6), dia_recebimento=6,
                         responsavel_id=1),
            ReceitaDados(2, "Salário Bruno", D("3000.00"), date(2026, 1, 15),
                         dia_recebimento=15, responsavel_id=2),
        ],
        parcelas_comissao=[
            ParcelaComissaoDados(1, 1, "Acme", 2, 3, date(2026, 10, 15), D("500.00"),
                                 responsavel_id=2),
        ],
        despesas=[
            conta(1, "Aluguel", "1000.00", dia=5),  # conjunto
            conta(2, "Curso", "300.00", responsavel_id=2),
            conta(3, "Academia", "100.00", responsavel_id=1),
        ],
        despesas_pagas={chave for chave in pagas_em},
        despesas_pagas_em=pagas_em,
        conferencias=list(conferencias),
    )


def test_sem_conferencia_no_mes_nao_ha_previsao_pelo_banco():
    assert calcular_mes(dados(), OUT, HOJE).conferencia is None


def test_sobra_parte_do_saldo_real_mais_o_que_entra_menos_o_que_falta_pagar():
    conf = ConferenciaDados(1, date(2026, 10, 6), D("1500.00"), junto=True)
    # Aluguel pago dia 5 (antes da conferência): já tinha saído do saldo
    c = calcular_mes(dados(conf, pagas_em={(1, OUT): date(2026, 10, 5)}), OUT, HOJE).conferencia
    assert {x["descricao"] for x in c["a_entrar"]} == {"Salário Bruno", "Comissão Acme (2/3)"}
    assert c["total_a_entrar"] == D("3500.00")
    assert c["a_entrar_previsto"] == D("500.00")
    assert c["total_a_pagar"] == D("400.00")  # curso + academia
    assert c["sobra"] == D("4600.00")  # 1500 + 3500 - 400
    assert c["sobra_sem_previstas"] == D("4100.00")
    assert c["dias"] == 3
    assert c["por_pessoa"] == []  # tudo junto: só o total


def test_conta_paga_depois_da_conferencia_continua_descontada():
    conf = ConferenciaDados(1, date(2026, 10, 6), D("1500.00"), junto=True)
    pagas = {(1, OUT): date(2026, 10, 5), (2, OUT): date(2026, 10, 8)}  # curso pago dia 8
    c = calcular_mes(dados(conf, pagas_em=pagas), OUT, HOJE).conferencia
    assert c["total_a_pagar"] == D("400.00")


def test_receita_que_caiu_antes_nao_entra_de_novo():
    conf = ConferenciaDados(1, date(2026, 10, 6), D("4500.00"), junto=True,
                            ja_entrou=frozenset({"receita:2"}))
    c = calcular_mes(dados(conf), OUT, HOJE).conferencia
    assert [x["chave"] for x in c["a_entrar"]] == ["comissao:1"]


def test_por_pessoa_divide_as_contas_da_casa_e_fecha_com_o_total():
    conf = ConferenciaDados(1, date(2026, 10, 6), D("1500.00"),
                            saldos={1: D("900.00"), 2: D("600.00")})
    c = calcular_mes(dados(conf), OUT, HOJE).conferencia
    carla, bruno = c["por_pessoa"]
    # Aluguel (conjunto) ainda não pago, dividido pela renda do mês: 2.000 × 3.500
    assert (carla["parte_conjunto"], bruno["parte_conjunto"]) == (D("363.64"), D("636.36"))
    assert carla["sobra"] == D("900.00") - D("100.00") - D("363.64")  # saldo - academia - parte
    assert carla["sobra"] + bruno["sobra"] == c["sobra"]
    assert bruno["a_entrar"] == D("3500.00")


def test_usa_a_ultima_conferencia_do_mes():
    antiga = ConferenciaDados(1, date(2026, 10, 2), D("100.00"), junto=True)
    nova = ConferenciaDados(2, date(2026, 10, 6), D("1500.00"), junto=True)
    setembro = ConferenciaDados(3, date(2026, 9, 28), D("9999.00"), junto=True)
    c = calcular_mes(dados(antiga, nova, setembro), OUT, HOJE).conferencia
    assert c["id"] == 2


def test_compara_com_a_conferencia_anterior_e_mostra_o_que_nao_foi_anotado():
    # Dia 2: 1.500 na conta, nada pago ainda. Dia 6: aluguel pago (dia 5) e 2.000 do
    # salário da Carla entraram; deveria ter 2.500, mas tem 2.300: 200 saíram por fora.
    antes = ConferenciaDados(1, date(2026, 10, 2), D("1500.00"), junto=True)
    agora = ConferenciaDados(2, date(2026, 10, 6), D("2300.00"), junto=True)
    c = calcular_mes(dados(antes, agora, pagas_em={(1, OUT): date(2026, 10, 5)}), OUT, HOJE).conferencia
    assert c["anterior"] == {"data": date(2026, 10, 2), "saldo_real": D("1500.00"), "dias": 4,
                             "nao_anotado": D("200.00")}


def test_conferencia_corrigida_no_mesmo_dia_nao_vira_comparacao():
    errada = ConferenciaDados(1, date(2026, 10, 6), D("15000.00"), junto=True)
    certa = ConferenciaDados(2, date(2026, 10, 6), D("1500.00"), junto=True)
    assert "anterior" not in calcular_mes(dados(errada, certa), OUT, HOJE).conferencia


def test_entrada_valida_os_saldos():
    assert ConferenciaEntrada(junto=True, total="-50.00").total == D("-50.00")  # cheque especial
    with pytest.raises(ValidationError):
        ConferenciaEntrada(junto=True)
    with pytest.raises(ValidationError):
        ConferenciaEntrada(saldos=[])
    with pytest.raises(ValidationError):
        ConferenciaEntrada(saldos=[{"responsavel_id": 1, "valor": 1},
                                   {"responsavel_id": 1, "valor": 2}])
