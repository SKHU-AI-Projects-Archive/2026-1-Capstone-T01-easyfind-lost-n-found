import { useState } from 'react'

function PreciseDection() {
  const [filterDate, setFilterDate] = useState('')
  const [filterTimeStart, setFilterTimeStart] = useState('')
  const [filterTimeEnd, setFilterTimeEnd] = useState('')
  const [filterLocation, setFilterLocation] = useState('All Locations')
  const [filterInsert, setFilterInsert] = useState('')

  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')

  const resetFilters = () => {
    setFilterDate('')
    setFilterTimeStart('')
    setFilterTimeEnd('')
    setFilterLocation('All Locations')
    setFilterInsert('')
  }

  const handleStartDetection = async () => {
    setLoading(true)
    setStatus('명령 실행 중...')
    try {
      const res = await fetch('http://localhost:5000/api/start_detection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          date: filterDate,
          timeStart: filterTimeStart,
          timeEnd: filterTimeEnd,
          location: filterLocation,
          insert: filterInsert
        })
      })
      if (res.ok) {
        setStatus('탐색이 시작되었습니다.')
      } else {
        setStatus('오류가 발생했습니다.')
      }
    } catch (err) {
      console.error(err)
      setStatus('서버 연결 실패')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '24px', overflow: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '24px', fontWeight: '600', marginBottom: '8px' }}>Precise Detection</h2>
      <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '24px' }}>고급 분석 및 정밀 탐색 프로세스를 위한 조건을 설정하고 시작합니다.</p>

      {/* Filters */}
      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '16px 20px', marginBottom: '32px' }}>
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
          <div>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>Location</div>
            <select value={filterLocation} onChange={(e) => setFilterLocation(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', color: '#1a1f2e' }}>
              {['All Locations', 'CAM-A2', 'CAM-B1', 'CAM-C4', 'CAM-D3'].map((opt, j) => <option key={j}>{opt}</option>)}
            </select>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>Insert</div>
            <input 
              type="text" 
              placeholder="한글 입력 가능" 
              value={filterInsert} 
              onChange={(e) => setFilterInsert(e.target.value)} 
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', boxSizing: 'border-box' }} 
            />
          </div>
        </div>
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '40px' }}>
        <button 
          onClick={handleStartDetection}
          disabled={loading}
          style={{
            background: '#1a1f2e',
            color: 'white',
            padding: '16px 64px',
            border: 'none',
            borderRadius: '8px',
            fontSize: '18px',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
            transition: 'transform 0.1s, background 0.2s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = '#2a2f3e'}
          onMouseLeave={e => e.currentTarget.style.background = '#1a1f2e'}
          onMouseDown={e => e.currentTarget.style.transform = 'scale(0.98)'}
          onMouseUp={e => e.currentTarget.style.transform = 'scale(1)'}
        >
          {loading ? '시작 중...' : '탐색 시작'}
        </button>

        {status && (
          <div style={{ marginTop: '20px', padding: '12px 24px', borderRadius: '8px', background: '#f3f4f6', color: '#374151', fontSize: '14px', fontWeight: '500' }}>
            {status}
          </div>
        )}
      </div>
    </div>
  )
}

export default PreciseDection