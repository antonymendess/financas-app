"""Dependências de sessão usadas pelas rotas.

- obter_sessao: sessão da casa do usuário logado (filtrada por casa + RLS);
- obter_sessao_sistema: sem filtro, só para login, convites e infraestrutura.
As conexões em si ficam em core/conexao.py.
"""

from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from core.conexao import abrir_sessao_da_casa, obter_engine, obter_sessao_sistema  # noqa: F401
from core.contexto import Contexto, contexto_casa


def obter_sessao(contexto: Contexto = Depends(contexto_casa)) -> Iterator[Session]:
    """Dependência do FastAPI: sessão da casa do usuário logado, fechada no final."""
    sessao = abrir_sessao_da_casa(contexto.casa_id, contexto.usuario_id)
    try:
        yield sessao
    finally:
        sessao.close()
