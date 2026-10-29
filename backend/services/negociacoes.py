"""Negociações (possíveis fechamentos) e a passagem de um fechado para Comissões."""

from datetime import timedelta
from decimal import ROUND_HALF_UP

from sqlalchemy.orm import Session

from core.erros import ErroNegocio
from repositories.base import Repositorio
from repositories.modelos import Negociacao
from schemas.comissoes import ComissaoEntrada, FechamentoNegociacao, NegociacaoEntrada
from services import comissoes
from services.calculos import CENTAVO, hoje
from services.regras_comissao import proxima_data_pagamento


def _repo(sessao: Session) -> Repositorio[Negociacao]:
    return Repositorio(sessao, Negociacao, "Negociação")


def montar_saida(n: Negociacao) -> dict:
    prevista = ponderada = None
    if n.valor_implantacao is not None:
        prevista = comissoes.calcular_valor_comissao(n.valor_implantacao, n.percentual)
        if n.probabilidade is not None:
            ponderada = (prevista * n.probabilidade / 100).quantize(CENTAVO, ROUND_HALF_UP)
    return {
        **{c: getattr(n, c) for c in NegociacaoEntrada.model_fields},
        "id": n.id,
        "comissao_id": n.comissao_id,
        "transferido_em": n.transferido_em,
        "comissao_prevista": prevista,
        "comissao_ponderada": ponderada,
    }


def listar(sessao: Session) -> list[dict]:
    negociacoes = _repo(sessao).listar(Negociacao.previsao_fechamento.asc().nulls_last(),
                                       Negociacao.id.desc())
    return [montar_saida(n) for n in negociacoes]


def criar(sessao: Session, entrada: NegociacaoEntrada) -> dict:
    return montar_saida(_repo(sessao).salvar(Negociacao(**entrada.model_dump())))


def atualizar(sessao: Session, negociacao_id: int, entrada: NegociacaoEntrada) -> dict:
    repo = _repo(sessao)
    negociacao = repo.obter(negociacao_id)
    for campo, valor in entrada.model_dump().items():
        setattr(negociacao, campo, valor)
    return montar_saida(repo.salvar(negociacao))


def excluir(sessao: Session, negociacao_id: int) -> None:
    repo = _repo(sessao)
    repo.excluir(repo.obter(negociacao_id))


def fechar(sessao: Session, negociacao_id: int, entrada: FechamentoNegociacao) -> dict:
    """Cria a comissão a partir da negociação (equivale ao "Mover fechados" da planilha).

    Rodar duas vezes não duplica: se já foi transferida, só devolve a comissão.
    """
    negociacao = _repo(sessao).obter(negociacao_id)
    if negociacao.comissao_id is not None:
        return comissoes.obter(sessao, negociacao.comissao_id)
    if negociacao.valor_implantacao is None:
        raise ErroNegocio("Informe o valor da implantação antes de fechar a negociação.")

    data_hoje = hoje()
    # 1ª parcela: hoje se for dia de pagamento, senão o próximo dia 15/30
    primeira = entrada.data_primeira_parcela or proxima_data_pagamento(
        data_hoje - timedelta(days=1)
    )
    dados = ComissaoEntrada(
        cliente=negociacao.cliente,
        telefone=negociacao.telefone,
        mes_fechamento=data_hoje.replace(day=1),
        valor_implantacao=negociacao.valor_implantacao,
        mensalidade=negociacao.mensalidade,
        percentual=negociacao.percentual,
        num_parcelas=negociacao.num_parcelas,
        data_primeira_parcela=primeira,
        observacao=negociacao.observacao,
    )
    comissao = comissoes.criar(sessao, dados)
    negociacao.etapa = "Fechado"
    negociacao.comissao_id = comissao["id"]
    negociacao.transferido_em = data_hoje
    sessao.commit()
    return comissao
