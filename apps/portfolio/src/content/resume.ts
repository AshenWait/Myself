export type ResumeLink = {
  label: string
  href: string
}

export type ResumeSection = {
  title: string
  items: string[]
}

export type ResumeProfile = {
  name: string
  role: string
  location: string
  summary: string
  links: ResumeLink[]
  focus: string[]
  skills: ResumeSection[]
  timeline: ResumeSection[]
}

export const resume: ResumeProfile = {
  name: 'AshenWait',
  role: 'AI 应用开发者 / RAG Agent 工程方向',
  location: 'China',
  summary:
    '围绕企业知识库、RAG、Agent 工具调用和可观测性做持续实践。当前作品集先展示 Knowledge Agent 项目，后续会继续补充完整简历经历、线上 Demo、小游戏和更多工程项目。',
  links: [
    {
      label: 'GitHub',
      href: 'https://github.com/AshenWait',
    },
    {
      label: 'Knowledge Agent',
      href: 'https://github.com/AshenWait/knowledge-agent',
    },
  ],
  focus: [
    'RAG 问答链路',
    'Agent 工具调用',
    'FastAPI 服务',
    'PostgreSQL + pgvector',
    '前端工作台',
    'Trace 与评测',
  ],
  skills: [
    {
      title: 'Backend',
      items: ['Python', 'FastAPI', 'Pydantic', 'SQLAlchemy', 'PostgreSQL'],
    },
    {
      title: 'AI Engineering',
      items: ['RAG', 'Embedding', 'pgvector', 'Tool Calling', 'Guardrails'],
    },
    {
      title: 'Frontend & Delivery',
      items: ['React', 'TypeScript', 'Vite', 'Docker', 'Nginx'],
    },
  ],
  timeline: [
    {
      title: '当前重点',
      items: [
        '把企业知识库 Agent 做成可演示、可部署、可写进简历的完整项目。',
        '持续补齐文档解析、向量检索、引用来源、流式输出、Trace 面板和离线评测。',
      ],
    },
    {
      title: '待补充',
      items: [
        '真实工作经历、教育背景、联系方式和简历图片会在你提供正式内容后替换。',
      ],
    },
  ],
}
