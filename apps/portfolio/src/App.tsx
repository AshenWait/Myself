import {
  ArrowUpRight,
  Blocks,
  Download,
  FileText,
  FlaskConical,
  GitBranch,
  Menu,
  Pencil,
  RotateCcw,
  Save,
  X,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, Route, Routes, useLocation, useParams } from 'react-router-dom'
import './App.css'
import { projects } from './content/projects'
import { resume } from './content/resume'

const navItems = [
  { label: '简历', href: '/', icon: FileText },
  { label: '项目', href: '/projects', icon: Blocks },
  { label: 'Agent', href: '/knowledge-agent', icon: Blocks },
  { label: 'Lab', href: '/lab', icon: FlaskConical },
]

const KNOWLEDGE_AGENT_URL = import.meta.env.VITE_KNOWLEDGE_AGENT_URL || 'http://127.0.0.1:5174/'
const RESUME_STORAGE_KEY = 'portfolio.resume.html'
const DEFAULT_RESUME_HTML = createResumeHtml()

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function linkText(href: string) {
  return href.replace(/^mailto:/, '').replace(/^tel:\+?86?/, '')
}

function listItems(items: string[]) {
  return items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')
}

function createResumeHtml() {
  const [education, ...projects] = resume.timeline

  return `
    <header class="resume-sheet-header">
      <div>
        <h1>${escapeHtml(resume.name)}</h1>
        <p class="resume-role">${escapeHtml(resume.role)}</p>
        <div class="resume-contact">
          <span>城市：${escapeHtml(resume.location)}</span>
          ${resume.links
            .slice(0, 3)
            .map(
              (link) =>
                `<a href="${escapeHtml(link.href)}" target="_blank" rel="noreferrer">${escapeHtml(link.label)}：${escapeHtml(
                  linkText(link.href),
                )}</a>`,
            )
            .join('')}
        </div>
      </div>
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
      <h2>Positioning</h2>
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
          <Route element={<ProjectsPage />} path="/projects" />
          <Route element={<ProjectPage />} path="/projects/:slug" />
          <Route element={<LabPage />} path="/lab/*" />
          <Route element={<NotFoundPage />} path="*" />
        </Routes>
      </main>
    </div>
  )
}

function HomePage() {
  const resumeRef = useRef<HTMLElement>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [resumeHtml, setResumeHtml] = useState(() => localStorage.getItem(RESUME_STORAGE_KEY) || DEFAULT_RESUME_HTML)

  const saveResume = () => {
    const nextHtml = resumeRef.current?.innerHTML || DEFAULT_RESUME_HTML
    localStorage.setItem(RESUME_STORAGE_KEY, nextHtml)
    setResumeHtml(nextHtml)
    setIsEditing(false)
  }

  const resetResume = () => {
    localStorage.removeItem(RESUME_STORAGE_KEY)
    setResumeHtml(DEFAULT_RESUME_HTML)
    setIsEditing(false)
  }

  const autosaveResume = () => {
    if (resumeRef.current) {
      localStorage.setItem(RESUME_STORAGE_KEY, resumeRef.current.innerHTML)
    }
  }

  return (
    <>
      <section className="section resume-page" id="resume">
        <div className="resume-toolbar" aria-label="Resume actions">
          <button
            className={isEditing ? 'primary-action' : 'secondary-action'}
            onClick={() => setIsEditing((editing) => !editing)}
            type="button"
          >
            <Pencil size={16} />
            {isEditing ? '退出编辑' : '编辑简历'}
          </button>
          <button className="secondary-action" onClick={saveResume} type="button">
            <Save size={16} />
            保存
          </button>
          <button className="secondary-action" onClick={resetResume} type="button">
            <RotateCcw size={16} />
            恢复默认
          </button>
          <a className="secondary-action" href="/resume/resume.pdf" target="_blank" rel="noreferrer">
            <Download size={16} />
            PDF
          </a>
        </div>

        <article
          className={`resume-sheet ${isEditing ? 'is-editing' : ''}`}
          contentEditable={isEditing}
          dangerouslySetInnerHTML={{ __html: resumeHtml }}
          onInput={autosaveResume}
          ref={resumeRef}
          suppressContentEditableWarning
        />

        <div className="resume-next">
          <Link className="primary-action" to="/projects">
            查看项目
            <ArrowUpRight size={17} />
          </Link>
        </div>
      </section>
    </>
  )
}

function ProjectsPage() {
  return (
    <section className="section projects-page" id="projects">
      <div className="section-heading">
        <p className="eyebrow">Projects</p>
        <h2>项目</h2>
      </div>

      <div className="project-list">
        {projects.map((project) => (
          <article className="project-card" key={project.slug}>
            <div className="project-card-header">
              <div>
                <span className="project-status">{project.status}</span>
                <h3>{project.name}</h3>
                <p>{project.tagline}</p>
              </div>
              <span className="project-year">{project.period}</span>
            </div>

            <p className="project-summary">{project.summary}</p>

            <div className="metric-grid">
              {project.metrics.map((metric) => (
                <div key={metric.label}>
                  <strong>{metric.value}</strong>
                  <span>{metric.label}</span>
                </div>
              ))}
            </div>

            <div className="stack-list">
              {project.stack.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>

            <div className="project-actions">
              {project.appPath && (
                <Link to={project.appPath}>
                  打开工作台
                  <ArrowUpRight size={16} />
                </Link>
              )}
              <Link to={`/projects/${project.slug}`}>
                项目详情
                <ArrowUpRight size={16} />
              </Link>
              <a href={project.repoUrl} target="_blank" rel="noreferrer">
                GitHub
                <GitBranch size={16} />
              </a>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

function ProjectPage() {
  const { slug } = useParams()
  const project = projects.find((item) => item.slug === slug)

  if (!project) {
    return <NotFoundPage />
  }

  return (
    <section className="detail-page">
      <Link className="back-link" to="/projects">
        返回项目
      </Link>
      <p className="eyebrow">{project.status}</p>
      <h1>{project.name}</h1>
      <p className="detail-lede">{project.summary}</p>

      <div className="metric-grid detail-metrics">
        {project.metrics.map((metric) => (
          <div key={metric.label}>
            <strong>{metric.value}</strong>
            <span>{metric.label}</span>
          </div>
        ))}
      </div>

      <div className="detail-columns">
        <article>
          <h2>项目亮点</h2>
          <ul className="check-list">
            {project.highlights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article>
          <h2>技术栈</h2>
          <div className="stack-list large">
            {project.stack.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
          {project.appPath && (
            <Link className="primary-action repo-action" to={project.appPath}>
              打开工作台
              <ArrowUpRight size={17} />
            </Link>
          )}
          <a className="primary-action repo-action" href={project.repoUrl} target="_blank" rel="noreferrer">
            打开 GitHub
            <GitBranch size={17} />
          </a>
        </article>
      </div>
    </section>
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

function LabPage() {
  return (
    <section className="detail-page">
      <p className="eyebrow">Lab</p>
      <h1>实验区</h1>
      <p className="detail-lede">
        后续网页小游戏、小工具和交互 Demo 会放在这里。当前版本保留路由和导航入口，方便逐步扩展。
      </p>
      <div className="empty-lab">
        <FlaskConical size={34} strokeWidth={1.6} />
        <span>Next build slot is open.</span>
      </div>
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
