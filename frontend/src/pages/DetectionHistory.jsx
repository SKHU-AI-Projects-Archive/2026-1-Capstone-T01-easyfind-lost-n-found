import { useState } from 'react'

function DetectionHistory() {
  const [filterDate, setFilterDate] = useState('Today')
  const [filterCam, setFilterCam] = useState('All Cameras')
  const [filterType, setFilterType] = useState('All Types')
  const [filterStatus, setFilterStatus] = useState('All Status')

  const allData = [
    { type: 'Backpack', cam: 'CAM-A2', location: 'Terminal A Gate 12', time: 'Mar 27, 2026 11:22', duration: '45 min', status: 'Confirmed' },
    { type: 'Luggage', cam: 'CAM-B1', location: 'Food Court', time: 'Mar 27, 2026 09:22', duration: '28 min', status: 'Suspected' },
    { type: 'Handbag', cam: 'CAM-C4', location: 'East Entrance', time: 'Mar 27, 2026 08:22', duration: '15 min', status: 'Suspected' },
    { type: 'Coat', cam: 'CAM-D3', location: 'West Wing', time: 'Mar 27, 2026 07:22', duration: '62 min', status: 'Confirmed' },
    { type: 'Backpack', cam: 'CAM-A2', location: 'Terminal A Gate 12', time: 'Mar 27, 2026 05:22', duration: '33 min', status: 'Suspected' },
    { type: 'Luggage', cam: 'CAM-B1', location: 'Food Court', time: 'Mar 27, 2026 03:22', duration: '89 min', status: 'Confirmed' },
  ]

  const filtered = allData.filter(row => {
    if (filterCam !== 'All Cameras' && row.cam !== filterCam) return false
    if (filterType !== 'All Types' && row.type !== filterType) return false
    if (filterStatus !== 'All Status' && row.status !== filterStatus) return false
    return true
  })

  return (
    <div style={{ flex: 1, padding: '24px', overflow: 'auto' }}>
      <h2 style={{ fontSize: '22px', fontWeight: '600', margin: '0 0 4px' }}>Detection History</h2>
      <p style={{ color: '#6b7280', fontSize: '13px', margin: '0 0 20px' }}>View and filter all detected lost items</p>

      {/* Filters */}
      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '16px 20px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
          <span style={{ fontSize: '13px', fontWeight: '600' }}>🔍 Filters</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          {[
            { label: 'Date Range', value: filterDate, setter: setFilterDate, options: ['Today', 'This Week', 'This Month'] },
            { label: 'Camera', value: filterCam, setter: setFilterCam, options: ['All Cameras', 'CAM-A2', 'CAM-B1', 'CAM-C4', 'CAM-D3'] },
            { label: 'Object Type', value: filterType, setter: setFilterType, options: ['All Types', 'Backpack', 'Luggage', 'Handbag', 'Coat'] },
            { label: 'Status', value: filterStatus, setter: setFilterStatus, options: ['All Status', 'Suspected', 'Confirmed'] },
          ].map((filter, i) => (
            <div key={i}>
              <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>{filter.label}</div>
              <select
                value={filter.value}
                onChange={(e) => filter.setter(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '13px', color: '#1a1f2e' }}
              >
                {filter.options.map((opt, j) => <option key={j}>{opt}</option>)}
              </select>
            </div>
          ))}
        </div>
      </div>

      {/* Table */}
      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', overflow: 'hidden' }}>
        <div style={{ padding: '12px 20px', fontSize: '13px', color: '#6b7280', borderBottom: '1px solid #e5e7eb' }}>
          Showing {filtered.length} results
        </div>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px', color: '#9ca3af', fontSize: '14px' }}>
            No results found
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9fafb' }}>
                {['Thumbnail', 'Object Type', 'Camera', 'Location', 'Time', 'Duration', 'Status'].map((col, i) => (
                  <th key={i} style={{ padding: '10px 16px', fontSize: '11px', fontWeight: '600', color: '#6b7280', textAlign: 'left', letterSpacing: '0.05em', textTransform: 'uppercase' }}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, i) => (
                <tr key={i} style={{ borderTop: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '12px 16px' }}>
                    <div style={{ width: '44px', height: '44px', background: '#1a1f2e', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', color: '#6b7280' }}>IMG</div>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px', fontWeight: '500' }}>{row.type}</td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>{row.cam}</td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>{row.location}</td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>{row.time}</td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>{row.duration}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{
                      fontSize: '11px',
                      padding: '3px 10px',
                      borderRadius: '10px',
                      fontWeight: '600',
                      background: row.status === 'Confirmed' ? '#fef2f2' : '#fffbeb',
                      color: row.status === 'Confirmed' ? '#ef4444' : '#f59e0b',
                    }}>{row.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default DetectionHistory