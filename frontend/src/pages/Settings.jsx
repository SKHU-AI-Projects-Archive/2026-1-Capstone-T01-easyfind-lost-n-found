import { useState } from 'react'

function Settings() {
  const [cameras, setCameras] = useState([
    { id: 'CAM-A2', name: 'Terminal A - Gate 12', location: 'Terminal A', enabled: true },
    { id: 'CAM-B1', name: 'Food Court - Main Area', location: 'Food Court', enabled: true },
    { id: 'CAM-C4', name: 'East Entrance - Lobby', location: 'East Entrance', enabled: true },
    { id: 'CAM-D3', name: 'West Wing - Corridor', location: 'West Wing', enabled: false },
  ])
  const [suspectedTime, setSuspectedTime] = useState(5)
  const [confirmedTime, setConfirmedTime] = useState(10)
  const [objectTypes, setObjectTypes] = useState({ Backpack: true, Handbag: true, Luggage: true, Coat: true })
  const [adminAlerts, setAdminAlerts] = useState(true)
  const [alertSound, setAlertSound] = useState(true)

  const toggleCamera = (id) => {
    setCameras(cameras.map(c => c.id === id ? { ...c, enabled: !c.enabled } : c))
  }

  const toggleObject = (type) => {
    setObjectTypes({ ...objectTypes, [type]: !objectTypes[type] })
  }

  const sectionStyle = {
    background: 'white',
    border: '1px solid #e5e7eb',
    borderRadius: '10px',
    padding: '20px 24px',
    marginBottom: '16px',
  }

  const sectionTitle = {
    fontSize: '15px',
    fontWeight: '600',
    marginBottom: '16px',
    paddingBottom: '12px',
    borderBottom: '1px solid #f3f4f6',
  }

  const toggleStyle = (enabled) => ({
    width: '40px',
    height: '22px',
    borderRadius: '11px',
    background: enabled ? '#22c55e' : '#e5e7eb',
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
      <p style={{ color: '#6b7280', fontSize: '13px', margin: '0 0 20px' }}>Configure camera, detection, and notification settings</p>

      {/* Camera Settings */}
      <div style={sectionStyle}>
        <div style={sectionTitle}>Camera Settings</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {cameras.map((cam) => (
            <div key={cam.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: '#f9fafb', borderRadius: '8px' }}>
              <div>
                <div style={{ fontWeight: '500', fontSize: '14px' }}>{cam.name}</div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>{cam.id} · {cam.location}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '12px', color: cam.enabled ? '#22c55e' : '#9ca3af' }}>{cam.enabled ? 'Enabled' : 'Disabled'}</span>
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
        <div style={sectionTitle}>Detection Settings</div>

        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontWeight: '500', fontSize: '14px', marginBottom: '12px' }}>Detection Thresholds</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '13px', fontWeight: '500', marginBottom: '4px' }}>Suspected Status (minutes)</div>
              <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px' }}>Time before an item is marked as suspected</div>
              <input type="number" value={suspectedTime} onChange={(e) => setSuspectedTime(e.target.value)} min="1" max="60" style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '14px', boxSizing: 'border-box' }} />
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: '500', marginBottom: '4px' }}>Confirmed Status (minutes)</div>
              <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px' }}>Time before an item is marked as confirmed lost</div>
              <input type="number" value={confirmedTime} onChange={(e) => setConfirmedTime(e.target.value)} min="1" max="60" style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '14px', boxSizing: 'border-box' }} />
            </div>
          </div>
        </div>

        <div>
          <div style={{ fontWeight: '500', fontSize: '14px', marginBottom: '12px' }}>Object Types to Detect</div>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {Object.keys(objectTypes).map((type) => (
              <div key={type} onClick={() => toggleObject(type)} style={{
                padding: '8px 16px',
                borderRadius: '20px',
                border: `1px solid ${objectTypes[type] ? '#1a1f2e' : '#e5e7eb'}`,
                background: objectTypes[type] ? '#1a1f2e' : 'white',
                color: objectTypes[type] ? 'white' : '#6b7280',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: objectTypes[type] ? '600' : '400',
              }}>{type}</div>
            ))}
          </div>
        </div>
      </div>

      {/* Notification Settings */}
      <div style={sectionStyle}>
        <div style={sectionTitle}>Notification Settings</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {[
            { label: 'Admin Alerts', desc: 'Receive notifications for all detected items', value: adminAlerts, toggle: () => setAdminAlerts(!adminAlerts) },
            { label: 'Alert Sound', desc: 'Play sound when new alert is detected', value: alertSound, toggle: () => setAlertSound(!alertSound) },
          ].map((item, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontWeight: '500', fontSize: '14px' }}>{item.label}</div>
                <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>{item.desc}</div>
              </div>
              <div style={toggleStyle(item.value)} onClick={item.toggle}>
                <div style={toggleDotStyle(item.value)}></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Save Button */}
      <button onClick={() => alert('Settings saved!')} style={{
        padding: '12px 32px',
        background: '#1a1f2e',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        fontSize: '14px',
        fontWeight: '600',
        cursor: 'pointer',
      }}>Save Settings</button>
    </div>
  )
}

export default Settings