"""Casas (clientes), membros e convites.

- Cada login pertence a uma casa; cada casa tem até LIMITE_MEMBROS logins.
- Cliente novo só entra por convite 'nova_casa', criado pelo administrador
  (e-mail do ALLOWED_EMAIL). O dono da casa convida mais uma pessoa ('membro').
- O convite é um link com token secreto, vale CONVITE_DIAS dias e só pode ser
  aceito pelo e-mail para o qual foi feito.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.auth import Usuario
from core.erros import ErroNegocio
from repositories.modelos import Casa, Categoria, Convite, FormaPagamento, Membro

LIMITE_MEMBROS = 2
CONVITE_DIAS = 7

CATEGORIAS_PADRAO = (
    "Casa", "Alimentação", "Transporte", "Saúde", "Educação", "Lazer", "Tecnologia",
    "Vestuário", "Pets", "Financeiro", "Outros",
)
FORMAS_PADRAO = ("Pix", "Boleto", "Débito Automático", "Carnê / Loja", "Dinheiro")


def _agora() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------- login
def resolver_membro(sessao: Session, usuario: Usuario, admin: bool) -> tuple[Membro, Casa] | None:
    """Casa do usuário. No primeiro login do administrador, ele vira dono da casa
    com os dados de antes da separação por casas (legado)."""
    membro = sessao.scalar(select(Membro).where(Membro.usuario_id == uuid.UUID(usuario.id)))
    if membro is None and admin:
        legado = sessao.scalar(
            select(Casa).where(Casa.legado, ~select(Membro.id).where(Membro.casa_id == Casa.id).exists())
            .order_by(Casa.id)
        )
        if legado is not None:
            membro = Membro(casa_id=legado.id, usuario_id=uuid.UUID(usuario.id),
                            email=usuario.email, papel="dono")
            sessao.add(membro)
            sessao.commit()
    if membro is None:
        return None
    return membro, sessao.get(Casa, membro.casa_id)


def criar_casa(sessao: Session, nome: str) -> Casa:
    """Casa nova com as categorias e formas de pagamento padrão (sem commit)."""
    casa = Casa(nome=nome)
    sessao.add(casa)
    sessao.flush()
    sessao.add_all([Categoria(nome=n, casa_id=casa.id) for n in CATEGORIAS_PADRAO])
    sessao.add_all([FormaPagamento(nome=n, casa_id=casa.id) for n in FORMAS_PADRAO])
    return casa


# ---------------------------------------------------------------- casa e membros
def membros(sessao: Session, casa_id: int) -> list[Membro]:
    return list(sessao.scalars(
        select(Membro).where(Membro.casa_id == casa_id).order_by(Membro.papel, Membro.id)
    ))


def renomear(sessao: Session, casa_id: int, nome: str) -> Casa:
    casa = sessao.get(Casa, casa_id)
    casa.nome = nome
    sessao.commit()
    return casa


def remover_membro(sessao: Session, casa_id: int, membro_id: int) -> None:
    membro = sessao.scalar(select(Membro).where(Membro.id == membro_id, Membro.casa_id == casa_id))
    if membro is None:
        raise ErroNegocio("Pessoa não encontrada.", 404)
    if membro.papel == "dono":
        raise ErroNegocio("O dono da casa não pode ser removido.")
    sessao.delete(membro)
    sessao.commit()


# ---------------------------------------------------------------- convites
def _pendente(convite: Convite) -> bool:
    return convite.aceito_em is None and convite.expira_em > _agora()


def convites_visiveis(sessao: Session, casa_id: int, usuario_id: str) -> list[Convite]:
    """Convites da casa + os de cliente novo criados por este usuário (administrador)."""
    return list(sessao.scalars(
        select(Convite)
        .where((Convite.casa_id == casa_id) | (Convite.criado_por == uuid.UUID(usuario_id)))
        .order_by(Convite.criado_em.desc())
    ))


def _novo_convite(sessao: Session, **campos) -> Convite:
    convite = Convite(token=secrets.token_urlsafe(24),
                      expira_em=_agora() + timedelta(days=CONVITE_DIAS), **campos)
    sessao.add(convite)
    sessao.commit()
    return convite


def convidar_membro(sessao: Session, casa_id: int, usuario_id: str, email: str) -> Convite:
    """Dono chama mais uma pessoa para a própria casa (respeitando o limite de logins)."""
    email = email.strip().lower()
    atuais = membros(sessao, casa_id)
    if any(m.email.lower() == email for m in atuais):
        raise ErroNegocio("Essa pessoa já faz parte da casa.")
    pendentes = [c for c in convites_visiveis(sessao, casa_id, usuario_id)
                 if c.tipo == "membro" and _pendente(c)]
    if len(atuais) + len(pendentes) >= LIMITE_MEMBROS:
        raise ErroNegocio(
            f"O plano permite até {LIMITE_MEMBROS} pessoas por casa. "
            "Cancele um convite pendente ou remova alguém antes."
        )
    return _novo_convite(sessao, tipo="membro", casa_id=casa_id, email=email,
                         criado_por=uuid.UUID(usuario_id))


def convidar_cliente(sessao: Session, usuario_id: str, email: str, nome_casa: str | None) -> Convite:
    """Administrador convida um cliente novo (a casa é criada quando ele aceitar)."""
    return _novo_convite(sessao, tipo="nova_casa", casa_id=None, email=email.strip().lower(),
                         nome_casa=nome_casa, criado_por=uuid.UUID(usuario_id))


def cancelar_convite(sessao: Session, casa_id: int, usuario_id: str, convite_id: int) -> None:
    convite = next((c for c in convites_visiveis(sessao, casa_id, usuario_id) if c.id == convite_id), None)
    if convite is None:
        raise ErroNegocio("Convite não encontrado.", 404)
    if convite.aceito_em is not None:
        raise ErroNegocio("Esse convite já foi aceito.")
    sessao.delete(convite)
    sessao.commit()


def _por_token(sessao: Session, token: str) -> Convite:
    convite = sessao.scalar(select(Convite).where(Convite.token == token))
    if convite is None:
        raise ErroNegocio("Convite não encontrado. Confira o link.", 404)
    return convite


def ver_convite(sessao: Session, token: str) -> dict:
    """O que a tela do convite mostra antes do login (sem dados da casa)."""
    convite = _por_token(sessao, token)
    nome = convite.nome_casa
    if convite.tipo == "membro":
        nome = sessao.get(Casa, convite.casa_id).nome
    return {
        "tipo": convite.tipo,
        "email": convite.email,
        "nome_casa": nome,
        "situacao": ("aceito" if convite.aceito_em else "expirado" if convite.expira_em <= _agora()
                     else "pendente"),
    }


def aceitar(sessao: Session, token: str, usuario: Usuario) -> Casa:
    convite = _por_token(sessao, token)
    if convite.aceito_em is not None:
        raise ErroNegocio("Esse convite já foi usado.")
    if convite.expira_em <= _agora():
        raise ErroNegocio("Esse convite expirou. Peça um novo.")
    if usuario.email != convite.email.lower():
        raise ErroNegocio(f"Este convite é para {convite.email}. Entre com esse e-mail para aceitar.", 403)
    if sessao.scalar(select(Membro).where(Membro.usuario_id == uuid.UUID(usuario.id))) is not None:
        raise ErroNegocio("Seu login já faz parte de uma casa.")

    if convite.tipo == "nova_casa":
        casa = criar_casa(sessao, convite.nome_casa or f"Casa de {usuario.email.split('@')[0]}")
        papel = "dono"
    else:
        casa = sessao.get(Casa, convite.casa_id)
        quantos = sessao.scalar(select(func.count()).where(Membro.casa_id == casa.id))
        if quantos >= LIMITE_MEMBROS:
            raise ErroNegocio(f"Essa casa já tem {LIMITE_MEMBROS} pessoas.")
        papel = "membro"
    sessao.add(Membro(casa_id=casa.id, usuario_id=uuid.UUID(usuario.id), email=usuario.email,
                      papel=papel))
    convite.aceito_em = _agora()
    convite.aceito_por = uuid.UUID(usuario.id)
    sessao.commit()
    return casa
