import { useNavigate, useLocation } from 'react-router-dom'

function Layout({ children }) {
  const navigate = useNavigate()
  const location = useLocation()

  const navItems = [
    { label: 'Monitoring', path: '/dashboard' },
    { label: 'Detection History', path: '/detection-history' },
    { label: 'Alerts', path: '/alerts' },
    { label: 'Settings', path: '/settings' },
  ]

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
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ background: '#f59e0b', color: '#1a1f2e', fontSize: '11px', padding: '2px 8px', borderRadius: '10px', fontWeight: '600' }}>Suspected 2</span>
          <span style={{ background: '#ef4444', color: 'white', fontSize: '11px', padding: '2px 8px', borderRadius: '10px', fontWeight: '600' }}>Confirmed 1</span>
          <button onClick={() => navigate('/')} style={{ background: 'transparent', color: '#aaa', border: '1px solid #444', borderRadius: '6px', padding: '4px 12px', cursor: 'pointer', fontSize: '12px' }}>Logout</button>
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
            }}>{item.label}</div>
          ))}
          <div style={{ marginTop: 'auto', padding: '12px 20px', fontSize: '11px', color: '#9ca3af' }}>
            <div>Camera 4 / 4 connected</div>
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