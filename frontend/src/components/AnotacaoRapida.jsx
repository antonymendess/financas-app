// Campo para anotar em 1 toque: escreve e aperta Enter.
// Reconhece data, valor e tipo no texto e mostra o que entendeu antes de salvar.
import { useMemo, useState } from 'react'
import { CalendarDays, Loader2, Send } from 'lucide-react'
import { api } from '../lib/api'
import { data as formatarData, dinheiro } from '../lib/formato'
import { interpretarAnotacao } from '../lib/interpretar'
import { useDados } from '../contexts/DadosContext'

export default function AnotacaoRapida({ autoFocus = false }) {
  const { dadosMudaram, avisar } = useDados()
  const [texto, setTexto] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)
  const sugestao = useMemo(() => interpretarAnotacao(texto), [texto])

  const salvar = async (e) => {
    e.preventDefault()
    if (!texto.trim() || salvando) return
    setSalvando(true)
    setErro(null)
    try {
      await api.post('/anotacoes', {
        texto: texto.trim(),
        tipo: sugestao.tipo,
        data: sugestao.data,
        valor: sugestao.valor,
        pessoa: null,
        entra_no_saldo: false,
        concluida: false,
      })
      setTexto('')
      avisar('Anotado')
      dadosMudaram()
    } catch (e) {
      setErro(e.message)
    } finally {
      setSalvando(false)
    }
  }

  const temSugestao = texto.trim() && (sugestao.data || sugestao.valor || sugestao.tipo !== 'Lembrete')

  return (
    <form onSubmit={salvar}>
      <div className="flex items-center gap-2 rounded-2xl border border-borda bg-painel-2 p-1.5 pl-4 focus-within:border-alerta">
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Anotar algo… ex.: pagar João dia 20 R$ 50"
          className="min-h-10 flex-1 bg-transparent text-texto placeholder:text-apagado focus:outline-none"
          autoFocus={autoFocus}
          maxLength={300}
          enterKeyHint="send"
          aria-label="Nova anotação"
        />
        <button
          type="submit"
          disabled={!texto.trim() || salvando}
          className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-alerta text-fundo transition disabled:opacity-30"
          aria-label="Salvar anotação"
        >
          {salvando ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
        </button>
      </div>
      {temSugestao && (
        <p className="mt-1.5 flex flex-wrap items-center gap-1.5 pl-1 text-xs text-suave">
          Vou salvar como:
          {sugestao.tipo !== 'Lembrete' && <span className="rounded-full bg-painel-2 px-2 py-0.5">{sugestao.tipo}</span>}
          {sugestao.data && (
            <span className="inline-flex items-center gap-1 rounded-full bg-painel-2 px-2 py-0.5">
              <CalendarDays className="size-3" /> {formatarData(sugestao.data)}
            </span>
          )}
          {sugestao.valor && <span className="rounded-full bg-painel-2 px-2 py-0.5">{dinheiro(sugestao.valor)}</span>}
        </p>
      )}
      {erro && <p className="mt-1.5 pl-1 text-xs text-negativo">{erro}</p>}
    </form>
  )
}
