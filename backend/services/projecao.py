"""Lógica central do controle financeiro: o que entra e sai em cada mês.

Somente funções puras (sem banco): recebem DadosFinanceiros já carregados e
devolvem estruturas prontas para virar JSON. Isso deixa as regras fáceis de
testar e permite calcular 13 meses com uma única ida ao banco.
"""

from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal

from services.calculos import CENTAVO, Mes, dividir_valor
from services.dominio import (
    AnotacaoDados,
    CartaoDados,
    ConferenciaDados,
    DadosFinanceiros,
    DespesaDados,
    GastoCartaoDados,
    ReceitaDados,
    ResponsavelDados,
)

ZERO = Decimal("0.00")


# ---------------------------------------------------------------------------
# Estruturas de saída
# ---------------------------------------------------------------------------
@dataclass
class ItemReceita:
    origem: str  # "receita" | "comissao" | "anotacao"
    id: int
    descricao: str
    valor: Decimal
    data: date | None
    # Já entrou? Receita cadastrada: a data dela já chegou. Comissão: parcela marcada
    # como recebida. Anotação "A receber": concluída.
    recebida: bool | None = None
    recorrente: bool = False  # receita que entra todo mês (ex.: salário)
    responsavel_id: int | None = None  # None = conjunto
    tipo: str | None = None  # tipo da receita cadastrada (Salário, Comissão...)
    recebida_em: date | None = None


@dataclass
class ItemDespesa:
    origem: str  # "despesa" | "gasto_cartao" | "anotacao"
    id: int
    descricao: str
    valor: Decimal
    categoria: str
    forma: str
    data_vencimento: date | None
    cartao_id: int | None = None
    parcela_atual: int | None = None
    num_parcelas: int | None = None
    faltam: int | None = None  # parcelas a pagar a partir deste mês (inclui a atual)
    ainda_devo: Decimal | None = None  # valor dessas parcelas
    termina_em: str | None = None  # "AAAA-MM"
    pago: bool = False  # conta paga no mês (ou fatura do cartão paga)
    pago_em: date | None = None  # dia em que foi marcada como paga
    responsavel_id: int | None = None  # None = conjunto


@dataclass
class Fatura:
    cartao_id: int
    nome: str
    dia_fechamento: int | None
    dia_vencimento: int | None
    data_vencimento: date | None
    total: Decimal = ZERO
    sem_dias: bool = False  # cartão sem fechamento/vencimento cadastrados
    termina_em: str | None = None  # mês do último parcelamento ainda ativo
    paga: bool = False
    itens: list[ItemDespesa] = field(default_factory=list)


@dataclass
class Vencimento:
    tipo: str  # "conta" | "fatura" | "anotacao"
    id: int
    descricao: str
    data: date | None
    valor: Decimal | None
    vencido: bool = False  # data passou e ainda não foi paga/concluída
    pago: bool = False
    anotacao_tipo: str | None = None
    pessoa: str | None = None
    responsavel_id: int | None = None  # de quem é a conta/fatura (None = conjunto)


@dataclass
class Situacao:
    """Situação de uma despesa na data de hoje (tela de Despesas)."""

    status: str  # Fixa | Em andamento | A iniciar | Quitado | Cancelada
    pagas: int | None
    faltam: int | None
    ainda_devo: Decimal | None
    termina_em: str | None


@dataclass
class ResumoMes:
    ano: int
    mes: int
    receitas: list[ItemReceita]
    despesas: list[ItemDespesa]
    total_receitas: Decimal
    total_despesas: Decimal
    total_pago: Decimal
    total_a_pagar: Decimal
    saldo: Decimal
    comissoes_recebidas: Decimal
    comissoes_a_receber: Decimal
    por_categoria: list[dict]
    por_forma: list[dict]
    faturas: list[Fatura]
    total_faturas: Decimal
    contas_ativas: int
    vencimentos: list[Vencimento]
    anotacoes_do_mes: list[AnotacaoDados]
    pendencias: list[AnotacaoDados]
    avisos: list[str]
    por_responsavel: list[dict]
    # Preenchido quando o resumo foi filtrado por uma pessoa (linha dela em por_responsavel)
    pessoa: dict | None = None
    # Previsão a partir do saldo real do banco (última conferência feita neste mês)
    conferencia: dict | None = None


# ---------------------------------------------------------------------------
# Despesas (fixas e parceladas)
# ---------------------------------------------------------------------------
def ocorrencia_despesa(despesa: DespesaDados, mes: Mes) -> ItemDespesa | None:
    """Devolve a cobrança da despesa no mês, ou None se ela não cai nesse mês.

    - Fixa: todo mês a partir da 1ª cobrança.
    - Parcelada: do mês da 1ª cobrança até completar num_parcelas.
    - Cancelada: deixa de entrar quando o vencimento do mês é depois de cancelada_em.
    """
    inicio = Mes.de(despesa.primeira_cobranca)
    numero = inicio.meses_ate(mes) + 1
    if numero < 1:
        return None
    if despesa.num_parcelas is not None and numero > despesa.num_parcelas:
        return None
    vencimento = mes.data(despesa.dia)
    if despesa.cancelada_em is not None and vencimento > despesa.cancelada_em:
        return None

    item = ItemDespesa(
        origem="despesa",
        id=despesa.id,
        descricao=despesa.descricao,
        valor=despesa.valor_mensal,
        categoria=despesa.categoria,
        forma=despesa.forma,
        data_vencimento=vencimento,
        cartao_id=despesa.cartao_id,
        responsavel_id=despesa.responsavel_no_mes(mes),
    )
    if despesa.num_parcelas is not None:
        faltam = despesa.num_parcelas - numero + 1
        item.parcela_atual = numero
        item.num_parcelas = despesa.num_parcelas
        item.faltam = faltam
        item.ainda_devo = despesa.valor_mensal * faltam
        item.termina_em = str(inicio.somar(despesa.num_parcelas - 1))
    return item


def situacao_despesa(despesa: DespesaDados, hoje: date) -> Situacao:
    """Status e progresso da despesa considerando a data de hoje.

    Uma parcela conta como paga quando a data de vencimento dela já chegou. A conta
    só vira "Quitado"/"Cancelada" depois do último mês em que ainda cobra: enquanto
    a cobrança do mês existir (ex.: última parcela, que está na fatura aberta) ela
    continua ativa, para não sumir das listas antes de ser paga.
    """
    mes_hoje = Mes.de(hoje)
    if (despesa.cancelada_em is not None and despesa.cancelada_em <= hoje
            and ocorrencia_despesa(despesa, mes_hoje) is None):
        return Situacao("Cancelada", None, 0, ZERO, str(Mes.de(despesa.cancelada_em)))
    if despesa.num_parcelas is None:
        return Situacao("Fixa", None, None, None, None)

    inicio = Mes.de(despesa.primeira_cobranca)
    meses = inicio.meses_ate(Mes.de(hoje))
    if meses < 0:
        pagas = 0
    else:
        vencimento_deste_mes = inicio.somar(meses).data(despesa.dia)
        pagas = meses + (1 if hoje >= vencimento_deste_mes else 0)
    pagas = min(max(pagas, 0), despesa.num_parcelas)
    faltam = despesa.num_parcelas - pagas
    fim = inicio.somar(despesa.num_parcelas - 1)
    termina = str(fim)

    if faltam == 0 and mes_hoje > fim:
        status = "Quitado"
    elif pagas == 0:
        status = "A iniciar"
    else:
        status = "Em andamento"
    return Situacao(status, pagas, faltam, despesa.valor_mensal * faltam, termina)


# ---------------------------------------------------------------------------
# Cartões: regra da fatura
# ---------------------------------------------------------------------------
def mes_da_fatura(data_compra: date, cartao: CartaoDados) -> Mes:
    """Mês em que a fatura que contém a compra é PAGA (mês do vencimento).

    - Compra até o dia de fechamento: fatura que fecha no mesmo mês.
    - Compra depois do fechamento: fatura que fecha no mês seguinte.
    - Se o vencimento é antes (ou no mesmo dia) do fechamento, ele cai no mês
      seguinte ao fechamento.
    - Cartão sem dias cadastrados: considera o mês seguinte à compra.
    """
    mes_compra = Mes.de(data_compra)
    if not cartao.tem_dias:
        return mes_compra.somar(1)

    fechamento = mes_compra.data(cartao.dia_fechamento)
    mes_fechamento = mes_compra if data_compra <= fechamento else mes_compra.somar(1)
    if cartao.dia_vencimento <= cartao.dia_fechamento:
        return mes_fechamento.somar(1)
    return mes_fechamento


def parcela_gasto_no_mes(
    gasto: GastoCartaoDados, cartao: CartaoDados, mes: Mes
) -> ItemDespesa | None:
    """Parcela do gasto avulso que cai na fatura paga no mês informado."""
    primeira = mes_da_fatura(gasto.data_compra, cartao)
    indice = primeira.meses_ate(mes)
    if not 0 <= indice < gasto.num_parcelas:
        return None
    valores = dividir_valor(gasto.valor_total, gasto.num_parcelas)
    numero = indice + 1
    return ItemDespesa(
        origem="gasto_cartao",
        id=gasto.id,
        descricao=gasto.descricao,
        valor=valores[indice],
        categoria=gasto.categoria or "Outros",
        forma=cartao.nome,
        data_vencimento=mes.data(cartao.dia_vencimento) if cartao.tem_dias else None,
        cartao_id=cartao.id,
        parcela_atual=numero if gasto.num_parcelas > 1 else None,
        num_parcelas=gasto.num_parcelas if gasto.num_parcelas > 1 else None,
        faltam=gasto.num_parcelas - indice,
        ainda_devo=sum(valores[indice:], ZERO),
        termina_em=str(primeira.somar(gasto.num_parcelas - 1)),
        # Sem responsável no gasto: é de quem é o cartão
        responsavel_id=gasto.responsavel_id or cartao.responsavel_id,
    )


def _fim_ultimo_parcelamento(
    dados: DadosFinanceiros, cartao: CartaoDados, mes: Mes
) -> str | None:
    """Mês do último parcelamento do cartão que ainda não terminou no mês informado."""
    fins = []
    for despesa in dados.despesas:
        if despesa.cartao_id == cartao.id and (despesa.num_parcelas or 0) > 1:
            fim = Mes.de(despesa.primeira_cobranca).somar(despesa.num_parcelas - 1)
            if despesa.cancelada_em is None or Mes.de(despesa.cancelada_em) >= fim:
                fins.append(fim)
    for gasto in dados.gastos_cartao:
        if gasto.cartao_id == cartao.id and gasto.num_parcelas > 1:
            fins.append(mes_da_fatura(gasto.data_compra, cartao).somar(gasto.num_parcelas - 1))
    ativos = [fim for fim in fins if fim >= mes]
    return str(max(ativos)) if ativos else None


# ---------------------------------------------------------------------------
# Receitas
# ---------------------------------------------------------------------------
def receita_no_mes(receita: ReceitaDados, mes: Mes) -> ItemReceita | None:
    """Recorrente: todo mês entre data_inicio e data_fim. Não recorrente: só no mês de início."""
    inicio = Mes.de(receita.data_inicio)
    if receita.recorrente:
        if mes < inicio or (receita.data_fim is not None and mes > Mes.de(receita.data_fim)):
            return None
    elif mes != inicio:
        return None
    dia = receita.dia_recebimento or receita.data_inicio.day
    return ItemReceita("receita", receita.id, receita.descricao, receita.valor, mes.data(dia),
                       recorrente=receita.recorrente, responsavel_id=receita.responsavel_id,
                       tipo=receita.tipo)


# ---------------------------------------------------------------------------
# Anotações
# ---------------------------------------------------------------------------
def anotacao_entra_no_saldo(anotacao: AnotacaoDados, mes: Mes) -> bool:
    """Só soma se o usuário marcou entra_no_saldo e há valor e data naquele mês.

    Continua somando mesmo depois de concluída: o dinheiro saiu/entrou naquele mês.
    """
    return (
        anotacao.entra_no_saldo
        and anotacao.valor is not None
        and mes.contem(anotacao.data)
        and anotacao.tipo in ("A pagar", "A receber")
    )


# ---------------------------------------------------------------------------
# Cálculo do mês
# ---------------------------------------------------------------------------
def _somar_por(itens: list[ItemDespesa], chave: str) -> list[dict]:
    totais: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for item in itens:
        totais[getattr(item, chave)] += item.valor
    return [
        {"nome": nome, "valor": valor}
        for nome, valor in sorted(totais.items(), key=lambda par: par[1], reverse=True)
    ]


def _dividir_conjunto(
    saldo_conjunto: Decimal, rendas: list[Decimal]
) -> tuple[list[Decimal], list[Decimal]]:
    """Divide o saldo do Conjunto pela renda de cada um (iguais se ninguém tiver renda).

    A última pessoa fica com o resto, para os centavos fecharem.
    """
    total = sum(rendas, ZERO)
    proporcoes = [r / total if total else Decimal(1) / len(rendas) for r in rendas]
    partes = [(saldo_conjunto * p).quantize(CENTAVO) for p in proporcoes[:-1]]
    partes.append(saldo_conjunto - sum(partes, ZERO))
    return partes, proporcoes


def resumo_por_responsavel(
    receitas: list[ItemReceita], despesas: list[ItemDespesa], responsaveis: list[ResponsavelDados]
) -> list[dict]:
    """Quanto entra, sai e sobra para cada pessoa e para o Conjunto (sem responsável).

    O saldo do Conjunto (normalmente as contas da casa) é dividido entre as pessoas
    proporcionalmente à renda de cada uma no mês (partes iguais se ninguém tiver
    renda). A soma de `saldo_final` das pessoas é sempre igual ao saldo do mês.

    Parcelas de comissão ainda não recebidas entram em `receitas` (é previsão),
    mas também aparecem à parte em `receitas_previstas`; `saldo_final_garantido`
    é a mesma conta sem elas (só com o que é certo ou já entrou).
    Sem pessoas cadastradas, devolve lista vazia.
    """
    if not responsaveis:
        return []

    def grupo(responsavel_id: int | None, nome: str) -> dict:
        return {"responsavel_id": responsavel_id, "nome": nome,
                "receitas": ZERO, "receitas_previstas": ZERO, "despesas": ZERO, "pago": ZERO}

    pessoas = {r.id: grupo(r.id, r.nome) for r in responsaveis}
    conjunto = grupo(None, "Conjunto")
    conjunto["receitas_comissao"] = ZERO  # parte sem dono que veio de comissões
    for receita in receitas:
        alvo = pessoas.get(receita.responsavel_id, conjunto)
        alvo["receitas"] += receita.valor
        if receita.origem == "comissao" and not receita.recebida:
            alvo["receitas_previstas"] += receita.valor
        if receita.responsavel_id not in pessoas and (
            receita.origem == "comissao" or receita.tipo == "Comissão"
        ):
            conjunto["receitas_comissao"] += receita.valor
    for despesa in despesas:
        alvo = pessoas.get(despesa.responsavel_id, conjunto)
        alvo["despesas"] += despesa.valor
        if despesa.pago:
            alvo["pago"] += despesa.valor
    for alvo in [*pessoas.values(), conjunto]:
        alvo["saldo"] = alvo["receitas"] - alvo["despesas"]

    lista = list(pessoas.values())
    partes, proporcoes = _dividir_conjunto(conjunto["saldo"], [p["receitas"] for p in lista])
    for pessoa, parte, proporcao in zip(lista, partes, proporcoes):
        pessoa["proporcao"] = proporcao.quantize(Decimal("0.0001"))
        pessoa["parte_conjunto"] = -parte  # positivo = quanto cobre das contas conjuntas
        pessoa["saldo_final"] = pessoa["saldo"] + parte

    # Mesma divisão sem as comissões que ainda não entraram
    garantidas = [p["receitas"] - p["receitas_previstas"] for p in lista]
    saldo_conjunto_garantido = conjunto["saldo"] - conjunto["receitas_previstas"]
    partes, _ = _dividir_conjunto(saldo_conjunto_garantido, garantidas)
    for pessoa, renda, parte in zip(lista, garantidas, partes):
        pessoa["saldo_final_garantido"] = renda - pessoa["despesas"] + parte

    if conjunto["receitas"] or conjunto["despesas"]:
        lista.append(conjunto)
    return lista


def calcular_mes(dados: DadosFinanceiros, mes: Mes, hoje: date) -> ResumoMes:
    """Monta tudo o que o dashboard precisa para um mês."""
    cartoes = {cartao.id: cartao for cartao in dados.cartoes}
    avisos: list[str] = []

    # --- Receitas: cadastradas + parcelas de comissão + anotações "A receber"
    receitas = [r for r in (receita_no_mes(x, mes) for x in dados.receitas) if r]
    for receita in receitas:
        receita.recebida = receita.data <= hoje  # ex.: salário do dia 15 ainda não caiu no dia 6
        receita.recebida_em = receita.data if receita.recebida else None
    comissoes_recebidas = comissoes_a_receber = ZERO
    for parcela in dados.parcelas_comissao:
        if not mes.contem(parcela.data_prevista):
            continue
        if parcela.paga:
            comissoes_recebidas += parcela.valor
        else:
            comissoes_a_receber += parcela.valor
        if parcela.lancada_como_receita:
            continue  # já entra como receita cadastrada (no mês em que foi recebida)
        receitas.append(ItemReceita(
            "comissao",
            parcela.id,
            f"Comissão {parcela.cliente} ({parcela.numero}/{parcela.total_parcelas})",
            parcela.valor,
            parcela.data_prevista,
            recebida=parcela.paga,
            recebida_em=parcela.paga_em,
            responsavel_id=parcela.responsavel_id,
        ))

    despesas: list[ItemDespesa] = []
    for anotacao in dados.anotacoes:
        if not anotacao_entra_no_saldo(anotacao, mes):
            continue
        if anotacao.tipo == "A receber":
            receitas.append(ItemReceita(
                "anotacao", anotacao.id, anotacao.texto, anotacao.valor, anotacao.data,
                recebida=anotacao.concluida,
            ))
        else:
            despesas.append(ItemDespesa(
                "anotacao", anotacao.id, anotacao.texto, anotacao.valor,
                categoria="Outros", forma="Anotação", data_vencimento=anotacao.data,
                pago=anotacao.concluida,
            ))

    # --- Despesas cadastradas (fixas e parceladas)
    contas_ativas = 0
    for despesa in dados.despesas:
        item = ocorrencia_despesa(despesa, mes)
        if item:
            contas_ativas += 1
            item.pago = (despesa.id, mes) in dados.despesas_pagas
            item.pago_em = dados.despesas_pagas_em.get((despesa.id, mes))
            if item.responsavel_id is None and despesa.cartao_id in cartoes:
                # Conta no cartão sem responsável: é de quem é o cartão
                item.responsavel_id = cartoes[despesa.cartao_id].responsavel_id
            despesas.append(item)

    # --- Gastos avulsos no cartão
    for gasto in dados.gastos_cartao:
        cartao = cartoes.get(gasto.cartao_id)
        if cartao is None:
            continue
        item = parcela_gasto_no_mes(gasto, cartao, mes)
        if item:
            despesas.append(item)

    # --- Faturas: agrupa (sem somar de novo no total) o que é de cada cartão
    faturas = []
    for cartao in dados.cartoes:
        fatura = Fatura(
            cartao_id=cartao.id,
            nome=cartao.nome,
            dia_fechamento=cartao.dia_fechamento,
            dia_vencimento=cartao.dia_vencimento,
            data_vencimento=mes.data(cartao.dia_vencimento) if cartao.dia_vencimento else None,
            sem_dias=not cartao.tem_dias,
            termina_em=_fim_ultimo_parcelamento(dados, cartao, mes),
            paga=(cartao.id, mes) in dados.faturas_pagas,
        )
        fatura.itens = [d for d in despesas if d.cartao_id == cartao.id]
        for item in fatura.itens:
            item.pago = fatura.paga  # o que está no cartão é pago junto com a fatura
            item.pago_em = dados.faturas_pagas_em.get((cartao.id, mes))
        fatura.total = sum((d.valor for d in fatura.itens), ZERO)
        faturas.append(fatura)
        if fatura.sem_dias and any(
            g.cartao_id == cartao.id for g in dados.gastos_cartao
        ):
            avisos.append(
                f"{cartao.nome} sem dias de fechamento/vencimento: "
                "os gastos avulsos foram lançados no mês seguinte à compra."
            )

    # --- Vencimentos: contas fora do cartão + faturas + anotações com data
    vencimentos = [
        Vencimento("conta", d.id, d.descricao, d.data_vencimento, d.valor,
                   vencido=not d.pago and d.data_vencimento < hoje, pago=d.pago,
                   responsavel_id=d.responsavel_id)
        for d in despesas
        if d.origem == "despesa" and d.cartao_id is None
    ]
    vencimentos += [
        Vencimento("fatura", f.cartao_id, f"Fatura {f.nome}", f.data_vencimento, f.total,
                   vencido=(not f.paga and f.data_vencimento is not None
                            and f.data_vencimento < hoje),
                   pago=f.paga, responsavel_id=cartoes[f.cartao_id].responsavel_id)
        for f in faturas
        if f.total > 0
    ]
    anotacoes_do_mes = sorted(
        (a for a in dados.anotacoes if mes.contem(a.data) and not a.concluida),
        key=lambda a: (a.data, a.id),
    )
    # No mês atual, anotações atrasadas de meses anteriores continuam aparecendo
    # (em vermelho) até serem concluídas
    atrasadas = []
    if mes == Mes.de(hoje):
        atrasadas = sorted(
            (a for a in dados.anotacoes
             if a.data is not None and a.data < mes.data(1) and not a.concluida),
            key=lambda a: (a.data, a.id),
        )
    vencimentos += [
        Vencimento("anotacao", a.id, a.texto, a.data, a.valor, vencido=a.data < hoje,
                   anotacao_tipo=a.tipo, pessoa=a.pessoa)
        for a in atrasadas + anotacoes_do_mes
    ]
    vencimentos.sort(key=lambda v: (v.data is None, v.data or date.max, v.tipo, v.descricao))

    pendencias = sorted(
        (a for a in dados.anotacoes if a.data is None and not a.concluida),
        key=lambda a: a.id,
    )

    total_receitas = sum((r.valor for r in receitas), ZERO)
    # Total do mês = soma dos itens; faturas são só um agrupamento (sem contagem dupla)
    total_despesas = sum((d.valor for d in despesas), ZERO)
    total_pago = sum((d.valor for d in despesas if d.pago), ZERO)
    receitas.sort(key=lambda r: (r.data or date.max, r.descricao))
    despesas.sort(key=lambda d: (d.data_vencimento or date.max, d.descricao))

    resumo = ResumoMes(
        ano=mes.ano,
        mes=mes.mes,
        receitas=receitas,
        despesas=despesas,
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        total_pago=total_pago,
        total_a_pagar=total_despesas - total_pago,
        saldo=total_receitas - total_despesas,
        comissoes_recebidas=comissoes_recebidas,
        comissoes_a_receber=comissoes_a_receber,
        por_categoria=_somar_por(despesas, "categoria"),
        por_forma=_somar_por(despesas, "forma"),
        faturas=faturas,
        total_faturas=sum((f.total for f in faturas), ZERO),
        contas_ativas=contas_ativas,
        vencimentos=vencimentos,
        anotacoes_do_mes=anotacoes_do_mes,
        pendencias=pendencias,
        avisos=avisos,
        por_responsavel=resumo_por_responsavel(receitas, despesas, dados.responsaveis),
    )
    conferencias = [c for c in dados.conferencias if mes.contem(c.data)]
    if conferencias:
        ultima = max(conferencias, key=lambda c: (c.data, c.id))
        resumo.conferencia = aplicar_conferencia(resumo, ultima, hoje)
        # Conferência de um dia anterior (no mesmo dia vale só a última, é correção)
        anteriores = [c for c in conferencias if c.data < ultima.data]
        if anteriores:
            anterior = max(anteriores, key=lambda c: (c.data, c.id))
            resumo.conferencia["anterior"] = comparar_conferencias(resumo, anterior, ultima, hoje)
    return resumo


# ---------------------------------------------------------------------------
# Conferência com o saldo real do banco
# ---------------------------------------------------------------------------
def chave_receita(item: ItemReceita) -> str:
    return f"{item.origem}:{item.id}"


def _ainda_ia_entrar(item: ItemReceita, dia: date) -> bool:
    """Na data da conferência, esse dinheiro ainda não estava na conta?"""
    if item.origem == "receita":
        return item.data is not None and item.data > dia
    if item.origem == "comissao":
        return not item.recebida or (item.recebida_em is not None and item.recebida_em > dia)
    return not item.recebida  # anotação "A receber"


def _ainda_faltava_pagar(item: ItemDespesa, dia: date) -> bool:
    """Conta não paga, ou paga depois da conferência (o dinheiro estava no saldo)."""
    return not item.pago or (item.pago_em is not None and item.pago_em > dia)


def aplicar_conferencia(resumo: ResumoMes, conferencia: ConferenciaDados, hoje: date) -> dict:
    """Quanto deve sobrar no fim do mês a partir do saldo real informado.

    Sobra = saldo do banco + o que ainda ia entrar depois da conferência - o que
    ainda faltava pagar naquele dia. Gastos pequenos não anotados já saíram do
    saldo, então já estão considerados. Separado por pessoa, as contas do Conjunto
    que faltam são divididas pela renda (como no resto do app); a soma das pessoas
    é sempre o total da casa.
    """
    dia = conferencia.data
    entrar = [
        r for r in resumo.receitas
        if chave_receita(r) not in conferencia.ja_entrou and _ainda_ia_entrar(r, dia)
    ]
    pagar = [d for d in resumo.despesas if _ainda_faltava_pagar(d, dia)]
    total_entrar = sum((r.valor for r in entrar), ZERO)
    previstas = sum((r.valor for r in entrar if r.origem == "comissao"), ZERO)
    total_pagar = sum((d.valor for d in pagar), ZERO)
    sobra = conferencia.total + total_entrar - total_pagar

    por_pessoa = []
    pessoas = [p for p in resumo.por_responsavel if p["responsavel_id"] is not None]
    if not conferencia.junto and pessoas:
        ids = {p["responsavel_id"] for p in pessoas}

        def de(lista, responsavel_id) -> Decimal:
            # Sem pessoa (ou pessoa que não existe mais) = Conjunto
            return sum(
                (x.valor for x in lista
                 if (x.responsavel_id if x.responsavel_id in ids else None) == responsavel_id),
                ZERO,
            )

        pendente_conjunto = de(pagar, None) - de(entrar, None)
        partes, _ = _dividir_conjunto(pendente_conjunto, [p["receitas"] for p in pessoas])
        for pessoa, parte in zip(pessoas, partes):
            rid = pessoa["responsavel_id"]
            saldo = conferencia.saldos.get(rid, ZERO)
            a_entrar, a_pagar = de(entrar, rid), de(pagar, rid)
            por_pessoa.append({
                "responsavel_id": rid, "nome": pessoa["nome"], "saldo_real": saldo,
                "a_entrar": a_entrar, "a_pagar": a_pagar, "parte_conjunto": parte,
                "sobra": saldo + a_entrar - a_pagar - parte,
            })

    return {
        "id": conferencia.id,
        "data": dia,
        "dias": (hoje - dia).days,
        "junto": conferencia.junto,
        "saldo_real": conferencia.total,
        "saldos": [{"responsavel_id": k, "valor": v} for k, v in conferencia.saldos.items()],
        "a_entrar": [
            {"chave": chave_receita(r), "descricao": r.descricao, "valor": r.valor, "data": r.data,
             "responsavel_id": r.responsavel_id, "previsto": r.origem == "comissao"}
            for r in entrar
        ],
        "total_a_entrar": total_entrar,
        "a_entrar_previsto": previstas,
        "a_pagar": [
            {"descricao": d.descricao, "valor": d.valor, "data": d.data_vencimento,
             "responsavel_id": d.responsavel_id}
            for d in pagar
        ],
        "total_a_pagar": total_pagar,
        "sobra": sobra,
        "sobra_sem_previstas": sobra - previstas,
        "por_pessoa": por_pessoa,
    }


def comparar_conferencias(
    resumo: ResumoMes, anterior: ConferenciaDados, atual: ConferenciaDados, hoje: date
) -> dict:
    """Quanto saiu da conta entre duas conferências sem estar anotado no app.

    As duas previsões de fim de mês são refeitas com os dados de agora (conta
    cadastrada depois também entra na anterior). Se tudo estivesse anotado, elas
    seriam iguais: a diferença é o que foi gasto por fora (positivo) ou entrou a
    mais (negativo) nesse intervalo.
    """
    sobra_antes = aplicar_conferencia(resumo, anterior, hoje)["sobra"]
    sobra_agora = aplicar_conferencia(resumo, atual, hoje)["sobra"]
    return {
        "data": anterior.data,
        "saldo_real": anterior.total,
        "dias": (atual.data - anterior.data).days,
        "nao_anotado": sobra_antes - sobra_agora,
    }


# ---------------------------------------------------------------------------
# Filtro por pessoa e visão de vários meses
# ---------------------------------------------------------------------------
TODOS = object()  # sem filtro (None já significa "Conjunto")


def filtrar_por_responsavel(resumo: ResumoMes, responsavel_id: int | None) -> ResumoMes:
    """Só o que é de uma pessoa (None = Conjunto).

    Receitas e despesas pelo responsável de cada item (conta no cartão sem pessoa =
    dono do cartão); faturas mostram só os itens dela; contas a pagar por quem paga.
    Anotações continuam (não têm dono). A sobra própria fica em `saldo` e a linha
    completa da pessoa (com a parte do Conjunto) em `pessoa`.
    """
    def dela(item) -> bool:
        return item.responsavel_id == responsavel_id

    receitas = [r for r in resumo.receitas if dela(r)]
    despesas = [d for d in resumo.despesas if dela(d)]
    faturas = []
    for fatura in resumo.faturas:
        itens = [d for d in fatura.itens if dela(d)]
        if itens:
            faturas.append(replace(fatura, itens=itens, total=sum((d.valor for d in itens), ZERO)))
    total_receitas = sum((r.valor for r in receitas), ZERO)
    total_despesas = sum((d.valor for d in despesas), ZERO)
    total_pago = sum((d.valor for d in despesas if d.pago), ZERO)
    comissoes = [r for r in receitas if r.origem == "comissao" or r.tipo == "Comissão"]
    return replace(
        resumo,
        receitas=receitas,
        despesas=despesas,
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        total_pago=total_pago,
        total_a_pagar=total_despesas - total_pago,
        saldo=total_receitas - total_despesas,
        comissoes_recebidas=sum((r.valor for r in comissoes if r.recebida is not False), ZERO),
        comissoes_a_receber=sum((r.valor for r in comissoes if r.recebida is False), ZERO),
        por_categoria=_somar_por(despesas, "categoria"),
        por_forma=_somar_por(despesas, "forma"),
        faturas=faturas,
        total_faturas=sum((f.total for f in faturas), ZERO),
        contas_ativas=sum(1 for d in despesas if d.origem == "despesa"),
        vencimentos=[v for v in resumo.vencimentos if v.tipo == "anotacao" or dela(v)],
        pessoa=next(
            (p for p in resumo.por_responsavel if p["responsavel_id"] == responsavel_id), None
        ),
    )


def resumo_do_mes(dados: DadosFinanceiros, mes: Mes, hoje: date, responsavel=TODOS) -> ResumoMes:
    resumo = calcular_mes(dados, mes, hoje)
    return resumo if responsavel is TODOS else filtrar_por_responsavel(resumo, responsavel)


def _totais(resumo: ResumoMes) -> tuple[Decimal, Decimal, Decimal]:
    """Receitas, despesas e saldo do mês para gráficos e somas de período.

    Filtrado por uma pessoa, a parte dela no Conjunto entra como despesa (ou como
    receita, se o Conjunto sobrou), e o saldo é a sobra final dela.
    """
    pessoa = resumo.pessoa
    if pessoa is None or "parte_conjunto" not in pessoa:
        return resumo.total_receitas, resumo.total_despesas, resumo.saldo
    parte = pessoa["parte_conjunto"]
    receitas = resumo.total_receitas + max(-parte, ZERO)
    despesas = resumo.total_despesas + max(parte, ZERO)
    return receitas, despesas, receitas - despesas


def resumo_periodo(
    dados: DadosFinanceiros, inicio: Mes, fim: Mes, hoje: date, responsavel=TODOS
) -> dict:
    """Soma de vários meses (de `inicio` a `fim`, inclusive), opcionalmente de uma pessoa."""
    meses = []
    categorias: dict[str, Decimal] = defaultdict(lambda: ZERO)
    maiores: dict[str, Decimal] = defaultdict(lambda: ZERO)
    pessoas: dict[int | None, dict] = {}
    campos = ("receitas", "receitas_previstas", "despesas", "parte_conjunto", "saldo_final",
              "saldo_final_garantido")
    for deslocamento in range(inicio.meses_ate(fim) + 1):
        resumo = resumo_do_mes(dados, inicio.somar(deslocamento), hoje, responsavel)
        receitas, despesas, saldo = _totais(resumo)
        meses.append({"ano": resumo.ano, "mes": resumo.mes, "receitas": receitas,
                      "despesas": despesas, "saldo": saldo,
                      "comissoes_a_receber": resumo.comissoes_a_receber})
        for item in resumo.despesas:
            categorias[item.categoria] += item.valor
            maiores[item.descricao] += item.valor
        for linha in resumo.por_responsavel:
            acumulado = pessoas.setdefault(
                linha["responsavel_id"],
                {"responsavel_id": linha["responsavel_id"], "nome": linha["nome"],
                 **{c: ZERO for c in campos}},
            )
            for campo in campos:
                acumulado[campo] += linha.get(campo, ZERO)

    total_receitas = sum((m["receitas"] for m in meses), ZERO)
    total_despesas = sum((m["despesas"] for m in meses), ZERO)
    ordenar = lambda totais: [  # noqa: E731
        {"nome": nome, "valor": valor}
        for nome, valor in sorted(totais.items(), key=lambda par: par[1], reverse=True)
    ]
    melhor = max(meses, key=lambda m: m["saldo"])
    pior = min(meses, key=lambda m: m["saldo"])
    return {
        "inicio": str(inicio),
        "fim": str(fim),
        "meses": meses,
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "saldo": total_receitas - total_despesas,
        "media_saldo": ((total_receitas - total_despesas) / len(meses)).quantize(CENTAVO),
        "comissoes_a_receber": sum((m["comissoes_a_receber"] for m in meses), ZERO),
        "melhor_mes": {"ano": melhor["ano"], "mes": melhor["mes"], "saldo": melhor["saldo"]},
        "pior_mes": {"ano": pior["ano"], "mes": pior["mes"], "saldo": pior["saldo"]},
        "por_categoria": ordenar(categorias),
        "maiores_despesas": ordenar(maiores)[:8],
        "por_responsavel": list(pessoas.values()),
    }


def projetar(
    dados: DadosFinanceiros, inicio: Mes, meses: int, hoje: date, responsavel=TODOS
) -> list[dict]:
    """Resumo do mês inicial + `meses` seguintes, calculado todo em memória."""
    resultado = []
    for deslocamento in range(meses + 1):
        resumo = resumo_do_mes(dados, inicio.somar(deslocamento), hoje, responsavel)
        receitas, despesas, saldo = _totais(resumo)
        resultado.append({
            "ano": resumo.ano,
            "mes": resumo.mes,
            "receitas": receitas,
            "despesas": despesas,
            "saldo": saldo,
            "comissoes_a_receber": resumo.comissoes_a_receber,
            "faturas": [
                {"cartao_id": f.cartao_id, "nome": f.nome, "total": f.total,
                 "data_vencimento": f.data_vencimento, "paga": f.paga,
                 # Tudo o que soma nesta fatura (a tela de Cartões lista exatamente isso)
                 "itens": [
                     {"origem": i.origem, "id": i.id, "descricao": i.descricao,
                      "valor": i.valor, "parcela_atual": i.parcela_atual,
                      "num_parcelas": i.num_parcelas, "responsavel_id": i.responsavel_id}
                     for i in f.itens
                 ]}
                for f in resumo.faturas
            ],
        })
    return resultado
