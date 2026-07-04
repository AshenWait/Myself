import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

const API_BASE_URL = 'http://127.0.0.1:8000'

function formatDate(value) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

async function readError(response) {
  try {
    const data = await response.json()
    return data.detail || '请求失败，请稍后重试'
  } catch {
    return '请求失败，请稍后重试'
  }
}

function App() {
  const [documents, setDocuments] = useState([])
  const [selectedDocumentId, setSelectedDocumentId] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [isDraggingFile, setIsDraggingFile] = useState(false)
  const [question, setQuestion] = useState('这个文档是做什么用的？')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [traceRunId, setTraceRunId] = useState('')
  const [traceSteps, setTraceSteps] = useState([])
  const [isLoadingTrace, setIsLoadingTrace] = useState(false)
  const fileInputRef = useRef(null)


  const selectedDocument = useMemo(
    () =>
      documents.find((document) => String(document.id) === selectedDocumentId),
    [documents, selectedDocumentId],
  )

  const loadDocuments = useCallback(async () => {
    setIsLoadingDocuments(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/documents`)
      if (!response.ok) {
        throw new Error(await readError(response))
      }

      const data = await response.json()
      setDocuments(data)

      if (!selectedDocumentId && data.length > 0) {
        setSelectedDocumentId(String(data[0].id))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoadingDocuments(false)
    }
  }, [selectedDocumentId])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  async function handleUpload(event) {
    event.preventDefault()

    if (!selectedFile) {
      setError('请先选择一个文件')
      return
    }

    const formData = new FormData()
    formData.append('file', selectedFile)
    setIsUploading(true)
    setNotice('')
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      const uploaded = await response.json()
      setNotice(`上传成功：${uploaded.filename}`)
      setSelectedFile(null)
      await loadDocuments()
      setSelectedDocumentId(String(uploaded.document_id))
    } catch (err) {
      setError(err.message)
    } finally {
      setIsUploading(false)
    }
  }

  function pickFile(file) {
    if (!file) {
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      return
    }

    setSelectedFile(file)
    setNotice(`已选择：${file.name}`)
    setError('')
  }

  function handleDragOver(event) {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'copy'
    setIsDraggingFile(true)
  }

  function handleDragLeave(event) {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setIsDraggingFile(false)
    }
  }

  function handleDrop(event) {
    event.preventDefault()
    setIsDraggingFile(false)

    const file = event.dataTransfer.files?.[0]
    pickFile(file || null)
  }
  //根据 run_id 调后端 trace API，把步骤加载到页面
  async function loadTrace(runId) {
    if (!runId.trim()) {
      setError('请输入 run_id')
      return
    }

    setIsLoadingTrace(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/traces/${runId.trim()}`)
      if (!response.ok) {
        throw new Error(await readError(response))
      }

      const data = await response.json()
      setTraceSteps(data)
    } catch (err) {
      setError(err.message)
      setTraceSteps([])
    } finally {
      setIsLoadingTrace(false)
    }
  }


  async function handleAsk() {
    const trimmedQuestion = question.trim()

    if (!trimmedQuestion) {
      setError('问题不能为空')
      return
    }

    setIsAsking(true)
    setAnswer('')
    setSources([])
    setNotice('')
    setError('')

    const payload = {
      message: trimmedQuestion,
      document_id: selectedDocumentId ? Number(selectedDocumentId) : null,
      session_id: sessionId,
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      const data = await response.json()
      setAnswer(data.reply)
      setSources(data.sources)
      setSessionId(data.session_id)
      setTraceRunId(data.run_id || '')
      if (data.run_id) {
        await loadTrace(data.run_id)
      }
      setNotice(`回答完成，耗时 ${data.latency_ms} ms`)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsAsking(false)
    }
  }

  function clearQuestion() {
    setQuestion('')
    setAnswer('')
    setSources([])
    setError('')
    setNotice('')
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Knowledge Agent · 第 5 周</p>
          <h1>知识库问答工作台</h1>
        </div>
        <div className="status-pill">前后端联调中</div>
      </header>

      {(notice || error) && (
        <section className={`banner ${error ? 'error' : 'success'}`}>
          {error || notice}
        </section>
      )}

      <section className="workspace" aria-label="知识库问答工作台">
        <aside className="panel side-panel">
          <div className="panel-heading">
            <p className="eyebrow">文档</p>
            <h2>上传资料</h2>
          </div>

          <form onSubmit={handleUpload}>
            <label
              className={`upload-box ${isDraggingFile ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.md,.markdown,.pdf"
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  pickFile(file || null)
                }}
              />
              <span className="upload-icon">+</span>
              <strong>{selectedFile?.name || '拖入文件或点击选择'}</strong>
              <small>支持 PDF、TXT、Markdown，最大 10MB</small>
              <span className="upload-hint">
                {isDraggingFile ? '松开鼠标即可添加文件' : '拖拽文件到这里会自动选中'}
              </span>
            </label>

            {selectedFile && (
              <div className="selected-file">
                <span>{selectedFile.name}</span>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => pickFile(null)}
                >
                  移除
                </button>
              </div>
            )}

            <button
              className="full-button"
              type="submit"
              disabled={isUploading}
            >
              {isUploading ? '上传并入库中...' : '上传到知识库'}
            </button>
          </form>

          <div className="document-list" aria-label="文档列表">
            <div className="list-title">
              <h2>文档列表</h2>
              <span>{isLoadingDocuments ? '刷新中' : `${documents.length} 个`}</span>
            </div>

            {documents.length === 0 && !isLoadingDocuments ? (
              <p className="empty-state">还没有文档，先上传一份资料。</p>
            ) : (
              documents.map((document) => (
                <button
                  className={`document-item ${
                    String(document.id) === selectedDocumentId ? 'active' : ''
                  }`}
                  key={document.id}
                  type="button"
                  onClick={() => setSelectedDocumentId(String(document.id))}
                >
                  <div>
                    <h3>{document.filename}</h3>
                    <p>
                      {document.page_count} 页 · {formatDate(document.created_at)}
                    </p>
                  </div>
                  <span>#{document.id}</span>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="panel chat-panel">
          <div className="panel-heading row-heading">
            <div>
              <p className="eyebrow">RAG 问答</p>
              <h2>向知识库提问</h2>
            </div>

            <label className="document-select">
              文档范围
              <select
                value={selectedDocumentId}
                onChange={(event) => setSelectedDocumentId(event.target.value)}
              >
                <option value="">全部文档</option>
                {documents.map((document) => (
                  <option key={document.id} value={document.id}>
                    {document.filename}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="question-area">
            <span>问题</span>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="例如：这个文档主要讲了什么？"
              rows="5"
            />
          </label>

          <div className="actions">
            <button type="button" onClick={handleAsk} disabled={isAsking}>
              {isAsking ? '思考中...' : '发送问题'}
            </button>
            <button type="button" className="secondary" onClick={clearQuestion}>
              清空
            </button>
          </div>

          <section className="answer-box" aria-label="回答区">
            <div className="answer-header">
              <h2>回答区</h2>
              <span>
                {selectedDocument ? `当前文档：${selectedDocument.filename}` : '全部文档'}
              </span>
            </div>
            <p>
              {isAsking
                ? '正在检索资料并生成回答...'
                : answer || '回答会显示在这里。'}
            </p>
          </section>

          <section className="sources-box" aria-label="引用来源">
            <h2>引用来源</h2>
            {sources.length === 0 ? (
              <p className="empty-state">暂无引用来源。</p>
            ) : (
              sources.map((source) => (
                <details className="source-card" key={source.chunk_id} open>
                  <summary className="source-row">
                    <span>{source.document_filename}</span>
                    <span>
                      第 {source.page_number} 页 · distance{' '}
                      {source.distance.toFixed(4)}
                    </span>
                  </summary>
                  <p>{source.content}</p>
                </details>
              ))
            )}
          </section>
          <section className="trace-box" aria-label="Trace 步骤">
            <div className="trace-header">
              <div>
                <h2>Trace 步骤</h2>
                <p>查看本次请求每一步做了什么</p>
              </div>
              <button
                type="button"
                className="secondary"
                onClick={() => loadTrace(traceRunId)}
                disabled={isLoadingTrace || !traceRunId}
              >
                {isLoadingTrace ? '加载中...' : '刷新 Trace'}
              </button>
            </div>

            <label className="trace-run-input">
              run_id
              <input
                value={traceRunId}
                onChange={(event) => setTraceRunId(event.target.value)}
                placeholder="回答后会自动填入 run_id"
              />
            </label>

            {traceSteps.length === 0 ? (
              <p className="empty-state">暂无 Trace 步骤。</p>
            ) : (
              <div className="trace-list">
                {traceSteps.map((step) => (
                  <details className="trace-card" key={step.id}>
                    <summary>
                      <span>Step {step.step}</span>
                      <span>{step.status}</span>
                    </summary>
                    <p>工具：{step.tool_name || '模型或系统步骤'}</p>
                    <p>耗时：{step.latency_ms.toFixed(2)} ms</p>
                    <pre>{JSON.stringify({ input: step.input, output: step.output }, null, 2)}</pre>
                  </details>
                ))}
              </div>
            )}
          </section>

        </section>
      </section>
    </main>
  )
}

export default App
