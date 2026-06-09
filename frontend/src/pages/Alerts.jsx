import { useState, useEffect } from 'react'

function Alerts() {
  const [filter, setFilter] = useState('All')
  const [alerts, setAlerts] = useState([])

  // 백엔드 API에서 실시간 알림 데이터 가져오기
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/alerts')
        const data = await response.json()
        
        // 백엔드 상태명을 프런트엔드 표시용 텍스트로 변환
        const formattedAlerts = data.map(item => ({
          id: item.id,
          track_id: item.track_id,
          type: item.type,
          cam: item.pipe_name,
          location: 'Detected Area',
          date: item.first_seen.split(' ')[0],
          time: item.last_seen.split(' ')[1],
          status: mapStateToStatus(item.state),
          raw_state: item.state
        }))
        
        setAlerts(formattedAlerts.reverse()) // 최신순
      } catch (error) {
        console.error("Failed to fetch alerts:", error)
      }
    }

    fetchAlerts()
    const interval = setInterval(fetchAlerts, 3000)
    return () => clearInterval(interval)
  }, [])

  const mapStateToStatus = (state) => {
    switch(state) {
      case 'SUSPECTED': return 'Suspected';
      case 'LOST': return 'Confirmed';
      default: return state;
    }
  }

  const filtered = filter === 'All' ? alerts : alerts.filter(a => a.status === filter)

  const dismiss = (id) => setAlerts(alerts.filter(a => a.id !== id))
  const clearAll = () => setAlerts([])

  return (
    <div style={{ padding: '24px', overflow: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '22px', fontWeight: '600', margin: '0 0 4px' }}>Alerts</h2>
      <p style={{ color: '#6b7280', fontSize: '13px', margin: '0 0 20px' }}>Manage and respond to real-time lost item alerts</p>

      {/* Filter Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          {['All', 'Suspected', 'Confirmed'].map((f) => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '6px 16px',
              borderRadius: '20px',
              border: '1px solid #e5e7eb',
              fontSize: '13px',
              cursor: 'pointer',
              background: filter === f ? '#1a1f2e' : 'white',
              color: filter === f ? 'white' : '#6b7280',
              fontWeight: filter === f ? '600' : '400',
            }}>{f}</button>
          ))}
        </div>
        <button onClick={clearAll} style={{
          padding: '6px 16px',
          borderRadius: '8px',
          border: '1px solid #e5e7eb',
          fontSize: '13px',
          cursor: 'pointer',
          background: 'white',
          color: '#ef4444',
        }}>Clear All</button>
      </div>

      {/* Alert Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px', color: '#9ca3af', fontSize: '14px' }}>
            No alerts to display
          </div>
        ) : (
          filtered.map((alert) => (
            <div key={alert.id} style={{
              background: 'white',
              border: '1px solid #e5e7eb',
              borderLeft: `4px solid ${alert.raw_state === 'LOST' ? '#ef4444' : alert.raw_state === 'SUSPECTED' ? '#f59e0b' : '#3b82f6'}`,
              borderRadius: '0 10px 10px 0',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1 }}>
                <img
                  src={`http://localhost:5000/api/obj_img/${alert.cam}/${alert.track_id}?date=${alert.date}`}
                  alt="thumbnail"
                  style={{ width: '44px', height: '44px', objectFit: 'cover', borderRadius: '8px', background: '#1a1f2e', flexShrink: 0 }}
                  onError={e => { e.target.onerror = null; e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
                />
                <div style={{ width: '44px', height: '44px', background: '#1a1f2e', borderRadius: '8px', display: 'none', alignItems: 'center', justifyContent: 'center', fontSize: '10px', color: '#6b7280', flexShrink: 0 }}>IMG</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: '600', fontSize: '14px', marginBottom: '4px' }}>{alert.type} (ID:{alert.id})</div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>{alert.cam} · {alert.location} · {alert.time}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{
                  fontSize: '11px',
                  padding: '3px 10px',
                  borderRadius: '10px',
                  fontWeight: '600',
                  background: alert.raw_state === 'LOST' ? '#fef2f2' : alert.raw_state === 'SUSPECTED' ? '#fffbeb' : '#eff6ff',
                  color: alert.raw_state === 'LOST' ? '#ef4444' : alert.raw_state === 'SUSPECTED' ? '#f59e0b' : '#3b82f6',
                }}>{alert.status}</span>
                <button onClick={() => dismiss(alert.id)} style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid #e5e7eb',
                  fontSize: '12px',
                  cursor: 'pointer',
                  background: 'white',
                  color: '#6b7280',
                }}>Dismiss</button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default Alerts