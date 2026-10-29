// Comissões no mesmo modelo da planilha: Contratos, Negociações (funil) e Resumo.
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Check, ChevronDown, Handshake, Pencil, Phone, Plus, Receipt, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { data, dataCurta, diasAte, dinheiro, hojeIso, lerValor, mesAno, MESES, valorParaCampo } from '../lib/formato'
import { useCarregar } from '../hooks/useCarregar'
import { useDados } from '../contexts/DadosContext'
import SeletorMes, { mesAtual, somarMes } from '../components/SeletorMes'
import CampoResponsavel, { MarcaPessoa, responsavelParaApi, useResponsaveis } from '../components/CampoResponsavel'
import {
  Abas, AreaTexto, BarraProgresso, Botao, BotaoIcone, Campo, CampoValor, Cartao, Carregando,
  Etiqueta, Indicador, Interruptor, MensagemErro, Modal, Opcoes, Selecao, Titulo, Vazio,
} from '../components/ui'

const COR_STATUS = {
  Quitado: 'border-positivo/50 text-positivo',
  'Em andamento': 'border-alerta/50 text-alerta',
  'A iniciar': 'border-borda text-suave',
}
const ETAPAS = ['Contato inicial', 'Proposta enviada', 'Em negociação', 'Aguardando assinatura', 'Fechado', 'Perdido']
const ENCERRADAS = ['Fechado', 'Perdido']
const PREF_LANCAR = 'lancar-comissao-em-receitas'

// Preferência "lançar em Receitas ao marcar recebida" (padrão: ligado), guardada no aparelho
function lerPreferenciaLancar() {
  try {
    return localStorage.getItem(PREF_LANCAR) !== 'nao'
  } catch {
    return true
  }
}

export default function Comissoes() {
  const { versao } = useDados()
  const [params, setParams] = useSearchParams()
  const aba = params.get('aba') ?? 'contratos'
  const comissoes = useCarregar(() => api.get('/comissoes'), [versao], '/comissoes')
  const negociacoes = useCarregar(() => api.get('/negociacoes'), [versao], '/negociacoes')
  const [editando, setEditando] = useState(null) // { tipo: 'comissao'|'negociacao', item|null }

  const trocarAba = (valor) => setParams(valor === 'contratos' ? {} : { aba: valor }, { replace: true })
  const novo = () => setEditando({ tipo: aba === 'negociacoes' ? 'negociacao' : 'comissao', item: null })
  const erro = comissoes.erro || negociacoes.erro

  return (
    <div className="space-y-6">
      <Titulo acao={<Botao onClick={novo}><Plus className="size-4" /> {aba === 'negociacoes' ? 'Negociação' : 'Comissão'}</Botao>}>
        Comissões
      </Titulo>
      <Abas
        abas={[
          { valor: 'contratos', rotulo: 'Contratos' },
          { valor: 'negociacoes', rotulo: 'Negociações' },
          { valor: 'resumo', rotulo: 'Resumo' },
        ]}
        ativa={aba}
        onChange={trocarAba}
      />

      {erro && <MensagemErro mensagem={erro} tentarNovamente={() => { comissoes.recarregar(); negociacoes.recarregar() }} />}
      {comissoes.carregando && !comissoes.dados && <Carregando />}

      {comissoes.dados && aba === 'contratos' && (
        <Contratos lista={comissoes.dados} setLista={comissoes.setDados} onEditar={(item) => setEditando({ tipo: 'comissao', item })} />
      )}
      {negociacoes.dados && aba === 'negociacoes' && (
        <Negociacoes lista={negociacoes.dados} onEditar={(item) => setEditando({ tipo: 'negociacao', item })} />
      )}
      {comissoes.dados && aba === 'resumo' && <Resumo lista={comissoes.dados} />}

      <Modal
        aberto={editando !== null}
        titulo={`${editando?.item ? 'Editar' : 'Nova'} ${editando?.tipo === 'negociacao' ? 'negociação' : 'comissão'}`}
        onFechar={() => setEditando(null)}
      >
        {editando?.tipo === 'comissao' && <FormComissao comissao={editando.item} onFechar={() => setEditando(null)} />}
        {editando?.tipo === 'negociacao' && <FormNegociacao negociacao={editando.item} onFechar={() => setEditando(null)} />}
      </Modal>
    </div>
  )
}

// =====================================================================
// Contratos
// =====================================================================
function Contratos({ lista, setLista, onEditar }) {
  const { dadosMudaram, avisar, excluir } = useDados()
  const responsaveis = useResponsaveis()
  const [mes, setMes] = useState(mesAtual)
  const [status, setStatus] = useState('')
  const [lancarReceita, setLancarReceita] = useState(lerPreferenciaLancar)

  const mudarLancar = (valor) => {
    setLancarReceita(valor)
    try {
      localStorage.setItem(PREF_LANCAR, valor ? 'sim' : 'nao')
    } catch {
      /* sem armazenamento: vale só nesta sessão */
    }
  }

  const totais = useMemo(() => {
    const contratado = lista.reduce((s, c) => s + c.valor_comissao, 0)
    const recebido = lista.reduce((s, c) => s + c.total_recebido, 0)
    return { contratado, recebido, falta: contratado - recebido }
  }, [lista])

  // O que entra no mês escolhido, separado em dia 15 e segunda quinzena
  const doMes = useMemo(() => {
    const prefixo = `${mes.ano}-${String(mes.mes).padStart(2, '0')}`
    const r = { dia15: 0, dia30: 0, recebido: 0, aReceber: 0 }
    for (const c of lista) {
      for (const p of c.parcelas) {
        if (!p.data_prevista.startsWith(prefixo)) continue
        if (Number(p.data_prevista.slice(8)) <= 15) r.dia15 += p.valor
        else r.dia30 += p.valor
        if (p.paga) r.recebido += p.valor
        else r.aReceber += p.valor
      }
    }
    return r
  }, [lista, mes])

  const filtrada = status ? lista.filter((c) => c.status === status) : lista

  const alternarParcela = async (comissao, parcela) => {
    const paga = !parcela.paga
    // Atualiza a tela na hora; se a API falhar, recarrega
    setLista((todas) =>
      todas.map((c) => {
        if (c.id !== comissao.id) return c
        const parcelas = c.parcelas.map((p) =>
          p.id === parcela.id ? { ...p, paga, paga_em: paga ? hojeIso() : null, receita_id: paga ? p.receita_id : null } : p,
        )
        const pagas = parcelas.filter((p) => p.paga)
        const recebido = pagas.reduce((s, p) => s + p.valor, 0)
        const st = pagas.length >= parcelas.length ? 'Quitado' : pagas.length ? 'Em andamento' : 'A iniciar'
        return { ...c, parcelas, pagas: pagas.length, em_aberto: parcelas.length - pagas.length, total_recebido: recebido, total_a_receber: c.valor_comissao - recebido, status: st }
      }),
    )
    try {
      await api.patch(`/comissoes/parcelas/${parcela.id}`, { paga, lancar_receita: lancarReceita })
      if (paga) avisar(`${parcela.numero}ª parcela recebida${lancarReceita ? ' · lançada em Receitas' : ''}`)
      else avisar(parcela.receita_id ? 'Recebimento desmarcado · receita removida' : 'Recebimento desmarcado')
    } catch (e) {
      avisar(e.message)
    }
    dadosMudaram()
  }

  const apagar = (c) => excluir(`/comissoes/${c.id}`, `a comissão de "${c.cliente}" e todas as parcelas`)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Indicador rotulo="Comissão contratada" valor={dinheiro(totais.contratado)} detalhe={`${lista.length} contratos`} />
        <Indicador rotulo="Já recebido" valor={dinheiro(totais.recebido)} cor="text-positivo" />
        <Indicador rotulo="Falta receber" valor={dinheiro(totais.falta)} />
        <div className="rounded-2xl border border-borda bg-painel p-4">
          <p className="text-xs text-suave">Recebido</p>
          <p className="mt-0.5 text-lg font-semibold">{totais.contratado ? Math.round((totais.recebido / totais.contratado) * 100) : 0}%</p>
          <BarraProgresso atual={totais.recebido} total={totais.contratado} cor="bg-positivo" />
        </div>
      </div>

      <Cartao titulo="Recebimentos do mês">
        <div className="grid gap-3 lg:grid-cols-[18rem_1fr] lg:items-center">
          <SeletorMes valor={mes} onChange={setMes} />
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <ResumoMini rotulo="Dia 15" valor={doMes.dia15} />
            <ResumoMini rotulo="Dia 30" valor={doMes.dia30} />
            <ResumoMini rotulo="Recebido" valor={doMes.recebido} cor="text-positivo" />
            <ResumoMini rotulo="A receber" valor={doMes.aReceber} />
          </div>
        </div>
      </Cartao>

      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <Opcoes
          opcoes={[{ valor: '', rotulo: 'Todos' }, { valor: 'A iniciar', rotulo: 'A iniciar' }, { valor: 'Em andamento', rotulo: 'Em andamento' }, { valor: 'Quitado', rotulo: 'Quitados' }]}
          valor={status}
          onChange={setStatus}
        />
        <div className="rounded-2xl border border-borda bg-painel px-4 lg:w-96">
          <Interruptor
            rotulo="Lançar em Receitas ao marcar recebida"
            dica="Cria a receita na data em que você marcou"
            checked={lancarReceita}
            onChange={mudarLancar}
          />
        </div>
      </div>

      {!filtrada.length && <Vazio>Nenhum contrato. Use o botão "Comissão" ou feche uma negociação.</Vazio>}

      {/* Celular */}
      <div className="space-y-3 lg:hidden">
        {filtrada.map((c) => (
          <Cartao key={c.id}>
            <div className="flex items-start justify-between gap-2">
              <button onClick={() => onEditar(c)} className="min-w-0 text-left">
                <p className="truncate font-semibold">{c.cliente}</p>
                <p className="text-xs text-apagado">
                  {mesAno(c.mes_fechamento.slice(0, 7))} · {dinheiro(c.valor_implantacao)} × {c.percentual}%
                  {c.mensalidade ? ` · mensal. ${dinheiro(c.mensalidade)}` : ''}
                </p>
                {c.telefone && <TelefoneLink telefone={c.telefone} />}
                {responsaveis.ativo && <MarcaPessoa id={c.responsavel_id} className="mt-0.5 flex text-xs text-suave" />}
              </button>
              <div className="text-right">
                <p className="font-bold">{dinheiro(c.valor_comissao)}</p>
                <Etiqueta cor={COR_STATUS[c.status]}>{c.status}</Etiqueta>
              </div>
            </div>
            <div className="mt-3 mb-1 flex justify-between text-xs text-suave">
              <span>Recebido {dinheiro(c.total_recebido)}</span>
              <span>Falta {dinheiro(c.total_a_receber)}</span>
            </div>
            <BarraProgresso atual={c.total_recebido} total={c.valor_comissao} cor="bg-positivo" />
            <div className="mt-3 flex flex-wrap gap-2">
              {c.parcelas.map((p) => (
                <ChipParcela key={p.id} parcela={p} onClick={() => alternarParcela(c, p)} />
              ))}
            </div>
            <div className="mt-2 flex justify-end gap-1 border-t border-borda pt-2">
              <BotaoIcone rotulo="Editar" onClick={() => onEditar(c)}><Pencil className="size-4" /></BotaoIcone>
              <BotaoIcone rotulo="Excluir" onClick={() => apagar(c)} className="hover:text-negativo"><Trash2 className="size-4" /></BotaoIcone>
            </div>
          </Cartao>
        ))}
      </div>

      {/* Computador */}
      {filtrada.length > 0 && (
        <div className="hidden overflow-x-auto rounded-2xl border border-borda bg-painel lg:block">
          <table className="w-full text-sm">
            <thead className="border-b border-borda text-left text-xs text-suave">
              <tr>
                <th className="px-4 py-3 font-medium">Cliente</th>
                <th className="px-2 py-3 font-medium">Fechamento</th>
                <th className="px-2 py-3 text-right font-medium">Implantação</th>
                <th className="px-2 py-3 text-right font-medium">Mensalidade</th>
                <th className="px-2 py-3 text-right font-medium">Comissão</th>
                <th className="px-4 py-3 font-medium">Parcelas (clique para marcar recebida)</th>
                <th className="px-2 py-3 text-right font-medium">Recebido</th>
                <th className="px-2 py-3 text-right font-medium">Falta</th>
                <th className="px-2 py-3 font-medium">Status</th>
                <th className="w-24 px-2 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-borda/60">
              {filtrada.map((c) => (
                <tr key={c.id} className="align-top transition hover:bg-painel-2/40">
                  <td className="px-4 py-3">
                    <p className="font-medium">{c.cliente}</p>
                    {c.telefone && <TelefoneLink telefone={c.telefone} />}
                    {responsaveis.ativo && <MarcaPessoa id={c.responsavel_id} className="flex text-xs text-suave" />}
                  </td>
                  <td className="px-2 py-3 text-suave">{mesAno(c.mes_fechamento.slice(0, 7))}</td>
                  <td className="px-2 py-3 text-right">{dinheiro(c.valor_implantacao)}</td>
                  <td className="px-2 py-3 text-right text-suave">{c.mensalidade ? dinheiro(c.mensalidade) : '—'}</td>
                  <td className="px-2 py-3 text-right font-semibold">
                    {dinheiro(c.valor_comissao)}
                    <p className="text-xs font-normal text-apagado">{c.percentual}% · {c.num_parcelas}× {dinheiro(c.valor_parcela)}</p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1.5">
                      {c.parcelas.map((p) => (
                        <ChipParcela key={p.id} parcela={p} onClick={() => alternarParcela(c, p)} compacto />
                      ))}
                    </div>
                  </td>
                  <td className="px-2 py-3 text-right text-positivo">{dinheiro(c.total_recebido)}</td>
                  <td className="px-2 py-3 text-right">{dinheiro(c.total_a_receber)}</td>
                  <td className="px-2 py-3"><Etiqueta cor={COR_STATUS[c.status]}>{c.status}</Etiqueta></td>
                  <td className="px-2 py-2 text-right whitespace-nowrap">
                    <BotaoIcone rotulo="Editar" onClick={() => onEditar(c)}><Pencil className="size-4" /></BotaoIcone>
                    <BotaoIcone rotulo="Excluir" onClick={() => apagar(c)} className="hover:text-negativo"><Trash2 className="size-4" /></BotaoIcone>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function ResumoMini({ rotulo, valor, cor = '' }) {
  return (
    <div className="rounded-xl bg-painel-2 p-2.5">
      <p className="text-xs text-suave">{rotulo}</p>
      <p className={`font-semibold ${cor}`}>{dinheiro(valor)}</p>
    </div>
  )
}

function TelefoneLink({ telefone }) {
  return (
    <a href={`tel:${telefone.replace(/[^\d+]/g, '')}`} className="mt-0.5 inline-flex items-center gap-1 text-xs text-saldo">
      <Phone className="size-3" aria-hidden /> {telefone}
    </a>
  )
}

// Parcela como "chip": verde com ✓ quando recebida
function ChipParcela({ parcela: p, onClick, compacto }) {
  const atrasada = !p.paga && diasAte(p.data_prevista) < 0
  return (
    <button
      onClick={onClick}
      aria-pressed={p.paga}
      title={`${p.numero}ª parcela · ${data(p.data_prevista)} · ${dinheiro(p.valor)}${p.paga ? ' · recebida' : atrasada ? ' · atrasada' : ''}${p.receita_id ? ' · lançada em Receitas' : ''}`}
      className={`inline-flex min-h-9 items-center gap-1.5 rounded-xl border px-2.5 text-xs transition active:scale-95 ${
        p.paga
          ? 'border-positivo/60 bg-positivo/15 text-positivo'
          : atrasada
            ? 'border-negativo/60 bg-negativo/10 text-negativo hover:border-positivo/60'
            : 'border-borda bg-painel-2 text-suave hover:border-positivo/60'
      }`}
    >
      <span className={`flex size-4 items-center justify-center rounded-full border ${p.paga ? 'border-positivo bg-positivo text-fundo' : 'border-apagado'}`}>
        {p.paga && <Check className="size-3" strokeWidth={3.5} />}
      </span>
      {p.numero}ª · {dataCurta(p.data_prevista)}
      {!compacto && <span className="text-apagado">· {dinheiro(p.valor)}</span>}
      {p.receita_id && <Receipt className="size-3" aria-label="lançada em Receitas" />}
    </button>
  )
}

// =====================================================================
// Negociações (funil)
// =====================================================================
function corpoNegociacao(n, mudancas = {}) {
  const campos = ['cliente', 'telefone', 'etapa', 'probabilidade', 'valor_implantacao', 'mensalidade', 'percentual', 'num_parcelas', 'previsao_fechamento', 'ultimo_contato', 'proxima_acao', 'observacao']
  return { ...Object.fromEntries(campos.map((c) => [c, n[c]])), ...mudancas }
}

function Negociacoes({ lista, onEditar }) {
  const { dadosMudaram, avisar, confirmar, excluir } = useDados()
  const [mostrarEncerradas, setMostrarEncerradas] = useState(false)
  const abertas = lista.filter((n) => !ENCERRADAS.includes(n.etapa))
  const encerradas = lista.filter((n) => ENCERRADAS.includes(n.etapa))
  const soma = (campo) => abertas.reduce((s, n) => s + (n[campo] || 0), 0)

  const mudarEtapa = async (n, etapa) => {
    try {
      await api.put(`/negociacoes/${n.id}`, corpoNegociacao(n, { etapa }))
      avisar(`Etapa: ${etapa}`)
      dadosMudaram()
    } catch (e) {
      avisar(e.message)
    }
  }

  const fechar = async (n) => {
    if (!n.valor_implantacao) {
      onEditar(n)
      return avisar('Informe o valor da implantação para fechar.')
    }
    const ok = await confirmar(
      `Fechar com "${n.cliente}"? Será criada a comissão de ${dinheiro(n.comissao_prevista)} em ${n.num_parcelas}x, com a 1ª parcela no próximo dia 15/30.`,
      'Fechar negócio',
    )
    if (!ok) return
    try {
      await api.post(`/negociacoes/${n.id}/fechar`, {})
      avisar('Fechado! Comissão criada em Contratos')
      dadosMudaram()
    } catch (e) {
      avisar(e.message)
    }
  }

  const linha = (n) => (
    <li key={n.id} className="rounded-2xl border border-borda bg-painel p-4 lg:grid lg:grid-cols-[1.4fr_1fr_1fr_1.3fr_auto] lg:items-center lg:gap-4">
      <button onClick={() => onEditar(n)} className="min-w-0 text-left">
        <p className="truncate font-medium">{n.cliente}</p>
        <p className="text-xs text-apagado">
          {n.valor_implantacao ? `Implantação ${dinheiro(n.valor_implantacao)}` : 'Sem valor'} · {n.num_parcelas}x
          {n.mensalidade ? ` · mensal. ${dinheiro(n.mensalidade)}` : ''}
        </p>
        {n.telefone && <TelefoneLink telefone={n.telefone} />}
      </button>
      <div className="mt-2 grid grid-cols-2 gap-2 lg:mt-0 lg:block">
        <Selecao opcoes={ETAPAS} value={n.etapa} onChange={(e) => mudarEtapa(n, e.target.value)} aria-label="Etapa" disabled={Boolean(n.comissao_id)} />
        <p className="self-center text-xs text-apagado lg:mt-1">{n.probabilidade ? `${n.probabilidade}% de chance` : 'Probabilidade —'}</p>
      </div>
      <div className="mt-2 text-sm lg:mt-0">
        <p>{n.comissao_prevista ? dinheiro(n.comissao_prevista) : '—'} <span className="text-xs text-apagado">prevista</span></p>
        {n.comissao_ponderada !== null && <p className="text-xs text-apagado">{dinheiro(n.comissao_ponderada)} ponderada</p>}
      </div>
      <div className="mt-2 text-xs text-suave lg:mt-0">
        {n.proxima_acao && <p className="text-texto">→ {n.proxima_acao}</p>}
        <p>
          {n.previsao_fechamento && `Previsão ${data(n.previsao_fechamento)}`}
          {n.ultimo_contato && ` · último contato ${dataCurta(n.ultimo_contato)}`}
          {n.transferido_em && `Transferido em ${data(n.transferido_em)}`}
        </p>
      </div>
      <div className="mt-2 flex items-center justify-end gap-1 lg:mt-0">
        {!n.comissao_id && n.etapa !== 'Perdido' && (
          <Botao variante="secundario" className="min-h-9 border-positivo/50 text-positivo" onClick={() => fechar(n)}>
            <Handshake className="size-4" /> Fechar
          </Botao>
        )}
        <BotaoIcone rotulo="Editar" onClick={() => onEditar(n)}><Pencil className="size-4" /></BotaoIcone>
        <BotaoIcone rotulo="Excluir" onClick={() => excluir(`/negociacoes/${n.id}`, `a negociação com "${n.cliente}"`)} className="hover:text-negativo"><Trash2 className="size-4" /></BotaoIcone>
      </div>
    </li>
  )

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Indicador rotulo="Negociações abertas" valor={abertas.length} />
        <Indicador rotulo="Comissão prevista" valor={dinheiro(soma('comissao_prevista'))} />
        <Indicador rotulo="Comissão ponderada" valor={dinheiro(soma('comissao_ponderada'))} detalhe="prevista × probabilidade" />
        <Indicador rotulo="Aguardando assinatura" valor={abertas.filter((n) => n.etapa === 'Aguardando assinatura').length} />
        <Indicador rotulo="Perdidas" valor={lista.filter((n) => n.etapa === 'Perdido').length} />
      </div>

      {!abertas.length && <Vazio>Nenhuma negociação aberta. Use o botão "Negociação".</Vazio>}
      <ul className="space-y-2">
        {abertas.map(linha)}
      </ul>

      {encerradas.length > 0 && (
        <div>
          <button onClick={() => setMostrarEncerradas(!mostrarEncerradas)} className="flex items-center gap-1 text-sm text-suave">
            <ChevronDown className={`size-4 transition ${mostrarEncerradas ? 'rotate-180' : ''}`} /> Fechadas e perdidas ({encerradas.length})
          </button>
          {mostrarEncerradas && (
            <ul className="mt-2 space-y-2 opacity-70">
              {encerradas.map(linha)}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

// =====================================================================
// Resumo (indicadores + por mês de fechamento)
// =====================================================================
function Resumo({ lista }) {
  const soma = (f) => lista.reduce((s, c) => s + f(c), 0)
  const contratado = soma((c) => c.valor_comissao)
  const recebido = soma((c) => c.total_recebido)
  const contar = (st) => lista.filter((c) => c.status === st).length

  // 12 meses terminando no mês atual (ou no fechamento mais recente, se for depois)
  const ultimoFechamento = lista.reduce((m, c) => (c.mes_fechamento > m ? c.mes_fechamento : m), hojeIso())
  const fim = { ano: Number(ultimoFechamento.slice(0, 4)), mes: Number(ultimoFechamento.slice(5, 7)) }
  const meses = Array.from({ length: 12 }, (_, i) => somarMes(fim, i - 11))
  const linhas = meses.map((m) => {
    const prefixo = `${m.ano}-${String(m.mes).padStart(2, '0')}`
    const doMes = lista.filter((c) => c.mes_fechamento.startsWith(prefixo))
    const s = (f) => doMes.reduce((t, c) => t + (f(c) || 0), 0)
    return {
      chave: prefixo,
      rotulo: `${MESES[m.mes - 1].slice(0, 3)}/${m.ano}`,
      contratos: doMes.length,
      implantacao: s((c) => c.valor_implantacao),
      mensalidade: s((c) => c.mensalidade),
      comissao: s((c) => c.valor_comissao),
      recebido: s((c) => c.total_recebido),
      aReceber: s((c) => c.total_a_receber),
    }
  })
  const total = (campo) => linhas.reduce((s, l) => s + l[campo], 0)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicador rotulo="Contratos" valor={lista.length} />
        <Indicador rotulo="Comissão contratada" valor={dinheiro(contratado)} />
        <Indicador rotulo="Já recebido" valor={dinheiro(recebido)} cor="text-positivo" detalhe={contratado ? `${Math.round((recebido / contratado) * 100)}% do total` : null} />
        <Indicador rotulo="A receber" valor={dinheiro(contratado - recebido)} />
        <Indicador rotulo="Parcelas" valor={`${soma((c) => c.pagas)} pagas`} detalhe={`${soma((c) => c.em_aberto)} em aberto`} />
        <Indicador rotulo="Contratos por status" valor={`${contar('Quitado')} quitados`} detalhe={`${contar('Em andamento')} em andamento · ${contar('A iniciar')} a iniciar`} />
        <Indicador rotulo="Total vendido (implantação)" valor={dinheiro(soma((c) => c.valor_implantacao))} />
        <Indicador rotulo="Mensalidades somadas" valor={dinheiro(soma((c) => c.mensalidade || 0))} detalhe="recorrente, só informativo" />
      </div>

      <Cartao titulo="Por mês de fechamento">
        <div className="-mx-4 overflow-x-auto px-4">
          <table className="w-full min-w-[40rem] text-sm">
            <thead className="text-left text-xs text-suave">
              <tr className="border-b border-borda">
                <th className="py-2 pr-2 font-medium">Mês</th>
                <th className="px-2 py-2 text-right font-medium">Contratos</th>
                <th className="px-2 py-2 text-right font-medium">Implantação</th>
                <th className="px-2 py-2 text-right font-medium">Mensalidade</th>
                <th className="px-2 py-2 text-right font-medium">Comissão</th>
                <th className="px-2 py-2 text-right font-medium">Já recebido</th>
                <th className="py-2 pl-2 text-right font-medium">A receber</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borda/50">
              {linhas.map((l) => (
                <tr key={l.chave} className={l.contratos ? '' : 'text-apagado'}>
                  <td className="py-2 pr-2">{l.rotulo}</td>
                  <td className="px-2 py-2 text-right">{l.contratos}</td>
                  <td className="px-2 py-2 text-right">{dinheiro(l.implantacao)}</td>
                  <td className="px-2 py-2 text-right">{dinheiro(l.mensalidade)}</td>
                  <td className="px-2 py-2 text-right">{dinheiro(l.comissao)}</td>
                  <td className="px-2 py-2 text-right">{dinheiro(l.recebido)}</td>
                  <td className="py-2 pl-2 text-right">{dinheiro(l.aReceber)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t-2 border-borda font-semibold">
              <tr>
                <td className="py-2 pr-2">Total</td>
                <td className="px-2 py-2 text-right">{total('contratos')}</td>
                <td className="px-2 py-2 text-right">{dinheiro(total('implantacao'))}</td>
                <td className="px-2 py-2 text-right">{dinheiro(total('mensalidade'))}</td>
                <td className="px-2 py-2 text-right">{dinheiro(total('comissao'))}</td>
                <td className="px-2 py-2 text-right text-positivo">{dinheiro(total('recebido'))}</td>
                <td className="py-2 pl-2 text-right">{dinheiro(total('aReceber'))}</td>
              </tr>
            </tfoot>
          </table>
        </div>
        <p className="mt-2 text-xs text-apagado">Valores agrupados pelo mês em que o contrato foi fechado.</p>
      </Cartao>
    </div>
  )
}

// =====================================================================
// Formulários
// =====================================================================
export function FormComissao({ comissao, onFechar }) {
  const { dadosMudaram, avisar, excluir } = useDados()
  const [form, setForm] = useState({
    cliente: comissao?.cliente ?? '',
    valor_implantacao: valorParaCampo(comissao?.valor_implantacao),
    percentual: comissao?.percentual ?? 25,
    num_parcelas: comissao?.num_parcelas ?? 1,
    data_primeira_parcela: comissao?.data_primeira_parcela ?? hojeIso(),
    mes_fechamento: (comissao?.mes_fechamento ?? hojeIso()).slice(0, 7),
    telefone: comissao?.telefone ?? '',
    mensalidade: valorParaCampo(comissao?.mensalidade),
    observacao: comissao?.observacao ?? '',
    responsavel_id: comissao?.responsavel_id ?? '',
  })
  // Datas previstas de cada parcela (só na edição), para ajustar quando o cliente atrasa
  const [datas, setDatas] = useState(() => Object.fromEntries((comissao?.parcelas ?? []).map((p) => [p.id, p.data_prevista])))
  const [detalhes, setDetalhes] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)
  const mudar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value })

  const implantacao = lerValor(form.valor_implantacao)
  const previa = implantacao > 0 ? (implantacao * Number(form.percentual || 0)) / 100 : 0

  const salvar = async (e) => {
    e.preventDefault()
    if (!implantacao || implantacao <= 0) return setErro('Informe o valor da implantação.')
    const mensalidade = lerValor(form.mensalidade)
    if (Number.isNaN(mensalidade)) return setErro('Mensalidade inválida.')
    setSalvando(true)
    setErro(null)
    const corpo = {
      cliente: form.cliente,
      valor_implantacao: implantacao,
      percentual: Number(form.percentual),
      num_parcelas: Number(form.num_parcelas),
      data_primeira_parcela: form.data_primeira_parcela,
      mes_fechamento: `${form.mes_fechamento}-01`,
      telefone: form.telefone || null,
      mensalidade,
      observacao: form.observacao || null,
      responsavel_id: responsavelParaApi(form.responsavel_id),
    }
    try {
      if (comissao) {
        await api.put(`/comissoes/${comissao.id}`, corpo)
        // Mesma quantidade e mesma 1ª data: aplica as datas ajustadas à mão
        const mesmaEstrutura =
          Number(form.num_parcelas) === comissao.num_parcelas && form.data_primeira_parcela === comissao.data_primeira_parcela
        if (mesmaEstrutura) {
          for (const p of comissao.parcelas.filter((p) => p.numero > 1 && datas[p.id] && datas[p.id] !== p.data_prevista)) {
            await api.patch(`/comissoes/parcelas/${p.id}/data`, { data_prevista: datas[p.id] })
          }
        }
      } else {
        await api.post('/comissoes', corpo)
      }
      avisar('Comissão salva')
      dadosMudaram()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  const apagar = async () => {
    try {
      if (await excluir(`/comissoes/${comissao.id}`, `a comissão de "${comissao.cliente}" e todas as parcelas`)) onFechar()
    } catch (e) {
      setErro(e.message)
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-4">
      <Campo rotulo="Cliente" value={form.cliente} onChange={mudar('cliente')} required maxLength={300} autoFocus={!comissao} />
      <div className="grid grid-cols-2 gap-3">
        <CampoValor rotulo="Valor da implantação" value={form.valor_implantacao} onChange={mudar('valor_implantacao')} required />
        <CampoValor rotulo="Mensalidade (info)" value={form.mensalidade} onChange={mudar('mensalidade')} />
      </div>
      <p className="text-sm text-suave">
        Comissão ({form.percentual}%): <span className="font-semibold text-texto">{dinheiro(previa)}</span>
        {Number(form.num_parcelas) > 1 && ` · ${form.num_parcelas}× ${dinheiro(previa / Number(form.num_parcelas))}`}
      </p>
      <Opcoes rotulo="Parcelas" opcoes={[1, 2, 3, 4, 6].map((n) => ({ valor: n, rotulo: `${n}x` }))} valor={form.num_parcelas} onChange={(n) => setForm({ ...form, num_parcelas: n })} />
      <CampoResponsavel rotulo="Quem recebe" valor={form.responsavel_id} onChange={(responsavel_id) => setForm({ ...form, responsavel_id })} />
      <Campo rotulo="Data da 1ª parcela" type="date" value={form.data_primeira_parcela} onChange={mudar('data_primeira_parcela')} required dica="As seguintes caem no dia 15 de cada mês seguinte (quando o cliente paga)." />
      {comissao && comissao.parcelas.length > 1 && (
        <div>
          <span className="mb-1 block text-sm text-suave">Datas das parcelas (ajuste se o cliente atrasar)</span>
          <div className="grid grid-cols-2 gap-2">
            {comissao.parcelas.filter((p) => p.numero > 1).map((p) => (
              <Campo
                key={p.id}
                type="date"
                rotulo={`${p.numero}ª${p.paga ? ' (recebida)' : ''}`}
                value={datas[p.id] ?? ''}
                onChange={(e) => setDatas({ ...datas, [p.id]: e.target.value })}
              />
            ))}
          </div>
          <p className="mt-1 text-xs text-apagado">Se mudar o nº de parcelas ou a data da 1ª, as datas são recalculadas.</p>
        </div>
      )}

      <button type="button" onClick={() => setDetalhes(!detalhes)} className="flex items-center gap-1 text-sm text-suave">
        <ChevronDown className={`size-4 transition ${detalhes ? 'rotate-180' : ''}`} /> Mais detalhes
      </button>
      {detalhes && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <Campo rotulo="Mês do fechamento" type="month" value={form.mes_fechamento} onChange={mudar('mes_fechamento')} required className="col-span-2" />
            <Campo rotulo="% comissão" type="number" min={0.01} max={100} step="0.01" inputMode="decimal" value={form.percentual} onChange={mudar('percentual')} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Campo rotulo="Telefone" type="tel" value={form.telefone} onChange={mudar('telefone')} maxLength={40} />
            <Campo rotulo="Outro nº de parcelas" type="number" min={1} max={600} inputMode="numeric" value={form.num_parcelas} onChange={mudar('num_parcelas')} />
          </div>
          <AreaTexto rotulo="Observação" value={form.observacao} onChange={mudar('observacao')} maxLength={2000} />
        </div>
      )}
      {erro && <MensagemErro mensagem={erro} />}
      <div className="flex gap-2">
        {comissao && <Botao type="button" variante="perigo" onClick={apagar}><Trash2 className="size-4" /> Excluir</Botao>}
        <Botao type="submit" carregando={salvando} className="flex-1">Salvar</Botao>
      </div>
    </form>
  )
}

function FormNegociacao({ negociacao: n, onFechar }) {
  const { dadosMudaram, avisar, excluir } = useDados()
  const [form, setForm] = useState({
    cliente: n?.cliente ?? '',
    telefone: n?.telefone ?? '',
    etapa: n?.etapa ?? 'Contato inicial',
    probabilidade: n?.probabilidade ?? '',
    valor_implantacao: valorParaCampo(n?.valor_implantacao),
    mensalidade: valorParaCampo(n?.mensalidade),
    percentual: n?.percentual ?? 25,
    num_parcelas: n?.num_parcelas ?? 1,
    previsao_fechamento: n?.previsao_fechamento ?? '',
    ultimo_contato: n?.ultimo_contato ?? hojeIso(),
    proxima_acao: n?.proxima_acao ?? '',
    observacao: n?.observacao ?? '',
  })
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)
  const mudar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value })
  const implantacao = lerValor(form.valor_implantacao)

  const salvar = async (e) => {
    e.preventDefault()
    const mensalidade = lerValor(form.mensalidade)
    if (Number.isNaN(implantacao) || Number.isNaN(mensalidade)) return setErro('Valor inválido.')
    setSalvando(true)
    setErro(null)
    const corpo = {
      ...form,
      telefone: form.telefone || null,
      probabilidade: form.probabilidade ? Number(form.probabilidade) : null,
      valor_implantacao: implantacao,
      mensalidade,
      percentual: Number(form.percentual),
      num_parcelas: Number(form.num_parcelas),
      previsao_fechamento: form.previsao_fechamento || null,
      ultimo_contato: form.ultimo_contato || null,
      proxima_acao: form.proxima_acao || null,
      observacao: form.observacao || null,
    }
    try {
      if (n) await api.put(`/negociacoes/${n.id}`, corpo)
      else await api.post('/negociacoes', corpo)
      avisar('Negociação salva')
      dadosMudaram()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  const apagar = async () => {
    try {
      if (await excluir(`/negociacoes/${n.id}`, `a negociação com "${n.cliente}"`)) onFechar()
    } catch (e) {
      setErro(e.message)
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Campo rotulo="Cliente" value={form.cliente} onChange={mudar('cliente')} required maxLength={300} autoFocus={!n} />
        <Campo rotulo="Telefone" type="tel" value={form.telefone} onChange={mudar('telefone')} maxLength={40} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Selecao rotulo="Etapa" opcoes={ETAPAS} value={form.etapa} onChange={mudar('etapa')} disabled={Boolean(n?.comissao_id)} />
        <Selecao rotulo="Probabilidade" vazio="—" opcoes={[10, 25, 50, 75, 90].map((p) => ({ id: p, nome: `${p}%` }))} value={form.probabilidade} onChange={mudar('probabilidade')} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <CampoValor rotulo="Valor implantação" value={form.valor_implantacao} onChange={mudar('valor_implantacao')} />
        <CampoValor rotulo="Mensalidade (info)" value={form.mensalidade} onChange={mudar('mensalidade')} />
      </div>
      {implantacao > 0 && (
        <p className="text-sm text-suave">
          Comissão prevista: <span className="font-semibold text-texto">{dinheiro((implantacao * Number(form.percentual || 0)) / 100)}</span>
        </p>
      )}
      <div className="grid grid-cols-3 gap-3">
        <Campo rotulo="Nº parcelas" type="number" min={1} max={600} inputMode="numeric" value={form.num_parcelas} onChange={mudar('num_parcelas')} />
        <Campo rotulo="Previsão" type="date" value={form.previsao_fechamento} onChange={mudar('previsao_fechamento')} className="col-span-2" />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Campo rotulo="Último contato" type="date" value={form.ultimo_contato} onChange={mudar('ultimo_contato')} className="col-span-2" />
        <Campo rotulo="% comissão" type="number" min={0.01} max={100} step="0.01" inputMode="decimal" value={form.percentual} onChange={mudar('percentual')} />
      </div>
      <Campo rotulo="Próxima ação" value={form.proxima_acao} onChange={mudar('proxima_acao')} placeholder="Ex.: ligar dia 04/09" maxLength={300} />
      <AreaTexto rotulo="Observação" value={form.observacao} onChange={mudar('observacao')} maxLength={2000} />
      {erro && <MensagemErro mensagem={erro} />}
      <div className="flex gap-2">
        {n && <Botao type="button" variante="perigo" onClick={apagar}><Trash2 className="size-4" /> Excluir</Botao>}
        <Botao type="submit" carregando={salvando} className="flex-1">Salvar</Botao>
      </div>
    </form>
  )
}
