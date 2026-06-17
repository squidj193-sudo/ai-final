import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sendChat, getDirection, setDirection as apiSetDirection } from '../api.js'
import './DirectionPage.css'

// 彩色卡片的左邊框顏色序列
const GAP_COLORS = [
  '#818cf8', '#f472b6', '#34d399', '#60a5fa', '#fbbf24', '#a78bfa'
]

// 從 Markdown 文字解析研究缺口列表
// 匹配格式：「1. **標題**\n內文」或「1. **標題（補充）**\n內文」
function parseGaps(text) {
  if (!text) return []
  try {
    const pattern = /\d+\.\s+\*\*(.+?)\*\*(?:[（(][^)）]*[)）])?\n+([\s\S]+?)(?=\n\d+\.|\n---\n|\n##|$)/g
    const matches = [...text.matchAll(pattern)]
    if (matches.length === 0) return []
    return matches.map(m => ({
      title: m[1].trim(),
      body: m[2].trim().slice(0, 200),
    }))
  } catch {
    return []
  }
}

export default function DirectionPage({ sessionId, onStateUpdate }) {
  const [report, setReport] = useState(() => localStorage.getItem(`direction_${sessionId}`) || '')
  const [loading, setLoading] = useState(false)

  // Load from backend (or fallback to localStorage) when sessionId changes
  useEffect(() => {
    let active = true
    const loadDirection = async () => {
      try {
        const data = await getDirection(sessionId)
        if (active) {
          if (data && data.direction) {
            setReport(data.direction)
            localStorage.setItem(`direction_${sessionId}`, data.direction)
            onStateUpdate?.()
          } else {
            // fallback to local storage
            const saved = localStorage.getItem(`direction_${sessionId}`) || ''
            setReport(saved)
            if (saved) {
              // sync fallback to backend
              await apiSetDirection(sessionId, saved)
              onStateUpdate?.()
            }
          }
        }
      } catch (e) {
        console.error("Failed to load direction from backend", e)
        if (active) {
          const saved = localStorage.getItem(`direction_${sessionId}`) || ''
          setReport(saved)
        }
      }
    }
    loadDirection()
    return () => { active = false }
  }, [sessionId])

  const analyze = async () => {
    setLoading(true)
    try {
      const res = await sendChat(sessionId, '分析研究方向')
      setReport(res.content)
      localStorage.setItem(`direction_${sessionId}`, res.content)
      await apiSetDirection(sessionId, res.content)
      onStateUpdate?.()
    } catch (e) {
      setReport(`⚠️ 發生錯誤：${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const exportMd = () => {
    const blob = new Blob([report], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'research-directions.md'
    a.click()
  }

  return (
    <div className="direction-page">
      <div className="direction-header">
        <div>
          <h1>🧭 研究方向建議</h1>
          <p>根據文獻矩陣，AI 自動識別研究缺口並提出可行建議</p>
        </div>
        <div className="direction-actions">
          <button id="analyze-direction-btn" className="btn btn-primary" onClick={analyze} disabled={loading}>
            {loading ? <><span className="spinner" /> 分析中...</> : '🧠 開始分析'}
          </button>
          {report && !report.startsWith('⚠️') && (
            <button id="export-direction-btn" className="btn btn-ghost" onClick={exportMd}>
              📥 匯出報告
            </button>
          )}
        </div>
      </div>

      <div className="direction-content">
        {!report && !loading ? (
          <div className="empty-state">
            <div className="direction-hero">
              <div style={{ fontSize: 64 }}>🧭</div>
              <div className="hero-glow" />
            </div>
            <h3>尚未分析研究方向</h3>
            <p>請先生成文獻比較矩陣，系統將根據矩陣識別研究缺口，並為您量身提出可行的研究方向建議。</p>
            <button className="btn btn-primary" onClick={analyze}>🧠 立即分析</button>
          </div>
        ) : loading ? (
          <div className="loading-state">
            <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
            <p>Agent 正在深度分析文獻矩陣，尋找研究缺口...</p>
            <p className="loading-sub">此步驟可能需要 15-30 秒，請稍候</p>
          </div>
        ) : (
          <div className="direction-body glass-card fade-in">
            {/* ── 研究缺口卡片列 ── */}
            {(() => {
              const gaps = parseGaps(report)
              if (gaps.length === 0) return null
              return (
                <div className="gap-cards-section">
                  <div className="gap-cards-label">🔍 識別到的研究缺口</div>
                  <div className="gap-cards-row">
                    {gaps.map((gap, i) => (
                      <div
                        key={i}
                        className="gap-card"
                        style={{ '--gap-color': GAP_COLORS[i % GAP_COLORS.length] }}
                      >
                        <div className="gap-card-index">{i + 1}</div>
                        <div className="gap-card-content">
                          <div className="gap-card-title">{gap.title}</div>
                          <div className="gap-card-body">{gap.body}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })()}
            {/* ── 完整 Markdown 報告 ── */}
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
