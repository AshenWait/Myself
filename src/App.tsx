import {
  ArrowUpRight,
  Blocks,
  FileText,
  FlaskConical,
  GitBranch,
  Home,
  Image,
  MapPin,
  Menu,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, Route, Routes, useLocation, useParams } from 'react-router-dom'
import './App.css'
import { projects } from './content/projects'
import { resume } from './content/resume'

const navItems = [
  { label: '概览', href: '/', icon: Home },
  { label: '简历', href: '/#resume', icon: FileText },
  { label: '项目', href: '/#projects', icon: Blocks },
  { label: 'Lab', href: '/lab', icon: FlaskConical },
]

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
            <span className="brand-mark">AW</span>
            <span>
              <span className="brand-name">AshenWait</span>
              <span className="brand-role">AI Portfolio</span>
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
          <span className="brand-mark">AW</span>
          <span className="brand-name">AshenWait</span>
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
          <Route element={<ProjectPage />} path="/projects/:slug" />
          <Route element={<LabPage />} path="/lab/*" />
          <Route element={<NotFoundPage />} path="*" />
        </Routes>
      </main>
    </div>
  )
}

function HomePage() {
  return (
    <>
      <section className="hero-section" id="top">
        <div className="hero-copy">
          <p className="eyebrow">Personal portfolio</p>
          <h1>{resume.name}</h1>
          <p className="hero-role">{resume.role}</p>
          <p className="hero-summary">{resume.summary}</p>

          <div className="hero-actions">
            <a className="primary-action" href="#projects">
              查看项目
              <ArrowUpRight size={17} />
            </a>
            <a className="secondary-action" href="/resume/resume.png" target="_blank" rel="noreferrer">
              简历图片
              <Image size={17} />
            </a>
          </div>
        </div>

        <div className="hero-panel" aria-label="Profile snapshot">
          <div className="signal-row">
            <span>RAG</span>
            <span>Agent</span>
            <span>Trace</span>
          </div>
          <div className="terminal-card">
            <span className="terminal-dot"></span>
            <span>build: portfolio ready</span>
          </div>
          <div className="hero-stats">
            <div>
              <strong>01</strong>
              <span>当前项目</span>
            </div>
            <div>
              <strong>63</strong>
              <span>项目推进天数</span>
            </div>
            <div>
              <strong>30</strong>
              <span>RAG 评测题</span>
            </div>
          </div>
        </div>
      </section>

      <section className="section" id="resume">
        <div className="section-heading">
          <p className="eyebrow">Resume</p>
          <h2>简历</h2>
        </div>

        <div className="resume-grid">
          <article className="resume-main">
            <div className="resume-title">
              <div>
                <h3>{resume.name}</h3>
                <p>{resume.role}</p>
              </div>
              <span className="location">
                <MapPin size={16} />
                {resume.location}
              </span>
            </div>

            <p className="resume-summary">{resume.summary}</p>

            <div className="focus-list" aria-label="Focus areas">
              {resume.focus.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>

            <div className="resume-links">
              {resume.links.map((link) => (
                <a href={link.href} key={link.href} target="_blank" rel="noreferrer">
                  {link.label}
                  <ArrowUpRight size={15} />
                </a>
              ))}
            </div>
          </article>

          <aside className="resume-image-panel">
            <img alt="Resume preview" src="/resume/resume.png" />
          </aside>
        </div>

        <div className="resume-details">
          {resume.skills.map((section) => (
            <article className="detail-block" key={section.title}>
              <h3>{section.title}</h3>
              <ul>
                {section.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
          {resume.timeline.map((section) => (
            <article className="detail-block wide" key={section.title}>
              <h3>{section.title}</h3>
              <ul>
                {section.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="section" id="projects">
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

      <section className="section lab-strip" id="lab">
        <div>
          <p className="eyebrow">Lab</p>
          <h2>网页小游戏与实验区</h2>
          <p>这里预留给后续小游戏、交互 Demo 和小工具。当前先保持入口，避免提前引入复杂逻辑。</p>
        </div>
        <Link className="primary-action" to="/lab">
          进入 Lab
          <ArrowUpRight size={17} />
        </Link>
      </section>
    </>
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
      <Link className="back-link" to="/#projects">
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
          <a className="primary-action repo-action" href={project.repoUrl} target="_blank" rel="noreferrer">
            打开 GitHub
            <GitBranch size={17} />
          </a>
        </article>
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
