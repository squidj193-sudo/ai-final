import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sendChat } from '../api.js'
import './MatrixPage.css'

export default function MatrixPage({ sessionId }) {
  const [matrix, setMatrix] = useState('')
  const [loading, setLoading] = useState(false)
  const [generated, setGenerated] = useState(false)

  const generateMatrix = async () => {
    setLoading(true)
    try {
      const res = await sendChat(sessionId, '生成比較矩陣')
      if (res.type === 'matrix') {
        setMatrix(res.content)
        setGenerated(true)
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
            <button id="export-matrix-btn" className="btn btn-ghost" onClick={exportMd}>
              📥 匯出 Markdown
            </button>
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
