import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sendChat, uploadPaper, extractMetadata } from '../api.js'
import './ChatPage.css'

export default function ChatPage({ sessionId, onStateUpdate }) {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(`chat_history_${sessionId}`)
    if (saved) {
      try { return JSON.parse(saved) } catch (e) { console.error(e) }
    }
    return [
      {
        id: 1,
        role: 'assistant',
        content: '您好！我是 AI 研究助理 🔬\n\n您可以：\n- 輸入關鍵字搜尋論文（例：perovskite solar cell）\n- 上傳 PDF 論文進行分析\n- 輸入「生成比較矩陣」整合已分析的論文\n- 輸入「分析研究方向」獲取可行研究建議\n\n請問您想如何開始？',
        type: 'chat',
      },
    ]
  })
  const [input, setInput] = useState('')

  useEffect(() => {
    localStorage.setItem(`chat_history_${sessionId}`, JSON.stringify(messages))
  }, [messages, sessionId])
  const [loading, setLoading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadForm, setUploadForm] = useState({ title: '', authors: '', year: '' })
  const [parsingMetadata, setParsingMetadata] = useState(false)
  const [metadataError, setMetadataError] = useState(null)
  const bottomRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const addMessage = (role, content, type = 'chat', extra = {}) => {
    setMessages(prev => [...prev, { id: Date.now(), role, content, type, ...extra }])
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    addMessage('user', userMsg)
    setLoading(true)
    try {
      const res = await sendChat(sessionId, userMsg)
      addMessage('assistant', res.content, res.type, { papers: res.papers, suggestions: res.suggestions })
      if (res.type === 'matrix') {
        localStorage.setItem(`matrix_${sessionId}`, res.content)
      } else if (res.type === 'direction') {
        localStorage.setItem(`direction_${sessionId}`, res.content)
      }
      onStateUpdate?.()
    } catch (e) {
      addMessage('assistant', `⚠️ 發生錯誤：${e.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleSuggestionClick = async (sugText) => {
    if (loading) return
    addMessage('user', sugText)
    setLoading(true)
    try {
      const res = await sendChat(sessionId, sugText)
      addMessage('assistant', res.content, res.type, { papers: res.papers, suggestions: res.suggestions })
      if (res.type === 'matrix') {
        localStorage.setItem(`matrix_${sessionId}`, res.content)
      } else if (res.type === 'direction') {
        localStorage.setItem(`direction_${sessionId}`, res.content)
      }
      onStateUpdate?.()
    } catch (e) {
      addMessage('assistant', `⚠️ 發生錯誤：${e.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }


  const handleFileChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploadFile(file)
    setParsingMetadata(true)
    setMetadataError(null)
    try {
      const meta = await extractMetadata(file)
      setUploadForm({
        title: meta.title || '',
        authors: Array.isArray(meta.authors) ? meta.authors.join(', ') : '',
        year: meta.year || ''
      })
    } catch (err) {
      console.error("Metadata extraction failed:", err)
      setMetadataError('自動解析論文資訊失敗，請手動輸入。')
    } finally {
      setParsingMetadata(false)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile || !uploadForm.title) return
    setLoading(true)
    setShowUpload(false)
    addMessage('user', `📎 上傳論文：${uploadFile.name}`)
    try {
      const res = await uploadPaper(sessionId, uploadFile, uploadForm.title, uploadForm.authors, uploadForm.year)
      addMessage('assistant', `✅ ${res.message}\n\n**摘要摘錄：**\n\n**研究目的：** ${res.summary.research_goal}\n\n**主要發現：** ${res.summary.main_findings}`, 'analyze')
      onStateUpdate?.()
    } catch (e) {
      addMessage('assistant', `⚠️ 上傳失敗：${e.message}`, 'error')
    } finally {
      setLoading(false)
      setUploadForm({ title: '', authors: '', year: '' })
      setUploadFile(null)
      setParsingMetadata(false)
      setMetadataError(null)
    }
  }

  const getMessageIcon = (type) => {
    const icons = { search: '🔍', analyze: '📄', matrix: '📊', direction: '🧭', error: '⚠️', chat: '🤖' }
    return icons[type] || '🤖'
  }

  return (
    <div className="chat-page">
      {/* 訊息列表 */}
      <div className="messages-container">
        {messages.map((msg, index) => (
          <div key={msg.id} className="message-wrapper" style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
            <div className={`message message-${msg.role} fade-in`}>
              {msg.role === 'assistant' && (
                <div className="message-avatar">{getMessageIcon(msg.type)}</div>
              )}
              <div className={`message-bubble message-bubble-${msg.role}`}>
                {msg.role === 'assistant' ? (
                  <div className="markdown-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p>{msg.content}</p>
                )}
                {msg.type !== 'chat' && msg.type !== 'error' && (
                  <span className={`message-type-badge badge badge-${msg.type === 'search' ? 'blue' : msg.type === 'matrix' ? 'purple' : 'green'}`}>
                    {msg.type === 'search' ? '搜尋結果' : msg.type === 'matrix' ? '比較矩陣' : msg.type === 'analyze' ? '論文分析' : '方向建議'}
                  </span>
                )}
              </div>
            </div>
            {msg.role === 'assistant' && msg.suggestions && msg.suggestions.length > 0 && index === messages.length - 1 && (
              <div className="suggestions-container">
                {msg.suggestions.map((sug, i) => (
                  <button key={i} className="suggestion-btn" onClick={() => handleSuggestionClick(sug)}>
                    <span>{sug}</span>
                    <span className="suggestion-arrow">➔</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="message message-assistant fade-in">
            <div className="message-avatar">🤖</div>
            <div className="message-bubble message-bubble-assistant">
              <div className="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 上傳表單 */}
      {showUpload && (
        <div className="upload-modal glass-card fade-in">
          <div className="upload-modal-header">
            <h3>📎 上傳論文</h3>
            <button className="btn-icon btn" onClick={() => {
              setShowUpload(false)
              setParsingMetadata(false)
              setMetadataError(null)
            }}>✕</button>
          </div>
          <div className="upload-form">
            <label>論文標題 *
              <input value={uploadForm.title} onChange={e => setUploadForm(p => ({ ...p, title: e.target.value }))} placeholder="例：A Review of Perovskite Solar Cells" disabled={parsingMetadata} />
            </label>
            <label>作者（以逗號分隔）
              <input value={uploadForm.authors} onChange={e => setUploadForm(p => ({ ...p, authors: e.target.value }))} placeholder="例：Wang, Li, Chen" disabled={parsingMetadata} />
            </label>
            <label>年份
              <input type="number" value={uploadForm.year} onChange={e => setUploadForm(p => ({ ...p, year: e.target.value }))} placeholder="例：2024" disabled={parsingMetadata} />
            </label>
            <label className="file-input-label">
              {uploadFile ? `📄 ${uploadFile.name}` : '選擇 PDF 檔案'}
              <input ref={fileInputRef} type="file" accept=".pdf" style={{ display: 'none' }}
                onChange={handleFileChange} />
              <button className="btn btn-ghost" onClick={() => fileInputRef.current?.click()} disabled={parsingMetadata}>瀏覽</button>
            </label>
            {parsingMetadata && (
              <div className="parsing-metadata-status">
                <span className="spinner small-spinner"></span> 正在自動解析論文標題與作者...
              </div>
            )}
            {metadataError && (
              <div className="parsing-metadata-error">
                {metadataError}
              </div>
            )}
          </div>
          <div className="upload-actions">
            <button className="btn btn-ghost" onClick={() => {
              setShowUpload(false)
              setParsingMetadata(false)
              setMetadataError(null)
            }} disabled={parsingMetadata}>取消</button>
            <button className="btn btn-primary" onClick={handleUpload} disabled={!uploadFile || !uploadForm.title || parsingMetadata}>
              開始解析
            </button>
          </div>
        </div>
      )}

      {/* 輸入列 */}
      <div className="input-bar glass-card">
        <button className="btn btn-ghost" id="upload-btn" onClick={() => setShowUpload(true)}>
          📎 上傳論文
        </button>
        <input
          id="chat-input"
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder="輸入關鍵字搜尋、或輸入「生成比較矩陣」、「分析研究方向」..."
          disabled={loading}
        />
        <button id="send-btn" className="btn btn-primary" onClick={handleSend} disabled={loading || !input.trim()}>
          {loading ? <span className="spinner" /> : '送出 ➤'}
        </button>
      </div>
    </div>
  )
}
