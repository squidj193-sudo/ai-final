import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sendChat, getMatrix, setMatrix as apiSetMatrix } from '../api.js'
import './MatrixPage.css'

export default function MatrixPage({ sessionId, onStateUpdate }) {
  const [matrix, setMatrix] = useState(() => localStorage.getItem(`matrix_${sessionId}`) || '')
  const [loading, setLoading] = useState(false)
  const [generated, setGenerated] = useState(() => !!localStorage.getItem(`matrix_${sessionId}`))

  // Load from backend (or fallback to localStorage) when sessionId changes
  useEffect(() => {
    let active = true
    const loadMatrix = async () => {
      try {
        const data = await getMatrix(sessionId)
        if (active) {
          if (data && data.matrix) {
            setMatrix(data.matrix)
            setGenerated(true)
            localStorage.setItem(`matrix_${sessionId}`, data.matrix)
            onStateUpdate?.()
          } else {
            // fallback to local storage
            const saved = localStorage.getItem(`matrix_${sessionId}`) || ''
            setMatrix(saved)
            setGenerated(!!saved)
            if (saved) {
              // sync fallback to backend
              await apiSetMatrix(sessionId, saved)
              onStateUpdate?.()
            }
          }
        }
      } catch (e) {
        console.error("Failed to load matrix from backend", e)
        if (active) {
          const saved = localStorage.getItem(`matrix_${sessionId}`) || ''
          setMatrix(saved)
          setGenerated(!!saved)
        }
      }
    }
    loadMatrix()
    return () => { active = false }
  }, [sessionId])

  const generateMatrix = async () => {
    setLoading(true)
    try {
      const res = await sendChat(sessionId, '生成比較矩陣')
      if (res.type === 'matrix') {
        setMatrix(res.content)
        setGenerated(true)
        localStorage.setItem(`matrix_${sessionId}`, res.content)
        await apiSetMatrix(sessionId, res.content)
        onStateUpdate?.()
      } else {
        setMatrix(res.content)
        setGenerated(false)
      }
    } catch (e) {
      setMatrix(`⚠️ 發生錯誤：${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const exportMd = () => {
    const blob = new Blob([matrix], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'literature-matrix.md'
    a.click()
  }

  const exportCsv = () => {
    const lines = matrix.split(/\r?\n/)
    const csvRows = []
    
    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        // Skip separator line (e.g. |---|---| or | :--- |)
        if (trimmed.includes('---')) {
          continue
        }
        const cells = trimmed.split('|').slice(1, -1).map(cell => cell.trim())
        const csvCells = cells.map(cell => {
          let escaped = cell.replace(/"/g, '""')
          if (escaped.includes(',') || escaped.includes('\n') || escaped.includes('\r') || escaped.includes('"')) {
            escaped = `"${escaped}"`
          }
          return escaped
        })
        csvRows.push(csvCells.join(','))
      }
    }
    
    // Add UTF-8 BOM for Excel Chinese compatibility
    const csvContent = "\uFEFF" + csvRows.join('\r\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'literature-matrix.csv'
    a.click()
  }

  return (
    <div className="matrix-page">
      <div className="matrix-header">
        <div>
          <h1>📊 文獻比較矩陣</h1>
          <p>彙整多篇論文的研究方法、發現與限制</p>
        </div>
        <div className="matrix-actions">
          <button id="generate-matrix-btn" className="btn btn-primary" onClick={generateMatrix} disabled={loading}>
            {loading ? <><span className="spinner" /> 生成中...</> : '⚡ 生成矩陣'}
          </button>
          {generated && (
            <div style={{ display: 'flex', gap: '8px' }}>
              <button id="export-matrix-btn" className="btn btn-ghost" onClick={exportMd}>
                📥 匯出 Markdown
              </button>
              <button id="export-matrix-csv-btn" className="btn btn-ghost" onClick={exportCsv}>
                📥 匯出 CSV
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="matrix-content">
        {!matrix && !loading ? (
          <div className="empty-state">
            <div style={{ fontSize: 56 }}>📊</div>
            <h3>尚未生成比較矩陣</h3>
            <p>請先至對話頁分析至少 2 篇論文，再點擊「生成矩陣」按鈕。</p>
            <button className="btn btn-primary" onClick={generateMatrix}>⚡ 立即生成</button>
          </div>
        ) : loading ? (
          <div className="loading-state">
            <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
            <p>Agent 正在分析論文並建立比較矩陣，請稍候...</p>
          </div>
        ) : (
          <div className="matrix-body glass-card fade-in">
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{matrix}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
