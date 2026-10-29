// Rotas do app.
// - /convite/TOKEN funciona com ou sem login (é por onde gente nova entra);
// - sem sessão válida, só a tela de login;
// - logado mas sem casa (sem convite aceito), a tela "sem acesso".
import { useCallback, useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { DadosProvider } from './contexts/DadosContext'
import { api } from './lib/api'
import { Botao, Carregando, MensagemErro } from './components/ui'
import Layout from './components/Layout'
import Login from './pages/Login'
import Convite from './pages/Convite'
import Dashboard from './pages/Dashboard'
import Despesas from './pages/Despesas'
import Receitas from './pages/Receitas'
import Comissoes from './pages/Comissoes'
import Cartoes from './pages/Cartoes'
import Anotacoes from './pages/Anotacoes'
import Mais from './pages/Mais'
import Simulador from './pages/Simulador'
import Metas from './pages/Metas'
import Pessoas from './pages/Pessoas'
import Categorias from './pages/Categorias'
import Casa from './pages/Casa'

function Rotas() {
  const { sessao } = useAuth()
  const { pathname } = useLocation()
  if (sessao === undefined) return <Carregando />

  const convite = pathname.match(/^\/convite\/([^/]+)/)
  if (convite) return <Convite token={decodeURIComponent(convite[1])} />
  if (!sessao) return <Login />
  return <PortaoCasa />
}

// Descobre a casa do usuário antes de abrir o app
function PortaoCasa() {
  const { sair } = useAuth()
  const [eu, setEu] = useState(null)
  const [erro, setErro] = useState(null) // { status, mensagem }

  const carregarEu = useCallback(
    () => api.get('/eu').then((d) => {
      setEu(d)
      setErro(null)
    }).catch((e) => setErro({ status: e.status, mensagem: e.message })),
    [],
  )
  useEffect(() => {
    carregarEu()
  }, [carregarEu])

  if (erro?.status === 403) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center px-6">
        <img src="/icon.svg" alt="" className="mb-6 size-16" />
        <h1 className="text-2xl font-bold">Você ainda não tem acesso</h1>
        <p className="mt-2 mb-6 text-suave">
          Para usar o app é preciso um convite. Se você recebeu um link de convite, abra-o neste aparelho.
        </p>
        <Botao variante="secundario" onClick={sair}><LogOut className="size-4" /> Sair</Botao>
      </main>
    )
  }
  if (erro) return <div className="mx-auto max-w-sm p-6"><MensagemErro mensagem={erro.mensagem} tentarNovamente={carregarEu} /></div>
  if (!eu) return <Carregando />

  return (
    <DadosProvider eu={eu} recarregarEu={carregarEu}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="despesas" element={<Despesas />} />
          <Route path="receitas" element={<Receitas />} />
          <Route path="comissoes" element={<Comissoes />} />
          <Route path="cartoes" element={<Cartoes />} />
          <Route path="anotacoes" element={<Anotacoes />} />
          <Route path="metas" element={<Metas />} />
          <Route path="simulador" element={<Simulador />} />
          <Route path="pessoas" element={<Pessoas />} />
          <Route path="categorias" element={<Categorias />} />
          <Route path="casa" element={<Casa />} />
          <Route path="mais" element={<Mais />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </DadosProvider>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Rotas />
      </BrowserRouter>
    </AuthProvider>
  )
}
