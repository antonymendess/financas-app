"""Configurações lidas das variáveis de ambiente (nenhuma credencial no código)."""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# Em desenvolvimento lê o arquivo backend/.env; na Vercel as variáveis já existem
load_dotenv()


@dataclass(frozen=True)
class Configuracoes:
    database_url: str
    # Conexão do dono das tabelas (sem RLS) para login, convites e cron.
    # Vazia = usa a mesma do DATABASE_URL (antes de migrar para o papel app_api).
    database_url_sistema: str
    # Conexão do papel app_api (com RLS) para o dia a dia. Alternativa mais simples:
    # deixar DATABASE_URL como está (dono) e só acrescentar esta variável.
    database_url_app: str
    supabase_url: str
    allowed_email: str
    frontend_url: str
    cron_secret: str
    # Login da demonstração pública: os dados dele são recriados pelo cron todo dia
    demo_email: str
    em_producao: bool

    @property
    def origens_cors(self) -> list[str]:
        """Origens liberadas no CORS: o front publicado e, fora da Vercel, o localhost."""
        origens = [self.frontend_url] if self.frontend_url else []
        if not self.em_producao:
            origens += ["http://localhost:5173", "http://127.0.0.1:5173"]
        return origens


def _normalizar_url_banco(url: str) -> str:
    """Força o driver psycopg (v3) no SQLAlchemy, aceitando a URL copiada do Supabase."""
    for prefixo in ("postgresql://", "postgres://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes(
        database_url=_normalizar_url_banco(os.getenv("DATABASE_URL", "").strip()),
        database_url_sistema=_normalizar_url_banco(os.getenv("DATABASE_URL_SISTEMA", "").strip()),
        database_url_app=_normalizar_url_banco(os.getenv("DATABASE_URL_APP", "").strip()),
        supabase_url=os.getenv("SUPABASE_URL", "").strip().rstrip("/"),
        allowed_email=os.getenv("ALLOWED_EMAIL", "").strip().lower(),
        frontend_url=os.getenv("FRONTEND_URL", "").strip().rstrip("/"),
        cron_secret=os.getenv("CRON_SECRET", "").strip(),
        demo_email=os.getenv("DEMO_EMAIL", "").strip().lower(),
        # A Vercel define VERCEL_ENV automaticamente (production / preview)
        em_producao=bool(os.getenv("VERCEL_ENV")),
    )
