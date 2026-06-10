import { useState, useEffect, useRef } from 'react'
import { getGraph } from '../api.js'
import './GraphPage.css'

const COMMUNITY_COLORS = [
  '#818cf8', // Indigo
  '#f472b6', // Pink
  '#34d399', // Emerald
  '#60a5fa', // Blue
  '#fb7185', // Rose
  '#a78bfa', // Purple
  '#fbbf24', // Amber
  '#2dd4bf', // Teal
  '#f87171', // Red
  '#fb923c'  // Orange
]

export default function GraphPage({ sessionId, activePage }) {
  const [rawData, setRawData] = useState({ nodes: [], edges: [] })
  const [communityLabels, setCommunityLabels] = useState({})
  const [paperCount, setPaperCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // Slider & Panel States
  const [threshold, setThreshold] = useState(0.15)
  const [selectedItem, setSelectedItem] = useState(null)
  const [selectedType, setSelectedType] = useState(null) // 'node' | 'edge' | null
  
  const containerRef = useRef(null)
  const networkRef = useRef(null)
  const [visLoaded, setVisLoaded] = useState(false)

  // 1. 動態載入 Vis.js CDN (避免 bundler 過大，且更安全)
  useEffect(() => {
    if (window.vis) {
      setVisLoaded(true)
      return
    }
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js'
    script.async = true
    script.onload = () => setVisLoaded(true)
    script.onerror = () => setError('無法載入 Vis.js 圖表渲染庫，請檢查您的網路連線。')
    document.body.appendChild(script)

    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/vis-network/styles/vis-network.min.css'
    document.head.appendChild(link)

    return () => {
      // 保持全域庫以加速之後的加載
    }
  }, [])

  // 2. 獲取圖譜原始數據
  const loadGraphData = async () => {
    setLoading(true)
    setError(null)
    setSelectedItem(null)
    setSelectedType(null)
    try {
      const res = await getGraph(sessionId)
      setRawData(res)
      setCommunityLabels(res.community_labels || {})
      setPaperCount(res.count)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGraphData()
  }, [sessionId])

  // 3. 核心 Vis.js 渲染與過濾邏輯
  useEffect(() => {
    if (!visLoaded || !containerRef.current || !rawData.nodes || rawData.nodes.length === 0) return
    // 當前分頁不是圖譜時，不進行畫布初始化或重繪，避免 display none 下寬高被誤判為 0
    if (activePage !== 'graph') return

    // 依相似度閾值過濾連線
    const filteredEdges = rawData.edges
      .filter(edge => edge.weight >= threshold)
      .map(edge => ({
        from: edge.from,
        to: edge.to,
        value: edge.weight,
        title: `共同核心主題: ${edge.common_terms.join(', ') || '一般關聯'} (${(edge.weight * 100).toFixed(1)}%)`,
        // 額外欄位，供點擊事件讀取
        customData: {
          weight: edge.weight,
          common_terms: edge.common_terms,
          fromNode: rawData.nodes[edge.from],
          toNode: rawData.nodes[edge.to]
        }
      }))

    // 格式化 Nodes
    const formattedNodes = rawData.nodes.map(node => {
      const color = COMMUNITY_COLORS[node.group % COMMUNITY_COLORS.length]
      return {
        id: node.id,
        label: node.label,
        size: Math.max(15, node.pagerank * 100 + 15),
        color: {
          background: color,
          border: color,
          highlight: {
            background: color,
            border: '#ffffff'
          }
        },
        title: `📄 ${node.title}\n作者: ${node.authors}\n年份: ${node.year}`,
        customData: node
      }
    })

    const visNodes = new window.vis.DataSet(formattedNodes)
    const visEdges = new window.vis.DataSet(filteredEdges)

    const data = { nodes: visNodes, edges: visEdges }
    const options = {
      nodes: {
        shape: 'dot',
        font: {
          size: 11,
          color: '#e2e8f0',
          face: 'system-ui, -apple-system, sans-serif',
          strokeWidth: 3,
          strokeColor: '#0a0e1a'
        },
        borderWidth: 2
      },
      edges: {
        color: {
          color: 'rgba(99, 102, 241, 0.25)',
          highlight: '#f472b6',
          hover: 'rgba(99, 102, 241, 0.6)'
        },
        smooth: {
          type: 'continuous',
          forceDirection: 'none',
          roundness: 0.5
        },
        hoverWidth: 2.5
      },
      interaction: {
        hover: true,
        tooltipDelay: 150,
        selectable: true,
        selectConnectedEdges: false
      },
      physics: {
        barnesHut: {
          gravitationalConstant: -4000,
          centralGravity: 0.2,
          springLength: 200,
          springConstant: 0.04,
          damping: 0.09,
          avoidOverlap: 0.1
        },
        solver: 'barnesHut'
      }
    }

    const network = new window.vis.Network(containerRef.current, data, options)
    networkRef.current = network

    // 第一次繪製完成後，執行一次 fit() 以居中適應
    network.once('afterDrawing', () => {
      network.fit()
    })

    // 綁定點擊事件
    network.on('click', (params) => {
      if (params.nodes.length > 0) {
        // 點擊節點
        const nodeId = params.nodes[0]
        const clickedNode = rawData.nodes.find(n => n.id === nodeId)
        if (clickedNode) {
          setSelectedItem(clickedNode)
          setSelectedType('node')
        }
      } else if (params.edges.length > 0) {
        // 點擊連線
        const edgeId = params.edges[0]
        // 藉由 edgeId 尋找過濾後對應的 Vis Edge 實例
        const edgeObj = visEdges.get(edgeId)
        if (edgeObj && edgeObj.customData) {
          setSelectedItem(edgeObj.customData)
          setSelectedType('edge')
        }
      } else {
        // 點擊空白處
        setSelectedItem(null)
        setSelectedType(null)
      }
    })

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy()
        networkRef.current = null
      }
    }
  }, [visLoaded, rawData, threshold, activePage])

  return (
    <div className="graph-page">
      {/* 標題與操作欄 */}
      <div className="graph-header">
        <div>
          <h1>🕸️ 論文知識圖譜</h1>
          <p>基於已分析文獻的語意相似度動態關聯。請點選「節點」或「連線」查看詳細分析與關聯原因。</p>
        </div>
        <div className="graph-actions">
          <span className="graph-count-badge">
            {paperCount > 0 ? `收錄 ${paperCount} 篇文獻` : '尚無資料'}
          </span>
          <button
            id="refresh-graph-btn"
            className="btn btn-primary"
            onClick={loadGraphData}
            disabled={loading}
          >
            {loading ? <><span className="spinner" /> 計算中...</> : '🔄 重新計算'}
          </button>
        </div>
      </div>

      <div className="graph-content-wrapper">
        {loading ? (
          <div className="loading-state">
            <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
            <p>正在動態建立文獻關聯圖譜...</p>
            <p className="loading-sub">計算 TF-IDF 語意特徵值中，請稍候</p>
          </div>
        ) : error ? (
          <div className="empty-state animate-fade-in">
            <div style={{ fontSize: 48 }}>⚠️</div>
            <h3>載入失敗</h3>
            <p>{error}</p>
            <button className="btn btn-primary" onClick={loadGraphData}>重試</button>
          </div>
        ) : paperCount === 0 ? (
          <div className="empty-state animate-fade-in">
            <div className="graph-hero">
              <div style={{ fontSize: 64 }}>🕸️</div>
              <div className="hero-glow" />
            </div>
            <h3>尚無論文資料</h3>
            <p>請先在「對話搜尋」頁面上傳 PDF 或搜尋分析論文，<br />系統將自動依語意相似度建立圖譜。</p>
          </div>
        ) : (
          <div className="graph-main-layout">
            
            {/* 左側：圖譜畫布與控制項 */}
            <div className="graph-canvas-container glass-card">
              
              {/* 控制項：滑桿過濾門檻 */}
              <div className="graph-controls-panel">
                <div className="control-group">
                  <label htmlFor="similarity-slider">
                    🔗 相似度過濾門檻：<span>{(threshold * 100).toFixed(0)}%</span>
                  </label>
                  <input
                    id="similarity-slider"
                    type="range"
                    min="0.05"
                    max="0.80"
                    step="0.05"
                    value={threshold}
                    onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  />
                  <span className="control-help-text">（拉高數值可過濾微弱關聯，消除視野雜訊）</span>
                </div>
              </div>

              {/* 畫布 */}
              <div 
                ref={containerRef} 
                className="graph-canvas" 
                id="mynetwork"
              />
              
              {/* 說明指標圖例 */}
              <div className="graph-legend-bar">
                {/* 第一行：社群分類標題 */}
                <div className="legend-section-title">🏷️ 社群分類</div>
                {/* 第二行：動態社群 pill badges */}
                <div className="legend-community-row">
                  {(() => {
                    const hasLabels = Object.keys(communityLabels).length > 0
                    const hasNodes = rawData.nodes && rawData.nodes.length > 0
                    if (!hasLabels && !hasNodes) {
                      return <span className="legend-empty-hint">尚無論文資料</span>
                    }
                    if (!hasLabels && hasNodes) {
                      return <span className="legend-empty-hint">社群分析中…</span>
                    }
                    // 計算每個社群的論文數量
                    const groupCounts = {}
                    rawData.nodes.forEach(n => {
                      groupCounts[n.group] = (groupCounts[n.group] || 0) + 1
                    })
                    return Object.entries(communityLabels).map(([groupId, label]) => {
                      const color = COMMUNITY_COLORS[parseInt(groupId) % COMMUNITY_COLORS.length]
                      const count = groupCounts[parseInt(groupId)] || 0
                      return (
                        <span
                          key={groupId}
                          className="legend-pill"
                          style={{ '--pill-color': color }}
                        >
                          <span className="legend-dot" style={{ backgroundColor: color }} />
                          <span className="legend-label">{label}</span>
                          {count > 0 && (
                            <span className="legend-count">{count}篇</span>
                          )}
                        </span>
                      )
                    })
                  })()}
                </div>
                {/* 第三行：其他圖例指標 */}
                <div className="legend-metrics-row">
                  <span>⚫ 節點大小 = PageRank 影響力</span>
                  <span className="legend-separator">|</span>
                  <span>━ 連線粗細 = 語意相似度</span>
                </div>
              </div>
            </div>

            {/* 右側：側邊細節面板 (Sidebar Inspector) */}
            <div className={`graph-inspector-sidebar glass-card ${selectedItem ? 'active' : ''}`}>
              {!selectedItem ? (
                <div className="sidebar-empty">
                  <div style={{ fontSize: 32, opacity: 0.6, marginBottom: 12 }}>🔍</div>
                  <h4>細節檢查員</h4>
                  <p>點選圖譜上的「節點（論文）」或「連線（關聯線）」可在此處查看詳細的學術關聯原因與摘要分析。</p>
                </div>
              ) : selectedType === 'node' ? (
                <div className="sidebar-content fade-in">
                  <div className="sidebar-category">📄 文獻摘要</div>
                  <h3 className="paper-title">{selectedItem.title}</h3>
                  <div className="paper-meta">
                    <p><b>作者：</b>{selectedItem.authors}</p>
                    <p><b>年份：</b>{selectedItem.year}</p>
                    <p><b>PageRank 影響力：</b><span className="badge badge-purple">{selectedItem.pagerank.toFixed(4)}</span></p>
                  </div>
                  
                  <hr className="divider" />
                  
                  <div className="section-block">
                    <h4>🎯 研究目的</h4>
                    <p>{selectedItem.details.research_goal}</p>
                  </div>

                  <div className="section-block">
                    <h4>💡 主要發現</h4>
                    <p>{selectedItem.details.main_findings}</p>
                  </div>

                  <div className="section-block">
                    <h4>⚠️ 研究限制</h4>
                    <p>{selectedItem.details.limitations}</p>
                  </div>
                </div>
              ) : (
                <div className="sidebar-content fade-in">
                  <div className="sidebar-category">🔗 關聯分析</div>
                  
                  <div className="similarity-gauge">
                    <div className="gauge-number">{(selectedItem.weight * 100).toFixed(1)}%</div>
                    <div className="gauge-label">餘弦語意相似度</div>
                  </div>

                  <hr className="divider" />

                  <div className="section-block">
                    <h4>🏷️ 共同核心主題</h4>
                    <div className="tag-container">
                      {selectedItem.common_terms.length > 0 ? (
                        selectedItem.common_terms.map((term, i) => (
                          <span key={i} className="badge badge-purple">{term}</span>
                        ))
                      ) : (
                        <span className="text-muted">主要為背景語意相似性連結</span>
                      )}
                    </div>
                  </div>

                  <div className="section-block" style={{ marginTop: 20 }}>
                    <h4>🔬 關聯論文對</h4>
                    <div className="edge-nodes-info">
                      <div className="node-info-box">
                        <span className="dot-indicator" style={{ backgroundColor: COMMUNITY_COLORS[selectedItem.fromNode.group % COMMUNITY_COLORS.length] }} />
                        <span className="node-title-sub" title={selectedItem.fromNode.title}>{selectedItem.fromNode.title}</span>
                      </div>
                      <div className="arrow-down">⬇️</div>
                      <div className="node-info-box">
                        <span className="dot-indicator" style={{ backgroundColor: COMMUNITY_COLORS[selectedItem.toNode.group % COMMUNITY_COLORS.length] }} />
                        <span className="node-title-sub" title={selectedItem.toNode.title}>{selectedItem.toNode.title}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="sidebar-help-alert">
                    <p>💡 <b>提示：</b>相似度是由研究目的、主要發現及關鍵詞經 TF-IDF 計算而成。若百分比高，代表兩者在研究技術或材料上有很高的重複與互補性。</p>
                  </div>
                </div>
              )}
            </div>

          </div>
        )}
      </div>
    </div>
  )
}
