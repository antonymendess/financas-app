// Lê uma anotação escrita livremente e sugere data, valor e tipo.
// Ex.: "pagar João dia 20 R$ 50" -> { tipo: 'A pagar', data: '2026-10-20', valor: 50 }
import { paraIso } from './formato'

function dataDoDia(dia, mes, ano) {
  const hoje = new Date()
  hoje.setHours(0, 0, 0, 0)
  if (mes) {
    const alvo = new Date(ano ?? hoje.getFullYear(), mes - 1, dia)
    // dd/mm sem ano que já passou há muito tempo: provavelmente é do ano que vem
    if (!ano && alvo < hoje && hoje - alvo > 60 * 86400000) alvo.setFullYear(alvo.getFullYear() + 1)
    return alvo.getMonth() === mes - 1 ? paraIso(alvo) : null
  }
  // só o dia: este mês, ou o próximo se o dia já passou
  let alvo = new Date(hoje.getFullYear(), hoje.getMonth(), dia)
  if (alvo < hoje) alvo = new Date(hoje.getFullYear(), hoje.getMonth() + 1, dia)
  return alvo.getDate() === dia ? paraIso(alvo) : null
}

export function interpretarAnotacao(texto) {
  const t = ` ${texto.toLowerCase()} `
  const resultado = { tipo: 'Lembrete', data: null, valor: null }

  if (/\b(pagar|devo|transferir pr[ao]|pix pr[ao])\b/.test(t)) resultado.tipo = 'A pagar'
  else if (/\b(receber|me deve|cobrar|me paga)\b/.test(t)) resultado.tipo = 'A receber'

  const hoje = new Date()
  const dataBarra = t.match(/\b(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\b/)
  const dia = t.match(/\bdia\s+(\d{1,2})\b/)
  if (/\bamanh[ãa]\b/.test(t)) {
    resultado.data = paraIso(new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() + 1))
  } else if (/\bhoje\b/.test(t)) {
    resultado.data = paraIso(hoje)
  } else if (dataBarra) {
    const ano = dataBarra[3] ? Number(dataBarra[3].length === 2 ? `20${dataBarra[3]}` : dataBarra[3]) : undefined
    resultado.data = dataDoDia(Number(dataBarra[1]), Number(dataBarra[2]), ano)
  } else if (dia && Number(dia[1]) >= 1 && Number(dia[1]) <= 31) {
    resultado.data = dataDoDia(Number(dia[1]))
  }

  const valor = t.match(/r\$\s*([\d.]+(?:,\d{1,2})?)/) || t.match(/\b([\d.]+(?:,\d{1,2})?)\s*(?:reais|conto|pila)\b/)
  if (valor) {
    const numero = Number(valor[1].replace(/\./g, '').replace(',', '.'))
    if (numero > 0) resultado.valor = numero
  }
  return resultado
}
