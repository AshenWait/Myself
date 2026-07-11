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
  const [selectedFiles, setSelectedFiles] = useState([])
  const [isDraggingFile, setIsDraggingFile] = useState(false)
  const [question, setQuestion] = useState('这个文档是做什么用的？')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [deletingDocumentId, setDeletingDocumentId] = useState(null)
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

  async function uploadFiles(filesToUpload) {
    if (filesToUpload.length === 0) {
      return []
    }

    setIsUploading(true)
    const uploadedDocuments = []

    try {
      for (const file of filesToUpload) {
        const formData = new FormData()
        formData.append('file', file)
        const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          throw new Error(await readError(response))
        }

        uploadedDocuments.push(await response.json())
      }

      setSelectedFiles((currentFiles) =>
        currentFiles.filter((file) => !filesToUpload.includes(file)),
      )
      await loadDocuments()
      if (uploadedDocuments.length === 1) {
        setSelectedDocumentId(String(uploadedDocuments[0].document_id))
      } else {
        setSelectedDocumentId('')
      }
      setNotice(`已上传 ${uploadedDocuments.length} 个文件到知识库`)
      return uploadedDocuments
    } catch (err) {
      if (uploadedDocuments.length > 0) {
        const uploadedFiles = filesToUpload.slice(0, uploadedDocuments.length)
        setSelectedFiles((currentFiles) =>
          currentFiles.filter((file) => !uploadedFiles.includes(file)),
        )
        await loadDocuments()
      }
      throw err
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  async function handleUpload(event) {
    event.preventDefault()

    if (selectedFiles.length === 0) {
      setError('请先添加文件')
      return
    }

    setNotice('')
    setError('')

    try {
      await uploadFiles(selectedFiles)
    } catch (err) {
      setError(err.message)
    }
  }

  function addFiles(fileList) {
    const files = Array.from(fileList || [])
    if (files.length === 0) {
      return
    }

    setSelectedFiles((currentFiles) => [...currentFiles, ...files])
    setNotice(`已添加 ${files.length} 个文件，发送问题前会自动上传`)
    setError('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  function removeSelectedFile(index) {
    setSelectedFiles((currentFiles) =>
      currentFiles.filter((_, fileIndex) => fileIndex !== index),
    )
  }

  function clearSelectedFiles() {
    setSelectedFiles([])
    setNotice('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
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

    addFiles(event.dataTransfer.files)
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

    try {
      const uploadedDocuments = await uploadFiles(selectedFiles)
      const documentId =
        uploadedDocuments.length === 1
          ? uploadedDocuments[0].document_id
          : uploadedDocuments.length > 1
            ? null
            : selectedDocumentId
              ? Number(selectedDocumentId)
              : null

      const payload = {
        message: trimmedQuestion,
        document_id: documentId,
        session_id: sessionId,
      }

      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      if (!response.body) {
        throw new Error('浏览器不支持流式响应')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let finalRunId = ''
      let finalNotice = ''

      const handleStreamEvent = (event) => {
        if (event.type === 'meta') {
          setSessionId(event.session_id)
          setTraceRunId(event.run_id || '')
          finalRunId = event.run_id || ''
          return
        }

        if (event.type === 'chunk') {
          setAnswer((currentAnswer) => currentAnswer + event.text)
          return
        }

        if (event.type === 'done') {
          setSources(event.sources || [])
          setSessionId(event.session_id)
          setTraceRunId(event.run_id || '')
          finalRunId = event.run_id || ''
          finalNotice = `回答完成，耗时 ${event.latency_ms} ms`
          return
        }

        if (event.type === 'error') {
          throw new Error(event.message || '流式回答失败')
        }
      }

      while (true) {
        const { value, done } = await reader.read()
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.trim()) {
            handleStreamEvent(JSON.parse(line))
          }
        }
      }

      buffer += decoder.decode()
      if (buffer.trim()) {
        handleStreamEvent(JSON.parse(buffer))
      }

      if (finalRunId) {
        await loadTrace(finalRunId)
      }
      setNotice(finalNotice || '回答完成')
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

  async function handleDeleteDocument(document) {
    const confirmed = window.confirm(`确定删除「${document.filename}」吗？`)
    if (!confirmed) {
      return
    }

    setDeletingDocumentId(document.id)
    setNotice('')
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/${document.id}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      setDocuments((currentDocuments) =>
        currentDocuments.filter((item) => item.id !== document.id),
      )
      if (selectedDocumentId === String(document.id)) {
        setSelectedDocumentId('')
      }
      setNotice(`已删除文档：${document.filename}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setDeletingDocumentId(null)
    }
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <h1>知识库问答工作台</h1>
          <p>上传资料后直接提问，回答会实时生成。</p>
        </div>
        <div className="status-pill">流式输出</div>
      </header>

      {(notice || error) && (
        <section className={`banner ${error ? 'error' : 'success'}`}>
          {error || notice}
        </section>
      )}

      <section className="workspace" aria-label="知识库问答工作台">
        <aside className="library-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">文档</p>
              <h2>知识库</h2>
            </div>
            <span>{isLoadingDocuments ? '刷新中' : `${documents.length} 个`}</span>
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
                multiple
                accept=".txt,.md,.markdown,.pdf"
                onChange={(event) => {
                  addFiles(event.target.files)
                }}
              />
              <span className="upload-icon">+</span>
              <strong>
                {selectedFiles.length > 0
                  ? `已添加 ${selectedFiles.length} 个文件`
                  : '添加资料'}
              </strong>
              <small>PDF / TXT / Markdown · 10MB</small>
              <span className="upload-hint">
                {isDraggingFile ? '松开即可添加' : '可多选，提问前自动上传'}
              </span>
            </label>

            {selectedFiles.length > 0 && (
              <div className="selected-files">
                <div className="selected-files-header">
                  <span>待上传文件</span>
                  <button type="button" className="text-button" onClick={clearSelectedFiles}>
                    清空
                  </button>
                </div>
                {selectedFiles.map((file, index) => (
                  <div className="selected-file" key={`${file.name}-${file.size}-${file.lastModified}-${index}`}>
                    <span>{file.name}</span>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => removeSelectedFile(index)}
                    >
                      移除
                    </button>
                  </div>
                ))}
              </div>
            )}

            <button
              className="full-button"
              type="submit"
              disabled={isUploading || isAsking || selectedFiles.length === 0}
            >
              {isUploading
                ? '上传并入库中...'
                : selectedFiles.length > 0
                  ? `上传 ${selectedFiles.length} 个文件到知识库`
                  : '上传到知识库'}
            </button>
          </form>

          <div className="document-list" aria-label="文档列表">
            <div className="list-title">
              <h2>文档列表</h2>
            </div>

            {documents.length === 0 && !isLoadingDocuments ? (
              <p className="empty-state">还没有文档，先上传一份资料。</p>
            ) : (
              documents.map((document) => (
                <div
                  className={`document-item ${
                    String(document.id) === selectedDocumentId ? 'active' : ''
                  }`}
                  key={document.id}
                >
                  <button
                    className="document-main"
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
                  <button
                    aria-label={`删除 ${document.filename}`}
                    className="delete-document-button"
                    disabled={deletingDocumentId === document.id}
                    type="button"
                    onClick={() => handleDeleteDocument(document)}
                  >
                    {deletingDocumentId === document.id ? '删除中' : '删除'}
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>

        <section className="chat-panel">
          <div className="chat-toolbar">
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

          <section className="question-card">
            <label className="question-area">
              <span>问题</span>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="例如：这个文档主要讲了什么？"
                rows="4"
            />
            </label>

            <div className="actions">
              <button type="button" onClick={handleAsk} disabled={isAsking || isUploading}>
                {isUploading
                  ? '上传中...'
                  : isAsking
                    ? selectedFiles.length > 0
                      ? '上传并生成中...'
                      : '生成中...'
                  : selectedFiles.length > 0
                    ? '上传并提问'
                    : '发送问题'}
              </button>
              <button type="button" className="secondary" onClick={clearQuestion}>
                清空
              </button>
            </div>
          </section>

          <section className={`answer-box ${isAsking ? 'streaming' : ''}`} aria-label="回答区">
            <div className="answer-header">
              <h2>回答区</h2>
              <span>
                {selectedDocument ? `当前文档：${selectedDocument.filename}` : '全部文档'}
              </span>
            </div>
            <p>
              {answer || (isAsking ? '正在检索资料并生成回答...' : '回答会显示在这里。')}
            </p>
          </section>

          <div className="support-grid">
            <section className="sources-box" aria-label="引用来源">
              <div className="box-heading">
                <h2>引用来源</h2>
                <span>{sources.length} 条</span>
              </div>
              {sources.length === 0 ? (
                <p className="empty-state">暂无引用来源。</p>
              ) : (
                sources.map((source) => (
                  <details className="source-card" key={source.chunk_id}>
                    <summary className="source-row">
                      <span>{source.document_filename}</span>
                      <span>
                        第 {source.page_number} 页 · {source.distance.toFixed(4)}
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
                  <h2>Trace</h2>
                  <p>{traceRunId || '等待本次请求'}</p>
                </div>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => loadTrace(traceRunId)}
                  disabled={isLoadingTrace || !traceRunId}
                >
                  {isLoadingTrace ? '加载中' : '刷新'}
                </button>
              </div>

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
          </div>

        </section>
      </section>
    </main>
  )
}

export default App
