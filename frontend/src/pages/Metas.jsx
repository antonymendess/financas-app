// Metas no formato "cofrinho": quanto quero juntar, até quando e quanto já guardei.
// É só informativo e para incentivar: nada daqui mexe no saldo, nas receitas ou nas despesas.
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ArrowDownCircle, CheckCircle2, Flame, History, Pencil, PiggyBank, Plus, Target, Trash2, TrendingUp } from 'lucide-react'
import { api } from '../lib/api'
import { data, dinheiro, hojeIso, lerValor, mesAno, mesCurto, numeroCurto, valorParaCampo } from '../lib/formato'
import { useCarregar } from '../hooks/useCarregar'
import { useDados } from '../contexts/DadosContext'
import {
  Botao, BotaoIcone, Campo, CampoValor, Cartao, Carregando, Etiqueta, Interruptor, MensagemErro, Modal, Opcoes, Titulo, Vazio,
} from '../components/ui'

// Mesma paleta categórica do Início, sempre na mesma ordem (cor segue a meta, pelo id)
const CORES_METAS = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767']
const CORES = { guardado: '#3987e5', retirado: '#d95926', grade: 'var(--color-borda)', eixo: 'var(--color-apagado)' }

// Frase de incentivo conforme o progresso
function incentivo(m) {
  if (m.concluida) return 'Meta batida! 🎉'
  if (m.marco === 75) return 'Reta final, falta pouco!'
  if (m.marco === 50) return 'Já passou da metade!'
  if (m.marco === 25) return 'Um quarto do caminho!'
  if (m.guardado > 0) return 'Bom começo, continue!'
  return 'Guarde o primeiro valor para começar.'
}

export function coresDasMetas(metas) {
  const cores = {}
  ;[...metas].sort((a, b) => a.id - b.id).forEach((m, i) => {
    cores[m.id] = CORES_METAS[i % CORES_METAS.length]
  })
  return cores
}

export default function Metas() {
  const { versao } = useDados()
  const painel = useCarregar(() => api.get('/metas/painel'), [versao], '/metas/painel')
  const [editando, setEditando] = useState(null) // null | 'nova' | meta
  const [movendo, setMovendo] = useState(null) // { meta, tipo }
  const [historico, setHistorico] = useState(null) // meta

  const p = painel.dados
  const cores = coresDasMetas(p?.metas ?? [])

  return (
    <div className="space-y-6 lg:space-y-8">
      <Titulo acao={<Botao onClick={() => setEditando('nova')}><Plus className="size-4" /> Nova meta</Botao>}>Metas</Titulo>

      {painel.erro && <MensagemErro mensagem={painel.erro} tentarNovamente={painel.recarregar} />}
      {painel.carregando && !p && <Carregando />}

      {p && (
        <div className={`space-y-4 transition-opacity lg:space-y-6 ${painel.carregando ? 'opacity-70' : ''}`}>
          <ResumoCofrinho p={p} />

          {!p.metas.length ? (
            <Cartao>
              <div className="py-8 text-center">
                <PiggyBank className="mx-auto mb-2 size-10 text-apagado" aria-hidden />
                <p className="mb-1 font-medium">Nenhuma meta ainda</p>
                <p className="mb-4 text-sm text-apagado">Ex.: juntar R$ 5.000 para uma viagem até dezembro.</p>
                <Botao onClick={() => setEditando('nova')}><Plus className="size-4" /> Criar primeira meta</Botao>
              </div>
            </Cartao>
          ) : (
            <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {p.metas.map((m) => (
                <CartaoMeta
                  key={m.id}
                  meta={m}
                  cor={cores[m.id]}
                  onEditar={() => setEditando(m)}
                  onMover={(tipo) => setMovendo({ meta: m, tipo })}
                  onHistorico={() => setHistorico(m)}
                />
              ))}
            </ul>
          )}

          <Cartao titulo="Guardado por mês — últimos 12 meses">
            <GraficoHistorico historico={p.historico} />
          </Cartao>
        </div>
      )}

      <Modal aberto={editando !== null} titulo={editando === 'nova' ? 'Nova meta' : 'Editar meta'} onFechar={() => setEditando(null)}>
        {editando !== null && <FormMeta meta={editando === 'nova' ? null : editando} onFechar={() => setEditando(null)} />}
      </Modal>
      <Modal
        aberto={movendo !== null}
        titulo={movendo?.tipo === 'retirar' ? `Retirar de "${movendo?.meta.nome}"` : `Guardar em "${movendo?.meta.nome}"`}
        onFechar={() => setMovendo(null)}
      >
        {movendo && <FormMovimento {...movendo} onFechar={() => setMovendo(null)} />}
      </Modal>
      <Modal aberto={historico !== null} titulo={`Histórico — ${historico?.nome ?? ''}`} onFechar={() => setHistorico(null)}>
        {historico && <HistoricoMeta meta={historico} />}
      </Modal>
    </div>
  )
}

// ---------------------------------------------------------------- resumo geral
function ResumoCofrinho({ p }) {
  const pct = p.progresso_total !== null ? Math.round(p.progresso_total * 100) : null
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="rounded-2xl border border-borda bg-painel-2/60 p-4 sm:col-span-2">
        <p className="flex items-center gap-1.5 text-sm text-suave"><PiggyBank className="size-4" aria-hidden /> Total guardado</p>
        <p className="mt-1 text-3xl font-bold text-saldo">{dinheiro(p.guardado_total)}</p>
        {pct !== null && (
          <>
            <p className="mt-1 text-sm text-suave">de {dinheiro(p.alvo_total)} somando as metas ativas · {pct}%</p>
            <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-borda">
              <div className="h-full rounded-full bg-destaque" style={{ width: `${pct}%` }} />
            </div>
          </>
        )}
      </div>
      <div className="rounded-2xl border border-borda bg-painel p-5">
        <p className="text-sm text-suave">Guardado este mês</p>
        <p className={`mt-1 text-2xl font-bold ${p.guardado_no_mes > 0 ? 'text-positivo' : ''}`}>
          {p.guardado_no_mes > 0 ? '+ ' : ''}{dinheiro(p.guardado_no_mes)}
        </p>
        {p.retirado_no_mes > 0 && (
          <p className="text-sm text-negativo">− {dinheiro(p.retirado_no_mes)} retirado</p>
        )}
        <p className="mt-1 text-xs text-apagado">Só informativo: não mexe no seu saldo.</p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- cartão de cada meta
function CartaoMeta({ meta: m, cor, onEditar, onMover, onHistorico }) {
  const pct = m.progresso !== null ? Math.round(m.progresso * 100) : null

  return (
    <li className={`flex flex-col rounded-2xl border border-borda bg-painel p-5 ${m.ativa ? '' : 'opacity-60'}`}>
      <div className="flex items-start gap-2">
        <span className="mt-1.5 size-2.5 shrink-0 rounded-full" style={{ background: cor }} />
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{m.nome}</p>
          <p className="text-xs text-apagado">{m.data_alvo ? `até ${data(m.data_alvo)}` : 'sem data'}</p>
        </div>
        {m.concluida ? (
          <Etiqueta cor="text-positivo border-positivo/40"><CheckCircle2 className="size-3" aria-hidden /> Concluída</Etiqueta>
        ) : !m.ativa ? (
          <Etiqueta>Pausada</Etiqueta>
        ) : null}
        <BotaoIcone rotulo="Editar meta" onClick={onEditar} className="-mt-2 -mr-2">
          <Pencil className="size-4" />
        </BotaoIcone>
      </div>

      <p className="mt-3 text-2xl font-bold">{dinheiro(m.guardado)}</p>
      {m.valor_alvo ? (
        <>
          <p className="text-sm text-suave">de {dinheiro(m.valor_alvo)} · <span className="font-semibold text-texto">{pct}%</span></p>
          {/* Barra com marcos em 25%, 50% e 75% */}
          <div className="relative mt-2 h-3 w-full overflow-hidden rounded-full bg-borda" role="progressbar" aria-valuenow={pct} aria-valuemax={100}>
            <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: cor }} />
            {[25, 50, 75].map((x) => (
              <span key={x} className="absolute inset-y-0 w-px bg-fundo/70" style={{ left: `${x}%` }} aria-hidden />
            ))}
          </div>
        </>
      ) : (
        <p className="text-sm text-apagado">guardado até agora (sem valor final)</p>
      )}
      <p className="mt-2 text-sm font-medium" style={{ color: cor }}>{incentivo(m)}</p>

      <dl className="mt-3 space-y-1.5 text-sm">
        {m.falta > 0 && (
          <Linha rotulo="Falta">{dinheiro(m.falta)}</Linha>
        )}
        {m.retirado_no_mes > 0 && (
          <Linha rotulo="Retirado este mês"><span className="text-negativo">− {dinheiro(m.retirado_no_mes)}</span></Linha>
        )}
        {m.ritmo > 0 && (
          <Linha rotulo="Seu ritmo">{dinheiro(m.ritmo)}/mês</Linha>
        )}
        {m.previsao && !m.concluida && (
          <Linha rotulo="Nesse ritmo chega em">
            <span className="flex items-center gap-1"><TrendingUp className="size-3.5 text-positivo" aria-hidden />{mesAno(m.previsao)}</span>
          </Linha>
        )}
        {m.precisa_por_mes !== null && !m.concluida && (
          <Linha rotulo={`Para ${data(m.data_alvo)}`}>
            <span className={m.no_ritmo ? 'text-positivo' : 'text-alerta'}>
              guardar {dinheiro(m.precisa_por_mes)}/mês {m.no_ritmo ? '✓' : ''}
            </span>
          </Linha>
        )}
        {m.sequencia >= 2 && (
          <p className="flex items-center gap-1.5 text-alerta">
            <Flame className="size-4" aria-hidden /> {m.sequencia} meses seguidos guardando
          </p>
        )}
      </dl>

      <div className="mt-auto flex gap-2 pt-4">
        <Botao onClick={() => onMover('guardar')} className="flex-1 text-sm" disabled={!m.ativa}>
          <Plus className="size-4" /> Guardei
        </Botao>
        <Botao variante="secundario" onClick={() => onMover('retirar')} className="flex-1 text-sm" disabled={!(m.guardado > 0)}>
          <ArrowDownCircle className="size-4" /> Retirar
        </Botao>
        <BotaoIcone rotulo="Histórico" onClick={onHistorico} className="border border-borda">
          <History className="size-4" />
        </BotaoIcone>
      </div>
    </li>
  )
}

function Linha({ rotulo, children }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-suave">{rotulo}</dt>
      <dd>{children}</dd>
    </div>
  )
}

// ---------------------------------------------------------------- gráfico
function GraficoHistorico({ historico }) {
  if (!historico.some((h) => h.guardado || h.retirado)) {
    return <Vazio>Quando você anotar valores guardados, a evolução aparece aqui.</Vazio>
  }
  const linhas = historico.map((h) => ({ ...h, rotulo: mesCurto(h.ano, h.mes) }))
  const temRetirada = historico.some((h) => h.retirado)
  return (
    <div className="h-56 w-full lg:h-64">
      <ResponsiveContainer>
        <BarChart data={linhas} margin={{ top: 8, right: 4, left: -8, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={CORES.grade} />
          <XAxis dataKey="rotulo" tick={{ fill: CORES.eixo, fontSize: 11 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis tickFormatter={numeroCurto} tick={{ fill: CORES.eixo, fontSize: 11 }} tickLine={false} axisLine={false} width={58} />
          <Tooltip
            cursor={{ fill: 'var(--color-painel-2)' }}
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <div className="rounded-xl border border-borda bg-painel px-3 py-2 text-xs shadow-xl">
                  <p className="font-semibold">{label}</p>
                  <p>Guardado: {dinheiro(payload[0].payload.guardado)}</p>
                  {payload[0].payload.retirado > 0 && <p>Retirado: {dinheiro(payload[0].payload.retirado)}</p>}
                </div>
              ) : null
            }
          />
          <Bar dataKey="guardado" name="Guardado" fill={CORES.guardado} radius={[4, 4, 0, 0]} maxBarSize={28} />
          {temRetirada && <Bar dataKey="retirado" name="Retirado" fill={CORES.retirado} radius={[4, 4, 0, 0]} maxBarSize={28} />}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ---------------------------------------------------------------- formulários
// Meses entre hoje e a data escolhida (contando o mês atual)
function mesesAte(dataIso) {
  const hoje = hojeIso()
  const [a1, m1] = hoje.split('-').map(Number)
  const [a2, m2] = dataIso.split('-').map(Number)
  return Math.max((a2 - a1) * 12 + (m2 - m1) + 1, 1)
}

function FormMeta({ meta, onFechar }) {
  const { dadosMudaram, avisar, excluir } = useDados()
  const [form, setForm] = useState({
    nome: meta?.nome ?? '',
    valor_alvo: valorParaCampo(meta?.valor_alvo),
    data_alvo: meta?.data_alvo ?? '',
    ativa: meta?.ativa ?? true,
  })
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)
  const mudar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value })
  const alvo = lerValor(form.valor_alvo)
  const falta = alvo > 0 ? Math.max(alvo - (meta?.guardado ?? 0), 0) : 0
  const porMes = falta > 0 && form.data_alvo ? falta / mesesAte(form.data_alvo) : null

  const salvar = async (e) => {
    e.preventDefault()
    if (Number.isNaN(alvo)) return setErro('Valor da meta inválido.')
    setSalvando(true)
    setErro(null)
    const corpo = { nome: form.nome, valor_alvo: alvo || null, data_alvo: form.data_alvo || null, ativa: form.ativa }
    try {
      if (meta) await api.put(`/metas/${meta.id}`, corpo)
      else await api.post('/metas', corpo)
      avisar('Meta salva')
      dadosMudaram()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  const apagar = async () => {
    if (await excluir(`/metas/${meta.id}`, `a meta "${meta.nome}" e todo o histórico dela`)) onFechar()
  }

  return (
    <form onSubmit={salvar} className="space-y-4">
      <Campo rotulo="Nome" value={form.nome} onChange={mudar('nome')} required maxLength={300} autoFocus={!meta} placeholder="Ex.: Viagem, Reserva de emergência" />
      <div className="grid grid-cols-2 gap-3">
        <CampoValor rotulo="Quanto quero juntar" value={form.valor_alvo} onChange={mudar('valor_alvo')} />
        <Campo rotulo="Até quando (opcional)" type="date" value={form.data_alvo} onChange={mudar('data_alvo')} />
      </div>
      {porMes !== null && (
        <p className="rounded-xl bg-painel-2 p-3 text-sm text-suave">
          Para chegar lá, guarde cerca de <span className="font-semibold text-texto">{dinheiro(porMes)}</span> por mês.
        </p>
      )}
      <p className="text-xs text-apagado">A meta é só um acompanhamento: ela não tira dinheiro do saldo nem vira despesa.</p>
      {meta && (
        <Interruptor
          rotulo="Meta ativa"
          dica={form.ativa ? 'Aparece no total das metas' : 'Pausada: guarda o histórico, mas sai do total'}
          checked={form.ativa}
          onChange={(ativa) => setForm({ ...form, ativa })}
        />
      )}
      {erro && <MensagemErro mensagem={erro} />}
      <div className="flex gap-2">
        {meta && <Botao type="button" variante="perigo" onClick={apagar}><Trash2 className="size-4" /> Excluir</Botao>}
        <Botao type="submit" carregando={salvando} className="flex-1"><Target className="size-4" /> Salvar</Botao>
      </div>
    </form>
  )
}

// Motivos rápidos de retirada (viram a observação, que aparece no histórico)
const MOTIVOS_RETIRADA = ['Usei no objetivo da meta', 'Emergência', 'Imprevisto do mês']

function FormMovimento({ meta, tipo, onFechar }) {
  const { dadosMudaram, avisar } = useDados()
  const sugestao = tipo === 'guardar' && meta.precisa_por_mes && meta.guardado_no_mes === 0 ? meta.precisa_por_mes : null
  const [form, setForm] = useState({ valor: sugestao ? valorParaCampo(sugestao) : '', data: hojeIso(), descricao: '' })
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)
  const mudar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value })

  const salvar = async (e) => {
    e.preventDefault()
    const valor = lerValor(form.valor)
    if (!valor || valor <= 0) return setErro('Informe um valor maior que zero.')
    if (tipo === 'retirar' && valor > meta.guardado) return setErro(`Essa meta só tem ${dinheiro(meta.guardado)} guardado.`)
    setSalvando(true)
    setErro(null)
    try {
      await api.post(`/metas/${meta.id}/movimentos`, { ...form, tipo, valor })
      avisar(tipo === 'guardar' ? 'Valor anotado na meta' : 'Retirada anotada')
      dadosMudaram()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-4">
      {tipo === 'guardar' ? (
        <p className="text-sm text-suave">Anote quanto você separou (na poupança, na conta, onde for). Isso não mexe no saldo do app.</p>
      ) : (
        <p className="text-sm text-suave">Guardado nesta meta: <span className="font-semibold text-texto">{dinheiro(meta.guardado)}</span></p>
      )}
      <CampoValor rotulo={tipo === 'guardar' ? 'Quanto você guardou' : 'Quanto você tirou'} value={form.valor} onChange={mudar('valor')} required autoFocus />
      {sugestao && <p className="-mt-2 text-xs text-apagado">Sugestão para manter a data: {dinheiro(sugestao)}</p>}
      {tipo === 'retirar' && (
        <button type="button" onClick={() => setForm({ ...form, valor: valorParaCampo(meta.guardado) })} className="-mt-2 text-xs text-saldo">
          Retirar tudo ({dinheiro(meta.guardado)})
        </button>
      )}
      {tipo === 'retirar' && (
        <Opcoes
          rotulo="Por quê?"
          opcoes={MOTIVOS_RETIRADA}
          valor={form.descricao}
          onChange={(descricao) => setForm({ ...form, descricao })}
        />
      )}
      <Campo rotulo="Data" type="date" value={form.data} onChange={mudar('data')} required />
      <Campo
        rotulo="Observação (opcional)"
        value={form.descricao}
        onChange={mudar('descricao')}
        maxLength={300}
        placeholder={tipo === 'retirar' ? 'Ex.: paguei a passagem' : 'Ex.: transferi para a poupança'}
      />
      {tipo === 'retirar' && (
        <p className="text-xs text-apagado">A retirada diminui o guardado da meta, mas não conta contra o seu ritmo nem quebra a sequência de meses guardando.</p>
      )}
      {erro && <MensagemErro mensagem={erro} />}
      <Botao type="submit" carregando={salvando} variante={tipo === 'retirar' ? 'perigo' : 'primario'} className="w-full">
        {tipo === 'retirar' ? 'Anotar retirada' : 'Anotar valor guardado'}
      </Botao>
    </form>
  )
}

function HistoricoMeta({ meta }) {
  const { versao, excluir } = useDados()
  const { dados, carregando, erro } = useCarregar(() => api.get(`/metas/${meta.id}/movimentos`), [meta.id, versao], `/metas/${meta.id}/movimentos`)

  if (erro) return <MensagemErro mensagem={erro} />
  if (carregando && !dados) return <Carregando />
  if (!dados.length) return <Vazio>Nada guardado nesta meta ainda.</Vazio>
  return (
    <ul className="divide-y divide-borda">
      {dados.map((x) => (
        <li key={x.id} className="flex items-center gap-3 py-2">
          <span className="w-20 shrink-0 text-sm text-suave">{data(x.data)}</span>
          <span className="min-w-0 flex-1 truncate text-sm text-apagado">{x.descricao ?? (x.valor > 0 ? 'Guardado' : 'Retirada')}</span>
          <span className={`text-sm font-medium ${x.valor > 0 ? 'text-positivo' : 'text-negativo'}`}>
            {x.valor > 0 ? '+' : '−'} {dinheiro(Math.abs(x.valor))}
          </span>
          <BotaoIcone rotulo="Excluir registro" onClick={() => excluir(`/metas/movimentos/${x.id}`, `este registro de ${dinheiro(Math.abs(x.valor))}`)} className="hover:text-negativo">
            <Trash2 className="size-4" />
          </BotaoIcone>
        </li>
      ))}
    </ul>
  )
}
