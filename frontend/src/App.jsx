import { useState, useEffect } from 'react'
import ChatPage from './pages/ChatPage.jsx'
import SummaryPage from './pages/SummaryPage.jsx'
import MatrixPage from './pages/MatrixPage.jsx'
import GraphPage from './pages/GraphPage.jsx'
import DirectionPage from './pages/DirectionPage.jsx'
import { updateRoleState, getRoleState, getConversations, saveConversations, uploadPaper, getChatHistory, saveChatHistory, deleteConversation, getSummaries, getMatrix, getDirection, resetSystem, importDemos, diagnoseSystem, downloadBackup, uploadRestore, getSystemConfig, saveSystemConfig, getRagDocuments, deleteRagDocument, rebuildRagIndex } from './api.js'
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
  
  const [showToolsModal, setShowToolsModal] = useState(false)
  const [diagnostics, setDiagnostics] = useState(null)
  const [diagnosing, setDiagnosing] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  // 系統工具箱擴充狀態
  const [toolsActiveTab, setToolsActiveTab] = useState('diagnostics')
  const [configForm, setConfigForm] = useState({
    GEMINI_API_KEY: '',
    SEMANTIC_SCHOLAR_API_KEY: '',
    PAPERS_DB_PATH: '',
    GEMINI_MODEL: ''
  })
  const [showApiKey, setShowApiKey] = useState(false)
  const [ragDocs, setRagDocs] = useState([])
  const [loadingRag, setLoadingRag] = useState(false)
  const [savingConfig, setSavingConfig] = useState(false)

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
  const [roleForm, setRoleForm] = useState({ researchDirection: '' })
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
        researchDirection: d.state.research_direction || '',
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

  const handleRunDiagnostics = async () => {
    setDiagnosing(true)
    try {
      const data = await diagnoseSystem()
      setDiagnostics(data)
    } catch (e) {
      alert(`診斷失敗：${e.message}`)
    } finally {
      setDiagnosing(false)
    }
  }

  const handleResetSystem = async () => {
    if (!window.confirm("⚠️ 您確定要初始化系統嗎？\n這將清除所有對話紀錄、已分析文獻快取、比較矩陣以及 RAG 知識庫中的所有論文！此操作無法復原！")) {
      return
    }
    if (!window.confirm("‼️ 請再次確認：此操作會清除所有已上傳的 PDF 檔案與研究進度，您真的要重置嗎？")) {
      return
    }

    setActionLoading(true)
    try {
      const res = await resetSystem()
      
      // 清空本地存儲快取
      localStorage.clear()
      
      // 重新載入對話列表並切換
      const data = await getConversations()
      setConversations(data.conversations || [])
      setSessionId(res.session_id)
      
      alert("✅ 系統已初始化完成，所有快取與資料已清空！")
      setShowToolsModal(false)
      setActivePage('chat')
    } catch (e) {
      alert(`重置失敗：${e.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const handleImportDemos = async () => {
    setActionLoading(true)
    try {
      const res = await importDemos(sessionId)
      if (res.imported > 0) {
        alert(`✅ 成功匯入 ${res.imported} 篇示範文獻！\n系統已自動為您推導設定研究方向。\n現在您可以立即去「對話搜尋」檢視論文摘要、「比較矩陣」或「論文圖譜」測試功能。`)
        refreshState()
      } else {
        alert("ℹ️ 示範文獻先前已匯入過，無需重複匯入。")
      }
      setShowToolsModal(false)
    } catch (e) {
      alert(`匯入失敗：${e.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  // 加載系統設定
  const loadConfig = async () => {
    try {
      const data = await getSystemConfig()
      setConfigForm(data)
    } catch (e) {
      console.error("無法載入環境設定:", e)
    }
  }

  // 加載 RAG 文獻列表
  const loadRagDocs = async () => {
    setLoadingRag(true)
    try {
      const data = await getRagDocuments()
      setRagDocs(data.documents || [])
    } catch (e) {
      console.error("無法載入文獻清單:", e)
    } finally {
      setLoadingRag(false)
    }
  }

  // 當 Tab 切換或 Modal 開啟時載入數據
  useEffect(() => {
    if (showToolsModal) {
      if (toolsActiveTab === 'settings') {
        loadConfig()
      } else if (toolsActiveTab === 'rag') {
        loadRagDocs()
      }
    }
  }, [toolsActiveTab, showToolsModal])

  // 匯出備份
  const handleDownloadBackup = () => {
    downloadBackup()
  }

  // 匯入還原
  const handleUploadRestore = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!window.confirm("⚠️ 您確定要還原此備份嗎？\n這會清除目前所有數據，並覆寫為備份檔案中的狀態！此操作無法復原。")) {
      return
    }
    setActionLoading(true)
    try {
      await uploadRestore(file)
      alert("✅ 系統資料還原成功！")
      // 重置頁面與狀態
      localStorage.clear()
      const data = await getConversations()
      setConversations(data.conversations || [])
      if (data.conversations?.length > 0) {
        setSessionId(data.conversations[0].id)
      }
      refreshState()
      setShowToolsModal(false)
      setActivePage('chat')
    } catch (e) {
      alert(`還原失敗：${e.message}`)
    } finally {
      setActionLoading(false)
      e.target.value = '' // 清除 input 值以供下次選擇
    }
  }

  // 儲存設定
  const handleSaveConfig = async (e) => {
    e.preventDefault()
    setSavingConfig(true)
    try {
      await saveSystemConfig(configForm)
      alert("✅ 設定儲存成功！已完成熱重載 API 設定。")
      loadConfig() // 重新加載更新後的屏蔽值
    } catch (e) {
      alert(`儲存失敗：${e.message}`)
    } finally {
      setSavingConfig(false)
    }
  }

  // 刪除單篇論文
  const handleDeleteDoc = async (paperId, title) => {
    if (!window.confirm(`⚠️ 您確定要完全刪除論文「${title}」嗎？\n這將會移除此論文摘要、向量 RAG 知識庫及 PDF 文件，但不會影響其他論文。`)) {
      return
    }
    setLoadingRag(true)
    try {
      await deleteRagDocument(paperId)
      alert("✅ 論文已成功刪除！")
      loadRagDocs() // 重新加載
      refreshState()
    } catch (e) {
      alert(`刪除失敗：${e.message}`)
    } finally {
      setLoadingRag(false)
    }
  }

  // 重建 RAG 索引
  const handleRebuildIndex = async () => {
    if (!window.confirm("⚠️ 您確定要重建所有 RAG 索引嗎？\n系統會重新掃描本地 papers 目錄下的 PDF 檔案並重新進行 AI 格式解讀與索引重建，這可能需要數十秒至數分鐘。")) {
      return
    }
    setActionLoading(true)
    try {
      const res = await rebuildRagIndex()
      alert(`✅ 索引重建完成！成功重新索引 ${res.reindexed} 篇文獻。`)
      loadRagDocs()
      refreshState()
    } catch (e) {
      alert(`重建失敗：${e.message}`)
    } finally {
      setActionLoading(false)
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
              className="system-tools-btn"
              onClick={() => {
                setShowToolsModal(true);
                handleRunDiagnostics();
              }}
              title="系統工具箱 (重置、匯入示範文獻、檢測)"
            >
              🛠️ 系統工具
            </button>
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
              <div className={`step-item ${roleForm.researchDirection ? 'completed' : 'active'} ${aiRecommendedStep === 1 ? 'recommended' : ''}`} onClick={() => setShowRoleModal(true)}>
                <div className="step-number">
                  🎯
                  {aiRecommendedStep === 1 && <span className="recommended-dot" />}
                </div>
                <div className="step-label">研究定位</div>
                <div className="step-status-text">{roleForm.researchDirection ? '已設定' : '待定位'}</div>
              </div>

              <div className={`step-line ${roleForm.researchDirection ? 'completed' : ''}`} />

              {/* Step 2 */}
              <div className={`step-item ${summariesCount >= 1 ? 'completed' : roleForm.researchDirection ? 'active' : 'pending'} ${aiRecommendedStep === 2 ? 'recommended' : ''}`} onClick={() => setActivePage('summary')}>
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
                    📡 目前研究方向 (AI 自動推導)
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    {summariesCount > 0 ? '🔒 已進入論文摘要階段，方向已鎖定' : '⚡ 隨對話即時更新中'}
                  </span>
                </div>
                
                {roleForm.researchDirection ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <div className="direction-pill" style={{
                      background: 'rgba(99, 102, 241, 0.12)',
                      border: '1px solid rgba(99, 102, 241, 0.25)',
                      borderRadius: '6px',
                      padding: '6px 12px',
                      fontSize: '12px',
                      color: '#c7d2fe',
                      fontWeight: '500'
                    }}>
                      <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', marginRight: '4px' }}>🎯</span>
                      {roleForm.researchDirection}
                    </div>
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
                    您可以在此手動輸入或微調目前的研究大方向，儲存後即可生效。
                  </p>
                  <div className="direction-field" style={{ maxWidth: '400px' }}>
                    <label>研究方向</label>
                    <input
                      id="large-direction-input"
                      value={roleForm.researchDirection}
                      onChange={e => setRoleForm({ researchDirection: e.target.value })}
                      placeholder="例：鈣鈦礦太陽能電池元件效能、大型語言模型微調"
                    />
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

      {/* ─── 系統工具 Modal ─── */}
      {showToolsModal && (
        <div className="modal-backdrop" onClick={() => { if (!actionLoading) setShowToolsModal(false) }}>
          <div className="modal glass-card fade-in" style={{ maxWidth: '560px' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>🛠️ 系統工具箱</h2>
              <button className="btn btn-icon" disabled={actionLoading} onClick={() => setShowToolsModal(false)}>✕</button>
            </div>
            
            <div className="tools-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '20px', minHeight: '380px' }}>
              
              {/* Tab 頁籤切換 */}
              <div className="tools-modal-tabs" style={{ display: 'flex', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '10px' }}>
                <button 
                  type="button"
                  className={`tab-item ${toolsActiveTab === 'diagnostics' ? 'active' : ''}`}
                  onClick={() => setToolsActiveTab('diagnostics')}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '6px',
                    border: 'none',
                    background: toolsActiveTab === 'diagnostics' ? 'rgba(99,102,241,0.15)' : 'transparent',
                    color: toolsActiveTab === 'diagnostics' ? '#a5b4fc' : 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: '600',
                    transition: 'all 0.2s'
                  }}
                >
                  🔍 診斷與重置
                </button>
                <button 
                  type="button"
                  className={`tab-item ${toolsActiveTab === 'settings' ? 'active' : ''}`}
                  onClick={() => setToolsActiveTab('settings')}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '6px',
                    border: 'none',
                    background: toolsActiveTab === 'settings' ? 'rgba(99,102,241,0.15)' : 'transparent',
                    color: toolsActiveTab === 'settings' ? '#a5b4fc' : 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: '600',
                    transition: 'all 0.2s'
                  }}
                >
                  ⚙️ 參數與備份設定
                </button>
                <button 
                  type="button"
                  className={`tab-item ${toolsActiveTab === 'rag' ? 'active' : ''}`}
                  onClick={() => setToolsActiveTab('rag')}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '6px',
                    border: 'none',
                    background: toolsActiveTab === 'rag' ? 'rgba(99,102,241,0.15)' : 'transparent',
                    color: toolsActiveTab === 'rag' ? '#a5b4fc' : 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: '600',
                    transition: 'all 0.2s'
                  }}
                >
                  📚 知識庫文獻管理
                </button>
              </div>

              {/* 1. 診斷與重置頁面 */}
              {toolsActiveTab === 'diagnostics' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {/* 診斷區塊 */}
                  <div className="diagnostics-panel" style={{
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '16px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                      <span style={{ fontSize: '13px', fontWeight: '700', color: '#a5b4fc' }}>
                        🔍 系統狀態自我檢測
                      </span>
                      <button 
                        className="btn btn-ghost" 
                        style={{ padding: '2px 8px', fontSize: '11px', height: 'auto' }}
                        onClick={handleRunDiagnostics}
                        disabled={diagnosing || actionLoading}
                      >
                        {diagnosing ? '檢測中...' : '🔄 重新檢測'}
                      </button>
                    </div>

                    <div className="diagnostics-list" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {diagnostics ? (
                        Object.entries(diagnostics).map(([key, item]) => (
                          <div key={key} style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
                            <div style={{ fontSize: '12px' }}>
                              <strong>{
                                key === 'gemini_api' ? 'Gemini API 連線' :
                                key === 'pdf_parser' ? 'PDF 解析器依賴' :
                                key === 'semantic_scholar' ? '學術資料庫 API' :
                                '本地磁碟寫入'
                              }：</strong>
                              <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '11px', marginTop: '2px' }}>
                                {item.message}
                              </span>
                            </div>
                            <span className={`status-badge status-${item.status}`} style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: '600',
                              whiteSpace: 'nowrap',
                              background: item.status === 'success' ? 'rgba(16,185,129,0.15)' : item.status === 'warning' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                              color: item.status === 'success' ? '#34d399' : item.status === 'warning' ? '#fbbf24' : '#f87171',
                              border: `1px solid ${item.status === 'success' ? 'rgba(16,185,129,0.3)' : item.status === 'warning' ? 'rgba(245,158,11,0.3)' : 'rgba(239,68,68,0.3)'}`
                            }}>
                              {item.status === 'success' ? '正常' : item.status === 'warning' ? '警告' : '失敗'}
                            </span>
                          </div>
                        ))
                      ) : (
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '10px 0' }}>
                          正在執行系統診斷...
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 操作區塊 */}
                  <div className="tools-actions-panel" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {/* 匯入示範數據 */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '16px',
                      background: 'rgba(99,102,241,0.03)',
                      border: '1px solid rgba(99,102,241,0.15)',
                      borderRadius: '8px',
                      padding: '16px'
                    }}>
                      <div style={{ flex: 1 }}>
                        <h4 style={{ margin: 0, fontSize: '13px', color: '#c7d2fe' }}>📚 匯入示範學術論文</h4>
                        <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                          一鍵匯入 2 篇精選示範論文（鈣鈦礦太陽能、CoT 推理），自動設定研究定位，以便立刻測試對比矩陣與圖譜。
                        </p>
                      </div>
                      <button 
                        className="btn btn-primary" 
                        onClick={handleImportDemos}
                        disabled={actionLoading}
                        style={{ whiteSpace: 'nowrap' }}
                      >
                        {actionLoading ? '請稍候...' : '📥 快速匯入'}
                      </button>
                    </div>

                    {/* 重置系統 */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '16px',
                      background: 'rgba(239,68,68,0.03)',
                      border: '1px solid rgba(239,68,68,0.15)',
                      borderRadius: '8px',
                      padding: '16px'
                    }}>
                      <div style={{ flex: 1 }}>
                        <h4 style={{ margin: 0, fontSize: '13px', color: '#fca5a5' }}>⚠️ 一鍵初始化系統</h4>
                        <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                          刪除所有對話紀錄、快取的論文摘要、對比矩陣，並清空 RAG 知識庫資料夾。會保留 API Key 設定。
                        </p>
                      </div>
                      <button 
                        className="btn" 
                        onClick={handleResetSystem}
                        disabled={actionLoading}
                        style={{ whiteSpace: 'nowrap', backgroundColor: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' }}
                      >
                        {actionLoading ? '重置中...' : '🧹 系統初始化'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* 2. 參數與備份設定頁面 */}
              {toolsActiveTab === 'settings' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {/* 備份與還原面板 */}
                  <div style={{
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '16px'
                  }}>
                    <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#a5b4fc' }}>💾 系統資料備份與還原</h4>
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <button 
                        type="button"
                        className="btn"
                        onClick={handleDownloadBackup}
                        style={{ flex: 1, fontSize: '12px', background: 'rgba(255,255,255,0.05)', color: 'var(--text-primary)', border: '1px solid rgba(255,255,255,0.15)' }}
                      >
                        📤 匯出完整備份 (ZIP)
                      </button>
                      <label 
                        className="btn btn-ghost" 
                        style={{ flex: 1, fontSize: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', margin: 0, border: '1px solid rgba(99,102,241,0.3)' }}
                      >
                        📥 匯入備份還原
                        <input 
                          type="file" 
                          accept=".zip" 
                          onChange={handleUploadRestore} 
                          style={{ display: 'none' }} 
                          disabled={actionLoading}
                        />
                      </label>
                    </div>
                  </div>

                  {/* 環境變數參數表單 */}
                  <form onSubmit={handleSaveConfig} style={{
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}>
                    <h4 style={{ margin: '0 0 4px 0', fontSize: '13px', color: '#a5b4fc' }}>⚙️ API 金鑰與模型變數設定</h4>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Gemini API 金鑰</label>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <input 
                          type={showApiKey ? 'text' : 'password'}
                          value={configForm.GEMINI_API_KEY}
                          onChange={e => setConfigForm({...configForm, GEMINI_API_KEY: e.target.value})}
                          placeholder="請輸入 Gemini API Key..."
                          style={{
                            flex: 1,
                            background: 'rgba(0,0,0,0.2)',
                            border: '1px solid rgba(255,255,255,0.15)',
                            borderRadius: '4px',
                            color: 'var(--text-primary)',
                            padding: '8px',
                            fontSize: '12px'
                          }}
                        />
                        <button 
                          type="button"
                          className="btn"
                          onClick={() => setShowApiKey(!showApiKey)}
                          style={{ padding: '0 12px', fontSize: '12px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.15)' }}
                        >
                          {showApiKey ? '隱藏' : '顯示'}
                        </button>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>主要語言模型 (GEMINI_MODEL)</label>
                      <select 
                        value={configForm.GEMINI_MODEL}
                        onChange={e => setConfigForm({...configForm, GEMINI_MODEL: e.target.value})}
                        style={{
                          background: '#1a1b26',
                          border: '1px solid rgba(255,255,255,0.15)',
                          borderRadius: '4px',
                          color: 'var(--text-primary)',
                          padding: '8px',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        <option value="gemini-3.5-flash">gemini-3.5-flash (推薦: 速度最快)</option>
                        <option value="gemini-1.5-pro">gemini-1.5-pro (推薦: 適合推理)</option>
                        <option value="gemini-3.1-flash-lite">gemini-3.1-flash-lite</option>
                        <option value="gemma-4-26b-a4b-it">gemma-4-26b-a4b-it</option>
                      </select>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Semantic Scholar API 金鑰 (選填)</label>
                      <input 
                        type="password"
                        value={configForm.SEMANTIC_SCHOLAR_API_KEY}
                        onChange={e => setConfigForm({...configForm, SEMANTIC_SCHOLAR_API_KEY: e.target.value})}
                        placeholder="無 (留空將使用免費配額與共用限制)..."
                        style={{
                          background: 'rgba(0,0,0,0.2)',
                          border: '1px solid rgba(255,255,255,0.15)',
                          borderRadius: '4px',
                          color: 'var(--text-primary)',
                          padding: '8px',
                          fontSize: '12px'
                        }}
                      />
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>本地知識庫資料夾 (PAPERS_DB_PATH)</label>
                      <input 
                        type="text"
                        value={configForm.PAPERS_DB_PATH}
                        readOnly
                        style={{
                          background: 'rgba(0,0,0,0.4)',
                          border: '1px solid rgba(255,255,255,0.08)',
                          borderRadius: '4px',
                          color: 'var(--text-muted)',
                          padding: '8px',
                          fontSize: '12px'
                        }}
                      />
                      <span style={{ fontSize: '9px', color: 'var(--text-muted)' }}>※ 為保護系統路徑安全，此參數設定為唯讀，固定於專案的 data/papers/ 目錄。</span>
                    </div>

                    <button 
                      type="submit" 
                      className="btn btn-primary"
                      disabled={savingConfig}
                      style={{ marginTop: '8px', width: '100%' }}
                    >
                      {savingConfig ? '儲存中...' : '💾 儲存並熱重載設定'}
                    </button>
                  </form>
                </div>
              )}

              {/* 3. 知識庫文獻管理頁面 */}
              {toolsActiveTab === 'rag' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {/* 文獻表格 */}
                  <div style={{
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '16px',
                    maxHeight: '300px',
                    overflowY: 'auto'
                  }}>
                    <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#a5b4fc', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>📚 已上傳文獻清單</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 'normal' }}>總計: {ragDocs.length} 篇</span>
                    </h4>

                    {loadingRag ? (
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '30px 0', gap: '8px' }}>
                        <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>讀取資料中...</span>
                      </div>
                    ) : ragDocs.length > 0 ? (
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', textAlign: 'left' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-muted)' }}>
                            <th style={{ padding: '8px 4px' }}>標題</th>
                            <th style={{ padding: '8px 4px', width: '60px' }}>年份</th>
                            <th style={{ padding: '8px 4px', width: '90px' }}>檔案大小</th>
                            <th style={{ padding: '8px 4px', width: '60px', textAlign: 'center' }}>操作</th>
                          </tr>
                        </thead>
                        <tbody>
                          {ragDocs.map((doc, idx) => (
                            <tr key={doc.paper_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                              <td style={{ padding: '8px 4px', maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={doc.title}>
                                📄 {doc.title}
                              </td>
                              <td style={{ padding: '8px 4px' }}>{doc.year || '未知'}</td>
                              <td style={{ padding: '8px 4px', color: 'var(--text-secondary)' }}>{doc.size}</td>
                              <td style={{ padding: '8px 4px', textAlign: 'center' }}>
                                <button 
                                  type="button"
                                  className="btn"
                                  onClick={() => handleDeleteDoc(doc.paper_id, doc.title)}
                                  style={{
                                    padding: '2px 6px',
                                    fontSize: '10px',
                                    backgroundColor: 'rgba(239,68,68,0.1)',
                                    color: '#f87171',
                                    border: '1px solid rgba(239,68,68,0.2)',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  🗑️ 刪除
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text-muted)', fontSize: '12px' }}>
                        目前資料庫中無任何論文文獻。您可以使用「快速匯入」或「📎 上傳論文」來添加。
                      </div>
                    )}
                  </div>

                  {/* 全域索引重建 */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '16px',
                    background: 'rgba(245,158,11,0.03)',
                    border: '1px solid rgba(245,158,11,0.15)',
                    borderRadius: '8px',
                    padding: '16px'
                  }}>
                    <div style={{ flex: 1 }}>
                      <h4 style={{ margin: 0, fontSize: '13px', color: '#fde047' }}>🔄 重建 RAG 向量索引 (RAG Rebuilder)</h4>
                      <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                        如果資料庫索引發生混亂、或是更新了 PDF 解析套件，此操作會重新將本地 `data/papers` 下所有 PDF 解析並重構向量庫檢索。
                      </p>
                    </div>
                    <button 
                      type="button"
                      className="btn" 
                      onClick={handleRebuildIndex}
                      disabled={actionLoading}
                      style={{ whiteSpace: 'nowrap', backgroundColor: 'rgba(245,158,11,0.15)', color: '#fef08a', border: '1px solid rgba(245,158,11,0.3)' }}
                    >
                      {actionLoading ? '重建中...' : '🔄 索引重構'}
                    </button>
                  </div>
                </div>
              )}

            </div>

            <div className="modal-footer">
              <button className="btn btn-ghost" disabled={actionLoading} onClick={() => setShowToolsModal(false)}>關閉</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
