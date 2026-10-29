// Simulador: contas de "e se...?" (orçamento, investimento e meta).
// Nada aqui é enviado ao servidor nem altera o histórico; os números ficam
// guardados só neste aparelho para não se perderem ao trocar de tela.
import { useEffect, useState } from 'react'
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Download, FlaskConical, Plus, RotateCcw, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { dinheiro, lerValor, numeroCurto, valorParaCampo } from '../lib/formato'
import { useDados } from '../contexts/DadosContext'
import { Abas, Botao, BotaoIcone, Campo, CampoValor, Cartao, Indicador, Opcoes, Titulo } from '../components/ui'

const CHAVE = 'simulador-v1'
const CORES = { investido: 'var(--color-apagado)', total: '#3987e5', grade: 'var(--color-borda)', eixo: 'var(--color-apagado)' }

const INICIAL = {
  aba: 'orcamento',
  orcamento: {
    entradas: [{ descricao: 'Salário', valor: '' }],
    gastos: [{ descricao: '', valor: '' }],
    guardarModo: 'pct',
    guardar: '10',
  },
  investimento: { inicial: '', aporte: '', taxa: '1', periodo: 'mes', prazo: '12' },
  meta: { alvo: '', inicial: '', taxa: '1', periodo: 'mes', prazo: '12' },
}

function carregar() {
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE))
    return salvo ? { ...INICIAL, ...salvo } : INICIAL
  } catch {
    return INICIAL
  }
}

// Valor digitado -> número (vazio ou inválido conta como 0)
const num = (texto) => {
  const v = lerValor(texto)
  return Number.isFinite(v) ? v : 0
}

// Taxa digitada em % -> taxa mensal decimal (taxa anual vira equivalente mensal)
function taxaMensal(texto, periodo) {
  const t = num(texto) / 100
  return periodo === 'ano' ? Math.pow(1 + t, 1 / 12) - 1 : t
}

export default function Simulador() {
  const [estado, setEstado] = useState(carregar)

  useEffect(() => {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(estado))
    } catch {
      // sem armazenamento (aba anônima): o simulador funciona do mesmo jeito
    }
  }, [estado])

  const mudar = (parte) => (dados) => setEstado((e) => ({ ...e, [parte]: { ...e[parte], ...dados } }))
  const limpar = () => setEstado((e) => ({ ...INICIAL, aba: e.aba }))

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <Titulo
        acao={
          <Botao variante="fantasma" onClick={limpar} className="text-sm">
            <RotateCcw className="size-4" /> Limpar
          </Botao>
        }
      >
        Simulador
      </Titulo>

      <p className="flex items-start gap-2 rounded-xl border border-borda bg-painel p-3 text-sm text-suave">
        <FlaskConical className="mt-0.5 size-4 shrink-0 text-saldo" aria-hidden />
        Área de testes: nada do que você digitar aqui entra no seu histórico.
      </p>

      <Abas
        abas={[
          { valor: 'orcamento', rotulo: 'Orçamento' },
          { valor: 'investimento', rotulo: 'Investimento' },
          { valor: 'meta', rotulo: 'Meta' },
        ]}
        ativa={estado.aba}
        onChange={(aba) => setEstado((e) => ({ ...e, aba }))}
      />

      {estado.aba === 'orcamento' && <Orcamento dados={estado.orcamento} onChange={mudar('orcamento')} />}
      {estado.aba === 'investimento' && <Investimento dados={estado.investimento} onChange={mudar('investimento')} />}
      {estado.aba === 'meta' && <Meta dados={estado.meta} onChange={mudar('meta')} />}
    </div>
  )
}

// ---------------------------------------------------------------- orçamento
function Orcamento({ dados, onChange }) {
  const { avisar } = useDados()
  const [buscando, setBuscando] = useState(false)

  const totalEntradas = dados.entradas.reduce((s, i) => s + num(i.valor), 0)
  const totalGastos = dados.gastos.reduce((s, i) => s + num(i.valor), 0)
  const guardar = dados.guardarModo === 'pct' ? (totalEntradas * num(dados.guardar)) / 100 : num(dados.guardar)
  const livre = totalEntradas - totalGastos - guardar

  const hoje = new Date()
  const diasNoMes = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0).getDate()

  // Copia os totais do mês atual só como ponto de partida (leitura, não grava nada)
  const usarMeuMes = async () => {
    setBuscando(true)
    try {
      const r = await api.get(`/dashboard?ano=${hoje.getFullYear()}&mes=${hoje.getMonth() + 1}`)
      onChange({
        entradas: [{ descricao: 'Receitas do mês', valor: valorParaCampo(r.total_receitas) }],
        gastos: [{ descricao: 'Despesas do mês', valor: valorParaCampo(r.total_despesas) }],
      })
      avisar('Números do mês copiados para o simulador')
    } catch (e) {
      avisar(e.message)
    }
    setBuscando(false)
  }

  return (
    <div className="space-y-6">
      <Botao variante="secundario" onClick={usarMeuMes} carregando={buscando} className="w-full text-sm sm:w-auto">
        {!buscando && <Download className="size-4" />} Começar com os números deste mês
      </Botao>

      <div className="grid gap-4 md:grid-cols-2">
        <ListaValores
          titulo="Vou receber"
          itens={dados.entradas}
          total={totalEntradas}
          exemplo="Ex.: salário, comissão"
          onChange={(entradas) => onChange({ entradas })}
        />
        <ListaValores
          titulo="Vou gastar"
          itens={dados.gastos}
          total={totalGastos}
          exemplo="Ex.: aluguel, mercado"
          onChange={(gastos) => onChange({ gastos })}
        />
      </div>

      <Cartao titulo="Quero guardar">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Opcoes
            opcoes={[{ valor: 'pct', rotulo: '% do que entra' }, { valor: 'valor', rotulo: 'Valor fixo' }]}
            valor={dados.guardarModo}
            onChange={(guardarModo) => onChange({ guardarModo, guardar: '' })}
          />
          {dados.guardarModo === 'pct' ? (
            <Campo
              inputMode="decimal"
              placeholder="10"
              value={dados.guardar}
              onChange={(e) => onChange({ guardar: e.target.value })}
              aria-label="Porcentagem para guardar"
              className="sm:w-32"
            />
          ) : (
            <CampoValor
              value={dados.guardar}
              onChange={(e) => onChange({ guardar: e.target.value })}
              aria-label="Valor para guardar"
              className="sm:w-48"
            />
          )}
        </div>
      </Cartao>

      <div className={`rounded-2xl border p-4 ${livre >= 0 ? 'border-positivo/40 bg-positivo/5' : 'border-negativo/50 bg-negativo/5'}`}>
        <p className="text-sm text-suave">{livre >= 0 ? 'Sobra para gastar livre' : 'Falta dinheiro'}</p>
        <p className={`mt-1 text-3xl font-bold ${livre >= 0 ? 'text-positivo' : 'text-negativo'}`}>{dinheiro(livre)}</p>
        {livre < 0 && (
          <p className="mt-1 text-sm text-suave">Corte gastos ou guarde menos para fechar a conta.</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicador rotulo="Guardando" valor={dinheiro(guardar)} detalhe={totalEntradas ? `${Math.round((guardar / totalEntradas) * 100)}% do que entra` : null} cor="text-saldo" />
        <Indicador rotulo="Em 12 meses guarda" valor={dinheiro(guardar * 12)} detalhe="sem contar rendimento" />
        <Indicador rotulo="Livre por semana" valor={dinheiro(Math.max(livre, 0) / (diasNoMes / 7))} />
        <Indicador rotulo="Livre por dia" valor={dinheiro(Math.max(livre, 0) / diasNoMes)} detalhe={`mês de ${diasNoMes} dias`} />
      </div>
    </div>
  )
}

function ListaValores({ titulo, itens, total, exemplo, onChange }) {
  const alterar = (i, campo, valor) => onChange(itens.map((x, j) => (j === i ? { ...x, [campo]: valor } : x)))
  const remover = (i) => onChange(itens.length > 1 ? itens.filter((_, j) => j !== i) : [{ descricao: '', valor: '' }])

  return (
    <Cartao titulo={titulo} acao={<span className="text-sm font-semibold">{dinheiro(total)}</span>}>
      <ul className="space-y-2">
        {itens.map((item, i) => (
          <li key={i} className="flex items-center gap-2">
            <Campo
              placeholder={i === 0 ? exemplo : 'Descrição'}
              value={item.descricao}
              onChange={(e) => alterar(i, 'descricao', e.target.value)}
              aria-label="Descrição"
              className="flex-1"
            />
            <CampoValor value={item.valor} onChange={(e) => alterar(i, 'valor', e.target.value)} aria-label="Valor" className="w-32 shrink-0 sm:w-36" />
            <BotaoIcone rotulo="Remover" onClick={() => remover(i)}>
              <Trash2 className="size-4" />
            </BotaoIcone>
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => onChange([...itens, { descricao: '', valor: '' }])}
        className="mt-2 flex min-h-10 items-center gap-1 text-sm text-saldo"
      >
        <Plus className="size-4" /> Adicionar linha
      </button>
    </Cartao>
  )
}

// ---------------------------------------------------------------- investimento
function CamposTaxa({ dados, onChange }) {
  return (
    <>
      <div className="flex items-end gap-2">
        <Campo
          rotulo="Rendimento (%)"
          inputMode="decimal"
          placeholder="1"
          value={dados.taxa}
          onChange={(e) => onChange({ taxa: e.target.value })}
          className="w-28"
        />
        <Opcoes
          opcoes={[{ valor: 'mes', rotulo: 'ao mês' }, { valor: 'ano', rotulo: 'ao ano' }]}
          valor={dados.periodo}
          onChange={(periodo) => onChange({ periodo })}
        />
      </div>
      <Campo
        rotulo="Prazo (meses)"
        inputMode="numeric"
        placeholder="12"
        value={dados.prazo}
        onChange={(e) => onChange({ prazo: e.target.value.replace(/\D/g, '') })}
        dica={num(dados.prazo) >= 12 ? `${(num(dados.prazo) / 12).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} anos` : null}
      />
    </>
  )
}

// Evolução mês a mês: aporte no fim de cada mês, juros compostos
function evolucao(inicial, aporte, i, meses) {
  const linhas = [{ mes: 0, investido: inicial, total: inicial }]
  let total = inicial
  for (let m = 1; m <= meses; m++) {
    total = total * (1 + i) + aporte
    linhas.push({ mes: m, investido: inicial + aporte * m, total })
  }
  return linhas
}

function Investimento({ dados, onChange }) {
  const inicial = num(dados.inicial)
  const aporte = num(dados.aporte)
  const i = taxaMensal(dados.taxa, dados.periodo)
  const meses = Math.min(Math.round(num(dados.prazo)), 600) // até 50 anos

  const linhas = evolucao(inicial, aporte, i, meses)
  const final = linhas[linhas.length - 1]
  const juros = final.total - final.investido

  return (
    <div className="space-y-6">
      <Cartao titulo="Se eu investir...">
        <div className="grid gap-3 sm:grid-cols-2">
          <CampoValor rotulo="Valor que já tenho" value={dados.inicial} onChange={(e) => onChange({ inicial: e.target.value })} />
          <CampoValor rotulo="Quanto coloco por mês" value={dados.aporte} onChange={(e) => onChange({ aporte: e.target.value })} />
          <CamposTaxa dados={dados} onChange={onChange} />
        </div>
      </Cartao>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <div className="col-span-2 rounded-2xl border border-borda bg-painel-2/60 p-4 md:col-span-1">
          <p className="text-sm text-suave">Vou ficar com</p>
          <p className="mt-1 text-2xl font-bold text-saldo">{dinheiro(final.total)}</p>
          <p className="text-xs text-apagado">depois de {meses} {meses === 1 ? 'mês' : 'meses'}</p>
        </div>
        <Indicador rotulo="Dinheiro que eu coloquei" valor={dinheiro(final.investido)} />
        <Indicador rotulo="Ganho com rendimento" valor={dinheiro(juros)} cor="text-positivo" />
      </div>

      {meses > 0 && final.total > 0 && (
        <Cartao titulo="Evolução (R$)">
          <GraficoEvolucao linhas={linhas} />
        </Cartao>
      )}
      <p className="text-xs text-apagado">
        Conta aproximada: não desconta imposto de renda nem taxas, e considera o rendimento constante.
      </p>
    </div>
  )
}

function GraficoEvolucao({ linhas }) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <AreaChart data={linhas} margin={{ top: 8, right: 4, left: -8, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={CORES.grade} />
          <XAxis dataKey="mes" tick={{ fill: CORES.eixo, fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(m) => `${m}m`} />
          <YAxis tickFormatter={numeroCurto} tick={{ fill: CORES.eixo, fontSize: 11 }} tickLine={false} axisLine={false} width={58} />
          <Tooltip
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <div className="rounded-xl border border-borda bg-painel px-3 py-2 text-xs shadow-xl">
                  <p className="mb-1 font-semibold">Mês {label}</p>
                  {payload.map((p) => (
                    <p key={p.dataKey} className="flex items-center gap-2">
                      <span className="size-2 rounded-full" style={{ background: p.color }} />
                      <span className="text-suave">{p.name}:</span> {dinheiro(p.value)}
                    </p>
                  ))}
                </div>
              ) : null
            }
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: CORES.eixo }} />
          <Area dataKey="total" name="Com rendimento" stroke={CORES.total} fill={CORES.total} fillOpacity={0.25} strokeWidth={2} type="monotone" />
          <Area dataKey="investido" name="Só o que coloquei" stroke={CORES.investido} fill={CORES.investido} fillOpacity={0.1} strokeWidth={2} type="monotone" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ---------------------------------------------------------------- meta
function Meta({ dados, onChange }) {
  const alvo = num(dados.alvo)
  const inicial = num(dados.inicial)
  const i = taxaMensal(dados.taxa, dados.periodo)
  const meses = Math.min(Math.round(num(dados.prazo)), 600)

  // Quanto o valor inicial vira sozinho e quanto falta cobrir com aportes
  const crescimento = Math.pow(1 + i, meses)
  const inicialNoFim = inicial * crescimento
  const falta = alvo - inicialNoFim
  const fator = i > 0 ? (crescimento - 1) / i : meses
  const porMes = meses > 0 && falta > 0 ? falta / fator : 0
  const semRendimento = meses > 0 ? Math.max(alvo - inicial, 0) / meses : 0
  const pronto = alvo > 0 && falta <= 0

  return (
    <div className="space-y-6">
      <Cartao titulo="Quero juntar...">
        <div className="grid gap-3 sm:grid-cols-2">
          <CampoValor rotulo="Meta" value={dados.alvo} onChange={(e) => onChange({ alvo: e.target.value })} />
          <CampoValor rotulo="Valor que já tenho" value={dados.inicial} onChange={(e) => onChange({ inicial: e.target.value })} />
          <CamposTaxa dados={dados} onChange={onChange} />
        </div>
      </Cartao>

      {alvo > 0 && meses > 0 && (
        <>
          <div className={`rounded-2xl border p-4 ${pronto ? 'border-positivo/40 bg-positivo/5' : 'border-borda bg-painel-2/60'}`}>
            <p className="text-sm text-suave">{pronto ? 'Você já chega lá' : 'Preciso guardar por mês'}</p>
            <p className={`mt-1 text-3xl font-bold ${pronto ? 'text-positivo' : 'text-saldo'}`}>
              {pronto ? dinheiro(inicialNoFim) : dinheiro(porMes)}
            </p>
            <p className="text-xs text-apagado">
              {pronto
                ? `Só com o que já tem, rendendo, em ${meses} meses.`
                : `durante ${meses} ${meses === 1 ? 'mês' : 'meses'} para chegar a ${dinheiro(alvo)}`}
            </p>
          </div>
          {!pronto && (
            <div className="grid grid-cols-2 gap-3">
              <Indicador rotulo="Sem rendimento seria" valor={dinheiro(semRendimento)} detalhe="por mês" />
              <Indicador rotulo="Rendimento ajuda com" valor={dinheiro(alvo - inicial - porMes * meses)} cor="text-positivo" />
            </div>
          )}
        </>
      )}
    </div>
  )
}
