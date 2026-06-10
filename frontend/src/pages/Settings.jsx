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

  const sectionStyle = {
    background: 'var(--bg-card)',
    border: '1px solid var(--border-color)',
    borderRadius: '10px',
    padding: '20px 24px',
    marginBottom: '16px',
  }

  const sectionTitleStyle = {
    fontSize: '15px',
    fontWeight: '600',
    marginBottom: '16px',
    paddingBottom: '12px',
    borderBottom: '1px solid var(--border-subtle)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  }

  const toggleStyle = (enabled) => ({
    width: '40px',
    height: '22px',
    borderRadius: '11px',
    background: enabled ? '#22c55e' : 'var(--border-color)',
    cursor: 'pointer',
    position: 'relative',
    transition: 'background 0.2s',
    flexShrink: 0,
  })

  const toggleDotStyle = (enabled) => ({
    position: 'absolute',
    top: '3px',
    left: enabled ? '21px' : '3px',
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    background: 'white',
    transition: 'left 0.2s',
  })

  return (
    <div style={{ padding: '24px', overflow: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '22px', fontWeight: '600', margin: '0 0 4px' }}>System Settings</h2>
      <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: '0 0 20px' }}>Configure notification settings</p>

      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>
          <span style={{ fontSize: '18px' }}>🎨</span>
          Appearance
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: '500', fontSize: '14px' }}>Dark Mode</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>Switch between light and dark theme</div>
          </div>
          <div style={toggleStyle(isDark)} onClick={toggleTheme}>
            <div style={toggleDotStyle(isDark)}></div>
          </div>
        </div>
      </div>

      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>
          <span style={{ fontSize: '18px' }}>🔔</span>
          Notification Settings
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: '500', fontSize: '14px' }}>Toast Notifications</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>Show toast alerts when new lost items are detected</div>
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
  )
}

export default Settings
