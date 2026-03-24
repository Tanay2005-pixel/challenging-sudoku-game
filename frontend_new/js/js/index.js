const API = 'http://localhost:8000/api'

function showToast(msg, type='') {
  const t = document.getElementById('toast')
  t.textContent = msg
  t.className = `toast show ${type}`
  setTimeout(() => t.className = 'toast', 3000)
}

function showRegister() {
  document.getElementById('login-form').style.display    = 'none'
  document.getElementById('register-form').style.display = 'block'
}
function showLogin() {
  document.getElementById('register-form').style.display = 'none'
  document.getElementById('login-form').style.display    = 'block'
}

async function login() {
  const username = document.getElementById('login-username').value.trim()
  const password = document.getElementById('login-password').value.trim()
  if (!username || !password)
    return showToast('Fill in all fields', 'error')

  const res  = await fetch(`${API}/login`, {
    method:  'POST',
    headers: {'Content-Type': 'application/json'},
    body:    JSON.stringify({username, password})
  })
  const data = await res.json()
  if (!res.ok) return showToast(data.detail || 'Login failed', 'error')

  localStorage.setItem('player', JSON.stringify(data.player))
  window.location.href = '/lobby'
}

async function register() {
  const username = document.getElementById('reg-username').value.trim()
  const password = document.getElementById('reg-password').value.trim()
  if (!username || !password)
    return showToast('Fill in all fields', 'error')

  const res  = await fetch(`${API}/register`, {
    method:  'POST',
    headers: {'Content-Type': 'application/json'},
    body:    JSON.stringify({username, password})
  })
  const data = await res.json()
  if (!res.ok) return showToast(data.detail || 'Register failed', 'error')

  showToast('Account created! Please login.', 'success')
  showLogin()
}

// Redirect if already logged in
const player = JSON.parse(localStorage.getItem('player') || 'null')
if (player) window.location.href = '/lobby'