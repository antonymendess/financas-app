"""Validação do token do Supabase Auth em todas as rotas protegidas.

O front faz login no Supabase e envia "Authorization: Bearer <access_token>".
Aqui conferimos a assinatura do JWT com as chaves públicas do projeto (JWKS),
a validade e o público ("authenticated"). A casa do usuário é resolvida depois
(core/contexto.py). Nunca registramos o token em log.
"""

import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import obter_configuracoes

# Algoritmos assimétricos usados pelas "JWT Signing Keys" do Supabase
_ALGORITMOS = ["ES256", "RS256"]

_esquema_bearer = HTTPBearer(auto_error=False)


@lru_cache
def _cliente_jwks() -> jwt.PyJWKClient:
    """Cliente que baixa e mantém em cache as chaves públicas do projeto."""
    url = f"{obter_configuracoes().supabase_url}/auth/v1/.well-known/jwks.json"
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=3600, timeout=10)


def obter_chave_publica(token: str):
    """Isolado numa função para os testes poderem substituir a origem da chave."""
    return _cliente_jwks().get_signing_key_from_jwt(token).key


@dataclass(frozen=True)
class Usuario:
    id: str  # uuid do usuário no Supabase Auth
    email: str


def _nao_autenticado(mensagem: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=mensagem,
        headers={"WWW-Authenticate": "Bearer"},
    )


def usuario_autenticado(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
) -> Usuario:
    """Dependência do FastAPI: devolve o usuário do token ou interrompe com 401."""
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise _nao_autenticado("Faça login para continuar.")

    config = obter_configuracoes()
    token = credenciais.credentials
    try:
        dados = jwt.decode(
            token,
            obter_chave_publica(token),
            algorithms=_ALGORITMOS,
            audience="authenticated",
            issuer=f"{config.supabase_url}/auth/v1",
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise _nao_autenticado("Sessão expirada. Entre novamente.") from None
    except (jwt.PyJWTError, ValueError):
        # Inclui assinatura inválida, chave desconhecida e falha ao buscar o JWKS
        raise _nao_autenticado("Token inválido. Entre novamente.") from None

    email = str(dados.get("email", "")).strip().lower()
    try:
        usuario_id = str(uuid.UUID(str(dados["sub"])))
    except ValueError:
        raise _nao_autenticado("Token inválido. Entre novamente.") from None
    if not email:
        raise _nao_autenticado("Token sem e-mail. Entre novamente.")
    return Usuario(usuario_id, email)
