// Escolha da categoria com atalho para criar uma nova sem sair do formulário.
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../lib/api'
import { useDados } from '../contexts/DadosContext'
import { Selecao } from './ui'

export default function CampoCategoria({ rotulo = 'Categoria', vazio, value, onChange }) {
  const { opcoes, recarregarOpcoes, avisar } = useDados()
  const [criando, setCriando] = useState(false)
  const [nome, setNome] = useState('')
  const [salvando, setSalvando] = useState(false)

  const criar = async () => {
    if (!nome.trim()) return
    setSalvando(true)
    try {
      const nova = await api.post('/categorias', { nome })
      await recarregarOpcoes()
      onChange(String(nova.id))
      avisar(`Categoria "${nova.nome}" criada`)
      setCriando(false)
      setNome('')
    } catch (e) {
      avisar(e.message)
    }
    setSalvando(false)
  }

  if (criando) {
    return (
      <div className="min-w-0">
        <span className="mb-1 block text-sm text-suave">Nova categoria</span>
        <div className="flex gap-2">
          <input
            autoFocus
            value={nome}
            maxLength={60}
            onChange={(e) => setNome(e.target.value)}
            // Enter cria a categoria sem enviar o formulário de fora
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                criar()
              }
              if (e.key === 'Escape') setCriando(false)
            }}
            placeholder="Ex.: Mercado"
            className="min-h-11 w-full min-w-0 rounded-xl border border-apagado bg-painel px-3 text-texto focus:outline-none"
          />
          <button type="button" onClick={criar} disabled={salvando} className="rounded-xl bg-destaque px-3 text-sm font-medium text-sobre-destaque disabled:opacity-50">
            Criar
          </button>
        </div>
        <button type="button" onClick={() => setCriando(false)} className="mt-1 text-xs text-apagado">cancelar</button>
      </div>
    )
  }

  return (
    <div className="min-w-0">
      <Selecao rotulo={rotulo} vazio={vazio} opcoes={opcoes.categorias} value={value} onChange={(e) => onChange(e.target.value)} />
      <button type="button" onClick={() => setCriando(true)} className="mt-1 flex items-center gap-1 text-xs text-saldo">
        <Plus className="size-3" aria-hidden /> nova categoria
      </button>
    </div>
  )
}
