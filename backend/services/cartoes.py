"""Regras de cartões e gastos avulsos.

Cada cartão tem uma forma de pagamento com o mesmo nome (ligada por cartao_id),
para que despesas possam ser cadastradas "no cartão".
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.erros import ErroNegocio
from repositories.base import Repositorio
from repositories.consultas import cartao_para_dados
from repositories.modelos import Cartao, Categoria, Despesa, FormaPagamento, GastoCartao
from schemas.cartoes import CartaoEntrada, ContaFixaCartaoEntrada, GastoCartaoEntrada
from services import despesas, responsaveis
from services.projecao import mes_da_fatura


def _repo(sessao: Session) -> Repositorio[Cartao]:
    return Repositorio(sessao, Cartao, "Cartão")


def _forma_do_cartao(sessao: Session, cartao_id: int) -> FormaPagamento | None:
    return sessao.scalar(select(FormaPagamento).where(FormaPagamento.cartao_id == cartao_id))


def _nome_em_uso(sessao: Session, nome: str, ignorar_cartao_id: int | None = None) -> bool:
    consulta = select(FormaPagamento).where(func.lower(FormaPagamento.nome) == nome.lower())
    forma = sessao.scalar(consulta)
    return forma is not None and (ignorar_cartao_id is None or forma.cartao_id != ignorar_cartao_id)


def listar(sessao: Session) -> list[Cartao]:
    return _repo(sessao).listar(Cartao.nome)


def criar(sessao: Session, entrada: CartaoEntrada) -> Cartao:
    if _nome_em_uso(sessao, entrada.nome):
        raise ErroNegocio("Já existe um cartão ou forma de pagamento com esse nome.", 409)
    responsaveis.validar(sessao, entrada.responsavel_id)
    cartao = Cartao(**entrada.model_dump())
    sessao.add(cartao)
    sessao.flush()  # gera o id do cartão para ligar a forma de pagamento
    sessao.add(FormaPagamento(nome=cartao.nome, cartao_id=cartao.id))
    sessao.commit()
    return cartao


def atualizar(sessao: Session, cartao_id: int, entrada: CartaoEntrada) -> Cartao:
    repo = _repo(sessao)
    cartao = repo.obter(cartao_id)
    if _nome_em_uso(sessao, entrada.nome, ignorar_cartao_id=cartao_id):
        raise ErroNegocio("Já existe um cartão ou forma de pagamento com esse nome.", 409)
    responsaveis.validar(sessao, entrada.responsavel_id)
    for campo, valor in entrada.model_dump().items():
        setattr(cartao, campo, valor)
    forma = _forma_do_cartao(sessao, cartao_id)
    if forma:
        forma.nome = cartao.nome  # mantém a forma de pagamento com o mesmo nome
    return repo.salvar(cartao)


def excluir(sessao: Session, cartao_id: int) -> None:
    repo = _repo(sessao)
    cartao = repo.obter(cartao_id)
    forma = _forma_do_cartao(sessao, cartao_id)
    tem_gastos = sessao.scalar(select(func.count()).where(GastoCartao.cartao_id == cartao_id))
    tem_despesas = forma is not None and sessao.scalar(
        select(func.count()).where(Despesa.forma_pagamento_id == forma.id)
    )
    if tem_gastos or tem_despesas:
        raise ErroNegocio(
            "Este cartão tem despesas ou gastos lançados. Exclua-os antes de excluir o cartão.", 409
        )
    if forma:
        sessao.delete(forma)
        sessao.flush()
    repo.excluir(cartao)


# ---------------------------------------------------------------- gastos avulsos
def _repo_gastos(sessao: Session) -> Repositorio[GastoCartao]:
    return Repositorio(sessao, GastoCartao, "Gasto")


def _montar_saida_gasto(sessao: Session, gasto: GastoCartao, cartoes: dict | None = None,
                        categorias: dict | None = None) -> dict:
    """`cartoes`/`categorias` (por id) evitam uma consulta por gasto nas listagens."""
    cartao = cartoes[gasto.cartao_id] if cartoes else sessao.get(Cartao, gasto.cartao_id)
    if not gasto.categoria_id:
        categoria = None
    elif categorias is not None:
        categoria = categorias.get(gasto.categoria_id)
    else:
        categoria = sessao.get(Categoria, gasto.categoria_id)
    dados_cartao = cartao_para_dados(cartao)
    return {
        **{c: getattr(gasto, c) for c in GastoCartaoEntrada.model_fields},
        "id": gasto.id,
        "cartao": cartao.nome,
        "categoria": categoria.nome if categoria else None,
        "primeira_fatura": str(mes_da_fatura(gasto.data_compra, dados_cartao)),
        "sem_dias": not dados_cartao.tem_dias,
    }


def _validar_gasto(sessao: Session, entrada: GastoCartaoEntrada) -> None:
    if not _repo(sessao).existe(entrada.cartao_id):
        raise ErroNegocio("Cartão inválido.")
    if entrada.categoria_id is not None and sessao.get(Categoria, entrada.categoria_id) is None:
        raise ErroNegocio("Categoria inválida.")
    responsaveis.validar(sessao, entrada.responsavel_id)


def listar_gastos(sessao: Session, cartao_id: int | None = None) -> list[dict]:
    consulta = select(GastoCartao).order_by(GastoCartao.data_compra.desc(), GastoCartao.id.desc())
    if cartao_id is not None:
        consulta = consulta.where(GastoCartao.cartao_id == cartao_id)
    gastos = list(sessao.scalars(consulta))
    # Cartões e categorias de uma vez (antes era uma consulta por gasto)
    cartoes = {c.id: c for c in sessao.scalars(select(Cartao))}
    categorias = {c.id: c for c in sessao.scalars(select(Categoria))}
    return [_montar_saida_gasto(sessao, g, cartoes, categorias) for g in gastos]


def obter_gasto(sessao: Session, gasto_id: int) -> dict:
    return _montar_saida_gasto(sessao, _repo_gastos(sessao).obter(gasto_id))


def criar_gasto(sessao: Session, entrada: GastoCartaoEntrada) -> dict:
    _validar_gasto(sessao, entrada)
    gasto = _repo_gastos(sessao).salvar(GastoCartao(**entrada.model_dump()))
    return _montar_saida_gasto(sessao, gasto)


def atualizar_gasto(sessao: Session, gasto_id: int, entrada: GastoCartaoEntrada) -> dict:
    repo = _repo_gastos(sessao)
    gasto = repo.obter(gasto_id)
    _validar_gasto(sessao, entrada)
    for campo, valor in entrada.model_dump().items():
        setattr(gasto, campo, valor)
    return _montar_saida_gasto(sessao, repo.salvar(gasto))


def excluir_gasto(sessao: Session, gasto_id: int) -> None:
    repo = _repo_gastos(sessao)
    repo.excluir(repo.obter(gasto_id))


# ---------------------------------------------------------------- contas fixas no cartão
def criar_conta_fixa(sessao: Session, cartao_id: int, entrada: ContaFixaCartaoEntrada) -> dict:
    """Cria uma despesa FIXA paga com o cartão (entra em toda fatura, sem data de fim).

    A 1ª cobrança é a fatura em que a compra cai (mesma regra dos gastos avulsos).
    """
    cartao = _repo(sessao).obter(cartao_id)
    responsaveis.validar(sessao, entrada.responsavel_id)
    forma = _forma_do_cartao(sessao, cartao_id)
    if forma is None:  # cartão antigo sem forma de pagamento ligada
        forma = FormaPagamento(nome=cartao.nome, cartao_id=cartao.id)
        sessao.add(forma)
        sessao.flush()

    if entrada.categoria_id is not None:
        if sessao.get(Categoria, entrada.categoria_id) is None:
            raise ErroNegocio("Categoria inválida.")
        categoria_id = entrada.categoria_id
    else:
        categoria_id = sessao.scalar(select(Categoria.id).where(Categoria.nome == "Outros"))
        if categoria_id is None:
            raise ErroNegocio('Cadastre a categoria "Outros" ou escolha uma categoria.')

    dados_cartao = cartao_para_dados(cartao)
    mes = mes_da_fatura(entrada.data_inicio, dados_cartao)
    dia = cartao.dia_vencimento or entrada.data_inicio.day
    despesa = Despesa(
        descricao=entrada.descricao,
        categoria_id=categoria_id,
        forma_pagamento_id=forma.id,
        valor_mensal=entrada.valor_mensal,
        num_parcelas=None,  # fixa: sem fim
        primeira_cobranca=mes.data(dia),
        responsavel_id=entrada.responsavel_id,
    )
    sessao.add(despesa)
    sessao.commit()
    return despesas.obter(sessao, despesa.id)
