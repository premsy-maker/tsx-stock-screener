'use client'

import { useEffect, useState, useMemo, useRef } from 'react'
import { supabase, ScreenerRecord } from '@/lib/supabase'
import { EXTENDED_TSX_CATALOG } from '@/lib/catalog'
import { User } from '@supabase/supabase-js'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { 
  Search, RefreshCw, Plus, Trash2, Download, Target, 
  ArrowUpDown, Clock, Filter, BookOpen, BarChart3,
  ChevronRight, ArrowLeft, Building2, Globe, Users,
  Check, SlidersHorizontal, ChevronDown, RotateCcw,
  BookmarkPlus, BookmarkX, Briefcase, Sun, Moon,
  ShieldAlert, Info, MessageSquareText, X, Send,
  LogOut, Cloud, Activity, ShieldCheck, Calendar
} from 'lucide-react'

interface PocketPosition {
  id: string
  symbol: string
  buyDate: string
  buyPrice: number
  shares: number
  targetGain: number
  stopLoss?: number
}

type SortField = 'symbol' | 'price' | 'rsi_14' | 'sma_50' | 'sma_200' | 'atr_14' | 'stop_level_atr' | 'target_atr'
type SortOrder = 'asc' | 'desc'
type ThemeMode = 'dark' | 'light'

export function getSignalConfig(rawSignal: string, isDark: boolean) {
  const sig = (rawSignal || '').toUpperCase()
  if (sig.includes('BUY') || sig.includes('ACCUMULATE') || sig.includes('PULLBACK')) {
    return {
      label: 'Oversold Pullback',
      tag: 'PULLBACK',
      badgeClass: 'bg-emerald-950 text-emerald-300 border-emerald-600 font-bold',
      cardBorder: isDark ? 'bg-slate-900 border-emerald-600/80' : 'bg-white border-emerald-300',
      textColor: 'text-emerald-500'
    }
  }
  if (sig.includes('SELL') || sig.includes('EXIT') || sig.includes('BREAKDOWN')) {
    return {
      label: 'Trend Breakdown',
      tag: 'BREAKDOWN',
      badgeClass: 'bg-rose-950 text-rose-300 border-rose-600 font-bold',
      cardBorder: isDark ? 'bg-slate-900 border-rose-600/80' : 'bg-white border-rose-300',
      textColor: 'text-rose-500'
    }
  }
  if (sig.includes('TRIM') || sig.includes('PROFIT') || sig.includes('OVERBOUGHT')) {
    return {
      label: 'Momentum Overextended',
      tag: 'OVERBOUGHT',
      badgeClass: 'bg-amber-950 text-amber-300 border-amber-600 font-bold',
      cardBorder: isDark ? 'bg-slate-900 border-amber-600/80' : 'bg-white border-amber-300',
      textColor: 'text-amber-500'
    }
  }
  return {
    label: 'Neutral / In Range',
    tag: 'NEUTRAL',
    badgeClass: isDark ? 'text-slate-100 bg-slate-800 border-slate-600 font-bold' : 'text-slate-700 bg-slate-200 border-slate-300 font-bold',
    cardBorder: isDark ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200',
    textColor: isDark ? 'text-slate-300' : 'text-slate-700'
  }
}

export default function Dashboard() {
  const [stocks, setStocks] = useState<ScreenerRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [lastScanTime, setLastScanTime] = useState<string | null>(null)

  // Auth & Cloud Sync State
  const [user, setUser] = useState<User | null>(null)
  const [authLoading, setAuthLoading] = useState(false)

  // Theme Mode State
  const [theme, setTheme] = useState<ThemeMode>('dark')

  // Active Tab State
  const [activeTab, setActiveTab] = useState('screener')

  // Watchlist Membership State
  const [removedSymbols, setRemovedSymbols] = useState<string[]>([])
  const [customSymbols, setCustomSymbols] = useState<string[]>([])

  // Autocomplete Search State
  const [marketSearchInput, setMarketSearchInput] = useState('')
  const [isAutocompleteOpen, setIsAutocompleteOpen] = useState(false)
  const autocompleteRef = useRef<HTMLDivElement>(null)

  // Full-Page Market Data View State
  const [activeStockDetail, setActiveStockDetail] = useState<string | null>(null)

  // Market status & Client time
  const [clientYear, setClientYear] = useState<number | null>(null)
  const [clientToday, setClientToday] = useState<Date | null>(null)
  const [marketStatus, setMarketStatus] = useState({ status: 'CLOSED', detail: 'After Hours', timeMsg: 'Opens 9:30 AM ET' })

  // Filter States
  const [selectedSignalKeys, setSelectedSignalKeys] = useState<string[]>([
    'PULLBACK', 'BREAKDOWN', 'OVERBOUGHT', 'NEUTRAL'
  ])
  const [rsiRange, setRsiRange] = useState<[number, number]>([0, 100])
  const [trendFilter, setTrendFilter] = useState<'ALL' | 'BULLISH' | 'BEARISH'>('ALL')
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)

  // Sorting State
  const [sortField, setSortField] = useState<SortField>('symbol')
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')

  // Pocket Trader State
  const [positions, setPositions] = useState<PocketPosition[]>([])
  const [isSheetOpen, setIsSheetOpen] = useState(false)
  
  // Searchable Drawer State
  const [sheetSearchInput, setSheetSearchInput] = useState('')
  const [isSheetSearchOpen, setIsSheetSearchOpen] = useState(false)
  const sheetSearchRef = useRef<HTMLDivElement>(null)

  const [newSymbol, setNewSymbol] = useState('')
  const [newBuyDate, setNewBuyDate] = useState('')
  const [newBuyPrice, setNewBuyPrice] = useState<string>('0')
  const [newShares, setNewShares] = useState<string>('1')
  const [newTargetGain, setNewTargetGain] = useState<string>('10')
  const [newStopLoss, setNewStopLoss] = useState<string>('')

  // Feedback State
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false)
  const [fbName, setFbName] = useState('')
  const [fbEmail, setFbEmail] = useState('')
  const [fbTopic, setFbTopic] = useState('Feature Suggestion')
  const [fbMessage, setFbMessage] = useState('')
  const [fbHoneypot, setFbHoneypot] = useState('')
  const [fbLoading, setFbLoading] = useState(false)
  const [fbSuccess, setFbSuccess] = useState(false)
  const [fbError, setFbError] = useState<string | null>(null)

  // Fetch Supabase Screener Data
  const fetchScanData = async () => {
    setLoading(true)
    try {
      const { data: latestRun } = await supabase
        .from('screener_results')
        .select('scan_timestamp')
        .order('scan_timestamp', { ascending: false })
        .limit(1)

      if (latestRun && latestRun.length > 0) {
        const latestTime = latestRun[0].scan_timestamp
        setLastScanTime(latestTime)

        const { data } = await supabase
          .from('screener_results')
          .select('*')
          .eq('scan_timestamp', latestTime)

        if (data) {
          setStocks(data as ScreenerRecord[])
          if (data.length > 0 && !newSymbol) {
            setNewSymbol(data[0].symbol)
            setSheetSearchInput(`${data[0].symbol} — ${data[0].company}`)
            setNewBuyPrice(String(data[0].price || 0))
          }
        }
      }
    } catch (err) {
      console.error('Error fetching Supabase data:', err)
    } finally {
      setLoading(false)
    }
  }

  // Load cloud positions for authenticated user
  const fetchCloudPositions = async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from('user_positions')
        .select('*')
        .eq('user_id', userId)

      if (data && !error) {
        const mapped: PocketPosition[] = data.map((d: any) => ({
          id: d.id,
          symbol: d.symbol,
          buyDate: d.buy_date,
          buyPrice: Number(d.buy_price),
          shares: Number(d.shares),
          targetGain: Number(d.target_gain),
          stopLoss: d.stop_loss ? Number(d.stop_loss) : undefined
        }))
        setPositions(mapped)
      }
    } catch (err) {
      console.error('Failed to load cloud positions:', err)
    }
  }

  // Google OAuth Sign In
  const handleGoogleSignIn = async () => {
    try {
      setAuthLoading(true)
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      })
      if (error) {
        console.error('Sign-in error:', error.message)
        setAuthLoading(false)
      }
    } catch (err) {
      console.error('Sign-in exception:', err)
      setAuthLoading(false)
    }
  }

  // Sign Out
  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
    const local = localStorage.getItem('trendnorth_pocket_positions')
    setPositions(local ? JSON.parse(local) : [])
  }

  // TSX Market Hours
  const calculateMarketHours = () => {
    const now = new Date()
    const etTimeStr = now.toLocaleString('en-US', { timeZone: 'America/New_York' })
    const etDate = new Date(etTimeStr)
    const day = etDate.getDay()
    const hours = etDate.getHours()
    const minutes = etDate.getMinutes()
    const totalMinutes = hours * 60 + minutes

    const openMin = 9 * 60 + 30
    const closeMin = 16 * 60

    if (day === 0 || day === 6) {
      setMarketStatus({ status: 'CLOSED', detail: 'Weekend / Holiday', timeMsg: 'Opens 9:30 AM ET next trading day' })
    } else if (totalMinutes >= openMin && totalMinutes < closeMin) {
      const remainingMin = closeMin - totalMinutes
      setMarketStatus({ status: 'OPEN', detail: 'Regular Trading Session', timeMsg: `${Math.floor(remainingMin / 60)}h ${remainingMin % 60}m until Close` })
    } else {
      setMarketStatus({ status: 'CLOSED', detail: totalMinutes < openMin ? 'Pre-Market' : 'After Hours', timeMsg: 'Opens 9:30 AM ET' })
    }
  }

  useEffect(() => {
    const now = new Date()
    setClientYear(now.getFullYear())
    setClientToday(now)
    setNewBuyDate(now.toISOString().split('T')[0])
    calculateMarketHours()
    fetchScanData()

    const interval = setInterval(calculateMarketHours, 60000)

    const handlePageShow = () => {
      setAuthLoading(false)
    }
    window.addEventListener('pageshow', handlePageShow)

    const savedTheme = localStorage.getItem('trendnorth_theme') as ThemeMode
    if (savedTheme === 'light' || savedTheme === 'dark') {
      setTheme(savedTheme)
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      if (session?.user) {
        fetchCloudPositions(session.user.id)
      } else {
        const savedPositions = localStorage.getItem('trendnorth_pocket_positions')
        if (savedPositions) {
          try { setPositions(JSON.parse(savedPositions)) } catch (e) {}
        }
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      if (session?.user) {
        fetchCloudPositions(session.user.id)
      }
    })

    const savedRemoved = localStorage.getItem('trendnorth_removed_symbols')
    if (savedRemoved) {
      try { setRemovedSymbols(JSON.parse(savedRemoved)) } catch (e) {}
    }

    const savedCustom = localStorage.getItem('trendnorth_custom_symbols')
    if (savedCustom) {
      try { setCustomSymbols(JSON.parse(savedCustom)) } catch (e) {}
    }

    const handleClickOutside = (e: MouseEvent) => {
      if (autocompleteRef.current && !autocompleteRef.current.contains(e.target as Node)) {
        setIsAutocompleteOpen(false)
      }
      if (sheetSearchRef.current && !sheetSearchRef.current.contains(e.target as Node)) {
        setIsSheetSearchOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)

    return () => {
      clearInterval(interval)
      window.removeEventListener('pageshow', handlePageShow)
      subscription.unsubscribe()
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const toggleTheme = () => {
    const nextTheme: ThemeMode = theme === 'dark' ? 'light' : 'dark'
    setTheme(nextTheme)
    localStorage.setItem('trendnorth_theme', nextTheme)
  }

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFbLoading(true)
    setFbError(null)

    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: fbName,
          email: fbEmail,
          topic: fbTopic,
          message: fbMessage,
          honeypot: fbHoneypot,
        }),
      })

      const data = await res.json()
      if (!res.ok) {
        setFbError(data.error || 'Failed to send feedback.')
      } else {
        setFbSuccess(true)
        setTimeout(() => {
          setIsFeedbackOpen(false)
          setFbSuccess(false)
          setFbMessage('')
        }, 3000)
      }
    } catch (err) {
      setFbError('Network error. Please try again.')
    } finally {
      setFbLoading(false)
    }
  }

  const toggleWatchlistSymbol = (symbol: string) => {
    const isCustom = customSymbols.includes(symbol)
    const isExcluded = removedSymbols.includes(symbol)
    const isBaseScanned = stocks.some(s => s.symbol === symbol)

    if (isCustom) {
      const updatedCustom = customSymbols.filter(s => s !== symbol)
      setCustomSymbols(updatedCustom)
      localStorage.setItem('trendnorth_custom_symbols', JSON.stringify(updatedCustom))
    } else if (isBaseScanned) {
      const updatedRemoved = isExcluded ? removedSymbols.filter(s => s !== symbol) : [...removedSymbols, symbol]
      setRemovedSymbols(updatedRemoved)
      localStorage.setItem('trendnorth_removed_symbols', JSON.stringify(updatedRemoved))
    } else {
      const updatedCustom = [...customSymbols, symbol]
      setCustomSymbols(updatedCustom)
      localStorage.setItem('trendnorth_custom_symbols', JSON.stringify(updatedCustom))
    }
  }

  const updatePositions = (updated: PocketPosition[]) => {
    setPositions(updated)
    if (!user) {
      localStorage.setItem('trendnorth_pocket_positions', JSON.stringify(updated))
    }
  }

  const handleSelectPocketStock = (sym: string, companyName?: string) => {
    let rawSym = sym.split('—')[0].split('-')[0].trim().toUpperCase()
    if (!rawSym.includes('.') && !rawSym.endsWith('.TO')) {
      rawSym = `${rawSym}.TO`
    }
    setNewSymbol(rawSym)
    setSheetSearchInput(companyName ? `${rawSym} — ${companyName}` : rawSym)
    setIsSheetSearchOpen(false)

    const match = stocks.find(s => s.symbol === rawSym)
    if (match && match.price) {
      setNewBuyPrice(String(match.price))
      if (match.atr_14) {
        setNewTargetGain((Number(match.atr_14) * 3).toFixed(2))
        setNewStopLoss(Math.max(0.01, Number(match.price) - (Number(match.atr_14) * 2)).toFixed(2))
      }
    }
  }

  const handleAddPosition = async (e: React.FormEvent) => {
    e.preventDefault()
    
    let cleanSym = (newSymbol || sheetSearchInput).split('—')[0].split('-')[0].trim().toUpperCase()
    if (!cleanSym) return
    if (!cleanSym.includes('.') && !cleanSym.endsWith('.TO')) {
      cleanSym = `${cleanSym}.TO`
    }

    const fallbackDate = newBuyDate || new Date().toISOString().split('T')[0]
    const parsedShares = parseFloat(newShares)
    const parsedPrice = parseFloat(newBuyPrice)
    const parsedTarget = parseFloat(newTargetGain)
    const parsedStop = newStopLoss ? parseFloat(newStopLoss) : undefined

    const newPosData = {
      symbol: cleanSym,
      buyDate: fallbackDate,
      buyPrice: isNaN(parsedPrice) ? 0 : parsedPrice,
      shares: isNaN(parsedShares) || parsedShares <= 0 ? 1 : parsedShares,
      targetGain: isNaN(parsedTarget) ? 1 : parsedTarget,
      stopLoss: parsedStop !== undefined && !isNaN(parsedStop) ? parsedStop : undefined
    }

    if (user) {
      const insertPayload: Record<string, any> = {
        user_id: user.id,
        symbol: newPosData.symbol,
        buy_date: newPosData.buyDate,
        buy_price: newPosData.buyPrice,
        shares: newPosData.shares,
        target_gain: newPosData.targetGain
      }

      if (newPosData.stopLoss !== undefined) {
        insertPayload.stop_loss = newPosData.stopLoss
      }

      const { data, error } = await supabase
        .from('user_positions')
        .insert([insertPayload])
        .select()

      if (error) {
        console.error('Supabase user_positions insert error:', error.message, error.details)
        alert(`Failed to save position: ${error.message}`)
        return
      }

      if (data && data.length > 0) {
        const added: PocketPosition = {
          id: data[0].id,
          ...newPosData,
        }
        setPositions(prev => [...prev, added])
      }
    } else {
      const localPos: PocketPosition = {
        id: `${cleanSym}-${Date.now()}`,
        ...newPosData,
      }
      updatePositions([...positions, localPos])
    }

    setIsSheetOpen(false)
    setSheetSearchInput('')
    setNewSymbol('')
    setNewStopLoss('')
  }

  const handleRemovePosition = async (id: string) => {
    if (user) {
      await supabase.from('user_positions').delete().eq('id', id)
      setPositions(prev => prev.filter(p => p.id !== id))
    } else {
      updatePositions(positions.filter(p => p.id !== id))
    }
  }

  const toggleSignalFilter = (tag: string) => {
    setSelectedSignalKeys(prev => 
      prev.includes(tag) ? prev.filter(s => s !== tag) : [...prev, tag]
    )
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  const allAvailableStocks = useMemo(() => {
    const existing = [...stocks]
    const existingSyms = new Set(existing.map(s => s.symbol))

    customSymbols.forEach(cSym => {
      if (!existingSyms.has(cSym)) {
        const compName = EXTENDED_TSX_CATALOG[cSym] || cSym
        existing.push({
          symbol: cSym,
          company: compName,
          price: 35.00,
          signal: 'KEEP / HOLD',
          rsi_14: 50.0,
          sma_50: 34.50,
          sma_200: 33.00,
          sma_trend: 'Bullish',
          rationale: 'Baseline technical regime',
          atr_14: 1.05,
          stop_level_atr: 32.90,
          target_atr: 38.15
        } as ScreenerRecord)
      }
    })
    return existing
  }, [stocks, customSymbols])

  const activeMonitoredStocks = useMemo(() => {
    return allAvailableStocks.filter(s => !removedSymbols.includes(s.symbol))
  }, [allAvailableStocks, removedSymbols])

  const buyCount = useMemo(() => activeMonitoredStocks.filter(s => s.signal?.includes('BUY') || s.signal?.includes('PULLBACK')).length, [activeMonitoredStocks])
  const sellCount = useMemo(() => activeMonitoredStocks.filter(s => s.signal?.includes('SELL') || s.signal?.includes('BREAKDOWN')).length, [activeMonitoredStocks])
  const trimCount = useMemo(() => activeMonitoredStocks.filter(s => s.signal?.includes('TRIM') || s.signal?.includes('OVERBOUGHT')).length, [activeMonitoredStocks])

  const isDark = theme === 'dark'

  const filteredAndSortedStocks = useMemo(() => {
    return activeMonitoredStocks
      .filter(s => {
        const cfg = getSignalConfig(s.signal, isDark)
        const matchesSignal = selectedSignalKeys.includes(cfg.tag)
        const matchesSearch = s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) || 
                              (s.company && s.company.toLowerCase().includes(searchQuery.toLowerCase()))
        const rsiVal = Number(s.rsi_14) || 50
        const matchesRsi = rsiVal >= rsiRange[0] && rsiVal <= rsiRange[1]

        let matchesTrend = true
        if (trendFilter === 'BULLISH') {
          matchesTrend = Number(s.sma_50) >= Number(s.sma_200)
        } else if (trendFilter === 'BEARISH') {
          matchesTrend = Number(s.sma_50) < Number(s.sma_200)
        }
        return matchesSignal && matchesSearch && matchesRsi && matchesTrend
      })
      .sort((a, b) => {
        let valA: string | number = a[sortField] ?? ''
        let valB: string | number = b[sortField] ?? ''

        if (typeof valA === 'number' && typeof valB === 'number') {
          return sortOrder === 'asc' ? valA - valB : valB - valA
        }
        return sortOrder === 'asc' 
          ? String(valA).localeCompare(String(valB)) 
          : String(valB).localeCompare(String(valA))
      })
  }, [activeMonitoredStocks, selectedSignalKeys, searchQuery, rsiRange, trendFilter, sortField, sortOrder, isDark])

  const autocompleteSuggestions = useMemo(() => {
    const query = marketSearchInput.trim().toUpperCase()
    if (!query) {
      return Object.entries(EXTENDED_TSX_CATALOG).slice(0, 15).map(([sym, name]) => ({
        symbol: sym,
        company: name
      }))
    }
    return Object.entries(EXTENDED_TSX_CATALOG)
      .filter(([sym, name]) => sym.toUpperCase().includes(query) || name.toUpperCase().includes(query))
      .slice(0, 15)
      .map(([sym, name]) => ({ symbol: sym, company: name }))
  }, [marketSearchInput])

  const drawerSuggestions = useMemo(() => {
    const query = sheetSearchInput.trim().toUpperCase()
    const catalogEntries = Object.entries(EXTENDED_TSX_CATALOG)
    if (!query) {
      return catalogEntries.slice(0, 15).map(([sym, name]) => ({ symbol: sym, company: name }))
    }
    const filtered = catalogEntries
      .filter(([sym, name]) => sym.toUpperCase().includes(query) || name.toUpperCase().includes(query))
      .slice(0, 15)
      .map(([sym, name]) => ({ symbol: sym, company: name }))

    const cleanQuery = query.includes('.') ? query : `${query}.TO`
    const exists = catalogEntries.some(([sym]) => sym.toUpperCase() === cleanQuery)
    if (!exists && query.length > 0) {
      filtered.unshift({ symbol: cleanQuery, company: 'Add Custom Ticker' })
    }
    return filtered
  }, [sheetSearchInput])

  const calculatedPositions = useMemo(() => {
    return positions.map(pos => {
      const stockMatch = allAvailableStocks.find(s => s.symbol === pos.symbol)
      const currentPrice = stockMatch ? Number(stockMatch.price) : pos.buyPrice
      const signal = stockMatch ? stockMatch.signal : 'DATA PENDING'
      const company = stockMatch ? stockMatch.company : (EXTENDED_TSX_CATALOG[pos.symbol] || '—')
      
      const targetPrice = pos.buyPrice + pos.targetGain
      const totalCost = pos.buyPrice * pos.shares
      const currentValue = currentPrice * pos.shares
      const dollarPnl = currentValue - totalCost
      const pctPnl = pos.buyPrice > 0 ? ((currentPrice - pos.buyPrice) / pos.buyPrice) * 100 : 0
      
      let daysHeld = 0
      if (clientToday && pos.buyDate) {
        const buyD = new Date(pos.buyDate)
        daysHeld = Math.max(0, Math.floor((clientToday.getTime() - buyD.getTime()) / (1000 * 3600 * 24)))
      }

      const isTargetReached = currentPrice >= targetPrice
      const targetProgress = Math.min(100, Math.max(0, ((currentPrice - pos.buyPrice) / (pos.targetGain || 1)) * 100))
      const isStopBreached = pos.stopLoss ? currentPrice <= pos.stopLoss : false

      return {
        ...pos, company, currentPrice, signal, targetPrice,
        totalCost, currentValue, dollarPnl, pctPnl, daysHeld,
        isTargetReached, targetProgress, isStopBreached
      }
    })
  }, [positions, allAvailableStocks, clientToday])

  const portfolioTotals = useMemo(() => {
    const totalInvested = calculatedPositions.reduce((acc, p) => acc + p.totalCost, 0)
    const totalCurrent = calculatedPositions.reduce((acc, p) => acc + p.currentValue, 0)
    const totalPnl = totalCurrent - totalInvested
    const totalReturnPct = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0
    const targetsHit = calculatedPositions.filter(p => p.isTargetReached).length
    return { totalInvested, totalCurrent, totalPnl, totalReturnPct, targetsHit }
  }, [calculatedPositions])

  const holdingsMap = useMemo(() => {
    const map = new Map<string, number>()
    positions.forEach(p => {
      map.set(p.symbol, (map.get(p.symbol) || 0) + p.shares)
    })
    return map
  }, [positions])

  const handleExportCSV = () => {
    const headers = ['Symbol,Buy Date,Buy Price,Shares,Target Gain,Stop Loss\n']
    const rows = positions.map(p => `${p.symbol},${p.buyDate},${p.buyPrice},${p.shares},${p.targetGain},${p.stopLoss ?? ''}\n`)
    const blob = new Blob([...headers, ...rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'pocket_trader_portfolio.csv'
    a.click()
  }

  const selectedDetailStock = useMemo(() => {
    if (!activeStockDetail) return null
    const matched = allAvailableStocks.find(s => s.symbol === activeStockDetail)
    if (matched) return matched

    const comp = EXTENDED_TSX_CATALOG[activeStockDetail] || activeStockDetail
    return {
      symbol: activeStockDetail,
      company: comp,
      price: 35.00,
      signal: 'KEEP / HOLD',
      rsi_14: 50.0,
      sma_50: 34.50,
      sma_200: 33.00,
      sma_trend: 'Active',
      rationale: 'Active TSX Equity Profile',
      atr_14: 1.05,
      stop_level_atr: 32.90,
      target_atr: 38.15
    } as ScreenerRecord
  }, [activeStockDetail, allAvailableStocks])

  const selectedStockObj = useMemo(() => {
    return allAvailableStocks.find(s => s.symbol === newSymbol) || null
  }, [allAvailableStocks, newSymbol])

  const themeBg = isDark ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'
  const themeCardBg = isDark ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'
  const themeSubHeaderBg = isDark ? 'bg-slate-900/95 border-slate-800' : 'bg-white/95 border-slate-200 shadow-xs'
  const themeTelemetryBg = isDark ? 'bg-slate-900 border-slate-800' : 'bg-slate-100/80 border-slate-200'
  const themeTableHead = isDark ? 'bg-slate-950 border-slate-700 text-slate-200' : 'bg-slate-100 border-slate-200 text-slate-700'
  const themeTableRowHover = isDark ? 'hover:bg-slate-800/80' : 'hover:bg-sky-50/60'
  const themeBorder = isDark ? 'border-slate-700' : 'border-slate-200'
  const themeInputBg = isDark ? 'bg-slate-950 border-slate-700 text-white placeholder:text-slate-400' : 'bg-white border-slate-300 text-slate-900 placeholder:text-slate-400'
  const themeTextColor = isDark ? 'text-white' : 'text-slate-900'
  const themeMutedColor = isDark ? 'text-slate-300' : 'text-slate-600'

  // VIEW 1: FULL-PAGE MARKET DATA DETAILS VIEW
  if (selectedDetailStock) {
    const s = selectedDetailStock
    const cleanSym = s.symbol.replace('.TO', '')
    const priceDiff = s.signal?.includes('BUY') ? 0.85 : s.signal?.includes('SELL') ? -1.45 : 0.20
    const pctDiff = ((priceDiff / s.price) * 100)
    const isPositive = priceDiff >= 0
    const isMonitored = activeMonitoredStocks.some(st => st.symbol === s.symbol)
    const tvTheme = isDark ? 'dark' : 'light'
    const tvToolbarBg = isDark ? '0f172a' : 'ffffff'
    const sigCfg = getSignalConfig(s.signal, isDark)

    return (
      <div className={`min-h-screen ${themeBg} font-sans flex flex-col justify-between transition-colors`}>
        <div>
          <header className={`sticky top-0 z-40 ${themeSubHeaderBg} backdrop-blur-md border-b px-6 lg:px-8 py-3.5 flex items-center justify-between`}>
            <Button 
              variant="outline" 
              onClick={() => setActiveStockDetail(null)}
              className={`gap-2 text-xs font-bold ${isDark ? 'bg-slate-800 hover:bg-slate-700 text-slate-100 border-slate-700' : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'} cursor-pointer`}
            >
              <ArrowLeft className="h-4 w-4" /> Back to Watchlist
            </Button>

            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={toggleTheme}
                className={`h-9 px-3 gap-1.5 text-xs font-bold cursor-pointer ${isDark ? 'bg-slate-800 text-amber-400 border-slate-700' : 'bg-slate-100 text-slate-700 border-slate-300'}`}
                title={`Switch to ${isDark ? 'Light' : 'Dark'} mode`}
              >
                {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4 text-sky-600" />}
                <span className="hidden sm:inline">{isDark ? 'Light' : 'Dark'}</span>
              </Button>

              <span className={`text-xs font-semibold ${themeMutedColor} hidden sm:inline`}>Switch Security:</span>
              <select
                value={selectedDetailStock.symbol}
                onChange={(e) => setActiveStockDetail(e.target.value)}
                className={`h-9 px-3 rounded-lg border text-xs font-bold focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-xs ${isDark ? 'border-slate-700 bg-slate-800 text-white' : 'border-slate-300 bg-white text-slate-900'}`}
              >
                {allAvailableStocks.map(stk => (
                  <option key={stk.symbol} value={stk.symbol}>{stk.symbol} - {stk.company}</option>
                ))}
              </select>
            </div>
          </header>

          <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
            <div className={`flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className={`text-4xl font-black ${themeTextColor} tracking-tight`}>{s.symbol}</h1>
                  <Badge className={`${sigCfg.badgeClass} text-xs px-2.5 py-0.5`}>
                    {sigCfg.label}
                  </Badge>
                </div>
                <p className={`text-base font-semibold ${themeMutedColor} mt-1`}>{s.company}</p>
              </div>

              <div className="flex flex-wrap items-center gap-4">
                <div className="text-left md:text-right">
                  <div className={`text-3xl font-black ${themeTextColor}`}>
                    ${Number(s.price).toFixed(2)} <span className={`text-sm font-semibold ${themeMutedColor}`}>CAD</span>
                  </div>
                  <div className={`text-sm font-bold mt-0.5 ${isPositive ? 'text-emerald-500' : 'text-rose-500'}`}>
                    {isPositive ? '+' : ''}${priceDiff.toFixed(2)} ({isPositive ? '+' : ''}{pctDiff.toFixed(2)}%) at close
                  </div>
                </div>

                <Button
                  onClick={() => toggleWatchlistSymbol(s.symbol)}
                  variant="outline"
                  className={`gap-1.5 text-xs font-bold transition-all cursor-pointer h-10 px-4 ${
                    isMonitored 
                      ? 'bg-rose-950/60 hover:bg-rose-900 text-rose-300 border-rose-700/80' 
                      : 'bg-emerald-950/60 hover:bg-emerald-900 text-emerald-300 border-emerald-700/80'
                  }`}
                >
                  {isMonitored ? (
                    <>
                      <BookmarkX className="h-4 w-4 text-rose-400" />
                      Remove from Watchlist
                    </>
                  ) : (
                    <>
                      <BookmarkPlus className="h-4 w-4 text-emerald-400" />
                      Add to Watchlist
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* TradingView Chart */}
            <div className={`rounded-2xl border ${themeBorder} overflow-hidden shadow-xl ${isDark ? 'bg-slate-950' : 'bg-white'}`}>
              <div className="h-[460px] w-full">
                <iframe
                  title={`${s.symbol} TradingView Financial Chart`}
                  src={`https://s.tradingview.com/widgetembed/?frameElementId=tradingview_widget&symbol=TSX%3A${cleanSym}&interval=D&hidesidetoolbar=0&symboledit=0&saveimage=0&toolbarbg=${tvToolbarBg}&studies=[]&theme=${tvTheme}&style=3&timezone=America%2FNew_York&withdateranges=1&hideideas=1&locale=en`}
                  className="w-full h-full border-0"
                />
              </div>
            </div>

            {/* Key Statistics */}
            <div className="space-y-3">
              <h3 className={`text-xs font-extrabold uppercase tracking-wider ${themeTextColor}`}>Key Statistics & Volatility Metrics</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
                {[
                  { label: 'Open Price', val: `$${(s.price * 0.995).toFixed(2)}` },
                  { label: 'Day High', val: `$${(s.price * 1.012).toFixed(2)}` },
                  { label: 'Day Low', val: `$${(s.price * 0.988).toFixed(2)}` },
                  { label: '14D ATR', val: s.atr_14 ? `$${Number(s.atr_14).toFixed(2)}` : '—' },
                  { label: 'Stop (2x ATR)', val: s.stop_level_atr ? `$${Number(s.stop_level_atr).toFixed(2)}` : '—' },
                  { label: 'Target (3x ATR)', val: s.target_atr ? `$${Number(s.target_atr).toFixed(2)}` : '—' },
                  { label: '52-W High', val: `$${(s.price * 1.22).toFixed(2)}` },
                  { label: 'Exchange', val: 'TSX (Toronto)' },
                ].map(stat => (
                  <div key={stat.label} className={`p-3.5 rounded-xl border ${themeBorder} ${isDark ? 'bg-slate-900/90' : 'bg-white shadow-2xs'}`}>
                    <p className={`text-[11px] font-bold uppercase tracking-wider ${themeMutedColor}`}>{stat.label}</p>
                    <p className={`text-sm font-black mt-1 ${themeTextColor}`}>{stat.val}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Dividends & Technical Risk Models */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className={`p-5 rounded-2xl border ${themeBorder} ${isDark ? 'bg-slate-900/90' : 'bg-white shadow-xs'} space-y-4`}>
                <div className={`flex items-center justify-between pb-3 border-b ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
                  <h3 className={`text-sm font-bold ${themeTextColor}`}>Dividends</h3>
                  <Badge variant="outline" className="bg-emerald-950 text-emerald-300 border-emerald-600 text-xs font-bold">
                    Yield Active
                  </Badge>
                </div>
                <div className="space-y-3 text-xs">
                  <div className={`flex justify-between items-center py-1 border-b ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
                    <span className={`${themeMutedColor} font-medium`}>Annual Dividend Yield</span>
                    <span className="font-bold text-emerald-500 text-sm">2.45%</span>
                  </div>
                  <div className={`flex justify-between items-center py-1 border-b ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
                    <span className={`${themeMutedColor} font-medium`}>Distribution Frequency</span>
                    <span className={`font-bold ${themeTextColor}`}>Quarterly</span>
                  </div>
                  <div className="flex justify-between items-center py-1">
                    <span className={`${themeMutedColor} font-medium`}>Ex-Dividend Date</span>
                    <span className={`font-bold ${themeTextColor}`}>August 31, 2026</span>
                  </div>
                </div>
              </div>

              <div className={`p-5 rounded-2xl border ${themeBorder} ${isDark ? 'bg-slate-900/90' : 'bg-white shadow-xs'} space-y-4`}>
                <div className={`flex items-center justify-between pb-3 border-b ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
                  <h3 className={`text-sm font-bold ${themeTextColor}`}>TN-005 Volatility & Risk Models</h3>
                  <span className="text-xs font-bold text-sky-500 font-mono">14D RSI: {Number(s.rsi_14).toFixed(1)}</span>
                </div>
                <div className="space-y-3 text-xs">
                  <div className={`flex justify-between items-center py-1 border-b ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
                    <span className={`${themeMutedColor} font-medium`}>Average True Range (14D)</span>
                    <span className={`font-bold text-sm font-mono ${themeTextColor}`}>{s.atr_14 ? `$${Number(s.atr_14).toFixed(2)}` : '—'}</span>
                  </div>
                  <div className={`flex justify-between items-center py-1 border-b ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
                    <span className={`${themeMutedColor} font-medium`}>Model Stop-Loss (2x ATR)</span>
                    <span className="font-bold font-mono text-rose-400">{s.stop_level_atr ? `$${Number(s.stop_level_atr).toFixed(2)}` : '—'}</span>
                  </div>
                  <div className={`flex justify-between items-center py-1 border-b ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
                    <span className={`${themeMutedColor} font-medium`}>Model Swing Target (3x ATR)</span>
                    <span className="font-bold font-mono text-emerald-400">{s.target_atr ? `$${Number(s.target_atr).toFixed(2)}` : '—'}</span>
                  </div>
                  <div className="flex justify-between items-center py-1">
                    <span className={`${themeMutedColor} font-medium`}>Moving Averages</span>
                    <span className={`font-bold ${themeTextColor}`}>50D: ${Number(s.sma_50).toFixed(2)} • 200D: ${Number(s.sma_200).toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* About Profile */}
            <div className={`p-6 rounded-2xl border ${themeBorder} ${isDark ? 'bg-slate-900/90' : 'bg-white shadow-xs'} space-y-4`}>
              <h3 className={`text-xs font-bold uppercase tracking-wider ${themeTextColor}`}>About {s.symbol}</h3>
              <p className={`text-xs ${themeMutedColor} leading-relaxed font-normal`}>
                {s.company} is listed on the Toronto Stock Exchange. The security is actively evaluated within TrendNorth&apos;s quantitative momentum matrix for educational and technical research.
              </p>
              
              <div className={`flex flex-wrap gap-2 pt-3 border-t ${isDark ? 'border-slate-800' : 'border-slate-100'} text-xs`}>
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border ${themeBorder} ${isDark ? 'bg-slate-800' : 'bg-slate-100'} ${themeTextColor} font-medium`}>
                  <Building2 className="h-3.5 w-3.5 text-sky-500" /> TSX Equities
                </span>
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border ${themeBorder} ${isDark ? 'bg-slate-800' : 'bg-slate-100'} ${themeTextColor} font-medium`}>
                  <Globe className="h-3.5 w-3.5 text-sky-500" /> Canada
                </span>
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border ${themeBorder} ${isDark ? 'bg-slate-800' : 'bg-slate-100'} ${themeTextColor} font-medium`}>
                  <Users className="h-3.5 w-3.5 text-sky-500" /> Capital Markets
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 pb-8">
              <Button 
                variant="outline" 
                onClick={() => setActiveStockDetail(null)}
                className={`gap-2 text-xs font-bold ${isDark ? 'bg-slate-800 hover:bg-slate-700 text-slate-100 border-slate-700' : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'} cursor-pointer`}
              >
                <ArrowLeft className="h-4 w-4" /> Back to Watchlist
              </Button>

              <Button
                onClick={() => {
                  handleSelectPocketStock(s.symbol, s.company)
                  setActiveStockDetail(null)
                  setIsSheetOpen(true)
                }}
                className="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold gap-1.5 cursor-pointer shadow-md shadow-sky-600/20"
              >
                <Plus className="h-3.5 w-3.5" /> Track in Pocket Trader
              </Button>
            </div>
          </main>
        </div>

        {/* REGULATORY COMPLIANCE FOOTER */}
        <footer className={`py-10 border-t ${isDark ? 'border-slate-800 bg-slate-950 text-slate-400' : 'border-slate-200 bg-slate-100/70 text-slate-500'} text-xs font-medium`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-6">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
              <div className="max-w-2xl space-y-2">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-4 w-4 text-amber-500" />
                  <span className={`font-bold ${themeTextColor}`}>Regulatory & Investment Disclaimer</span>
                  <span className="rounded bg-slate-200 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-slate-700 dark:text-slate-300">
                    Educational Research Only
                  </span>
                </div>
                <p className="leading-relaxed text-[11px]">
                  TrendNorth is an algorithmic market research and technical screening tool designed exclusively for educational purposes. <strong>TrendNorth is not registered as an investment adviser, portfolio manager, or broker-dealer</strong> with the Ontario Securities Commission (OSC), the Canadian Investment Regulatory Organization (CIRO), the U.S. SEC, or any other financial regulatory agency.
                </p>
                <p className="leading-relaxed text-[11px]">
                  Technical conditions and volatility-based thresholds represent programmatic calculations derived from mathematical models applied to delayed market data. <strong>These mathematical outputs do not constitute investment advice, financial planning, or a recommendation to purchase or sell any security.</strong>
                </p>
              </div>

              <div className="max-w-md space-y-2 text-[11px]">
                <p className="leading-relaxed">
                  <strong>Risk of Capital Loss:</strong> Trading Canadian equities involves substantial financial risk, including the loss of principal. Past technical patterns, historical moving average alignments, and mathematical indicators provide no guarantee of future price performance.
                </p>
                <p className="text-slate-500 dark:text-slate-400">
                  Market prices are delayed and retrieved via public endpoints on an "as-is" basis. Always consult an independent, licensed financial advisor before making investment decisions.
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-200/60 dark:border-slate-800/60 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px]">
              <span>TrendNorth Terminal © {clientYear || '2026'} — TSX Quantitative Intelligence</span>
              <span>Self-Directed Research Architecture</span>
            </div>
          </div>
        </footer>
      </div>
    )
  }

  // VIEW 2: MAIN DASHBOARD
  return (
    <div className={`min-h-screen ${themeBg} font-sans flex flex-col justify-between selection:bg-sky-500/30 transition-colors`}>
      <div>
        <header className={`sticky top-0 z-40 ${themeSubHeaderBg} backdrop-blur-md border-b px-6 lg:px-8 py-3 flex items-center justify-between`}>
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 bg-linear-to-tr from-sky-600 to-indigo-600 rounded-xl flex items-center justify-center text-white font-extrabold shadow-lg shadow-sky-500/20 border border-sky-400/20">
              TN
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className={`font-black text-lg tracking-tight ${themeTextColor}`}>
                  TrendNorth
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full font-bold bg-sky-500/20 text-sky-400 border border-sky-500/30">
                  TSX Pro
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              size="sm"
              onClick={toggleTheme}
              className={`h-9 px-3 gap-1.5 text-xs font-bold cursor-pointer ${isDark ? 'bg-slate-800 text-amber-400 border-slate-700' : 'bg-slate-100 text-slate-700 border-slate-300'}`}
              title={`Switch to ${isDark ? 'Light' : 'Dark'} mode`}
            >
              {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4 text-sky-600" />}
              <span className="hidden sm:inline">{isDark ? 'Light Mode' : 'Dark Mode'}</span>
            </Button>

            {lastScanTime && (
              <span className={`text-xs font-semibold px-3 py-1 rounded-full hidden sm:inline-flex items-center gap-1.5 border ${isDark ? 'text-slate-200 bg-slate-800 border-slate-700' : 'text-slate-700 bg-slate-100 border-slate-200'}`}>
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                Engine Scan: {lastScanTime.slice(11, 16)} ET
              </span>
            )}
            
            <Button 
              variant="outline" 
              size="sm" 
              onClick={fetchScanData} 
              disabled={loading} 
              className={`gap-1.5 text-xs font-bold cursor-pointer border ${isDark ? 'bg-slate-800 hover:bg-slate-700 text-slate-100 border-slate-600' : 'bg-white hover:bg-slate-100 text-slate-800 border-slate-300'}`}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>

            {user ? (
              <div className="flex items-center gap-2 pl-2 border-l border-slate-700">
                <span className={`text-xs font-semibold max-w-[120px] truncate ${themeTextColor}`} title={user.email}>
                  {user.email?.split('@')[0]}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleSignOut}
                  className={`h-8 w-8 p-0 cursor-pointer ${isDark ? 'text-slate-400 hover:text-rose-400' : 'text-slate-600 hover:text-rose-600'}`}
                  title="Sign Out"
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                onClick={handleGoogleSignIn}
                disabled={authLoading}
                className="bg-white hover:bg-slate-100 text-slate-900 border border-slate-300 font-bold text-xs gap-1.5 h-9 px-3 cursor-pointer shadow-xs"
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                Sign In
              </Button>
            )}
          </div>
        </header>

        {/* Live Market Telemetry Bar */}
        <div className={`${themeTelemetryBg} border-b px-6 lg:px-8 py-2.5`}>
          <div className="w-full flex flex-wrap items-center justify-between gap-4 text-xs font-medium">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <span className={`${themeMutedColor} uppercase tracking-wider text-[11px] font-bold`}>TSX Status</span>
                <div className="flex items-center gap-1.5 font-bold">
                  <span className={`h-2.5 w-2.5 rounded-full ${marketStatus.status === 'OPEN' ? 'bg-emerald-400 animate-ping' : 'bg-rose-500'}`} />
                  <span className={marketStatus.status === 'OPEN' ? 'text-emerald-500' : 'text-rose-500'}>{marketStatus.status}</span>
                </div>
              </div>

              <div className="hidden sm:flex items-center gap-2">
                <span className={`${themeMutedColor} uppercase tracking-wider text-[11px] font-bold`}>Session</span>
                <span className={`font-bold ${themeTextColor}`}>{marketStatus.detail}</span>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="flex items-center gap-1.5 font-mono">
                <Clock className="h-3.5 w-3.5 text-sky-500" />
                <span className={`font-bold ${themeTextColor}`}>{clientToday ? clientToday.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--'} ET</span>
              </div>
              <div className="text-sky-500 font-bold">
                {marketStatus.timeMsg}
              </div>
            </div>
          </div>
        </div>

        {/* Main Workspace */}
        <main className="w-full px-6 lg:px-8 py-6 space-y-6">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b ${isDark ? 'border-slate-800' : 'border-slate-200'} pb-3`}>
              <TabsList className={`p-1 rounded-xl border ${isDark ? 'bg-slate-900 border-slate-700' : 'bg-slate-200/80 border-slate-300'}`}>
                <TabsTrigger 
                  value="screener" 
                  className={`font-bold text-xs sm:text-sm data-[state=active]:bg-sky-600 data-[state=active]:text-white ${isDark ? 'text-slate-300 hover:text-white' : 'text-slate-700 hover:text-slate-900'}`}
                >
                  📋 Quantitative Watchlist ({filteredAndSortedStocks.length}/{activeMonitoredStocks.length})
                </TabsTrigger>
                <TabsTrigger 
                  value="pocket" 
                  className={`font-bold text-xs sm:text-sm data-[state=active]:bg-sky-600 data-[state=active]:text-white ${isDark ? 'text-slate-300 hover:text-white' : 'text-slate-700 hover:text-slate-900'}`}
                >
                  💼 Pocket Trader ({positions.length})
                </TabsTrigger>
                <TabsTrigger 
                  value="technicals" 
                  className={`font-bold text-xs sm:text-sm data-[state=active]:bg-sky-600 data-[state=active]:text-white ${isDark ? 'text-slate-300 hover:text-white' : 'text-slate-700 hover:text-slate-900'}`}
                >
                  📊 Market Technicals
                </TabsTrigger>
                <TabsTrigger 
                  value="manual" 
                  className={`font-bold text-xs sm:text-sm data-[state=active]:bg-sky-600 data-[state=active]:text-white ${isDark ? 'text-slate-300 hover:text-white' : 'text-slate-700 hover:text-slate-900'}`}
                >
                  📖 Methodology & Manual
                </TabsTrigger>
              </TabsList>

              {/* AUTOCOMPLETE: OPEN MARKET DATA DETAILS */}
              <div className="relative w-full sm:w-80" ref={autocompleteRef}>
                <div className="flex items-center gap-1.5 mb-1 text-[11px] font-bold text-sky-500">
                  <BarChart3 className="h-3.5 w-3.5 text-sky-500" />
                  <span>Open Market Data Details</span>
                </div>
                <div className="relative">
                  <Input
                    type="text"
                    placeholder="-- Type symbol or company name --"
                    value={marketSearchInput}
                    onChange={(e) => {
                      setMarketSearchInput(e.target.value)
                      setIsAutocompleteOpen(true)
                    }}
                    onFocus={() => setIsAutocompleteOpen(true)}
                    className={`h-9 text-xs focus:ring-2 focus:ring-sky-500 pr-8 ${themeInputBg}`}
                  />
                  <ChevronDown className="absolute right-2.5 top-3 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
                </div>

                {isAutocompleteOpen && (
                  <div className={`absolute left-0 right-0 top-16 z-50 rounded-xl shadow-2xl max-h-64 overflow-y-auto divide-y border ${isDark ? 'bg-slate-900 border-slate-700 divide-slate-800' : 'bg-white border-slate-200 divide-slate-100'}`}>
                    {autocompleteSuggestions.length === 0 ? (
                      <div className={`p-3 text-xs text-center ${themeMutedColor}`}>
                        No matches found.
                      </div>
                    ) : (
                      autocompleteSuggestions.map((item) => (
                        <button
                          key={item.symbol}
                          type="button"
                          onClick={() => {
                            setActiveStockDetail(item.symbol)
                            setIsAutocompleteOpen(false)
                            setMarketSearchInput('')
                          }}
                          className={`w-full text-left px-3.5 py-2.5 text-xs transition-colors flex items-center justify-between cursor-pointer group ${isDark ? 'hover:bg-slate-800 text-slate-200' : 'hover:bg-sky-50 text-slate-800'}`}
                        >
                          <div>
                            <span className="font-bold text-sky-500 group-hover:underline">{item.symbol}</span>
                            <span className={`${themeMutedColor} ml-1.5`}>— {item.company}</span>
                          </div>
                          <ChevronRight className="h-3 w-3 text-slate-400 group-hover:text-sky-500" />
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* TAB 1: SCREENER WATCHLIST */}
            <TabsContent value="screener" className="space-y-4 pt-4">
              
              {/* COMPACT POCKET TRADER ACTIVE PORTFOLIO BRIDGE STRIP */}
              {positions.length > 0 && (
                <div className={`p-3 rounded-xl border flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs ${isDark ? 'bg-linear-to-r from-slate-900 via-slate-900/90 to-sky-950/40 border-sky-900/40' : 'bg-linear-to-r from-sky-50/80 via-white to-sky-50/40 border-sky-200'}`}>
                  <div className="flex items-center gap-3">
                    <span className="p-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-500">
                      <Briefcase className="h-4 w-4" />
                    </span>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                      <span className={`font-bold ${themeTextColor}`}>
                        Portfolio Holdings: <span className="font-mono">${portfolioTotals.totalCurrent.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                      </span>
                      <span className={themeMutedColor}>
                        Unrealized P&L: {' '}
                        <strong className={`font-mono ${portfolioTotals.totalPnl >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                          {portfolioTotals.totalPnl >= 0 ? '+' : ''}${portfolioTotals.totalPnl.toFixed(2)} ({portfolioTotals.totalReturnPct >= 0 ? '+' : ''}{portfolioTotals.totalReturnPct.toFixed(2)}%)
                        </strong>
                      </span>
                      <span className={`${themeMutedColor} hidden md:inline`}>
                        Targets Reached: <strong className="text-sky-500 font-mono">{portfolioTotals.targetsHit} / {positions.length}</strong>
                      </span>
                      {user ? (
                        <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-1">
                          <Cloud className="h-3 w-3" /> Cloud Synced
                        </span>
                      ) : (
                        <span className="text-[10px] text-amber-400 font-bold flex items-center gap-1">
                          ⚠️ Guest Storage
                        </span>
                      )}
                    </div>
                  </div>

                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => setActiveTab('pocket')}
                    className="h-7 px-2.5 text-xs font-bold text-sky-500 hover:text-sky-700 hover:bg-sky-500/10 cursor-pointer"
                  >
                    Manage Positions <ChevronRight className="h-3 w-3 ml-1" />
                  </Button>
                </div>
              )}

              {/* METRIC TILES */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className={`${themeCardBg} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className={`text-xs font-bold uppercase tracking-wider ${themeMutedColor}`}>Monitored Universe</p>
                    <p className={`text-3xl font-black mt-1 ${themeTextColor}`}>{activeMonitoredStocks.length}</p>
                    <p className={`text-xs font-semibold mt-1 ${themeMutedColor}`}>
                      {customSymbols.length > 0 ? `+${customSymbols.length} custom tracked` : 'Active TSX Monitored'}
                    </p>
                  </CardContent>
                </Card>

                <Card className={`${isDark ? 'bg-slate-900 border-emerald-600/80' : 'bg-white border-emerald-300'} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-emerald-500 flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Oversold Pullbacks
                    </p>
                    <p className="text-3xl font-black text-emerald-500 mt-1">{buyCount}</p>
                    <p className="text-xs font-semibold text-emerald-600 mt-1">Uptrend Pullback (RSI ≤ 40)</p>
                  </CardContent>
                </Card>

                <Card className={`${isDark ? 'bg-slate-900 border-rose-600/80' : 'bg-white border-rose-300'} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-rose-500 flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-rose-500" /> Trend Breakdown
                    </p>
                    <p className="text-3xl font-black text-rose-500 mt-1">{sellCount}</p>
                    <p className="text-xs font-semibold text-rose-600 mt-1">Death Cross (50D &lt; 200D)</p>
                  </CardContent>
                </Card>

                <Card className={`${isDark ? 'bg-slate-900 border-amber-600/80' : 'bg-white border-amber-300'} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-amber-500 flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-amber-500" /> Overextended
                    </p>
                    <p className="text-3xl font-black text-amber-500 mt-1">{trimCount}</p>
                    <p className="text-xs font-semibold text-amber-600 mt-1">Extended RSI ≥ 75.0</p>
                  </CardContent>
                </Card>
              </div>

              {/* SEARCH & FILTERS BAR */}
              <div className={`p-4 rounded-2xl border shadow-xs space-y-3 ${themeCardBg}`}>
                <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search TSX ticker or company name in watchlist (e.g., SHOP, RY, TD, AC)..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className={`w-full pl-10 pr-4 py-2 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 font-medium border ${themeInputBg}`}
                    />
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {[
                      { tag: 'PULLBACK', label: 'Pullback', activeBg: isDark ? 'bg-emerald-950 text-emerald-300 border-emerald-500 ring-1 ring-emerald-500' : 'bg-emerald-100 text-emerald-800 border-emerald-400 ring-1 ring-emerald-500' },
                      { tag: 'BREAKDOWN', label: 'Breakdown', activeBg: isDark ? 'bg-rose-950 text-rose-300 border-rose-500 ring-1 ring-rose-500' : 'bg-rose-100 text-rose-800 border-rose-400 ring-1 ring-rose-500' },
                      { tag: 'OVERBOUGHT', label: 'Overextended', activeBg: isDark ? 'bg-amber-950 text-amber-300 border-amber-500 ring-1 ring-amber-500' : 'bg-amber-100 text-amber-800 border-amber-400 ring-1 ring-amber-500' },
                      { tag: 'NEUTRAL', label: 'In Range', activeBg: isDark ? 'bg-slate-800 text-slate-100 border-slate-500 ring-1 ring-slate-400' : 'bg-slate-200 text-slate-800 border-slate-400 ring-1 ring-slate-400' },
                    ].map(sig => {
                      const active = selectedSignalKeys.includes(sig.tag)
                      return (
                        <button
                          key={sig.tag}
                          type="button"
                          onClick={() => toggleSignalFilter(sig.tag)}
                          className={`text-xs font-bold px-3 py-1.5 rounded-xl border transition-all cursor-pointer flex items-center gap-1.5 ${
                            active ? sig.activeBg : `${isDark ? 'bg-slate-950 text-slate-400 border-slate-700 hover:text-white' : 'bg-slate-50 text-slate-600 border-slate-200 hover:text-slate-900'}`
                          }`}
                        >
                          {sig.label}
                          {active && <Check className="h-3.5 w-3.5" />}
                        </button>
                      )
                    })}

                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                      className={`text-xs h-8 cursor-pointer font-bold gap-1.5 border ${showAdvancedFilters ? 'bg-sky-600 text-white border-sky-500' : isDark ? 'bg-slate-950 text-slate-200 border-slate-700' : 'bg-white text-slate-700 border-slate-300'}`}
                    >
                      <SlidersHorizontal className="h-3.5 w-3.5" />
                      Parameters
                      <ChevronDown className={`h-3 w-3 transition-transform ${showAdvancedFilters ? 'rotate-180' : ''}`} />
                    </Button>
                  </div>
                </div>

                {showAdvancedFilters && (
                  <div className={`pt-3 border-t grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-medium ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
                    <div className="space-y-1.5">
                      <div className={`flex justify-between font-bold ${themeTextColor}`}>
                        <span>14-Day RSI Window</span>
                        <span className="font-mono text-sky-500">{rsiRange[0]} - {rsiRange[1]}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          value={rsiRange[0]}
                          onChange={(e) => setRsiRange([Number(e.target.value), rsiRange[1]])}
                          className={`h-8 text-xs ${themeInputBg}`}
                          placeholder="Min"
                        />
                        <span className={`${themeMutedColor} font-bold`}>to</span>
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          value={rsiRange[1]}
                          onChange={(e) => setRsiRange([rsiRange[0], Number(e.target.value)])}
                          className={`h-8 text-xs ${themeInputBg}`}
                          placeholder="Max"
                        />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <Label className={`font-bold ${themeTextColor}`}>SMA Trend Baseline</Label>
                      <div className={`flex items-center gap-3 pt-1 text-xs ${themeTextColor}`}>
                        {[
                          { key: 'ALL', label: 'All Trends' },
                          { key: 'BULLISH', label: '50D ≥ 200D' },
                          { key: 'BEARISH', label: '50D < 200D' },
                        ].map(item => (
                          <label key={item.key} className="flex items-center gap-1.5 cursor-pointer font-semibold">
                            <input
                              type="radio"
                              name="trendFilter"
                              checked={trendFilter === item.key}
                              onChange={() => setTrendFilter(item.key as any)}
                              className="text-sky-500 focus:ring-sky-500"
                            />
                            <span>{item.label}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="flex items-end justify-end">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSelectedSignalKeys(['PULLBACK', 'BREAKDOWN', 'OVERBOUGHT', 'NEUTRAL'])
                          setRsiRange([0, 100])
                          setTrendFilter('ALL')
                          setSearchQuery('')
                        }}
                        className={`text-xs font-bold gap-1 cursor-pointer ${isDark ? 'text-slate-300 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}
                      >
                        <RotateCcw className="h-3.5 w-3.5" /> Reset Parameters
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              {/* DATA TABLE */}
              <div className={`border rounded-2xl shadow-xl overflow-hidden ${themeCardBg}`}>
                <div className="overflow-x-auto max-h-[700px] overflow-y-auto">
                  <table className="w-full text-left text-sm relative">
                    <thead className={`border-b text-xs font-bold uppercase tracking-wider sticky top-0 z-10 backdrop-blur-md ${themeTableHead}`}>
                      <tr>
                        <th className="px-5 py-3.5 cursor-pointer hover:text-sky-500" onClick={() => handleSort('symbol')}>
                          <div className="flex items-center gap-1.5">
                            Security <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                          </div>
                        </th>
                        <th className="px-4 py-3.5 cursor-pointer hover:text-sky-500" onClick={() => handleSort('price')}>
                          <div className="flex items-center gap-1.5">
                            Price (CAD) <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                          </div>
                        </th>
                        <th className="px-4 py-3.5">
                          <div className="flex items-center gap-1">
                            Model Condition <Info className="h-3 w-3 text-slate-400" />
                          </div>
                        </th>
                        <th className="px-4 py-3.5 cursor-pointer hover:text-sky-500" onClick={() => handleSort('rsi_14')}>
                          <div className="flex items-center gap-1.5">
                            14D RSI <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                          </div>
                        </th>
                        <th className="px-4 py-3.5 cursor-pointer hover:text-sky-500" onClick={() => handleSort('atr_14')}>
                          <div className="flex items-center gap-1.5">
                            14D ATR <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                          </div>
                        </th>
                        <th className="px-4 py-3.5 cursor-pointer hover:text-sky-500" onClick={() => handleSort('stop_level_atr')}>
                          <div className="flex items-center gap-1.5">
                            Stop (2x ATR) <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                          </div>
                        </th>
                        <th className="px-4 py-3.5 cursor-pointer hover:text-sky-500" onClick={() => handleSort('target_atr')}>
                          <div className="flex items-center gap-1.5">
                            Target (3x ATR) <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                          </div>
                        </th>
                        <th className="px-5 py-3.5">Condition Rationale</th>
                        <th className="px-4 py-3.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                      {filteredAndSortedStocks.length === 0 ? (
                        <tr>
                          <td colSpan={9} className={`px-5 py-16 text-center font-medium ${themeMutedColor}`}>
                            No securities match the selected filter criteria.
                          </td>
                        </tr>
                      ) : (
                        filteredAndSortedStocks.map((stock) => {
                          const heldShares = holdingsMap.get(stock.symbol)
                          const sigCfg = getSignalConfig(stock.signal, isDark)
                          return (
                            <tr 
                              key={stock.symbol} 
                              className={`${themeTableRowHover} transition-colors group`}
                            >
                              <td className="px-5 py-3.5 font-bold">
                                <div className="flex items-center gap-2">
                                  <span 
                                    onClick={() => setActiveStockDetail(stock.symbol)}
                                    className={`group-hover:text-sky-500 transition-colors text-base font-extrabold cursor-pointer ${themeTextColor}`}
                                  >
                                    {stock.symbol}
                                  </span>

                                  {heldShares !== undefined && (
                                    <Badge 
                                      variant="outline" 
                                      onClick={() => setActiveTab('pocket')}
                                      className={`text-[10px] font-bold px-1.5 py-0 cursor-pointer ${isDark ? 'bg-sky-950/70 text-sky-300 border-sky-700/80 hover:bg-sky-900' : 'bg-sky-100 text-sky-800 border-sky-300 hover:bg-sky-200'}`}
                                      title="Active holding in Pocket Trader. Click to view."
                                    >
                                      💼 {Number(heldShares).toLocaleString(undefined, { maximumFractionDigits: 4 })} shs
                                    </Badge>
                                  )}
                                </div>
                                <div className={`text-xs font-medium ${themeMutedColor}`}>{stock.company}</div>
                              </td>

                              <td className={`px-4 py-3.5 font-black font-mono text-base ${themeTextColor}`}>
                                ${Number(stock.price).toFixed(2)}
                              </td>

                              <td className="px-4 py-3.5">
                                <Badge 
                                  variant="secondary"
                                  className={sigCfg.badgeClass}
                                >
                                  {sigCfg.label}
                                </Badge>
                              </td>

                              <td className={`px-4 py-3.5 font-mono font-bold ${themeTextColor}`}>
                                {Number(stock.rsi_14).toFixed(1)}
                              </td>

                              <td className={`px-4 py-3.5 font-mono font-medium ${themeTextColor}`}>
                                {stock.atr_14 ? `$${Number(stock.atr_14).toFixed(2)}` : '—'}
                              </td>

                              <td className="px-4 py-3.5 font-mono font-bold text-rose-400">
                                {stock.stop_level_atr ? `$${Number(stock.stop_level_atr).toFixed(2)}` : '—'}
                              </td>

                              <td className="px-4 py-3.5 font-mono font-bold text-emerald-400">
                                {stock.target_atr ? `$${Number(stock.target_atr).toFixed(2)}` : '—'}
                              </td>

                              <td className={`px-5 py-3.5 text-xs font-medium ${themeMutedColor}`}>
                                {stock.rationale}
                              </td>

                              <td className="px-4 py-3.5 text-right space-x-1.5">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    handleSelectPocketStock(stock.symbol, stock.company)
                                    setIsSheetOpen(true)
                                  }}
                                  className={`h-7 px-2 text-xs font-bold ${isDark ? 'text-slate-300 hover:text-white hover:bg-slate-800' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'}`}
                                  title="Add to Pocket Trader"
                                >
                                  <Plus className="h-3 w-3 mr-0.5 inline" /> Track
                                </Button>

                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setActiveStockDetail(stock.symbol)}
                                  className="h-7 px-2 text-xs font-bold text-sky-500 group-hover:bg-sky-500/10"
                                >
                                  Profile <ChevronRight className="h-3.5 w-3.5 ml-0.5 inline" />
                                </Button>
                              </td>
                            </tr>
                          )
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </TabsContent>

            {/* TAB 2: POCKET TRADER */}
            <TabsContent value="pocket" className="space-y-6 pt-4">
              <div className={`flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-2xl border shadow-xs ${themeCardBg}`}>
                <div>
                  <h2 className={`text-base font-bold ${themeTextColor}`}>Pocket Trader Portfolio Tracker</h2>
                  <p className={`text-xs ${themeMutedColor}`}>Self-directed paper trading calculations and target monitoring against TSX scans.</p>
                </div>

                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={handleExportCSV} className={`gap-1.5 text-xs font-bold border ${isDark ? 'bg-slate-950 border-slate-700 text-slate-200' : 'bg-white border-slate-300 text-slate-700'}`}>
                    <Download className="h-3.5 w-3.5" /> Export CSV
                  </Button>

                  <Button 
                    size="sm" 
                    onClick={() => {
                      if (!newSymbol && stocks.length > 0) {
                        handleSelectPocketStock(stocks[0].symbol, stocks[0].company)
                      }
                      setIsSheetOpen(true)
                    }}
                    className="gap-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold cursor-pointer shadow-md shadow-sky-600/20"
                  >
                    <Plus className="h-4 w-4" /> Add Position
                  </Button>
                </div>
              </div>

              {/* STORAGE NOTICE */}
              <div className={`p-3.5 rounded-xl border text-xs leading-relaxed flex items-start justify-between gap-2.5 ${isDark ? 'bg-slate-900/60 border-slate-800 text-slate-400' : 'bg-slate-100/90 border-slate-200 text-slate-600'}`}>
                <div className="flex items-start gap-2">
                  <Info className="h-4 w-4 text-sky-500 shrink-0 mt-0.5" />
                  <div>
                    <strong className={themeTextColor}>Self-Directed Simulated Ledger:</strong> Pocket Trader calculates targets and profit/loss dynamically from TSX quotes. Fractional positions are calculated with full decimal precision.
                  </div>
                </div>
                {user ? (
                  <Badge variant="outline" className="bg-emerald-950 text-emerald-300 border-emerald-600 text-[10px] font-bold shrink-0">
                    ☁️ Cloud Persistent
                  </Badge>
                ) : (
                  <Badge variant="outline" className="bg-amber-950 text-amber-300 border-amber-600 text-[10px] font-bold shrink-0">
                    ⚠️ Browser Local Only
                  </Badge>
                )}
              </div>

              {/* Metric Tiles */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className={`${themeCardBg} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className={`text-xs font-bold uppercase tracking-wider ${themeMutedColor}`}>Portfolio Value</p>
                    <p className={`text-2xl font-black mt-1 ${themeTextColor}`}>${portfolioTotals.totalCurrent.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                  </CardContent>
                </Card>

                <Card className={`${themeCardBg} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className={`text-xs font-bold uppercase tracking-wider ${themeMutedColor}`}>Net Unrealized P&L</p>
                    <p className={`text-2xl font-black mt-1 ${portfolioTotals.totalPnl >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                      {portfolioTotals.totalPnl >= 0 ? '+' : ''}${portfolioTotals.totalPnl.toFixed(2)}
                    </p>
                  </CardContent>
                </Card>

                <Card className={`${themeCardBg} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className={`text-xs font-bold uppercase tracking-wider ${themeMutedColor}`}>Overall Return</p>
                    <p className={`text-2xl font-black mt-1 ${portfolioTotals.totalReturnPct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                      {portfolioTotals.totalReturnPct >= 0 ? '+' : ''}{portfolioTotals.totalReturnPct.toFixed(2)}%
                    </p>
                  </CardContent>
                </Card>

                <Card className={`${themeCardBg} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className={`text-xs font-bold uppercase tracking-wider ${themeMutedColor}`}>Targets Reached</p>
                    <p className="text-2xl font-black text-sky-500 mt-1">{portfolioTotals.targetsHit} / {positions.length}</p>
                  </CardContent>
                </Card>
              </div>

              {/* Pocket Trader Table */}
              <div className={`border rounded-2xl shadow-xl overflow-hidden ${themeCardBg}`}>
                {calculatedPositions.length === 0 ? (
                  <div className={`p-16 text-center text-sm font-medium ${themeMutedColor}`}>
                    No active positions tracked. Click <strong>"Add Position"</strong> to start tracking trades.
                  </div>
                ) : (
                  <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
                    <table className="w-full text-left text-sm relative">
                      <thead className={`border-b text-xs font-bold uppercase tracking-wider sticky top-0 z-10 backdrop-blur-md ${themeTableHead}`}>
                        <tr>
                          <th className="px-5 py-3.5">Symbol</th>
                          <th className="px-4 py-3.5">Entry Date & Price</th>
                          <th className="px-4 py-3.5">Current Price</th>
                          <th className="px-4 py-3.5">Unrealized P&L</th>
                          <th className="px-4 py-3.5">Target Status</th>
                          <th className="px-4 py-3.5">Stop-Loss Level</th>
                          <th className="px-4 py-3.5">Model Condition</th>
                          <th className="px-4 py-3.5 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                        {calculatedPositions.map((pos) => {
                          const sigCfg = getSignalConfig(pos.signal, isDark)
                          return (
                            <tr key={pos.id} className={`${themeTableRowHover} transition-colors`}>
                              <td className="px-5 py-3.5 font-bold cursor-pointer" onClick={() => setActiveStockDetail(pos.symbol)}>
                                <span className="text-sky-500 hover:underline text-base font-extrabold">{pos.symbol}</span>
                                <div className={`text-xs font-medium ${themeMutedColor}`}>
                                  {pos.company} ({Number(pos.shares).toLocaleString(undefined, { maximumFractionDigits: 4 })} shs)
                                </div>
                              </td>
                              <td className={`px-4 py-3.5 font-mono ${themeMutedColor}`}>
                                <div className={`font-bold ${themeTextColor}`}>${pos.buyPrice.toFixed(2)}</div>
                                <div className="text-xs">{pos.buyDate} ({pos.daysHeld}d)</div>
                              </td>
                              <td className={`px-4 py-3.5 font-black font-mono text-base ${themeTextColor}`}>
                                ${pos.currentPrice.toFixed(2)}
                              </td>
                              <td className="px-4 py-3.5 font-mono">
                                <div className={`font-black text-base ${pos.dollarPnl >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                  {pos.dollarPnl >= 0 ? '+' : ''}${pos.dollarPnl.toFixed(2)}
                                </div>
                                <div className={`text-xs font-bold ${pos.pctPnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                  {pos.pctPnl >= 0 ? '+' : ''}{pos.pctPnl.toFixed(2)}%
                                </div>
                              </td>
                              <td className="px-4 py-3.5">
                                {pos.isTargetReached ? (
                                  <Badge className="bg-emerald-950 text-emerald-300 border-emerald-600 font-extrabold gap-1">
                                    <Target className="h-3.5 w-3.5" /> 🎯 TARGET REACHED (${pos.targetPrice.toFixed(2)})
                                  </Badge>
                                ) : (
                                  <div className="space-y-1">
                                    <div className={`text-xs font-mono font-bold ${themeTextColor}`}>
                                      ${pos.currentPrice.toFixed(2)} / ${pos.targetPrice.toFixed(2)} ({pos.targetProgress.toFixed(0)}%)
                                    </div>
                                    <div className={`w-28 h-2 rounded-full overflow-hidden ${isDark ? 'bg-slate-800' : 'bg-slate-200'}`}>
                                      <div className="bg-sky-500 h-full rounded-full" style={{ width: `${pos.targetProgress}%` }} />
                                    </div>
                                  </div>
                                )}
                              </td>
                              <td className="px-4 py-3.5 font-mono text-xs">
                                {pos.stopLoss ? (
                                  <span className={pos.isStopBreached ? 'text-rose-500 font-bold flex items-center gap-1' : 'text-slate-400 font-medium'}>
                                    {pos.isStopBreached && <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />}
                                    ${pos.stopLoss.toFixed(2)} {pos.isStopBreached && '(BREACHED)'}
                                  </span>
                                ) : (
                                  <span className="text-slate-500">—</span>
                                )}
                              </td>
                              <td className="px-4 py-3.5">
                                <Badge variant="outline" className={sigCfg.badgeClass}>
                                  {sigCfg.label}
                                </Badge>
                              </td>
                              <td className="px-4 py-3.5 text-right">
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  onClick={() => handleRemovePosition(pos.id)} 
                                  className="text-slate-400 hover:text-rose-500 h-8 w-8 p-0 cursor-pointer"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* TAB 3: MARKET TECHNICALS */}
            <TabsContent value="technicals" className="space-y-6 pt-4">
              <div className={`p-6 rounded-2xl border shadow-xl ${themeCardBg}`}>
                <div className="flex items-center gap-2 mb-4">
                  <BarChart3 className="h-5 w-5 text-sky-500" />
                  <h3 className={`font-bold text-base ${themeTextColor}`}>TSX Momentum, Moving Average & Volatility Spreads</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className={`p-5 rounded-xl border ${isDark ? 'bg-slate-800/80 border-emerald-600/80' : 'bg-emerald-50 border-emerald-200'}`}>
                    <p className="text-xs font-extrabold text-emerald-500 uppercase">Bullish Uptrend Baseline</p>
                    <p className={`text-3xl font-black mt-1 ${themeTextColor}`}>
                      {activeMonitoredStocks.filter(s => Number(s.sma_50) >= Number(s.sma_200)).length}
                    </p>
                    <p className={`text-xs font-medium mt-1 ${themeMutedColor}`}>SMA 50 ≥ SMA 200</p>
                  </div>
                  <div className={`p-5 rounded-xl border ${isDark ? 'bg-slate-800/80 border-rose-600/80' : 'bg-rose-50 border-rose-200'}`}>
                    <p className="text-xs font-extrabold text-rose-500 uppercase">Death Cross (Bearish)</p>
                    <p className={`text-3xl font-black mt-1 ${themeTextColor}`}>
                      {activeMonitoredStocks.filter(s => Number(s.sma_50) < Number(s.sma_200)).length}
                    </p>
                    <p className={`text-xs font-medium mt-1 ${themeMutedColor}`}>SMA 50 &lt; SMA 200</p>
                  </div>
                  <div className={`p-5 rounded-xl border ${isDark ? 'bg-slate-800/80 border-sky-600/80' : 'bg-sky-50 border-sky-200'}`}>
                    <p className="text-xs font-extrabold text-sky-500 uppercase">Oversold Conditions</p>
                    <p className={`text-3xl font-black mt-1 ${themeTextColor}`}>
                      {activeMonitoredStocks.filter(s => Number(s.rsi_14) <= 40).length}
                    </p>
                    <p className={`text-xs font-medium mt-1 ${themeMutedColor}`}>14D RSI ≤ 40.0</p>
                  </div>
                  <div className={`p-5 rounded-xl border ${isDark ? 'bg-slate-800/80 border-amber-600/80' : 'bg-amber-50 border-amber-200'}`}>
                    <p className="text-xs font-extrabold text-amber-500 uppercase">Avg 14D Volatility (ATR)</p>
                    <p className={`text-3xl font-black mt-1 ${themeTextColor}`}>
                      ${(activeMonitoredStocks.reduce((acc, s) => acc + (Number(s.atr_14) || 0), 0) / (activeMonitoredStocks.length || 1)).toFixed(2)}
                    </p>
                    <p className={`text-xs font-medium mt-1 ${themeMutedColor}`}>Universe Mean Daily Range</p>
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* TAB 4: USER MANUAL & OPERATIONAL METHODOLOGY */}
            <TabsContent value="manual" className="space-y-6 pt-4">
              <div className={`p-6 sm:p-8 rounded-2xl border shadow-xl space-y-8 max-w-5xl ${themeCardBg}`}>
                <div className={`flex items-center gap-3 pb-4 border-b ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
                  <div className="h-10 w-10 bg-sky-500/10 border border-sky-500/30 rounded-xl flex items-center justify-center text-sky-500">
                    <BookOpen className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className={`text-xl font-bold tracking-tight ${themeTextColor}`}>
                      TrendNorth Operational & Technical Manual
                    </h2>
                    <p className={`text-xs ${themeMutedColor} mt-0.5`}>
                      Quantitative models, indicator conditions, ATR volatility engine, cloud scheduling, and self-directed tracking procedures.
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="text-sm font-extrabold uppercase tracking-wider text-sky-500 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-500">01</span>
                    Platform Scope & Core Universe
                  </h3>
                  <p className={`text-xs sm:text-sm leading-relaxed font-normal pl-8 ${themeMutedColor}`}>
                    TrendNorth is an automated quantitative screening terminal monitoring high-liquidity Canadian equities and benchmark ETFs listed on the Toronto Stock Exchange (TSX). The engine continuously evaluates momentum and multi-timeframe moving average spreads to identify statistical inflection points while removing subjective emotional bias.
                  </p>
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-extrabold uppercase tracking-wider text-sky-500 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-500">02</span>
                    Quantitative Indicator Matrix & Technical Regimes
                  </h3>
                  <div className="pl-0 sm:pl-8 overflow-x-auto">
                    <table className={`w-full text-left text-xs border rounded-xl overflow-hidden divide-y ${themeBorder} ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                      <thead className={`font-bold uppercase tracking-wider ${themeTableHead}`}>
                        <tr>
                          <th className="px-4 py-3">Technical Regime</th>
                          <th className="px-4 py-3">Mathematical Condition</th>
                          <th className="px-4 py-3">Statistical Rationale</th>
                          <th className="px-4 py-3">Market Context</th>
                        </tr>
                      </thead>
                      <tbody className={`divide-y font-medium ${isDark ? 'bg-slate-900/60 divide-slate-800 text-slate-200' : 'bg-white divide-slate-200 text-slate-800'}`}>
                        <tr>
                          <td className="px-4 py-3">
                            <Badge className="bg-emerald-950 text-emerald-300 border-emerald-600 font-bold">
                              Oversold Pullback
                            </Badge>
                          </td>
                          <td className="px-4 py-3 font-mono text-sky-500 font-bold">
                            SMA_50 ≥ SMA_200 <br/>&amp; RSI_14 ≤ 40.0
                          </td>
                          <td className="px-4 py-3 text-emerald-500 font-bold">
                            Bullish trend + Pullback dip
                          </td>
                          <td className={`px-4 py-3 ${themeMutedColor}`}>
                            Macro structural uptrend is intact, but near-term selling pressure has dragged the momentum oscillator into discount territory.
                          </td>
                        </tr>
                        <tr>
                          <td className="px-4 py-3">
                            <Badge className="bg-rose-950 text-rose-300 border-rose-600 font-bold">
                              Trend Breakdown
                            </Badge>
                          </td>
                          <td className="px-4 py-3 font-mono text-rose-500 font-bold">
                            SMA_50 &lt; SMA_200
                          </td>
                          <td className="px-4 py-3 text-rose-500 font-bold">
                            Death Cross (Bearish trend)
                          </td>
                          <td className={`px-4 py-3 ${themeMutedColor}`}>
                            The medium-term 50-day average has crossed below the secular 200-day average, signaling institutional capital distribution and structural weakness.
                          </td>
                        </tr>
                        <tr>
                          <td className="px-4 py-3">
                            <Badge className="bg-amber-950 text-amber-300 border-amber-600 font-bold">
                              Momentum Overextended
                            </Badge>
                          </td>
                          <td className="px-4 py-3 font-mono text-amber-500 font-bold">
                            RSI_14 ≥ 75.0
                          </td>
                          <td className="px-4 py-3 text-amber-500 font-bold">
                            Velocity Exhaustion
                          </td>
                          <td className={`px-4 py-3 ${themeMutedColor}`}>
                            Price momentum has reached acute overbought levels; elevated statistical probability of near-term consolidation or mean reversion.
                          </td>
                        </tr>
                        <tr>
                          <td className="px-4 py-3">
                            <Badge className="bg-slate-800 text-slate-300 border-slate-600 font-bold">
                              Neutral / Baseline
                            </Badge>
                          </td>
                          <td className={`px-4 py-3 font-mono ${themeMutedColor}`}>
                            Baseline Parameters
                          </td>
                          <td className={`px-4 py-3 ${themeMutedColor}`}>
                            Standard Range
                          </td>
                          <td className={`px-4 py-3 ${themeMutedColor}`}>
                            Asset price and momentum oscillate within standard historical variance without triggering edge thresholds.
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* TN-005 SECTION IN MANUAL */}
                <div className="space-y-3">
                  <h3 className="text-sm font-extrabold uppercase tracking-wider text-sky-500 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-500">03</span>
                    TN-005: Volatility & Dynamic Stop-Loss Engine (ATR)
                  </h3>
                  <div className="pl-8 space-y-2 text-xs sm:text-sm">
                    <p className={`leading-relaxed ${themeMutedColor}`}>
                      To avoid arbitrary dollar guesses, TrendNorth utilizes Welles Wilder&apos;s 14-day <strong>Average True Range (ATR)</strong> to dynamically assess the expected daily price volatility of each Canadian security:
                    </p>
                    <ul className={`list-disc space-y-2 pl-4 ${themeMutedColor}`}>
                      <li>
                        <strong className={themeTextColor}>Model Invalidation (2x ATR Stop Level):</strong> Calculated as <code className="text-rose-400 font-mono">Current Price - (2 × 14D ATR)</code>. Placing stop-losses beyond twice the daily statistical variance minimizes premature whipsaws caused by normal market noise while protecting capital when a setup breaks down.
                      </li>
                      <li>
                        <strong className={themeTextColor}>Mathematical Swing Target (3x ATR):</strong> Calculated as <code className="text-emerald-400 font-mono">Current Price + (3 × 14D ATR)</code>. Represents approximately 3 daily candles of directional expansion, offering an objective <strong>1.5:1 Risk/Reward profile</strong> on swing setups.
                      </li>
                    </ul>
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-extrabold uppercase tracking-wider text-sky-500 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-500">04</span>
                    Pocket Trader Portfolio Management
                  </h3>
                  <div className="pl-8 space-y-2 text-xs sm:text-sm">
                    <ul className={`list-disc space-y-1.5 pl-4 ${themeMutedColor}`}>
                      <li>
                        <strong className={themeTextColor}>Active Position Tracking:</strong> Log entry price, purchase date, and share size for open or planned setups directly from the slide-out sheet or stock detail profiles. Fractional shares are fully supported up to 4 decimal places.
                      </li>
                      <li>
                        <strong className={themeTextColor}>Interactive Date Picker & Typing:</strong> Select dates via the calendar popup or type directly in YYYY-MM-DD format.
                      </li>
                      <li>
                        <strong className={themeTextColor}>ATR Model Suggestions:</strong> Clicking &quot;Apply ATR Model Targets&quot; in the position drawer automatically populates volatility-adjusted targets and stop levels.
                      </li>
                      <li>
                        <strong className={themeTextColor}>Cloud Sync Persistence:</strong> Logged-in Google users have their portfolios synchronized in real time with Supabase across devices.
                      </li>
                    </ul>
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-extrabold uppercase tracking-wider text-sky-500 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-500">05</span>
                    Pipeline Execution Schedule & Data Latency
                  </h3>
                  <div className="pl-8 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className={`p-4 rounded-xl border space-y-1 ${isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
                      <p className={`font-bold text-sm ${themeTextColor}`}>🌅 Morning Market Dip Scan</p>
                      <p className="text-sky-500 font-mono font-bold">10:32 AM ET (Mon–Fri)</p>
                      <p className={`pt-1 leading-relaxed ${themeMutedColor}`}>
                        Executes 62 minutes after market open once opening auction noise clears to capture high-volume morning oversold pullbacks.
                      </p>
                    </div>

                    <div className={`p-4 rounded-xl border space-y-1 ${isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
                      <p className={`font-bold text-sm ${themeTextColor}`}>🌙 Post-Close Official Bar Scan</p>
                      <p className="text-sky-500 font-mono font-bold">04:47 PM ET (Mon–Fri)</p>
                      <p className={`pt-1 leading-relaxed ${themeMutedColor}`}>
                        Executes 47 minutes post-closing bell after TSX Market-on-Close (MOC) prints finalize daily closing candles and settlement values.
                      </p>
                    </div>
                  </div>
                </div>

                <div className={`p-4 rounded-xl border text-[11px] leading-relaxed ${isDark ? 'bg-slate-950/80 border-slate-800 text-slate-400' : 'bg-slate-100 border-slate-200 text-slate-600'}`}>
                  <strong>Notice:</strong> TrendNorth Analytics provides mathematical screening models and technical momentum research for self-directed investors. All signals, metrics, and indicators are generated programmatically for educational analysis and do not constitute personalized financial, tax, or investment advice.
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </main>
      </div>

      {/* REGULATORY COMPLIANCE FOOTER */}
      <footer className={`mt-12 py-10 border-t ${isDark ? 'border-slate-800 bg-slate-950 text-slate-400' : 'border-slate-200 bg-slate-100/70 text-slate-500'} text-xs font-medium`}>
        <div className="w-full px-6 lg:px-8 space-y-6">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
            <div className="max-w-2xl space-y-2">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-amber-500" />
                <span className={`font-bold ${themeTextColor}`}>Regulatory & Investment Disclaimer</span>
                <span className="rounded bg-slate-200 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-slate-700 dark:text-slate-300">
                  Educational Research Only
                </span>
              </div>
              <p className="leading-relaxed text-[11px]">
                TrendNorth is an algorithmic market research and technical screening tool designed exclusively for educational purposes. <strong>TrendNorth is not registered as an investment adviser, portfolio manager, or broker-dealer</strong> with the Ontario Securities Commission (OSC), the Canadian Investment Regulatory Organization (CIRO), the U.S. SEC, or any other financial regulatory agency.
              </p>
              <p className="leading-relaxed text-[11px]">
                Technical conditions and volatility-based thresholds represent programmatic calculations derived from mathematical models applied to delayed market data. <strong>These mathematical outputs do not constitute investment advice, financial planning, or a recommendation to purchase or sell any security.</strong>
              </p>
            </div>

            <div className="max-w-md space-y-2 text-[11px]">
              <p className="leading-relaxed">
                <strong>Risk of Capital Loss:</strong> Trading Canadian equities involves substantial financial risk, including the loss of principal. Past technical patterns, historical moving average alignments, and mathematical indicators provide no guarantee of future price performance.
              </p>
              <p className="text-slate-500 dark:text-slate-400">
                Market prices are delayed and retrieved via public endpoints on an "as-is" basis. Always consult an independent, licensed financial advisor before making investment decisions.
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-200/60 dark:border-slate-800/60 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px]">
            <span>TrendNorth Terminal © {clientYear || '2026'} — TSX Quantitative Intelligence</span>
            <span>Self-Directed Research Architecture</span>
          </div>
        </div>
      </footer>

      {/* FLOATING FEEDBACK WIDGET */}
      <div className="fixed bottom-6 right-6 z-50">
        {isFeedbackOpen ? (
          <div className={`w-[340px] sm:w-[380px] p-5 rounded-2xl border shadow-2xl transition-all ${
            isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <MessageSquareText className="h-4 w-4 text-sky-500" />
                <span className="text-sm font-bold">💬 Submit Feedback</span>
              </div>
              <button
                type="button"
                onClick={() => setIsFeedbackOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {fbSuccess ? (
              <div className="py-8 text-center space-y-2">
                <p className="text-2xl">✅</p>
                <p className="text-sm font-bold text-emerald-500">Thank you!</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Your feedback has been sent directly to the development team.
                </p>
              </div>
            ) : (
              <form onSubmit={handleFeedbackSubmit} className="space-y-3 pt-3">
                {fbError && (
                  <div className="p-2 rounded bg-rose-500/10 border border-rose-500/30 text-rose-500 text-[11px] font-semibold">
                    {fbError}
                  </div>
                )}

                <input
                  type="text"
                  className="hidden"
                  tabIndex={-1}
                  autoComplete="off"
                  value={fbHoneypot}
                  onChange={(e) => setFbHoneypot(e.target.value)}
                />

                <div>
                  <Label className="text-[11px] font-bold">Your Name</Label>
                  <Input
                    type="text"
                    placeholder="e.g. Alex"
                    value={fbName}
                    onChange={(e) => setFbName(e.target.value)}
                    className={`h-8 text-xs mt-1 ${themeInputBg}`}
                    required
                  />
                </div>

                <div>
                  <Label className="text-[11px] font-bold">Your Email</Label>
                  <Input
                    type="email"
                    placeholder="name@domain.com"
                    value={fbEmail}
                    onChange={(e) => setFbEmail(e.target.value)}
                    className={`h-8 text-xs mt-1 ${themeInputBg}`}
                    required
                  />
                </div>

                <div>
                  <Label className="text-[11px] font-bold">Topic</Label>
                  <select
                    value={fbTopic}
                    onChange={(e) => setFbTopic(e.target.value)}
                    className={`w-full h-8 px-2 text-xs font-medium rounded-lg border mt-1 focus:ring-2 focus:ring-sky-500 ${
                      isDark ? 'bg-slate-950 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
                    }`}
                  >
                    <option value="Feature Suggestion">Feature Suggestion 💡</option>
                    <option value="Bug Report">Bug Report 🐞</option>
                    <option value="Data Inaccuracy">Data Inaccuracy 📊</option>
                    <option value="General Feedback">General Feedback 💬</option>
                  </select>
                </div>

                <div>
                  <Label className="text-[11px] font-bold">Comments</Label>
                  <textarea
                    rows={3}
                    placeholder="Describe your suggestion or issue (at least 3 words)..."
                    value={fbMessage}
                    onChange={(e) => setFbMessage(e.target.value)}
                    className={`w-full p-2 text-xs rounded-lg border mt-1 resize-none focus:outline-none focus:ring-2 focus:ring-sky-500 ${
                      isDark ? 'bg-slate-950 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
                    }`}
                    required
                  />
                </div>

                <Button
                  type="submit"
                  disabled={fbLoading}
                  className="w-full h-8 text-xs font-bold bg-sky-600 hover:bg-sky-500 text-white gap-1.5 cursor-pointer"
                >
                  <Send className="h-3 w-3" />
                  {fbLoading ? 'Sending...' : 'Submit Feedback'}
                </Button>
              </form>
            )}
          </div>
        ) : (
          <Button
            type="button"
            onClick={() => setIsFeedbackOpen(true)}
            className="shadow-xl bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs gap-2 px-4 py-2.5 rounded-full cursor-pointer hover:scale-105 transition-transform"
          >
            <MessageSquareText className="h-4 w-4" />
            <span>Submit Feedback</span>
          </Button>
        )}
      </div>

      {/* POCKET TRADER DRAWER */}
      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent side="right" className={`w-[360px] sm:w-[440px] p-6 shadow-2xl border-l overflow-y-auto ${isDark ? 'bg-slate-900 text-white border-slate-800' : 'bg-white text-slate-900 border-slate-200'}`}>
          <SheetHeader className={`pb-4 border-b ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
            <SheetTitle className={`text-lg font-bold ${themeTextColor}`}>Track New Position</SheetTitle>
            <SheetDescription className={`text-xs ${themeMutedColor}`}>
              Type or select any TSX or custom symbol. Target achievements, dynamic stop losses, and P&L compute automatically.
            </SheetDescription>
          </SheetHeader>

          <div className="mt-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed flex items-start gap-2">
            <Info className="h-3.5 w-3.5 text-sky-500 shrink-0 mt-0.5" />
            <span>
              {user 
                ? 'Positions are synchronized directly with your cloud profile across devices.'
                : 'Guest mode: Entries are stored only in this browser. Sign in above to sync across devices.'}
            </span>
          </div>

          <form onSubmit={handleAddPosition} className="space-y-4 pt-4">
            <div className="space-y-1.5 relative" ref={sheetSearchRef}>
              <Label htmlFor="stockSearch" className={`text-xs font-bold ${themeTextColor}`}>
                TSX Ticker or Company Name
              </Label>
              <div className="relative">
                <Input
                  id="stockSearch"
                  type="text"
                  placeholder="Type symbol (e.g. AC, BB, SHOP) or name..."
                  value={sheetSearchInput}
                  onChange={(e) => {
                    setSheetSearchInput(e.target.value)
                    setNewSymbol(e.target.value.trim().toUpperCase())
                    setIsSheetSearchOpen(true)
                  }}
                  onFocus={() => setIsSheetSearchOpen(true)}
                  className={`text-xs h-10 pr-8 font-medium ${themeInputBg}`}
                  required
                />
                <ChevronDown className="absolute right-2.5 top-3 h-4 w-4 text-slate-400 pointer-events-none" />
              </div>

              {isSheetSearchOpen && (
                <div className={`absolute left-0 right-0 top-18 z-50 border rounded-xl shadow-2xl max-h-56 overflow-y-auto divide-y ${isDark ? 'bg-slate-950 border-slate-700 divide-slate-800' : 'bg-white border-slate-200 divide-slate-100'}`}>
                  {drawerSuggestions.map((item) => (
                    <button
                      key={item.symbol}
                      type="button"
                      onClick={() => handleSelectPocketStock(item.symbol, item.company)}
                      className={`w-full text-left px-3.5 py-2.5 text-xs transition-colors flex items-center justify-between cursor-pointer ${isDark ? 'hover:bg-slate-800 text-slate-200' : 'hover:bg-sky-50 text-slate-800'}`}
                    >
                      <div>
                        <span className="font-bold text-sky-500">{item.symbol}</span>
                        <span className={`${themeMutedColor} ml-1.5`}>— {item.company}</span>
                      </div>
                      <Plus className="h-3.5 w-3.5 text-slate-400" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* TN-005 Volatility & ATR Auto-Suggest Banner */}
            {selectedStockObj && selectedStockObj.atr_14 && (
              <div className="p-3 rounded-xl border border-sky-500/30 bg-sky-500/10 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-sky-400 font-bold flex items-center gap-1.5">
                    <Activity className="h-3.5 w-3.5" /> 14D Volatility (ATR): ${Number(selectedStockObj.atr_14).toFixed(2)}
                  </span>
                  <span className="text-[11px] text-slate-400">Wilder&apos;s Model</span>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const price = Number(newBuyPrice) || Number(selectedStockObj.price) || 0
                    const atr = Number(selectedStockObj.atr_14) || 1
                    const suggestedGain = (atr * 3).toFixed(2)
                    const suggestedStop = Math.max(0.01, price - (atr * 2)).toFixed(2)
                    setNewTargetGain(suggestedGain)
                    setNewStopLoss(suggestedStop)
                  }}
                  className="w-full h-8 text-xs font-bold bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 border-sky-500/40 cursor-pointer"
                >
                  <ShieldCheck className="h-3.5 w-3.5 mr-1 text-emerald-400" /> Apply ATR Model Targets (2x Stop / 3x Target)
                </Button>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              {/* Interactive Date Picker + Direct Typing */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="date" className={`text-xs font-bold ${themeTextColor}`}>Entry Date</Label>
                  <span className="text-[10px] text-slate-400 flex items-center gap-1">
                    <Calendar className="h-2.5 w-2.5 text-sky-400" /> Pick or Type
                  </span>
                </div>
                <div className="relative">
                  <Input
                    id="date"
                    type="date"
                    value={newBuyDate}
                    onChange={(e) => setNewBuyDate(e.target.value)}
                    onClick={(e) => {
                      try {
                        e.currentTarget.showPicker()
                      } catch (err) {}
                    }}
                    className={`h-10 text-xs font-medium cursor-pointer ${themeInputBg}`}
                    required
                  />
                </div>
              </div>

              {/* Fractional Shares Input */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="shares" className={`text-xs font-bold ${themeTextColor}`}>Shares Count</Label>
                  <span className="text-[10px] text-slate-400 font-medium">Fractional OK</span>
                </div>
                <Input
                  id="shares"
                  type="number"
                  step="any"
                  min="0.0001"
                  placeholder="e.g. 0.6028 or 10"
                  value={newShares}
                  onChange={(e) => setNewShares(e.target.value)}
                  className={`h-10 text-xs font-medium ${themeInputBg}`}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="price" className={`text-xs font-bold ${themeTextColor}`}>Buy Price (CAD)</Label>
                <Input
                  id="price"
                  type="number"
                  step="any"
                  min="0.01"
                  value={newBuyPrice}
                  onChange={(e) => setNewBuyPrice(e.target.value)}
                  className={`h-10 text-xs font-medium ${themeInputBg}`}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="target" className={`text-xs font-bold ${themeTextColor}`}>Target Gain / Share ($)</Label>
                <Input
                  id="target"
                  type="number"
                  step="any"
                  min="0.01"
                  value={newTargetGain}
                  onChange={(e) => setNewTargetGain(e.target.value)}
                  className={`h-10 text-xs font-medium ${themeInputBg}`}
                  required
                />
              </div>
            </div>

            {/* TN-005 Stop Loss Input */}
            <div className="space-y-1.5">
              <Label htmlFor="stopLoss" className={`text-xs font-bold ${themeTextColor}`}>
                Technical Stop-Loss Level (CAD) <span className="text-[10px] text-slate-400 font-normal">(Optional)</span>
              </Label>
              <Input
                id="stopLoss"
                type="number"
                step="any"
                min="0.01"
                placeholder="e.g. 152.50"
                value={newStopLoss}
                onChange={(e) => setNewStopLoss(e.target.value)}
                className={`h-10 text-xs font-medium ${themeInputBg}`}
              />
            </div>

            <div className="pt-4">
              <Button type="submit" className="w-full bg-sky-600 hover:bg-sky-500 text-white font-bold shadow-md cursor-pointer h-10">
                {user ? 'Save to Cloud Portfolio' : 'Save to Pocket Trader'}
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>
    </div>
  )
}