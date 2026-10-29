"""Dados fictícios da demonstração pública.

A casa do login de demonstração (DEMO_EMAIL) é apagada e preenchida de novo todo dia
pelo cron, com datas relativas a hoje para a demo sempre parecer atual. Usa a sessão
de sistema, então todo registro recebe o casa_id explicitamente.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from repositories.modelos import (
    Anotacao, Cartao, Casa, Categoria, Comissao, ComissaoParcela, Convite, Despesa, DespesaPagamento,
    DespesaResponsavel, FaturaPagamento, FormaPagamento, GastoCartao, Membro, Meta, MetaMovimento,
    Negociacao, Receita, Responsavel,
)
from services.calculos import Mes
from services.casas import CATEGORIAS_PADRAO, FORMAS_PADRAO
from services.regras_comissao import gerar_parcelas, proxima_data_pagamento

NOME_CASA = "Casa Demo"

# Filhos antes dos pais (há chaves estrangeiras com "on delete restrict")
TABELAS = (
    "conferencia_saldos", "conferencias", "meta_meses_fechados", "meta_movimentos", "metas",
    "negociacoes", "receitas", "comissao_parcelas", "comissoes", "despesa_responsaveis",
    "despesa_pagamentos", "fatura_pagamentos", "despesas", "gastos_cartao", "anotacoes",
    "formas_pagamento", "cartoes", "categorias", "responsaveis",
)

D = Decimal


def usuario_por_email(sessao: Session, email: str) -> uuid.UUID | None:
    """Id do login no Supabase Auth (tabela auth.users, visível só para o dono do banco)."""
    return sessao.scalar(text("select id from auth.users where lower(email) = :e"), {"e": email.lower()})


def recriar(sessao: Session, usuario_id: uuid.UUID, email: str, hoje: date) -> int:
    """Garante a casa do login de demonstração e troca todos os dados dela pelos fictícios."""
    membro = sessao.scalar(select(Membro).where(Membro.usuario_id == usuario_id))
    if membro is None:
        casa = Casa(nome=NOME_CASA)
        sessao.add(casa)
        sessao.flush()
        sessao.add(Membro(casa_id=casa.id, usuario_id=usuario_id, email=email, papel="dono"))
        casa_id = casa.id
    else:
        casa_id = membro.casa_id
        for tabela in TABELAS:
            sessao.execute(text(f"delete from {tabela} where casa_id = :c"), {"c": casa_id})
        # Visitantes podem ter renomeado a casa, convidado alguém ou aceitado convite
        sessao.execute(delete(Convite).where(Convite.casa_id == casa_id))
        sessao.execute(delete(Membro).where(Membro.casa_id == casa_id, Membro.id != membro.id))
        sessao.get(Casa, casa_id).nome = NOME_CASA

    _popular(sessao, casa_id, hoje)
    sessao.commit()
    return casa_id


def _popular(sessao: Session, casa_id: int, hoje: date) -> None:
    c = {"casa_id": casa_id}
    mes = Mes.de(hoje)

    def dia(meses: int, d: int) -> date:
        return mes.somar(meses).data(d)

    def salvar(*objetos):
        sessao.add_all(objetos)
        sessao.flush()
        return objetos

    categorias = {n: o.id for n, o in zip(
        CATEGORIAS_PADRAO, salvar(*(Categoria(nome=n, **c) for n in CATEGORIAS_PADRAO))
    )}
    formas = {n: o.id for n, o in zip(
        FORMAS_PADRAO, salvar(*(FormaPagamento(nome=n, **c) for n in FORMAS_PADRAO))
    )}
    bruno, carla = salvar(Responsavel(nome="Bruno", **c), Responsavel(nome="Carla", **c))
    azul, verde = salvar(
        Cartao(nome="Cartão Azul", dia_fechamento=3, dia_vencimento=10, responsavel_id=bruno.id, **c),
        Cartao(nome="Cartão Verde", dia_fechamento=25, dia_vencimento=5, responsavel_id=carla.id, **c),
    )
    no_azul, no_verde = salvar(
        FormaPagamento(nome=azul.nome, cartao_id=azul.id, **c),
        FormaPagamento(nome=verde.nome, cartao_id=verde.id, **c),
    )

    salvar(
        Receita(descricao="Salário Bruno", tipo="Salário", valor=D("4800"), recorrente=True,
                dia_recebimento=5, data_inicio=dia(-12, 1), responsavel_id=bruno.id, **c),
        Receita(descricao="Salário Carla", tipo="Salário", valor=D("3900"), recorrente=True,
                dia_recebimento=20, data_inicio=dia(-12, 1), responsavel_id=carla.id, **c),
        Receita(descricao="Freela de fotografia", tipo="Extra", valor=D("850"), recorrente=False,
                dia_recebimento=12, data_inicio=dia(0, 12), responsavel_id=carla.id, **c),
    )

    def conta(descricao, categoria, forma, valor, inicio, venc=None, parcelas=None, quem=None,
              cancelada=None):
        return Despesa(descricao=descricao, categoria_id=categorias[categoria], forma_pagamento_id=forma,
                       valor_mensal=D(valor), num_parcelas=parcelas, primeira_cobranca=inicio,
                       dia_vencimento=venc, responsavel_id=quem, cancelada_em=cancelada, **c)

    contas = salvar(
        conta("Aluguel", "Casa", formas["Boleto"], "1800", dia(-12, 10), venc=10),
        conta("Condomínio", "Casa", formas["Boleto"], "450", dia(-12, 10), venc=10),
        conta("Internet", "Casa", formas["Débito Automático"], "120", dia(-12, 15), venc=15),
        conta("Luz", "Casa", formas["Débito Automático"], "180", dia(-12, 20), venc=20),
        conta("Plano de saúde", "Saúde", formas["Boleto"], "520", dia(-12, 8), venc=8, quem=bruno.id),
        conta("Curso de inglês", "Educação", formas["Pix"], "290", dia(-1, 12), venc=12, parcelas=6,
              quem=carla.id),
        conta("Academia", "Saúde", no_verde.id, "110", dia(-6, 1), quem=carla.id),
        conta("Streaming", "Lazer", no_azul.id, "55.90", dia(-12, 1)),
        conta("Notebook", "Tecnologia", no_azul.id, "389.90", dia(-3, 1), parcelas=10, quem=bruno.id),
        conta("Revista digital", "Lazer", no_azul.id, "29.90", dia(-10, 1), cancelada=dia(-1, 1)),
    )
    aluguel, luz = contas[0], contas[3]

    # Mês passado todo pago; neste mês, o que já venceu
    salvar(*(
        DespesaPagamento(despesa_id=d.id, competencia=dia(m, 1), pago_em=dia(m, d.dia_vencimento), **c)
        for d in contas if d.dia_vencimento and d.cancelada_em is None
        for m in (-1, 0)
        if (m < 0 or d.dia_vencimento < hoje.day) and d.primeira_cobranca <= dia(m, d.dia_vencimento)
    ))
    salvar(
        DespesaResponsavel(despesa_id=aluguel.id, a_partir_de=dia(1, 1), responsavel_id=bruno.id, **c),
        DespesaResponsavel(despesa_id=aluguel.id, a_partir_de=dia(2, 1), responsavel_id=None, **c),
        DespesaResponsavel(despesa_id=luz.id, a_partir_de=dia(1, 1), responsavel_id=carla.id, **c),
    )

    def gasto(descricao, categoria, cartao, valor, data, parcelas=1, quem=None):
        return GastoCartao(descricao=descricao, categoria_id=categorias[categoria], cartao_id=cartao.id,
                           valor_total=D(valor), num_parcelas=parcelas, data_compra=data,
                           responsavel_id=quem, **c)

    salvar(
        gasto("Mercado do mês", "Alimentação", azul, "642.30", hoje - timedelta(days=6)),
        gasto("Farmácia", "Saúde", azul, "89.40", hoje - timedelta(days=10), quem=bruno.id),
        gasto("Tênis de corrida", "Vestuário", azul, "459.90", dia(-1, 18), parcelas=3, quem=bruno.id),
        gasto("Restaurante", "Lazer", verde, "186.00", hoje - timedelta(days=3)),
        gasto("Combustível", "Transporte", verde, "250.00", hoje - timedelta(days=2), quem=carla.id),
        gasto("Geladeira", "Casa", verde, "3600.00", dia(-2, 14), parcelas=10),
    )
    salvar(*(FaturaPagamento(cartao_id=k.id, competencia=dia(-1, 1), pago_em=dia(-1, k.dia_vencimento), **c)
             for k in (azul, verde)))

    for cliente, implantacao, parcelas, fechamento in (
        ("Padaria Pão Quente", "4000", 3, dia(-1, 20)),
        ("Clínica Sorriso", "6000", 2, hoje),
    ):
        comissao = Comissao(cliente=cliente, mes_fechamento=Mes.de(fechamento).data(1),
                            valor_implantacao=D(implantacao), percentual=D("25"), num_parcelas=parcelas,
                            data_primeira_parcela=proxima_data_pagamento(fechamento),
                            responsavel_id=bruno.id, **c)
        salvar(comissao)
        total = D(implantacao) * D("0.25")
        salvar(*(ComissaoParcela(comissao_id=comissao.id, numero=p.numero, data_prevista=p.data_prevista,
                                 valor=p.valor, paga=p.data_prevista < hoje,
                                 paga_em=p.data_prevista if p.data_prevista < hoje else None, **c)
                 for p in gerar_parcelas(total, parcelas, comissao.data_primeira_parcela)))

    salvar(
        Negociacao(cliente="Academia Movimento", etapa="Proposta enviada", probabilidade=50,
                   valor_implantacao=D("5000"), previsao_fechamento=dia(1, 10),
                   ultimo_contato=hoje - timedelta(days=4), proxima_acao="Ligar para tirar dúvidas", **c),
        Negociacao(cliente="Pet Shop Amigo", etapa="Em negociação", probabilidade=75,
                   valor_implantacao=D("4500"), num_parcelas=2, previsao_fechamento=dia(0, 28), **c),
        Negociacao(cliente="Mercado Bom Preço", etapa="Contato inicial", probabilidade=10,
                   valor_implantacao=D("3000"), **c),
    )

    salvar(
        Anotacao(texto="Pagar Lucas do churrasco", tipo="A pagar", data=hoje + timedelta(days=4),
                 valor=D("80"), pessoa="Lucas", entra_no_saldo=True, **c),
        Anotacao(texto="Receber da Júlia o ingresso do show", tipo="A receber",
                 data=hoje + timedelta(days=8), valor=D("150"), pessoa="Júlia", entra_no_saldo=True, **c),
        Anotacao(texto="Renovar a CNH", data=dia(1, 15), **c),
        Anotacao(texto="Pedir orçamento do conserto da máquina de lavar", **c),
    )

    viagem, reserva = salvar(
        Meta(nome="Viagem de férias", valor_alvo=D("8000"), data_alvo=dia(8, 1), **c),
        Meta(nome="Reserva de emergência", valor_alvo=D("15000"), **c),
    )
    salvar(
        *(MetaMovimento(meta_id=viagem.id, data=dia(m, 6), valor=D("500"), **c) for m in range(-5, 0)),
        MetaMovimento(meta_id=reserva.id, data=dia(-3, 6), valor=D("1000"), **c),
        MetaMovimento(meta_id=reserva.id, data=dia(-2, 6), valor=D("800"), **c),
        MetaMovimento(meta_id=reserva.id, data=dia(-1, 6), valor=D("1200"), **c),
        MetaMovimento(meta_id=reserva.id, data=dia(-1, 22), valor=D("-300"), descricao="Conserto do carro",
                      **c),
    )
