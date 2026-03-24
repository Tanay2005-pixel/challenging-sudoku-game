const API    = 'http://localhost:8000'
const player = JSON.parse(localStorage.getItem('player') || 'null')
const roomId = localStorage.getItem('room_id')
if (!player || !roomId) window.location.href = '/'

// ── State ─────────────────────────────────────────────────────
let board        = []       // current board state (2D array)
let givenCells   = new Set()// indices of pre-filled (read-only) cells
let selectedCell = null     // currently selected cell index
let ws           = null
let timerInterval= null
let seconds      = 0
let hintsUsed    = 0
let gameActive   = false

// ── UI refs ───────────────────────────────────────────────────
const boardEl    = document.getElementById('board')
document.getElementById('nav-room').textContent    = roomId
document.getElementById('nav-username').textContent= player.username

// ── WebSocket connect ─────────────────────────────────────────
function connectWS() {
  ws = new WebSocket(
    `ws://localhost:8000/ws/${roomId}/${player.id}/${player.username}`
  )

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    handleMessage(msg)
  }

  ws.onclose = () => {
    if (gameActive)
      showToast('Connection lost!', 'error')
  }
}

function handleMessage(msg) {
  switch(msg.type) {

    case 'player_joined':
      document.getElementById('status-msg').textContent =
        `${msg.player} joined. Players: ${msg.count}/2`
      break

    case 'game_start':
      startGame(msg.board, msg.difficulty)
      break

    case 'opponent_progress':
      document.getElementById('opponent-name').textContent =
        msg.username
      document.getElementById('nav-opponent').textContent =
        msg.username
      const oppPct = Math.round((msg.filled / 81) * 100)
      document.getElementById('opp-progress').style.width =
        oppPct + '%'
      document.getElementById('opp-filled').textContent =
        msg.filled
      break

    case 'hint_response':
      board[msg.row][msg.col] = msg.value
      renderBoard()
      hintsUsed = msg.hints_used
      document.getElementById('hints-used').textContent = hintsUsed
      updateProgress()
      break

    case 'game_over':
      endGame(msg.winner === player.username, msg.winner, msg.time)
      break

    case 'invalid_solution':
      showToast(msg.msg, 'error')
      break

    case 'opponent_disconnected':
      endGame(true, player.username, seconds)
      showToast('Opponent disconnected. You win!', 'success')
      break

    case 'error':
      showToast(msg.msg, 'error')
      setTimeout(() => window.location.href = '/lobby', 2000)
      break
  }
}

// ── Start game ────────────────────────────────────────────────
function startGame(serverBoard, difficulty) {
  board = serverBoard
  gameActive = true

  document.getElementById('difficulty-display').textContent =
    difficulty
  document.getElementById('status-msg').textContent =
    'Game started! Race to finish!'
  document.getElementById('submit-btn').disabled = false
  document.getElementById('hint-btn').disabled   = false

  // Mark given cells
  givenCells.clear()
  for (let r = 0; r < 9; r++)
    for (let c = 0; c < 9; c++)
      if (board[r][c] !== 0)
        givenCells.add(r * 9 + c)

  renderBoard()
  startTimer()
}

// ── Render board ──────────────────────────────────────────────
function renderBoard() {
  boardEl.innerHTML = ''

  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const idx  = r * 9 + c
      const cell = document.createElement('div')
      cell.className = 'sudoku-cell'
      cell.dataset.idx = idx

      const val = board[r][c]
      if (val !== 0) cell.textContent = val

      if (givenCells.has(idx))  cell.classList.add('given')
      if (idx === selectedCell) cell.classList.add('selected')

      cell.addEventListener('click', () => selectCell(idx))
      boardEl.appendChild(cell)
    }
  }
}

// ── Select cell ───────────────────────────────────────────────
function selectCell(idx) {
  if (givenCells.has(idx)) return
  selectedCell = idx
  renderBoard()
}

// ── Place number ──────────────────────────────────────────────
function placeNumber(num) {
  if (!gameActive || selectedCell === null) return
  if (givenCells.has(selectedCell)) return

  const r = Math.floor(selectedCell / 9)
  const c = selectedCell % 9
  board[r][c] = num

  // Send move to server
  ws.send(JSON.stringify({type:'move', row:r, col:c, value:num}))

  renderBoard()
  updateProgress()
}

// ── Keyboard input ────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (!gameActive || selectedCell === null) return
  const num = parseInt(e.key)
  if (num >= 1 && num <= 9) placeNumber(num)
  if (e.key === 'Backspace' || e.key === 'Delete') placeNumber(0)

  // Arrow key navigation
  const r = Math.floor(selectedCell / 9)
  const c = selectedCell % 9
  if (e.key==='ArrowUp'    && r>0) selectCell((r-1)*9+c)
  if (e.key==='ArrowDown'  && r<8) selectCell((r+1)*9+c)
  if (e.key==='ArrowLeft'  && c>0) selectCell(r*9+(c-1))
  if (e.key==='ArrowRight' && c<8) selectCell(r*9+(c+1))
})

// ── Progress ──────────────────────────────────────────────────
function updateProgress() {
  const filled = board.flat().filter(v => v !== 0).length
  const pct    = Math.round((filled / 81) * 100)
  document.getElementById('my-progress').style.width = pct + '%'
}

// ── Submit ────────────────────────────────────────────────────
function submitBoard() {
  ws.send(JSON.stringify({type: 'submit'}))
}

// ── Hint ─────────────────────────────────────────────────────
function requestHint() {
  if (selectedCell === null)
    return showToast('Select an empty cell first', 'error')
  if (givenCells.has(selectedCell))
    return showToast('That cell is already given', 'error')

  const r = Math.floor(selectedCell / 9)
  const c = selectedCell % 9
  if (board[r][c] !== 0)
    return showToast('Cell is already filled', 'error')

  ws.send(JSON.stringify({type:'hint', row:r, col:c}))
}

// ── Timer ─────────────────────────────────────────────────────
function startTimer() {
  timerInterval = setInterval(() => {
    seconds++
    const m = String(Math.floor(seconds/60)).padStart(2,'0')
    const s = String(seconds % 60).padStart(2,'0')
    document.getElementById('timer').textContent = `${m}:${s}`
  }, 1000)
}

// ── Game over ─────────────────────────────────────────────────
function endGame(won, winnerName, time) {
  gameActive = false
  clearInterval(timerInterval)
  document.getElementById('submit-btn').disabled = true
  document.getElementById('hint-btn').disabled   = true

  document.getElementById('modal-icon').textContent  = won ? '🏆' : '😔'
  document.getElementById('modal-title').textContent = won ? 'You Win!' : 'You Lose!'
  document.getElementById('modal-msg').textContent   =
    won
      ? `Congratulations! Solved in ${time}s`
      : `${winnerName} finished first in ${time}s`

  document.getElementById('game-modal').classList.add('show')
}

function goToLobby() { window.location.href = '/lobby' }

// ── Toast ─────────────────────────────────────────────────────
function showToast(msg, type='') {
  const t = document.getElementById('toast')
  t.textContent = msg
  t.className = `toast show ${type}`
  setTimeout(() => t.className = 'toast', 3000)
}

// ── Init ──────────────────────────────────────────────────────
connectWS()