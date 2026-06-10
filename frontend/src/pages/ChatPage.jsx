import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sendChat, uploadPaper, getChatHistory, saveChatHistory } from '../api.js'
import './ChatPage.css'

export default function ChatPage({ sessionId, onStateUpdate }) {
  const [messages, setMessages] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)

  // 載入歷史對話紀錄
  useEffect(() => {
    let active = true
    const loadHistory = async () => {
      if (!sessionId) return
      setHistoryLoading(true)
      try {
        const data = await getChatHistory(sessionId)
        if (active) {
          if (data && data.history && data.history.length > 0) {
            setMessages(data.history)
          } else {
            const defaultMsg = [
              {
                id: 1,
                role: 'assistant',
                content: '您好！我是 AI 研究助理 🔬\n\n您可以：\n- 輸入關鍵字搜尋論文（例：perovskite solar cell）\n- 上傳 PDF 論文進行分析\n- 輸入「生成比較矩陣」整合已分析的論文\n- 輸入「分析研究方向」獲取可行研究建議\n\n請問您想如何開始？',
                type: 'chat',
              }
            ]
            setMessages(defaultMsg)
            await saveChatHistory(sessionId, defaultMsg)
          }
        }
      } catch (e) {
        console.error("Failed to load chat history from backend:", e)
        if (active) {
          const saved = localStorage.getItem(`chat_history_${sessionId}`)
          if (saved) {
            setMessages(JSON.parse(saved))
          } else {
            setMessages([
              {
                id: 1,
                role: 'assistant',
                content: '您好！我是 AI 研究助理 🔬\n\n您可以：\n- 輸入關鍵字搜尋論文（例：perovskite solar cell）\n- 上傳 PDF 論文進行分析\n- 輸入「生成比較矩陣」整合已分析的論文\n- 輸入「分析研究方向」獲取可行研究建議\n\n請問您想如何開始？',
                type: 'chat',
              }
            ])
          }
        }
      } finally {
        if (active) setHistoryLoading(false)
      }
    }
    loadHistory()
    return () => { active = false }
  }, [sessionId])

  // 自動同步訊息至後端與 localStorage
  useEffect(() => {
    if (!sessionId || messages.length === 0 || historyLoading) return
    localStorage.setItem(`chat_history_${sessionId}`, JSON.stringify(messages))
    saveChatHistory(sessionId, messages).catch(console.error)
  }, [messages, sessionId, historyLoading])


  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadQueue, setUploadQueue] = useState([])
  const [uploading, setUploading] = useState(false)
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
      addMessage('assistant', `⚠️ 發生錯誤：${e.message}`, 'error', { suggestions: ["如何更換 API Key？", "為什麼會出現 429 錯誤？"] })
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
      addMessage('assistant', `⚠️ 發生錯誤：${e.message}`, 'error', { suggestions: ["如何更換 API Key？", "重試對話"] })
    } finally {
      setLoading(false)
    }
  }

  const handleFileChange = (e) => {
    if (!e.target.files) return
    const files = Array.from(e.target.files)
    const newItems = files.map(file => ({
      id: Math.random().toString(36).substring(2, 9),
      file,
      status: 'pending', // 'pending' | 'processing' | 'success' | 'failed'
      error: null
    }))
    setUploadQueue(prev => [...prev, ...newItems])
  }

  const handleRemoveFile = (id) => {
    setUploadQueue(prev => prev.filter(item => item.id !== id))
  }

  const handleCloseModal = () => {
    if (uploading) return
    setShowUpload(false)
    setUploadQueue([])
  }

  const handleUpload = async () => {
    if (uploadQueue.length === 0 || uploading) return
    setUploading(true)
    setLoading(true)
    
    // Process queue sequentially
    for (let i = 0; i < uploadQueue.length; i++) {
      const item = uploadQueue[i]
      if (item.status !== 'pending') continue

      setUploadQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'processing' } : q))
      addMessage('user', `📎 上傳論文：${item.file.name}`)

      try {
        const res = await uploadPaper(sessionId, item.file, "", "", "")
        setUploadQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'success' } : q))
        addMessage('assistant', `✅ 論文「${res.summary.title}」已解析完成，存入知識庫中。\n\n**摘要摘錄：**\n\n**研究目的：** ${res.summary.research_goal}\n\n**主要發現：** ${res.summary.main_findings}`, 'analyze', { suggestions: ["生成比較矩陣", "分析研究方向"] })
      } catch (e) {
        console.error(e)
        setUploadQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'failed', error: e.message } : q))
        addMessage('assistant', `⚠️ 論文「${item.file.name}」解析失敗：${e.message}`, 'error', { suggestions: ["如何安裝 PDF 依賴？", "重試對話"] })
      }
    }

    onStateUpdate?.()
    setUploading(false)
    setLoading(false)
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
            <h3>📎 上傳多篇論文</h3>
            <button className="btn-icon btn" onClick={handleCloseModal} disabled={uploading}>✕</button>
          </div>
          <div className="upload-form">
            <div className={`file-upload-zone ${uploading ? 'disabled' : ''}`} onClick={() => !uploading && fileInputRef.current?.click()}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>📥</div>
              <p>{uploading ? '正在依序解析論文中...' : '點擊選擇多個 PDF 論文檔案'}</p>
              <input 
                ref={fileInputRef} 
                type="file" 
                accept=".pdf" 
                multiple 
                style={{ display: 'none' }}
                onChange={handleFileChange}
                disabled={uploading}
              />
            </div>
            {uploadQueue.length > 0 && (
              <div className="file-queue-list">
                {uploadQueue.map(item => (
                  <div key={item.id} className="queue-item">
                    <span className="queue-file-name" title={item.file.name}>
                      📄 {item.file.name}
                    </span>
                    <div className="queue-item-actions">
                      <span className={`status-badge status-${item.status}`}>
                        {item.status === 'pending' && '等待中'}
                        {item.status === 'processing' && '解析中...'}
                        {item.status === 'success' && '完成 ✅'}
                        {item.status === 'failed' && '失敗 ❌'}
                      </span>
                      {item.status === 'pending' && !uploading && (
                        <button className="btn-remove-item" onClick={() => handleRemoveFile(item.id)}>✕</button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="upload-actions">
            <button className="btn btn-ghost" onClick={handleCloseModal} disabled={uploading}>取消</button>
            <button className="btn btn-primary" onClick={handleUpload} disabled={uploading || uploadQueue.length === 0 || !uploadQueue.some(q => q.status === 'pending')}>
              {uploading ? '解析中...' : '開始解析'}
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
