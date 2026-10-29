"""Regras do cadastro de despesas."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.erros import ErroNegocio, NaoEncontrado
from repositories.base import Repositorio
from repositories.consultas import despesa_para_dados, despesas_com_nomes, trocas_de_responsavel
from repositories.modelos import Categoria, Despesa, DespesaResponsavel, FormaPagamento
from schemas.despesas import DespesaEntrada, QuemPagaEntrada
from services import responsaveis
from services.calculos import Mes, hoje
from services.dominio import responsavel_em
from services.pagamentos import despesas_pagas_no_mes, faturas_pagas_no_mes
from services.projecao import ocorrencia_despesa, situacao_despesa


def _repo(sessao: Session) -> Repositorio[Despesa]:
    return Repositorio(sessao, Despesa, "Despesa")


def _validar_referencias(sessao: Session, entrada: DespesaEntrada) -> None:
    if not Repositorio(sessao, Categoria, "Categoria").existe(entrada.categoria_id):
        raise ErroNegocio("Categoria inválida.")
    if not Repositorio(sessao, FormaPagamento, "Forma").existe(entrada.forma_pagamento_id):
        raise ErroNegocio("Forma de pagamento inválida.")
    responsaveis.validar(sessao, entrada.responsavel_id)


def _montar_saida(
    linha, mes: Mes, pagas_no_mes: set[int], faturas_pagas: set[int], trocas: dict
) -> dict:
    despesa, categoria, forma, cartao_id = linha
    dados = despesa_para_dados(*linha, trocas.get(despesa.id, ()))
    # Cobrança do mês escolhido (se houver), para o botão "paguei" da lista
    ocorrencia = ocorrencia_despesa(dados, mes)
    # No cartão, a conta é paga junto com a fatura daquele mês
    pago = cartao_id in faturas_pagas if cartao_id is not None else despesa.id in pagas_no_mes
    return {
        **{c: getattr(despesa, c) for c in DespesaEntrada.model_fields},
        "id": despesa.id,
        "categoria": categoria,
        "forma": forma,
        "cartao_id": cartao_id,
        "situacao": situacao_despesa(dados, hoje()),
        "vencimento_mes_atual": ocorrencia.data_vencimento if ocorrencia else None,
        "pago_mes_atual": pago,
        "parcela_no_mes": ocorrencia.parcela_atual if ocorrencia else None,
        # Quem paga no mês consultado (pode ser diferente do responsável do cadastro)
        "responsavel_no_mes": dados.responsavel_no_mes(mes),
        "trocas": [{"a_partir_de": m.data(1), "responsavel_id": r} for m, r in dados.trocas],
    }


def listar(sessao: Session, mes: Mes | None = None) -> list[dict]:
    """`mes`: mês da coluna "vence/pago" (padrão: o mês atual)."""
    mes = mes or Mes.de(hoje())
    pagas, faturas = despesas_pagas_no_mes(sessao, mes), faturas_pagas_no_mes(sessao, mes)
    trocas = trocas_de_responsavel(sessao)
    return [_montar_saida(linha, mes, pagas, faturas, trocas) for linha in despesas_com_nomes(sessao)]


def obter(sessao: Session, despesa_id: int, mes: Mes | None = None) -> dict:
    linhas = despesas_com_nomes(sessao, despesa_id)
    if not linhas:
        raise NaoEncontrado("Despesa")
    mes = mes or Mes.de(hoje())
    return _montar_saida(linhas[0], mes, despesas_pagas_no_mes(sessao, mes),
                         faturas_pagas_no_mes(sessao, mes), trocas_de_responsavel(sessao, despesa_id))


def criar(sessao: Session, entrada: DespesaEntrada) -> dict:
    _validar_referencias(sessao, entrada)
    despesa = _repo(sessao).salvar(Despesa(**entrada.model_dump()))
    return obter(sessao, despesa.id)


def atualizar(sessao: Session, despesa_id: int, entrada: DespesaEntrada) -> dict:
    repo = _repo(sessao)
    despesa = repo.obter(despesa_id)
    _validar_referencias(sessao, entrada)
    for campo, valor in entrada.model_dump().items():
        setattr(despesa, campo, valor)
    repo.salvar(despesa)
    return obter(sessao, despesa_id)


def definir_quem_paga(sessao: Session, despesa_id: int, entrada: QuemPagaEntrada) -> dict:
    """Troca quem paga a conta a partir de um mês, sem mexer nos meses anteriores.

    - "deste mês em diante": vale até o fim (trocas futuras são descartadas);
    - "só este mês": no mês seguinte volta quem pagava antes.
    No fim, tira trocas que não mudam nada (mesma pessoa do mês anterior).
    """
    despesa = _repo(sessao).obter(despesa_id)
    responsaveis.validar(sessao, entrada.responsavel_id)
    mes = Mes(entrada.ano, entrada.mes)
    linhas = {
        Mes.de(t.a_partir_de): t
        for t in sessao.scalars(select(DespesaResponsavel).where(DespesaResponsavel.despesa_id == despesa_id))
    }
    antes = sorted((m, t.responsavel_id) for m, t in linhas.items())
    seguinte = mes.somar(1)

    def trocar(inicio: Mes, responsavel_id: int | None) -> None:
        if inicio in linhas:
            linhas[inicio].responsavel_id = responsavel_id
        else:
            linhas[inicio] = DespesaResponsavel(
                despesa_id=despesa_id, a_partir_de=inicio.data(1), responsavel_id=responsavel_id
            )
            sessao.add(linhas[inicio])

    def remover(inicio: Mes) -> None:
        linha = linhas.pop(inicio)
        if linha in sessao.new:
            sessao.expunge(linha)  # criada agora, ainda não foi gravada
        else:
            sessao.delete(linha)

    if entrada.so_este_mes:
        if seguinte not in linhas:
            trocar(seguinte, responsavel_em(despesa.responsavel_id, antes, seguinte))
    else:
        for inicio in [m for m in linhas if m > mes]:
            remover(inicio)
    trocar(mes, entrada.responsavel_id)

    atual = despesa.responsavel_id
    for inicio in sorted(linhas):
        if linhas[inicio].responsavel_id == atual:
            remover(inicio)
        else:
            atual = linhas[inicio].responsavel_id
    sessao.commit()
    return obter(sessao, despesa_id, mes)


def excluir(sessao: Session, despesa_id: int) -> None:
    repo = _repo(sessao)
    repo.excluir(repo.obter(despesa_id))
