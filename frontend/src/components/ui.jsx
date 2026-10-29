// Componentes visuais reutilizados em todas as telas.
import { useEffect } from 'react'
import { AlertTriangle, Loader2, X } from 'lucide-react'

export function Carregando({ texto = 'Carregando...' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-suave" role="status">
      <Loader2 className="size-5 animate-spin" aria-hidden />
      <span>{texto}</span>
    </div>
  )
}

export function MensagemErro({ mensagem, tentarNovamente }) {
  return (
    <div className="my-6 rounded-2xl border border-negativo/30 bg-negativo/5 p-4 text-sm" role="alert">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-negativo" aria-hidden />
        <p>{mensagem}</p>
      </div>
      {tentarNovamente && (
        <button onClick={tentarNovamente} className="mt-3 font-medium underline underline-offset-4">
          Tentar novamente
        </button>
      )}
    </div>
  )
}

export function Vazio({ children }) {
  return <p className="py-12 text-center text-sm text-apagado">{children}</p>
}

export function Cartao({ titulo, acao, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-borda bg-painel p-5 sm:p-6 ${className}`}>
      {(titulo || acao) && (
        <div className="mb-5 flex items-center justify-between gap-3">
          {titulo && <h2 className="text-[15px] font-semibold tracking-tight text-texto">{titulo}</h2>}
          {acao}
        </div>
      )}
      {children}
    </section>
  )
}

export function Botao({ variante = 'primario', className = '', carregando, children, ...props }) {
  const estilos = {
    primario: 'bg-destaque text-sobre-destaque hover:opacity-85',
    secundario: 'bg-painel text-texto border border-borda hover:bg-painel-2',
    perigo: 'bg-transparent text-negativo border border-negativo/40 hover:bg-negativo/5',
    fantasma: 'bg-transparent text-suave hover:text-texto',
  }
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-medium transition disabled:opacity-50 ${estilos[variante]} ${className}`}
      disabled={carregando || props.disabled}
      {...props}
    >
      {carregando && <Loader2 className="size-4 animate-spin" aria-hidden />}
      {children}
    </button>
  )
}

const classeCampo =
  'w-full min-w-0 min-h-11 rounded-xl border border-borda bg-painel px-3 text-texto placeholder:text-apagado transition focus:border-apagado focus:outline-none focus:ring-4 focus:ring-destaque/5'

export function Campo({ rotulo, dica, className = '', ...props }) {
  return (
    <label className={`block min-w-0 ${className}`}>
      {rotulo && <span className="mb-1 block text-sm text-suave">{rotulo}</span>}
      <input className={classeCampo} {...props} />
      {dica && <span className="mt-1 block text-xs text-apagado">{dica}</span>}
    </label>
  )
}

// Campo de dinheiro: abre o teclado numérico com vírgula no celular
export function CampoValor({ rotulo, className = '', ...props }) {
  return (
    <label className={`block min-w-0 ${className}`}>
      {rotulo && <span className="mb-1 block text-sm text-suave">{rotulo}</span>}
      <div className="relative">
        <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-apagado">R$</span>
        <input
          className={`${classeCampo} pl-10`}
          inputMode="decimal"
          autoComplete="off"
          placeholder="0,00"
          {...props}
        />
      </div>
    </label>
  )
}

export function Selecao({ rotulo, opcoes, vazio, className = '', ...props }) {
  return (
    <label className={`block min-w-0 ${className}`}>
      {rotulo && <span className="mb-1 block text-sm text-suave">{rotulo}</span>}
      <select className={classeCampo} {...props}>
        {vazio !== undefined && <option value="">{vazio}</option>}
        {opcoes.map((o) => (
          <option key={o.id ?? o} value={o.id ?? o}>
            {o.nome ?? o}
          </option>
        ))}
      </select>
    </label>
  )
}

export function AreaTexto({ rotulo, className = '', ...props }) {
  return (
    <label className={`block min-w-0 ${className}`}>
      {rotulo && <span className="mb-1 block text-sm text-suave">{rotulo}</span>}
      <textarea className={`${classeCampo} min-h-24 py-2`} {...props} />
    </label>
  )
}

export function Interruptor({ rotulo, dica, checked, onChange }) {
  return (
    <label className="flex min-h-11 cursor-pointer items-center justify-between gap-3">
      <span>
        <span className="block text-sm">{rotulo}</span>
        {dica && <span className="block text-xs text-apagado">{dica}</span>}
      </span>
      <input
        type="checkbox"
        className="peer sr-only"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="relative h-6 w-11 shrink-0 rounded-full bg-borda transition peer-checked:bg-destaque peer-focus-visible:ring-2 peer-focus-visible:ring-destaque/30 after:absolute after:top-0.5 after:left-0.5 after:size-5 after:rounded-full after:bg-painel after:shadow-sm after:transition peer-checked:after:translate-x-5" />
    </label>
  )
}

// Botões de escolha rápida (ex.: número de parcelas, tipo)
export function Opcoes({ rotulo, opcoes, valor, onChange }) {
  return (
    <div>
      {rotulo && <span className="mb-1 block text-sm text-suave">{rotulo}</span>}
      <div className="flex flex-wrap gap-2">
        {opcoes.map((o) => {
          const v = o.valor ?? o
          const ativo = String(v) === String(valor)
          return (
            <button
              type="button"
              key={v}
              onClick={() => onChange(v)}
              aria-pressed={ativo}
              className={`min-h-10 rounded-xl border px-3.5 text-sm transition ${
                ativo ? 'border-destaque bg-destaque font-medium text-sobre-destaque' : 'border-borda bg-painel text-suave hover:text-texto'
              }`}
            >
              {o.rotulo ?? o}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// Janela que sobe de baixo no celular e fica centralizada no computador
export function Modal({ aberto, titulo, onFechar, children }) {
  useEffect(() => {
    if (!aberto) return
    const fecharComEsc = (e) => e.key === 'Escape' && onFechar()
    document.addEventListener('keydown', fecharComEsc)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', fecharComEsc)
      document.body.style.overflow = ''
    }
  }, [aberto, onFechar])

  if (!aberto) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center" role="dialog" aria-modal="true" aria-label={titulo}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" onClick={onFechar} />
      <div className="relative max-h-[92dvh] w-full overflow-x-hidden overflow-y-auto rounded-t-3xl border border-borda bg-painel p-6 pb-[calc(1.5rem+env(safe-area-inset-bottom))] shadow-2xl sm:max-w-lg sm:rounded-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight">{titulo}</h2>
          <button onClick={onFechar} className="-mr-2 p-2 text-suave" aria-label="Fechar">
            <X className="size-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function BarraProgresso({ atual, total, cor = 'bg-destaque' }) {
  const pct = total ? Math.min(100, Math.round((atual / total) * 100)) : 0
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-borda" role="progressbar" aria-valuenow={atual} aria-valuemax={total}>
      <div className={`h-full rounded-full ${cor}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export function Etiqueta({ children, cor = 'text-suave border-borda' }) {
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium ${cor}`}>
      {children}
    </span>
  )
}

export function Titulo({ children, acao }) {
  return (
    <div className="mb-2 flex items-center justify-between gap-3 pt-1 lg:mb-4">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-[28px]">{children}</h1>
      {acao}
    </div>
  )
}

// Botão só com ícone (editar, excluir...) com área de toque confortável
export function BotaoIcone({ rotulo, children, className = '', ...props }) {
  return (
    <button
      type="button"
      aria-label={rotulo}
      title={rotulo}
      className={`inline-flex size-10 shrink-0 items-center justify-center rounded-xl text-apagado transition hover:bg-painel-2 hover:text-texto ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

// Caixa redonda de "pago/concluído": verde e com ✓ quando marcada
export function CaixaPago({ marcado, onChange, rotulo, carregando }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={marcado}
      aria-label={rotulo}
      title={rotulo}
      disabled={carregando}
      onClick={(e) => {
        e.stopPropagation()
        onChange(!marcado)
      }}
      className={`inline-flex size-6 shrink-0 items-center justify-center rounded-full border-[1.5px] transition disabled:opacity-50 ${
        marcado ? 'border-positivo bg-positivo text-white' : 'border-apagado/50 hover:border-suave'
      }`}
    >
      {marcado && (
        <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="3.5" aria-hidden>
          <path d="M5 12.5l4.5 4.5L19 7.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </button>
  )
}

export function Abas({ abas, ativa, onChange }) {
  return (
    <div className="flex gap-1 overflow-x-auto rounded-xl bg-painel-2 p-1" role="tablist">
      {abas.map((a) => (
        <button
          key={a.valor}
          role="tab"
          aria-selected={ativa === a.valor}
          onClick={() => onChange(a.valor)}
          className={`min-h-9 flex-1 whitespace-nowrap rounded-lg px-3 text-sm font-medium transition ${
            ativa === a.valor ? 'bg-painel text-texto shadow-sm' : 'text-apagado hover:text-texto'
          }`}
        >
          {a.rotulo}
        </button>
      ))}
    </div>
  )
}

// Indicador numérico pequeno (usado em resumos)
export function Indicador({ rotulo, valor, detalhe, cor = '', onClick }) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag
      onClick={onClick}
      className={`rounded-2xl border border-borda bg-painel p-5 text-left sm:p-5 ${onClick ? 'transition hover:border-apagado/50 active:scale-[0.99]' : ''}`}
    >
      <p className="text-xs font-medium text-suave">{rotulo}</p>
      <p className={`mt-2 text-lg font-semibold tracking-tight sm:text-xl ${cor}`}>{valor}</p>
      {detalhe && <p className="mt-0.5 text-xs text-apagado">{detalhe}</p>}
    </Tag>
  )
}
