"""Estruturas de dados simples usadas pela projeção (independentes do banco).

O repositório converte as linhas do banco nessas estruturas; os testes podem
criá-las diretamente, sem precisar de PostgreSQL.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from services.calculos import Mes


def responsavel_em(
    padrao: int | None, trocas: tuple[tuple[Mes, int | None], ...] | list, mes: Mes
) -> int | None:
    """Quem paga em `mes`: a última troca feita até ele; sem troca, o `padrao`."""
    atual = padrao
    for inicio, responsavel_id in trocas:
        if inicio > mes:
            break
        atual = responsavel_id
    return atual


@dataclass(frozen=True)
class ResponsavelDados:
    id: int
    nome: str


@dataclass(frozen=True)
class CartaoDados:
    id: int
    nome: str
    dia_fechamento: int | None = None
    dia_vencimento: int | None = None
    responsavel_id: int | None = None  # dono do cartão

    @property
    def tem_dias(self) -> bool:
        return self.dia_fechamento is not None and self.dia_vencimento is not None


@dataclass(frozen=True)
class DespesaDados:
    id: int
    descricao: str
    valor_mensal: Decimal
    primeira_cobranca: date
    categoria: str = "Outros"
    forma: str = "Pix"
    cartao_id: int | None = None  # preenchido quando a forma de pagamento é um cartão
    num_parcelas: int | None = None  # None = conta fixa
    cancelada_em: date | None = None
    dia_vencimento: int | None = None
    responsavel_id: int | None = None  # None = conjunto (ou o dono do cartão)
    # Trocas de quem paga: (mês a partir do qual vale, pessoa ou None = conjunto), em ordem
    trocas: tuple[tuple[Mes, int | None], ...] = ()

    def responsavel_no_mes(self, mes: Mes) -> int | None:
        """Quem paga no mês: a última troca até esse mês ou, sem troca, o da despesa."""
        return responsavel_em(self.responsavel_id, self.trocas, mes)

    @property
    def dia(self) -> int:
        """Dia de vencimento; se não informado, o mesmo dia da 1ª cobrança."""
        return self.dia_vencimento or self.primeira_cobranca.day


@dataclass(frozen=True)
class ReceitaDados:
    id: int
    descricao: str
    valor: Decimal
    data_inicio: date
    tipo: str = "Salário"
    recorrente: bool = True
    dia_recebimento: int | None = None
    data_fim: date | None = None
    responsavel_id: int | None = None  # None = conjunto


@dataclass(frozen=True)
class ParcelaComissaoDados:
    id: int
    comissao_id: int
    cliente: str
    numero: int
    total_parcelas: int
    data_prevista: date
    valor: Decimal
    paga: bool = False
    # Já virou uma receita cadastrada: não soma de novo na previsão
    lancada_como_receita: bool = False
    responsavel_id: int | None = None  # quem recebe a comissão
    paga_em: date | None = None


@dataclass(frozen=True)
class GastoCartaoDados:
    id: int
    descricao: str
    data_compra: date
    cartao_id: int
    valor_total: Decimal
    num_parcelas: int = 1
    categoria: str | None = None
    responsavel_id: int | None = None  # None = dono do cartão


@dataclass(frozen=True)
class AnotacaoDados:
    id: int
    texto: str
    data: date | None = None
    valor: Decimal | None = None
    pessoa: str | None = None
    tipo: str = "Lembrete"
    concluida: bool = False
    entra_no_saldo: bool = False


@dataclass(frozen=True)
class ConferenciaDados:
    """Saldo real informado numa data. `saldos` vazio = tudo junto (só o total)."""

    id: int
    data: date
    total: Decimal
    junto: bool = False
    saldos: dict[int, Decimal] = field(default_factory=dict)  # responsavel_id -> saldo
    ja_entrou: frozenset[str] = frozenset()  # receitas que caíram antes do previsto


@dataclass
class DadosFinanceiros:
    """Tudo o que a projeção precisa, carregado do banco de uma só vez."""

    cartoes: list[CartaoDados] = field(default_factory=list)
    despesas: list[DespesaDados] = field(default_factory=list)
    receitas: list[ReceitaDados] = field(default_factory=list)
    parcelas_comissao: list[ParcelaComissaoDados] = field(default_factory=list)
    gastos_cartao: list[GastoCartaoDados] = field(default_factory=list)
    anotacoes: list[AnotacaoDados] = field(default_factory=list)
    # Pagamentos marcados: (id da despesa ou do cartão, mês)
    despesas_pagas: set[tuple[int, Mes]] = field(default_factory=set)
    faturas_pagas: set[tuple[int, Mes]] = field(default_factory=set)
    responsaveis: list[ResponsavelDados] = field(default_factory=list)
    # Data em que cada conta/fatura foi marcada como paga: (id, mês) -> data
    despesas_pagas_em: dict[tuple[int, Mes], date] = field(default_factory=dict)
    faturas_pagas_em: dict[tuple[int, Mes], date] = field(default_factory=dict)
    conferencias: list[ConferenciaDados] = field(default_factory=list)
