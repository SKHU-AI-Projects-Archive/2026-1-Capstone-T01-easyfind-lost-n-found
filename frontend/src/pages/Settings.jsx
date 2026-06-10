import { useState } from 'react'

function Settings() {
  const [suspectedTime, setSuspectedTime] = useState(() => localStorage.getItem('suspectedTime') || 15)
  const [confirmedTime, setConfirmedTime] = useState(() => localStorage.getItem('confirmedTime') || 15)
  const [adminAlerts, setAdminAlerts] = useState(() => localStorage.getItem('adminAlerts') !== 'false')

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
      <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: '0 0 20px' }}>Configure detection and notification settings</p>

      {/* Detection Thresholds */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>
          <span style={{ fontSize: '18px' }}>🎯</span>
          Detection Thresholds
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '13px', fontWeight: '500', marginBottom: '4px' }}>Suspected Status (minutes)</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>Time before an item is marked as suspected</div>
            <input
              type="number"
              value={suspectedTime}
              onChange={(e) => setSuspectedTime(e.target.value)}
              min="1" max="60"
              style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '14px', boxSizing: 'border-box', background: 'var(--bg-input)', color: 'var(--text-primary)' }}
            />
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: '500', marginBottom: '4px' }}>Confirmed Status (minutes)</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>Time before an item is marked as confirmed lost</div>
            <input
              type="number"
              value={confirmedTime}
              onChange={(e) => setConfirmedTime(e.target.value)}
              min="1" max="60"
              style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '14px', boxSizing: 'border-box', background: 'var(--bg-input)', color: 'var(--text-primary)' }}
            />
          </div>
        </div>
      </div>

      {/* Notification Settings */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>
          <span style={{ fontSize: '18px' }}>🔔</span>
          Notification Settings
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {[
            { label: 'Admin Alerts', desc: 'Receive notifications for all detected items', value: adminAlerts, toggle: () => setAdminAlerts(!adminAlerts) },
          ].map((item, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontWeight: '500', fontSize: '14px' }}>{item.label}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{item.desc}</div>
              </div>
              <div style={toggleStyle(item.value)} onClick={item.toggle}>
                <div style={toggleDotStyle(item.value)}></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Save Button */}
      <button onClick={() => {
        localStorage.setItem('suspectedTime', suspectedTime)
        localStorage.setItem('confirmedTime', confirmedTime)
        localStorage.setItem('adminAlerts', adminAlerts)
        alert('Settings saved!')
      }} style={{
        padding: '12px 32px',
        background: '#22c55e',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        fontSize: '14px',
        fontWeight: '600',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        💾 Save Settings
      </button>
    </div>
  )
}

export default Settings
