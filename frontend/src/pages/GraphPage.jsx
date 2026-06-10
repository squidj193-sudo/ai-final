import { useState, useEffect } from 'react'
import { getGraph } from '../api.js'
import './GraphPage.css'

export default function GraphPage({ sessionId }) {
  const [graphHtml, setGraphHtml] = useState('')
  const [paperCount, setPaperCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadGraph = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getGraph(sessionId)
      setPaperCount(res.count)
      setGraphHtml(res.html)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGraph()
  }, [sessionId])

  return (
    <div className="graph-page">
      <div className="graph-header">
        <div>
          <h1>🕸️ 論文圖譜</h1>
          <p>根據已分析論文的語意相似度，自動建立互動式知識圖譜</p>
        </div>
        <div className="graph-actions">
          <span className="graph-count-badge">
            {paperCount > 0 ? `共 ${paperCount} 篇論文` : '尚無論文'}
          </span>
          <button
            id="refresh-graph-btn"
            className="btn btn-primary"
            onClick={loadGraph}
            disabled={loading}
          >
            {loading ? <><span className="spinner" /> 生成中...</> : '🔄 重新生成'}
          </button>
        </div>
      </div>

      <div className="graph-content">
        {loading ? (
          <div className="loading-state">
            <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
            <p>正在建構論文知識圖譜...</p>
            <p className="loading-sub">依論文語意相似度計算中，請稍候</p>
          </div>
        ) : error ? (
          <div className="empty-state">
            <div style={{ fontSize: 48 }}>⚠️</div>
            <h3>載入失敗</h3>
            <p>{error}</p>
            <button className="btn btn-primary" onClick={loadGraph}>重試</button>
          </div>
        ) : paperCount === 0 ? (
          <div className="empty-state">
            <div className="graph-hero">
              <div style={{ fontSize: 64 }}>🕸️</div>
              <div className="hero-glow" />
            </div>
            <h3>尚無論文資料</h3>
            <p>請先在「對話搜尋」頁面上傳 PDF 或搜尋分析論文，<br />系統將自動依語意相似度建立圖譜。</p>
          </div>
        ) : (
          <div className="graph-frame-wrapper glass-card fade-in">
            <iframe
              id="graph-iframe"
              className="graph-iframe"
              srcDoc={graphHtml}
              title="論文知識圖譜"
              sandbox="allow-scripts"
            />
          </div>
        )}
      </div>
    </div>
  )
}
