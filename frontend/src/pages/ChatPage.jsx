import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sendChat, uploadPaper } from '../api.js'
import './ChatPage.css'

export default function ChatPage({ sessionId, onSummaryUpdate }) {
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem(`chat_messages_${sessionId}`)
      if (saved) return JSON.parse(saved)
    } catch (e) {}
    return [
      {
        id: 1,
        role: 'assistant',
        content: '您好！我是 AI 研究助理 🔬\n\n您可以：\n- 輸入關鍵字搜尋論文（例：perovskite solar cell）\n- 上傳 PDF 論文進行分析\n- 輸入「生成比較矩陣」整合已分析的論文\n- 輸入「分析研究方向」獲取可行研究建議\n\n請問您想如何開始？',
        type: 'chat',
      },
    ]
  })

  useEffect(() => {
    localStorage.setItem(`chat_messages_${sessionId}`, JSON.stringify(messages))
  }, [messages, sessionId])

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadForm, setUploadForm] = useState({ title: '', authors: '', year: '' })
  const [uploadFile, setUploadFile] = useState(null)
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
      addMessage('assistant', res.content, res.type, { papers: res.papers })
      if (res.type === 'matrix' || res.type === 'analyze') onSummaryUpdate?.()
    } catch (e) {
      addMessage('assistant', `⚠️ 發生錯誤：${e.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile || !uploadForm.title) return
    setLoading(true)
    setShowUpload(false)
    addMessage('user', `📎 上傳論文：${uploadForm.title}`)
    try {
      const res = await uploadPaper(
        sessionId, uploadFile,
        uploadForm.title, uploadForm.authors, uploadForm.year
      )
      addMessage('assistant', `✅ ${res.message}\n\n**摘要摘錄：**\n\n**研究目的：** ${res.summary.research_goal}\n\n**主要發現：** ${res.summary.main_findings}`, 'analyze')
      onSummaryUpdate?.()
    } catch (e) {
      addMessage('assistant', `⚠️ 上傳失敗：${e.message}`, 'error')
    } finally {
      setLoading(false)
      setUploadForm({ title: '', authors: '', year: '' })
      setUploadFile(null)
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
        {messages.map(msg => (
          <div key={msg.id} className={`message message-${msg.role} fade-in`}>
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
            <button className="btn-icon btn" onClick={() => setShowUpload(false)}>✕</button>
          </div>
          <div className="upload-form">
            <label>論文標題 *
              <input value={uploadForm.title} onChange={e => setUploadForm(p => ({ ...p, title: e.target.value }))} placeholder="例：A Review of Perovskite Solar Cells" />
            </label>
            <label>作者（以逗號分隔）
              <input value={uploadForm.authors} onChange={e => setUploadForm(p => ({ ...p, authors: e.target.value }))} placeholder="例：Wang, Li, Chen" />
            </label>
            <label>年份
              <input type="number" value={uploadForm.year} onChange={e => setUploadForm(p => ({ ...p, year: e.target.value }))} placeholder="例：2024" />
            </label>
            <label className="file-input-label">
              {uploadFile ? `📄 ${uploadFile.name}` : '選擇 PDF 檔案'}
              <input ref={fileInputRef} type="file" accept=".pdf" style={{ display: 'none' }}
                onChange={e => setUploadFile(e.target.files[0])} />
              <button className="btn btn-ghost" onClick={() => fileInputRef.current?.click()}>瀏覽</button>
            </label>
          </div>
          <div className="upload-actions">
            <button className="btn btn-ghost" onClick={() => setShowUpload(false)}>取消</button>
            <button className="btn btn-primary" onClick={handleUpload} disabled={!uploadFile || !uploadForm.title}>
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
