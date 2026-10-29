"""Migrações num PostgreSQL real: aplicam do zero, são idempotentes e batem com o ORM."""

import psycopg
from sqlalchemy import inspect

from repositories.modelos import Base
from scripts.migrar import aplicar_pendentes, conectar, listar_migracoes, marcar, pendentes


def test_todas_as_migracoes_aplicam_num_banco_vazio(banco_vazio):
    feitas = aplicar_pendentes(banco_vazio)
    assert feitas == [m.nome for m in listar_migracoes()]
    assert aplicar_pendentes(banco_vazio) == []  # segunda vez: nada pendente


def test_cada_migracao_pode_rodar_de_novo_sem_erro(banco_vazio):
    """Idempotência: quem já rodou um SQL à mão pode rodar de novo sem quebrar nada."""
    aplicar_pendentes(banco_vazio)
    with psycopg.connect(banco_vazio) as conexao:
        for migracao in listar_migracoes():
            conexao.execute(migracao.caminho.read_text(encoding="utf-8"))


def test_marcar_registra_sem_executar(banco_vazio):
    migracoes = listar_migracoes()
    with conectar(banco_vazio) as conexao:
        marcar(conexao, migracoes[0])
        assert migracoes[0] not in pendentes(conexao, migracoes)
        tabelas = {r[0] for r in conexao.execute(
            "select tablename from pg_tables where schemaname = 'public'"
        )}
    assert "cartoes" not in tabelas  # 001 só foi marcada, não executada


def test_dados_iniciais_existem(sessao):
    from repositories.modelos import Categoria, FormaPagamento

    nomes = {c.nome for c in sessao.query(Categoria)}
    assert "Outros" in nomes
    assert sessao.query(FormaPagamento).filter_by(nome="Pix").count() == 1


def test_modelos_do_orm_batem_com_as_tabelas(sessao):
    """Toda coluna mapeada no código existe no banco (pega esquecimento de migração)."""
    inspetor = inspect(sessao.get_bind())
    for tabela in Base.metadata.sorted_tables:
        no_banco = {c["name"] for c in inspetor.get_columns(tabela.name)}
        no_codigo = {c.name for c in tabela.columns}
        assert no_codigo <= no_banco, f"{tabela.name}: faltam {no_codigo - no_banco}"


def test_rls_ligado_em_todas_as_tabelas(sessao):
    sem_rls = [
        nome for nome, ligado in sessao.connection().exec_driver_sql(
            "select relname, relrowsecurity from pg_class c "
            "join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' and c.relkind = 'r'"
        )
        if not ligado
    ]
    assert sem_rls == []
