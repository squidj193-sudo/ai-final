import { useState, useEffect } from 'react'
import ChatPage from './pages/ChatPage.jsx'
import SummaryPage from './pages/SummaryPage.jsx'
import MatrixPage from './pages/MatrixPage.jsx'
import DirectionPage from './pages/DirectionPage.jsx'
import { updateRoleState, getRoleState } from './api.js'
import { v4 as uuidv4 } from 'uuid'
import './App.css'

const NAV_ITEMS = [
  { id: 'chat',      icon: '💬', label: '對話搜尋' },
  { id: 'summary',   icon: '📋', label: '論文摘要' },
  { id: 'matrix',    icon: '📊', label: '比較矩陣' },
  { id: 'direction', icon: '🧭', label: '研究方向' },
]

function getOrCreateSession() {
  let id = localStorage.getItem('ai_session_id')
  if (!id) { id = uuidv4(); localStorage.setItem('ai_session_id', id) }
  return id
}

function getSavedConversations(defaultId) {
  const saved = localStorage.getItem('ai_conversations')
  if (saved) return JSON.parse(saved)
  return [{ id: defaultId, label: '研究對話 1', active: true }]
}

export default function App() {
  const [sessionId, setSessionId] = useState(getOrCreateSession)
  const [activePage, setActivePage] = useState('chat')
  const [conversations, setConversations] = useState(() => getSavedConversations(sessionId))

  const switchConversation = (id) => {
    setSessionId(id)
    localStorage.setItem('ai_session_id', id)
    setConversations(prev => {
      const next = prev.map(c => ({ ...c, active: c.id === id }))
      localStorage.setItem('ai_conversations', JSON.stringify(next))
      return next
    })
    setActivePage('chat')
  }

  const handleNewChat = () => {
    const newId = uuidv4()
    const newLabel = `研究對話 ${conversations.length + 1}`
    setSessionId(newId)
    localStorage.setItem('ai_session_id', newId)
    setConversations(prev => {
      const next = [...prev.map(c => ({ ...c, active: false })), { id: newId, label: newLabel, active: true }]
      localStorage.setItem('ai_conversations', JSON.stringify(next))
      return next
    })
    setActivePage('chat')
  }
  const [showRoleModal, setShowRoleModal] = useState(false)
  const [roleForm, setRoleForm] = useState({ large: '', medium: '', small: '' })
  const [roleDesc, setRoleDesc] = useState('尚未設定研究方向')
  const [summaryKey, setSummaryKey] = useState(0)

  // 載入角色狀態
  useEffect(() => {
    getRoleState(sessionId)
      .then(d => {
        setRoleDesc(d.description)
        setRoleForm({
          large: d.state.large_direction || '',
          medium: d.state.medium_direction || '',
          small: d.state.small_direction || '',
        })
      })
      .catch(() => {})
  }, [sessionId])

  const saveRoleState = async () => {
    try {
      await updateRoleState(sessionId, roleForm)
      const d = await getRoleState(sessionId)
      setRoleDesc(d.description)
      setShowRoleModal(false)
    } catch (e) {
      console.error(e)
    }
  }

  const renderPage = () => {
    switch (activePage) {
      case 'chat':      return <ChatPage key={sessionId} sessionId={sessionId} onSummaryUpdate={() => setSummaryKey(k => k + 1)} />
      case 'summary':   return <SummaryPage key={summaryKey} sessionId={sessionId} />
      case 'matrix':    return <MatrixPage sessionId={sessionId} />
      case 'direction': return <DirectionPage sessionId={sessionId} />
      default:          return null
    }
  }

  return (
    <div className="app-shell">
      {/* ─── 側邊欄 ─── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="logo-icon">🔬</span>
          <div>
            <h2>AI 研究助理</h2>
            <p>gemini-2.5-flash</p>
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
                style={{ cursor: 'pointer' }}
              >
                <span className="conv-dot">●</span>
                <span className="conv-label">{c.label}</span>
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
            <span className="badge badge-purple">Gemini 2.5 Flash</span>
            <span className="badge badge-green">RAG 已啟用</span>
          </div>
        </header>

        {/* 頁面內容 */}
        <div className="page-container">
          {renderPage()}
        </div>
      </main>

      {/* ─── 角色設定 Modal ─── */}
      {showRoleModal && (
        <div className="modal-backdrop" onClick={() => setShowRoleModal(false)}>
          <div className="modal glass-card fade-in" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>👤 研究角色設定</h2>
              <button className="btn btn-icon" onClick={() => setShowRoleModal(false)}>✕</button>
            </div>
            <p className="modal-desc">
              設定您的研究方向後，Agent 會自動縮小論文搜尋範圍，提供更精準的結果。
            </p>

            <div className="modal-form">
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
                <div className="direction-arrow">→</div>
                <div className="direction-field">
                  <label>中方向</label>
                  <input
                    id="medium-direction-input"
                    value={roleForm.medium}
                    onChange={e => setRoleForm(p => ({ ...p, medium: e.target.value }))}
                    placeholder="例：太陽能電池"
                  />
                </div>
                <div className="direction-arrow">→</div>
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

              {(roleForm.large || roleForm.medium || roleForm.small) && (
                <div className="direction-preview">
                  <span className="preview-label">目前設定：</span>
                  <span className="preview-path">
                    {[roleForm.large, roleForm.medium, roleForm.small]
                      .filter(Boolean)
                      .join(' › ')}
                  </span>
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
