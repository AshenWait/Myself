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
  name: '杨鹏坤',
  role: '2027 届应届生 | AI 应用开发实习 / 大模型应用实习 / Python 后端实习',
  location: '南京',
  summary:
    '面向 AI 应用实习，把 Demo 做成可演示、可调试的原型。主要学习 RAG、Agent Tool Calling 和 Python 后端开发，通过个人项目搭建知识库问答和小程序体验版，能在 AI Agent 辅助下完成需求拆解、代码实现、联调和运行验证。',
  links: [
    {
      label: '手机',
      href: 'tel:+8619732031811',
    },
    {
      label: '邮箱',
      href: 'mailto:yangpengkun2020@gmail.com',
    },
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
    'RAG / Embedding / 向量检索',
    'Python 后端与 FastAPI',
    'Codex / Claude 辅助开发',
    '运行结果校验',
    'Tool Calling / Trace',
    '前后端联调',
  ],
  skills: [
    {
      title: '大模型应用',
      items: ['RAG', 'Embedding', '向量检索', 'pgvector', '引用来源', '无引用拒答', 'Tool Calling', 'Trace'],
    },
    {
      title: 'Python 后端',
      items: ['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'Git'],
    },
    {
      title: '前端与全栈',
      items: ['React', 'Vue3', '前后端联调'],
    },
    {
      title: 'Agent 协作工程',
      items: ['熟练使用 Codex / Claude 开发', '辅助需求拆解', '代码生成', '文档整理', '能通过运行结果校验'],
    },
  ],
  timeline: [
    {
      title: '教育背景与资质证明',
      items: [
        '金陵科技学院 · 数字媒体技术，本科在读，2025.09 - 2027.06 。',
        '无锡科技职业学院 · 物联网应用技术，专科，2020.10 - 2023.06。',
        '阿里云大模型工程师 ACA 认证，2026.05.06；',
        '全国计算机等级考试二级 Python，2021.03。',
        '参军 2 年，服役期间获嘉奖一次。',
      ],
    },
    {
      title: 'Knowledge Agent: 企业知识库 RAG + Agent 原型系统（重点项目）',
      items: [
        '技术栈：个人项目 | AI 应用开发学习 / Python 后端 | Codex / Claude / FastAPI / RAG / Agent / pgvector / Trace。',
        '核心功能：面向企业知识库问答场景，搭建文档处理、向量检索、RAG 问答和工具调用原型，重点练习让回答有引用、可排查、可演示。',
        '完成基础 RAG 链路：文档上传解析、chunk 切分、embedding 入库、pgvector 检索、问答生成和引用来源展示，并接入前端工作台联调演示。',
        '尝试接入 Agent Tool Calling，设计文档列表、检索、总结、创建笔记等工具；写入类工具加入参数校验、会话白名单和确认步骤。',
        '加入 prompt injection 检查、无引用拒答、输出日志和 run_id 记录，便于复盘模型调用、工具调用和错误原因。',
        '编写离线评测脚本和固定题集，记录 top-3 检索命中、引用完整性和失败原因，用于调整 chunk size、top_k 和提示词。',
      ],
    },
    {
      title: 'SilentElderSense: 面向独居老人的异常行为识别与应急响应系统（负责前后端，竞赛项目）',
      items: [
        '技术栈：Vue 3 前端 + Python Quart 后端 + SQLite 数据库 + ONNX 计算机视觉推理。',
        '面向独居老人异常行为识别场景，参与后端接口和事件链路开发，把视频检测结果保存为可查询、可追踪的风险事件。',
        '使用 AI Agent 辅助阅读既有模块、梳理接口职责和生成初版代码，再通过联调问题和运行结果逐步修正。',
        '参与视频上传、WebSocket 实时检测、识别结果解析、事件生命周期记录和管理端查询等接口开发。',
        '参与事件数据模型设计，记录用户、video_id、person_id、事件类型、风险等级、起止时间、快照路径等字段，支持分页筛选和状态更新。',
      ],
    },
    {
      title: 'Trading Tycoon: A 股 K 线训练与好友 PK 小程序体验版（个人作品）',
      items: [
        '面向 A 股 K 线训练和好友 PK 场景，在 Codex 辅助下完成需求拆解、界面迭代、真机问题定位和云函数联调，交付可测试体验版。',
        '实现月 / 周 / 日混合 K 线训练盘，接入本地化 A 股数据，使用 Canvas 渲染涨跌停高亮、买卖点和 MA，并支持手势缩放。',
        '接入微信云开发实现好友 PK 房基础流程，包括房间创建、邀请加入、状态轮询、双方确认推进交易日和收益率结算。',
      ],
    },
  ],
}
