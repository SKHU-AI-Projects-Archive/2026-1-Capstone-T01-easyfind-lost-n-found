import { useState, useEffect, useRef } from 'react'

const API = 'http://localhost:5000'

function PreciseDection() {
  const [cams, setCams] = useState([])
  const [filterDate, setFilterDate] = useState('')
  const [filterTimeStart, setFilterTimeStart] = useState('')
  const [filterTimeEnd, setFilterTimeEnd] = useState('')
  const [filterCam, setFilterCam] = useState('')
  const [filterPrompt, setFilterPrompt] = useState('')
  const [interval, setIntervalSec] = useState(5)

  const [jobId, setJobId] = useState('')
  const [running, setRunning] = useState(false)
  const [paused, setPaused] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('')
  const [groups, setGroups] = useState([])
  const [hitCount, setHitCount] = useState(0)
  const [message, setMessage] = useState('')

  const jobRef = useRef('')
  const runRef = useRef(false)
  useEffect(() => { jobRef.current = jobId }, [jobId])
  useEffect(() => { runRef.current = running }, [running])

  // 검색 가능한 카메라(아카이브 보유) 목록
  useEffect(() => {
    fetch(`${API}/api/archive_cams`)
      .then(r => r.json())
      .then(d => {
        setCams(d.cams || [])
        if (d.cams && d.cams.length && !filterCam) setFilterCam(d.cams[0])
      })
      .catch(() => {})
  }, [])

  // 진행 중 잡 폴링
  useEffect(() => {
    if (!jobId) return
    const iv = setInterval(async () => {
      try {
        const s = await fetch(`${API}/api/search/${jobId}`).then(r => r.json())
        setStatus(s.status)
        setProgress(s.progress || 0)
        setGroups(s.groups || [])
        setHitCount((s.hits || []).length)
        if (s.done) {
          clearInterval(iv)
          setRunning(false)
          setMessage(`완료: ${(s.groups || []).length}개 구간에서 발견 (총 ${(s.hits || []).length}장)`)
        }
      } catch { /* ignore */ }
    }, 1000)
    return () => clearInterval(iv)
  }, [jobId])

  // 페이지 이탈(unmount) 시 진행 중 검색 자동 중지
  useEffect(() => {
    return () => {
      if (jobRef.current && runRef.current) {
        fetch(`${API}/api/search/${jobRef.current}/stop`, { method: 'POST' }).catch(() => {})
      }
    }
  }, [])

  const toEpoch = (date, t, fallback) => {
    const dt = new Date(`${date}T${t || fallback}`)
    return Math.floor(dt.getTime() / 1000)
  }

  const fmt = (ts) => new Date(ts * 1000).toLocaleString()

  const handleSearch = async () => {
    if (!filterCam) { setMessage('카메라를 선택하세요.'); return }
    if (!filterDate) { setMessage('날짜를 선택하세요.'); return }
    if (!filterPrompt.trim()) { setMessage('찾을 물건을 입력하세요.'); return }

    const start_ts = toEpoch(filterDate, filterTimeStart, '00:00')
    const end_ts = toEpoch(filterDate, filterTimeEnd, '23:59')
    setGroups([]); setProgress(0); setHitCount(0); setMessage('검색을 시작합니다...')
    try {
      const r = await fetch(`${API}/api/search`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cam: filterCam, start_ts, end_ts, prompt: filterPrompt, interval_sec: Number(interval) })
      }).then(res => res.json())
      if (r.job_id) {
        setJobId(r.job_id); setRunning(true); setPaused(false)
        setMessage(`검색 중... (해석된 프롬프트: "${r.prompt}")`)
      } else {
        setMessage(`오류: ${r.message || '시작 실패'}`)
      }
    } catch (e) {
      setMessage('서버 연결 실패')
    }
  }

  const control = async (action) => {
    if (!jobId) return
    await fetch(`${API}/api/search/${jobId}/${action}`, { method: 'POST' }).catch(() => {})
    if (action === 'stop') { setRunning(false); setMessage('검색을 중지했습니다.') }
    if (action === 'pause') { setPaused(true) }
    if (action === 'resume') { setPaused(false) }
  }

  return (
    <div style={{ padding: '24px', overflow: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '24px', fontWeight: '600', marginBottom: '8px' }}>Precise Detection</h2>
      <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '24px' }}>
        과거 영상에서 분실물을 소급 검색합니다. CCTV · 시간 · 찾을 물건을 입력하세요. (한글/영어 모두 가능)
      </p>

      {/* 필터 */}
      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '16px 20px', marginBottom: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '12px' }}>
          <Field label="Date">
            <input type="date" value={filterDate} onChange={e => setFilterDate(e.target.value)} style={inp} />
          </Field>
          <Field label="Time From">
            <input type="time" value={filterTimeStart} onChange={e => setFilterTimeStart(e.target.value)} style={inp} />
          </Field>
          <Field label="Time To">
            <input type="time" value={filterTimeEnd} onChange={e => setFilterTimeEnd(e.target.value)} style={inp} />
          </Field>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          <Field label="Camera">
            <select value={filterCam} onChange={e => setFilterCam(e.target.value)} style={inp}>
              {cams.length === 0 && <option value="">(아카이브 없음)</option>}
              {cams.map((c, i) => <option key={i} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Object (찾을 물건)">
            <input type="text" placeholder="예: 검은 가방 / red backpack" value={filterPrompt}
              onChange={e => setFilterPrompt(e.target.value)} style={inp} />
          </Field>
          <Field label="Interval (sec)">
            <input type="number" min="0" value={interval} onChange={e => setIntervalSec(e.target.value)} style={inp} />
          </Field>
        </div>
      </div>

      {/* 컨트롤 */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <button onClick={handleSearch} disabled={running} style={btn(running ? '#9ca3af' : '#1a1f2e')}>
          {running ? '검색 중...' : '탐색 시작'}
        </button>
        {running && !paused && <button onClick={() => control('pause')} style={btn('#f59e0b')}>일시정지</button>}
        {running && paused && <button onClick={() => control('resume')} style={btn('#22c55e')}>재개</button>}
        {running && <button onClick={() => control('stop')} style={btn('#ef4444')}>중지</button>}
      </div>

      {/* 진행률 */}
      {(running || progress > 0) && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ height: '8px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${Math.round(progress * 100)}%`, height: '100%', background: '#3b82f6', transition: 'width 0.3s' }} />
          </div>
          <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
            {Math.round(progress * 100)}% · status: {status} · 발견 {hitCount}장
          </div>
        </div>
      )}

      {message && (
        <div style={{ padding: '10px 16px', borderRadius: '8px', background: '#f3f4f6', color: '#374151', fontSize: '14px', marginBottom: '16px' }}>
          {message}
        </div>
      )}

      {/* 타임라인 결과 */}
      {groups.length > 0 && (
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
            발견 구간 ({groups.length})
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '16px' }}>
            {groups.map((g, i) => (
              <div key={i} style={{ border: '1px solid #e5e7eb', borderRadius: '10px', overflow: 'hidden', background: 'white' }}>
                <img src={`${API}/search_thumb/${g.peak_thumb}`} alt="hit"
                  style={{ width: '100%', height: '160px', objectFit: 'cover', display: 'block', background: '#000' }} />
                <div style={{ padding: '12px' }}>
                  <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '4px' }}>
                    {fmt(g.start_ts)}
                  </div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>
                    ~ {fmt(g.end_ts)}
                  </div>
                  <div style={{ fontSize: '12px', color: '#374151', marginTop: '6px' }}>
                    {g.count}장 · 신뢰도 {(g.peak_conf * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const inp = { width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', boxSizing: 'border-box' }

function Field({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>{label}</div>
      {children}
    </div>
  )
}

function btn(bg) {
  return {
    background: bg, color: 'white', padding: '12px 24px', border: 'none',
    borderRadius: '8px', fontSize: '15px', fontWeight: '600', cursor: 'pointer',
  }
}

export default PreciseDection
