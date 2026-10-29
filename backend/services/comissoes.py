"""Regras das comissões: cálculo do valor e geração/atualização das parcelas."""

from decimal import ROUND_HALF_UP, Decimal

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.erros import ErroNegocio
from repositories.base import Repositorio
from repositories.modelos import Comissao, ComissaoParcela, Receita
from schemas.comissoes import ComissaoEntrada, PagamentoParcela
from services import responsaveis
from services.calculos import CENTAVO, hoje
from services.regras_comissao import gerar_parcelas


def _repo(sessao: Session) -> Repositorio[Comissao]:
    return Repositorio(sessao, Comissao, "Comissão")


def calcular_valor_comissao(implantacao: Decimal, percentual: Decimal) -> Decimal:
    """Mesma conta da coluna gerada no banco: implantação × percentual / 100."""
    return (implantacao * percentual / 100).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _sincronizar_parcelas(
    comissao: Comissao, entrada: ComissaoEntrada, regenerar_datas: bool = True
) -> None:
    """Gera as parcelas de novo, mantendo marcado como pago o que já estava pago.

    As parcelas existentes são atualizadas no lugar (pelo número) para não
    esbarrar na restrição única (comissao_id, numero). Com regenerar_datas=False
    (nº de parcelas e 1ª data iguais), as datas ajustadas à mão são mantidas.
    """
    total = calcular_valor_comissao(entrada.valor_implantacao, entrada.percentual)
    if total / entrada.num_parcelas < CENTAVO:
        raise ErroNegocio("Valor da comissão pequeno demais para essa quantidade de parcelas.")

    novas = gerar_parcelas(total, entrada.num_parcelas, entrada.data_primeira_parcela)
    existentes = {p.numero: p for p in comissao.parcelas}
    for gerada in novas:
        parcela = existentes.pop(gerada.numero, None)
        if parcela is None:
            parcela = ComissaoParcela(numero=gerada.numero, paga=False)
            comissao.parcelas.append(parcela)
        if regenerar_datas or parcela.data_prevista is None:
            parcela.data_prevista = gerada.data_prevista
        parcela.valor = gerada.valor
    for sobra in existentes.values():
        comissao.parcelas.remove(sobra)


def status_comissao(pagas: int, total: int) -> str:
    """Mesma regra da planilha: Quitado, Em andamento ou A iniciar."""
    if total and pagas >= total:
        return "Quitado"
    return "Em andamento" if pagas else "A iniciar"


def montar_saida(comissao: Comissao) -> dict:
    recebido = sum((p.valor for p in comissao.parcelas if p.paga), Decimal("0"))
    a_receber = sum((p.valor for p in comissao.parcelas if not p.paga), Decimal("0"))
    pagas = sum(1 for p in comissao.parcelas if p.paga)
    return {
        "status": status_comissao(pagas, len(comissao.parcelas)),
        "pagas": pagas,
        "em_aberto": len(comissao.parcelas) - pagas,
        "valor_parcela": comissao.parcelas[0].valor if comissao.parcelas else Decimal("0"),
        **{c: getattr(comissao, c) for c in ComissaoEntrada.model_fields},
        "id": comissao.id,
        "valor_comissao": comissao.valor_comissao,
        "total_recebido": recebido,
        "total_a_receber": a_receber,
        "parcelas": comissao.parcelas,
    }


def listar(sessao: Session) -> list[dict]:
    comissoes = _repo(sessao).listar(Comissao.mes_fechamento.desc(), Comissao.cliente)
    return [montar_saida(c) for c in comissoes]


def obter(sessao: Session, comissao_id: int) -> dict:
    return montar_saida(_repo(sessao).obter(comissao_id))


def criar(sessao: Session, entrada: ComissaoEntrada) -> dict:
    responsaveis.validar(sessao, entrada.responsavel_id)
    comissao = Comissao(**entrada.model_dump())
    _sincronizar_parcelas(comissao, entrada)
    return montar_saida(_repo(sessao).salvar(comissao))


def atualizar(sessao: Session, comissao_id: int, entrada: ComissaoEntrada) -> dict:
    repo = _repo(sessao)
    comissao = repo.obter(comissao_id)
    responsaveis.validar(sessao, entrada.responsavel_id)
    # Só recalcula as datas se mudou o que as define; senão mantém ajustes manuais
    regenerar = (
        comissao.num_parcelas != entrada.num_parcelas
        or comissao.data_primeira_parcela != entrada.data_primeira_parcela
    )
    for campo, valor in entrada.model_dump().items():
        setattr(comissao, campo, valor)
    _sincronizar_parcelas(comissao, entrada, regenerar_datas=regenerar)
    return montar_saida(repo.salvar(comissao))


def excluir(sessao: Session, comissao_id: int) -> None:
    repo = _repo(sessao)
    repo.excluir(repo.obter(comissao_id))


def marcar_pagamento(sessao: Session, parcela_id: int, entrada: PagamentoParcela) -> ComissaoParcela:
    """Marca/desmarca a parcela como recebida (manual, pelo checkbox).

    Com lancar_receita=True, ao receber cria uma receita "Comissão" na data do
    recebimento. Ao desmarcar, a receita lançada por esta parcela é removida.
    """
    repo = Repositorio(sessao, ComissaoParcela, "Parcela")
    parcela = repo.obter(parcela_id)
    parcela.paga = entrada.paga
    parcela.paga_em = (entrada.paga_em or hoje()) if entrada.paga else None

    receita = sessao.scalar(select(Receita).where(Receita.comissao_parcela_id == parcela.id))
    if entrada.paga and entrada.lancar_receita and receita is None:
        comissao = parcela.comissao
        sessao.add(Receita(
            descricao=f"Comissão {comissao.cliente} ({parcela.numero}/{comissao.num_parcelas})",
            tipo="Comissão",
            valor=parcela.valor,
            recorrente=False,
            data_inicio=parcela.paga_em,
            comissao_parcela_id=parcela.id,
            responsavel_id=comissao.responsavel_id,
        ))
    elif not entrada.paga and receita is not None:
        sessao.delete(receita)

    repo.salvar(parcela)
    sessao.refresh(parcela, ["receita"])
    return parcela


def alterar_data(sessao: Session, parcela_id: int, nova_data: date) -> ComissaoParcela:
    """Ajuste manual da data prevista de uma parcela (ex.: cliente atrasou)."""
    repo = Repositorio(sessao, ComissaoParcela, "Parcela")
    parcela = repo.obter(parcela_id)
    parcela.data_prevista = nova_data
    return repo.salvar(parcela)
