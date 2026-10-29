// Estrutura das telas:
// - computador: menu lateral fixo + conteúdo largo
// - celular: barra inferior fixa com o botão "+" no meio
import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  ArrowUpCircle, Briefcase, Calculator, CreditCard, Home, LayoutGrid, LogOut, PiggyBank, Plus, Receipt, StickyNote, Tags, UserPlus, Users, Wallet,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useDados } from '../contexts/DadosContext'
import { Modal } from './ui'
import SeletorTema from './SeletorTema'
import FormGastoCartao from './FormGastoCartao'
import FormAnotacao from './FormAnotacao'
import { FormDespesa } from '../pages/Despesas'
import { FormReceita } from '../pages/Receitas'
import { FormComissao } from '../pages/Comissoes'

// Menu agrupado por assunto (a tela "Mais" do celular usa os mesmos grupos)
export const GRUPOS_MENU = [
  {
    titulo: 'Dia a dia',
    links: [
      { para: '/', rotulo: 'Início', Icone: Home },
      { para: '/despesas', rotulo: 'Despesas', Icone: Receipt },
      { para: '/cartoes', rotulo: 'Cartões', Icone: CreditCard },
      { para: '/receitas', rotulo: 'Receitas', Icone: ArrowUpCircle },
    ],
  },
  {
    titulo: 'Ganhos e planos',
    links: [
      { para: '/comissoes', rotulo: 'Comissões', Icone: Wallet },
      { para: '/metas', rotulo: 'Metas', Icone: PiggyBank },
      { para: '/simulador', rotulo: 'Simulador', Icone: Calculator },
    ],
  },
  {
    titulo: 'Organizar',
    links: [
      { para: '/anotacoes', rotulo: 'Anotações', Icone: StickyNote },
      { para: '/pessoas', rotulo: 'Pessoas da casa', Icone: Users },
      { para: '/categorias', rotulo: 'Categorias', Icone: Tags },
      { para: '/casa', rotulo: 'Minha casa e convites', Icone: UserPlus },
    ],
  },
]

const NAV_CELULAR = [
  { para: '/', rotulo: 'Início', Icone: Home },
  { para: '/despesas', rotulo: 'Despesas', Icone: Receipt },
  null, // espaço do botão "+"
  { para: '/comissoes', rotulo: 'Comissões', Icone: Wallet },
  { para: '/mais', rotulo: 'Mais', Icone: LayoutGrid, ativoEm: ['/mais', '/receitas', '/cartoes', '/anotacoes', '/metas', '/simulador', '/pessoas', '/categorias', '/casa'] },
]

// O que dá para criar pelo botão "+"
const RAPIDOS = [
  { chave: 'gasto', rotulo: 'Gasto no cartão', Icone: CreditCard, cor: 'text-suave' },
  { chave: 'anotacao', rotulo: 'Anotação', Icone: StickyNote, cor: 'text-suave' },
  { chave: 'despesa', rotulo: 'Conta / despesa', Icone: Receipt, cor: 'text-suave' },
  { chave: 'receita', rotulo: 'Receita', Icone: ArrowUpCircle, cor: 'text-suave' },
  { chave: 'comissao', rotulo: 'Comissão', Icone: Briefcase, cor: 'text-suave' },
]

export default function Layout() {
  const [rapido, setRapido] = useState(null) // null | 'escolha' | chave de RAPIDOS
  const { pathname } = useLocation()
  const { sessao, sair } = useAuth()
  const { eu } = useDados()
  const fechar = () => setRapido(null)
  const titulo = RAPIDOS.find((r) => r.chave === rapido)?.rotulo

  return (
    <div className="min-h-dvh">
      {/* ---------- Menu lateral (computador) ---------- */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-borda bg-fundo px-4 py-6 lg:flex">
        <div className="mb-8 flex items-center gap-2.5 px-2">
          <img src="/icon.svg" alt="" className="size-7" />
          <span className="text-[15px] font-semibold tracking-tight">Finanças</span>
        </div>
        <button
          onClick={() => setRapido('escolha')}
          className="mb-8 flex min-h-10 items-center justify-center gap-2 rounded-xl bg-destaque text-sm font-medium text-sobre-destaque transition hover:opacity-85"
        >
          <Plus className="size-4" /> Novo lançamento
        </button>
        <nav className="flex flex-1 flex-col gap-6 overflow-y-auto [scrollbar-width:thin]" aria-label="Menu principal">
          {GRUPOS_MENU.map((grupo) => (
            <div key={grupo.titulo}>
              <p className="mb-1.5 px-3 text-[11px] font-medium tracking-wider text-apagado uppercase">{grupo.titulo}</p>
              <div className="flex flex-col gap-0.5">
                {grupo.links.map(({ para, rotulo, Icone }) => (
                  <NavLink
                    key={para}
                    to={para}
                    end={para === '/'}
                    className={({ isActive }) =>
                      `flex min-h-9 items-center gap-3 rounded-lg px-3 text-sm transition ${
                        isActive ? 'bg-painel-2 font-medium text-texto' : 'text-suave hover:bg-painel-2/60 hover:text-texto'
                      }`
                    }
                  >
                    <Icone className="size-4" aria-hidden /> {rotulo}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="space-y-3 border-t border-borda pt-4">
          <SeletorTema />
          <div>
          {eu && <p className="truncate px-2 text-sm font-medium">{eu.casa_nome}</p>}
          <p className="truncate px-2 text-xs text-apagado">{sessao?.user?.email}</p>
          </div>
          <button onClick={sair} className="flex min-h-9 w-full items-center gap-3 rounded-lg px-3 text-sm text-suave hover:bg-painel-2 hover:text-negativo">
            <LogOut className="size-4" /> Sair
          </button>
        </div>
      </aside>

      {/* ---------- Conteúdo ---------- */}
      <main className="pb-seguro px-4 pt-[calc(1.25rem+env(safe-area-inset-top))] sm:px-6 lg:pb-16 lg:pl-[calc(16rem+2rem)] lg:pr-8 lg:pt-8 2xl:pl-[calc(16rem+3rem)] 2xl:pr-12">
        {/* No computador ocupa a tela toda; só centraliza em monitores muito largos */}
        <div className="mx-auto max-w-[2000px]">
          <Outlet />
        </div>
      </main>

      {/* ---------- Barra inferior (celular) ---------- */}
      <nav
        className="fixed inset-x-0 bottom-0 z-40 border-t border-borda bg-fundo/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
        aria-label="Navegação principal"
      >
        <div className="mx-auto grid max-w-lg grid-cols-5">
          {NAV_CELULAR.map((item) =>
            item === null ? (
              <div key="rapido" className="flex justify-center">
                <button
                  onClick={() => setRapido('escolha')}
                  className="-mt-4 flex size-13 items-center justify-center rounded-full bg-destaque text-sobre-destaque shadow-lg shadow-black/20 active:scale-95"
                  aria-label="Novo lançamento"
                >
                  <Plus className="size-6" />
                </button>
              </div>
            ) : (
              <NavLink
                key={item.para}
                to={item.para}
                end={item.para === '/'}
                className={({ isActive }) => {
                  const ativo = isActive || item.ativoEm?.includes(pathname)
                  return `flex min-h-16 flex-col items-center justify-center gap-1 text-[11px] ${ativo ? 'font-medium text-texto' : 'text-apagado'}`
                }}
              >
                <item.Icone className="size-5" aria-hidden />
                {item.rotulo}
              </NavLink>
            ),
          )}
        </div>
      </nav>

      {/* ---------- Lançamento rápido ---------- */}
      <Modal aberto={rapido === 'escolha'} titulo="O que você quer lançar?" onFechar={fechar}>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {RAPIDOS.map(({ chave, rotulo, Icone, cor }) => (
            <button
              key={chave}
              onClick={() => setRapido(chave)}
              className="flex flex-col items-center gap-2.5 rounded-2xl border border-borda bg-painel p-5 transition hover:border-apagado/50 hover:bg-painel-2 active:scale-95"
            >
              <Icone className={`size-6 ${cor}`} strokeWidth={1.75} aria-hidden />
              <span className="text-sm font-medium">{rotulo}</span>
            </button>
          ))}
        </div>
      </Modal>
      <Modal aberto={rapido !== null && rapido !== 'escolha'} titulo={titulo} onFechar={fechar}>
        {rapido === 'gasto' && <FormGastoCartao onSalvo={fechar} />}
        {rapido === 'anotacao' && <FormAnotacao onSalvo={fechar} />}
        {rapido === 'despesa' && <FormDespesa onFechar={fechar} />}
        {rapido === 'receita' && <FormReceita onFechar={fechar} />}
        {rapido === 'comissao' && <FormComissao onFechar={fechar} />}
      </Modal>
    </div>
  )
}
