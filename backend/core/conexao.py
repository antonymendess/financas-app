"""Conexões com o PostgreSQL do Supabase, pensadas para ambiente serverless.

Duas conexões:
- a do dia a dia (papel `app_api`, sujeito ao RLS por casa);
- a do dono das tabelas (postgres), só para login, convites e cron.

Duas formas de configurar (a primeira é a mais simples):
1. DATABASE_URL = dono (como sempre foi) + DATABASE_URL_APP = app_api;
2. DATABASE_URL = app_api + DATABASE_URL_SISTEMA = dono.
Só com DATABASE_URL, as duas usam a mesma conexão (modo de antes do RLS).
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

import core.escopo  # noqa: F401  (registra o filtro automático por casa)
from core.config import obter_configuracoes


def _criar_engine(url: str) -> Engine:
    """- NullPool: cada request abre e fecha a conexão; quem faz o pool é o
      pooler do Supabase (porta 6543, modo transaction).
    - prepare_threshold=None: desativa prepared statements, que não funcionam
      no modo transaction do pooler.
    - hide_parameters: mensagens de erro não incluem os valores das consultas,
      para dados financeiros nunca irem parar nos logs.
    """
    if not url:
        raise RuntimeError("DATABASE_URL não configurada.")
    return create_engine(
        url,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
        hide_parameters=True,
    )


@lru_cache
def obter_engine() -> Engine:
    """Conexão das requisições da casa (com RLS quando houver app_api configurado)."""
    config = obter_configuracoes()
    return _criar_engine(config.database_url_app or config.database_url)


@lru_cache
def obter_engine_sistema() -> Engine:
    """Conexão do dono das tabelas (sem RLS)."""
    config = obter_configuracoes()
    if config.database_url_sistema:
        return _criar_engine(config.database_url_sistema)
    if config.database_url_app:
        return _criar_engine(config.database_url)  # DATABASE_URL continua sendo o dono
    return obter_engine()


@lru_cache
def _fabrica_sessoes() -> sessionmaker[Session]:
    return sessionmaker(bind=obter_engine(), expire_on_commit=False)


@lru_cache
def _fabrica_sistema() -> sessionmaker[Session]:
    return sessionmaker(bind=obter_engine_sistema(), expire_on_commit=False)


def abrir_sessao_da_casa(casa_id: int, usuario_id: str | None = None) -> Session:
    sessao = _fabrica_sessoes()()
    sessao.info["casa_id"] = casa_id
    sessao.info["usuario_id"] = usuario_id or ""
    return sessao


def obter_sessao_sistema() -> Iterator[Session]:
    """Sessão sem filtro de casa: só login, convites e rotas de infraestrutura."""
    sessao = _fabrica_sistema()()
    try:
        yield sessao
    finally:
        sessao.close()
