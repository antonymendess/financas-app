// Conferência com o saldo real do banco: em vez de depender de anotar todo gasto,
// parte do que existe de fato na conta e soma/subtrai só o que ainda vai acontecer no mês.
import { useState } from 'react'
import { Landmark, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'
import { dataCurta, dinheiro, hojeIso, lerValor } from '../lib/formato'
import { useDados } from '../contexts/DadosContext'
import { MarcaPessoa, useResponsaveis } from './CampoResponsavel'
import { Botao, CaixaPago, CampoValor, Cartao, MensagemErro, Opcoes } from './ui'

const quandoFoi = (dias) => (dias <= 0 ? 'hoje' : dias === 1 ? 'ontem' : `há ${dias} dias`)

// ---------------------------------------------------------------- cartão no Início
export function CartaoConferencia({ conferencia: c, onConferir }) {
  const { excluir } = useDados()

  if (!c) {
    return (
      <button
        onClick={onConferir}
        className="flex w-full items-center gap-3 rounded-2xl border border-borda bg-painel p-5 text-left transition hover:border-apagado/50"
      >
        <Landmark className="size-6 shrink-0 text-saldo" aria-hidden />
        <span className="flex-1">
          <span className="block font-medium">Conferir com o saldo do banco</span>
          <span className="block text-sm text-suave">
            Digite quanto tem na conta e veja quanto deve sobrar de verdade, já contando os gastos que você não anotou.
          </span>
        </span>
        <span className="hidden rounded-xl bg-destaque px-4 py-2 text-sm font-medium text-sobre-destaque sm:block">Conferir</span>
      </button>
    )
  }

  const positivo = c.sobra >= 0
  const desatualizada = c.dias >= 7
  return (
    <Cartao
      titulo="Pelo saldo do banco"
      acao={<span className={`text-sm ${desatualizada ? 'text-alerta' : 'text-suave'}`}>conferido {quandoFoi(c.dias)} ({dataCurta(c.data)})</span>}
    >
      <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
        <div>
          <p className="text-sm text-suave">Deve sobrar no fim do mês</p>
          <p className={`text-3xl font-bold ${positivo ? 'text-positivo' : 'text-negativo'}`}>{dinheiro(c.sobra)}</p>
          {c.a_entrar_previsto > 0 && (
            <p className="text-xs text-alerta">sem as comissões ainda não recebidas: {dinheiro(c.sobra_sem_previstas)}</p>
          )}
          <div className="mt-3 space-y-1 rounded-xl bg-painel-2/60 p-3 text-sm">
            <Linha rotulo="Saldo no banco" valor={dinheiro(c.saldo_real)} />
            <Linha rotulo="+ Ainda vai entrar" valor={dinheiro(c.total_a_entrar)} cor="text-positivo" />
            <Linha rotulo="− Ainda falta pagar" valor={dinheiro(c.total_a_pagar)} />
          </div>
          <PorDia c={c} />
          {c.anterior && <NaoAnotado a={c.anterior} />}
          {desatualizada && <p className="mt-2 text-xs text-alerta">Faz uma semana ou mais: confira de novo para a previsão ficar certa.</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            <Botao variante="secundario" onClick={onConferir} className="text-sm"><RefreshCw className="size-4" /> Conferir de novo</Botao>
            <Botao variante="fantasma" onClick={() => excluir(`/conferencias/${c.id}`, 'esta conferência')} className="text-sm">Desfazer</Botao>
          </div>
        </div>

        {c.por_pessoa.length > 0 ? (
          <div className="grid content-start gap-2 sm:grid-cols-2">
            {c.por_pessoa.map((p) => (
              <div key={p.responsavel_id} className="rounded-xl border border-borda bg-painel-2 p-3 text-sm">
                <MarcaPessoa id={p.responsavel_id} className="font-semibold" />
                <div className="mt-2 space-y-0.5">
                  <Linha rotulo="Tem no banco" valor={dinheiro(p.saldo_real)} />
                  {p.a_entrar > 0 && <Linha rotulo="+ Vai entrar" valor={dinheiro(p.a_entrar)} cor="text-positivo" />}
                  {p.a_pagar > 0 && <Linha rotulo="− Contas próprias" valor={dinheiro(p.a_pagar)} />}
                  {p.parte_conjunto !== 0 && (
                    <Linha rotulo={p.parte_conjunto > 0 ? '− Parte da casa' : '+ Parte do conjunto'} valor={dinheiro(Math.abs(p.parte_conjunto))} />
                  )}
                </div>
                <p className="mt-2 flex items-baseline justify-between border-t border-borda pt-2">
                  <span className="text-suave">Deve ficar com</span>
                  <span className={`text-lg font-bold ${p.sobra >= 0 ? 'text-positivo' : 'text-negativo'}`}>{dinheiro(p.sobra)}</span>
                </p>
              </div>
            ))}
            <p className="text-xs text-apagado sm:col-span-2">
              Se um passou dinheiro para o outro, os valores de cada um mudam, mas o total da casa continua certo.
            </p>
          </div>
        ) : (
          <p className="self-center text-sm text-apagado">
            Conferido com um saldo só (tudo junto). Para ver quanto fica com cada um, confira separado por pessoa.
          </p>
        )}
      </div>
    </Cartao>
  )
}

// Quanto dá para gastar por dia até o fim do mês (só no mês da conferência)
function PorDia({ c }) {
  const hoje = hojeIso()
  const sobra = c.a_entrar_previsto > 0 ? c.sobra_sem_previstas : c.sobra
  if (c.data.slice(0, 7) !== hoje.slice(0, 7) || sobra <= 0) return null
  const [ano, mes, dia] = hoje.split('-').map(Number)
  const ultimo = new Date(ano, mes, 0).getDate()
  const dias = ultimo - dia + 1
  return (
    <p className="mt-3 rounded-xl bg-saldo/10 p-3 text-sm">
      Dá para gastar cerca de <span className="font-semibold">{dinheiro(sobra / dias)} por dia</span> até o dia {ultimo}
      <span className="text-suave"> ({dias} dia{dias > 1 ? 's' : ''}{c.a_entrar_previsto > 0 ? ', sem contar comissões a receber' : ''})</span>
    </p>
  )
}

// Comparação com a conferência anterior: o que saiu da conta sem estar anotado
function NaoAnotado({ a }) {
  const v = a.nao_anotado
  if (Math.abs(v) < 1) {
    return <p className="mt-2 text-xs text-positivo">Desde a conferência de {dataCurta(a.data)}, tudo bateu: nada saiu sem estar anotado ✓</p>
  }
  if (v > 0) {
    return (
      <p className="mt-2 rounded-xl border border-alerta/40 bg-alerta/10 p-3 text-sm">
        Desde {dataCurta(a.data)} ({a.dias} dia{a.dias > 1 ? 's' : ''}) saíram <span className="font-semibold">{dinheiro(v)}</span> que não estão anotados no app
        {a.dias > 1 && <span className="text-suave">, cerca de {dinheiro(v / a.dias)} por dia</span>}.
      </p>
    )
  }
  return (
    <p className="mt-2 text-xs text-suave">
      Desde {dataCurta(a.data)} entraram {dinheiro(-v)} a mais do que o anotado (ou alguma conta foi marcada como paga sem ter saído do banco).
    </p>
  )
}

function Linha({ rotulo, valor, cor = '' }) {
  return (
    <p className="flex justify-between gap-2">
      <span className="text-suave">{rotulo}</span>
      <span className={`whitespace-nowrap ${cor}`}>{valor}</span>
    </p>
  )
}

// ---------------------------------------------------------------- formulário
// `r` é o resumo do mês atual sem filtro de pessoa (para listar tudo o que falta)
export function FormConferencia({ r, onPagar, onFechar }) {
  const { avisar, dadosMudaram } = useDados()
  const responsaveis = useResponsaveis()
  const [modo, setModo] = useState(responsaveis.ativo ? 'separado' : 'junto')
  const [saldos, setSaldos] = useState({}) // id da pessoa (ou 'total') -> texto digitado
  const [negativo, setNegativo] = useState({}) // conta no vermelho
  const pendentes = r.receitas.filter((x) => !x.recebida)
  const [jaEntrou, setJaEntrou] = useState(() => new Set())
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)

  const chave = (x) => `${x.origem}:${x.id}`
  const campos = modo === 'junto' ? [{ id: 'total', nome: 'Saldo da conta' }] : responsaveis.lista
  const valorDe = (id) => {
    const v = lerValor(saldos[id])
    return v === null || Number.isNaN(v) ? v : negativo[id] ? -Math.abs(v) : v
  }

  // Vencidas primeiro: se já saíram do banco e não forem marcadas, são descontadas duas vezes
  const contas = r.vencimentos
    .filter((v) => v.tipo !== 'anotacao' && !v.pago)
    .sort((a, b) => Number(Boolean(b.vencido)) - Number(Boolean(a.vencido)))
  const vencidas = contas.filter((v) => v.vencido).length
  const totalSaldo = campos.reduce((s, c) => s + (valorDe(c.id) || 0), 0)
  const totalEntrar = pendentes.filter((x) => !jaEntrou.has(chave(x))).reduce((s, x) => s + x.valor, 0)
  const totalPagar = r.despesas.filter((d) => !d.pago).reduce((s, d) => s + d.valor, 0)
  const previa = totalSaldo + totalEntrar - totalPagar

  const alternarEntrou = (x) => {
    const novo = new Set(jaEntrou)
    novo.has(chave(x)) ? novo.delete(chave(x)) : novo.add(chave(x))
    setJaEntrou(novo)
  }

  const salvar = async (e) => {
    e.preventDefault()
    if (campos.some((c) => valorDe(c.id) === null)) return setErro('Preencha o saldo de todas as contas (pode ser 0).')
    if (campos.some((c) => Number.isNaN(valorDe(c.id)))) return setErro('Algum saldo está inválido.')
    setSalvando(true)
    setErro(null)
    const corpo = {
      data: hojeIso(),
      junto: modo === 'junto',
      total: modo === 'junto' ? valorDe('total') : null,
      saldos: modo === 'junto' ? [] : campos.map((c) => ({ responsavel_id: c.id, valor: valorDe(c.id) })),
      ja_entrou: [...jaEntrou],
    }
    try {
      await api.post('/conferencias', corpo)
      avisar('Conferência salva')
      dadosMudaram()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-5">
      <section className="space-y-3">
        <p className="font-medium">Quanto tem na conta agora?</p>
        {responsaveis.ativo && (
          <Opcoes
            opcoes={[{ valor: 'separado', rotulo: 'Separado por pessoa' }, { valor: 'junto', rotulo: 'Tudo junto' }]}
            valor={modo}
            onChange={setModo}
          />
        )}
        {campos.map((c) => (
          <div key={c.id} className="flex items-end gap-2">
            <CampoValor
              className="flex-1"
              rotulo={c.id === 'total' ? c.nome : <MarcaPessoa id={c.id} />}
              value={saldos[c.id] ?? ''}
              onChange={(e) => setSaldos({ ...saldos, [c.id]: e.target.value })}
              autoFocus={c === campos[0]}
            />
            <button
              type="button"
              onClick={() => setNegativo({ ...negativo, [c.id]: !negativo[c.id] })}
              aria-pressed={Boolean(negativo[c.id])}
              className={`min-h-11 rounded-xl border px-3 text-sm ${negativo[c.id] ? 'border-negativo bg-negativo/15 text-negativo' : 'border-borda bg-painel-2 text-suave'}`}
              title="Conta no vermelho (saldo negativo)"
            >
              negativo
            </button>
          </div>
        ))}
        <p className="text-xs text-apagado">Só o dinheiro disponível na conta corrente, não a poupança das metas.</p>
      </section>

      {pendentes.length > 0 && (
        <section>
          <p className="font-medium">Ainda vai entrar este mês?</p>
          <p className="mb-2 text-xs text-apagado">Desmarque o que já caiu na conta.</p>
          <ul className="divide-y divide-borda/60 rounded-xl bg-painel-2/50 px-3">
            {pendentes.map((x) => (
              <li key={chave(x)}>
                <label className="flex min-h-11 cursor-pointer items-center gap-3 py-2 text-sm">
                  <input type="checkbox" checked={!jaEntrou.has(chave(x))} onChange={() => alternarEntrou(x)} className="size-4 accent-[var(--color-destaque)]" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate">{x.descricao}</span>
                    <span className="text-xs text-apagado">
                      {x.data ? `dia ${dataCurta(x.data)}` : 'sem data'}
                      {x.origem === 'comissao' && <span className="text-alerta"> · comissão prevista</span>}
                    </span>
                  </span>
                  <span className="whitespace-nowrap">{dinheiro(x.valor)}</span>
                </label>
              </li>
            ))}
          </ul>
        </section>
      )}

      {contas.length > 0 && (
        <section>
          <p className="font-medium">Ainda falta pagar?</p>
          <p className="mb-2 text-xs text-apagado">Marque o que você já pagou (fica marcado como pago no app).</p>
          {vencidas > 0 && (
            <p className="mb-2 rounded-xl border border-alerta/40 bg-alerta/10 p-2.5 text-xs">
              {vencidas === 1 ? '1 conta já venceu' : `${vencidas} contas já venceram`} e não {vencidas === 1 ? 'está marcada' : 'estão marcadas'} como paga.
              Se já saiu do banco, marque: senão ela é descontada duas vezes.
            </p>
          )}
          <ul className="divide-y divide-borda/60 rounded-xl bg-painel-2/50 px-3">
            {contas.map((v) => (
              <li key={`${v.tipo}-${v.id}`} className="flex min-h-11 items-center gap-3 py-2 text-sm">
                <CaixaPago marcado={false} onChange={() => onPagar(v, true)} rotulo={`Marcar ${v.descricao} como paga`} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate">{v.descricao}</span>
                  <span className={`text-xs ${v.vencido ? 'text-alerta' : 'text-apagado'}`}>
                    {v.data ? (v.vencido ? `venceu ${dataCurta(v.data)}: já saiu da conta?` : `vence ${dataCurta(v.data)}`) : 'sem data'}
                  </span>
                </span>
                <span className="whitespace-nowrap">{dinheiro(v.valor)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="rounded-xl border border-borda p-3 text-sm">
        <Linha rotulo="Saldo informado" valor={dinheiro(totalSaldo)} />
        <Linha rotulo="+ Ainda vai entrar" valor={dinheiro(totalEntrar)} cor="text-positivo" />
        <Linha rotulo="− Ainda falta pagar" valor={dinheiro(totalPagar)} />
        <p className="mt-2 flex items-baseline justify-between border-t border-borda pt-2">
          <span className="font-medium">Deve sobrar no fim do mês</span>
          <span className={`text-xl font-bold ${previa >= 0 ? 'text-positivo' : 'text-negativo'}`}>{dinheiro(previa)}</span>
        </p>
      </div>

      {erro && <MensagemErro mensagem={erro} />}
      <Botao type="submit" carregando={salvando} className="w-full">Salvar conferência</Botao>
    </form>
  )
}
