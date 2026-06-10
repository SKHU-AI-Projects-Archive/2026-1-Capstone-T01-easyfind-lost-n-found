import { useState } from 'react'

function Settings() {
  const [adminAlerts, setAdminAlerts] = useState(() => localStorage.getItem('adminAlerts') !== 'false')
  const [isDark, setIsDark] = useState(() => localStorage.getItem('theme') === 'dark')

  const toggleTheme = () => {
    const next = !isDark
    setIsDark(next)
    localStorage.setItem('theme', next ? 'dark' : 'light')
    document.documentElement.setAttribute('data-theme', next ? 'dark' : 'light')
  }

  const toggleStyle = (enabled) => ({
    width: '44px',
    height: '24px',
    borderRadius: '12px',
    background: enabled ? '#22c55e' : 'var(--border-color)',
    cursor: 'pointer',
    position: 'relative',
    transition: 'background 0.2s',
    flexShrink: 0,
  })

  const toggleDotStyle = (enabled) => ({
    position: 'absolute',
    top: '4px',
    left: enabled ? '22px' : '4px',
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    background: 'white',
    transition: 'left 0.2s',
  })

  const rowStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  }

  return (
    <div style={{ padding: '40px 32px', overflow: 'auto', height: '100%' }}>

      {/* 큰 외부 카드 — 제목 포함 */}
      <div style={{
        maxWidth: '800px',
        margin: '0 auto',
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '16px',
        padding: '32px',
      }}>

        <h2 style={{ fontSize: '26px', fontWeight: '700', margin: '0 0 6px' }}>System Settings</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '15px', margin: '0 0 28px' }}>Configure system preferences</p>

        {/* Appearance 내부 카드 */}
        <div style={{
          background: 'var(--bg-subtle)',
          border: '1px solid var(--border-color)',
          borderRadius: '10px',
          padding: '20px 24px',
          marginBottom: '16px',
        }}>
          <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '16px' }}>
            Appearance
          </div>
          <div style={rowStyle}>
            <div>
              <div style={{ fontWeight: '600', fontSize: '16px' }}>Dark Mode</div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '3px' }}>Switch between light and dark theme</div>
            </div>
            <div style={toggleStyle(isDark)} onClick={toggleTheme}>
              <div style={toggleDotStyle(isDark)}></div>
            </div>
          </div>
        </div>

        {/* Notifications 내부 카드 */}
        <div style={{
          background: 'var(--bg-subtle)',
          border: '1px solid var(--border-color)',
          borderRadius: '10px',
          padding: '20px 24px',
        }}>
          <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '16px' }}>
            Notifications
          </div>
          <div style={rowStyle}>
            <div>
              <div style={{ fontWeight: '600', fontSize: '16px' }}>Toast Notifications</div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '3px' }}>Show toast alerts when new lost items are detected</div>
            </div>
            <div style={toggleStyle(adminAlerts)} onClick={() => {
              const v = !adminAlerts
              setAdminAlerts(v)
              localStorage.setItem('adminAlerts', v)
            }}>
              <div style={toggleDotStyle(adminAlerts)}></div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}

export default Settings
