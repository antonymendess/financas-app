// Visão de vários meses somados (Início → "Período"): totais, evolução mês a mês,
// quem recebeu/gastou quanto, categorias e as maiores despesas do período.
import { useState } from 'react'
import {
  Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { ArrowDownCircle, ArrowUpCircle, TrendingDown, TrendingUp } from 'lucide-react'
import { api } from '../lib/api'
import { dinheiro, mesAno, mesCurto, numeroCurto } from '../lib/formato'
import { useCarregar } from '../hooks/useCarregar'
import { useDados } from '../contexts/DadosContext'
import { mesAtual, somarMes } from './SeletorMes'
import { MarcaPessoa } from './CampoResponsavel'
import { Cartao, Carregando, MensagemErro, Opcoes, Vazio } from './ui'

const CORES = { receitas: '#199e70', despesas: '#d95926', saldo: '#3987e5', grade: 'var(--color-borda)', eixo: 'var(--color-apagado)' }
const CORES_CATEGORIAS = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767']

const paraTexto = ({ ano, mes }) => `${ano}-${String(mes).padStart(2, '0')}`

// Atalhos de período (sempre terminando/começando no mês atual)
function atalho(chave) {
  const atual = mesAtual()
  if (chave === '3m') return { inicio: somarMes(atual, -2), fim: atual }
  if (chave === '6m') return { inicio: somarMes(atual, -5), fim: atual }
  if (chave === '12m') return { inicio: somarMes(atual, -11), fim: atual }
  if (chave === 'ano') return { inicio: { ano: atual.ano, mes: 1 }, fim: { ano: atual.ano, mes: 12 } }
  if (chave === 'prox6') return { inicio: atual, fim: somarMes(atual, 5) }
  return null
}

const ATALHOS = [
  { valor: '3m', rotulo: 'Últimos 3 meses' },
  { valor: '6m', rotulo: 'Últimos 6 meses' },
  { valor: '12m', rotulo: 'Últimos 12 meses' },
  { valor: 'ano', rotulo: `Ano de ${mesAtual().ano}` },
  { valor: 'prox6', rotulo: 'Próximos 6 meses' },
  { valor: 'outro', rotulo: 'Escolher…' },
]

export default function VisaoPeriodo({ pessoa, onEscolherMes }) {
  const { versao } = useDados()
  const [escolha, setEscolha] = useState('6m')
  const [faixa, setFaixa] = useState(() => {
    const a = atalho('6m')
    return { inicio: paraTexto(a.inicio), fim: paraTexto(a.fim) }
  })

  const escolher = (chave) => {
    setEscolha(chave)
    const a = atalho(chave)
    if (a) setFaixa({ inicio: paraTexto(a.inicio), fim: paraTexto(a.fim) })
  }

  const filtro = pessoa ? `&responsavel=${pessoa}` : ''
  const valido = faixa.inicio && faixa.fim && faixa.inicio <= faixa.fim
  const periodo = useCarregar(
    () => (valido ? api.get(`/periodo?inicio=${faixa.inicio}&fim=${faixa.fim}${filtro}`) : Promise.resolve(null)),
    [faixa.inicio, faixa.fim, filtro, versao],
    valido ? `/periodo?inicio=${faixa.inicio}&fim=${faixa.fim}${filtro}` : null,
  )
  const p = periodo.dados

  return (
    <div className="space-y-6 lg:space-y-8">
      <div className="space-y-3">
        <Opcoes opcoes={ATALHOS} valor={escolha} onChange={escolher} />
        {escolha === 'outro' && (
          <div className="grid max-w-md grid-cols-2 gap-3">
            <CampoMes rotulo="De" value={faixa.inicio} onChange={(inicio) => setFaixa({ ...faixa, inicio })} />
            <CampoMes rotulo="Até" value={faixa.fim} onChange={(fim) => setFaixa({ ...faixa, fim })} />
          </div>
        )}
        {!valido && <p className="text-sm text-negativo">O mês final precisa ser depois do inicial.</p>}
      </div>

      {periodo.erro && <MensagemErro mensagem={periodo.erro} tentarNovamente={periodo.recarregar} />}
      {periodo.carregando && !p && <Carregando />}

      {p && (
        <div className={`space-y-4 transition-opacity lg:space-y-6 ${periodo.carregando ? 'opacity-70' : ''}`}>
          <Totais p={p} />

          <div className="grid gap-4 lg:grid-cols-3 lg:gap-6">
            <Cartao titulo={`Mês a mês · ${mesAno(p.inicio)} a ${mesAno(p.fim)}`} className="lg:col-span-2">
              <Grafico meses={p.meses} onEscolherMes={onEscolherMes} />
            </Cartao>
            <Cartao titulo="Maiores despesas do período">
              {p.maiores_despesas.length ? (
                <ol className="space-y-1.5 text-sm">
                  {p.maiores_despesas.map((d, i) => (
                    <li key={d.nome} className="flex items-center gap-2">
                      <span className="w-5 text-right text-xs text-apagado">{i + 1}</span>
                      <span className="flex-1 truncate">{d.nome}</span>
                      <span className="font-medium">{dinheiro(d.valor)}</span>
                    </li>
                  ))}
                </ol>
              ) : <Vazio>Nenhuma despesa no período.</Vazio>}
            </Cartao>
          </div>

          {!pessoa && p.por_responsavel.length > 0 && <PorPessoaPeriodo itens={p.por_responsavel} />}

          <div className="grid gap-4 lg:grid-cols-2 lg:gap-6">
            <Cartao titulo="Despesas por categoria">
              <Categorias itens={p.por_categoria} total={p.total_despesas} />
            </Cartao>
            <Cartao titulo="Tabela mês a mês">
              <TabelaMeses meses={p.meses} onEscolherMes={onEscolherMes} />
            </Cartao>
          </div>
        </div>
      )}
    </div>
  )
}

function CampoMes({ rotulo, value, onChange }) {
  return (
    <label className="block min-w-0">
      <span className="mb-1 block text-sm text-suave">{rotulo}</span>
      <input
        type="month"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-h-11 w-full min-w-0 rounded-xl border border-borda bg-painel px-3 text-texto focus:border-apagado focus:outline-none"
      />
    </label>
  )
}

function Totais({ p }) {
  const positivo = p.saldo >= 0
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <div className={`col-span-2 rounded-2xl border p-4 ${positivo ? 'border-positivo/40 bg-positivo/5' : 'border-negativo/50 bg-negativo/5'}`}>
        <p className="flex items-center gap-1.5 text-sm text-suave">
          {positivo ? <TrendingUp className="size-4" aria-hidden /> : <TrendingDown className="size-4" aria-hidden />}
          {positivo ? 'Sobrou no período' : 'Faltou no período'}
        </p>
        <p className={`mt-1 text-3xl font-bold ${positivo ? 'text-positivo' : 'text-negativo'}`}>{dinheiro(p.saldo)}</p>
        <p className="mt-1 text-sm text-suave">média de {dinheiro(p.media_saldo)} por mês · {p.meses.length} meses</p>
        {p.comissoes_a_receber > 0 && (
          <p className="mt-1 text-xs text-alerta">conta com {dinheiro(p.comissoes_a_receber)} de comissões ainda não recebidas</p>
        )}
      </div>
      <div className="rounded-2xl border border-borda bg-painel p-5">
        <p className="flex items-center gap-1 text-sm text-suave"><ArrowUpCircle className="size-4" aria-hidden /> Entrou</p>
        <p className="mt-1 text-xl font-bold">{dinheiro(p.total_receitas)}</p>
        <p className="mt-2 text-xs text-apagado">Melhor mês: {mesCurto(p.melhor_mes.ano, p.melhor_mes.mes)} ({dinheiro(p.melhor_mes.saldo)})</p>
      </div>
      <div className="rounded-2xl border border-borda bg-painel p-5">
        <p className="flex items-center gap-1 text-sm text-suave"><ArrowDownCircle className="size-4" aria-hidden /> Saiu</p>
        <p className="mt-1 text-xl font-bold">{dinheiro(p.total_despesas)}</p>
        <p className="mt-2 text-xs text-apagado">Mês mais apertado: {mesCurto(p.pior_mes.ano, p.pior_mes.mes)} ({dinheiro(p.pior_mes.saldo)})</p>
      </div>
    </div>
  )
}

function Grafico({ meses, onEscolherMes }) {
  const linhas = meses.map((m) => ({ ...m, rotulo: mesCurto(m.ano, m.mes) }))
  const escolher = (e) => {
    const m = linhas[e?.activeTooltipIndex]
    if (m) onEscolherMes({ ano: m.ano, mes: m.mes })
  }
  return (
    <div className="h-64 w-full lg:h-72">
      <ResponsiveContainer>
        <ComposedChart data={linhas} margin={{ top: 8, right: 4, left: -8, bottom: 0 }} barGap={2} onClick={escolher} className="cursor-pointer">
          <CartesianGrid vertical={false} stroke={CORES.grade} />
          <XAxis dataKey="rotulo" tick={{ fill: CORES.eixo, fontSize: 11 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis tickFormatter={numeroCurto} tick={{ fill: CORES.eixo, fontSize: 11 }} tickLine={false} axisLine={false} width={58} />
          <Tooltip
            cursor={{ fill: 'var(--color-painel-2)' }}
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <div className="rounded-xl border border-borda bg-painel px-3 py-2 text-xs shadow-xl">
                  <p className="mb-1 font-semibold">{label}</p>
                  {payload.map((x) => (
                    <p key={x.dataKey} className="flex items-center gap-2">
                      <span className="size-2 rounded-full" style={{ background: x.color }} />
                      <span className="text-suave">{x.name}:</span> {dinheiro(x.value)}
                    </p>
                  ))}
                  <p className="mt-1 text-apagado">Clique para abrir este mês</p>
                </div>
              ) : null
            }
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: CORES.eixo }} />
          <Bar dataKey="receitas" name="Entrou" fill={CORES.receitas} radius={[4, 4, 0, 0]} maxBarSize={22} />
          <Bar dataKey="despesas" name="Saiu" fill={CORES.despesas} radius={[4, 4, 0, 0]} maxBarSize={22} />
          <Line dataKey="saldo" name="Sobra" stroke={CORES.saldo} strokeWidth={2} dot={{ r: 3, fill: CORES.saldo }} type="monotone" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

function PorPessoaPeriodo({ itens }) {
  const pessoas = itens.filter((p) => p.responsavel_id !== null)
  const conjunto = itens.find((p) => p.responsavel_id === null)
  return (
    <Cartao titulo="Cada um no período">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {pessoas.map((p) => (
          <div key={p.responsavel_id} className="rounded-xl border border-borda bg-painel-2 p-4 text-sm">
            <MarcaPessoa id={p.responsavel_id} className="font-semibold" />
            <dl className="mt-3 space-y-1">
              <div className="flex justify-between"><dt className="text-suave">Recebeu</dt><dd className="text-positivo">+ {dinheiro(p.receitas)}</dd></div>
              <div className="flex justify-between"><dt className="text-suave">Contas próprias</dt><dd>− {dinheiro(p.despesas)}</dd></div>
              {conjunto && (
                <div className="flex justify-between">
                  <dt className="text-suave">Parte do conjunto</dt>
                  <dd>{p.parte_conjunto >= 0 ? '− ' : '+ '}{dinheiro(Math.abs(p.parte_conjunto))}</dd>
                </div>
              )}
            </dl>
            <p className="mt-2 flex items-baseline justify-between border-t border-borda pt-2">
              <span className="font-medium">Sobrou</span>
              <span className={`text-xl font-bold ${p.saldo_final >= 0 ? 'text-positivo' : 'text-negativo'}`}>{dinheiro(p.saldo_final)}</span>
            </p>
          </div>
        ))}
        {conjunto && (
          <div className="rounded-xl border border-dashed border-borda p-4 text-sm">
            <MarcaPessoa id={null} className="font-semibold" />
            <p className="mt-3 text-suave">Contas da casa no período</p>
            <p className="text-xl font-bold">{dinheiro(conjunto.despesas)}</p>
            {conjunto.receitas > 0 && <p className="mt-1 text-xs text-alerta">{dinheiro(conjunto.receitas)} em receitas sem pessoa</p>}
          </div>
        )}
      </div>
    </Cartao>
  )
}

function Categorias({ itens, total }) {
  if (!itens.length) return <Vazio>Nenhuma despesa no período.</Vazio>
  const maior = itens[0].valor
  return (
    <ul className="space-y-2.5 text-sm">
      {itens.slice(0, 10).map((c, i) => (
        <li key={c.nome}>
          <div className="flex justify-between gap-2">
            <span className="truncate">{c.nome}</span>
            <span><span className="text-xs text-apagado">{Math.round((c.valor / total) * 100)}% · </span>{dinheiro(c.valor)}</span>
          </div>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-borda">
            <div className="h-full rounded-full" style={{ width: `${(c.valor / maior) * 100}%`, background: CORES_CATEGORIAS[i % CORES_CATEGORIAS.length] }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

function TabelaMeses({ meses, onEscolherMes }) {
  return (
    <div className="-mx-1 overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-suave">
          <tr>
            <th className="px-1 py-1.5 font-medium">Mês</th>
            <th className="px-1 py-1.5 text-right font-medium">Entrou</th>
            <th className="px-1 py-1.5 text-right font-medium">Saiu</th>
            <th className="px-1 py-1.5 text-right font-medium">Sobra</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-borda/60">
          {meses.map((m) => (
            <tr key={`${m.ano}-${m.mes}`} onClick={() => onEscolherMes({ ano: m.ano, mes: m.mes })} className="cursor-pointer hover:bg-painel-2/60">
              <td className="px-1 py-2">{mesCurto(m.ano, m.mes)}</td>
              <td className="px-1 py-2 text-right">{dinheiro(m.receitas)}</td>
              <td className="px-1 py-2 text-right">{dinheiro(m.despesas)}</td>
              <td className={`px-1 py-2 text-right font-medium ${m.saldo >= 0 ? 'text-positivo' : 'text-negativo'}`}>{dinheiro(m.saldo)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
