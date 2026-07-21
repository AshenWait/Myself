import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  ArrowUpRight,
  Blocks,
  Download,
  FileText,
  FlaskConical,
  Gamepad2,
  GitBranch,
  Menu,
  Pause,
  Play,
  RotateCcw,
  Upload,
  X,
} from 'lucide-react'
import {
  type ChangeEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import './App.css'
import { resume } from './content/resume'

const navItems = [
  { label: '简历', href: '/', icon: FileText },
  { label: 'Agent', href: '/knowledge-agent', icon: Blocks },
  { label: 'Lab', href: '/lab', icon: FlaskConical },
]

const KNOWLEDGE_AGENT_URL =
  import.meta.env.VITE_KNOWLEDGE_AGENT_URL ||
  (import.meta.env.DEV ? 'http://127.0.0.1:5174/' : '/knowledge-agent-app/')
const RESUME_STORAGE_KEY = 'portfolio.resume.html.20260715'
const MAX_SAVED_RESUME_HTML_LENGTH = 1_100_000
const RESUME_AVATAR_DEFAULT_SRC = '/resume/avatar.jpg'
const RESUME_AVATAR_DEFAULT_IMAGE_HTML = `<img alt="${escapeHtml(resume.name)} 头像" src="${RESUME_AVATAR_DEFAULT_SRC}" />`
const RESUME_AVATAR_FRAME_HTML =
  `<div aria-label="头像位置，点击上传" class="resume-avatar-frame" contenteditable="false" data-placeholder="点击上传" role="button" tabindex="0">${RESUME_AVATAR_DEFAULT_IMAGE_HTML}</div>`
const RESUME_CONTACT_BREAK_HTML = '<span aria-hidden="true" class="resume-contact-break"></span>'
const RESUME_SUMMARY_SECTION_TITLE = '个人简介'
const DEFAULT_RESUME_HTML = createResumeHtml()
const MAX_RESUME_AVATAR_SOURCE_BYTES = 8_000_000
const MAX_RESUME_AVATAR_DATA_URL_LENGTH = 850_000
const RESUME_AVATAR_MAX_WIDTH = 720
const RESUME_AVATAR_MAX_HEIGHT = 960
const RESUME_AVATAR_JPEG_QUALITY = 0.86
const SNAKE_BEST_SCORE_KEY = 'portfolio.snake.best.20260716'
const SNAKE_BOARD_SIZE = 16
const SNAKE_TICK_MS = 145
const POWER_UP_CHANCE = 0.05
const TRADING_QR_DEFAULT_SRC = '/lab/trading-tycoon.png'
const TRADING_QR_STORAGE_KEY = 'portfolio.lab.tradingTycoonQr.20260721'
const MAX_TRADING_QR_IMAGE_BYTES = 1_500_000
const MAX_TRADING_QR_DATA_URL_LENGTH = 2_100_000

type Direction = 'up' | 'down' | 'left' | 'right'
type PowerUp = 'slow' | 'burst' | 'life'

type Cell = {
  x: number
  y: number
}

type Food = Cell & {
  id: string
  power?: PowerUp
}

const INITIAL_SNAKE: Cell[] = [
  { x: 7, y: 8 },
  { x: 6, y: 8 },
  { x: 5, y: 8 },
]

const DIRECTION_DELTAS: Record<Direction, Cell> = {
  up: { x: 0, y: -1 },
  down: { x: 0, y: 1 },
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
}

const OPPOSITE_DIRECTIONS: Record<Direction, Direction> = {
  up: 'down',
  down: 'up',
  left: 'right',
  right: 'left',
}

const BOARD_CELLS = Array.from({ length: SNAKE_BOARD_SIZE * SNAKE_BOARD_SIZE }, (_, index) => ({
  x: index % SNAKE_BOARD_SIZE,
  y: Math.floor(index / SNAKE_BOARD_SIZE),
}))

const POWER_UPS: PowerUp[] = ['slow', 'burst', 'life']
const POWER_UP_LABELS: Record<PowerUp, string> = {
  slow: '慢速 1/2',
  burst: '+5 糖果',
  life: '+1 生命',
}

const labTiles = [
  { id: 'snake', title: '贪吃蛇', kicker: '小游戏', status: '开放', tone: 'tile-mint' },
] as const

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function linkText(href: string) {
  return href.replace(/^mailto:/, '').replace(/^tel:\+?86?/, '').replace(/^https?:\/\//, '')
}

function shouldBreakBeforeResumeContactLink(href: string) {
  return href.startsWith('mailto:') || href.includes('github.com/')
}

function listItems(items: string[]) {
  return items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')
}

function sameCell(a: Cell, b: Cell) {
  return a.x === b.x && a.y === b.y
}

function cloneInitialSnake() {
  return INITIAL_SNAKE.map((cell) => ({ ...cell }))
}

function wrapBoard(value: number) {
  return (value + SNAKE_BOARD_SIZE) % SNAKE_BOARD_SIZE
}

function createFoodId(cell: Cell) {
  return `${cell.x}-${cell.y}-${Math.random().toString(36).slice(2)}`
}

function createPowerUp() {
  return POWER_UPS[Math.floor(Math.random() * POWER_UPS.length)]
}

function createFood(snake: Cell[], foods: Food[] = []) {
  const emptyCells = BOARD_CELLS.filter(
    (cell) => !snake.some((part) => sameCell(part, cell)) && !foods.some((food) => sameCell(food, cell)),
  )
  const selectedCell = emptyCells[Math.floor(Math.random() * emptyCells.length)]

  if (!selectedCell) {
    return undefined
  }

  return {
    ...selectedCell,
    id: createFoodId(selectedCell),
    power: Math.random() < POWER_UP_CHANCE ? createPowerUp() : undefined,
  }
}

function appendFoods(snake: Cell[], foods: Food[], count: number) {
  const nextFoods = [...foods]

  for (let index = 0; index < count; index += 1) {
    const food = createFood(snake, nextFoods)
    if (!food) {
      break
    }

    nextFoods.push(food)
  }

  return nextFoods
}

function readSnakeBestScore() {
  if (typeof window === 'undefined') {
    return 0
  }

  const savedScore = Number(window.localStorage.getItem(SNAKE_BEST_SCORE_KEY))
  return Number.isFinite(savedScore) ? savedScore : 0
}

function writeSnakeBestScore(score: number) {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(SNAKE_BEST_SCORE_KEY, String(score))
  }
}

function readStoredTradingQrSrc() {
  if (typeof window === 'undefined') {
    return TRADING_QR_DEFAULT_SRC
  }

  try {
    const storedSrc = window.localStorage.getItem(TRADING_QR_STORAGE_KEY)
    if (!storedSrc) {
      return TRADING_QR_DEFAULT_SRC
    }

    if (!storedSrc.startsWith('data:image/') || storedSrc.length > MAX_TRADING_QR_DATA_URL_LENGTH) {
      window.localStorage.removeItem(TRADING_QR_STORAGE_KEY)
      return TRADING_QR_DEFAULT_SRC
    }

    return storedSrc
  } catch {
    return TRADING_QR_DEFAULT_SRC
  }
}

function writeStoredTradingQrSrc(nextSrc: string) {
  if (typeof window === 'undefined') {
    return false
  }

  try {
    window.localStorage.setItem(TRADING_QR_STORAGE_KEY, nextSrc)
    return true
  } catch {
    return false
  }
}

function clearStoredTradingQrSrc() {
  if (typeof window === 'undefined') {
    return
  }

  try {
    window.localStorage.removeItem(TRADING_QR_STORAGE_KEY)
  } catch {
    // Storage cleanup is best-effort for embedded browser compatibility.
  }
}

function createResumeHtml() {
  const [education, ...projects] = resume.timeline
  const contactLinks = resume.links.slice(0, 3)

  return `
    <header class="resume-sheet-header">
      <div>
        <h1>${escapeHtml(resume.name)}</h1>
        <p class="resume-role">${escapeHtml(resume.role)}</p>
        <div class="resume-contact">
          ${contactLinks
            .map(
              (link) =>
                `${shouldBreakBeforeResumeContactLink(link.href) ? RESUME_CONTACT_BREAK_HTML : ''}<a href="${escapeHtml(
                  link.href,
                )}" target="_blank" rel="noreferrer">${escapeHtml(link.label)}：${escapeHtml(linkText(link.href))}</a>`,
            )
            .join('')}
          </div>
      </div>
      ${RESUME_AVATAR_FRAME_HTML}
    </header>

    <section class="resume-section">
      <h2>教育背景与资质证明</h2>
      <div class="resume-split">
        <div>
          <h3>${escapeHtml(education.title)}</h3>
          <ul>${listItems(education.items)}</ul>
        </div>
        <div>
          <h3>主线能力</h3>
          <ul>${listItems(resume.focus.slice(0, 4))}</ul>
        </div>
      </div>
    </section>

    <section class="resume-section">
      <h2>${RESUME_SUMMARY_SECTION_TITLE}</h2>
      <div class="resume-summary-grid">
        <p>${escapeHtml(resume.summary)}</p>
        <ul>${listItems(resume.focus.slice(4))}</ul>
      </div>
    </section>

    <section class="resume-section">
      <h2>技术能力</h2>
      <div class="resume-skill-grid">
        ${resume.skills
          .map(
            (section) => `
              <div>
                <h3>${escapeHtml(section.title)}</h3>
                <p>${escapeHtml(section.items.join('、'))}</p>
              </div>
            `,
          )
          .join('')}
      </div>
    </section>

    <section class="resume-section">
      <h2>项目经历</h2>
      <div class="resume-projects">
        ${projects
          .map(
            (project) => `
              <article>
                <h3>${escapeHtml(project.title)}</h3>
                <ul>${listItems(project.items)}</ul>
              </article>
            `,
          )
          .join('')}
      </div>
    </section>
  `
}

function prepareResumeAvatarFrame(frame: HTMLElement) {
  frame.setAttribute('aria-label', '头像位置，点击上传')
  frame.setAttribute('contenteditable', 'false')
  frame.setAttribute('data-placeholder', '点击上传')
  frame.setAttribute('role', 'button')
  frame.setAttribute('tabindex', '0')

  if (!frame.querySelector('img')) {
    frame.innerHTML = RESUME_AVATAR_DEFAULT_IMAGE_HTML
  }
}

function normalizeResumeHtml(html: string) {
  if (typeof document === 'undefined') {
    return html
  }

  const template = document.createElement('template')
  template.innerHTML = html

  const contact = template.content.querySelector('.resume-contact')
  Array.from(contact?.children || []).forEach((child) => {
    if (
      child instanceof HTMLSpanElement &&
      !child.classList.contains('resume-contact-break') &&
      child.textContent?.trim().startsWith('城市：')
    ) {
      child.remove()
    }
  })

  const contactLinks = contact?.querySelectorAll<HTMLAnchorElement>('a[href]')
  contactLinks?.forEach((link) => {
    if (!shouldBreakBeforeResumeContactLink(link.href)) {
      return
    }

    if (link.previousElementSibling?.classList.contains('resume-contact-break')) {
      return
    }

    const contactBreak = document.createElement('span')
    contactBreak.className = 'resume-contact-break'
    contactBreak.setAttribute('aria-hidden', 'true')
    link.before(contactBreak)
  })

  template.content.querySelectorAll('h2').forEach((heading) => {
    if (heading.textContent?.trim() === 'Positioning') {
      heading.textContent = RESUME_SUMMARY_SECTION_TITLE
    }
  })

  const header = template.content.querySelector('.resume-sheet-header')
  if (!header) {
    return template.innerHTML
  }

  const avatarFrame =
    template.content.querySelector<HTMLElement>('.resume-avatar-frame') || document.createElement('div')
  avatarFrame.className = 'resume-avatar-frame'
  prepareResumeAvatarFrame(avatarFrame)

  if (!avatarFrame.parentElement) {
    header.append(avatarFrame)
  }

  return template.innerHTML
}

function createResumeAvatarDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const image = new Image()
    const objectUrl = URL.createObjectURL(file)

    const cleanup = () => URL.revokeObjectURL(objectUrl)

    image.onload = () => {
      const ratio = Math.min(
        RESUME_AVATAR_MAX_WIDTH / image.naturalWidth,
        RESUME_AVATAR_MAX_HEIGHT / image.naturalHeight,
        1,
      )
      const width = Math.max(1, Math.round(image.naturalWidth * ratio))
      const height = Math.max(1, Math.round(image.naturalHeight * ratio))
      const canvas = document.createElement('canvas')
      const context = canvas.getContext('2d')

      if (!context) {
        cleanup()
        reject(new Error('canvas-unavailable'))
        return
      }

      canvas.width = width
      canvas.height = height
      context.fillStyle = '#fffdf8'
      context.fillRect(0, 0, width, height)
      context.drawImage(image, 0, 0, width, height)

      const nextSrc = canvas.toDataURL('image/jpeg', RESUME_AVATAR_JPEG_QUALITY)
      cleanup()

      if (nextSrc.length > MAX_RESUME_AVATAR_DATA_URL_LENGTH) {
        reject(new Error('avatar-too-large'))
        return
      }

      resolve(nextSrc)
    }

    image.onerror = () => {
      cleanup()
      reject(new Error('avatar-load-failed'))
    }
    image.src = objectUrl
  })
}

function findResumeAvatarFrame(target: EventTarget | null) {
  return target instanceof Element ? (target.closest('.resume-avatar-frame') as HTMLElement | null) : null
}

function readStoredResumeHtml() {
  if (typeof window === 'undefined') {
    return DEFAULT_RESUME_HTML
  }

  try {
    const storedHtml = window.localStorage.getItem(RESUME_STORAGE_KEY)
    if (!storedHtml) {
      return DEFAULT_RESUME_HTML
    }

    if (storedHtml.length > MAX_SAVED_RESUME_HTML_LENGTH) {
      window.localStorage.removeItem(RESUME_STORAGE_KEY)
      return DEFAULT_RESUME_HTML
    }

    const nextHtml = normalizeResumeHtml(storedHtml)
    if (nextHtml !== storedHtml && nextHtml.length <= MAX_SAVED_RESUME_HTML_LENGTH) {
      window.localStorage.setItem(RESUME_STORAGE_KEY, nextHtml)
    }

    return nextHtml
  } catch {
    return DEFAULT_RESUME_HTML
  }
}

function writeStoredResumeHtml(nextHtml: string) {
  if (typeof window === 'undefined' || nextHtml.length > MAX_SAVED_RESUME_HTML_LENGTH) {
    return false
  }

  try {
    window.localStorage.setItem(RESUME_STORAGE_KEY, nextHtml)
    return true
  } catch {
    // The editable resume still works even when the embedded browser blocks storage.
    return false
  }
}

function ScrollToHash() {
  const location = useLocation()

  useEffect(() => {
    if (!location.hash) {
      window.scrollTo({ top: 0, behavior: 'smooth' })
      return
    }

    const element = document.querySelector(location.hash)
    element?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [location.pathname, location.hash])

  return null
}

function AppShell() {
  const [navOpen, setNavOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setNavOpen(false)
  }, [location.pathname, location.hash])

  return (
    <div className="app-shell">
      <ScrollToHash />
      <aside className={`sidebar ${navOpen ? 'is-open' : ''}`}>
        <div>
          <Link className="brand" to="/">
            <span className="brand-mark">YP</span>
            <span>
              <span className="brand-name">{resume.name}</span>
              <span className="brand-role">AI Resume</span>
            </span>
          </Link>

          <nav className="side-nav" aria-label="Primary navigation">
            {navItems.map((item) => {
              const Icon = item.icon
              const hash = item.href.includes('#') ? item.href.slice(item.href.indexOf('#')) : ''
              const isActive =
                item.href === '/'
                  ? location.pathname === '/' && location.hash === ''
                  : hash.length > 0
                    ? location.pathname === '/' && location.hash === hash
                    : location.pathname.startsWith(item.href)

              return (
                <Link className={`nav-link ${isActive ? 'is-active' : ''}`} key={item.label} to={item.href}>
                  <Icon size={18} strokeWidth={1.8} />
                  <span>{item.label}</span>
                </Link>
              )
            })}
          </nav>
        </div>

        <a
          className="github-link"
          href="https://github.com/AshenWait"
          target="_blank"
          rel="noreferrer"
        >
          <GitBranch size={18} strokeWidth={1.8} />
          GitHub
          <ArrowUpRight size={15} strokeWidth={1.8} />
        </a>
      </aside>

      <header className="mobile-header">
        <Link className="brand compact" to="/">
          <span className="brand-mark">YP</span>
          <span className="brand-name">{resume.name}</span>
        </Link>
        <button
          aria-label={navOpen ? 'Close navigation' : 'Open navigation'}
          className="icon-button"
          onClick={() => setNavOpen((open) => !open)}
          type="button"
        >
          {navOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>

      <main className="page">
        <Routes>
          <Route element={<HomePage />} path="/" />
          <Route element={<KnowledgeAgentPage />} path="/knowledge-agent/*" />
          <Route element={<LabPage />} path="/lab/*" />
          <Route element={<NotFoundPage />} path="*" />
        </Routes>
      </main>
    </div>
  )
}

function HomePage() {
  const resumeRef = useRef<HTMLElement>(null)
  const avatarInputRef = useRef<HTMLInputElement>(null)
  const [resumeHtml, setResumeHtml] = useState(() => readStoredResumeHtml())
  const [avatarError, setAvatarError] = useState('')

  const openAvatarPicker = () => {
    setAvatarError('')
    if (avatarInputRef.current) {
      avatarInputRef.current.value = ''
      avatarInputRef.current.click()
    }
  }

  const saveAvatarToResume = (nextSrc: string) => {
    const avatarFrame = resumeRef.current?.querySelector<HTMLElement>('.resume-avatar-frame')
    if (!avatarFrame || !resumeRef.current) {
      setAvatarError('没有找到头像框，请刷新页面后再试。')
      return
    }

    prepareResumeAvatarFrame(avatarFrame)
    avatarFrame.innerHTML = ''

    const image = document.createElement('img')
    image.alt = `${resume.name} 头像`
    image.src = nextSrc
    avatarFrame.append(image)

    const nextHtml = resumeRef.current.innerHTML
    if (!writeStoredResumeHtml(nextHtml)) {
      setAvatarError('头像保存失败，图片可能太大。')
      return
    }

    setResumeHtml(nextHtml)
    setAvatarError('')
  }

  const handleAvatarUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    if (!file.type.startsWith('image/')) {
      setAvatarError('请选择图片文件。')
      return
    }

    if (file.size > MAX_RESUME_AVATAR_SOURCE_BYTES) {
      setAvatarError('头像图片请控制在 8MB 内。')
      return
    }

    try {
      const nextSrc = await createResumeAvatarDataUrl(file)
      saveAvatarToResume(nextSrc)
    } catch {
      setAvatarError('头像读取失败，请换一张图片再试。')
    }
  }

  const handleResumeClick = (event: ReactMouseEvent<HTMLElement>) => {
    if (findResumeAvatarFrame(event.target)) {
      event.preventDefault()
      openAvatarPicker()
    }
  }

  const handleResumeKeyDown = (event: ReactKeyboardEvent<HTMLElement>) => {
    if (!findResumeAvatarFrame(event.target) || (event.key !== 'Enter' && event.key !== ' ')) {
      return
    }

    event.preventDefault()
    openAvatarPicker()
  }

  return (
    <>
      <section className="section resume-page" id="resume">
        <div className="resume-toolbar" aria-label="Resume actions">
          <a className="secondary-action" href="/resume/resume.pdf" target="_blank" rel="noreferrer">
            <Download size={16} />
            PDF
          </a>
        </div>
        <input
          accept="image/*"
          aria-label="上传简历头像"
          className="resume-avatar-input"
          onChange={handleAvatarUpload}
          ref={avatarInputRef}
          type="file"
        />
        {avatarError && (
          <p className="resume-avatar-error" role="alert">
            {avatarError}
          </p>
        )}

        <article
          className="resume-sheet"
          dangerouslySetInnerHTML={{ __html: resumeHtml }}
          onClick={handleResumeClick}
          onKeyDown={handleResumeKeyDown}
          ref={resumeRef}
        />
      </section>
    </>
  )
}

function KnowledgeAgentPage() {
  return (
    <section className="agent-page">
      <div className="agent-frame-wrap">
        <iframe
          className="agent-frame"
          src={KNOWLEDGE_AGENT_URL}
          title="Knowledge Agent workspace"
        />
      </div>
    </section>
  )
}

function SnakeGame() {
  const [snake, setSnake] = useState<Cell[]>(() => cloneInitialSnake())
  const [foods, setFoods] = useState<Food[]>(() => appendFoods(INITIAL_SNAKE, [], 1))
  const [direction, setDirection] = useState<Direction>('right')
  const [nextDirection, setNextDirection] = useState<Direction>('right')
  const [isRunning, setIsRunning] = useState(false)
  const [isGameOver, setIsGameOver] = useState(false)
  const [isLifePause, setIsLifePause] = useState(false)
  const [isSlowed, setIsSlowed] = useState(false)
  const [lives, setLives] = useState(0)
  const [lastPower, setLastPower] = useState<PowerUp | null>(null)
  const [score, setScore] = useState(0)
  const [bestScore, setBestScore] = useState(readSnakeBestScore)
  const directionRef = useRef<Direction>('right')
  const nextDirectionRef = useRef<Direction>('right')

  useEffect(() => {
    directionRef.current = direction
  }, [direction])

  const resetGame = useCallback((shouldRun = false) => {
    const freshSnake = cloneInitialSnake()
    setSnake(freshSnake)
    setFoods(appendFoods(freshSnake, [], 1))
    setDirection('right')
    setNextDirection('right')
    directionRef.current = 'right'
    nextDirectionRef.current = 'right'
    setScore(0)
    setIsLifePause(false)
    setIsGameOver(false)
    setIsSlowed(false)
    setLives(0)
    setLastPower(null)
    setIsRunning(shouldRun)
  }, [])

  const queueDirection = useCallback(
    (candidate: Direction) => {
      if (OPPOSITE_DIRECTIONS[directionRef.current] === candidate) {
        return
      }

      nextDirectionRef.current = candidate
      setNextDirection(candidate)
      if (!isGameOver) {
        setIsLifePause(false)
        setIsRunning(true)
      }
    },
    [isGameOver],
  )

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const keyDirections: Record<string, Direction> = {
        ArrowUp: 'up',
        w: 'up',
        W: 'up',
        ArrowDown: 'down',
        s: 'down',
        S: 'down',
        ArrowLeft: 'left',
        a: 'left',
        A: 'left',
        ArrowRight: 'right',
        d: 'right',
        D: 'right',
      }
      const chosenDirection = keyDirections[event.key]

      if (!chosenDirection) {
        return
      }

      event.preventDefault()
      queueDirection(chosenDirection)
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [queueDirection])

  useEffect(() => {
    if (!isRunning || isGameOver || isLifePause) {
      return undefined
    }

    const timer = window.setInterval(() => {
      setSnake((currentSnake) => {
        const selectedDirection = nextDirectionRef.current
        const delta = DIRECTION_DELTAS[selectedDirection]
        const head = currentSnake[0]
        const nextHead = { x: wrapBoard(head.x + delta.x), y: wrapBoard(head.y + delta.y) }
        const eatenFood = foods.find((food) => sameCell(nextHead, food))
        const ateFood = Boolean(eatenFood)
        const bodyToCheck = ateFood ? currentSnake : currentSnake.slice(0, -1)
        const hitSelf = bodyToCheck.some((part) => sameCell(part, nextHead))

        if (hitSelf) {
          if (lives > 0) {
            setLives((currentLives) => Math.max(0, currentLives - 1))
            setIsLifePause(true)
            setIsRunning(false)
            setLastPower(null)
            return currentSnake
          }

          setIsRunning(false)
          setIsGameOver(true)
          return currentSnake
        }

        const nextSnake = ateFood ? [nextHead, ...currentSnake] : [nextHead, ...currentSnake.slice(0, -1)]
        setDirection(selectedDirection)
        directionRef.current = selectedDirection

        if (eatenFood) {
          setFoods((currentFoods) => {
            const remainingFoods = currentFoods.filter((food) => food.id !== eatenFood.id)
            const nextFoods = appendFoods(nextSnake, remainingFoods, 1)

            if (eatenFood.power === 'burst') {
              return appendFoods(nextSnake, nextFoods, 5)
            }

            return nextFoods
          })
          setScore((currentScore) => {
            const nextScore = currentScore + 1
            setBestScore((currentBest) => {
              if (nextScore <= currentBest) {
                return currentBest
              }

              writeSnakeBestScore(nextScore)
              return nextScore
            })
            return nextScore
          })

          if (eatenFood.power === 'slow') {
            setIsSlowed(true)
            setLastPower('slow')
          } else if (eatenFood.power === 'life') {
            setLives((currentLives) => currentLives + 1)
            setLastPower('life')
          } else if (eatenFood.power === 'burst') {
            setLastPower('burst')
          }
        }

        return nextSnake
      })
    }, isSlowed ? SNAKE_TICK_MS * 2 : SNAKE_TICK_MS)

    return () => window.clearInterval(timer)
  }, [foods, isGameOver, isLifePause, isRunning, isSlowed, lives])

  const toggleRun = () => {
    if (isGameOver) {
      resetGame(true)
      return
    }

    setIsRunning((running) => !running)
  }

  const gameStatus = isGameOver
    ? '撞到自己'
    : isLifePause
      ? '生命保护，按方向键继续'
      : isRunning
        ? '奔跑中'
        : score > 0
          ? '暂停中'
          : '待启动'

  return (
    <article className="snake-console">
      <div className="snake-topline">
        <div className="snake-copy">
          <p className="eyebrow">Tiny Game</p>
          <h2>贪吃蛇</h2>
          <p>边界会连到另一边。糖果偶尔藏着道具：慢速、糖果雨，或者多一条命。</p>
        </div>

        <div className="snake-stats" aria-label="Game score">
          <div>
            <span>分数</span>
            <strong>{score}</strong>
          </div>
          <div>
            <span>最高</span>
            <strong>{bestScore}</strong>
          </div>
          <div>
            <span>生命</span>
            <strong>{lives}</strong>
          </div>
        </div>
      </div>

      <div className="snake-stage">
        <div
          className={`snake-board ${isGameOver ? 'is-game-over' : ''}`}
          aria-label={`贪吃蛇棋盘，当前分数 ${score}，糖果 ${foods.length} 个`}
          role="img"
        >
          {BOARD_CELLS.map((cell) => {
            const snakeIndex = snake.findIndex((part) => sameCell(part, cell))
            const food = foods.find((item) => sameCell(item, cell))
            const cellClasses = [
              'snake-cell',
              snakeIndex === 0 ? 'is-head' : '',
              snakeIndex > 0 ? 'is-body' : '',
              food ? 'is-food' : '',
              food?.power ? 'is-power-food' : '',
              food?.power ? `is-${food.power}` : '',
            ]
              .filter(Boolean)
              .join(' ')

            return <span className={cellClasses} key={`${cell.x}-${cell.y}`} />
          })}
        </div>

        <div className="snake-side">
          <div className="snake-status" aria-live="polite">
            <Gamepad2 size={19} strokeWidth={1.8} />
            <span>{gameStatus}</span>
          </div>

          <div className="snake-effects" aria-label="Power up status">
            <span>糖果 {foods.length}</span>
            <span className={isSlowed ? 'is-on' : ''}>速度 {isSlowed ? '1/2' : '正常'}</span>
            <span className={lives > 0 ? 'is-on' : ''}>生命 {lives}</span>
            <span>{lastPower ? `刚触发 ${POWER_UP_LABELS[lastPower]}` : '道具概率 5%'}</span>
          </div>

          <div className="snake-actions">
            <button className="secondary-action snake-command" onClick={toggleRun} type="button">
              {isRunning ? <Pause size={16} /> : <Play size={16} />}
              {isGameOver ? '再来' : isRunning ? '暂停' : '开始'}
            </button>
            <button className="secondary-action snake-command" onClick={() => resetGame(false)} type="button">
              <RotateCcw size={16} />
              重置
            </button>
          </div>

          <div className="snake-pad" aria-label="Direction controls">
            <button
              aria-label="向上"
              aria-pressed={nextDirection === 'up'}
              className={`snake-pad-button is-up ${nextDirection === 'up' ? 'is-active' : ''}`}
              onClick={() => queueDirection('up')}
              type="button"
            >
              <ArrowUp size={20} />
            </button>
            <button
              aria-label="向左"
              aria-pressed={nextDirection === 'left'}
              className={`snake-pad-button is-left ${nextDirection === 'left' ? 'is-active' : ''}`}
              onClick={() => queueDirection('left')}
              type="button"
            >
              <ArrowLeft size={20} />
            </button>
            <button
              aria-label="向下"
              aria-pressed={nextDirection === 'down'}
              className={`snake-pad-button is-down ${nextDirection === 'down' ? 'is-active' : ''}`}
              onClick={() => queueDirection('down')}
              type="button"
            >
              <ArrowDown size={20} />
            </button>
            <button
              aria-label="向右"
              aria-pressed={nextDirection === 'right'}
              className={`snake-pad-button is-right ${nextDirection === 'right' ? 'is-active' : ''}`}
              onClick={() => queueDirection('right')}
              type="button"
            >
              <ArrowRight size={20} />
            </button>
          </div>
        </div>
      </div>
    </article>
  )
}

function LabPage() {
  const [activeLab, setActiveLab] = useState<'snake' | null>(null)
  const [showTradingQr, setShowTradingQr] = useState(false)
  const [tradingQrSrc, setTradingQrSrc] = useState(() => readStoredTradingQrSrc())
  const [qrImageError, setQrImageError] = useState('')
  const qrFileInputRef = useRef<HTMLInputElement>(null)
  const tradingQrStatus = tradingQrSrc === TRADING_QR_DEFAULT_SRC ? '7月28日前有效' : '已更换图片'

  const openTradingQrPicker = () => {
    setQrImageError('')
    if (qrFileInputRef.current) {
      qrFileInputRef.current.value = ''
      qrFileInputRef.current.click()
    }
  }

  const showQrImageError = (message: string) => {
    setQrImageError(message)
    setShowTradingQr(true)
  }

  const handleTradingQrUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    if (!file.type.startsWith('image/')) {
      showQrImageError('请选择图片文件。')
      return
    }

    if (file.size > MAX_TRADING_QR_IMAGE_BYTES) {
      showQrImageError('图片请控制在 1.5MB 内。')
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const nextSrc = typeof reader.result === 'string' ? reader.result : ''

      if (!nextSrc.startsWith('data:image/') || nextSrc.length > MAX_TRADING_QR_DATA_URL_LENGTH) {
        showQrImageError('图片读取失败，请换一张更小的图片。')
        return
      }

      if (!writeStoredTradingQrSrc(nextSrc)) {
        showQrImageError('浏览器没有保存成功，请换一张更小的图片。')
        return
      }

      setTradingQrSrc(nextSrc)
      setQrImageError('')
    }
    reader.onerror = () => showQrImageError('图片读取失败，请再试一次。')
    reader.readAsDataURL(file)
  }

  const resetTradingQrImage = () => {
    clearStoredTradingQrSrc()
    setTradingQrSrc(TRADING_QR_DEFAULT_SRC)
    setQrImageError('')
  }

  return (
    <section className="detail-page lab-page">
      <div className="lab-hero">
        <p className="eyebrow">Lab</p>
        <h1>实验区</h1>
        <p className="detail-lede">
          小游戏、小工具和交互 Demo 都收进方片盒子里。打开一块方片，就进入对应的小空间。
        </p>
      </div>

      {activeLab === null ? (
        <div className="lab-tiles" aria-label="Lab showcase">
          {labTiles.map((tile) => (
            <button
              className={`lab-tile ${tile.tone}`}
              key={tile.id}
              onClick={() => setActiveLab(tile.id)}
              type="button"
            >
              <span className="lab-tile-icon">
                <Gamepad2 size={20} />
              </span>
              <span className="lab-tile-kicker">{tile.kicker}</span>
              <h3>{tile.title}</h3>
              <span className="lab-tile-status">{tile.status}</span>
            </button>
          ))}
          <input
            accept="image/*"
            aria-label="更换 Trading Tycoon 二维码图片"
            className="qr-upload-input"
            onChange={handleTradingQrUpload}
            ref={qrFileInputRef}
            type="file"
          />
          <article className="lab-qr-card">
            <button
              aria-label="放大 Trading Tycoon 体验版二维码"
              className="lab-qr-preview"
              onClick={() => setShowTradingQr(true)}
              type="button"
            >
              <div>
                <span className="lab-tile-kicker">小程序体验版</span>
                <h3>Trading Tycoon</h3>
                <p>扫码体验 A 股 K 线训练与好友 PK 小程序。</p>
              </div>
              <img
                alt="Trading Tycoon 体验版二维码，7月28日前有效"
                src={tradingQrSrc}
              />
            </button>
            <div className="lab-qr-actions">
              <span className="lab-tile-status">{tradingQrStatus}</span>
              <button className="qr-upload-button" onClick={openTradingQrPicker} type="button">
                <Upload size={14} />
                更换
              </button>
            </div>
          </article>
          {showTradingQr && (
            <div className="qr-lightbox" onClick={() => setShowTradingQr(false)} role="presentation">
              <div
                aria-label="Trading Tycoon 体验版二维码"
                aria-modal="true"
                className="qr-lightbox-card"
                onClick={(event) => event.stopPropagation()}
                role="dialog"
              >
                <img
                  alt="Trading Tycoon 体验版二维码，7月28日前有效"
                  src={tradingQrSrc}
                />
                <h3>Trading Tycoon</h3>
                <div className="qr-lightbox-actions">
                  <button className="qr-upload-button" onClick={openTradingQrPicker} type="button">
                    <Upload size={15} />
                    更换图片
                  </button>
                  <button
                    className="qr-reset-button"
                    disabled={tradingQrSrc === TRADING_QR_DEFAULT_SRC}
                    onClick={resetTradingQrImage}
                    type="button"
                  >
                    <RotateCcw size={15} />
                    恢复默认
                  </button>
                </div>
                <span className="lab-tile-status">{tradingQrStatus}</span>
                {qrImageError && (
                  <p className="qr-image-error" role="alert">
                    {qrImageError}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="lab-game-view">
          <button className="secondary-action lab-back-button" onClick={() => setActiveLab(null)} type="button">
            <ArrowLeft size={16} />
            返回 Lab
          </button>
          <SnakeGame />
        </div>
      )}
    </section>
  )
}

function NotFoundPage() {
  return (
    <section className="detail-page">
      <p className="eyebrow">404</p>
      <h1>页面不存在</h1>
      <p className="detail-lede">这个地址还没有对应内容。</p>
      <Link className="primary-action" to="/">
        回到首页
        <ArrowUpRight size={17} />
      </Link>
    </section>
  )
}

function App() {
  return <AppShell />
}

export default App
