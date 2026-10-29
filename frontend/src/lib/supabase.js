// Cliente do Supabase usado SOMENTE para login/sessão.
// Os dados nunca são lidos direto do banco: tudo passa pela API (FastAPI).
import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const chavePublica = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!url || !chavePublica) {
  console.error('Configure VITE_SUPABASE_URL e VITE_SUPABASE_ANON_KEY no arquivo .env')
}

export const supabase = createClient(url, chavePublica, {
  auth: {
    persistSession: true, // mantém o login mesmo fechando o app
    autoRefreshToken: true, // renova o token antes de expirar
  },
})
