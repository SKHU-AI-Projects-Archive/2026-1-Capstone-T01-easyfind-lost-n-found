import { useNavigate, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'

function Layout({ children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [time, setTime] = useState(new Date())
  const [status, setStatus] = useState({
    summary: { suspected: 0, confirmed: 0, taken: 0 },
    pipelines: {}
  })

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    
    const fetchStatus = async () => {
      try {
        const res = await fetch('http://localhost:5000/api/status')
        if (res.ok) {
          const data = await res.json()
          setStatus(data)
        }
      } catch (err) {
        console.error('Failed to fetch status:', err)
      }
    }
    
    fetchStatus()
    const statusTimer = setInterval(fetchStatus, 2000)

    return () => {
      clearInterval(timer)
      clearInterval(statusTimer)
    }
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f0f2f5' }}>

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
          <span style={{ background: '#22c55e', color: 'white', fontSize: '11px', padding: '2px 8px', borderRadius: '10px' }}>● LIVE</span>
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
          }}>{status.summary.suspected + status.summary.confirmed}</span>
        </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '13px', fontWeight: '600' }}>{formatTime(time)}</div>
            <div style={{ fontSize: '10px', color: '#9ca3af' }}>{formatDate(time)}</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Sidebar */}
        <div style={{ width: '200px', background: 'white', borderRight: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column', padding: '12px 0' }}>
          {navItems.map((item, i) => (
            <div key={i} onClick={() => navigate(item.path)} style={{
              padding: '10px 20px',
              fontSize: '13px',
              color: location.pathname === item.path ? '#1a1f2e' : '#6b7280',
              fontWeight: location.pathname === item.path ? '600' : '400',
              background: location.pathname === item.path ? '#f0f2f5' : 'transparent',
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
          <div style={{ marginTop: 'auto', padding: '12px 20px', fontSize: '11px', color: '#9ca3af' }}>
            <div>Camera {connectedCams} connected</div>
            <div style={{ marginTop: '4px' }}>YOLOWorld + ByteTrack</div>
          </div>
        </div>

        {/* Page Content */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {children}
        </div>

      </div>
    </div>
  )
}

export default Layout