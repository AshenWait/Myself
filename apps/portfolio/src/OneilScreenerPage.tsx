import {
  BookmarkPlus,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Database,
  ExternalLink,
  LoaderCircle,
  RefreshCw,
  Save,
  Search,
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
const DEFAULT_TDX_ROOT = 'D:\\new_tdx64'
const LEGACY_DEFAULT_TDX_ROOT = 'C:\\new_tdx'
const INCORRECT_TDX_ROOT = 'D:\\new\\_tdx64'
const PAGE_SIZE = 100

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

type ScreenerState = {
  results: ScoreRow[]
  watchlist: ScoreRow[]
  summary: {
    total: number
    a: number
    b: number
    c: number
    rejected: number
    watchlist: number
  }
  generated_at: string | null
}

type ViewMode = 'results' | 'watchlist'
type BucketFilter = 'all' | 'a' | 'b' | 'c'

const EMPTY_STATE: ScreenerState = {
  results: [],
  watchlist: [],
  summary: { total: 0, a: 0, b: 0, c: 0, rejected: 0, watchlist: 0 },
  generated_at: null,
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
  const [minScore, setMinScore] = useState(75)
  const [autoAdd, setAutoAdd] = useState(true)
  const [openEastmoney, setOpenEastmoney] = useState(readEastmoneyPreference)
  const [view, setView] = useState<ViewMode>('results')
  const [bucketFilter, setBucketFilter] = useState<BucketFilter>('all')
  const [query, setQuery] = useState('')
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
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
    setPage(1)
  }, [view, bucketFilter, query])

  const watchlistSymbols = useMemo(() => new Set(state.watchlist.map((item) => item.symbol)), [state.watchlist])
  const sourceRows = view === 'results' ? state.results : state.watchlist
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

  const runScan = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const nextRoot = saveTdxRoot()
    if (!nextRoot) return
    setScanning(true)
    setError('')
    try {
      applyState(
        await requestState('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tdx_root: nextRoot,
            min_score: minScore,
            auto_add: autoAdd,
          }),
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
          <span>{online ? '本地服务在线' : '本地服务离线'}</span>
        </div>
      </header>

      <form className="oneil-scanbar" onSubmit={runScan}>
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
        <label className="oneil-score-field">
          <span>入选分数</span>
          <input
            aria-label="自选股最低分数"
            max="100"
            min="0"
            onChange={(event) => setMinScore(Number(event.target.value))}
            type="number"
            value={minScore}
          />
        </label>
        <label className="oneil-toggle">
          <input checked={autoAdd} onChange={(event) => setAutoAdd(event.target.checked)} type="checkbox" />
          <span aria-hidden="true" />
          自动加入自选
        </label>
        <button className="oneil-run-button" disabled={scanning} type="submit">
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
          <strong>{state.summary.total}</strong>
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

      <div className="oneil-toolbar">
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
        </div>
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
      </div>

      <div className="oneil-workspace">
        <div className="oneil-table-panel">
          {loading && state.results.length === 0 ? (
            <div className="oneil-empty"><LoaderCircle className="is-spinning" size={24} />正在读取本地数据</div>
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

      <p className="oneil-disclaimer">筛选结果用于研究优先级排序，不构成投资建议。</p>
    </section>
  )
}
