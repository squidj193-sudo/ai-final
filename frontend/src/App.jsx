import { useState, useEffect } from 'react'
import ChatPage from './pages/ChatPage.jsx'
import SummaryPage from './pages/SummaryPage.jsx'
import MatrixPage from './pages/MatrixPage.jsx'
import GraphPage from './pages/GraphPage.jsx'
import DirectionPage from './pages/DirectionPage.jsx'
import { updateRoleState, getRoleState, getConversations, saveConversations, uploadPaper, getChatHistory, saveChatHistory, deleteConversation, getSummaries, getMatrix, getDirection } from './api.js'
import { v4 as uuidv4 } from 'uuid'
import './App.css'

const NAV_ITEMS = [
  { id: 'chat',      icon: '💬', label: '對話搜尋' },
  { id: 'summary',   icon: '📋', label: '論文摘要' },
  { id: 'matrix',    icon: '📊', label: '比較矩陣' },
  { id: 'graph',     icon: '🕸️', label: '論文圖譜' },
  { id: 'direction', icon: '🧭', label: '研究方向' },
]

export default function App() {
  const [sessionId, setSessionId] = useState('')
  const [activePage, setActivePage] = useState('chat')
  const [conversations, setConversations] = useState([])
  const [modelName, setModelName] = useState('gemma-4-26b-a4b-it')

  // 全域聊天歷史與上傳佇列狀態
  const [messages, setMessages] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [uploadQueue, setUploadQueue] = useState([])
  const [uploading, setUploading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)

  // 任務進度指標狀態
  const [summariesCount, setSummariesCount] = useState(0)
  const [matrixCached, setMatrixCached] = useState(false)
  const [directionCached, setDirectionCached] = useState(false)
  const [showStepper, setShowStepper] = useState(() => {
    const saved = localStorage.getItem('show_stepper')
    return saved !== null ? JSON.parse(saved) : true
  })

  const [aiRecommendedStep, setAiRecommendedStep] = useState(null)

  useEffect(() => {
    localStorage.setItem('show_stepper', JSON.stringify(showStepper))
  }, [showStepper])

  useEffect(() => {
    if (!messages || messages.length === 0) {
      setAiRecommendedStep(null)
      return
    }
    const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant')
    if (!lastAssistant) {
      setAiRecommendedStep(null)
      return
    }

    const suggestions = lastAssistant.suggestions || []
    const type = lastAssistant.type || ''

    let recommended = null
    for (const sug of suggestions) {
      const lowerSug = sug.toLowerCase()
      if (lowerSug.includes('定位') || lowerSug.includes('角色') || lowerSug.includes('設定研究') || lowerSug.includes('方向')) {
        recommended = 1
        break
      } else if (lowerSug.includes('搜尋') || lowerSug.includes('文獻') || lowerSug.includes('上傳') || lowerSug.includes('採集') || lowerSug.includes('pdf') || lowerSug.includes('找文獻')) {
        recommended = 2
        break
      } else if (lowerSug.includes('矩陣') || lowerSug.includes('比較矩陣') || lowerSug.includes('對比') || lowerSug.includes('表格')) {
        recommended = 3
        break
      } else if (lowerSug.includes('圖譜') || lowerSug.includes('知識圖譜') || lowerSug.includes('關聯')) {
        recommended = 4
        break
      } else if (lowerSug.includes('建議') || lowerSug.includes('課題') || lowerSug.includes('方向建議') || lowerSug.includes('研究方向')) {
        recommended = 5
        break
      }
    }

    if (!recommended) {
      if (type === 'search' || type === 'analyze') {
        recommended = 3
      } else if (type === 'matrix') {
        recommended = 5
      } else if (type === 'direction') {
        recommended = 2
      }
    }

    setAiRecommendedStep(recommended)
  }, [messages])

  // 載入對話列表與初始化 Session
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const data = await getConversations()
        if (data && data.conversations && data.conversations.length > 0) {
          setConversations(data.conversations)
          const activeConv = data.conversations.find(c => c.active) || data.conversations[0]
          setSessionId(activeConv.id)
        } else {
          const defaultId = uuidv4()
          const initialConversations = [{ id: defaultId, label: '研究對話 1', active: true }]
          setConversations(initialConversations)
          setSessionId(defaultId)
          await saveConversations(initialConversations)
        }
      } catch (e) {
        console.error("Failed to load conversations from backend:", e)
        let id = localStorage.getItem('ai_session_id') || uuidv4()
        const saved = localStorage.getItem('ai_conversations')
        const localConvs = saved ? JSON.parse(saved) : [{ id, label: '研究對話 1', active: true }]
        setConversations(localConvs)
        const activeConv = localConvs.find(c => c.active) || localConvs[0]
        setSessionId(activeConv.id)
      }
    }
    loadConversations()
  }, [])

  // 載入當前對話歷史紀錄
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

  const switchConversation = async (id) => {
    if (uploading) {
      alert("目前正在上傳/解析論文中，請待解析完成後再切換對話。")
      return
    }
    setSessionId(id)
    localStorage.setItem('ai_session_id', id)
    const nextConvs = conversations.map(c => ({ ...c, active: c.id === id }))
    setConversations(nextConvs)
    localStorage.setItem('ai_conversations', JSON.stringify(nextConvs))
    try {
      await saveConversations(nextConvs)
    } catch (e) {
      console.error(e)
    }
    setActivePage('chat')
  }

  const handleNewChat = async () => {
    if (uploading) {
      alert("目前正在上傳/解析論文中，請待解析完成後再新增對話。")
      return
    }
    const newId = uuidv4()
    const newLabel = `研究對話 ${conversations.length + 1}`
    setSessionId(newId)
    localStorage.setItem('ai_session_id', newId)
    const nextConvs = [...conversations.map(c => ({ ...c, active: false })), { id: newId, label: newLabel, active: true }]
    setConversations(nextConvs)
    localStorage.setItem('ai_conversations', JSON.stringify(nextConvs))
    try {
      await saveConversations(nextConvs)
    } catch (e) {
      console.error(e)
    }
    setActivePage('chat')
  }

  const [showRoleModal, setShowRoleModal] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [roleForm, setRoleForm] = useState({ large: '', medium: '', small: '' })
  const [roleDesc, setRoleDesc] = useState('尚未設定研究方向')
  const [summaryKey, setSummaryKey] = useState(0)

  // 全域背景上傳與佇列邏輯
  const addMessage = (role, content, type = 'chat', extra = {}) => {
    setMessages(prev => [...prev, { id: Date.now(), role, content, type, ...extra }])
  }

  const handleFileChange = (e) => {
    if (!e.target.files) return
    const files = Array.from(e.target.files)
    const newItems = files.map(file => ({
      id: Math.random().toString(36).substring(2, 9),
      file,
      status: 'pending',
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
    
    // 依序處理佇列中處於 pending 狀態的檔案
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

    refreshState()
    setUploading(false)
  }

  const handleDeleteConversation = async (id, event) => {
    event.stopPropagation()
    if (uploading) {
      alert("目前正在上傳/解析論文中，無法刪除對話。")
      return
    }
    if (!window.confirm("確定要刪除此對話紀錄嗎？這將會清除此對話的所有歷史與文獻摘要快取。")) {
      return
    }

    try {
      await deleteConversation(id)
      const nextConvs = conversations.filter(c => c.id !== id)
      
      let nextSessionId = sessionId
      if (id === sessionId) {
        if (nextConvs.length > 0) {
          nextSessionId = nextConvs[0].id
          nextConvs[0].active = true
        } else {
          nextSessionId = uuidv4()
          nextConvs.push({ id: nextSessionId, label: '研究對話 1', active: true })
        }
      }

      setConversations(nextConvs)
      setSessionId(nextSessionId)
      localStorage.setItem('ai_session_id', nextSessionId)
      localStorage.setItem('ai_conversations', JSON.stringify(nextConvs))

      await saveConversations(nextConvs)
      setActivePage('chat')
    } catch (e) {
      console.error("Failed to delete conversation:", e)
      alert(`刪除失敗：${e.message}`)
    }
  }

  // 載入模型名稱
  useEffect(() => {
    fetch('/health')
      .then(res => res.json())
      .then(data => {
        if (data && data.model) {
          setModelName(data.model)
        }
      })
      .catch(() => {})
  }, [])

  const refreshState = async () => {
    if (!sessionId) return
    try {
      const d = await getRoleState(sessionId)
      setRoleDesc(d.description)
      setRoleForm({
        large: d.state.large_direction || '',
        medium: d.state.medium_direction || '',
        small: d.state.small_direction || '',
      })

      const [sumsRes, matRes, dirRes] = await Promise.all([
        getSummaries(sessionId).catch(() => ({ summaries: [] })),
        getMatrix(sessionId).catch(() => ({ matrix: "" })),
        getDirection(sessionId).catch(() => ({ direction: "" }))
      ])

      setSummariesCount(sumsRes.summaries ? sumsRes.summaries.length : 0)
      setMatrixCached(!!(matRes && matRes.matrix))
      setDirectionCached(!!(dirRes && dirRes.direction))
    } catch (e) {
      console.error("Failed to refresh global progress states:", e)
    }
    setSummaryKey(k => k + 1)
  }

  // 載入角色狀態與研究進度指標
  useEffect(() => {
    refreshState()
  }, [sessionId])

  const saveRoleState = async () => {
    try {
      await updateRoleState(sessionId, roleForm)
      const d = await getRoleState(sessionId)
      setRoleDesc(d.description)
      setShowRoleModal(false)
      refreshState() // 儲存完後重新整理進度
    } catch (e) {
      console.error(e)
    }
  }

  const renderPages = () => {
    if (!sessionId) {
      return (
        <div className="loading-state" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
          <p style={{ marginTop: 12 }}>載入對話中...</p>
        </div>
      )
    }
    return (
      <div className="spa-page-container" style={{ width: '100%', height: '100%', position: 'relative' }}>
        <div style={{ display: activePage === 'chat' ? 'block' : 'none', height: '100%' }}>
          <ChatPage 
            key={sessionId} 
            sessionId={sessionId} 
            onStateUpdate={refreshState}
            messages={messages}
            setMessages={setMessages}
            historyLoading={historyLoading}
            uploadQueue={uploadQueue}
            uploading={uploading}
            showUpload={showUpload}
            setShowUpload={setShowUpload}
            handleFileChange={handleFileChange}
            handleRemoveFile={handleRemoveFile}
            handleCloseModal={handleCloseModal}
            handleUpload={handleUpload}
            addMessage={addMessage}
          />
        </div>
        <div style={{ display: activePage === 'summary' ? 'block' : 'none', height: '100%' }}>
          <SummaryPage key={summaryKey} sessionId={sessionId} />
        </div>
        <div style={{ display: activePage === 'matrix' ? 'block' : 'none', height: '100%' }}>
          <MatrixPage sessionId={sessionId} />
        </div>
        <div style={{ display: activePage === 'graph' ? 'block' : 'none', height: '100%' }}>
          <GraphPage sessionId={sessionId} activePage={activePage} />
        </div>
        <div style={{ display: activePage === 'direction' ? 'block' : 'none', height: '100%' }}>
          <DirectionPage sessionId={sessionId} />
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      {/* ─── 側邊欄 ─── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="logo-icon">🔬</span>
          <div>
            <h2>AI 研究助理</h2>
            <p>{modelName}</p>
          </div>
        </div>

        {/* 角色設定 */}
        <button id="role-state-btn" className="role-state-card" onClick={() => setShowRoleModal(true)}>
          <div className="role-icon">👤</div>
          <div className="role-info">
            <span className="role-label">研究角色設定</span>
            <span className="role-desc">{roleDesc}</span>
          </div>
          <span className="role-edit">✏️</span>
        </button>

        {/* 導覽 */}
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              id={`nav-${item.id}`}
              className={`nav-item ${activePage === item.id ? 'active' : ''}`}
              onClick={() => setActivePage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {/* 對話列表 */}
        <div className="sidebar-section">
          <div className="section-header">
            <span>對話歷史紀錄</span>
            <button className="btn btn-icon" id="new-chat-btn" title="新增對話" onClick={handleNewChat}>＋</button>
          </div>
          <ul className="conv-list">
            {conversations.map(c => (
              <li 
                key={c.id} 
                className={`conv-item ${c.active ? 'active' : ''}`}
                onClick={() => switchConversation(c.id)}
                style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                  <span className="conv-dot">●</span>
                  <span className="conv-label">{c.label}</span>
                </div>
                <button 
                  className="btn-delete-conv" 
                  title="刪除對話"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteConversation(c.id, e);
                  }}
                >
                  🗑️
                </button>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      {/* ─── 主內容 ─── */}
      <main className="main-content">
        {/* 頂部 Header */}
        <header className="main-header">
          <div className="header-title">
            <span>{NAV_ITEMS.find(n => n.id === activePage)?.icon}</span>
            <h1>{NAV_ITEMS.find(n => n.id === activePage)?.label}</h1>
          </div>
          <div className="header-badges">
            <button 
              className={`stepper-toggle-btn ${showStepper ? 'active' : ''}`}
              onClick={() => setShowStepper(!showStepper)}
              title={showStepper ? "隱藏研究進度" : "顯示研究進度"}
            >
              {showStepper ? '📊 隱藏進度' : '📊 顯示進度'}
            </button>
            <span className="badge badge-purple">{modelName}</span>
            <span className="badge badge-green">RAG 已啟用</span>
          </div>
        </header>

        {/* 研究進度指示器 */}
        {showStepper && (
          <div className="research-stepper glass-card">
            <div className="stepper-title" style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <span>🔬 當前會話研究進度：</span>
              {aiRecommendedStep && (
                <span className="stepper-ai-recommendation-hint fade-in">
                  🤖 AI 建議下一步：【{
                    aiRecommendedStep === 1 ? '研究定位' :
                    aiRecommendedStep === 2 ? '文獻採集' :
                    aiRecommendedStep === 3 ? '對比矩陣' :
                    aiRecommendedStep === 4 ? '知識圖譜' :
                    '課題建議'
                  }】
                </span>
              )}
            </div>
            <div className="stepper-steps">
              
              {/* Step 1 */}
              <div className={`step-item ${roleForm.large ? 'completed' : 'active'} ${aiRecommendedStep === 1 ? 'recommended' : ''}`} onClick={() => setShowRoleModal(true)}>
                <div className="step-number">
                  🎯
                  {aiRecommendedStep === 1 && <span className="recommended-dot" />}
                </div>
                <div className="step-label">研究定位</div>
                <div className="step-status-text">{roleForm.large ? '已設定' : '待定位'}</div>
              </div>
              
              <div className={`step-line ${summariesCount >= 2 ? 'completed' : ''}`} />

              {/* Step 2 */}
              <div className={`step-item ${summariesCount >= 2 ? 'completed' : (summariesCount === 1 || roleForm.large) ? 'active' : 'pending'} ${aiRecommendedStep === 2 ? 'recommended' : ''}`} onClick={() => setActivePage('chat')}>
                <div className="step-number">
                  📚
                  {aiRecommendedStep === 2 && <span className="recommended-dot" />}
                </div>
                <div className="step-label">文獻採集</div>
                <div className="step-status-text">已收錄 {summariesCount} 篇</div>
              </div>

              <div className={`step-line ${matrixCached ? 'completed' : ''}`} />

              {/* Step 3 */}
              <div className={`step-item ${matrixCached ? 'completed' : (summariesCount >= 2) ? 'active' : 'pending'} ${aiRecommendedStep === 3 ? 'recommended' : ''}`} onClick={() => setActivePage('matrix')}>
                <div className="step-number">
                  📊
                  {aiRecommendedStep === 3 && <span className="recommended-dot" />}
                </div>
                <div className="step-label">對比矩陣</div>
                <div className="step-status-text">{matrixCached ? '已生成' : '待生成'}</div>
              </div>

              <div className={`step-line ${summariesCount >= 2 ? 'completed' : ''}`} />

              {/* Step 4 */}
              <div className={`step-item ${summariesCount >= 2 ? 'completed' : summariesCount === 1 ? 'active' : 'pending'} ${aiRecommendedStep === 4 ? 'recommended' : ''}`} onClick={() => setActivePage('graph')}>
                <div className="step-number">
                  🕸️
                  {aiRecommendedStep === 4 && <span className="recommended-dot" />}
                </div>
                <div className="step-label">知識圖譜</div>
                <div className="step-status-text">{summariesCount >= 2 ? '已建構' : '文獻不足'}</div>
              </div>

              <div className={`step-line ${directionCached ? 'completed' : ''}`} />

              {/* Step 5 */}
              <div className={`step-item ${directionCached ? 'completed' : matrixCached ? 'active' : 'pending'} ${aiRecommendedStep === 5 ? 'recommended' : ''}`} onClick={() => setActivePage('direction')}>
                <div className="step-number">
                  🧭
                  {aiRecommendedStep === 5 && <span className="recommended-dot" />}
                </div>
                <div className="step-label">課題建議</div>
                <div className="step-status-text">{directionCached ? '已分析' : '待分析'}</div>
              </div>

            </div>
          </div>
        )}

        {/* 頁面內容 */}
        <div className="page-container">
          {renderPages()}
        </div>
      </main>

      {/* ─── 角色設定 Modal ─── */}
      {showRoleModal && (
        <div className="modal-backdrop" onClick={() => setShowRoleModal(false)}>
          <div className="modal glass-card fade-in" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>👤 研究方向設定</h2>
              <button className="btn btn-icon" onClick={() => setShowRoleModal(false)}>✕</button>
            </div>
            <p className="modal-desc">
              系統將根據您的對話自動分析並更新目前研究大、中、小方向。您也可以點擊下方展開手動調整。
            </p>

            <div className="modal-form">
              {/* 目前方向設定 */}
              <div className="current-direction-section" style={{
                background: 'rgba(99, 102, 241, 0.04)',
                border: '1px solid rgba(99, 102, 241, 0.15)',
                borderRadius: '8px',
                padding: '16px',
                marginBottom: '12px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '700', color: '#a5b4fc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    📡 目前方向設定 (AI 自動推導)
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    {summariesCount > 0 ? '🔒 已進入論文摘要階段，方向已鎖定' : '⚡ 隨對話即時更新中'}
                  </span>
                </div>
                
                {roleForm.large || roleForm.medium || roleForm.small ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    {roleForm.large && (
                      <div className="direction-pill" style={{
                        background: 'rgba(99, 102, 241, 0.12)',
                        border: '1px solid rgba(99, 102, 241, 0.25)',
                        borderRadius: '6px',
                        padding: '6px 12px',
                        fontSize: '12px',
                        color: '#c7d2fe',
                        fontWeight: '500'
                      }}>
                        <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', marginRight: '4px' }}>大</span>
                        {roleForm.large}
                      </div>
                    )}
                    {roleForm.large && (roleForm.medium || roleForm.small) && (
                      <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>➔</span>
                    )}
                    {roleForm.medium && (
                      <div className="direction-pill" style={{
                        background: 'rgba(139, 92, 246, 0.12)',
                        border: '1px solid rgba(139, 92, 246, 0.25)',
                        borderRadius: '6px',
                        padding: '6px 12px',
                        fontSize: '12px',
                        color: '#ddd6fe',
                        fontWeight: '500'
                      }}>
                        <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', marginRight: '4px' }}>中</span>
                        {roleForm.medium}
                      </div>
                    )}
                    {roleForm.medium && roleForm.small && (
                      <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>➔</span>
                    )}
                    {roleForm.small && (
                      <div className="direction-pill" style={{
                        background: 'rgba(236, 72, 153, 0.12)',
                        border: '1px solid rgba(236, 72, 153, 0.25)',
                        borderRadius: '6px',
                        padding: '6px 12px',
                        fontSize: '12px',
                        color: '#fbcfe8',
                        fontWeight: '500'
                      }}>
                        <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', marginRight: '4px' }}>小</span>
                        {roleForm.small}
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', padding: '4px 0' }}>
                    📡 目前尚未偵測到明確研究方向，可在對話中直接輸入您的研究想法，AI 將自動為您更新設定。
                  </div>
                )}
              </div>

              {/* 手動調整研究方向 */}
              <div style={{ margin: '8px 0' }}>
                <button 
                  type="button" 
                  onClick={() => setShowAdvanced(!showAdvanced)} 
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: '600',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '4px 0',
                    outline: 'none',
                    userSelect: 'none'
                  }}
                >
                  {showAdvanced ? '▼' : '▶'} ⚙️ 手動調整研究方向 (進階設定)
                </button>
              </div>

              {/* 進階設定欄位 */}
              {showAdvanced && (
                <div className="modal-form-advanced fade-in" style={{
                  background: 'rgba(255, 255, 255, 0.01)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '16px',
                  marginTop: '4px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: '0 0 4px 0' }}>
                    您可以在此手動輸入或微調目前的研究方向，儲存後即可生效。
                  </p>
                  <div className="direction-row">
                    <div className="direction-field">
                      <label>大方向</label>
                      <input
                        id="large-direction-input"
                        value={roleForm.large}
                        onChange={e => setRoleForm(p => ({ ...p, large: e.target.value }))}
                        placeholder="例：光電、材料科學、機器學習"
                      />
                    </div>
                    <div className="direction-arrow">➔</div>
                    <div className="direction-field">
                      <label>中方向</label>
                      <input
                        id="medium-direction-input"
                        value={roleForm.medium}
                        onChange={e => setRoleForm(p => ({ ...p, medium: e.target.value }))}
                        placeholder="例：太陽能電池"
                      />
                    </div>
                    <div className="direction-arrow">➔</div>
                    <div className="direction-field">
                      <label>小方向</label>
                      <input
                        id="small-direction-input"
                        value={roleForm.small}
                        onChange={e => setRoleForm(p => ({ ...p, small: e.target.value }))}
                        placeholder="例：鈣鈦礦"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setShowRoleModal(false)}>取消</button>
              <button id="save-role-btn" className="btn btn-primary" onClick={saveRoleState}>儲存設定</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
