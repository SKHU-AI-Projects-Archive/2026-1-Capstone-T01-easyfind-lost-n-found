import { useState } from 'react'
import { useLanguage } from '../LanguageContext'

function Settings() {
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

  const rowStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  }

  const innerCardStyle = {
    background: 'var(--bg-subtle)',
    border: '1px solid var(--border-color)',
    borderRadius: '10px',
    padding: '20px 24px',
    marginBottom: '16px',
  }

  const sectionLabelStyle = {
    fontSize: '13px',
    fontWeight: '700',
    color: 'var(--text-secondary)',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    marginBottom: '16px',
  }

  return (
    <div style={{ padding: '40px 32px', overflow: 'auto', height: '100%' }}>

      <div style={{
        maxWidth: '800px',
        margin: '0 auto',
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '16px',
        padding: '32px',
      }}>

        <h2 style={{ fontSize: '26px', fontWeight: '700', margin: '0 0 6px' }}>{t('systemSettings')}</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '15px', margin: '0 0 28px' }}>{t('configurePrefs')}</p>

        {/* Appearance */}
        <div style={innerCardStyle}>
          <div style={sectionLabelStyle}>{t('appearance')}</div>
          <div style={rowStyle}>
            <div>
              <div style={{ fontWeight: '600', fontSize: '16px' }}>{t('darkMode')}</div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '3px' }}>{t('darkModeDesc')}</div>
            </div>
            <div style={toggleStyle(isDark)} onClick={toggleTheme}>
              <div style={toggleDotStyle(isDark)}></div>
            </div>
          </div>
        </div>

        {/* Language */}
        <div style={innerCardStyle}>
          <div style={sectionLabelStyle}>{t('language')}</div>
          <div style={rowStyle}>
            <div>
              <div style={{ fontWeight: '600', fontSize: '16px' }}>{t('displayLanguage')}</div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '3px' }}>{t('displayLanguageDesc')}</div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              {[{ code: 'en', label: 'English' }, { code: 'ko', label: '한국어' }].map(({ code, label }) => (
                <button key={code} onClick={() => setLanguage(code)} style={{
                  padding: '6px 16px',
                  borderRadius: '8px',
                  border: `1px solid ${lang === code ? '#1a1f2e' : 'var(--border-color)'}`,
                  background: lang === code ? '#1a1f2e' : 'var(--bg-input)',
                  color: lang === code ? 'white' : 'var(--text-primary)',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}>
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Notifications */}
        <div style={{ ...innerCardStyle, marginBottom: 0 }}>
          <div style={sectionLabelStyle}>{t('notifications')}</div>
          <div style={rowStyle}>
            <div>
              <div style={{ fontWeight: '600', fontSize: '16px' }}>{t('toastNotifications')}</div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '3px' }}>{t('toastNotificationsDesc')}</div>
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
