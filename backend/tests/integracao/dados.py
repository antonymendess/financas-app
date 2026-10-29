"""Popula uma casa com uma linha em cada tabela (para os testes de isolamento)."""

from datetime import date
from decimal import Decimal

from repositories.modelos import (
    Anotacao, Cartao, Categoria, Comissao, ComissaoParcela, Conferencia, ConferenciaSaldo, Despesa,
    DespesaPagamento, DespesaResponsavel, FaturaPagamento, FormaPagamento, GastoCartao, Meta, MetaMesFechado,
    MetaMovimento, Negociacao, Receita, Responsavel,
)


def popular(sessao, casa_id: int, marca: str) -> dict:
    """Cria dados da casa usando `marca` nos textos, para achar vazamentos nas respostas."""
    c = {"casa_id": casa_id}
    pessoa = Responsavel(nome=f"{marca} pessoa", **c)
    cartao = Cartao(nome=f"{marca} cartão", dia_fechamento=5, dia_vencimento=15, **c)
    categoria = Categoria(nome=f"{marca} categoria", **c)
    sessao.add_all([pessoa, cartao, categoria])
    sessao.flush()
    forma = FormaPagamento(nome=f"{marca} cartão", cartao_id=cartao.id, **c)
    sessao.add(forma)
    sessao.flush()
    despesa = Despesa(descricao=f"{marca} despesa", categoria_id=categoria.id,
                      forma_pagamento_id=forma.id, valor_mensal=Decimal("100"),
                      primeira_cobranca=date(2026, 1, 10), responsavel_id=pessoa.id, **c)
    receita = Receita(descricao=f"{marca} receita", tipo="Salário", valor=Decimal("3000"),
                      recorrente=True, dia_recebimento=5, data_inicio=date(2026, 1, 1),
                      responsavel_id=pessoa.id, **c)
    comissao = Comissao(cliente=f"{marca} cliente", mes_fechamento=date(2026, 10, 1),
                        valor_implantacao=Decimal("1000"), percentual=Decimal("25"),
                        num_parcelas=1, data_primeira_parcela=date(2026, 10, 15), **c)
    gasto = GastoCartao(descricao=f"{marca} gasto", cartao_id=cartao.id, valor_total=Decimal("50"),
                        num_parcelas=1, data_compra=date(2026, 10, 1), categoria_id=categoria.id, **c)
    anotacao = Anotacao(texto=f"{marca} anotação", tipo="Lembrete", **c)
    negociacao = Negociacao(cliente=f"{marca} negociação", **c)
    meta = Meta(nome=f"{marca} meta", valor_alvo=Decimal("1000"), regra="valor_fixo", **c)
    conferencia = Conferencia(data=date(2026, 10, 6), junto=False, total=Decimal("500"),
                              ja_entrou=[], **c)
    sessao.add_all([despesa, receita, comissao, gasto, anotacao, negociacao, meta, conferencia])
    sessao.flush()
    parcela = ComissaoParcela(comissao_id=comissao.id, numero=1, data_prevista=date(2026, 10, 15),
                              valor=Decimal("250"), paga=False, **c)
    movimento = MetaMovimento(meta_id=meta.id, data=date(2026, 10, 2), valor=Decimal("10"),
                              descricao=f"{marca} movimento", **c)
    sessao.add_all([
        parcela, movimento,
        MetaMesFechado(meta_id=meta.id, competencia=date(2026, 10, 1), **c),
        DespesaPagamento(despesa_id=despesa.id, competencia=date(2026, 10, 1),
                         pago_em=date(2026, 10, 5), **c),
        DespesaResponsavel(despesa_id=despesa.id, a_partir_de=date(2026, 11, 1),
                           responsavel_id=None, **c),
        FaturaPagamento(cartao_id=cartao.id, competencia=date(2026, 10, 1),
                        pago_em=date(2026, 10, 5), **c),
        ConferenciaSaldo(conferencia_id=conferencia.id, responsavel_id=pessoa.id,
                         valor=Decimal("500"), **c),
    ])
    sessao.flush()
    return {
        "responsavel_id": pessoa.id, "cartao_id": cartao.id, "categoria_id": categoria.id,
        "despesa_id": despesa.id, "receita_id": receita.id, "comissao_id": comissao.id,
        "parcela_id": parcela.id, "gasto_id": gasto.id, "anotacao_id": anotacao.id,
        "negociacao_id": negociacao.id, "meta_id": meta.id, "movimento_id": movimento.id,
        "conferencia_id": conferencia.id, "forma_id": forma.id,
    }
