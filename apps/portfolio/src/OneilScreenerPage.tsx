import {
  BookmarkPlus,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Database,
  ExternalLink,
  HardDrive,
  LoaderCircle,
  RefreshCw,
  Save,
  Search,
  Server,
  Sparkles,
  Trash2,
  TrendingUp,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import './OneilScreenerPage.css'

const API_URL = import.meta.env.VITE_ONEIL_API_URL || 'http://127.0.0.1:8765'
const TDX_ROOT_STORAGE_KEY = 'portfolio.oneil.tdx-root'
const EASTMONEY_LINK_STORAGE_KEY = 'portfolio.oneil.open-eastmoney'
const DATA_SOURCE_STORAGE_KEY = 'portfolio.oneil.data-source'
const DEFAULT_TDX_ROOT = 'D:\\new_tdx64'
const LEGACY_DEFAULT_TDX_ROOT = 'C:\\new_tdx'
const INCORRECT_TDX_ROOT = 'D:\\new\\_tdx64'
const PAGE_SIZE = 50

type ScoreComponents = {
  trend?: number
  leader?: number
  volume?: number
  new_high?: number
  market?: number
  fundamental?: number
}

type ScoreRow = {
  rank: number
  symbol: string
  name: string
  industry: string
  trade_date: string
  close: number
  score: number
  bucket: string
  components: ScoreComponents
  metrics: Record<string, number | string>
  reasons: string[]
  flags: string[]
}

type SmartPick = {
  rank: number
  symbol: string
  name: string
  source_rank: number
  score: number
  trade_date: string
  close: number
  confidence: number
  holding_period: string
  entry_low: number
  entry_high: number
  stop_loss: number
  take_profit_1: number
  take_profit_2: number
  thesis: string
  entry_logic: string
  stop_logic: string
  take_profit_logic: string
  risks: string[]
}

type SmartPickGroup = {
  generated_at: string | null
  model: string
  source_trade_date: string | null
  candidate_count: number
  market_view: string
  selection_logic: string
  picks: SmartPick[]
  disclaimer: string
}

type ScreenerState = {
  results: ScoreRow[]
  watchlist: ScoreRow[]
  smart_picks: SmartPickGroup
  summary: {
    total: number
    scanned_total: number
    result_limit: number
    a: number
    b: number
    c: number
    rejected: number
    watchlist: number
    smart: number
  }
  generated_at: string | null
  data_sources: {
    active: DataSourceMode
    tushare: {
      configured: boolean
      automatic: boolean
      schedule: string
      syncing: boolean
      ready: boolean
      latest_trade_date: string | null
      stock_count: number
      progress?: number
      progress_total?: number
      last_error?: string
      completed_at?: string
    }
  }
}

type ViewMode = 'results' | 'watchlist' | 'smart'
type BucketFilter = 'all' | 'a' | 'b' | 'c'
type DataSourceMode = 'tdx' | 'tushare'

const EMPTY_STATE: ScreenerState = {
  results: [],
  watchlist: [],
  smart_picks: {
    generated_at: null,
    model: '',
    source_trade_date: null,
    candidate_count: 0,
    market_view: '',
    selection_logic: '',
    picks: [],
    disclaimer: '智选仅用于研究参考，不构成投资建议或收益承诺。',
  },
  summary: { total: 0, scanned_total: 0, result_limit: 50, a: 0, b: 0, c: 0, rejected: 0, watchlist: 0, smart: 0 },
  generated_at: null,
  data_sources: {
    active: 'tdx',
    tushare: {
      configured: false,
      automatic: false,
      schedule: '18:10',
      syncing: false,
      ready: false,
      latest_trade_date: null,
      stock_count: 0,
    },
  },
}

const COMPONENT_LABELS: Array<[keyof ScoreComponents, string]> = [
  ['trend', '趋势'],
  ['leader', '相对强弱'],
  ['volume', '量能'],
  ['new_high', '新高'],
  ['market', '市场'],
  ['fundamental', '基本面'],
]

const REASON_LABELS: Record<string, string> = {
  close_above_ma50: '收盘价高于 50 日均线',
  close_above_ma150: '收盘价高于 150 日均线',
  close_above_ma200: '收盘价高于 200 日均线',
  ma50_above_ma150: '50 日均线高于 150 日均线',
  ma150_above_ma200: '150 日均线高于 200 日均线',
  ma200_rising: '200 日均线向上',
  '30pct_above_52w_low': '较 52 周低点高 30% 以上',
  within_25pct_of_52w_high: '距 52 周高点不超过 25%',
  up_down_volume_ratio_strong: '上涨/下跌量比强',
  up_down_volume_ratio_positive: '上涨/下跌量比为正',
  positive_day_volume_expansion: '上涨日放量',
  positive_obv_proxy: '量价累积为正',
  near_52w_high: '接近 52 周新高',
  within_10pct_of_52w_high: '距 52 周高点不超过 10%',
  within_20pct_of_52w_high: '距 52 周高点不超过 20%',
  near_20d_breakout: '接近 20 日突破',
  positive_1m_return: '近 1 月收益为正',
}

function readSavedTdxRoot() {
  try {
    const savedRoot = window.localStorage.getItem(TDX_ROOT_STORAGE_KEY)
    return !savedRoot || savedRoot === LEGACY_DEFAULT_TDX_ROOT || savedRoot === INCORRECT_TDX_ROOT
      ? DEFAULT_TDX_ROOT
      : savedRoot
  } catch {
    return DEFAULT_TDX_ROOT
  }
}

function readEastmoneyPreference() {
  try {
    return window.localStorage.getItem(EASTMONEY_LINK_STORAGE_KEY) !== 'false'
  } catch {
    return true
  }
}

function readDataSourcePreference(): DataSourceMode {
  try {
    return window.localStorage.getItem(DATA_SOURCE_STORAGE_KEY) === 'tushare' ? 'tushare' : 'tdx'
  } catch {
    return 'tdx'
  }
}

async function copyToClipboard(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value)
    return
  }

  const textarea = document.createElement('textarea')
  textarea.value = value
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.append(textarea)
  textarea.select()
  const copied = document.execCommand('copy')
  textarea.remove()
  if (!copied) throw new Error('复制失败')
}

function eastmoneyUrl(symbol: string) {
  return `https://quote.eastmoney.com/${symbol.toLowerCase()}.html`
}

function bucketMeta(bucket: string) {
  if (bucket.startsWith('A')) return { label: '深度研究', tone: 'a' }
  if (bucket.startsWith('B')) return { label: '自选候选', tone: 'b' }
  if (bucket.startsWith('C')) return { label: '筛选关注', tone: 'c' }
  return { label: '暂不关注', tone: 'reject' }
}

function formatDateTime(value: string | null) {
  if (!value) return '尚未扫描'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

async function requestState(path: string, options?: RequestInit): Promise<ScreenerState> {
  const response = await fetch(`${API_URL}${path}`, options)
  const payload = (await response.json()) as ScreenerState & { error?: string }
  if (!response.ok) {
    throw new Error(payload.error || `请求失败 (${response.status})`)
  }
  return payload
}

function matchesBucket(row: ScoreRow, filter: BucketFilter) {
  if (filter === 'all') return true
  return row.bucket.toLowerCase().startsWith(filter)
}

export function OneilScreenerPage() {
  const [state, setState] = useState<ScreenerState>(EMPTY_STATE)
  const [tdxRoot, setTdxRoot] = useState(readSavedTdxRoot)
  const [savedTdxRoot, setSavedTdxRoot] = useState(readSavedTdxRoot)
  const [dataSource, setDataSource] = useState<DataSourceMode>(readDataSourcePreference)
  const [openEastmoney, setOpenEastmoney] = useState(readEastmoneyPreference)
  const [view, setView] = useState<ViewMode>('results')
  const [bucketFilter, setBucketFilter] = useState<BucketFilter>('all')
  const [query, setQuery] = useState('')
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [smarting, setSmarting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [busySymbol, setBusySymbol] = useState('')
  const [copiedKey, setCopiedKey] = useState('')
  const [online, setOnline] = useState(false)
  const [error, setError] = useState('')

  const applyState = useCallback((nextState: ScreenerState) => {
    setState(nextState)
    setOnline(true)
    setError('')
    setSelectedSymbol((current) => current || nextState.results[0]?.symbol || nextState.watchlist[0]?.symbol || '')
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      applyState(await requestState('/api/screener'))
    } catch (requestError) {
      setOnline(false)
      setError(requestError instanceof Error ? requestError.message : '选股服务连接失败')
    } finally {
      setLoading(false)
    }
  }, [applyState])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    if (!state.data_sources.tushare.syncing) return
    const interval = window.setInterval(() => void refresh(), 3000)
    return () => window.clearInterval(interval)
  }, [refresh, state.data_sources.tushare.syncing])

  useEffect(() => {
    setPage(1)
  }, [view, bucketFilter, query])

  const watchlistSymbols = useMemo(() => new Set(state.watchlist.map((item) => item.symbol)), [state.watchlist])
  const sourceRows = view === 'watchlist' ? state.watchlist : state.results
  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    return sourceRows.filter((row) => {
      const matchesQuery =
        !normalizedQuery ||
        row.symbol.toLowerCase().includes(normalizedQuery) ||
        row.name.toLowerCase().includes(normalizedQuery) ||
        row.industry.toLowerCase().includes(normalizedQuery)
      return matchesQuery && matchesBucket(row, bucketFilter)
    })
  }, [bucketFilter, query, sourceRows])
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE))
  const visibleRows = filteredRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const selected =
    state.results.find((item) => item.symbol === selectedSymbol) ||
    state.watchlist.find((item) => item.symbol === selectedSymbol) ||
    visibleRows[0]

  const saveTdxRoot = () => {
    const nextRoot = tdxRoot.trim()
    if (!nextRoot) {
      setError('请输入通达信目录')
      return ''
    }

    try {
      window.localStorage.setItem(TDX_ROOT_STORAGE_KEY, nextRoot)
      setSavedTdxRoot(nextRoot)
      setTdxRoot(nextRoot)
      setError('')
    } catch {
      setError('浏览器无法保存通达信目录')
      return ''
    }
    return nextRoot
  }

  const selectDataSource = (nextSource: DataSourceMode) => {
    setDataSource(nextSource)
    setError('')
    try {
      window.localStorage.setItem(DATA_SOURCE_STORAGE_KEY, nextSource)
    } catch {
      // The selected source still applies to the current session.
    }
  }

  const sourcePayload = () => {
    if (dataSource === 'tushare') return { data_source: 'tushare' }
    const nextRoot = saveTdxRoot()
    return nextRoot ? { data_source: 'tdx', tdx_root: nextRoot } : null
  }

  const runScan = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const payload = sourcePayload()
    if (!payload) return
    setScanning(true)
    setError('')
    try {
      applyState(
        await requestState('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }),
      )
      setView('results')
      setPage(1)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '扫描失败')
    } finally {
      setScanning(false)
    }
  }

  const runSmartPicks = async () => {
    const payload = sourcePayload()
    if (!payload) return
    setSmarting(true)
    setError('')
    try {
      applyState(
        await requestState('/api/smart-picks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }),
      )
      setView('smart')
      setPage(1)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '智选失败')
    } finally {
      setSmarting(false)
    }
  }

  const syncServerData = async () => {
    setSyncing(true)
    setError('')
    try {
      applyState(await requestState('/api/tushare/sync', { method: 'POST' }))
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '服务器行情同步失败')
    } finally {
      setSyncing(false)
    }
  }

  const updateWatchlist = async (row: ScoreRow, remove: boolean) => {
    setBusySymbol(row.symbol)
    setError('')
    try {
      const path = remove ? `/api/watchlist/${encodeURIComponent(row.symbol)}` : '/api/watchlist'
      const options: RequestInit = remove
        ? { method: 'DELETE' }
        : {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: row.symbol }),
          }
      applyState(await requestState(path, options))
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '自选股更新失败')
    } finally {
      setBusySymbol('')
    }
  }

  const toggleEastmoney = (enabled: boolean) => {
    setOpenEastmoney(enabled)
    try {
      window.localStorage.setItem(EASTMONEY_LINK_STORAGE_KEY, String(enabled))
    } catch {
      // The toggle still works for the current session when storage is unavailable.
    }
  }

  const activateStock = async (row: ScoreRow, field: 'name' | 'code') => {
    const value = field === 'name' && row.name ? row.name : row.symbol.slice(2)
    const key = `${row.symbol}:${field}`
    setSelectedSymbol(row.symbol)
    if (openEastmoney) {
      window.open(eastmoneyUrl(row.symbol), '_blank', 'noopener,noreferrer')
    }
    try {
      await copyToClipboard(value)
      setCopiedKey(key)
      window.setTimeout(() => setCopiedKey((current) => current === key ? '' : current), 1400)
    } catch {
      setError('复制失败，请检查浏览器剪贴板权限。')
    }
  }

  const tushareStatus = state.data_sources.tushare
  const serverSourceBusy = syncing || tushareStatus.syncing
  const sourceUnavailable = dataSource === 'tushare' && (!tushareStatus.ready || serverSourceBusy)
  const serverStatusLabel = serverSourceBusy
    ? `同步中 ${tushareStatus.progress || 0}/${tushareStatus.progress_total || 0}`
    : tushareStatus.ready
      ? `更新至 ${tushareStatus.latest_trade_date}`
      : tushareStatus.last_error
        ? '同步失败'
      : tushareStatus.configured
        ? '等待首次同步'
        : '未配置 Token'

  return (
    <section className="oneil-page">
      <header className="oneil-header">
        <div>
          <p className="oneil-kicker">Research Queue / A Shares</p>
          <h1>欧奈尔选股</h1>
          <p className="oneil-asof">数据时间：{formatDateTime(state.generated_at)}</p>
        </div>
        <div className={`oneil-service ${online ? 'is-online' : 'is-offline'}`}>
          {online ? <Wifi size={16} /> : <WifiOff size={16} />}
          <span>{online ? '选股服务在线' : '选股服务离线'}</span>
        </div>
      </header>

      <form className="oneil-scanbar" onSubmit={runScan}>
        <div className="oneil-source-field">
          <span>数据源</span>
          <div aria-label="行情数据源" className="oneil-source-segment" role="radiogroup">
            <button
              aria-checked={dataSource === 'tdx'}
              className={dataSource === 'tdx' ? 'is-active' : ''}
              onClick={() => selectDataSource('tdx')}
              role="radio"
              type="button"
            ><HardDrive size={14} />本地</button>
            <button
              aria-checked={dataSource === 'tushare'}
              className={dataSource === 'tushare' ? 'is-active' : ''}
              onClick={() => selectDataSource('tushare')}
              role="radio"
              type="button"
            ><Server size={14} />服务器</button>
          </div>
        </div>
        {dataSource === 'tdx' ? (
          <div className="oneil-path-field">
            <span>通达信目录</span>
            <div>
              <Database size={17} />
              <input
                aria-label="通达信目录"
                onChange={(event) => setTdxRoot(event.target.value)}
                spellCheck={false}
                value={tdxRoot}
              />
              <button
                aria-label={tdxRoot === savedTdxRoot ? '路径已保存' : '保存路径'}
                className="oneil-path-save"
                disabled={!tdxRoot.trim() || tdxRoot === savedTdxRoot}
                onClick={saveTdxRoot}
                title={tdxRoot === savedTdxRoot ? '路径已保存' : '保存路径'}
                type="button"
              >
                {tdxRoot === savedTdxRoot ? <Check size={16} /> : <Save size={16} />}
              </button>
            </div>
          </div>
        ) : (
          <div className="oneil-server-field">
            <span>服务器行情</span>
            <div>
              <Server size={17} />
              <strong>{serverStatusLabel}</strong>
              <small title={tushareStatus.last_error}>{tushareStatus.last_error || (tushareStatus.automatic ? `每日 ${tushareStatus.schedule}` : '自动更新关闭')}</small>
              <button
                aria-label="立即同步服务器行情"
                disabled={!tushareStatus.configured || serverSourceBusy}
                onClick={() => void syncServerData()}
                title="立即同步服务器行情"
                type="button"
              ><RefreshCw className={serverSourceBusy ? 'is-spinning' : ''} size={16} /></button>
            </div>
          </div>
        )}
        <button
          className="oneil-smart-button"
          disabled={smarting || scanning || sourceUnavailable}
          onClick={() => void runSmartPicks()}
          type="button"
        >
          {smarting ? <LoaderCircle className="is-spinning" size={18} /> : <Sparkles size={18} />}
          {smarting ? '智选中' : '一键智选'}
        </button>
        <button className="oneil-run-button" disabled={scanning || smarting || sourceUnavailable} type="submit">
          {scanning ? <LoaderCircle className="is-spinning" size={18} /> : <TrendingUp size={18} />}
          {scanning ? '扫描中' : '运行扫描'}
        </button>
        <button
          aria-label="刷新选股数据"
          className="oneil-icon-button"
          disabled={loading}
          onClick={() => void refresh()}
          title="刷新选股数据"
          type="button"
        >
          <RefreshCw className={loading ? 'is-spinning' : ''} size={18} />
        </button>
      </form>

      {error ? (
        <div className="oneil-error" role="alert">
          <CircleAlert size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <section className="oneil-funnel" aria-label="股票池统计">
        <div>
          <span>股票池</span>
          <strong>{state.summary.scanned_total}</strong>
        </div>
        <div className="tone-a">
          <span>A · 深度研究</span>
          <strong>{state.summary.a}</strong>
        </div>
        <div className="tone-b">
          <span>B · 自选候选</span>
          <strong>{state.summary.b}</strong>
        </div>
        <div className="tone-watch">
          <span>已保存</span>
          <strong>{state.summary.watchlist}</strong>
        </div>
      </section>

      <div className={`oneil-toolbar ${view === 'smart' ? 'is-smart' : ''}`}>
        <div className="oneil-tabs" role="tablist">
          <button
            aria-selected={view === 'results'}
            className={view === 'results' ? 'is-active' : ''}
            onClick={() => setView('results')}
            role="tab"
            type="button"
          >
            排名 <span>{state.summary.total}</span>
          </button>
          <button
            aria-selected={view === 'watchlist'}
            className={view === 'watchlist' ? 'is-active' : ''}
            onClick={() => setView('watchlist')}
            role="tab"
            type="button"
          >
            自选股 <span>{state.summary.watchlist}</span>
          </button>
          <button
            aria-selected={view === 'smart'}
            className={view === 'smart' ? 'is-active' : ''}
            onClick={() => setView('smart')}
            role="tab"
            type="button"
          >
            智选 <span>{state.summary.smart}</span>
          </button>
        </div>
        {view === 'smart' ? (
          <div className="oneil-smart-tab-meta">
            <Sparkles size={15} />
            <span>{state.smart_picks.model || '等待生成'} · {formatDateTime(state.smart_picks.generated_at)}</span>
          </div>
        ) : (
          <>
            <label className="oneil-search">
              <Search size={16} />
              <input
                aria-label="搜索股票"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="代码 / 名称 / 行业"
                value={query}
              />
            </label>
            <label className="oneil-link-toggle" title="点击股票名称或代码时打开东方财富个股页">
              <input
                checked={openEastmoney}
                onChange={(event) => toggleEastmoney(event.target.checked)}
                type="checkbox"
              />
              <span aria-hidden="true" />
              <ExternalLink size={15} />
              点击跳转
            </label>
            <select
              aria-label="评分分组"
              className="oneil-filter"
              onChange={(event) => setBucketFilter(event.target.value as BucketFilter)}
              value={bucketFilter}
            >
              <option value="all">全部分组</option>
              <option value="a">A · 深度研究</option>
              <option value="b">B · 自选候选</option>
              <option value="c">C · 筛选关注</option>
            </select>
          </>
        )}
      </div>

      {view === 'smart' ? (
        <section className="oneil-smart-panel" aria-label="智选组合">
          {state.smart_picks.picks.length === 0 ? (
            <div className="oneil-empty">
              <Sparkles size={28} />
              <strong>暂无智选组合</strong>
              <span>点击“一键智选”，模型将从扫描前 10 名中选择 3 只</span>
            </div>
          ) : (
            <>
              <header className="oneil-smart-head">
                <div>
                  <span>AI SHORTLIST / TOP 10</span>
                  <h2>短线智选组合</h2>
                </div>
                <div>
                  <span>数据日期 {state.smart_picks.source_trade_date || '未知'}</span>
                  <strong>{state.smart_picks.model}</strong>
                </div>
              </header>

              <div className="oneil-smart-list">
                {state.smart_picks.picks.map((pick) => {
                  const row = state.results.find((item) => item.symbol === pick.symbol)
                  const saved = watchlistSymbols.has(pick.symbol)
                  return (
                    <article className="oneil-smart-card" key={pick.symbol}>
                      <div className="oneil-smart-card-head">
                        <span className="oneil-smart-rank">0{pick.rank}</span>
                        <div>
                          <button
                            className="oneil-smart-name"
                            disabled={!row}
                            onClick={() => row && void activateStock(row, 'name')}
                            type="button"
                          >
                            {pick.name || pick.symbol.slice(2)}
                          </button>
                          <button
                            className="oneil-smart-code"
                            disabled={!row}
                            onClick={() => row && void activateStock(row, 'code')}
                            type="button"
                          >
                            {pick.symbol.slice(2)} · 扫描第 {pick.source_rank} 名
                          </button>
                        </div>
                        <div className="oneil-smart-confidence">
                          <span>置信</span>
                          <strong>{pick.confidence}</strong>
                        </div>
                        <button
                          aria-label={saved ? `从自选股移除 ${pick.symbol}` : `加入自选股 ${pick.symbol}`}
                          className={`oneil-smart-save ${saved ? 'is-saved' : ''}`}
                          disabled={!row || busySymbol === pick.symbol}
                          onClick={() => row && void updateWatchlist(row, saved)}
                          title={saved ? '从自选股移除' : '加入自选股'}
                          type="button"
                        >
                          {busySymbol === pick.symbol ? (
                            <LoaderCircle className="is-spinning" size={17} />
                          ) : saved ? (
                            <Trash2 size={17} />
                          ) : (
                            <BookmarkPlus size={17} />
                          )}
                        </button>
                      </div>

                      <p className="oneil-smart-thesis">{pick.thesis}</p>

                      <div className="oneil-smart-prices">
                        <div className="is-entry">
                          <span>参考买入区间</span>
                          <strong>{pick.entry_low.toFixed(2)} - {pick.entry_high.toFixed(2)}</strong>
                          <small>最新收盘 {pick.close.toFixed(2)}</small>
                        </div>
                        <div className="is-profit">
                          <span>止盈目标</span>
                          <strong>{pick.take_profit_1.toFixed(2)} / {pick.take_profit_2.toFixed(2)}</strong>
                          <small>分两档执行</small>
                        </div>
                        <div className="is-stop">
                          <span>止损参考</span>
                          <strong>{pick.stop_loss.toFixed(2)}</strong>
                          <small>{pick.holding_period}</small>
                        </div>
                      </div>

                      <dl className="oneil-smart-rules">
                        <div><dt>入场</dt><dd>{pick.entry_logic}</dd></div>
                        <div><dt>止盈</dt><dd>{pick.take_profit_logic}</dd></div>
                        <div><dt>止损</dt><dd>{pick.stop_logic}</dd></div>
                      </dl>

                      <div className="oneil-smart-risks">
                        <strong>失效风险</strong>
                        {pick.risks.map((risk) => <span key={risk}>{risk}</span>)}
                      </div>
                    </article>
                  )
                })}
              </div>

              <div className="oneil-smart-context">
                <div><strong>模型判断</strong><p>{state.smart_picks.market_view}</p></div>
                <div><strong>筛选逻辑</strong><p>{state.smart_picks.selection_logic}</p></div>
              </div>
              <p className="oneil-smart-disclaimer">{state.smart_picks.disclaimer}</p>
            </>
          )}
        </section>
      ) : (
      <div className="oneil-workspace">
        <div className="oneil-table-panel">
          {loading && state.results.length === 0 ? (
            <div className="oneil-empty"><LoaderCircle className="is-spinning" size={24} />正在读取选股数据</div>
          ) : visibleRows.length === 0 ? (
            <div className="oneil-empty">
              <Database size={26} />
              <strong>{view === 'watchlist' ? '暂无自选股' : '暂无筛选结果'}</strong>
              <span>{online ? '运行扫描后更新股票池' : '启动本地选股服务后刷新'}</span>
            </div>
          ) : (
            <div className="oneil-table-scroll">
              <table className="oneil-table">
                <colgroup>
                  <col className="oneil-rank-column" />
                  <col className="oneil-stock-column" />
                </colgroup>
                <thead>
                  <tr>
                    <th aria-label="排名" className="oneil-rank-heading">#</th>
                    <th>股票</th>
                    <th>总分</th>
                    <th>研究状态</th>
                    <th>RS</th>
                    <th>趋势</th>
                    <th>量能</th>
                    <th>收盘</th>
                    <th aria-label="自选股操作" />
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.map((row) => {
                    const meta = bucketMeta(row.bucket)
                    const saved = watchlistSymbols.has(row.symbol)
                    return (
                      <tr className={selected?.symbol === row.symbol ? 'is-selected' : ''} key={row.symbol}>
                        <td className="oneil-rank">{row.rank}</td>
                        <td>
                          <div className="oneil-stock-identity">
                            <button
                              className="oneil-stock-name"
                              disabled={!row.name}
                              onClick={() => void activateStock(row, 'name')}
                              title={openEastmoney ? '复制股票名称并打开东方财富' : '复制股票名称'}
                              type="button"
                            >
                              {row.name || '名称未提供'}
                            </button>
                            <div>
                              <button
                                className="oneil-stock-code"
                                onClick={() => void activateStock(row, 'code')}
                                title={openEastmoney ? '复制股票代码并打开东方财富' : '复制股票代码'}
                                type="button"
                              >
                                {row.symbol.slice(2)}
                              </button>
                              <span>{row.symbol.slice(0, 2).toUpperCase()}</span>
                            </div>
                            {copiedKey.startsWith(`${row.symbol}:`) ? (
                              <span className="oneil-copy-toast"><Check size={12} />已复制</span>
                            ) : null}
                          </div>
                        </td>
                        <td><strong className="oneil-score">{row.score.toFixed(1)}</strong></td>
                        <td><span className={`oneil-bucket tone-${meta.tone}`}>{meta.label}</span></td>
                        <td>{Number(row.metrics.rs_rank || 0).toFixed(0)}</td>
                        <td>{Number(row.components.trend || 0).toFixed(0)}</td>
                        <td>{Number(row.components.volume || 0).toFixed(0)}</td>
                        <td className="oneil-close">{row.close.toFixed(2)}</td>
                        <td>
                          <button
                            aria-label={saved ? `从自选股移除 ${row.symbol}` : `加入自选股 ${row.symbol}`}
                            className={`oneil-row-action ${saved ? 'is-saved' : ''}`}
                            disabled={busySymbol === row.symbol}
                            onClick={() => void updateWatchlist(row, saved)}
                            title={saved ? '从自选股移除' : '加入自选股'}
                            type="button"
                          >
                            {busySymbol === row.symbol ? (
                              <LoaderCircle className="is-spinning" size={17} />
                            ) : saved ? (
                              <Trash2 size={17} />
                            ) : (
                              <BookmarkPlus size={17} />
                            )}
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          <footer className="oneil-pagination">
            <span>{filteredRows.length} 条结果</span>
            <div>
              <button
                aria-label="上一页"
                disabled={page <= 1}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                title="上一页"
                type="button"
              ><ChevronLeft size={17} /></button>
              <span>{page} / {pageCount}</span>
              <button
                aria-label="下一页"
                disabled={page >= pageCount}
                onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
                title="下一页"
                type="button"
              ><ChevronRight size={17} /></button>
            </div>
          </footer>
        </div>

        <aside className="oneil-detail" aria-label="股票评分详情">
          {selected ? (
            <>
              <div className="oneil-detail-head">
                <div>
                  <span>{selected.symbol}</span>
                  <h2>{selected.name || selected.symbol.slice(2)}</h2>
                  <p>{selected.industry || '行业数据未提供'} · {selected.trade_date}</p>
                </div>
                <strong>{selected.score.toFixed(1)}</strong>
              </div>
              <div className="oneil-component-list">
                {COMPONENT_LABELS.map(([key, label]) => {
                  const value = Number(selected.components[key] || 0)
                  return (
                    <div key={key}>
                      <span>{label}</span>
                      <div><i style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>
                      <strong>{value.toFixed(0)}</strong>
                    </div>
                  )
                })}
              </div>
              <div className="oneil-detail-section">
                <h3>入选依据</h3>
                <div className="oneil-reasons">
                  {selected.reasons.length > 0
                    ? selected.reasons.map((reason) => <span key={reason}>{REASON_LABELS[reason] || reason}</span>)
                    : <span>暂无结构化依据</span>}
                </div>
              </div>
              {selected.flags.length > 0 ? (
                <div className="oneil-data-gap">
                  <CircleAlert size={16} />
                  {selected.flags.includes('fundamental_data_missing') ? '基本面数据缺失，当前按中性分处理' : selected.flags.join('、')}
                </div>
              ) : null}
            </>
          ) : (
            <div className="oneil-empty"><TrendingUp size={26} />选择一只股票查看评分</div>
          )}
        </aside>
      </div>
      )}

      <p className="oneil-disclaimer">筛选结果用于研究优先级排序，不构成投资建议。</p>
    </section>
  )
}
