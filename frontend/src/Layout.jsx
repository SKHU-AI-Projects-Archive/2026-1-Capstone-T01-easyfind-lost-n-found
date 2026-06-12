import { useNavigate, useLocation } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { useLanguage } from './LanguageContext'
import SettingsModal from './SettingsModal'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
const apiPort = import.meta.env.VITE_API_PORT
const launcherPort = import.meta.env.VITE_LAUNCHER_PORT

function Layout({ children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useLanguage()
  const [time, setTime] = useState(new Date())
  const [isDark, setIsDark] = useState(() => localStorage.getItem('theme') === 'dark')
  const [isConnected, setIsConnected] = useState(false)
  const [status, setStatus] = useState({
    summary: { suspected: 0, confirmed: 0 },
    pipelines: {}
  })
  const [toasts, setToasts] = useState([])
  const knownAlertKeys = useRef(null)
  const [isRunning, setIsRunning] = useState(false)
  const [launcherOnline, setLauncherOnline] = useState(false)
  const [stopLoading, setStopLoading] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

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

    const fetchLauncher = async () => {
      try {
        const res = await fetch(`${apiBaseUrl}:${launcherPort}/api/launcher/status`)
        if (res.ok) {
          const data = await res.json()
          setIsRunning(data.running)
          setLauncherOnline(true)
        } else {
          setLauncherOnline(false)
        }
      } catch {
        setLauncherOnline(false)
      }
    }

    fetchStatus()
    fetchLauncher()
    const statusTimer = setInterval(fetchStatus, 2000)
    const launcherTimer = setInterval(fetchLauncher, 3000)

    return () => {
      clearInterval(timer)
      clearInterval(statusTimer)
      clearInterval(launcherTimer)
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
            setToasts(prev => [...prev, { id, type: alert.type, pipeName: alert.pipe_name, state: alert.state }])
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
    { label: t('nav_monitoring'), path: '/dashboard', icon: '🖥️' },
    { label: t('nav_alerts'), path: '/alerts', icon: '🔔' },
    { label: t('nav_history'), path: '/detection-history', icon: '🕐' },
    { label: t('nav_retroactive'), path: '/precise-detection', icon: '🔍' },
  ]

  const connectedCams = Object.keys(status.pipelines).length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-page)' }}>

      {/* Top Bar */}
      <div style={{
        background: '#1a1f2e',
        color: 'white',
        padding: '0 36px',
        height: '72px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
          <span style={{ fontWeight: '600', fontSize: '22px' }}>{t('systemTitle')}</span>
          <span style={{ background: isConnected ? '#22c55e' : '#ef4444', color: 'white', fontSize: '16px', padding: '3px 12px', borderRadius: '10px' }}>
            {isConnected ? t('live') : t('offline')}
          </span>
          {launcherOnline && isRunning && (
            <button
              onClick={async () => {
                setStopLoading(true)
                try { await fetch(`${apiBaseUrl}:${launcherPort}/api/launcher/stop`, { method: 'POST' }) } finally { setStopLoading(false) }
              }}
              disabled={stopLoading}
              style={{
                padding: '3px 21px',
                background: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: '10px',
                fontSize: '19px',
                fontWeight: '600',
                lineHeight: 'inherit',
                cursor: stopLoading ? 'not-allowed' : 'pointer',
                opacity: stopLoading ? 0.6 : 1,
              }}
            >
              {stopLoading ? '...' : t('stopSystem')}
            </button>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <span style={{ background: '#f59e0b', color: '#1a1f2e', fontSize: '16px', padding: '3px 12px', borderRadius: '10px', fontWeight: '600' }}>{t('suspected')} {status.summary.suspected}</span>
          <span style={{ background: '#ef4444', color: 'white', fontSize: '16px', padding: '3px 12px', borderRadius: '10px', fontWeight: '600' }}>{t('confirmed')} {status.summary.confirmed}</span>
          <div style={{ cursor: 'pointer', position: 'relative' }} onClick={() => navigate('/alerts')}>
            <span style={{ fontSize: '27px' }}>🔔</span>
            <span style={{
              position: 'absolute',
              top: '-6px',
              right: '-8px',
              background: '#ef4444',
              color: 'white',
              fontSize: '15px',
              fontWeight: '600',
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>{(status.summary.suspected || 0) + (status.summary.confirmed || 0)}</span>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '19px', fontWeight: '600' }}>{formatTime(time)}</div>
            <div style={{ fontSize: '15px', color: '#9ca3af' }}>{formatDate(time)}</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Sidebar */}
        <div style={{ width: '250px', background: 'var(--bg-sidebar)', borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', padding: '18px 0' }}>
          {navItems.map((item, i) => (
            <div key={i} onClick={() => navigate(item.path)} style={{
              padding: '12px 25px',
              fontSize: '16px',
              color: location.pathname === item.path ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontWeight: location.pathname === item.path ? '600' : '400',
              background: location.pathname === item.path ? 'var(--bg-page)' : 'transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              borderLeft: location.pathname === item.path ? '3px solid #1a1f2e' : '3px solid transparent',
            }}>
              <span style={{ fontSize: '20px' }}>{item.icon}</span>
              {item.label}
            </div>
          ))}
          <div style={{ marginTop: 'auto' }}>
            <div
              onClick={() => setSettingsOpen(true)}
              style={{
                padding: '12px 25px',
                fontSize: '16px',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                borderLeft: '3px solid transparent',
                borderTop: '1px solid var(--border-color)',
              }}
            >
              <span style={{ fontSize: '20px' }}>⚙️</span>
              {t('nav_settings')}
            </div>
            <div style={{ padding: '10px 25px', fontSize: '14px', color: 'var(--text-muted)' }}>
              {t('cameraConnected', connectedCams)}
            </div>
          </div>
        </div>

        {/* Page Content */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {children}
        </div>

      </div>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />

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
              {toast.state === 'LOST' ? t('toastConfirmed') : t('toastSuspected')}
            </div>
            <div style={{ fontSize: '16px', fontWeight: '800' }}>
              {toast.type}
            </div>
            <div style={{ fontSize: '12px', fontWeight: '600', opacity: 0.85, marginTop: '3px' }}>
              {t('toastCamera', toast.pipeName)}
            </div>
          </div>
        ))}
      </div>

    </div>
  )
}

export default Layout
