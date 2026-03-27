function Dashboard() {
  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px', height: '100%', overflow: 'auto' }}>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        {[
          { label: 'Suspected Lost Items', value: '2', color: '#f59e0b' },
          { label: 'Confirmed Lost Items', value: '1', color: '#ef4444' },
        ].map((card, i) => (
          <div key={i} style={{ background: 'white', borderRadius: '10px', padding: '16px 20px', border: '1px solid #e5e7eb' }}>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>{card.label}</div>
            <div style={{ fontSize: '28px', fontWeight: '700', color: card.color }}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* CCTV Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', flex: 1 }}>
        {[
          { name: 'CAM 01 — 1F Entrance', status: 'Suspected', statusColor: '#f59e0b', msg: 'Backpack stationary (32s)' },
          { name: 'CAM 02 — 2F Corridor', status: 'Normal', statusColor: '#22c55e', msg: 'No alerts' },
          { name: 'CAM 03 — B1 Parking', status: 'Confirmed', statusColor: '#ef4444', msg: 'Luggage (2min+)' },
          { name: 'CAM 04 — 3F Lounge', status: 'Normal', statusColor: '#22c55e', msg: 'No alerts' },
        ].map((cam, i) => (
          <div key={i} style={{ background: '#111827', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px', border: cam.status === 'Confirmed' ? '1px solid #ef4444' : '1px solid transparent' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#9ca3af', fontSize: '12px' }}>{cam.name}</span>
              <span style={{ background: '#22c55e', color: 'white', fontSize: '10px', padding: '2px 6px', borderRadius: '8px' }}>● LIVE</span>
            </div>
            <div style={{ flex: 1, background: '#1f2937', borderRadius: '6px', minHeight: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: '#4b5563', fontSize: '12px' }}>Connecting to stream...</span>
            </div>
            <div style={{ fontSize: '11px', color: cam.statusColor }}>{cam.status} — {cam.msg}</div>
          </div>
        ))}
      </div>

      {/* Right Panel */}
      <div style={{ position: 'fixed', right: 0, top: '48px', width: '260px', background: 'white', borderLeft: '1px solid #e5e7eb', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px', height: 'calc(100vh - 48px)', overflow: 'auto' }}>
        <div>
          <div style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Real-time Alerts</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { item: 'Luggage', cam: 'CAM 03', time: '15:40', status: 'Confirmed', color: '#ef4444', bg: '#fef2f2' },
              { item: 'Backpack', cam: 'CAM 01', time: '15:42', status: 'Suspected', color: '#f59e0b', bg: '#fffbeb' },
            ].map((alert, i) => (
              <div key={i} style={{ border: `1px solid #e5e7eb`, borderLeft: `3px solid ${alert.color}`, borderRadius: '0 8px 8px 0', padding: '10px', background: alert.bg }}>
                <div style={{ fontWeight: '600', fontSize: '13px' }}>{alert.item}</div>
                <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>{alert.cam} · {alert.time}</div>
                <span style={{ fontSize: '11px', background: alert.color, color: 'white', padding: '2px 8px', borderRadius: '8px', display: 'inline-block', marginTop: '6px' }}>{alert.status}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Detection Timeline</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { time: '15:38', text: 'Luggage + person linked', color: '#9ca3af' },
              { time: '15:39', text: 'Person left, object fixed', color: '#9ca3af' },
              { time: '15:39', text: 'Suspected — timer started', color: '#f59e0b' },
              { time: '15:40', text: 'Confirmed lost item', color: '#ef4444' },
              { time: '15:42', text: 'Admin alert sent', color: '#3b82f6' },
            ].map((tl, i) => (
              <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '12px', color: '#6b7280' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: tl.color, flexShrink: 0 }}></div>
                <span style={{ color: tl.color, fontWeight: '500', minWidth: '36px' }}>{tl.time}</span>
                <span>{tl.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  )
}

export default Dashboard