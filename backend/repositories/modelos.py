"""Mapeamento ORM das tabelas criadas pelas migrações em sql/.

O banco é a fonte da verdade (constraints, defaults e coluna gerada ficam no SQL);
aqui só descrevemos as colunas para o SQLAlchemy.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Computed, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ComCasa:
    """Linha que pertence a uma casa (cliente). O filtro por casa é automático
    (ver core/escopo.py) e o banco também bloqueia outras casas (sql/011)."""

    casa_id: Mapped[int] = mapped_column(ForeignKey("casas.id", ondelete="CASCADE"))


class Casa(Base):
    """Cliente: os dados de uma família, com até 2 logins."""

    __tablename__ = "casas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    legado: Mapped[bool] = mapped_column(default=False)
    assinatura_status: Mapped[str] = mapped_column(default="teste")
    assinatura_ate: Mapped[date | None]
    criada_em: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Membro(Base):
    """Login do Supabase Auth ligado a uma casa."""

    __tablename__ = "membros"

    id: Mapped[int] = mapped_column(primary_key=True)
    casa_id: Mapped[int] = mapped_column(ForeignKey("casas.id", ondelete="CASCADE"))
    usuario_id: Mapped[uuid.UUID]
    email: Mapped[str]
    papel: Mapped[str] = mapped_column(default="membro")
    criado_em: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Convite(Base):
    """Link de convite: cliente novo ('nova_casa') ou mais uma pessoa na casa ('membro')."""

    __tablename__ = "convites"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str]
    tipo: Mapped[str]
    casa_id: Mapped[int | None] = mapped_column(ForeignKey("casas.id", ondelete="CASCADE"))
    email: Mapped[str]
    nome_casa: Mapped[str | None]
    criado_por: Mapped[uuid.UUID]
    criado_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
    expira_em: Mapped[datetime]
    aceito_em: Mapped[datetime | None]
    aceito_por: Mapped[uuid.UUID | None]


class Responsavel(ComCasa, Base):
    """Pessoa da casa; receitas e contas sem responsável são do "Conjunto"."""

    __tablename__ = "responsaveis"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Cartao(ComCasa, Base):
    __tablename__ = "cartoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    dia_fechamento: Mapped[int | None]
    dia_vencimento: Mapped[int | None]
    responsavel_id: Mapped[int | None] = mapped_column(
        ForeignKey("responsaveis.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Categoria(ComCasa, Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]


class FormaPagamento(ComCasa, Base):
    __tablename__ = "formas_pagamento"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    cartao_id: Mapped[int | None] = mapped_column(ForeignKey("cartoes.id"))


class Despesa(ComCasa, Base):
    __tablename__ = "despesas"

    id: Mapped[int] = mapped_column(primary_key=True)
    descricao: Mapped[str]
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"))
    forma_pagamento_id: Mapped[int] = mapped_column(ForeignKey("formas_pagamento.id"))
    valor_mensal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    num_parcelas: Mapped[int | None]
    primeira_cobranca: Mapped[date]
    cancelada_em: Mapped[date | None]
    dia_vencimento: Mapped[int | None]
    observacao: Mapped[str | None]
    responsavel_id: Mapped[int | None] = mapped_column(
        ForeignKey("responsaveis.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Receita(ComCasa, Base):
    __tablename__ = "receitas"

    id: Mapped[int] = mapped_column(primary_key=True)
    descricao: Mapped[str]
    tipo: Mapped[str]
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    recorrente: Mapped[bool]
    dia_recebimento: Mapped[int | None]
    data_inicio: Mapped[date]
    data_fim: Mapped[date | None]
    responsavel_id: Mapped[int | None] = mapped_column(
        ForeignKey("responsaveis.id", ondelete="SET NULL")
    )
    # Preenchido quando a receita foi lançada ao marcar uma parcela de comissão
    comissao_parcela_id: Mapped[int | None] = mapped_column(
        ForeignKey("comissao_parcelas.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Comissao(ComCasa, Base):
    __tablename__ = "comissoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente: Mapped[str]
    telefone: Mapped[str | None]
    mes_fechamento: Mapped[date]
    valor_implantacao: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    mensalidade: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    percentual: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    # Coluna gerada pelo banco: implantação × percentual / 100
    valor_comissao: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        Computed("round(valor_implantacao * percentual / 100, 2)", persisted=True),
    )
    num_parcelas: Mapped[int]
    data_primeira_parcela: Mapped[date]
    observacao: Mapped[str | None]
    responsavel_id: Mapped[int | None] = mapped_column(
        ForeignKey("responsaveis.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    parcelas: Mapped[list["ComissaoParcela"]] = relationship(
        back_populates="comissao",
        cascade="all, delete-orphan",
        order_by="ComissaoParcela.numero",
        lazy="selectin",
    )


class ComissaoParcela(ComCasa, Base):
    __tablename__ = "comissao_parcelas"

    id: Mapped[int] = mapped_column(primary_key=True)
    comissao_id: Mapped[int] = mapped_column(ForeignKey("comissoes.id", ondelete="CASCADE"))
    numero: Mapped[int]
    data_prevista: Mapped[date]
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paga: Mapped[bool] = mapped_column(default=False)
    paga_em: Mapped[date | None]

    comissao: Mapped[Comissao] = relationship(back_populates="parcelas")
    # Receita lançada a partir desta parcela (se houver)
    receita: Mapped[Receita | None] = relationship(
        primaryjoin="Receita.comissao_parcela_id == ComissaoParcela.id",
        viewonly=True,
        lazy="selectin",
        uselist=False,
    )

    @property
    def receita_id(self) -> int | None:
        return self.receita.id if self.receita else None


class GastoCartao(ComCasa, Base):
    __tablename__ = "gastos_cartao"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_compra: Mapped[date]
    descricao: Mapped[str]
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"))
    cartao_id: Mapped[int] = mapped_column(ForeignKey("cartoes.id"))
    valor_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    num_parcelas: Mapped[int] = mapped_column(default=1)
    responsavel_id: Mapped[int | None] = mapped_column(
        ForeignKey("responsaveis.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Anotacao(ComCasa, Base):
    __tablename__ = "anotacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    texto: Mapped[str]
    data: Mapped[date | None]
    valor: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    pessoa: Mapped[str | None]
    tipo: Mapped[str] = mapped_column(default="Lembrete")
    concluida: Mapped[bool] = mapped_column(default=False)
    entra_no_saldo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class DespesaPagamento(ComCasa, Base):
    """Conta marcada como paga em um mês (competencia = 1º dia do mês)."""

    __tablename__ = "despesa_pagamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    despesa_id: Mapped[int] = mapped_column(ForeignKey("despesas.id", ondelete="CASCADE"))
    competencia: Mapped[date]
    pago_em: Mapped[date]


class DespesaResponsavel(ComCasa, Base):
    """Troca de quem paga a conta, valendo a partir de um mês (1º dia) até a próxima."""

    __tablename__ = "despesa_responsaveis"

    id: Mapped[int] = mapped_column(primary_key=True)
    despesa_id: Mapped[int] = mapped_column(ForeignKey("despesas.id", ondelete="CASCADE"))
    a_partir_de: Mapped[date]
    responsavel_id: Mapped[int | None] = mapped_column(
        ForeignKey("responsaveis.id", ondelete="SET NULL")
    )


class FaturaPagamento(ComCasa, Base):
    """Fatura de cartão marcada como paga em um mês."""

    __tablename__ = "fatura_pagamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cartao_id: Mapped[int] = mapped_column(ForeignKey("cartoes.id", ondelete="CASCADE"))
    competencia: Mapped[date]
    pago_em: Mapped[date]


class Meta(ComCasa, Base):
    """Meta de economia (cofrinho): quanto juntar e até quando."""

    __tablename__ = "metas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    valor_alvo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    data_alvo: Mapped[date | None]
    # Regra antiga de quanto guardar por mês; o cofrinho não usa mais (fica no banco)
    regra: Mapped[str] = mapped_column(default="pct_sobra")
    regra_valor: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    ativa: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class MetaMovimento(ComCasa, Base):
    """Dinheiro guardado (positivo) ou retirado (negativo) de uma meta."""

    __tablename__ = "meta_movimentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    meta_id: Mapped[int] = mapped_column(ForeignKey("metas.id", ondelete="CASCADE"))
    data: Mapped[date]
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descricao: Mapped[str | None]


class MetaMesFechado(ComCasa, Base):
    """Mês encerrado numa meta: o que faltou guardar não fica pendente."""

    __tablename__ = "meta_meses_fechados"

    id: Mapped[int] = mapped_column(primary_key=True)
    meta_id: Mapped[int] = mapped_column(ForeignKey("metas.id", ondelete="CASCADE"))
    competencia: Mapped[date]


class Conferencia(ComCasa, Base):
    """Saldo real do banco informado numa data (por pessoa ou tudo junto)."""

    __tablename__ = "conferencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date]
    junto: Mapped[bool] = mapped_column(default=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    ja_entrou: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    saldos: Mapped[list["ConferenciaSaldo"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class ConferenciaSaldo(ComCasa, Base):
    __tablename__ = "conferencia_saldos"

    id: Mapped[int] = mapped_column(primary_key=True)
    conferencia_id: Mapped[int] = mapped_column(ForeignKey("conferencias.id", ondelete="CASCADE"))
    responsavel_id: Mapped[int] = mapped_column(ForeignKey("responsaveis.id", ondelete="CASCADE"))
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class Negociacao(ComCasa, Base):
    """Possível fechamento; ao fechar, vira uma comissão."""

    __tablename__ = "negociacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente: Mapped[str]
    telefone: Mapped[str | None]
    etapa: Mapped[str] = mapped_column(default="Contato inicial")
    probabilidade: Mapped[int | None]
    valor_implantacao: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    mensalidade: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    percentual: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("25"))
    num_parcelas: Mapped[int] = mapped_column(default=1)
    previsao_fechamento: Mapped[date | None]
    ultimo_contato: Mapped[date | None]
    proxima_acao: Mapped[str | None]
    observacao: Mapped[str | None]
    comissao_id: Mapped[int | None] = mapped_column(ForeignKey("comissoes.id", ondelete="SET NULL"))
    transferido_em: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
