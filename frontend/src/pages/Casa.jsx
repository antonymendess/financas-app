// Minha casa: nome, quem faz parte e convites (copiar link ou mandar pelo WhatsApp).
// O administrador também convida clientes novos daqui.
import { useState } from 'react'
import { Copy, Crown, MessageCircle, Send, Trash2, UserPlus, X } from 'lucide-react'
import { api } from '../lib/api'
import { data } from '../lib/formato'
import { useCarregar } from '../hooks/useCarregar'
import { useDados } from '../contexts/DadosContext'
import { Botao, BotaoIcone, Campo, Cartao, Etiqueta, MensagemErro, Titulo } from '../components/ui'

const linkDo = (convite) => `${window.location.origin}/convite/${convite.token}`

function mensagemWhatsApp(convite) {
  const texto = convite.tipo === 'membro'
    ? `Oi! Te convidei para organizarmos nossas finanças juntos no Controle Financeiro. Crie sua conta com o e-mail ${convite.email} por este link: ${linkDo(convite)}`
    : `Oi! Aqui está seu convite para o Controle Financeiro. Crie sua conta com o e-mail ${convite.email} por este link: ${linkDo(convite)}`
  return `https://wa.me/?text=${encodeURIComponent(texto)}`
}

export default function Casa() {
  const { eu, recarregarEu, versao, dadosMudaram, avisar, confirmar } = useDados()
  const convites = useCarregar(() => api.get('/casa/convites'), [versao], '/casa/convites')
  const ehDono = eu?.papel === 'dono'

  const pendentes = (convites.dados ?? []).filter((c) => !c.aceito_em && new Date(c.expira_em) > new Date())
  const vagas = (eu?.limite_membros ?? 2) - (eu?.membros.length ?? 0) - pendentes.filter((c) => c.tipo === 'membro').length

  const remover = async (m) => {
    if (!(await confirmar(`Remover ${m.email} da casa? A pessoa perde o acesso aos dados.`, 'Remover'))) return
    try {
      await api.delete(`/casa/membros/${m.id}`)
      avisar('Pessoa removida')
      recarregarEu()
    } catch (e) {
      avisar(e.message)
    }
  }

  const cancelar = async (c) => {
    if (!(await confirmar(`Cancelar o convite de ${c.email}? O link deixa de funcionar.`, 'Cancelar convite'))) return
    try {
      await api.delete(`/casa/convites/${c.id}`)
      avisar('Convite cancelado')
      dadosMudaram()
    } catch (e) {
      avisar(e.message)
    }
  }

  if (!eu) return null
  return (
    <div className="space-y-6">
      <Titulo>Minha casa</Titulo>

      <NomeCasa eu={eu} ehDono={ehDono} onSalvo={recarregarEu} />

      <Cartao titulo={`Quem faz parte (${eu.membros.length} de ${eu.limite_membros})`}>
        <ul className="divide-y divide-borda/60">
          {eu.membros.map((m) => (
            <li key={m.id} className="flex min-h-12 items-center gap-2">
              <span className="min-w-0 flex-1 truncate">{m.email}{m.email === eu.email && <span className="text-apagado"> (você)</span>}</span>
              {m.papel === 'dono' ? <Etiqueta cor="text-alerta border-alerta/40"><Crown className="size-3" aria-hidden /> Dono</Etiqueta> : <Etiqueta>Membro</Etiqueta>}
              {ehDono && m.papel !== 'dono' && (
                <BotaoIcone rotulo={`Remover ${m.email}`} onClick={() => remover(m)} className="hover:text-negativo"><Trash2 className="size-4" /></BotaoIcone>
              )}
            </li>
          ))}
        </ul>
        {ehDono && vagas > 0 && <FormConvite rotulo="Convidar alguém para a casa" dica="Ex.: seu cônjuge. Vocês vão ver as mesmas finanças." caminho="/casa/convites" onCriado={dadosMudaram} />}
        {ehDono && vagas <= 0 && <p className="mt-3 text-xs text-apagado">A casa já está completa (ou tem convite pendente). Cancele um convite ou remova alguém para convidar outra pessoa.</p>}
      </Cartao>

      {eu.admin && (
        <Cartao titulo="Convidar cliente novo">
          <p className="mb-3 text-sm text-suave">A pessoa ganha uma casa própria, com dados separados dos seus. Só você (administrador) vê esta área.</p>
          <FormConvite rotulo="E-mail do cliente" caminho="/admin/convites" comNomeCasa onCriado={dadosMudaram} />
        </Cartao>
      )}

      <Cartao titulo="Convites">
        {convites.erro && <MensagemErro mensagem={convites.erro} />}
        {convites.dados?.length === 0 && <p className="text-sm text-apagado">Nenhum convite ainda.</p>}
        <ul className="space-y-3">
          {(convites.dados ?? []).map((c) => {
            const pendente = !c.aceito_em && new Date(c.expira_em) > new Date()
            return (
              <li key={c.id} className="rounded-xl border border-borda bg-painel-2/50 p-3">
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{c.email}</p>
                    <p className="text-xs text-apagado">
                      {c.tipo === 'nova_casa' ? `Cliente novo${c.nome_casa ? ` · ${c.nome_casa}` : ''}` : 'Para esta casa'}
                      {' · '}
                      {c.aceito_em ? <span className="text-positivo">aceito em {data(c.aceito_em)}</span> : pendente ? `vale até ${data(c.expira_em)}` : <span className="text-negativo">expirado</span>}
                    </p>
                  </div>
                  {pendente && <BotaoIcone rotulo="Cancelar convite" onClick={() => cancelar(c)} className="-mt-1 -mr-1 hover:text-negativo"><X className="size-4" /></BotaoIcone>}
                </div>
                {pendente && <AcoesLink convite={c} />}
              </li>
            )
          })}
        </ul>
      </Cartao>
    </div>
  )
}

function NomeCasa({ eu, ehDono, onSalvo }) {
  const { avisar } = useDados()
  const [nome, setNome] = useState(eu.casa_nome)
  const [salvando, setSalvando] = useState(false)
  const salvar = async (e) => {
    e.preventDefault()
    setSalvando(true)
    try {
      await api.put('/casa', { nome })
      avisar('Nome salvo')
      onSalvo()
    } catch (e) {
      avisar(e.message)
    }
    setSalvando(false)
  }
  if (!ehDono) return <p className="text-lg font-semibold">{eu.casa_nome}</p>
  return (
    <form onSubmit={salvar} className="flex items-end gap-2">
      <Campo rotulo="Nome da casa" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={80} required className="flex-1" />
      {nome !== eu.casa_nome && <Botao type="submit" carregando={salvando}>Salvar</Botao>}
    </form>
  )
}

function FormConvite({ rotulo, dica, caminho, comNomeCasa = false, onCriado }) {
  const { avisar } = useDados()
  const [email, setEmail] = useState('')
  const [nomeCasa, setNomeCasa] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)
  const [criado, setCriado] = useState(null)

  const enviar = async (e) => {
    e.preventDefault()
    setSalvando(true)
    setErro(null)
    try {
      const convite = await api.post(caminho, { email: email.trim(), ...(comNomeCasa && { nome_casa: nomeCasa.trim() || null }) })
      setCriado(convite)
      setEmail('')
      setNomeCasa('')
      avisar('Convite criado: agora envie o link')
      onCriado()
    } catch (e) {
      setErro(e.message)
    }
    setSalvando(false)
  }

  return (
    <div className="mt-3 space-y-3">
      <form onSubmit={enviar} className="space-y-3">
        <div className={`grid gap-2 ${comNomeCasa ? 'sm:grid-cols-2' : ''}`}>
          <Campo rotulo={rotulo} type="email" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="pessoa@email.com" dica={dica} />
          {comNomeCasa && <Campo rotulo="Nome da casa (opcional)" value={nomeCasa} onChange={(e) => setNomeCasa(e.target.value)} maxLength={80} placeholder="Ex.: Família Silva" />}
        </div>
        {erro && <MensagemErro mensagem={erro} />}
        <Botao type="submit" carregando={salvando} variante="secundario"><UserPlus className="size-4" /> Criar convite</Botao>
      </form>
      {criado && (
        <div className="rounded-xl border border-positivo/40 bg-positivo/5 p-3">
          <p className="text-sm">Convite para <strong>{criado.email}</strong> criado. Envie o link (vale 7 dias):</p>
          <AcoesLink convite={criado} />
        </div>
      )}
    </div>
  )
}

function AcoesLink({ convite }) {
  const { avisar } = useDados()
  const link = linkDo(convite)
  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(link)
      avisar('Link copiado')
    } catch {
      avisar('Não deu para copiar: selecione o link e copie')
    }
  }
  const compartilhar = async () => {
    try {
      await navigator.share({ title: 'Convite', text: 'Seu convite para o Controle Financeiro', url: link })
    } catch {
      /* cancelado pelo usuário */
    }
  }
  return (
    <div className="mt-2 space-y-2">
      <input readOnly value={link} onFocus={(e) => e.target.select()} className="w-full min-w-0 truncate rounded-lg border border-borda bg-painel px-2 py-1.5 text-xs text-suave" aria-label="Link do convite" />
      <div className="flex flex-wrap gap-2">
        <Botao variante="secundario" onClick={copiar} className="min-h-9 px-3 text-sm"><Copy className="size-4" /> Copiar link</Botao>
        <a href={mensagemWhatsApp(convite)} target="_blank" rel="noreferrer" className="inline-flex min-h-9 items-center gap-2 rounded-xl bg-[#25D366] px-3 text-sm font-medium text-black">
          <MessageCircle className="size-4" aria-hidden /> WhatsApp
        </a>
        {typeof navigator !== 'undefined' && navigator.share && (
          <Botao variante="fantasma" onClick={compartilhar} className="min-h-9 px-3 text-sm"><Send className="size-4" /> Outros</Botao>
        )}
      </div>
    </div>
  )
}
