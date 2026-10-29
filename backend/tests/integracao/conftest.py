"""Banco PostgreSQL de verdade para testes de integração (sem Docker).

Usa o pacote `pgserver` (PostgreSQL embutido, instalado via pip). Sem ele, os testes
desta pasta são pulados. Cada sessão de testes cria um banco novo e aplica todas as
migrações de sql/, imitando o que o Supabase tem (papéis anon e authenticated).
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

pgserver = pytest.importorskip("pgserver", reason="instale pgserver para os testes com banco real")

# Papéis que o Supabase cria e que as migrações usam nos "revoke"
PREPARO_SUPABASE = """
do $$ begin
    if not exists (select from pg_roles where rolname = 'anon') then create role anon; end if;
    if not exists (select from pg_roles where rolname = 'authenticated') then
        create role authenticated;
    end if;
end $$;
"""


@pytest.fixture(scope="session")
def servidor(tmp_path_factory):
    srv = pgserver.get_server(tmp_path_factory.mktemp("pg"), cleanup_mode="stop")
    srv.psql(PREPARO_SUPABASE)
    yield srv


def _novo_banco(servidor) -> str:
    nome = f"teste_{uuid.uuid4().hex[:8]}"
    servidor.psql(f"create database {nome};")
    return servidor.get_uri(nome)


@pytest.fixture
def banco_vazio(servidor) -> str:
    """URL de um banco novo, sem nenhuma migração."""
    return _novo_banco(servidor)


@pytest.fixture(scope="session")
def banco_migrado(servidor) -> str:
    """URL de um banco com todas as migrações aplicadas (compartilhado na sessão)."""
    from scripts.migrar import aplicar_pendentes

    url = _novo_banco(servidor)
    aplicar_pendentes(url)
    return url


def _engine(url: str):
    return create_engine(
        url.replace("postgresql://", "postgresql+psycopg://", 1),
        poolclass=NullPool, connect_args={"prepare_threshold": None},
    )


@pytest.fixture
def conexao(banco_migrado):
    """Uma conexão com transação aberta; tudo é desfeito ao final do teste."""
    engine = _engine(banco_migrado)
    con = engine.connect()
    transacao = con.begin()
    yield con
    transacao.rollback()
    con.close()
    engine.dispose()


@pytest.fixture
def abrir(conexao):
    """Fábrica de sessões na mesma transação: abrir(casa_id) = sessão da casa;
    abrir(None) = sessão de sistema. Os commit() dos services viram savepoints."""
    abertas = []

    def _abrir(casa_id=None, usuario_id=""):
        s = sessionmaker(bind=conexao, join_transaction_mode="create_savepoint",
                         expire_on_commit=False)()
        if casa_id is not None:
            s.info["casa_id"] = casa_id
            s.info["usuario_id"] = usuario_id
        abertas.append(s)
        return s

    yield _abrir
    # Não fecha uma a uma: as sessões dividem a conexão e o rollback da fixture
    # `conexao` desfaz tudo de uma vez
    abertas.clear()


@pytest.fixture
def casa_legado(abrir) -> int:
    from repositories.modelos import Casa

    return abrir().query(Casa).filter_by(legado=True).one().id


@pytest.fixture
def sessao(abrir, casa_legado):
    """Sessão da casa que recebeu os dados de antes da separação (a do dono atual)."""
    return abrir(casa_legado)
