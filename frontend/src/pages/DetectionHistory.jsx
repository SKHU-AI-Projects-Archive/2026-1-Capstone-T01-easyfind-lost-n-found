import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function DetectionHistory() {
  const navigate = useNavigate()
  const [filterDate, setFilterDate] = useState('')
  const [filterTimeStart, setFilterTimeStart] = useState('')
  const [filterTimeEnd, setFilterTimeEnd] = useState('')
  const [filterType, setFilterType] = useState('All Types')
  const [filterStatus, setFilterStatus] = useState('All Status')
  const [filterCam, setFilterCam] = useState('All Cameras')
  const [selectedItem, setSelectedItem] = useState(null)
  const [videoModal, setVideoModal] = useState(null)
  const [videoZoom, setVideoZoom] = useState(1)
  
  const [allData, setAllData] = useState([])

  // 백엔드 API에서 실시간 데이터 가져오기
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/detections')
        const data = await response.json()
        
        // 백엔드 데이터 형식을 프런트엔드 테이블 형식으로 변환
        const formattedData = data.map(item => ({
          id: item.id,
          track_id: item.track_id,
          type: item.type,
          cam: item.pipe_name,
          location: 'Detected Area', // 추후 백엔드에서 위치 정보를 줄 수도 있음
          date: item.first_seen.split(' ')[0],
          time: item.first_seen.split(' ')[1],
          duration: calculateDuration(item.first_seen, item.last_seen),
          status: item.state === 'SUSPECTED' ? 'Suspected' : item.state === 'LOST' ? 'Confirmed' : item.state,
          raw_state: item.state
        }))
        
        setAllData(formattedData.reverse()) // 최신순 정렬
      } catch (error) {
        console.error("Failed to fetch detections:", error)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 3000) // 3초마다 갱신
    return () => clearInterval(interval)
  }, [])

  const calculateDuration = (start, end) => {
    const s = new Date(start)
    const e = new Date(end)
    const diff = Math.floor((e - s) / 1000 / 60) // 분 단위
    return `${diff} min`
  }

  const filtered = allData.filter(row => {
    if (filterDate && row.date !== filterDate) return false
    if (filterTimeStart && row.time < filterTimeStart) return false
    if (filterTimeEnd && row.time > filterTimeEnd) return false
    if (filterType !== 'All Types' && row.type !== filterType) return false
    if (filterStatus !== 'All Status' && row.status !== filterStatus) return false
    if (filterCam !== 'All Cameras' && row.cam !== filterCam) return false
    return true
  })

  // ... (rest of the component logic remains same)

  const resetFilters = () => {
    setFilterDate('')
    setFilterTimeStart('')
    setFilterTimeEnd('')
    setFilterType('All Types')
    setFilterStatus('All Status')
    setFilterCam('All Cameras')
  }

  const getStatusStyle = (status) => {
    if (status === 'Confirmed' || status === 'LOST') return { background: '#fef2f2', color: '#ef4444' }
    if (status === 'Taken') return { background: '#eff6ff', color: '#3b82f6' }
    return { background: '#fffbeb', color: '#f59e0b' }
  }

  const getTimeline = (status) => [
    { label: 'Detected', desc: 'Object detected in camera view', color: '#9ca3af', done: true },
    { label: 'Suspected', desc: 'Item stationary for threshold time', color: '#f59e0b', done: status === 'Suspected' || status === 'Confirmed' || status === 'Taken' },
    { label: 'Confirmed', desc: 'Confirmed as lost item', color: '#ef4444', done: status === 'Confirmed' || status === 'Taken' },
    { label: 'Taken', desc: 'Item taken by unknown person', color: '#3b82f6', done: status === 'Taken' },
  ]

  const VideoPlayer = ({ label, onExpand, zoom, onZoomIn, onZoomOut, onZoomReset }) => (
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: '12px', fontWeight: '600', color: '#6b7280', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div
        onClick={onExpand}
        style={{ background: '#111827', borderRadius: '8px', height: '160px', overflow: 'hidden', border: '1px solid #374151', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ transform: `scale(${zoom})`, transition: 'transform 0.2s', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
          <div style={{ fontSize: '24px' }}>🎬</div>
          <span style={{ color: '#4b5563', fontSize: '12px' }}>영상 준비 중</span>
          <span style={{ color: '#374151', fontSize: '11px' }}>클릭하면 크게 볼 수 있어요</span>
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={{ background: '#374151', color: 'white', border: 'none', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer' }}>⏮</button>
          <button style={{ background: '#374151', color: 'white', border: 'none', borderRadius: '6px', padding: '4px 14px', fontSize: '12px', cursor: 'pointer' }}>▶</button>
          <button style={{ background: '#374151', color: 'white', border: 'none', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer' }}>⏭</button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: '#9ca3af', fontSize: '11px' }}>{Math.round(zoom * 100)}%</span>
          <button onClick={onZoomOut} style={{ background: '#374151', color: 'white', border: 'none', borderRadius: '4px', width: '24px', height: '24px', fontSize: '14px', cursor: 'pointer' }}>−</button>
          <button onClick={onZoomIn} style={{ background: '#374151', color: 'white', border: 'none', borderRadius: '4px', width: '24px', height: '24px', fontSize: '14px', cursor: 'pointer' }}>+</button>
          <button onClick={onZoomReset} style={{ background: '#374151', color: '#9ca3af', border: 'none', borderRadius: '4px', padding: '0 6px', height: '24px', fontSize: '11px', cursor: 'pointer' }}>Reset</button>
        </div>
      </div>
    </div>
  )

  const [beforeZoom, setBeforeZoom] = useState(1)
  const [afterZoom, setAfterZoom] = useState(1)

  return (
    <div style={{ padding: '24px', overflow: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '22px', fontWeight: '600', margin: '0 0 4px' }}>Detection History</h2>
      <p style={{ color: '#6b7280', fontSize: '13px', margin: '0 0 20px' }}>View and filter all detected lost items</p>

      {/* Filters */}
      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '16px 20px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <span style={{ fontSize: '13px', fontWeight: '600' }}>🔍 Filters</span>
          <button onClick={resetFilters} style={{ fontSize: '12px', color: '#6b7280', background: 'none', border: '1px solid #e5e7eb', borderRadius: '6px', padding: '4px 10px', cursor: 'pointer' }}>Reset</button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '12px' }}>
          <div>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>Date</div>
            <input type="date" value={filterDate} onChange={(e) => setFilterDate(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', boxSizing: 'border-box' }} />
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>Time From</div>
            <input type="time" value={filterTimeStart} onChange={(e) => setFilterTimeStart(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', boxSizing: 'border-box' }} />
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>Time To</div>
            <input type="time" value={filterTimeEnd} onChange={(e) => setFilterTimeEnd(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', boxSizing: 'border-box' }} />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          {[
            { label: 'Camera', value: filterCam, setter: setFilterCam, options: ['All Cameras', ...new Set(allData.map(d => d.cam))] },
            { label: 'Object Type', value: filterType, setter: setFilterType, options: ['All Types', ...new Set(allData.map(d => d.type))] },
            { label: 'Status', value: filterStatus, setter: setFilterStatus, options: ['All Status', 'Suspected', 'Confirmed', 'Taken'] },
          ].map((filter, i) => (
            <div key={i}>
              <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>{filter.label}</div>
              <select value={filter.value} onChange={(e) => filter.setter(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', color: '#1a1f2e' }}>
                {filter.options.map((opt, j) => <option key={j}>{opt}</option>)}
              </select>
            </div>
          ))}
        </div>
      </div>

      {/* Table */}
      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', overflow: 'hidden' }}>
        <div style={{ padding: '12px 20px', fontSize: '13px', color: '#6b7280', borderBottom: '1px solid #e5e7eb' }}>
          Showing {filtered.length} results
        </div>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px', color: '#9ca3af', fontSize: '14px' }}>No results found</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9fafb' }}>
                {['Thumbnail', 'Object Type', 'Camera', 'ID', 'Date', 'Time', 'Duration', 'Status'].map((col, i) => (
                  <th key={i} style={{ padding: '10px 16px', fontSize: '11px', fontWeight: '600', color: '#6b7280', textAlign: 'left', letterSpacing: '0.05em', textTransform: 'uppercase' }}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.id}
                  onClick={() => { setSelectedItem(row); setBeforeZoom(1); setAfterZoom(1) }}
                  style={{ borderTop: '1px solid #f3f4f6', cursor: 'pointer' }}
                  onMouseEnter={e => e.currentTarget.style.background = '#f9fafb'}
                  onMouseLeave={e => e.currentTarget.style.background = 'white'}
                >
                  <td style={{ padding: '12px 16px' }}>
                    <img
                      src={`http://localhost:5000/api/obj_img/${row.cam}/${row.track_id}?date=${row.date}`}
                      alt="thumbnail"
                      style={{ width: '44px', height: '44px', objectFit: 'cover', borderRadius: '6px', background: '#1a1f2e', display: 'block' }}
                      onError={e => { e.target.onerror = null; e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
                    />
                    <div style={{ width: '44px', height: '44px', background: '#1a1f2e', borderRadius: '6px', display: 'none', alignItems: 'center', justifyContent: 'center', fontSize: '10px', color: '#6b7280' }}>IMG</div>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px', fontWeight: '500' }}>{row.type}</td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>{row.cam}</td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>{row.track_id}</td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>{row.date}</td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>{row.time}</td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>{row.duration}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ fontSize: '11px', padding: '3px 10px', borderRadius: '10px', fontWeight: '600', ...getStatusStyle(row.status) }}>{row.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 상세 모달 */}
      {selectedItem && (
        <div onClick={() => setSelectedItem(null)} style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'white', borderRadius: '12px', padding: '28px',
            width: selectedItem.status === 'Taken' ? '720px' : '500px',
            maxHeight: '85vh', overflow: 'auto',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <img
                  src={`http://localhost:5000/api/obj_img/${selectedItem.cam}/${selectedItem.track_id}?date=${selectedItem.date}`}
                  alt="thumbnail"
                  style={{ width: '48px', height: '48px', objectFit: 'cover', borderRadius: '8px', background: '#1a1f2e', display: 'block' }}
                  onError={e => { e.target.onerror = null; e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
                />
                <div style={{ width: '48px', height: '48px', background: '#1a1f2e', borderRadius: '8px', display: 'none', alignItems: 'center', justifyContent: 'center', fontSize: '11px', color: '#6b7280' }}>IMG</div>
                <div>
                  <div style={{ fontWeight: '600', fontSize: '16px' }}>{selectedItem.type} (ID:{selectedItem.track_id})</div>
                  <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '8px', fontWeight: '600', ...getStatusStyle(selectedItem.status) }}>{selectedItem.status}</span>
                </div>
              </div>
              <button onClick={() => setSelectedItem(null)} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#6b7280' }}>✕</button>
            </div>

            <div style={{ background: '#f9fafb', borderRadius: '8px', padding: '16px', marginBottom: '20px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                {[
                  { label: '📷 Camera', value: selectedItem.cam },
                  { label: '📍 Location', value: selectedItem.location },
                  { label: '📅 Date', value: selectedItem.date },
                  { label: '🕐 Time', value: selectedItem.time },
                  { label: '⏱ Duration', value: selectedItem.duration },
                ].map((info, i) => (
                  <div key={i}>
                    <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '2px' }}>{info.label}</div>
                    <div style={{ fontSize: '13px', fontWeight: '500' }}>{info.value}</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: '#6b7280', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Detection Timeline</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {getTimeline(selectedItem.status).map((step, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: step.done ? step.color : '#e5e7eb', flexShrink: 0 }}></div>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: '500', color: step.done ? '#1a1f2e' : '#9ca3af' }}>{step.label}</div>
                      <div style={{ fontSize: '11px', color: '#9ca3af' }}>{step.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Taken 일 때 Before/After */}
            {selectedItem.status === 'Taken' && (
              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', fontWeight: '600', color: '#6b7280', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>🎬 Before / After Footage</div>
                <div style={{ background: '#fff3cd', border: '1px solid #ffc107', borderRadius: '8px', padding: '8px 12px', marginBottom: '12px', fontSize: '12px', color: '#856404' }}>
                  ⚠️ 누군가 이 물건을 가져간 것이 감지되었습니다.
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <VideoPlayer
                    label="Before — 가져가기 전"
                    zoom={beforeZoom}
                    onExpand={() => { setVideoModal('before'); setVideoZoom(1) }}
                    onZoomIn={() => setBeforeZoom(z => Math.min(3, parseFloat((z + 0.25).toFixed(2))))}
                    onZoomOut={() => setBeforeZoom(z => Math.max(1, parseFloat((z - 0.25).toFixed(2))))}
                    onZoomReset={() => setBeforeZoom(1)}
                  />
                  <VideoPlayer
                    label="After — 가져간 후"
                    zoom={afterZoom}
                    onExpand={() => { setVideoModal('after'); setVideoZoom(1) }}
                    onZoomIn={() => setAfterZoom(z => Math.min(3, parseFloat((z + 0.25).toFixed(2))))}
                    onZoomOut={() => setAfterZoom(z => Math.max(1, parseFloat((z - 0.25).toFixed(2))))}
                    onZoomReset={() => setAfterZoom(1)}
                  />
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={() => {
                setSelectedItem(null)
                navigate('/', { state: { focusCam: selectedItem.cam } })
              }} style={{
                flex: 1, padding: '10px', background: '#1a1f2e', color: 'white', border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: '600', cursor: 'pointer',
              }}>📹 Go to Camera</button>
              <button onClick={() => setSelectedItem(null)} style={{
                flex: 1, padding: '10px', background: 'white', color: '#6b7280', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', cursor: 'pointer',
              }}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* 영상 크게보기 모달 */}
      {videoModal && (
        <div onClick={() => setVideoModal(null)} style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000,
        }}>
          <div onClick={e => e.stopPropagation()} style={{ background: '#111827', borderRadius: '12px', padding: '20px', width: '800px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ color: 'white', fontWeight: '600', fontSize: '15px' }}>
                {videoModal === 'before' ? '🎬 Before — 가져가기 전' : '🎬 After — 가져간 후'}
              </span>
              <button onClick={() => setVideoModal(null)} style={{ background: 'none', border: 'none', color: '#9ca3af', fontSize: '20px', cursor: 'pointer' }}>✕</button>
            </div>
            <div style={{ background: '#1f2937', borderRadius: '8px', height: '420px', overflow: 'hidden', marginBottom: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ transform: `scale(${videoZoom})`, transition: 'transform 0.2s', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                <div style={{ fontSize: '32px' }}>🎬</div>
                <span style={{ color: '#4b5563', fontSize: '14px' }}>영상 준비 중</span>
                <span style={{ color: '#374151', fontSize: '12px' }}>백엔드 연결 후 재생 가능</span>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button style={{ background: '#374151', color: 'white', border: 'none', borderRadius: '6px', padding: '6px 14px', fontSize: '14px', cursor: 'pointer' }}>⏮</button>
                <button style={{ background: '#374151', color: 'white', border: 'none', borderRadius: '6px', padding: '6px 18px', fontSize: '14px', cursor: 'pointer' }}>▶</button>
                <button style={{ background: '#374151', color: 'white', border: 'none', borderRadius: '6px', padding: '6px 14px', fontSize: '14px', cursor: 'pointer' }}>⏭</button>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#9ca3af', fontSize: '12px' }}>Zoom: {Math.round(videoZoom * 100)}%</span>
                <button onClick={() => setVideoZoom(z => Math.max(1, parseFloat((z - 0.25).toFixed(2))))} style={{ background: '#374151', color: 'white', border: 'none', borderRadius: '6px', width: '32px', height: '32px', fontSize: '18px', cursor: 'pointer' }}>−</button>
                <button onClick={() => setVideoZoom(z => Math.min(3, parseFloat((z + 0.25).toFixed(2))))} style={{ background: '#374151', color: 'white', border: 'none', borderRadius: '6px', width: '32px', height: '32px', fontSize: '18px', cursor: 'pointer' }}>+</button>
                <button onClick={() => setVideoZoom(1)} style={{ background: '#374151', color: '#9ca3af', border: 'none', borderRadius: '6px', padding: '0 10px', height: '32px', fontSize: '12px', cursor: 'pointer' }}>Reset</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DetectionHistory