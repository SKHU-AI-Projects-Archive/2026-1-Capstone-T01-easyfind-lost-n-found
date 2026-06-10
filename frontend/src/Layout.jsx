import { useNavigate, useLocation } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
const apiPort = import.meta.env.VITE_API_PORT

function Layout({ children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [time, setTime] = useState(new Date())
  const [isDark, setIsDark] = useState(() => localStorage.getItem('theme') === 'dark')
  const [isConnected, setIsConnected] = useState(false)
  const [status, setStatus] = useState({
    summary: { suspected: 0, confirmed: 0 },
    pipelines: {}
  })
  const [toasts, setToasts] = useState([])
  const knownAlertKeys = useRef(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
    localStorage.setItem('theme', isDark ? 'dark' : 'light')
  }, [isDark])

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)

    const fetchStatus = async () => {
      try {
        const res = await fetch(`${apiBaseUrl}:${apiPort}/api/status`)
        if (res.ok) {
          const data = await res.json()
          setStatus(data)
          setIsConnected(true)
        } else {
          setIsConnected(false)
        }
      } catch (err) {
        setIsConnected(false)
      }
    }

    fetchStatus()
    const statusTimer = setInterval(fetchStatus, 2000)

    return () => {
      clearInterval(timer)
      clearInterval(statusTimer)
    }
  }, [])

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await fetch(`${apiBaseUrl}:${apiPort}/api/alerts`)
        if (!res.ok) return
        const data = await res.json()

        if (knownAlertKeys.current === null) {
          // 초기화 — 페이지 로드 시 기존 알림은 토스트 안 띄움
          knownAlertKeys.current = new Set(data.map(a => `${a.pipe_name}_${a.track_id}_${a.state}`))
          return
        }

        for (const alert of data) {
          const key = `${alert.pipe_name}_${alert.track_id}_${alert.state}`
          if (!knownAlertKeys.current.has(key)) {
            knownAlertKeys.current.add(key)
            if (localStorage.getItem('adminAlerts') === 'false') continue
            const id = Date.now() + Math.random()
            const label = alert.state === 'LOST' ? 'Confirmed Lost' : 'Suspected Lost'
            const msg = `${alert.type} — ${label} (${alert.pipe_name})`
            setToasts(t => [...t, { id, msg, state: alert.state }])
            setTimeout(() => setToasts(t => t.filter(toast => toast.id !== id)), 4000)
          }
        }
      } catch {}
    }

    fetchAlerts()
    const alertTimer = setInterval(fetchAlerts, 3000)
    return () => clearInterval(alertTimer)
  }, [])

  const formatTime = (date) => date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  const formatDate = (date) => date.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })

  const navItems = [
    { label: 'Monitoring', path: '/dashboard', icon: '🖥️' },
    { label: 'Detection History', path: '/detection-history', icon: '🕐' },
    { label: 'Alerts', path: '/alerts', icon: '🔔' },
    { label: 'Precise Detection', path: '/precise-detection', icon: '🔍' },
    { label: 'Settings', path: '/settings', icon: '⚙️' },
  ]

  const connectedCams = Object.keys(status.pipelines).length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-page)' }}>

      {/* Top Bar */}
      <div style={{
        background: '#1a1f2e',
        color: 'white',
        padding: '0 24px',
        height: '48px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontWeight: '600', fontSize: '15px' }}>Lost Item Detection System</span>
          <span style={{ background: isConnected ? '#22c55e' : '#ef4444', color: 'white', fontSize: '11px', padding: '2px 8px', borderRadius: '10px' }}>
            {isConnected ? '● LIVE' : '● OFFLINE'}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{ background: '#f59e0b', color: '#1a1f2e', fontSize: '11px', padding: '2px 8px', borderRadius: '10px', fontWeight: '600' }}>Suspected {status.summary.suspected}</span>
          <span style={{ background: '#ef4444', color: 'white', fontSize: '11px', padding: '2px 8px', borderRadius: '10px', fontWeight: '600' }}>Confirmed {status.summary.confirmed}</span>
          <div style={{ cursor: 'pointer', position: 'relative' }} onClick={() => navigate('/alerts')}>
            <span style={{ fontSize: '18px' }}>🔔</span>
            <span style={{
              position: 'absolute',
              top: '-6px',
              right: '-8px',
              background: '#ef4444',
              color: 'white',
              fontSize: '10px',
              fontWeight: '600',
              width: '16px',
              height: '16px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>{(status.summary.suspected || 0) + (status.summary.confirmed || 0)}</span>
          </div>
<div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '13px', fontWeight: '600' }}>{formatTime(time)}</div>
            <div style={{ fontSize: '10px', color: '#9ca3af' }}>{formatDate(time)}</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Sidebar */}
        <div style={{ width: '200px', background: 'var(--bg-sidebar)', borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', padding: '12px 0' }}>
          {navItems.map((item, i) => (
            <div key={i} onClick={() => navigate(item.path)} style={{
              padding: '10px 20px',
              fontSize: '13px',
              color: location.pathname === item.path ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontWeight: location.pathname === item.path ? '600' : '400',
              background: location.pathname === item.path ? 'var(--bg-page)' : 'transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              borderLeft: location.pathname === item.path ? '3px solid #1a1f2e' : '3px solid transparent',
            }}>
              <span style={{ fontSize: '16px' }}>{item.icon}</span>
              {item.label}
            </div>
          ))}
          <div style={{ marginTop: 'auto', padding: '12px 20px', fontSize: '11px', color: 'var(--text-muted)' }}>
            <div>Camera {connectedCams} connected</div>
          </div>
        </div>

        {/* Page Content */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {children}
        </div>

      </div>

      {/* Toast 알림 */}
      <div style={{
        position: 'fixed', bottom: '24px', right: '24px',
        display: 'flex', flexDirection: 'column', gap: '8px', zIndex: 2000,
      }}>
        {toasts.map(toast => (
          <div key={toast.id} style={{
            background: toast.state === 'LOST' ? '#ef4444' : '#f59e0b',
            color: 'white',
            padding: '14px 20px',
            borderRadius: '12px',
            boxShadow: '0 6px 20px rgba(0,0,0,0.25)',
            minWidth: '280px',
            animation: 'slideIn 0.3s ease',
            borderLeft: `5px solid ${toast.state === 'LOST' ? '#b91c1c' : '#d97706'}`,
          }}>
            <div style={{ fontSize: '12px', fontWeight: '700', opacity: 0.9, marginBottom: '4px' }}>
              {toast.state === 'LOST' ? '🔴 Confirmed Lost' : '🟡 Suspected Lost'}
            </div>
            <div style={{ fontSize: '16px', fontWeight: '800' }}>
              {toast.msg.split(' — ')[0]}
            </div>
            <div style={{ fontSize: '12px', fontWeight: '600', opacity: 0.85, marginTop: '3px' }}>
              {toast.msg.split(' — ')[1].replace(/.*\((.+)\)/, '$1')}
            </div>
          </div>
        ))}
      </div>

    </div>
  )
}

export default Layout
