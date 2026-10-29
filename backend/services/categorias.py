"""Categorias de despesa: criar, renomear e excluir (movendo os lançamentos).

"Outros" é a categoria padrão do sistema (usada pelo nome em contas fixas no cartão
e em gastos sem categoria), então não pode ser renomeada nem excluída.
"""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from core.erros import ErroNegocio
from repositories.base import Repositorio
from repositories.modelos import Categoria, Despesa, GastoCartao
from schemas.categorias import CategoriaEntrada

PADRAO = "Outros"


def _repo(sessao: Session) -> Repositorio[Categoria]:
    return Repositorio(sessao, Categoria, "Categoria")


def _protegida(categoria: Categoria) -> bool:
    return categoria.nome.lower() == PADRAO.lower()


def _nome_em_uso(sessao: Session, nome: str, ignorar_id: int | None = None) -> bool:
    existente = sessao.scalar(select(Categoria).where(func.lower(Categoria.nome) == nome.lower()))
    return existente is not None and existente.id != ignorar_id


def _contagens(sessao: Session, modelo) -> dict[int, int]:
    return dict(sessao.execute(
        select(modelo.categoria_id, func.count())
        .where(modelo.categoria_id.is_not(None))
        .group_by(modelo.categoria_id)
    ).all())


def _saida(categoria: Categoria, despesas: dict[int, int], gastos: dict[int, int]) -> dict:
    return {
        "id": categoria.id,
        "nome": categoria.nome,
        "despesas": despesas.get(categoria.id, 0),
        "gastos": gastos.get(categoria.id, 0),
        "protegida": _protegida(categoria),
    }


def listar(sessao: Session) -> list[dict]:
    despesas, gastos = _contagens(sessao, Despesa), _contagens(sessao, GastoCartao)
    return [_saida(c, despesas, gastos) for c in _repo(sessao).listar(Categoria.nome)]


def criar(sessao: Session, entrada: CategoriaEntrada) -> dict:
    if _nome_em_uso(sessao, entrada.nome):
        raise ErroNegocio("Já existe uma categoria com esse nome.", 409)
    return _saida(_repo(sessao).salvar(Categoria(nome=entrada.nome)), {}, {})


def atualizar(sessao: Session, categoria_id: int, entrada: CategoriaEntrada) -> dict:
    repo = _repo(sessao)
    categoria = repo.obter(categoria_id)
    if _protegida(categoria) and entrada.nome.lower() != categoria.nome.lower():
        raise ErroNegocio(f'A categoria "{PADRAO}" é a padrão do sistema e não pode ser renomeada.')
    if _nome_em_uso(sessao, entrada.nome, ignorar_id=categoria_id):
        raise ErroNegocio("Já existe uma categoria com esse nome.", 409)
    categoria.nome = entrada.nome
    repo.salvar(categoria)
    return _saida(categoria, _contagens(sessao, Despesa), _contagens(sessao, GastoCartao))


def excluir(sessao: Session, categoria_id: int, mover_para: int | None = None) -> None:
    """Exclui a categoria. Se tiver lançamentos, eles vão para `mover_para`."""
    repo = _repo(sessao)
    categoria = repo.obter(categoria_id)
    if _protegida(categoria):
        raise ErroNegocio(f'A categoria "{PADRAO}" é a padrão do sistema e não pode ser excluída.')

    em_uso = sessao.scalar(select(func.count()).where(Despesa.categoria_id == categoria_id)) or 0
    em_uso += sessao.scalar(select(func.count()).where(GastoCartao.categoria_id == categoria_id)) or 0
    if em_uso:
        if mover_para is None:
            raise ErroNegocio(
                f"Esta categoria tem {em_uso} lançamento(s). Escolha para qual categoria movê-los.", 409
            )
        if mover_para == categoria_id or not repo.existe(mover_para):
            raise ErroNegocio("Categoria de destino inválida.")
        for modelo in (Despesa, GastoCartao):
            sessao.execute(
                update(modelo).where(modelo.categoria_id == categoria_id).values(categoria_id=mover_para)
            )
    repo.excluir(categoria)  # faz o commit da troca e da exclusão juntos
