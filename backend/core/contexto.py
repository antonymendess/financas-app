"""Quem está usando o app e de qual casa (resolvido a cada requisição).

A casa de cada login fica guardada na memória da instância por CACHE_SEGUNDOS: assim
a maioria das requisições não abre uma conexão extra só para descobrir a casa. Quem
for removido de uma casa perde o acesso em no máximo esse tempo.
"""

import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.auth import Usuario, usuario_autenticado
from core.config import obter_configuracoes
from core.conexao import obter_sessao_sistema

# O front reconhece este texto para mostrar a tela "você ainda não tem acesso"
SEM_CASA = "Você ainda não tem acesso. Peça um convite para usar o app."
CACHE_SEGUNDOS = 60

_cache: dict[str, tuple[float, "Contexto"]] = {}


@dataclass(frozen=True)
class Contexto:
    usuario_id: str
    email: str
    casa_id: int
    casa_nome: str
    papel: str  # "dono" | "membro"
    admin: bool  # pode convidar clientes novos (e-mail do ALLOWED_EMAIL)


def eh_admin(usuario: Usuario) -> bool:
    admin = obter_configuracoes().allowed_email
    return bool(admin) and usuario.email == admin


def esquecer(usuario_id: str | None = None) -> None:
    """Descarta a casa guardada (de um login ou de todos), ex.: ao remover alguém."""
    if usuario_id is None:
        _cache.clear()
    else:
        _cache.pop(usuario_id, None)


def contexto_casa(
    usuario: Usuario = Depends(usuario_autenticado),
    sessao: Session = Depends(obter_sessao_sistema),
) -> Contexto:
    """Dependência do FastAPI: a casa do usuário, ou 403 se ele não tiver uma."""
    from services.casas import resolver_membro  # evita import circular na carga do app

    guardado = _cache.get(usuario.id)
    if guardado and guardado[0] > time.monotonic() and guardado[1].email == usuario.email:
        return guardado[1]

    encontrado = resolver_membro(sessao, usuario, admin=eh_admin(usuario))
    if encontrado is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SEM_CASA)
    membro, casa = encontrado
    contexto = Contexto(
        usuario_id=usuario.id, email=usuario.email, casa_id=casa.id, casa_nome=casa.nome,
        papel=membro.papel, admin=eh_admin(usuario),
    )
    _cache[usuario.id] = (time.monotonic() + CACHE_SEGUNDOS, contexto)  # só quem tem casa
    return contexto
