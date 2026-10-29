// Uma anotação na lista: concluir, abrir para editar e excluir em 1 toque.
import { Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { data, diasAte, dinheiro } from '../lib/formato'
import { useDados } from '../contexts/DadosContext'
import { BotaoIcone, CaixaPago } from './ui'

const COR_TIPO = { 'A pagar': 'text-despesa', 'A receber': 'text-positivo', Lembrete: 'text-apagado' }

export default function ItemAnotacao({ anotacao: a, onEditar, compacto = false }) {
  const { dadosMudaram, avisar, excluir } = useDados()
  const dias = a.data ? diasAte(a.data) : null
  const vencida = !a.concluida && dias !== null && dias < 0
  const emBreve = !a.concluida && dias !== null && dias >= 0 && dias <= 7

  const alternar = async (concluida) => {
    try {
      await api.patch(`/anotacoes/${a.id}/concluir`, { concluida })
      avisar(concluida ? 'Concluída' : 'Reaberta')
      dadosMudaram()
    } catch (e) {
      avisar(e.message)
    }
  }

  return (
    <li
      className={`group flex items-start gap-3 rounded-xl px-2 py-2 transition ${
        vencida ? 'bg-negativo/10 ring-1 ring-negativo/40' : 'hover:bg-painel-2'
      }`}
    >
      <div className="pt-0.5">
        <CaixaPago marcado={a.concluida} onChange={alternar} rotulo={a.concluida ? 'Reabrir' : 'Concluir'} />
      </div>
      <button onClick={() => onEditar?.(a)} className="min-w-0 flex-1 text-left">
        <p className={`break-words ${compacto ? 'text-sm' : ''} ${a.concluida ? 'text-apagado line-through' : ''}`}>{a.texto}</p>
        {(a.data || a.valor || a.pessoa || a.tipo !== 'Lembrete') && (
          <p className="mt-0.5 flex flex-wrap gap-x-2 text-xs text-apagado">
            {a.tipo !== 'Lembrete' && <span className={COR_TIPO[a.tipo]}>{a.tipo}</span>}
            {a.data && (
              <span className={vencida ? 'font-medium text-negativo' : emBreve ? 'text-alerta' : ''}>
                {vencida ? `Venceu ${data(a.data)}` : dias === 0 ? 'Hoje' : dias === 1 ? 'Amanhã' : data(a.data)}
              </span>
            )}
            {a.valor && <span>{dinheiro(a.valor)}</span>}
            {a.pessoa && <span>{a.pessoa}</span>}
            {a.entra_no_saldo && <span>no saldo</span>}
          </p>
        )}
      </button>
      <BotaoIcone rotulo="Excluir anotação" onClick={() => excluir(`/anotacoes/${a.id}`, 'esta anotação')} className="-my-1 hover:text-negativo">
        <Trash2 className="size-4" />
      </BotaoIcone>
    </li>
  )
}
