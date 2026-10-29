"""Isolamento por casa na aplicação (a primeira trava; a segunda é o RLS do banco).

Uma sessão "da casa" tem `session.info["casa_id"]`. Para ela:
- toda consulta, UPDATE e DELETE do ORM ganha `casa_id = <casa>` em cada tabela de
  dados (inclusive em joins e carregamento de relacionamentos);
- todo objeto novo recebe o casa_id da sessão (e não pode ser de outra casa);
- no início de cada transação, o banco recebe `app.casa_id` / `app.usuario_id`,
  usados pelas policies de RLS (sql/011).

Sessão sem casa_id ("de sistema") não é filtrada: usada só no login, nos convites
e nas rotas de infraestrutura.
"""

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from core.erros import ErroNegocio
from repositories.modelos import ComCasa


@event.listens_for(Session, "do_orm_execute")
def _filtrar_por_casa(estado: ORMExecuteState) -> None:
    casa_id = estado.session.info.get("casa_id")
    if casa_id is None:
        return
    if estado.is_select or estado.is_update or estado.is_delete:
        estado.statement = estado.statement.options(
            with_loader_criteria(ComCasa, lambda cls: cls.casa_id == casa_id, include_aliases=True)
        )


@event.listens_for(Session, "before_flush")
def _carimbar_casa(sessao: Session, _contexto, _instancias) -> None:
    casa_id = sessao.info.get("casa_id")
    if casa_id is None:
        return
    for objeto in list(sessao.new) + list(sessao.dirty):
        if not isinstance(objeto, ComCasa):
            continue
        if objeto.casa_id is None:
            objeto.casa_id = casa_id
        elif objeto.casa_id != casa_id:
            # Nunca deveria acontecer: protege contra mover dados entre casas
            raise ErroNegocio("Registro de outra casa.", 404)


@event.listens_for(Session, "after_begin")
def _informar_banco(sessao: Session, _transacao, conexao) -> None:
    casa_id = sessao.info.get("casa_id")
    if casa_id is None:
        return
    conexao.exec_driver_sql(
        "select set_config('app.casa_id', %s, true), set_config('app.usuario_id', %s, true)",
        (str(casa_id), str(sessao.info.get("usuario_id", ""))),
    )
