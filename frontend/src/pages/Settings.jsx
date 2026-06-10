import { useState } from 'react'

function Settings() {
  const [cameras, setCameras] = useState(() => {
    const saved = localStorage.getItem('cameras')
    return saved ? JSON.parse(saved) : [
      { id: 'CAM-A2', name: 'Terminal A - Gate 12', location: 'Terminal A', enabled: true },
      { id: 'CAM-B1', name: 'Food Court - Main Area', location: 'Food Court', enabled: true },
      { id: 'CAM-C4', name: 'East Entrance - Lobby', location: 'East Entrance', enabled: true },
      { id: 'CAM-D3', name: 'West Wing - Corridor', location: 'West Wing', enabled: false },
    ]
  })
  const [suspectedTime, setSuspectedTime] = useState(() => localStorage.getItem('suspectedTime') || 5)
  const [confirmedTime, setConfirmedTime] = useState(() => localStorage.getItem('confirmedTime') || 10)
  const [objectTypes, setObjectTypes] = useState(() => {
    const saved = localStorage.getItem('objectTypes')
    return saved ? JSON.parse(saved) : { Backpack: true, Handbag: true, Luggage: true, Coat: true }
  })
  const [adminAlerts, setAdminAlerts] = useState(() => localStorage.getItem('adminAlerts') !== 'false')
  const [alertSound, setAlertSound] = useState(() => localStorage.getItem('alertSound') !== 'false')

  const toggleCamera = (id) => {
    setCameras(cameras.map(c => c.id === id ? { ...c, enabled: !c.enabled } : c))
  }

  const toggleObject = (type) => {
    setObjectTypes({ ...objectTypes, [type]: !objectTypes[type] })
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
      <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: '0 0 20px' }}>Configure camera, detection, and notification settings</p>

      {/* Camera Settings */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>
          <span style={{ fontSize: '18px' }}>📷</span>
          Camera Settings
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {cameras.map((cam) => (
            <div key={cam.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-subtle)', borderRadius: '8px' }}>
              <div>
                <div style={{ fontWeight: '500', fontSize: '14px' }}>{cam.name}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>{cam.id} · {cam.location}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '12px', color: cam.enabled ? '#22c55e' : 'var(--text-muted)' }}>{cam.enabled ? 'Enabled' : 'Disabled'}</span>
                <div style={toggleStyle(cam.enabled)} onClick={() => toggleCamera(cam.id)}>
                  <div style={toggleDotStyle(cam.enabled)}></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detection Settings */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>
          <span style={{ fontSize: '18px' }}>🎯</span>
          Detection Settings
        </div>

        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontWeight: '500', fontSize: '14px', marginBottom: '12px' }}>Detection Thresholds</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '13px', fontWeight: '500', marginBottom: '4px' }}>Suspected Status (minutes)</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>Time before an item is marked as suspected</div>
              <input type="number" value={suspectedTime} onChange={(e) => setSuspectedTime(e.target.value)} min="1" max="60" style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '14px', boxSizing: 'border-box', background: 'var(--bg-input)', color: 'var(--text-primary)' }} />
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: '500', marginBottom: '4px' }}>Confirmed Status (minutes)</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>Time before an item is marked as confirmed lost</div>
              <input type="number" value={confirmedTime} onChange={(e) => setConfirmedTime(e.target.value)} min="1" max="60" style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '14px', boxSizing: 'border-box', background: 'var(--bg-input)', color: 'var(--text-primary)' }} />
            </div>
          </div>
        </div>

        <div>
          <div style={{ fontWeight: '500', fontSize: '14px', marginBottom: '12px' }}>Object Types to Detect</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            {Object.keys(objectTypes).map((type) => (
              <div key={type} onClick={() => toggleObject(type)} style={{
                padding: '12px 16px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-card)',
                fontSize: '14px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}>
                <div style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '4px',
                  background: objectTypes[type] ? '#378ADD' : 'var(--bg-card)',
                  border: objectTypes[type] ? '2px solid #378ADD' : '2px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  {objectTypes[type] && <span style={{ color: 'white', fontSize: '12px', fontWeight: '700' }}>✓</span>}
                </div>
                <span style={{ color: 'var(--text-primary)' }}>{type}</span>
              </div>
            ))}
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
            { label: 'Alert Sound', desc: 'Play sound when new alert is detected', value: alertSound, toggle: () => setAlertSound(!alertSound) },
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
        localStorage.setItem('cameras', JSON.stringify(cameras))
        localStorage.setItem('suspectedTime', suspectedTime)
        localStorage.setItem('confirmedTime', confirmedTime)
        localStorage.setItem('objectTypes', JSON.stringify(objectTypes))
        localStorage.setItem('adminAlerts', adminAlerts)
        localStorage.setItem('alertSound', alertSound)
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
