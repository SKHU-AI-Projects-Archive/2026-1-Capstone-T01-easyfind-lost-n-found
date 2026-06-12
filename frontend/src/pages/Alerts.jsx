import { useState, useEffect } from 'react'
import { useLanguage } from '../LanguageContext'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
const apiPort = import.meta.env.VITE_API_PORT

function Alerts() {
  const { t } = useLanguage()
  const [filter, setFilter] = useState('all')
  const [alerts, setAlerts] = useState([])

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}:${apiPort}/api/alerts`)
        const data = await response.json()

        const formattedAlerts = data.map(item => ({
          id: item.id,
          track_id: item.track_id,
          type: item.type,
          cam: item.pipe_name,
          location: t('detectedArea'),
          date: item.first_seen.split(' ')[0],
          time: item.last_seen.split(' ')[1],
          status: mapStateToStatus(item.state),
          raw_state: item.state
        }))

        setAlerts(formattedAlerts.reverse())
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

  const filtered = filter === 'all' ? alerts : alerts.filter(a => a.status === filter)

  const filterOptions = [
    { key: 'all', label: t('all') },
    { key: 'Suspected', label: t('suspected') },
    { key: 'Confirmed', label: t('confirmed') },
  ]

  return (
    <div style={{ padding: '24px', overflow: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '22px', fontWeight: '600', margin: '0 0 4px' }}>{t('alerts')}</h2>
      <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: '0 0 20px' }}>{t('alertsDesc')}</p>

      {/* Filter Bar */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {filterOptions.map(({ key, label }) => (
          <button key={key} onClick={() => setFilter(key)} style={{
            padding: '6px 16px',
            borderRadius: '20px',
            border: '1px solid var(--border-color)',
            fontSize: '13px',
            cursor: 'pointer',
            background: filter === key ? '#1a1f2e' : 'var(--bg-card)',
            color: filter === key ? 'white' : 'var(--text-secondary)',
            fontWeight: filter === key ? '600' : '400',
          }}>{label}</button>
        ))}
      </div>

      {/* Alert Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)', fontSize: '14px' }}>
            {t('noAlerts')}
          </div>
        ) : (
          filtered.map((alert) => (
            <div key={alert.id} style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderLeft: `4px solid ${alert.raw_state === 'LOST' ? '#ef4444' : '#f59e0b'}`,
              borderRadius: '0 10px 10px 0',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
            }}>
              <img
                src={`${apiBaseUrl}:${apiPort}/api/obj_img/${alert.cam}/${alert.track_id}?date=${alert.date}`}
                alt="thumbnail"
                style={{ width: '44px', height: '44px', objectFit: 'cover', borderRadius: '8px', background: '#1a1f2e', flexShrink: 0 }}
                onError={e => { e.target.onerror = null; e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
              />
              <div style={{ width: '44px', height: '44px', background: '#1a1f2e', borderRadius: '8px', display: 'none', alignItems: 'center', justifyContent: 'center', fontSize: '10px', color: '#6b7280', flexShrink: 0 }}>IMG</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: '600', fontSize: '14px', marginBottom: '4px' }}>{alert.type} (ID:{alert.id})</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{alert.cam} · {alert.location} · {alert.time}</div>
              </div>
              <span style={{
                fontSize: '11px',
                padding: '3px 10px',
                borderRadius: '10px',
                fontWeight: '600',
                background: alert.raw_state === 'LOST' ? '#fef2f2' : '#fffbeb',
                color: alert.raw_state === 'LOST' ? '#ef4444' : '#f59e0b',
              }}>{alert.status}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default Alerts
