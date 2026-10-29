"""Consultas específicas, incluindo a carga única de dados para a projeção."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from repositories.modelos import (
    Anotacao, Cartao, Categoria, Comissao, ComissaoParcela, Despesa, DespesaPagamento,
    DespesaResponsavel, Conferencia, FaturaPagamento, FormaPagamento, GastoCartao, Receita, Responsavel,
)
from services.calculos import Mes
from services.dominio import (
    AnotacaoDados, CartaoDados, ConferenciaDados, DadosFinanceiros, DespesaDados,
    GastoCartaoDados, ParcelaComissaoDados, ReceitaDados, ResponsavelDados,
)


def despesas_com_nomes(sessao: Session, despesa_id: int | None = None):
    """Despesas junto com o nome da categoria, da forma e o cartão ligado à forma."""
    consulta = (
        select(Despesa, Categoria.nome, FormaPagamento.nome, FormaPagamento.cartao_id)
        .join(Categoria, Categoria.id == Despesa.categoria_id)
        .join(FormaPagamento, FormaPagamento.id == Despesa.forma_pagamento_id)
        .order_by(Despesa.descricao)
    )
    if despesa_id is not None:
        consulta = consulta.where(Despesa.id == despesa_id)
    return sessao.execute(consulta).all()


def trocas_de_responsavel(
    sessao: Session, despesa_id: int | None = None
) -> dict[int, tuple[tuple[Mes, int | None], ...]]:
    """Trocas de quem paga de cada despesa, em ordem de mês."""
    consulta = select(
        DespesaResponsavel.despesa_id, DespesaResponsavel.a_partir_de, DespesaResponsavel.responsavel_id
    ).order_by(DespesaResponsavel.despesa_id, DespesaResponsavel.a_partir_de)
    if despesa_id is not None:
        consulta = consulta.where(DespesaResponsavel.despesa_id == despesa_id)
    trocas: dict[int, list] = {}
    for id_, inicio, responsavel_id in sessao.execute(consulta):
        trocas.setdefault(id_, []).append((Mes.de(inicio), responsavel_id))
    return {id_: tuple(lista) for id_, lista in trocas.items()}


def despesa_para_dados(
    despesa: Despesa, categoria: str, forma: str, cartao_id, trocas: tuple = ()
) -> DespesaDados:
    return DespesaDados(
        id=despesa.id,
        descricao=despesa.descricao,
        valor_mensal=despesa.valor_mensal,
        primeira_cobranca=despesa.primeira_cobranca,
        categoria=categoria,
        forma=forma,
        cartao_id=cartao_id,
        num_parcelas=despesa.num_parcelas,
        cancelada_em=despesa.cancelada_em,
        dia_vencimento=despesa.dia_vencimento,
        responsavel_id=despesa.responsavel_id,
        trocas=trocas,
    )


def cartao_para_dados(cartao: Cartao) -> CartaoDados:
    return CartaoDados(cartao.id, cartao.nome, cartao.dia_fechamento, cartao.dia_vencimento,
                       cartao.responsavel_id)


def carregar_dados_financeiros(sessao: Session) -> DadosFinanceiros:
    """Lê tudo o que a projeção usa com um número FIXO de consultas (uma por tabela).

    O volume de dados de uma pessoa é pequeno, então calcular em memória é
    muito mais rápido do que fazer consultas mês a mês.
    """
    categorias = dict(sessao.execute(select(Categoria.id, Categoria.nome)).all())

    cartoes = [cartao_para_dados(c) for c in sessao.scalars(select(Cartao).order_by(Cartao.nome))]

    trocas = trocas_de_responsavel(sessao)
    despesas = [
        despesa_para_dados(*linha, trocas.get(linha[0].id, ())) for linha in despesas_com_nomes(sessao)
    ]

    receitas = [
        ReceitaDados(r.id, r.descricao, r.valor, r.data_inicio, r.tipo, r.recorrente,
                     r.dia_recebimento, r.data_fim, r.responsavel_id)
        for r in sessao.scalars(select(Receita))
    ]

    lancadas = set(sessao.scalars(
        select(Receita.comissao_parcela_id).where(Receita.comissao_parcela_id.is_not(None))
    ))
    parcelas = [
        ParcelaComissaoDados(p.id, p.comissao_id, cliente, p.numero, total, p.data_prevista,
                             p.valor, p.paga, p.id in lancadas, responsavel_id, p.paga_em)
        for p, cliente, total, responsavel_id in sessao.execute(
            select(ComissaoParcela, Comissao.cliente, Comissao.num_parcelas,
                   Comissao.responsavel_id)
            .join(Comissao, Comissao.id == ComissaoParcela.comissao_id)
        )
    ]

    gastos = [
        GastoCartaoDados(g.id, g.descricao, g.data_compra, g.cartao_id, g.valor_total,
                         g.num_parcelas, categorias.get(g.categoria_id), g.responsavel_id)
        for g in sessao.scalars(select(GastoCartao))
    ]

    anotacoes = [
        AnotacaoDados(a.id, a.texto, a.data, a.valor, a.pessoa, a.tipo, a.concluida,
                      a.entra_no_saldo)
        for a in sessao.scalars(select(Anotacao))
    ]

    despesas_pagas_em = {
        (despesa_id, Mes.de(competencia)): pago_em
        for despesa_id, competencia, pago_em in sessao.execute(
            select(DespesaPagamento.despesa_id, DespesaPagamento.competencia,
                   DespesaPagamento.pago_em)
        )
    }
    faturas_pagas_em = {
        (cartao_id, Mes.de(competencia)): pago_em
        for cartao_id, competencia, pago_em in sessao.execute(
            select(FaturaPagamento.cartao_id, FaturaPagamento.competencia, FaturaPagamento.pago_em)
        )
    }

    responsaveis = [
        ResponsavelDados(r.id, r.nome)
        for r in sessao.scalars(select(Responsavel).order_by(Responsavel.nome))
    ]

    conferencias = [
        ConferenciaDados(c.id, c.data, c.total, c.junto,
                         {s.responsavel_id: s.valor for s in c.saldos}, frozenset(c.ja_entrou))
        for c in sessao.scalars(select(Conferencia).order_by(Conferencia.data, Conferencia.id))
    ]

    return DadosFinanceiros(
        cartoes, despesas, receitas, parcelas, gastos, anotacoes,
        set(despesas_pagas_em), set(faturas_pagas_em), responsaveis,
        despesas_pagas_em, faturas_pagas_em, conferencias,
    )
