import { useState } from 'react'
import { useLanguage } from './LanguageContext'

function SettingsModal({ open, onClose }) {
  const { t, lang, setLanguage } = useLanguage()
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

  const sectionLabelStyle = {
    fontSize: '11px',
    fontWeight: '700',
    color: 'var(--text-secondary)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    marginBottom: '8px',
    paddingLeft: '4px',
  }

  const rowStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 16px',
    background: 'var(--bg-card)',
    borderRadius: '12px',
  }

  return (
    <>
      {/* 백드롭 */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.4)',
          zIndex: 1100,
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity 0.25s',
        }}
      />

      {/* 중앙 패널 */}
      <div style={{
        position: 'fixed', top: '50%', left: '50%',
        transform: open ? 'translate(-50%, -50%) scale(1)' : 'translate(-50%, -50%) scale(0.95)',
        opacity: open ? 1 : 0,
        pointerEvents: open ? 'auto' : 'none',
        width: '480px',
        background: 'var(--bg-page)',
        zIndex: 1200,
        transition: 'transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s',
        display: 'flex', flexDirection: 'column',
        borderRadius: '20px',
        boxShadow: '0 24px 64px rgba(0,0,0,0.35)',
        maxHeight: '85vh',
      }}>

        {/* 헤더 */}
        <div style={{
          padding: '20px 20px 16px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: '18px', fontWeight: '700' }}>{t('systemSettings')}</span>
          <button onClick={onClose} style={{
            background: 'var(--bg-subtle)', border: 'none', borderRadius: '50%',
            width: '30px', height: '30px', fontSize: '16px', cursor: 'pointer',
            color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>✕</button>
        </div>

        {/* 컨텐츠 */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 16px', display: 'flex', flexDirection: 'column', gap: '24px' }}>

          {/* Appearance */}
          <div>
            <div style={sectionLabelStyle}>{t('appearance')}</div>
            <div style={rowStyle}>
              <div>
                <div style={{ fontWeight: '600', fontSize: '15px' }}>{t('darkMode')}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{t('darkModeDesc')}</div>
              </div>
              <div style={toggleStyle(isDark)} onClick={toggleTheme}>
                <div style={toggleDotStyle(isDark)} />
              </div>
            </div>
          </div>

          {/* Language */}
          <div>
            <div style={sectionLabelStyle}>{t('language')}</div>
            <div style={rowStyle}>
              <div>
                <div style={{ fontWeight: '600', fontSize: '15px' }}>{t('displayLanguage')}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{t('displayLanguageDesc')}</div>
              </div>
              <select
                value={lang}
                onChange={e => setLanguage(e.target.value)}
                style={{
                  padding: '7px 12px',
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-input)',
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                <option value="en">{t('lang_en')}</option>
                <option value="ko">{t('lang_ko')}</option>
              </select>
            </div>
          </div>

          {/* Notifications */}
          <div>
            <div style={sectionLabelStyle}>{t('notifications')}</div>
            <div style={rowStyle}>
              <div>
                <div style={{ fontWeight: '600', fontSize: '15px' }}>{t('toastNotifications')}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{t('toastNotificationsDesc')}</div>
              </div>
              <div style={toggleStyle(adminAlerts)} onClick={() => {
                const v = !adminAlerts
                setAdminAlerts(v)
                localStorage.setItem('adminAlerts', v)
              }}>
                <div style={toggleDotStyle(adminAlerts)} />
              </div>
            </div>
          </div>

        </div>
      </div>
    </>
  )
}

export default SettingsModal
