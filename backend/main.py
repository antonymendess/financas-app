"""Ponto de entrada da API (a Vercel detecta a variável `app` automaticamente)."""

import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.contexto import contexto_casa
from core.config import obter_configuracoes
from core.erros import registrar_tratadores
from routers import (
    anotacoes, cartoes, casa, categorias, comissoes, conferencias, despesas, metas, painel, receitas,
    responsaveis, sistema,
)

# Log enxuto: nada de tokens, corpos de requisição ou dados financeiros
logging.basicConfig(level=logging.WARNING)

config = obter_configuracoes()

app = FastAPI(
    title="Controle Financeiro",
    # Documentação interativa só fora de produção
    docs_url=None if config.em_producao else "/docs",
    redoc_url=None,
    openapi_url=None if config.em_producao else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.origens_cors,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

registrar_tratadores(app)

# Rotas públicas (/health), protegidas por segredo próprio (/cron) e o aceite de
# convite (exige login, mas o usuário ainda não tem casa)
app.include_router(sistema.router)
app.include_router(casa.router_convites)

# Todas as demais exigem login de alguém que faz parte de uma casa
protegido = [Depends(contexto_casa)]
for roteador in (
    painel.router, despesas.router, receitas.router, comissoes.router,
    comissoes.router_negociacoes, cartoes.router, anotacoes.router, metas.router,
    responsaveis.router, conferencias.router, categorias.router, casa.router,
):
    app.include_router(roteador, dependencies=protegido)
