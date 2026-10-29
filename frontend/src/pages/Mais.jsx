// Menu "Mais": demais telas (mesmos grupos do menu do computador) e saída do app.
import { Link } from 'react-router-dom'
import { ChevronRight, LogOut } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { GRUPOS_MENU } from '../components/Layout'
import { Titulo } from '../components/ui'
import SeletorTema from '../components/SeletorTema'

// Já estão na barra inferior do celular
const NA_BARRA = ['/', '/despesas', '/comissoes']

export default function Mais() {
  const { sessao, sair } = useAuth()
  return (
    <div className="space-y-6">
      <Titulo>Mais</Titulo>
      {GRUPOS_MENU.map((grupo) => {
        const links = grupo.links.filter((l) => !NA_BARRA.includes(l.para))
        if (!links.length) return null
        return (
          <section key={grupo.titulo}>
            <p className="mb-2 px-1 text-[11px] font-medium tracking-wider text-apagado uppercase">{grupo.titulo}</p>
            <ul className="divide-y divide-borda overflow-hidden rounded-2xl border border-borda bg-painel">
              {links.map(({ para, rotulo, Icone }) => (
                <li key={para}>
                  <Link to={para} className="flex min-h-14 items-center gap-3 px-4 active:bg-painel-2">
                    <Icone className="size-[18px] text-suave" aria-hidden />
                    <span className="flex-1">{rotulo}</span>
                    <ChevronRight className="size-4 text-apagado" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
      <section>
        <p className="mb-2 px-1 text-[11px] font-medium tracking-wider text-apagado uppercase">Aparência</p>
        <SeletorTema className="border border-borda bg-painel" />
      </section>
      <button onClick={sair} className="flex min-h-14 w-full items-center gap-3 rounded-2xl border border-borda bg-painel px-4 text-negativo">
        <LogOut className="size-5" aria-hidden /> Sair
      </button>
      <p className="text-center text-xs text-apagado">Conectado como {sessao?.user?.email}</p>
    </div>
  )
}
