import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sendChat, uploadPaper, getChatHistory, saveChatHistory } from '../api.js'
import './ChatPage.css'

export default function ChatPage({
  sessionId,
  onStateUpdate,
  messages,
  setMessages,
  historyLoading,
  uploadQueue,
  uploading,
  showUpload,
  setShowUpload,
  handleFileChange,
  handleRemoveFile,
  handleCloseModal,
  handleUpload,
  addMessage
}) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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

  const getMessageIcon = (type) => {
    const icons = { search: '🔍', analyze: '📄', matrix: '📊', direction: '🧭', error: '⚠️', chat: '🤖' }
    return icons[type] || '🤖'
  }

  const renderPaperLinks = (papers) => {
    if (!papers || papers.length === 0) return null
    return (
      <div className="paper-links-row">
        {papers.map((p, i) => {
          // 原文連結優先順序：doi > url > 無
          const originalUrl = p.doi
            ? `https://doi.org/${p.doi}`
            : p.url || null
          // Semantic Scholar 連結：只在 paper_id 是有效 S2 hash（不含 "arxiv:" 前綴）時顯示
          const isValidS2Id = p.paper_id && !p.paper_id.startsWith('arxiv:')
          // arXiv 連結：當 paper_id 以 "arxiv:" 開頭時，改顯示 arXiv 按鈕
          const arxivId = p.paper_id?.startsWith('arxiv:')
            ? p.paper_id.replace('arxiv:', '')
            : null

          return (
            <div key={i} className="paper-link-card">
              <span className="paper-link-title" title={p.title}>{p.title}</span>
              <div className="paper-link-actions">
                {originalUrl && (
                  <a
                    href={originalUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="paper-link-btn"
                    title={p.doi ? `DOI: ${p.doi}` : '查看原文'}
                  >
                    📖 原文
                  </a>
                )}
                {isValidS2Id && (
                  <a
                    href={`https://www.semanticscholar.org/paper/${p.paper_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="paper-link-btn paper-link-ss"
                    title="Semantic Scholar"
                  >
                    🔍 S2
                  </a>
                )}
                {arxivId && (
                  <a
                    href={`https://arxiv.org/abs/${arxivId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="paper-link-btn paper-link-arxiv"
                    title="arXiv"
                  >
                    📄 arXiv
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>
    )
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
            {msg.role === 'assistant' && msg.type === 'search' && msg.papers && renderPaperLinks(msg.papers)}
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
