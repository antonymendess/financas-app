"""Metas de economia no formato "cofrinho": só informativas.

A meta é quanto quero juntar e até quando; os valores guardados são anotados à
parte. Nada aqui entra no saldo, nas receitas ou nas despesas: as metas só
mostram o progresso, o ritmo e quando a meta deve ser atingida.
"""

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.erros import ErroNegocio

from repositories.base import Repositorio
from repositories.modelos import Meta, MetaMesFechado, MetaMovimento
from schemas.metas import FechamentoMes, MetaEntrada, MovimentoEntrada
from services.calculos import CENTAVO, Mes, hoje

ZERO = Decimal("0")
MESES_DO_RITMO = 6  # o ritmo é a média do que foi guardado nos últimos meses
MARCOS = (25, 50, 75, 100)


@dataclass
class MetaDados:
    id: int
    nome: str
    valor_alvo: Decimal | None = None
    data_alvo: date | None = None
    ativa: bool = True


def _repo(sessao: Session) -> Repositorio[Meta]:
    return Repositorio(sessao, Meta, "Meta")


def _repo_movimentos(sessao: Session) -> Repositorio[MetaMovimento]:
    return Repositorio(sessao, MetaMovimento, "Valor guardado")


# ---------------------------------------------------------------- cálculos puros
def _centavos(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def resumo_meta(meta: MetaDados, movimentos: list[tuple[date, Decimal]], mes: Mes) -> dict:
    """Progresso da meta e previsões a partir do que já foi guardado.

    - ritmo: média por mês do que foi guardado nos últimos meses (desde o 1º valor
      guardado, no máximo 6), sem descontar retiradas: mede o hábito de guardar;
    - previsão: em que mês chega lá mantendo esse ritmo;
    - precisa por mês: quanto guardar por mês para chegar até a data escolhida;
    - sequência: quantos meses seguidos guardou algum valor (retirada não quebra).
    """
    depositos: dict[Mes, Decimal] = defaultdict(lambda: ZERO)
    retiradas: dict[Mes, Decimal] = defaultdict(lambda: ZERO)
    for data, valor in movimentos:
        if valor >= 0:
            depositos[Mes.de(data)] += valor
        else:
            retiradas[Mes.de(data)] -= valor
    guardado = sum(depositos.values(), ZERO) - sum(retiradas.values(), ZERO)
    guardado_no_mes = depositos.get(mes, ZERO)

    ritmo = None
    meses_com_valor = [m for m in depositos if m <= mes]
    if meses_com_valor:
        inicio = max(min(meses_com_valor), mes.somar(-(MESES_DO_RITMO - 1)))
        quantidade = inicio.meses_ate(mes) + 1
        ritmo = _centavos(sum((depositos.get(inicio.somar(i), ZERO) for i in range(quantidade)), ZERO) / quantidade)

    alvo = meta.valor_alvo
    falta = max(alvo - guardado, ZERO) if alvo else None
    concluida = bool(alvo) and falta == ZERO
    progresso = min(float(guardado / alvo), 1.0) if alvo else None

    previsao = None
    if falta and ritmo and ritmo > ZERO:
        previsao = str(mes.somar(math.ceil(falta / ritmo)))

    precisa_por_mes = None
    if falta and meta.data_alvo:
        # Conta o mês atual se ainda não guardou nada nele
        meses_restantes = mes.meses_ate(Mes.de(meta.data_alvo)) + (0 if guardado_no_mes > 0 else 1)
        precisa_por_mes = _centavos(falta / max(meses_restantes, 1))

    # Meses seguidos guardando (o mês atual só conta se já guardou nele)
    sequencia = 0
    atual = mes if guardado_no_mes > 0 else mes.somar(-1)
    while depositos.get(atual, ZERO) > 0:
        sequencia += 1
        atual = atual.somar(-1)

    return {
        "id": meta.id,
        "nome": meta.nome,
        "valor_alvo": alvo,
        "data_alvo": meta.data_alvo,
        "ativa": meta.ativa,
        "guardado": guardado,
        "guardado_no_mes": guardado_no_mes,  # só o que entrou no mês
        "retirado_no_mes": retiradas.get(mes, ZERO),
        "falta": falta,
        "progresso": progresso,
        "concluida": concluida,
        "marco": max((m for m in MARCOS if progresso is not None and progresso * 100 >= m), default=None),
        "ritmo": ritmo,  # média guardada por mês
        "previsao": previsao,  # "AAAA-MM" em que a meta deve ser atingida no ritmo atual
        "precisa_por_mes": precisa_por_mes,  # para chegar até data_alvo
        "no_ritmo": precisa_por_mes is None or (ritmo is not None and ritmo >= precisa_por_mes),
        "sequencia": sequencia,
    }


def montar_painel(
    metas: list[MetaDados], movimentos: list[tuple[int, date, Decimal]], mes: Mes
) -> dict:
    """Metas com progresso + total guardado e histórico dos 12 meses que terminam em `mes`.

    Guardado e retirado vêm separados (no mês e no histórico); o total é o saldo.
    """
    da_meta: dict[int, list[tuple[date, Decimal]]] = defaultdict(list)
    guardado_por_mes: dict[Mes, Decimal] = defaultdict(lambda: ZERO)
    retirado_por_mes: dict[Mes, Decimal] = defaultdict(lambda: ZERO)
    for meta_id, data, valor in movimentos:
        da_meta[meta_id].append((data, valor))
        if valor >= 0:
            guardado_por_mes[Mes.de(data)] += valor
        else:
            retirado_por_mes[Mes.de(data)] -= valor

    itens = [resumo_meta(m, da_meta[m.id], mes) for m in metas]
    alvo_total = sum((i["valor_alvo"] for i in itens if i["valor_alvo"] and i["ativa"]), ZERO)
    guardado_ativas = sum((i["guardado"] for i in itens if i["ativa"]), ZERO)
    return {
        "ano": mes.ano,
        "mes": mes.mes,
        "guardado_total": sum((i["guardado"] for i in itens), ZERO),
        "guardado_no_mes": guardado_por_mes[mes],
        "retirado_no_mes": retirado_por_mes[mes],
        "alvo_total": alvo_total,
        "progresso_total": float(min(guardado_ativas / alvo_total, 1)) if alvo_total else None,
        "metas": itens,
        "historico": [
            {"ano": m.ano, "mes": m.mes, "guardado": guardado_por_mes[m], "retirado": retirado_por_mes[m]}
            for m in (mes.somar(i) for i in range(-11, 1))
        ],
    }


# ---------------------------------------------------------------- banco
def painel(sessao: Session, ano: int, mes: int) -> dict:
    metas = [
        MetaDados(m.id, m.nome, m.valor_alvo, m.data_alvo, m.ativa)
        for m in sessao.scalars(select(Meta).order_by(Meta.ativa.desc(), Meta.id))
    ]
    movimentos = list(sessao.execute(
        select(MetaMovimento.meta_id, MetaMovimento.data, MetaMovimento.valor)
    ).tuples())
    return montar_painel(metas, movimentos, Mes(ano, mes))


def criar(sessao: Session, entrada: MetaEntrada) -> Meta:
    return _repo(sessao).salvar(Meta(**entrada.model_dump(), regra="valor_fixo", regra_valor=None))


def atualizar(sessao: Session, meta_id: int, entrada: MetaEntrada) -> Meta:
    repo = _repo(sessao)
    meta = repo.obter(meta_id)
    for campo, valor in entrada.model_dump().items():
        setattr(meta, campo, valor)
    return repo.salvar(meta)


def excluir(sessao: Session, meta_id: int) -> None:
    repo = _repo(sessao)
    repo.excluir(repo.obter(meta_id))


def movimentos(sessao: Session, meta_id: int) -> list[MetaMovimento]:
    _repo(sessao).obter(meta_id)
    consulta = (
        select(MetaMovimento)
        .where(MetaMovimento.meta_id == meta_id)
        .order_by(MetaMovimento.data.desc(), MetaMovimento.id.desc())
    )
    return list(sessao.scalars(consulta))


def movimentar(sessao: Session, meta_id: int, entrada: MovimentoEntrada) -> MetaMovimento:
    _repo(sessao).obter(meta_id)
    if entrada.tipo == "retirar":
        guardado = sessao.scalar(
            select(func.coalesce(func.sum(MetaMovimento.valor), 0)).where(MetaMovimento.meta_id == meta_id)
        )
        if entrada.valor > guardado:
            raise ErroNegocio(f"Essa meta só tem R$ {guardado:.2f} guardado.".replace(".", ","))
    valor = entrada.valor if entrada.tipo == "guardar" else -entrada.valor
    data = entrada.data or hoje()
    if entrada.tipo == "guardar" and entrada.fechar_mes:
        _marcar_fechado(sessao, meta_id, Mes.de(data), True)
    return _repo_movimentos(sessao).salvar(MetaMovimento(
        meta_id=meta_id, data=data, valor=valor, descricao=entrada.descricao,
    ))


def _marcar_fechado(sessao: Session, meta_id: int, mes: Mes, fechado: bool) -> None:
    """Fecha ou reabre o mês na meta (sem commit; quem chama salva)."""
    existente = sessao.scalar(select(MetaMesFechado).where(
        MetaMesFechado.meta_id == meta_id, MetaMesFechado.competencia == mes.data(1)
    ))
    if fechado and existente is None:
        sessao.add(MetaMesFechado(meta_id=meta_id, competencia=mes.data(1)))
    elif not fechado and existente is not None:
        sessao.delete(existente)


def fechar_mes(sessao: Session, meta_id: int, entrada: FechamentoMes) -> None:
    """Encerra o mês com o que já foi guardado (ou reabre, se `fechado` for falso)."""
    _repo(sessao).obter(meta_id)
    _marcar_fechado(sessao, meta_id, Mes(entrada.ano, entrada.mes), entrada.fechado)
    sessao.commit()


def excluir_movimento(sessao: Session, movimento_id: int) -> None:
    repo = _repo_movimentos(sessao)
    repo.excluir(repo.obter(movimento_id))
