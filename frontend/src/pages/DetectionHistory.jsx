import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const API = 'http://localhost:5000'

function DetectionHistory() {
  const navigate = useNavigate()
  const today = new Date().toISOString().split('T')[0]
  const [startDate, setStartDate] = useState(today)
  const [startTime, setStartTime] = useState('')
  const [endDate, setEndDate] = useState(today)
  const [endTime, setEndTime] = useState('')
  const [cams, setCams] = useState([])
  const [selectedCam, setSelectedCam] = useState('')
  const [results, setResults] = useState([])
  const [activeIds, setActiveIds] = useState(new Set())
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [selectedItem, setSelectedItem] = useState(null)

  useEffect(() => {
    fetch(`${API}/api/log_cams`).then(r => r.json()).then(d => setCams(d.cams || [])).catch(() => {})
  }, [])

  useEffect(() => {
    const fetchActive = async () => {
      try {
        const data = await fetch(`${API}/api/detections`).then(r => r.json())
        const ids = new Set(data.filter(d => d.state === 'SUSPECTED' || d.state === 'LOST').map(d => `${d.pipe_name}_${d.track_id}`))
        setActiveIds(ids)
      } catch {}
    }
    fetchActive()
    const iv = setInterval(fetchActive, 3000)
    return () => clearInterval(iv)
  }, [])

  const handleSearch = async () => {
    if (!startDate) { setMessage('시작 날짜를 입력하세요.'); return }
    const start = `${startDate} ${startTime ? startTime + ':00' : '00:00:00'}`
    const end = endDate ? `${endDate} ${endTime ? endTime + ':59' : '23:59:59'}` : ''
    setLoading(true); setMessage(''); setResults([])
    try {
      const url = `${API}/api/log_search?start=${encodeURIComponent(start)}${end ? `&end=${encodeURIComponent(end)}` : ''}${selectedCam ? `&cam=${encodeURIComponent(selectedCam)}` : ''}`
      const data = await fetch(url).then(r => r.json())
      setResults(data)
      setMessage(data.length === 0 ? '해당 시간대에 탐지된 분실물이 없습니다.' : '')
    } catch {
      setMessage('서버 연결 실패')
    }
    setLoading(false)
  }

  const isActive = (item) => activeIds.has(`${item.pipename}_${item.obj_id}`)

  const getItemStatus = (item) => {
    if (isActive(item)) return 'active'
    if (item.state === 'SUSPECTED') return 'before_confirmed'
    return 'disappeared'
  }

  const statusStyle = {
    active:          { bg: '#f0fdf4', color: '#16a34a', border: '#22c55e', label: '현재 감지 중' },
    before_confirmed:{ bg: '#fffbeb', color: '#d97706', border: '#f59e0b', label: 'Confirmed 이전 사라짐' },
    disappeared:     { bg: '#fef2f2', color: '#ef4444', border: '#ef4444', label: '사라짐' },
  }

  return (
    <div style={{ padding: '24px', overflow: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '22px', fontWeight: '600', margin: '0 0 4px' }}>Detection History</h2>
      <p style={{ color: '#6b7280', fontSize: '13px', margin: '0 0 20px' }}>분실 시간대를 지정해 탐지된 분실물을 조회합니다.</p>

      {/* 시간 범위 입력 */}
      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '16px 20px', marginBottom: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr auto', gap: '12px', alignItems: 'flex-end' }}>
          <Field label="From Date">
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={inp} />
          </Field>
          <Field label="From Time">
            <input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} style={inp} />
          </Field>
          <Field label="To Date (optional)">
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} style={inp} />
          </Field>
          <Field label="To Time (optional)">
            <input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} style={inp} />
          </Field>
          <Field label="Camera (optional)">
            <select value={selectedCam} onChange={e => setSelectedCam(e.target.value)} style={inp}>
              <option value="">All</option>
              {cams.map((c, i) => <option key={i} value={c}>{c}</option>)}
            </select>
          </Field>
          <button onClick={handleSearch} disabled={loading} style={{
            background: loading ? '#9ca3af' : '#1a1f2e', color: 'white', padding: '8px 20px',
            border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: '600', cursor: loading ? 'default' : 'pointer', height: '38px'
          }}>
            {loading ? '조회 중...' : '조회'}
          </button>
        </div>
      </div>

      {message && (
        <div style={{ padding: '10px 16px', borderRadius: '8px', background: '#f3f4f6', color: '#374151', fontSize: '14px', marginBottom: '16px' }}>
          {message}
        </div>
      )}

      {/* 결과 */}
      {results.length > 0 && (
        <div>
          <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '12px' }}>총 {results.length}건 탐지</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {results.map((item, i) => {
              const s = statusStyle[getItemStatus(item)]
              return (
                <div key={i} onClick={() => setSelectedItem(item)} style={{
                  background: 'white', border: '1px solid #e5e7eb',
                  borderLeft: `4px solid ${s.border}`,
                  borderRadius: '0 10px 10px 0', padding: '14px 20px',
                  display: 'flex', alignItems: 'center', gap: '16px', cursor: 'pointer',
                }}
                  onMouseEnter={e => e.currentTarget.style.background = '#f9fafb'}
                  onMouseLeave={e => e.currentTarget.style.background = 'white'}
                >
                  <img
                    src={`${API}/api/obj_img/${item.pipename}/${item.obj_id}?date=${item.time.split(' ')[0]}`}
                    alt="thumbnail"
                    style={{ width: '52px', height: '52px', objectFit: 'cover', borderRadius: '8px', background: '#1a1f2e', flexShrink: 0 }}
                    onError={e => { e.target.onerror = null; e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
                  />
                  <div style={{ width: '52px', height: '52px', background: '#1a1f2e', borderRadius: '8px', display: 'none', alignItems: 'center', justifyContent: 'center', fontSize: '10px', color: '#6b7280', flexShrink: 0 }}>IMG</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: '600', fontSize: '14px', marginBottom: '4px' }}>{item.class} (ID: {item.obj_id})</div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>{item.pipename} · {item.time}</div>
                  </div>
                  <span style={{ fontSize: '11px', padding: '3px 10px', borderRadius: '10px', fontWeight: '600', background: s.bg, color: s.color }}>
                    {s.label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 상세 모달 */}
      {selectedItem && (
        <div onClick={() => setSelectedItem(null)} style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'white', borderRadius: '12px', padding: '28px', width: '500px', maxHeight: '85vh', overflow: 'auto',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <img
                  src={`${API}/api/obj_img/${selectedItem.pipename}/${selectedItem.obj_id}?date=${selectedItem.time.split(' ')[0]}`}
                  alt="thumbnail"
                  style={{ width: '52px', height: '52px', objectFit: 'cover', borderRadius: '8px', background: '#1a1f2e' }}
                  onError={e => { e.target.onerror = null; e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
                />
                <div style={{ width: '52px', height: '52px', background: '#1a1f2e', borderRadius: '8px', display: 'none', alignItems: 'center', justifyContent: 'center', fontSize: '11px', color: '#6b7280' }}>IMG</div>
                <div>
                  <div style={{ fontWeight: '600', fontSize: '16px' }}>{selectedItem.class} (ID: {selectedItem.obj_id})</div>
                  <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>{selectedItem.pipename} · {selectedItem.time}</div>
                </div>
              </div>
              <button onClick={() => setSelectedItem(null)} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#6b7280' }}>✕</button>
            </div>

            {(() => {
              const status = getItemStatus(selectedItem)
              if (status === 'active') return (
                <div>
                  <div style={{ fontSize: '13px', color: '#16a34a', fontWeight: '600', marginBottom: '12px' }}>● 현재 카메라에서 감지 중</div>
                  <button onClick={() => { setSelectedItem(null); navigate('/dashboard', { state: { focusCam: selectedItem.pipename } }) }} style={{
                    width: '100%', padding: '10px', background: '#1a1f2e', color: 'white',
                    border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: '600', cursor: 'pointer',
                  }}>📹 카메라로 이동 ({selectedItem.pipename})</button>
                </div>
              )
              if (status === 'before_confirmed') return (
                <div style={{ padding: '20px', textAlign: 'center', background: '#fffbeb', borderRadius: '8px', color: '#d97706', fontSize: '13px', fontWeight: '600' }}>
                  Confirmed 이전에 사라짐
                </div>
              )
              return (
                <div>
                  <div style={{ fontSize: '13px', color: '#6b7280', fontWeight: '600', marginBottom: '12px' }}>가져간 장면</div>
                  <img
                    src={`${API}/api/scene_img/${selectedItem.pipename}/${selectedItem.obj_id}`}
                    alt="scene"
                    style={{ width: '100%', borderRadius: '8px', background: '#1a1f2e', display: 'block' }}
                    onError={e => { e.target.onerror = null; e.target.style.display = 'none'; e.target.nextSibling.style.display = 'block' }}
                  />
                  <div style={{ display: 'none', padding: '40px', textAlign: 'center', background: '#f3f4f6', borderRadius: '8px', color: '#9ca3af', fontSize: '13px' }}>
                    장면 이미지 없음
                  </div>
                </div>
              )
            })()}

            <button onClick={() => setSelectedItem(null)} style={{
              width: '100%', marginTop: '12px', padding: '10px', background: 'white', color: '#6b7280',
              border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', cursor: 'pointer',
            }}>닫기</button>
          </div>
        </div>
      )}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>{label}</div>
      {children}
    </div>
  )
}

const inp = { width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', boxSizing: 'border-box' }

export default DetectionHistory
