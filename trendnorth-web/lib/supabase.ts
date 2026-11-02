import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

export interface ScreenerRecord {
  id?: number
  scan_timestamp: string
  symbol: string
  company: string
  price: number
  signal: 'BUY / ACCUMULATE' | 'SELL / EXIT' | 'TRIM / TAKE PROFIT' | 'KEEP / HOLD'
  rsi_14: number
  sma_50: number
  sma_200: number
  sma_trend: string
  rationale: string
  atr_14?: number | null
  stop_level_atr?: number | null
  target_atr?: number | null
}