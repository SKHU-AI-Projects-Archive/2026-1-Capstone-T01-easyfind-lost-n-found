import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function Login() {
  const [id, setId] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()

  const handleLogin = () => {
    if (id === 'admin' && password === '1234') {
      navigate('/dashboard')
    } else {
      alert('아이디 또는 비밀번호가 틀렸습니다.')
    }
  }

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: '#1a1f2e',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '48px 40px',
        width: '400px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '16px',
      }}>
        <div style={{
          width: '56px',
          height: '56px',
          background: '#1a1f2e',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px',
        }}>🛡️</div>

        <h1 style={{ fontSize: '20px', fontWeight: '600', margin: 0, textAlign: 'center' }}>
          Lost Item Detection System
        </h1>
        <p style={{ color: '#666', margin: 0, fontSize: '14px' }}>Administrator Login</p>

        <input
          type="text"
          placeholder="Enter your ID"
          value={id}
          onChange={(e) => setId(e.target.value)}
          style={{
            width: '100%',
            padding: '12px 16px',
            border: '1px solid #ddd',
            borderRadius: '8px',
            fontSize: '14px',
            boxSizing: 'border-box',
          }}
        />
        <input
          type="password"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{
            width: '100%',
            padding: '12px 16px',
            border: '1px solid #ddd',
            borderRadius: '8px',
            fontSize: '14px',
            boxSizing: 'border-box',
          }}
        />
        <button
          onClick={handleLogin}
          style={{
            width: '100%',
            padding: '12px',
            background: '#1a1f2e',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '15px',
            cursor: 'pointer',
          }}
        >
          Login
        </button>
        <p style={{ color: '#999', fontSize: '12px', margin: 0 }}>
          Authorized personnel only
        </p>
      </div>
    </div>
  )
}

export default Login