"""Configuração dos testes: variáveis de ambiente fictícias (sem banco real)."""

import os

os.environ.update({
    "DATABASE_URL": "postgresql://usuario:senha@localhost:6543/teste",
    "SUPABASE_URL": "https://projeto-teste.supabase.co",
    "ALLOWED_EMAIL": "eu@exemplo.com",
    "FRONTEND_URL": "https://meu-front.vercel.app",
    "CRON_SECRET": "segredo-de-teste",
})
