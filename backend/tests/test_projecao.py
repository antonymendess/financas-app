"""Testes da lógica de projeção (funções puras, sem banco)."""

from datetime import date
from decimal import Decimal

from services.calculos import Mes, dividir_valor
from services.dominio import (
    AnotacaoDados,
    CartaoDados,
    DadosFinanceiros,
    DespesaDados,
    GastoCartaoDados,
    ParcelaComissaoDados,
    ReceitaDados,
    ResponsavelDados,
)
from services.projecao import (
    calcular_mes,
    mes_da_fatura,
    ocorrencia_despesa,
    parcela_gasto_no_mes,
    projetar,
    filtrar_por_responsavel,
    resumo_periodo,
    resumo_por_responsavel,
    situacao_despesa,
)
from services.regras_comissao import gerar_parcelas, proxima_data_pagamento

D = Decimal
HOJE = date(2026, 10, 2)


def despesa(**extra) -> DespesaDados:
    base = dict(id=1, descricao="Teste", valor_mensal=D("100.00"),
                primeira_cobranca=date(2026, 9, 10))
    return DespesaDados(**{**base, **extra})


# ---------------------------------------------------------------- utilidades
def test_virada_de_ano_na_aritmetica_de_meses():
    assert Mes(2026, 11).somar(3) == Mes(2027, 2)
    assert Mes(2027, 1).somar(-1) == Mes(2026, 12)
    assert Mes(2026, 2).data(30) == date(2026, 2, 28)
    assert Mes(2028, 2).data(31) == date(2028, 2, 29)  # ano bissexto


def test_dividir_valor_coloca_centavos_na_ultima():
    assert dividir_valor(D("100.00"), 3) == [D("33.33"), D("33.33"), D("33.34")]
    assert sum(dividir_valor(D("81.75"), 4)) == D("81.75")


# ---------------------------------------------------------------- despesas
def test_parcelada_entra_do_primeiro_mes_ate_completar_parcelas():
    d = despesa(num_parcelas=3)
    assert ocorrencia_despesa(d, Mes(2026, 8)) is None
    item = ocorrencia_despesa(d, Mes(2026, 10))
    assert (item.parcela_atual, item.num_parcelas, item.faltam) == (2, 3, 2)
    assert item.ainda_devo == D("200.00")
    assert item.termina_em == "2026-11"
    assert ocorrencia_despesa(d, Mes(2026, 11)).parcela_atual == 3
    assert ocorrencia_despesa(d, Mes(2026, 12)) is None


def test_parcelada_atravessando_virada_de_ano():
    d = despesa(num_parcelas=9, primeira_cobranca=date(2026, 9, 10))
    item = ocorrencia_despesa(d, Mes(2027, 1))
    assert item.parcela_atual == 5
    assert item.termina_em == "2027-05"
    assert ocorrencia_despesa(d, Mes(2027, 5)).parcela_atual == 9
    assert ocorrencia_despesa(d, Mes(2027, 6)) is None


def test_fixa_entra_todo_mes_sem_fim():
    d = despesa()
    assert ocorrencia_despesa(d, Mes(2030, 1)) is not None
    assert ocorrencia_despesa(d, Mes(2030, 1)).parcela_atual is None


def test_fixa_cancelada_para_de_entrar():
    d = despesa(cancelada_em=date(2026, 11, 20), dia_vencimento=10)
    assert ocorrencia_despesa(d, Mes(2026, 11)) is not None  # venceu dia 10, antes do cancelamento
    assert ocorrencia_despesa(d, Mes(2026, 12)) is None
    # cancelada antes do vencimento do mês: aquele mês já não entra
    d2 = despesa(cancelada_em=date(2026, 11, 5), dia_vencimento=10)
    assert ocorrencia_despesa(d2, Mes(2026, 11)) is None


def test_situacao_da_despesa_hoje():
    assert situacao_despesa(despesa(), HOJE).status == "Fixa"
    s = situacao_despesa(despesa(num_parcelas=9), HOJE)  # set/10 e out/10 ainda não venceu
    assert (s.status, s.pagas, s.faltam, s.ainda_devo) == ("Em andamento", 1, 8, D("800.00"))
    assert situacao_despesa(despesa(num_parcelas=2, primeira_cobranca=date(2026, 1, 1)), HOJE).status == "Quitado"
    assert situacao_despesa(despesa(num_parcelas=2, primeira_cobranca=date(2026, 12, 1)), HOJE).status == "A iniciar"
    assert situacao_despesa(despesa(cancelada_em=date(2026, 9, 30)), HOJE).status == "Cancelada"


def test_ultima_parcela_nao_vira_quitado_antes_do_mes_acabar():
    # Última parcela vence 01/10 (já passou), mas ainda está na cobrança/fatura de outubro
    d = despesa(num_parcelas=2, primeira_cobranca=date(2026, 9, 1))
    s = situacao_despesa(d, HOJE)
    assert (s.status, s.pagas, s.faltam) == ("Em andamento", 2, 0)
    assert situacao_despesa(d, date(2026, 11, 1)).status == "Quitado"


def test_cancelada_continua_ativa_enquanto_ainda_cobra_no_mes():
    # Cancelou dia 01/10, mas a cobrança de outubro venceu antes (dia 1): ainda cobra
    d = despesa(cancelada_em=date(2026, 10, 1), dia_vencimento=1)
    assert ocorrencia_despesa(d, Mes(2026, 10)) is not None
    assert situacao_despesa(d, HOJE).status == "Fixa"
    assert situacao_despesa(d, date(2026, 11, 2)).status == "Cancelada"


def test_projecao_lista_itens_de_cada_fatura():
    dados = DadosFinanceiros(
        cartoes=[CARTAO],
        despesas=[despesa(id=1, descricao="PC", valor_mensal=D("193.00"), num_parcelas=2,
                          forma="Cartão Teste", cartao_id=1, primeira_cobranca=date(2026, 9, 1))],
        gastos_cartao=[GastoCartaoDados(5, "Mercado", date(2026, 9, 20), 1, D("50.00"))],
    )
    fatura = projetar(dados, Mes(2026, 10), 0, HOJE)[0]["faturas"][0]
    assert fatura["total"] == sum(i["valor"] for i in fatura["itens"]) == D("243.00")
    assert {(i["origem"], i["id"]) for i in fatura["itens"]} == {("despesa", 1), ("gasto_cartao", 5)}


# ---------------------------------------------------------------- cartão
CARTAO = CartaoDados(id=1, nome="Cartão Teste", dia_fechamento=5, dia_vencimento=15)


def test_compra_ate_o_fechamento_entra_na_fatura_do_mes():
    assert mes_da_fatura(date(2026, 10, 5), CARTAO) == Mes(2026, 10)


def test_compra_depois_do_fechamento_vai_para_a_fatura_seguinte():
    assert mes_da_fatura(date(2026, 10, 6), CARTAO) == Mes(2026, 11)


def test_vencimento_antes_do_fechamento_paga_no_mes_seguinte():
    cartao = CartaoDados(id=2, nome="X", dia_fechamento=25, dia_vencimento=5)
    assert mes_da_fatura(date(2026, 10, 20), cartao) == Mes(2026, 11)
    assert mes_da_fatura(date(2026, 10, 26), cartao) == Mes(2026, 12)


def test_fatura_na_virada_de_ano():
    assert mes_da_fatura(date(2026, 12, 20), CARTAO) == Mes(2027, 1)


def test_cartao_sem_dias_usa_mes_seguinte_e_avisa():
    cartao = CartaoDados(id=3, nome="Sem dias")
    assert mes_da_fatura(date(2026, 10, 1), cartao) == Mes(2026, 11)
    dados = DadosFinanceiros(
        cartoes=[cartao],
        gastos_cartao=[GastoCartaoDados(1, "Mercado", date(2026, 10, 1), 3, D("50.00"))],
    )
    resumo = calcular_mes(dados, Mes(2026, 11), HOJE)
    assert resumo.faturas[0].sem_dias
    assert resumo.avisos


def test_gasto_parcelado_cai_nas_faturas_seguintes():
    gasto = GastoCartaoDados(1, "TV", date(2026, 10, 10), 1, D("100.00"), num_parcelas=3)
    assert parcela_gasto_no_mes(gasto, CARTAO, Mes(2026, 10)) is None
    assert parcela_gasto_no_mes(gasto, CARTAO, Mes(2026, 11)).valor == D("33.33")
    ultima = parcela_gasto_no_mes(gasto, CARTAO, Mes(2027, 1))
    assert (ultima.valor, ultima.parcela_atual, ultima.termina_em) == (D("33.34"), 3, "2027-01")
    assert parcela_gasto_no_mes(gasto, CARTAO, Mes(2027, 2)) is None


def test_despesa_no_cartao_soma_na_fatura_sem_contagem_dupla():
    dados = DadosFinanceiros(
        cartoes=[CARTAO],
        despesas=[
            despesa(id=1, descricao="PC", valor_mensal=D("193.00"), num_parcelas=9,
                    forma="Cartão Teste", cartao_id=1),
            despesa(id=2, descricao="Aluguel", valor_mensal=D("600.00")),
        ],
        gastos_cartao=[GastoCartaoDados(1, "Mercado", date(2026, 9, 20), 1, D("50.00"))],
    )
    resumo = calcular_mes(dados, Mes(2026, 10), HOJE)
    assert resumo.faturas[0].total == D("243.00")  # 193 + 50
    assert resumo.total_faturas == D("243.00")
    assert resumo.total_despesas == D("843.00")  # 600 + 193 + 50, nada duplicado
    assert resumo.contas_ativas == 2
    assert resumo.faturas[0].termina_em == "2027-05"
    # a despesa do cartão não aparece solta nos vencimentos, só a fatura
    tipos = {(v.tipo, v.descricao) for v in resumo.vencimentos}
    assert ("fatura", "Fatura Cartão Teste") in tipos
    assert ("conta", "PC") not in tipos


def test_conta_fixa_no_cartao_entra_em_toda_fatura_sem_fim():
    netflix = despesa(id=7, descricao="Netflix", valor_mensal=D("55.90"), cartao_id=1,
                      forma="Cartão Teste", primeira_cobranca=date(2026, 10, 15))
    dados = DadosFinanceiros(cartoes=[CARTAO], despesas=[netflix])
    for mes in (Mes(2026, 10), Mes(2027, 6), Mes(2030, 1)):
        resumo = calcular_mes(dados, mes, HOJE)
        assert resumo.faturas[0].total == D("55.90")
        assert resumo.total_despesas == D("55.90")  # conta uma vez só
    assert calcular_mes(dados, Mes(2026, 9), HOJE).faturas[0].total == D("0.00")


def test_totais_por_categoria_e_forma():
    dados = DadosFinanceiros(despesas=[
        despesa(id=1, categoria="Casa", forma="Pix", valor_mensal=D("600.00")),
        despesa(id=2, categoria="Casa", forma="Boleto", valor_mensal=D("70.00")),
        despesa(id=3, categoria="Saúde", forma="Pix", valor_mensal=D("170.00")),
    ])
    resumo = calcular_mes(dados, Mes(2026, 10), HOJE)
    assert resumo.por_categoria == [
        {"nome": "Casa", "valor": D("670.00")},
        {"nome": "Saúde", "valor": D("170.00")},
    ]
    assert {"nome": "Pix", "valor": D("770.00")} in resumo.por_forma


# ---------------------------------------------------------------- receitas e comissões
def test_receitas_recorrentes_e_avulsas():
    dados = DadosFinanceiros(receitas=[
        ReceitaDados(1, "Salário", D("3000.00"), date(2026, 1, 5)),
        ReceitaDados(2, "Freela", D("500.00"), date(2026, 10, 20), recorrente=False),
        ReceitaDados(3, "Bico antigo", D("100.00"), date(2026, 1, 1), data_fim=date(2026, 9, 30)),
    ])
    assert calcular_mes(dados, Mes(2026, 10), HOJE).total_receitas == D("3500.00")
    assert calcular_mes(dados, Mes(2026, 11), HOJE).total_receitas == D("3000.00")
    assert calcular_mes(dados, Mes(2026, 9), HOJE).total_receitas == D("3100.00")
    itens = {r.descricao: r.recorrente for r in calcular_mes(dados, Mes(2026, 10), HOJE).receitas}
    assert itens == {"Salário": True, "Freela": False}


def test_receita_so_conta_como_recebida_quando_a_data_chega():
    dados = DadosFinanceiros(receitas=[
        ReceitaDados(1, "Salário dela", D("2000.00"), date(2026, 1, 6), dia_recebimento=6),
        ReceitaDados(2, "Salário dele", D("2500.00"), date(2026, 1, 15), dia_recebimento=15),
    ])
    hoje = date(2026, 10, 6)
    outubro = {r.descricao: r.recebida for r in calcular_mes(dados, Mes(2026, 10), hoje).receitas}
    assert outubro == {"Salário dela": True, "Salário dele": False}
    assert all(r.recebida for r in calcular_mes(dados, Mes(2026, 9), hoje).receitas)
    assert not any(r.recebida for r in calcular_mes(dados, Mes(2026, 11), hoje).receitas)


def test_comissoes_separam_recebidas_e_a_receber():
    dados = DadosFinanceiros(parcelas_comissao=[
        ParcelaComissaoDados(1, 1, "Cliente A", 1, 2, date(2026, 10, 15), D("100.00"), paga=True),
        ParcelaComissaoDados(2, 1, "Cliente A", 2, 2, date(2026, 10, 30), D("100.00")),
        ParcelaComissaoDados(3, 2, "Cliente B", 1, 1, date(2026, 11, 15), D("999.00")),
    ])
    resumo = calcular_mes(dados, Mes(2026, 10), HOJE)
    assert resumo.comissoes_recebidas == D("100.00")
    assert resumo.comissoes_a_receber == D("100.00")
    assert resumo.total_receitas == D("200.00")


def test_parcelas_seguintes_caem_no_dia_15_de_cada_mes():
    # Fechou e recebe a 1ª dia 30; as próximas só quando o cliente paga (1 por mês)
    datas = [p.data_prevista for p in gerar_parcelas(D("1000.00"), 4, date(2026, 10, 30))]
    assert datas == [date(2026, 10, 30), date(2026, 11, 15), date(2026, 12, 15), date(2027, 1, 15)]


def test_primeira_no_dia_15_segunda_no_15_do_mes_seguinte():
    datas = [p.data_prevista for p in gerar_parcelas(D("300.00"), 3, date(2026, 12, 15))]
    assert datas == [date(2026, 12, 15), date(2027, 1, 15), date(2027, 2, 15)]


def test_sugestao_da_primeira_parcela_proximo_15_ou_30():
    assert proxima_data_pagamento(date(2026, 10, 2)) == date(2026, 10, 15)
    assert proxima_data_pagamento(date(2026, 10, 18)) == date(2026, 10, 30)
    assert proxima_data_pagamento(date(2026, 10, 31)) == date(2026, 11, 15)
    # fevereiro não tem dia 30: usa o último dia do mês
    assert proxima_data_pagamento(date(2027, 2, 15)) == date(2027, 2, 28)
    assert proxima_data_pagamento(date(2028, 2, 15)) == date(2028, 2, 29)


def test_parcelas_de_comissao_dividem_valor_com_centavos_na_ultima():
    parcelas = gerar_parcelas(D("100.00"), 3, date(2026, 10, 20))
    assert [p.valor for p in parcelas] == [D("33.33"), D("33.33"), D("33.34")]


def test_parcela_lancada_como_receita_nao_soma_duas_vezes():
    dados = DadosFinanceiros(
        receitas=[ReceitaDados(9, "Comissão ACME (1/2)", D("100.00"), date(2026, 10, 15),
                               tipo="Comissão", recorrente=False)],
        parcelas_comissao=[
            ParcelaComissaoDados(1, 1, "ACME", 1, 2, date(2026, 10, 15), D("100.00"),
                                 paga=True, lancada_como_receita=True),
            ParcelaComissaoDados(2, 1, "ACME", 2, 2, date(2026, 10, 30), D("100.00")),
        ],
    )
    resumo = calcular_mes(dados, Mes(2026, 10), HOJE)
    assert resumo.total_receitas == D("200.00")  # 100 da receita + 100 a receber
    assert resumo.comissoes_recebidas == D("100.00")
    assert resumo.comissoes_a_receber == D("100.00")


# ---------------------------------------------------------------- anotações
def test_anotacao_com_entra_no_saldo_soma_no_mes_certo():
    dados = DadosFinanceiros(anotacoes=[
        AnotacaoDados(1, "Pagar fulano", date(2026, 11, 20), D("50.00"),
                      tipo="A pagar", entra_no_saldo=True),
        AnotacaoDados(2, "Fulano me paga", date(2026, 11, 25), D("80.00"),
                      tipo="A receber", entra_no_saldo=True),
    ])
    outubro = calcular_mes(dados, Mes(2026, 10), HOJE)
    novembro = calcular_mes(dados, Mes(2026, 11), HOJE)
    assert outubro.saldo == D("0.00")
    assert novembro.total_despesas == D("50.00")
    assert novembro.total_receitas == D("80.00")
    assert novembro.saldo == D("30.00")


def test_anotacao_sem_entra_no_saldo_nao_altera_saldo():
    dados = DadosFinanceiros(anotacoes=[
        AnotacaoDados(1, "Pagar fulano", date(2026, 10, 20), D("50.00"), tipo="A pagar"),
    ])
    resumo = calcular_mes(dados, Mes(2026, 10), HOJE)
    assert resumo.saldo == D("0.00")
    assert resumo.total_despesas == D("0.00")
    # mas continua aparecendo nos vencimentos do mês
    assert [v.tipo for v in resumo.vencimentos] == ["anotacao"]


def test_pendencias_e_vencidas():
    dados = DadosFinanceiros(anotacoes=[
        AnotacaoDados(1, "Sem data"),
        AnotacaoDados(2, "Concluída", concluida=True),
        AnotacaoDados(3, "Atrasada", date(2026, 10, 1)),
        AnotacaoDados(4, "Feita", date(2026, 10, 1), concluida=True),
    ])
    resumo = calcular_mes(dados, Mes(2026, 10), HOJE)
    assert [a.id for a in resumo.pendencias] == [1]
    assert [a.id for a in resumo.anotacoes_do_mes] == [3]
    assert resumo.vencimentos[0].vencido is True


def test_anotacao_atrasada_de_mes_anterior_aparece_so_no_mes_atual():
    dados = DadosFinanceiros(anotacoes=[
        AnotacaoDados(1, "Pagar João", date(2026, 9, 30), tipo="A pagar"),
        AnotacaoDados(2, "Já paga", date(2026, 9, 10), concluida=True),
    ])
    atual = calcular_mes(dados, Mes(2026, 10), HOJE)
    assert [(v.id, v.vencido) for v in atual.vencimentos] == [(1, True)]
    assert calcular_mes(dados, Mes(2026, 11), HOJE).vencimentos == []


# ---------------------------------------------------------------- pagamentos
def test_conta_paga_no_mes_sai_do_a_pagar_e_nao_fica_vencida():
    d1 = despesa(id=1, descricao="Aluguel", valor_mensal=D("600.00"), dia_vencimento=1)
    d2 = despesa(id=2, descricao="Luz", valor_mensal=D("100.00"), dia_vencimento=1)
    dados = DadosFinanceiros(despesas=[d1, d2], despesas_pagas={(1, Mes(2026, 10))})
    resumo = calcular_mes(dados, Mes(2026, 10), HOJE)
    assert resumo.total_pago == D("600.00")
    assert resumo.total_a_pagar == D("100.00")
    situacao = {v.descricao: (v.pago, v.vencido) for v in resumo.vencimentos}
    assert situacao == {"Aluguel": (True, False), "Luz": (False, True)}
    # o pagamento vale só para aquele mês
    assert calcular_mes(dados, Mes(2026, 11), HOJE).total_pago == D("0.00")


def test_fatura_paga_marca_itens_do_cartao_como_pagos():
    dados = DadosFinanceiros(
        cartoes=[CARTAO],
        despesas=[despesa(id=1, valor_mensal=D("193.00"), cartao_id=1, forma="Cartão Teste")],
        gastos_cartao=[GastoCartaoDados(1, "Mercado", date(2026, 9, 20), 1, D("50.00"))],
        faturas_pagas={(1, Mes(2026, 10))},
    )
    resumo = calcular_mes(dados, Mes(2026, 10), HOJE)
    assert resumo.faturas[0].paga
    assert resumo.total_pago == D("243.00")
    assert all(d.pago for d in resumo.despesas)
    fatura = next(v for v in resumo.vencimentos if v.tipo == "fatura")
    assert fatura.pago and not fatura.vencido


# ---------------------------------------------------------------- por pessoa
EU, ELA = ResponsavelDados(1, "Bruno"), ResponsavelDados(2, "Carla")


def test_sem_pessoas_cadastradas_nao_separa():
    dados = DadosFinanceiros(receitas=[ReceitaDados(1, "Salário", D("3000.00"), date(2026, 1, 5))])
    assert calcular_mes(dados, Mes(2026, 10), HOJE).por_responsavel == []


def test_separa_receitas_e_despesas_por_pessoa_e_divide_o_conjunto_pela_renda():
    dados = DadosFinanceiros(
        responsaveis=[EU, ELA],
        receitas=[
            ReceitaDados(1, "Salário dele", D("3000.00"), date(2026, 1, 5), responsavel_id=1),
            ReceitaDados(2, "Salário dela", D("2000.00"), date(2026, 1, 5), responsavel_id=2),
        ],
        despesas=[
            despesa(id=1, descricao="Aluguel", valor_mensal=D("1000.00")),  # conjunto
            despesa(id=2, descricao="Academia", valor_mensal=D("100.00"), responsavel_id=2),
        ],
    )
    resumo = calcular_mes(dados, Mes(2026, 10), HOJE)
    eu, ela, conjunto = resumo.por_responsavel
    assert (eu["nome"], eu["receitas"], eu["despesas"]) == ("Bruno", D("3000.00"), D("0.00"))
    assert (ela["receitas"], ela["despesas"]) == (D("2000.00"), D("100.00"))
    assert (conjunto["responsavel_id"], conjunto["despesas"]) == (None, D("1000.00"))
    # Aluguel dividido 60% / 40% conforme a renda
    assert eu["parte_conjunto"] == D("600.00") and ela["parte_conjunto"] == D("400.00")
    assert eu["saldo_final"] == D("2400.00") and ela["saldo_final"] == D("1500.00")
    assert eu["saldo_final"] + ela["saldo_final"] == resumo.saldo


def test_conjunto_informa_quanto_das_receitas_sem_dono_e_de_comissao():
    dados = DadosFinanceiros(
        responsaveis=[EU, ELA],
        receitas=[
            ReceitaDados(1, "Comissão X (1/1)", D("300.00"), date(2026, 10, 3), "Comissão",
                         recorrente=False),
            ReceitaDados(2, "Presente", D("50.00"), date(2026, 10, 3), "Outros", recorrente=False),
        ],
        parcelas_comissao=[
            ParcelaComissaoDados(1, 1, "Cliente", 1, 1, date(2026, 10, 15), D("200.00")),
        ],
    )
    conjunto = calcular_mes(dados, Mes(2026, 10), HOJE).por_responsavel[-1]
    assert conjunto["receitas"] == D("550.00")
    assert conjunto["receitas_comissao"] == D("500.00")


def test_gasto_e_conta_no_cartao_sem_pessoa_sao_do_dono_do_cartao():
    cartao = CartaoDados(id=1, nome="Cartão dela", dia_fechamento=5, dia_vencimento=15,
                         responsavel_id=2)
    dados = DadosFinanceiros(
        responsaveis=[EU, ELA],
        cartoes=[cartao],
        despesas=[despesa(id=7, descricao="Netflix", cartao_id=1, valor_mensal=D("50.00"),
                          primeira_cobranca=date(2026, 10, 15))],
        gastos_cartao=[
            GastoCartaoDados(1, "Mercado", date(2026, 9, 20), 1, D("80.00")),
            GastoCartaoDados(2, "Presente dele", date(2026, 9, 20), 1, D("30.00"),
                             responsavel_id=1),
        ],
    )
    resumo = calcular_mes(dados, Mes(2026, 10), HOJE)
    eu, ela = resumo.por_responsavel  # nada no conjunto: some da lista
    assert eu["despesas"] == D("30.00")
    assert ela["despesas"] == D("130.00")
    fatura = next(v for v in resumo.vencimentos if v.tipo == "fatura")
    assert fatura.responsavel_id == 2


def test_comissao_nao_recebida_aparece_como_prevista_e_fica_fora_do_garantido():
    dados = DadosFinanceiros(
        responsaveis=[EU, ELA],
        receitas=[
            ReceitaDados(1, "Salário dele", D("2500.00"), date(2026, 1, 5), responsavel_id=1),
            ReceitaDados(2, "Comissão Beta (1/1)", D("650.00"), date(2026, 10, 2), "Comissão",
                         recorrente=False, responsavel_id=1),
        ],
        parcelas_comissao=[
            ParcelaComissaoDados(1, 1, "Acme", 2, 3, date(2026, 10, 15), D("500.00"),
                                 responsavel_id=1),
            ParcelaComissaoDados(2, 1, "Acme", 1, 3, date(2026, 10, 2), D("500.00"),
                                 paga=True, lancada_como_receita=True, responsavel_id=1),
        ],
    )
    eu = calcular_mes(dados, Mes(2026, 10), HOJE).por_responsavel[0]
    assert eu["receitas"] == D("3650.00")  # salário + Beta + parcela 2 prevista
    assert eu["receitas_previstas"] == D("500.00")
    assert eu["saldo_final"] == D("3650.00")
    assert eu["saldo_final_garantido"] == D("3150.00")


def test_sem_renda_o_conjunto_e_dividido_em_partes_iguais_e_os_centavos_fecham():
    despesas = [calcular_mes(DadosFinanceiros(despesas=[despesa(valor_mensal=D("100.00"))]),
                             Mes(2026, 10), HOJE).despesas[0]]
    tres = [EU, ELA, ResponsavelDados(3, "Outro")]
    lista = resumo_por_responsavel([], despesas, tres)
    partes = [p["parte_conjunto"] for p in lista[:3]]
    assert partes == [D("33.33"), D("33.33"), D("33.34")]


def _casal() -> DadosFinanceiros:
    return DadosFinanceiros(
        responsaveis=[EU, ELA],
        receitas=[
            ReceitaDados(1, "Salário dele", D("3000.00"), date(2026, 1, 5), responsavel_id=1),
            ReceitaDados(2, "Salário dela", D("2000.00"), date(2026, 1, 5), responsavel_id=2),
        ],
        despesas=[
            despesa(id=1, descricao="Aluguel", valor_mensal=D("1000.00")),
            despesa(id=2, descricao="Academia", valor_mensal=D("100.00"), responsavel_id=2,
                    categoria="Saúde"),
        ],
    )


def test_filtro_por_pessoa_mostra_so_o_que_e_dela():
    resumo = filtrar_por_responsavel(calcular_mes(_casal(), Mes(2026, 10), HOJE), 2)
    assert [r.descricao for r in resumo.receitas] == ["Salário dela"]
    assert [d.descricao for d in resumo.despesas] == ["Academia"]
    assert resumo.saldo == D("1900.00")  # sobra própria, antes do Conjunto
    assert resumo.pessoa["saldo_final"] == D("1500.00")  # depois de 40% do aluguel
    assert resumo.por_categoria == [{"nome": "Saúde", "valor": D("100.00")}]


def test_filtro_conjunto_mostra_as_contas_da_casa():
    resumo = filtrar_por_responsavel(calcular_mes(_casal(), Mes(2026, 10), HOJE), None)
    assert [d.descricao for d in resumo.despesas] == ["Aluguel"]
    assert resumo.total_receitas == D("0.00")


def test_projecao_de_uma_pessoa_conta_a_parte_dela_no_conjunto():
    linha = projetar(_casal(), Mes(2026, 10), 0, HOJE, responsavel=2)[0]
    assert (linha["receitas"], linha["despesas"]) == (D("2000.00"), D("500.00"))
    assert linha["saldo"] == D("1500.00")


def test_periodo_soma_os_meses_e_aponta_maiores_despesas():
    periodo = resumo_periodo(_casal(), Mes(2026, 10), Mes(2026, 12), HOJE)
    assert len(periodo["meses"]) == 3
    assert periodo["total_receitas"] == D("15000.00")
    assert periodo["total_despesas"] == D("3300.00")
    assert periodo["media_saldo"] == D("3900.00")
    assert periodo["maiores_despesas"][0] == {"nome": "Aluguel", "valor": D("3000.00")}
    ela = next(p for p in periodo["por_responsavel"] if p["responsavel_id"] == 2)
    assert ela["saldo_final"] == D("4500.00")


def test_periodo_de_uma_pessoa():
    periodo = resumo_periodo(_casal(), Mes(2026, 10), Mes(2026, 11), HOJE, responsavel=2)
    assert periodo["saldo"] == D("3000.00")
    assert periodo["por_categoria"] == [{"nome": "Saúde", "valor": D("200.00")}]


# ---------------------------------------------------------------- projeção
def test_projecao_mes_atual_mais_12():
    dados = DadosFinanceiros(
        receitas=[ReceitaDados(1, "Salário", D("3000.00"), date(2026, 1, 5))],
        despesas=[despesa(num_parcelas=3, valor_mensal=D("200.00"))],
    )
    projecao = projetar(dados, Mes(2026, 10), 12, HOJE)
    assert len(projecao) == 13
    assert (projecao[0]["ano"], projecao[0]["mes"]) == (2026, 10)
    assert (projecao[-1]["ano"], projecao[-1]["mes"]) == (2027, 10)
    assert projecao[0]["saldo"] == D("2800.00")
    assert projecao[2]["saldo"] == D("3000.00")  # parcelas terminaram em novembro


# ---------------------------------------------------------------- quem paga muda por mês
def test_troca_de_quem_paga_vale_so_a_partir_do_mes_dela():
    # Aluguel da Carla (2) até outubro; Bruno (1) em novembro; volta para ela em dezembro
    aluguel = despesa(descricao="Aluguel", valor_mensal=D("1500.00"), responsavel_id=2,
                      trocas=((Mes(2026, 11), 1), (Mes(2026, 12), 2)))
    assert ocorrencia_despesa(aluguel, Mes(2026, 10)).responsavel_id == 2
    assert ocorrencia_despesa(aluguel, Mes(2026, 11)).responsavel_id == 1
    assert ocorrencia_despesa(aluguel, Mes(2026, 12)).responsavel_id == 2

    dados = DadosFinanceiros(
        responsaveis=[ResponsavelDados(1, "Bruno"), ResponsavelDados(2, "Carla")],
        despesas=[aluguel],
    )
    outubro = {p["responsavel_id"]: p["despesas"] for p in calcular_mes(dados, Mes(2026, 10), HOJE).por_responsavel}
    novembro = {p["responsavel_id"]: p["despesas"] for p in calcular_mes(dados, Mes(2026, 11), HOJE).por_responsavel}
    assert outubro == {1: D("0"), 2: D("1500.00")}
    assert novembro == {1: D("1500.00"), 2: D("0")}


def test_troca_para_o_conjunto():
    conta = despesa(responsavel_id=1, trocas=((Mes(2026, 11), None),))
    assert ocorrencia_despesa(conta, Mes(2026, 11)).responsavel_id is None
