import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getSummaries } from '../api.js'
import './SummaryPage.css'

export default function SummaryPage({ sessionId }) {
  const [summaries, setSummaries] = useState([])
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const data = await getSummaries(sessionId)
      setSummaries(data.summaries || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [sessionId])

  const filtered = summaries.filter(s =>
    s.title.toLowerCase().includes(search.toLowerCase()) ||
    s.keywords?.some(k => k.toLowerCase().includes(search.toLowerCase()))
  )

  const exportMd = () => {
    const content = summaries.map(s =>
      `## ${s.title}\n\n**研究目的：** ${s.research_goal}\n\n**研究方法：** ${s.methodology}\n\n**主要發現：** ${s.main_findings}\n\n**研究限制：** ${s.limitations}\n\n**關鍵字：** ${s.keywords?.join('、')}\n\n---`
    ).join('\n\n')
    const blob = new Blob([content], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'paper-summaries.md'
    a.click()
  }

  const exportCsv = () => {
    const esc = (v) => `"${String(v || '').replace(/"/g, '""')}"`
    const headers = ['標題', '作者', '年份', '研究目的', '研究方法', '主要發現', '研究限制', '關鍵字']
    const rows = summaries.map(s => [
      esc(s.title),
      esc((s.authors || []).join('、')),
      s.year || '',
      esc(s.research_goal),
      esc(s.methodology),
      esc(s.main_findings),
      esc(s.limitations),
      esc((s.keywords || []).join('、')),
    ])
    // \uFEFF = UTF-8 BOM，讓 Excel 正確顯示中文
    const csv = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'paper-summaries.csv'
    a.click()
  }

  return (
    <div className="summary-page">
      <div className="summary-header">
        <div>
          <h1>📋 論文摘要記錄</h1>
          <p className="summary-count">{summaries.length} 篇已分析</p>
        </div>
        <div className="summary-actions">
          <div className="search-box">
            <span>🔍</span>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="搜尋標題或關鍵字..."
            />
          </div>
          <button className="btn btn-ghost" onClick={load} id="refresh-summaries">↻ 重新整理</button>
          <button className="btn btn-ghost" onClick={exportCsv} disabled={!summaries.length} id="export-summaries-csv">
            📊 匯出 CSV
          </button>
          <button className="btn btn-primary" onClick={exportMd} disabled={!summaries.length} id="export-summaries">
            📥 匯出 Markdown
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner" style={{ width: 32, height: 32 }} />
          <p>載入摘要中...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📚</div>
          <h3>{summaries.length === 0 ? '尚無論文摘要' : '找不到符合的結果'}</h3>
          <p>{summaries.length === 0 ? '請至對話頁上傳 PDF 論文，或搜尋論文後進行分析。' : '請嘗試其他搜尋關鍵字。'}</p>
        </div>
      ) : (
        <div className="summaries-grid">
          {filtered.map((s, index) => (
            <div
              key={`${index}-${s.paper_id || 'no-id'}`}
              className={`summary-card glass-card ${selected === s.paper_id ? 'selected' : ''}`}
              onClick={() => setSelected(selected === s.paper_id ? null : s.paper_id)}
            >
              <div className="summary-card-header">
                <div>
                  <h3 className="summary-title">{s.title}</h3>
                  <p className="summary-meta">
                    {s.authors?.slice(0, 2).join('、')}{s.authors?.length > 2 ? ' 等' : ''}
                    {s.year ? ` · ${s.year}` : ''}
                  </p>
                </div>
                <span className="expand-icon">{selected === s.paper_id ? '▲' : '▼'}</span>
              </div>

              <div className="keywords-row">
                {s.keywords?.map((k, kIdx) => (
                  <span key={`${kIdx}-${k}`} className="badge badge-purple">{k}</span>
                ))}
              </div>

              <div className="summary-preview">
                <strong>研究目的：</strong>{s.research_goal}
              </div>

              {selected === s.paper_id && (
                <div className="summary-detail fade-in">
                  <div className="detail-row">
                    <span className="detail-label">🔬 研究方法</span>
                    <p>{s.methodology}</p>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">📊 主要發現</span>
                    <p>{s.main_findings}</p>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">⚠️ 研究限制</span>
                    <p>{s.limitations}</p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
