export type ProjectMetric = {
  label: string
  value: string
}

export type Project = {
  slug: string
  name: string
  tagline: string
  repoUrl: string
  appPath?: string
  status: string
  period: string
  summary: string
  stack: string[]
  highlights: string[]
  metrics: ProjectMetric[]
}

export const projects: Project[] = [
  {
    slug: 'knowledge-agent',
    name: 'Knowledge Agent',
    tagline: '企业知识库 RAG + Agent 项目',
    repoUrl: 'https://github.com/AshenWait/knowledge-agent',
    appPath: '/knowledge-agent',
    status: '持续迭代',
    period: '2026',
    summary:
      '支持上传 PDF、txt、markdown 文档，解析并切分为 chunks，使用 PostgreSQL + pgvector 做相似度检索，再基于 RAG 生成带引用来源的回答。',
    stack: [
      'Python',
      'FastAPI',
      'PostgreSQL',
      'pgvector',
      'SQLAlchemy',
      'React',
      'Docker',
    ],
    highlights: [
      '文档上传、解析、chunk 切分、embedding 与语义搜索形成完整入库链路。',
      'RAG 问答返回引用来源，包含文档名、页码、chunk 内容和 distance。',
      '支持聊天会话、历史上下文、流式输出和 RAG 调用日志查询。',
      'Agent 工具系统区分只读、写入、危险工具，并加入白名单和确认策略。',
      'Trace 面板记录模型与工具调用步骤，离线评测脚本统计检索命中率和引用完整率。',
    ],
    metrics: [
      {
        label: '评测题',
        value: '30',
      },
      {
        label: '核心接口',
        value: '10+',
      },
      {
        label: '项目周期',
        value: '63 days',
      },
    ],
  },
]
