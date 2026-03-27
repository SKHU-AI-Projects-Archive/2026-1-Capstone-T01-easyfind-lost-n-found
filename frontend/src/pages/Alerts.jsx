import { useState } from 'react'

function Alerts() {
  const [filter, setFilter] = useState('All')
  const [alerts, setAlerts] = useState([
    { id: 1, type: 'Backpack', cam: 'CAM-A2', location: 'Terminal A Gate 12', time: '15:42', status: 'Suspected' },
    { id: 2, type: 'Luggage', cam: 'CAM-B1', location: 'Food Court', time: '15:40', status: 'Confirmed' },
    { id: 3, type: 'Handbag', cam: 'CAM-C4', location: 'East Entrance', time: '15:35', status: 'Suspected' },
    { id: 4, type: 'Coat', cam: 'CAM-D3', location: 'West Wing', time: '15:30', status: 'Confirmed' },
    { id: 5, type: 'Backpack', cam: 'CAM-A2', location: 'Terminal A Gate 12', time: '15:20', status: 'Suspected' },
  ])

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
              borderLeft: `4px solid ${alert.status === 'Confirmed' ? '#ef4444' : '#f59e0b'}`,
              borderRadius: '0 10px 10px 0',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1 }}>
                <div style={{ width: '44px', height: '44px', background: '#1a1f2e', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', color: '#6b7280', flexShrink: 0 }}>IMG</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: '600', fontSize: '14px', marginBottom: '4px' }}>{alert.type}</div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>{alert.cam} · {alert.location} · {alert.time}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{
                  fontSize: '11px',
                  padding: '3px 10px',
                  borderRadius: '10px',
                  fontWeight: '600',
                  background: alert.status === 'Confirmed' ? '#fef2f2' : '#fffbeb',
                  color: alert.status === 'Confirmed' ? '#ef4444' : '#f59e0b',
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