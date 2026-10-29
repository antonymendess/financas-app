// Navegação entre meses com setas anterior/próximo.
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { nomeMes } from '../lib/formato'

export function mesAtual() {
  const h = new Date()
  return { ano: h.getFullYear(), mes: h.getMonth() + 1 }
}

export function somarMes({ ano, mes }, n) {
  const indice = ano * 12 + (mes - 1) + n
  return { ano: Math.floor(indice / 12), mes: (indice % 12) + 1 }
}

export default function SeletorMes({ valor, onChange }) {
  const atual = mesAtual()
  const ehAtual = valor.ano === atual.ano && valor.mes === atual.mes
  return (
    <div className="flex items-center justify-between rounded-2xl border border-borda bg-painel px-1 py-1">
      <button className="p-3 text-suave" onClick={() => onChange(somarMes(valor, -1))} aria-label="Mês anterior">
        <ChevronLeft className="size-5" />
      </button>
      <button className="text-center" onClick={() => onChange(atual)} title="Voltar para o mês atual">
        <span className="block font-semibold">{nomeMes(valor.ano, valor.mes)}</span>
        {!ehAtual && <span className="block text-xs text-saldo">voltar para hoje</span>}
      </button>
      <button className="p-3 text-suave" onClick={() => onChange(somarMes(valor, 1))} aria-label="Próximo mês">
        <ChevronRight className="size-5" />
      </button>
    </div>
  )
}
