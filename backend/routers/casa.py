"""Endpoints da casa (membros e convites) e do aceite de convite."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.auth import Usuario, usuario_autenticado
from core.contexto import Contexto, contexto_casa, esquecer
from core.db import obter_sessao, obter_sessao_sistema
from core.erros import ErroNegocio
from schemas.casas import (
    CasaEntrada, ConviteClienteEntrada, ConviteMembroEntrada, ConvitePublico, ConviteSaida, EuSaida,
)
from services import casas as servico

# Protegido pela casa do usuário (incluído em main.py junto com as outras rotas)
router = APIRouter(tags=["casa"])
# Aceite de convite: quem aceita ainda não tem casa
router_convites = APIRouter(prefix="/convites", tags=["convites"])


def _so_dono(contexto: Contexto) -> None:
    if contexto.papel != "dono":
        raise ErroNegocio("Só o dono da casa pode fazer isso.", 403)


@router.get("/eu", response_model=EuSaida)
def eu(contexto: Contexto = Depends(contexto_casa), sessao: Session = Depends(obter_sessao)):
    """Quem está logado, de qual casa e quem mais faz parte dela."""
    return {
        "email": contexto.email, "admin": contexto.admin, "papel": contexto.papel,
        "casa_id": contexto.casa_id, "casa_nome": contexto.casa_nome,
        "membros": servico.membros(sessao, contexto.casa_id),
        "limite_membros": servico.LIMITE_MEMBROS,
    }


@router.put("/casa", status_code=status.HTTP_204_NO_CONTENT)
def renomear(entrada: CasaEntrada, contexto: Contexto = Depends(contexto_casa),
             sessao: Session = Depends(obter_sessao)):
    _so_dono(contexto)
    servico.renomear(sessao, contexto.casa_id, entrada.nome)
    esquecer()  # o nome da casa vem guardado junto


@router.delete("/casa/membros/{membro_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_membro(membro_id: int, contexto: Contexto = Depends(contexto_casa),
                   sessao: Session = Depends(obter_sessao)):
    _so_dono(contexto)
    servico.remover_membro(sessao, contexto.casa_id, membro_id)
    esquecer()  # nesta instância, quem saiu perde o acesso na hora


@router.get("/casa/convites", response_model=list[ConviteSaida])
def convites(contexto: Contexto = Depends(contexto_casa), sessao: Session = Depends(obter_sessao)):
    return servico.convites_visiveis(sessao, contexto.casa_id, contexto.usuario_id)


@router.post("/casa/convites", response_model=ConviteSaida, status_code=status.HTTP_201_CREATED)
def convidar_membro(entrada: ConviteMembroEntrada, contexto: Contexto = Depends(contexto_casa),
                    sessao: Session = Depends(obter_sessao)):
    """Dono chama mais uma pessoa para a casa (ex.: cônjuge)."""
    _so_dono(contexto)
    return servico.convidar_membro(sessao, contexto.casa_id, contexto.usuario_id, entrada.email)


@router.post("/admin/convites", response_model=ConviteSaida, status_code=status.HTTP_201_CREATED)
def convidar_cliente(entrada: ConviteClienteEntrada, contexto: Contexto = Depends(contexto_casa),
                     sessao: Session = Depends(obter_sessao)):
    """Administrador convida um cliente novo (ganha uma casa própria ao aceitar)."""
    if not contexto.admin:
        raise ErroNegocio("Só o administrador pode convidar clientes novos.", 403)
    return servico.convidar_cliente(sessao, contexto.usuario_id, entrada.email, entrada.nome_casa)


@router.delete("/casa/convites/{convite_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar(convite_id: int, contexto: Contexto = Depends(contexto_casa),
             sessao: Session = Depends(obter_sessao)):
    servico.cancelar_convite(sessao, contexto.casa_id, contexto.usuario_id, convite_id)


# ---------------------------------------------------------------- aceite (sem casa ainda)
@router_convites.get("/{token}", response_model=ConvitePublico)
def ver(token: str, sessao: Session = Depends(obter_sessao_sistema)):
    """Público: a tela do convite mostra para quem é antes de criar a conta."""
    return servico.ver_convite(sessao, token)


@router_convites.post("/{token}/aceitar", status_code=status.HTTP_204_NO_CONTENT)
def aceitar(token: str, usuario: Usuario = Depends(usuario_autenticado),
            sessao: Session = Depends(obter_sessao_sistema)):
    servico.aceitar(sessao, token, usuario)
