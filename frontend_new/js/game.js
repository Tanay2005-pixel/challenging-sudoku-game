// sudoku duel single player game code

// get settings from url
const params   = new URLSearchParams(window.location.search);
const GRID_SIZE = parseInt(params.get('size')) || 9;
const DIFF_NUM  = parseInt(params.get('diff'))  || 1;
const DIFF_NAMES = { 1: 'Easy', 2: 'Medium', 3: 'Hard' };
const DIFF_NAME  = DIFF_NAMES[DIFF_NUM] || 'Medium';

const BOX_SIZE = GRID_SIZE === 4 ? 2 : GRID_SIZE === 9 ? 3 : 4;
const TOTAL    = GRID_SIZE * GRID_SIZE;

// player info
const player = (() => {
  const saved = localStorage.getItem('player');
  if (!saved) { window.location.replace('index.html'); return null; }
  try { return JSON.parse(saved); }
  catch { localStorage.removeItem('player'); window.location.replace('index.html'); return null; }
})();

// game variables
let board        = [];      // flat 1D array of current values
let solution     = [];      // flat 1D array of the solution (for validation)
let given        = new Set();// indices of pre-filled cells
let selected     = null;    // currently selected cell index
let pencilMode   = false;
let notes        = [];      // notes[idx] = Set of pencil marks
let seconds      = 0;
let timerInterval= null;
let gameActive   = false;
let isPaused     = false;
let hintsUsed    = 0;
let MAX_HINTS    = DIFF_NUM === 1 ? 5 : DIFF_NUM === 2 ? 3 : 1;
let errorsCount  = 0;

// html elements
const boardEl       = () => document.getElementById('board');
const timerEl       = () => document.getElementById('timer-display');
const progressFill  = () => document.getElementById('progress-fill');
const progressCount = () => document.getElementById('progress-count');
const hintsEl       = () => document.getElementById('hint-count');
const errorsEl      = () => document.getElementById('errors-count');

// generate puzzle from server

async function generatePuzzle() {
  try {
    toast('Generating puzzle from server...', 'info');
    
    const response = await fetch('/api/puzzle/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        size: GRID_SIZE,
        difficulty: DIFF_NUM
      })
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.status !== 'ok' || !data.puzzle) {
      throw new Error(data.message || 'Failed to generate puzzle');
    }

    // data.puzzle is a flat 1D array
    board = [...data.puzzle];
    notes = Array(TOTAL).fill(null).map(() => new Set());
    
    // Get the solution by solving the puzzle
    try {
      const solveResponse = await fetch('/api/puzzle/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          size: GRID_SIZE,
          board: board
        })
      });
      
      if (solveResponse.ok) {
        const solveData = await solveResponse.json();
        if (solveData.status === 'ok' && solveData.solution) {
          solution = [...solveData.solution];
        }
      }
    } catch (e) {
      console.warn('Could not fetch solution:', e);
    }

    // Mark givens (non-zero cells in initial puzzle)
    given.clear();
    board.forEach((v, i) => { if (v !== 0) given.add(i); });
    
    renderBoard();
    startGame();
  } catch (error) {
    console.error('Puzzle generation error:', error);
    toast('Failed to generate puzzle: ' + error.message, 'error');
  }
}

// draw the board

function renderBoard() {
  const el = boardEl();
  el.innerHTML = '';
  el.dataset.size = GRID_SIZE;

  for (let idx = 0; idx < TOTAL; idx++) {
    const cell = document.createElement('div');
    cell.className = 'sudoku-cell';
    cell.dataset.idx = idx;

    const row = Math.floor(idx / GRID_SIZE);
    const col = idx % GRID_SIZE;

    // Box borders
    if ((row + 1) % BOX_SIZE === 0 && row !== GRID_SIZE - 1) {
      cell.classList.add('cell-box-bottom');
    }

    const val = board[idx];

    if (given.has(idx)) {
      cell.classList.add('given');
      cell.textContent = val;
    } else if (val !== 0) {
      cell.classList.add('user-fill');
      // Check for errors in real-time if solution is available
      if (solution.length > 0 && val !== solution[idx]) {
        cell.classList.add('error');
      }
      cell.textContent = val;
    } else if (notes[idx] && notes[idx].size > 0) {
      cell.classList.add('pencil');
      const noteGrid = document.createElement('div');
      noteGrid.className = 'cell-notes';
      for (let n = 1; n <= GRID_SIZE && n <= 9; n++) {
        const note = document.createElement('div');
        note.className = 'cell-note' + (notes[idx].has(n) ? ' active' : '');
        note.textContent = notes[idx].has(n) ? n : '';
        noteGrid.appendChild(note);
      }
      cell.appendChild(noteGrid);
    }

    // Highlights
    if (idx === selected) {
      cell.classList.add('selected');
    } else if (selected !== null) {
      const selRow = Math.floor(selected / GRID_SIZE);
      const selCol = selected % GRID_SIZE;
      const selBox = Math.floor(selRow / BOX_SIZE) * BOX_SIZE + Math.floor(selCol / BOX_SIZE);
      const curBox = Math.floor(row / BOX_SIZE) * BOX_SIZE + Math.floor(col / BOX_SIZE);

      if (row === selRow || col === selCol || curBox === selBox) {
        cell.classList.add('highlight');
      }
      // Same number highlight
      if (val !== 0 && val === board[selected]) {
        cell.classList.add('same-num');
      }
    }

    cell.addEventListener('click', () => selectCell(idx));
    el.appendChild(cell);
  }

  updateProgress();
}

function selectCell(idx) {
  selected = idx;
  renderBoard();
}

// handle number input

function placeNumber(num) {
  if (!gameActive || isPaused || selected === null) return;
  if (given.has(selected)) return;

  if (pencilMode && num !== 0) {
    // Toggle pencil mark
    if (notes[selected].has(num)) notes[selected].delete(num);
    else notes[selected].add(num);
    renderBoard();
    return;
  }

  notes[selected].clear();
  board[selected] = num;

  // Check for errors in real-time
  if (num !== 0 && solution.length > 0) {
    if (num !== solution[selected]) {
      // Wrong number!
      errorsCount++;
      updateErrors();
      animateCell(selected);
      toast('❌ Wrong number!', 'error');
    }
  }

  if (num !== 0) {
    animateCell(selected);
    checkWin();
  }

  renderBoard();
}

document.addEventListener('keydown', (e) => {
  if (!gameActive || isPaused || selected === null) return;

  const num = GRID_SIZE <= 9 ? parseInt(e.key) : null;
  if (num >= 1 && num <= GRID_SIZE) { placeNumber(num); return; }
  if (e.key === 'Backspace' || e.key === 'Delete' || e.key === '0') { placeNumber(0); return; }
  if (e.key === 'p' || e.key === 'P') { togglePencil(); return; }

  // Arrow key navigation
  const r = Math.floor(selected / GRID_SIZE);
  const c = selected % GRID_SIZE;
  if (e.key === 'ArrowUp'    && r > 0)             selectCell((r-1)*GRID_SIZE+c);
  if (e.key === 'ArrowDown'  && r < GRID_SIZE-1)   selectCell((r+1)*GRID_SIZE+c);
  if (e.key === 'ArrowLeft'  && c > 0)             selectCell(r*GRID_SIZE+(c-1));
  if (e.key === 'ArrowRight' && c < GRID_SIZE-1)   selectCell(r*GRID_SIZE+(c+1));
});

// game control buttons

function togglePencil() {
  pencilMode = !pencilMode;
  const btn = document.getElementById('pencil-btn');
  if (btn) btn.classList.toggle('active', pencilMode);
  toast(pencilMode ? 'Pencil mode ON' : 'Pencil mode OFF', 'info');
}

function requestHint() {
  if (!gameActive || isPaused) return;
  if (hintsUsed >= MAX_HINTS) { toast('No hints remaining!', 'error'); return; }

  // Find an empty cell to fill
  let target = selected;
  if (target === null || given.has(target) || board[target] !== 0) {
    target = board.findIndex((v, i) => v === 0 && !given.has(i));
  }
  if (target === -1) { toast('Board is complete!', 'success'); return; }

  // Get hint from server
  getHintFromServer(target);
}

async function getHintFromServer(cellIdx) {
  try {
    const row = Math.floor(cellIdx / GRID_SIZE);
    const col = cellIdx % GRID_SIZE;

    const response = await fetch('/api/puzzle/hint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        size: GRID_SIZE,
        board: board,
        row: row,
        col: col
      })
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.status !== 'ok' || data.hint === undefined) {
      throw new Error(data.message || 'Failed to get hint');
    }

    if (data.hint === -1) {
      toast('No hint available for this cell', 'warning');
      return;
    }

    board[cellIdx] = data.hint;
    notes[cellIdx].clear();
    hintsUsed++;
    updateHints();
    selected = cellIdx;
    renderBoard();
    checkWin();
    toast('Hint placed! (' + (MAX_HINTS - hintsUsed) + ' left)', 'info');
  } catch (error) {
    console.error('Hint error:', error);
    toast('Failed to get hint: ' + error.message, 'error');
  }
}

function pauseGame() {
  if (!gameActive) return;
  isPaused = !isPaused;
  const overlay = document.getElementById('pause-overlay');
  const btn = document.getElementById('pause-btn');
  if (isPaused) {
    clearInterval(timerInterval);
    overlay && overlay.classList.add('show');
    btn && (btn.textContent = '▶ Resume');
  } else {
    startTimer();
    overlay && overlay.classList.remove('show');
    btn && (btn.textContent = '⏸ Pause');
  }
}

function resetBoard() {
  board = board.map((v, i) => given.has(i) ? v : 0);
  notes = Array(TOTAL).fill(null).map(() => new Set());
  errorsCount = 0;
  selected = null;
  updateErrors();
  renderBoard();
  toast('Board reset', 'info');
}

function newGame() {
  closeModal('result-modal');
  window.location.href = 'dashboard.html';
}

// check if puzzle is solved

async function checkWin() {
  const filled = board.filter((v, i) => v !== 0).length;
  if (filled < TOTAL) {
    // Not all cells filled yet, don't show message
    return;
  }

  // Validate with server
  try {
    toast('Validating solution...', 'info');
    
    const response = await fetch('/api/puzzle/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        size: GRID_SIZE,
        board: board
      })
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.status !== 'ok') {
      throw new Error(data.message || 'Validation failed');
    }

    const isValid = data.valid === true || data.valid === 'true';
    const isComplete = data.complete === true || data.complete === 'true';

    if (isValid && isComplete) {
      // Puzzle solved correctly!
      gameActive = false;
      clearInterval(timerInterval);
      showResultModal(true);
      await saveResult();
      spawnConfetti();
    } else if (!isValid) {
      toast('Some cells have conflicts. Check for errors!', 'error');
      animateBoard('shake');
    } else {
      toast('Not quite right. Keep trying!', 'info');
    }
  } catch (error) {
    console.error('Validation error:', error);
    toast('Failed to validate solution: ' + error.message, 'error');
  }
}

function showResultModal(won) {
  const modal = document.getElementById('result-modal');
  if (!modal) return;

  const time  = timerEl() ? timerEl().textContent : '0:00';
  const mins  = Math.floor(seconds / 60);
  const secs  = seconds % 60;

  document.getElementById('result-icon').textContent  = won ? '🏆' : '💔';
  document.getElementById('result-title').textContent = won ? 'PUZZLE SOLVED!' : 'GAME OVER';
  document.getElementById('result-time').textContent  = `${mins}:${String(secs).padStart(2,'0')}`;
  document.getElementById('result-errors').textContent = errorsCount;
  document.getElementById('result-hints').textContent  = hintsUsed;
  document.getElementById('result-filled').textContent = board.filter((v,i)=>v!==0).length + '/' + TOTAL;

  modal.classList.add('show');

  if (won) spawnConfetti();
}

async function saveResult() {
  const p = JSON.parse(localStorage.getItem('player') || '{}');
  
  const mins = Math.floor(seconds / 60);
  const secs = String(seconds % 60).padStart(2,'0');
  const timeStr = mins + ':' + secs;

  // Save to database
  try {
    const response = await fetch('/api/game/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: p.id || p.user_id,
        board_size: GRID_SIZE,
        difficulty: DIFF_NUM,
        time_seconds: seconds,
        hints_used: hintsUsed,
        errors_made: errorsCount,
        completed: true
      })
    });

    if (response.ok) {
      console.log('Game result saved to database');
    } else {
      console.error('Failed to save game result');
    }
  } catch (error) {
    console.error('Error saving game result:', error);
  }

  // Update local storage
  p.wins = (p.wins || 0) + 1;
  p.games = (p.games || 0) + 1;

  const game = {
    result: 'win',
    vs:   'Solo ' + GRID_SIZE + '×' + GRID_SIZE,
    diff: DIFF_NAME,
    time: timeStr,
    score: board.filter(v=>v!==0).length + '/' + TOTAL,
  };
  p.recent_games = [game, ...(p.recent_games || []).slice(0, 4)];
  if (!p.best_time || seconds < parseTime(p.best_time)) {
    p.best_time = timeStr;
  }

  localStorage.setItem('player', JSON.stringify(p));
}

function parseTime(str) {
  const [m, s] = str.split(':').map(Number);
  return m * 60 + s;
}

// timer and progress updates

function startTimer() {
  timerInterval = setInterval(() => {
    seconds++;
    const m = String(Math.floor(seconds / 60)).padStart(2, '0');
    const s = String(seconds % 60).padStart(2, '0');
    const el = timerEl();
    if (!el) return;
    el.textContent = `${m}:${s}`;

    // Color shifts
    el.className = 'timer-display';
    if (seconds > 600) el.classList.add('danger');
    else if (seconds > 300) el.classList.add('warning');
  }, 1000);
}

function updateProgress() {
  const filled = board.filter(v => v !== 0).length;
  const pct    = Math.round((filled / TOTAL) * 100);
  const fp = progressFill();
  const fc = progressCount();
  if (fp) fp.style.width = pct + '%';
  if (fc) fc.textContent = filled + '/' + TOTAL;
}

function updateErrors() {
  const el = errorsEl();
  if (el) el.textContent = errorsCount;
}

function updateHints() {
  const el = hintsEl();
  if (el) el.textContent = MAX_HINTS - hintsUsed;
}

// visual effects

function animateCell(idx) {
  const cells = boardEl().children;
  if (cells[idx]) {
    cells[idx].classList.add('cell-animate');
    setTimeout(() => cells[idx].classList.remove('cell-animate'), 300);
  }
}

function animateBoard(cls) {
  const el = boardEl();
  el.classList.add(cls);
  setTimeout(() => el.classList.remove(cls), 500);
}

function spawnConfetti() {
  const colors = ['#e8ff47', '#47ffe8', '#47ff8a', '#ff9f47'];
  const container = document.getElementById('confetti-container') || document.body;
  for (let i = 0; i < 30; i++) {
    setTimeout(() => {
      const piece = document.createElement('div');
      piece.className = 'confetti-piece';
      piece.style.cssText = `
        left: ${20 + Math.random() * 60}%;
        top: ${30 + Math.random() * 20}%;
        background: ${colors[Math.floor(Math.random() * colors.length)]};
        animation-delay: ${Math.random() * 0.3}s;
        animation-duration: ${0.6 + Math.random() * 0.4}s;
      `;
      container.appendChild(piece);
      setTimeout(() => piece.remove(), 1200);
    }, i * 30);
  }
}

// show notification message

let toastTimer;
function toast(msg, type) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className   = 'toast show ' + (type || 'info');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2500);
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('show');
}

// create number buttons

function buildNumpad() {
  const pad = document.getElementById('numpad');
  if (!pad) return;
  pad.innerHTML = '';

  // Number buttons
  const nums = GRID_SIZE <= 9 ? GRID_SIZE : 9;
  for (let n = 1; n <= nums; n++) {
    const btn = document.createElement('button');
    btn.className = 'numpad-btn';
    btn.textContent = n;
    btn.onclick = () => placeNumber(n);
    pad.appendChild(btn);
  }
  // If 16x16, add hex-style buttons A-G (10-16)
  if (GRID_SIZE === 16) {
    for (let n = 10; n <= 16; n++) {
      const btn = document.createElement('button');
      btn.className = 'numpad-btn';
      btn.textContent = n;
      btn.style.fontSize = '12px';
      btn.onclick = () => placeNumber(n);
      pad.appendChild(btn);
    }
  }

  // Pencil button
  const pencilBtn = document.createElement('button');
  pencilBtn.className = 'numpad-btn pencil-btn';
  pencilBtn.id = 'pencil-btn';
  pencilBtn.textContent = '✏';
  pencilBtn.title = 'Toggle pencil mode (P)';
  pencilBtn.onclick = togglePencil;
  pad.appendChild(pencilBtn);

  // Erase button
  const eraseBtn = document.createElement('button');
  eraseBtn.className = 'numpad-btn erase';
  eraseBtn.textContent = '✕ Erase';
  eraseBtn.onclick = () => placeNumber(0);
  pad.appendChild(eraseBtn);
}

// start the game

function startGame() {
  gameActive = true;
  startTimer();
}

// initialize everything

document.addEventListener('DOMContentLoaded', async () => {
  // Set player name in header
  const nameEl = document.getElementById('hdr-name');
  const winsEl = document.getElementById('hdr-wins');
  if (nameEl) nameEl.textContent = player.name || player.username || 'Player';
  if (winsEl) winsEl.textContent = (player.wins || 0) + 'W';

  // Set difficulty badge
  const diffEl = document.getElementById('diff-badge');
  if (diffEl) {
    diffEl.textContent = DIFF_NAME;
    diffEl.className   = 'diff-badge diff-' + DIFF_NAME.toLowerCase();
  }

  // Set size label
  const sizeEl = document.getElementById('size-label');
  if (sizeEl) sizeEl.textContent = GRID_SIZE + '×' + GRID_SIZE;

  // Hints label
  updateHints();

  // Generate puzzle (now async)
  await generatePuzzle();
  buildNumpad();

  // Modal close
  document.querySelectorAll('.overlay').forEach(o => {
    o.addEventListener('click', e => {
      if (e.target === o) o.classList.remove('show');
    });
  });
});
