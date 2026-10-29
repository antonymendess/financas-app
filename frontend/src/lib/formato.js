// Formatação em português do Brasil: R$, dd/mm/aaaa e nomes de meses.

const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const compacto = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })

export const MESES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]

export function dinheiro(valor) {
  return moeda.format(Number(valor) || 0)
}

// Eixo dos gráficos: "4,5 mil" (o título do gráfico já diz que é R$)
export function numeroCurto(valor) {
  return compacto.format(Number(valor) || 0)
}

// Lê "AAAA-MM-DD" sem passar por fuso horário (evita a data "voltar um dia")
export function lerData(iso) {
  if (!iso) return null
  const [a, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(a, m - 1, d)
}

export function data(iso) {
  if (!iso) return ''
  const [a, m, d] = iso.slice(0, 10).split('-')
  return `${d}/${m}/${a}`
}

export function dataCurta(iso) {
  if (!iso) return ''
  const [, m, d] = iso.slice(0, 10).split('-')
  return `${d}/${m}`
}

// Data de hoje no formato do input type="date"
export function hojeIso() {
  const h = new Date()
  return paraIso(h)
}

export function paraIso(dt) {
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const d = String(dt.getDate()).padStart(2, '0')
  return `${dt.getFullYear()}-${m}-${d}`
}

// "2026-10" -> "out/2026"
export function mesAno(texto) {
  if (!texto) return ''
  const [a, m] = texto.split('-').map(Number)
  return `${MESES[m - 1].slice(0, 3).toLowerCase()}/${a}`
}

export function nomeMes(ano, mes) {
  return `${MESES[mes - 1]} ${ano}`
}

export function mesCurto(ano, mes) {
  return `${MESES[mes - 1].slice(0, 3)}/${String(ano).slice(2)}`
}

// Diferença em dias entre uma data ISO e hoje (negativo = já passou)
export function diasAte(iso) {
  const alvo = lerData(iso)
  if (!alvo) return null
  const hoje = new Date()
  hoje.setHours(0, 0, 0, 0)
  return Math.round((alvo - hoje) / 86400000)
}

// Aceita "12,50", "1.234,56" ou "12.5" digitados no celular
export function lerValor(texto) {
  if (texto === null || texto === undefined || texto === '') return null
  let limpo = String(texto).replace(/[R$\s]/g, '')
  if (limpo.includes(',')) limpo = limpo.replace(/\./g, '').replace(',', '.')
  const numero = Number(limpo)
  return Number.isFinite(numero) ? Math.round(numero * 100) / 100 : NaN
}

// Valor numérico -> texto para preencher um campo ao editar ("12,50")
export function valorParaCampo(valor) {
  if (valor === null || valor === undefined) return ''
  return Number(valor).toFixed(2).replace('.', ',')
}
