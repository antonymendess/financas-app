"""Rotas de infraestrutura: saúde do serviço e cron que mantém o Supabase ativo
(e, na demonstração, recria os dados fictícios)."""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import obter_configuracoes
from core.contexto import esquecer
from core.db import obter_sessao_sistema
from services import demo
from services.calculos import hoje

router = APIRouter(tags=["sistema"])


@router.get("/health")
def health(sessao: Session = Depends(obter_sessao_sistema)):
    """Rota pública: confirma que a API está de pé e o banco responde."""
    sessao.execute(text("select 1"))
    return {"status": "ok"}


@router.get("/cron/keepalive")
def keepalive(
    authorization: str = Header(default=""),
    sessao: Session = Depends(obter_sessao_sistema),
):
    """Chamado 1x por dia pelo Vercel Cron para o Supabase não pausar o projeto.

    A Vercel envia automaticamente "Authorization: Bearer <CRON_SECRET>".
    """
    config = obter_configuracoes()
    segredo = config.cron_secret
    esperado = f"Bearer {segredo}"
    # compare_digest evita ataques de tempo na comparação do segredo
    if not segredo or not hmac.compare_digest(authorization.encode(), esperado.encode()):
        raise HTTPException(status_code=401, detail="Não autorizado.")
    sessao.execute(text("select count(*) from categorias"))
    if config.demo_email and config.demo_email != config.allowed_email:
        usuario_id = demo.usuario_por_email(sessao, config.demo_email)
        if usuario_id is not None:
            demo.recriar(sessao, usuario_id, config.demo_email, hoje())
            esquecer(str(usuario_id))
    return {"status": "ok"}
