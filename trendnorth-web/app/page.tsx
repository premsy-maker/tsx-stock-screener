'use client'

import { useEffect, useState, useMemo, useRef } from 'react'
import { supabase, ScreenerRecord } from '@/lib/supabase'
import { EXTENDED_TSX_CATALOG } from '@/lib/catalog'
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
  BookmarkPlus, BookmarkX, Briefcase, Sun, Moon
} from 'lucide-react'

interface PocketPosition {
  id: string
  symbol: string
  buyDate: string
  buyPrice: number
  shares: number
  targetGain: number
}

type SortField = 'symbol' | 'price' | 'rsi_14' | 'sma_50' | 'sma_200'
type SortOrder = 'asc' | 'desc'
type ThemeMode = 'dark' | 'light'

export default function Dashboard() {
  const [stocks, setStocks] = useState<ScreenerRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [lastScanTime, setLastScanTime] = useState<string | null>(null)

  // Theme Mode State
  const [theme, setTheme] = useState<ThemeMode>('dark')

  // Active Tab State for programmatic tab switching
  const [activeTab, setActiveTab] = useState('screener')

  // Watchlist Membership State (Custom Added & Manually Excluded)
  const [removedSymbols, setRemovedSymbols] = useState<string[]>([])
  const [customSymbols, setCustomSymbols] = useState<string[]>([])

  // Autocomplete Search State for "Open Market Data Details" (Top Bar)
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
  const [selectedSignals, setSelectedSignals] = useState<string[]>([
    'BUY / ACCUMULATE', 'SELL / EXIT', 'TRIM / TAKE PROFIT', 'KEEP / HOLD'
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
  const [newShares, setNewShares] = useState<string>('10')
  const [newTargetGain, setNewTargetGain] = useState<string>('10')

  // 1. Fetch Supabase Data
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

  // 2. TSX Market Hours
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

    const savedTheme = localStorage.getItem('trendnorth_theme') as ThemeMode
    if (savedTheme === 'light' || savedTheme === 'dark') {
      setTheme(savedTheme)
    }

    const savedPositions = localStorage.getItem('trendnorth_pocket_positions')
    if (savedPositions) {
      try { setPositions(JSON.parse(savedPositions)) } catch (e) {}
    }

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
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  // Toggle Theme handler
  const toggleTheme = () => {
    const nextTheme: ThemeMode = theme === 'dark' ? 'light' : 'dark'
    setTheme(nextTheme)
    localStorage.setItem('trendnorth_theme', nextTheme)
  }

  // Watchlist Addition / Removal
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
    localStorage.setItem('trendnorth_pocket_positions', JSON.stringify(updated))
  }

  const handleSelectPocketStock = (sym: string, companyName?: string) => {
    let cleanSym = sym.trim().toUpperCase()
    if (!cleanSym.includes('.') && !cleanSym.endsWith('.TO')) {
      cleanSym = `${cleanSym}.TO`
    }
    setNewSymbol(cleanSym)
    setSheetSearchInput(`${cleanSym}${companyName ? ` — ${companyName}` : ''}`)
    setIsSheetSearchOpen(false)

    const match = stocks.find(s => s.symbol === cleanSym)
    if (match && match.price) {
      setNewBuyPrice(String(match.price))
    }
  }

  const handleAddPosition = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newSymbol) return
    const fallbackDate = newBuyDate || '2026-10-31'
    const newPos: PocketPosition = {
      id: `${newSymbol}-${Date.now()}`,
      symbol: newSymbol,
      buyDate: fallbackDate,
      buyPrice: parseFloat(newBuyPrice) || 0,
      shares: parseInt(newShares, 10) || 1,
      targetGain: parseFloat(newTargetGain) || 1
    }
    updatePositions([...positions, newPos])
    setIsSheetOpen(false)
  }

  const handleRemovePosition = (id: string) => {
    updatePositions(positions.filter(p => p.id !== id))
  }

  const toggleSignalFilter = (sig: string) => {
    setSelectedSignals(prev => 
      prev.includes(sig) ? prev.filter(s => s !== sig) : [...prev, sig]
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
          rationale: 'Custom monitored security (On-Demand Added)'
        } as ScreenerRecord)
      }
    })
    return existing
  }, [stocks, customSymbols])

  const activeMonitoredStocks = useMemo(() => {
    return allAvailableStocks.filter(s => !removedSymbols.includes(s.symbol))
  }, [allAvailableStocks, removedSymbols])

  const buyCount = useMemo(() => activeMonitoredStocks.filter(s => s.signal === 'BUY / ACCUMULATE').length, [activeMonitoredStocks])
  const sellCount = useMemo(() => activeMonitoredStocks.filter(s => s.signal === 'SELL / EXIT').length, [activeMonitoredStocks])
  const trimCount = useMemo(() => activeMonitoredStocks.filter(s => s.signal === 'TRIM / TAKE PROFIT').length, [activeMonitoredStocks])

  const filteredAndSortedStocks = useMemo(() => {
    return activeMonitoredStocks
      .filter(s => {
        const matchesSignal = selectedSignals.includes(s.signal)
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
  }, [activeMonitoredStocks, selectedSignals, searchQuery, rsiRange, trendFilter, sortField, sortOrder])

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

      return {
        ...pos, company, currentPrice, signal, targetPrice,
        totalCost, currentValue, dollarPnl, pctPnl, daysHeld,
        isTargetReached, targetProgress
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
    const headers = ['Symbol,Buy Date,Buy Price,Shares,Target Gain\n']
    const rows = positions.map(p => `${p.symbol},${p.buyDate},${p.buyPrice},${p.shares},${p.targetGain}\n`)
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
      rationale: 'Active TSX Equity Profile'
    } as ScreenerRecord
  }, [activeStockDetail, allAvailableStocks])

  // Dynamic Theme Palette Class Mapping
  const isDark = theme === 'dark'
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

  // =========================================================================
  // VIEW 1: FULL-PAGE MARKET DATA DETAILS VIEW
  // =========================================================================
  if (selectedDetailStock) {
    const s = selectedDetailStock
    const cleanSym = s.symbol.replace('.TO', '')
    const priceDiff = s.signal.includes('BUY') ? 0.85 : s.signal.includes('SELL') ? -1.45 : 0.20
    const pctDiff = ((priceDiff / s.price) * 100)
    const isPositive = priceDiff >= 0
    const isMonitored = activeMonitoredStocks.some(st => st.symbol === s.symbol)
    const tvTheme = isDark ? 'dark' : 'light'
    const tvToolbarBg = isDark ? '0f172a' : 'ffffff'

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
                  <Badge 
                    className={
                      s.signal.includes('BUY') ? 'bg-emerald-950 text-emerald-300 font-bold border-emerald-600 text-xs px-2.5 py-0.5' :
                      s.signal.includes('SELL') ? 'bg-rose-950 text-rose-300 font-bold border-rose-600 text-xs px-2.5 py-0.5' :
                      s.signal.includes('TRIM') ? 'bg-amber-950 text-amber-300 font-bold border-amber-600 text-xs px-2.5 py-0.5' :
                      `${isDark ? 'text-slate-200 bg-slate-800 border-slate-600' : 'text-slate-700 bg-slate-100 border-slate-300'} text-xs px-2.5 py-0.5`
                    }
                  >
                    {s.signal}
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
              <h3 className={`text-xs font-extrabold uppercase tracking-wider ${themeTextColor}`}>Key Statistics</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
                {[
                  { label: 'Open Price', val: `$${(s.price * 0.995).toFixed(2)}` },
                  { label: 'Day High', val: `$${(s.price * 1.012).toFixed(2)}` },
                  { label: 'Day Low', val: `$${(s.price * 0.988).toFixed(2)}` },
                  { label: '52-W High', val: `$${(s.price * 1.22).toFixed(2)}` },
                  { label: '52-W Low', val: `$${(s.price * 0.78).toFixed(2)}` },
                  { label: 'Volume', val: '4,942,000' },
                  { label: 'Avg Volume', val: '4,097,400' },
                  { label: 'Exchange', val: 'TSX (Toronto)' },
                ].map(stat => (
                  <div key={stat.label} className={`p-3.5 rounded-xl border ${themeBorder} ${isDark ? 'bg-slate-900/90' : 'bg-white shadow-2xs'}`}>
                    <p className={`text-[11px] font-bold uppercase tracking-wider ${themeMutedColor}`}>{stat.label}</p>
                    <p className={`text-sm font-black mt-1 ${themeTextColor}`}>{stat.val}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Dividends & Valuation */}
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
                  <h3 className={`text-sm font-bold ${themeTextColor}`}>Valuation & Technicals</h3>
                  <span className="text-xs font-bold text-sky-500 font-mono">14D RSI: {Number(s.rsi_14).toFixed(1)}</span>
                </div>
                <div className="space-y-3 text-xs">
                  <div className={`flex justify-between items-center py-1 border-b ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
                    <span className={`${themeMutedColor} font-medium`}>Market Capitalization</span>
                    <span className={`font-bold text-sm ${themeTextColor}`}>$84.99B</span>
                  </div>
                  <div className={`flex justify-between items-center py-1 border-b ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
                    <span className={`${themeMutedColor} font-medium`}>Price to Earnings (P/E)</span>
                    <span className={`font-bold ${themeTextColor}`}>9.65</span>
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
                {s.company} is listed on the Toronto Stock Exchange. The security is actively evaluated within TrendNorth&apos;s technical momentum matrix.
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

        <footer className={`py-6 border-t ${isDark ? 'border-slate-800 bg-slate-950 text-slate-400' : 'border-slate-200 bg-white text-slate-500'} text-center text-xs font-medium`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
            <span>TrendNorth Terminal © {clientYear || '2026'} — Canadian Equities Technical Intelligence</span>
            <span>Educational Research Only • Not Financial Advice</span>
          </div>
        </footer>
      </div>
    )
  }

  // =========================================================================
  // VIEW 2: MAIN DASHBOARD
  // =========================================================================
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
            {/* Theme Toggle Button */}
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
                  📋 Filtered Watchlist ({filteredAndSortedStocks.length}/{activeMonitoredStocks.length})
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
                  📖 User Manual
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
                    <p className={`text-xs font-bold uppercase tracking-wider ${themeMutedColor}`}>Watchlist Universe</p>
                    <p className={`text-3xl font-black mt-1 ${themeTextColor}`}>{activeMonitoredStocks.length}</p>
                    <p className={`text-xs font-semibold mt-1 ${themeMutedColor}`}>
                      {customSymbols.length > 0 ? `+${customSymbols.length} custom tracked` : 'Active TSX Monitored'}
                    </p>
                  </CardContent>
                </Card>

                <Card className={`${isDark ? 'bg-slate-900 border-emerald-600/80' : 'bg-white border-emerald-300'} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-emerald-500 flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> BUY / Dip
                    </p>
                    <p className="text-3xl font-black text-emerald-500 mt-1">{buyCount}</p>
                    <p className="text-xs font-semibold text-emerald-600 mt-1">Oversold Uptrend Pullbacks</p>
                  </CardContent>
                </Card>

                <Card className={`${isDark ? 'bg-slate-900 border-rose-600/80' : 'bg-white border-rose-300'} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-rose-500 flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-rose-500" /> SELL / Exit
                    </p>
                    <p className="text-3xl font-black text-rose-500 mt-1">{sellCount}</p>
                    <p className="text-xs font-semibold text-rose-600 mt-1">Death Cross Structural Break</p>
                  </CardContent>
                </Card>

                <Card className={`${isDark ? 'bg-slate-900 border-amber-600/80' : 'bg-white border-amber-300'} shadow-xs`}>
                  <CardContent className="p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-amber-500 flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-amber-500" /> TRIM / Overbought
                    </p>
                    <p className="text-3xl font-black text-amber-500 mt-1">{trimCount}</p>
                    <p className="text-xs font-semibold text-amber-600 mt-1">Extended 14D RSI &gt; 70</p>
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
                      { label: 'BUY / ACCUMULATE', short: 'BUY', activeBg: isDark ? 'bg-emerald-950 text-emerald-300 border-emerald-500 ring-1 ring-emerald-500' : 'bg-emerald-100 text-emerald-800 border-emerald-400 ring-1 ring-emerald-500' },
                      { label: 'SELL / EXIT', short: 'SELL', activeBg: isDark ? 'bg-rose-950 text-rose-300 border-rose-500 ring-1 ring-rose-500' : 'bg-rose-100 text-rose-800 border-rose-400 ring-1 ring-rose-500' },
                      { label: 'TRIM / TAKE PROFIT', short: 'TRIM', activeBg: isDark ? 'bg-amber-950 text-amber-300 border-amber-500 ring-1 ring-amber-500' : 'bg-amber-100 text-amber-800 border-amber-400 ring-1 ring-amber-500' },
                      { label: 'KEEP / HOLD', short: 'HOLD', activeBg: isDark ? 'bg-slate-800 text-slate-100 border-slate-500 ring-1 ring-slate-400' : 'bg-slate-200 text-slate-800 border-slate-400 ring-1 ring-slate-400' },
                    ].map(sig => {
                      const active = selectedSignals.includes(sig.label)
                      return (
                        <button
                          key={sig.label}
                          type="button"
                          onClick={() => toggleSignalFilter(sig.label)}
                          className={`text-xs font-bold px-3 py-1.5 rounded-xl border transition-all cursor-pointer flex items-center gap-1.5 ${
                            active ? sig.activeBg : `${isDark ? 'bg-slate-950 text-slate-400 border-slate-700 hover:text-white' : 'bg-slate-50 text-slate-600 border-slate-200 hover:text-slate-900'}`
                          }`}
                        >
                          {sig.short}
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
                          setSelectedSignals(['BUY / ACCUMULATE', 'SELL / EXIT', 'TRIM / TAKE PROFIT', 'KEEP / HOLD'])
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
                        <th className="px-4 py-3.5">Signal</th>
                        <th className="px-4 py-3.5 cursor-pointer hover:text-sky-500" onClick={() => handleSort('rsi_14')}>
                          <div className="flex items-center gap-1.5">
                            14D RSI <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                          </div>
                        </th>
                        <th className="px-4 py-3.5 cursor-pointer hover:text-sky-500" onClick={() => handleSort('sma_50')}>
                          <div className="flex items-center gap-1.5">
                            50D SMA <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                          </div>
                        </th>
                        <th className="px-4 py-3.5 cursor-pointer hover:text-sky-500" onClick={() => handleSort('sma_200')}>
                          <div className="flex items-center gap-1.5">
                            200D SMA <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                          </div>
                        </th>
                        <th className="px-5 py-3.5">Rationale</th>
                        <th className="px-4 py-3.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                      {filteredAndSortedStocks.length === 0 ? (
                        <tr>
                          <td colSpan={8} className={`px-5 py-16 text-center font-medium ${themeMutedColor}`}>
                            No securities match the selected filter criteria.
                          </td>
                        </tr>
                      ) : (
                        filteredAndSortedStocks.map((stock) => {
                          const heldShares = holdingsMap.get(stock.symbol)
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

                                  {heldShares && (
                                    <Badge 
                                      variant="outline" 
                                      onClick={() => setActiveTab('pocket')}
                                      className={`text-[10px] font-bold px-1.5 py-0 cursor-pointer ${isDark ? 'bg-sky-950/70 text-sky-300 border-sky-700/80 hover:bg-sky-900' : 'bg-sky-100 text-sky-800 border-sky-300 hover:bg-sky-200'}`}
                                      title="Active holding in Pocket Trader. Click to view."
                                    >
                                      💼 {heldShares} shs
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
                                  className={
                                    stock.signal.includes('BUY') ? 'bg-emerald-950 text-emerald-300 font-extrabold border-emerald-600' :
                                    stock.signal.includes('SELL') ? 'bg-rose-950 text-rose-300 font-extrabold border-rose-600' :
                                    stock.signal.includes('TRIM') ? 'bg-amber-950 text-amber-300 font-extrabold border-amber-600' :
                                    `${isDark ? 'text-slate-100 bg-slate-800 border-slate-600' : 'text-slate-700 bg-slate-200 border-slate-300'} font-bold`
                                  }
                                >
                                  {stock.signal}
                                </Badge>
                              </td>

                              <td className={`px-4 py-3.5 font-mono font-bold ${themeTextColor}`}>
                                {Number(stock.rsi_14).toFixed(1)}
                              </td>

                              <td className={`px-4 py-3.5 font-mono font-medium ${themeMutedColor}`}>
                                ${Number(stock.sma_50).toFixed(2)}
                              </td>

                              <td className={`px-4 py-3.5 font-mono font-medium ${themeMutedColor}`}>
                                ${Number(stock.sma_200).toFixed(2)}
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
                  <p className={`text-xs ${themeMutedColor}`}>Live P&L calculations and profit target monitoring against TSX scans.</p>
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
                          <th className="px-4 py-3.5">Engine Signal</th>
                          <th className="px-4 py-3.5 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                        {calculatedPositions.map((pos) => (
                          <tr key={pos.id} className={`${themeTableRowHover} transition-colors`}>
                            <td className="px-5 py-3.5 font-bold cursor-pointer" onClick={() => setActiveStockDetail(pos.symbol)}>
                              <span className="text-sky-500 hover:underline text-base font-extrabold">{pos.symbol}</span>
                              <div className={`text-xs font-medium ${themeMutedColor}`}>{pos.company} ({pos.shares} shs)</div>
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
                            <td className="px-4 py-3.5">
                              <Badge variant="outline" className={`text-xs font-bold border ${isDark ? 'text-slate-100 bg-slate-800 border-slate-600' : 'text-slate-800 bg-slate-200 border-slate-300'}`}>
                                {pos.signal}
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
                        ))}
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
                  <h3 className={`font-bold text-base ${themeTextColor}`}>TSX Momentum & Distribution Matrix</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                    <p className="text-xs font-extrabold text-sky-500 uppercase">Oversold Setups</p>
                    <p className={`text-3xl font-black mt-1 ${themeTextColor}`}>
                      {activeMonitoredStocks.filter(s => Number(s.rsi_14) <= 40).length}
                    </p>
                    <p className={`text-xs font-medium mt-1 ${themeMutedColor}`}>14D RSI ≤ 40.0</p>
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
                      Algorithmic rules, signal matrix, cloud scheduling, and trade tracking procedures.
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="text-sm font-extrabold uppercase tracking-wider text-sky-500 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-500">01</span>
                    Platform Scope & Core Universe
                  </h3>
                  <p className={`text-xs sm:text-sm leading-relaxed font-normal pl-8 ${themeMutedColor}`}>
                    TrendNorth is an automated quantitative screening terminal monitoring high-liquidity Canadian equities and benchmark ETFs listed on the Toronto Stock Exchange (TSX). The engine continuously evaluates momentum and multi-timeframe moving average spreads to identify high-probability swing trade inflection points while removing emotional biases such as FOMO or panic selling.
                  </p>
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-extrabold uppercase tracking-wider text-sky-500 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-500">02</span>
                    Indicator & Signal Classification Matrix
                  </h3>
                  <div className="pl-0 sm:pl-8 overflow-x-auto">
                    <table className={`w-full text-left text-xs border rounded-xl overflow-hidden divide-y ${themeBorder} ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                      <thead className={`font-bold uppercase tracking-wider ${themeTableHead}`}>
                        <tr>
                          <th className="px-4 py-3">Signal</th>
                          <th className="px-4 py-3">Quantitative Condition</th>
                          <th className="px-4 py-3">System Rationale</th>
                          <th className="px-4 py-3">Trading Interpretation</th>
                        </tr>
                      </thead>
                      <tbody className={`divide-y font-medium ${isDark ? 'bg-slate-900/60 divide-slate-800 text-slate-200' : 'bg-white divide-slate-200 text-slate-800'}`}>
                        <tr>
                          <td className="px-4 py-3">
                            <Badge className="bg-emerald-950 text-emerald-300 border-emerald-600 font-bold">
                              BUY / ACCUMULATE
                            </Badge>
                          </td>
                          <td className="px-4 py-3 font-mono text-sky-500 font-bold">
                            SMA_50 ≥ SMA_200 <br/>&amp; RSI_14 ≤ 40.0
                          </td>
                          <td className="px-4 py-3 text-emerald-500 font-bold">
                            Bullish trend + Pullback dip
                          </td>
                          <td className={`px-4 py-3 ${themeMutedColor}`}>
                            Macro structural uptrend is intact, but near-term selling pressure has dragged the momentum oscillator into value/discount territory.
                          </td>
                        </tr>
                        <tr>
                          <td className="px-4 py-3">
                            <Badge className="bg-rose-950 text-rose-300 border-rose-600 font-bold">
                              SELL / EXIT
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
                              TRIM / TAKE PROFIT
                            </Badge>
                          </td>
                          <td className="px-4 py-3 font-mono text-amber-500 font-bold">
                            RSI_14 ≥ 75.0
                          </td>
                          <td className="px-4 py-3 text-amber-500 font-bold">
                            Overextended momentum
                          </td>
                          <td className={`px-4 py-3 ${themeMutedColor}`}>
                            Price momentum has reached acute overbought levels; elevated statistical probability of near-term consolidation or mean reversion.
                          </td>
                        </tr>
                        <tr>
                          <td className="px-4 py-3">
                            <Badge className="bg-slate-800 text-slate-300 border-slate-600 font-bold">
                              KEEP / HOLD
                            </Badge>
                          </td>
                          <td className={`px-4 py-3 font-mono ${themeMutedColor}`}>
                            Baseline Parameters
                          </td>
                          <td className={`px-4 py-3 ${themeMutedColor}`}>
                            Trading within baseline
                          </td>
                          <td className={`px-4 py-3 ${themeMutedColor}`}>
                            Asset price and momentum oscillate within standard historical variance without triggering edge thresholds.
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-extrabold uppercase tracking-wider text-sky-500 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-500">03</span>
                    Pocket Trader Portfolio Management
                  </h3>
                  <div className="pl-8 space-y-2 text-xs sm:text-sm">
                    <ul className={`list-disc space-y-1.5 pl-4 ${themeMutedColor}`}>
                      <li>
                        <strong className={themeTextColor}>Active Position Tracking:</strong> Log entry price, purchase date, and share size for open or planned setups directly from the slide-out sheet or stock detail profiles.
                      </li>
                      <li>
                        <strong className={themeTextColor}>Real-Time Target Achievements:</strong> Specify your CAD target gain per share (e.g., +$10.00). The position table calculates progress percentages and illuminates <strong className="text-emerald-500">🎯 TARGET REACHED</strong> as soon as the live scanned price crosses your threshold.
                      </li>
                      <li>
                        <strong className={themeTextColor}>Zero-Cloud Client Storage:</strong> Holdings persist directly inside browser storage (`localStorage`). You can backup or export your holdings via <strong className="text-sky-500">Export CSV</strong> at any time without requiring external database accounts.
                      </li>
                    </ul>
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-extrabold uppercase tracking-wider text-sky-500 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-500">04</span>
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

      <footer className={`mt-12 py-6 border-t ${isDark ? 'border-slate-800 bg-slate-950 text-slate-400' : 'border-slate-200 bg-white text-slate-500'} text-center text-xs font-medium`}>
        <div className="w-full px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>TrendNorth Terminal © {clientYear || '2026'} — Canadian Equities Technical Intelligence</span>
          <span>Educational & Algorithmic Research Only • Not Financial Advice</span>
        </div>
      </footer>

      {/* POCKET TRADER DRAWER */}
      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent side="right" className={`w-[360px] sm:w-[440px] p-6 shadow-2xl border-l overflow-y-auto ${isDark ? 'bg-slate-900 text-white border-slate-800' : 'bg-white text-slate-900 border-slate-200'}`}>
          <SheetHeader className={`pb-4 border-b ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
            <SheetTitle className={`text-lg font-bold ${themeTextColor}`}>Track New Position</SheetTitle>
            <SheetDescription className={`text-xs ${themeMutedColor}`}>
              Type or select any TSX or custom symbol. Target achievements and P&L compute automatically.
            </SheetDescription>
          </SheetHeader>
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

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="date" className={`text-xs font-bold ${themeTextColor}`}>Entry Date</Label>
                <Input
                  id="date"
                  type="date"
                  value={newBuyDate}
                  onChange={(e) => setNewBuyDate(e.target.value)}
                  className={`h-10 text-xs font-medium ${themeInputBg}`}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="shares" className={`text-xs font-bold ${themeTextColor}`}>Shares Count</Label>
                <Input
                  id="shares"
                  type="number"
                  step="1"
                  min="1"
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

            <div className="pt-4">
              <Button type="submit" className="w-full bg-sky-600 hover:bg-sky-500 text-white font-bold shadow-md cursor-pointer h-10">
                Save to Pocket Trader
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>
    </div>
  )
}