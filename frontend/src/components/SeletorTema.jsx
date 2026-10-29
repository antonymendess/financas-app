// Escolha do tema: claro, escuro ou igual ao do aparelho.
import { Monitor, Moon, Sun } from 'lucide-react'
import { useTema } from '../lib/tema'

const OPCOES = [
  { valor: 'claro', rotulo: 'Claro', Icone: Sun },
  { valor: 'escuro', rotulo: 'Escuro', Icone: Moon },
  { valor: 'sistema', rotulo: 'Sistema', Icone: Monitor },
]

export default function SeletorTema({ className = '' }) {
  const [tema, setTema] = useTema()
  return (
    <div className={`flex gap-1 rounded-xl bg-painel-2 p-1 ${className}`} role="radiogroup" aria-label="Tema">
      {OPCOES.map(({ valor, rotulo, Icone }) => (
        <button
          key={valor}
          type="button"
          role="radio"
          aria-checked={tema === valor}
          title={rotulo}
          onClick={() => setTema(valor)}
          className={`flex min-h-8 flex-1 items-center justify-center gap-1.5 rounded-lg text-xs font-medium transition ${
            tema === valor ? 'bg-painel text-texto shadow-sm' : 'text-apagado hover:text-texto'
          }`}
        >
          <Icone className="size-3.5" aria-hidden /> {rotulo}
        </button>
      ))}
    </div>
  )
}
