// sudoku duel multiplayer game code

let currentUser = null;
let gameId = null;
let roomCode = null;
let boardSize = 9;
let difficulty = 1;
let puzzle = [];
let solution = [];
let board = [];
let selectedCell = null;
let isPaused = false;
let gameActive = false;
let timerInterval = null;
let timeElapsed = 0;
let errorCount = 0;
let hintsUsed = 0;
let hintsLeft = 3;
let gameCompleted = false;
let opponentCompleted = false;
let pollingInterval = null;

// initialize game
document.addEventListener('DOMContentLoaded', function() {
  loadUserInfo();
  loadGameData();
  initializeBoard();
  startTimer();
  startPolling();
});

// get player info
function loadUserInfo() {
  const userData = localStorage.getItem('user');
  if (userData) {
    currentUser = JSON.parse(userData);
    document.getElementById('hdr-name').textContent = currentUser.username || 'Player';
    document.getElementById('hdr-wins').textContent = (currentUser.wins || 0) + 'W';
  }
}

// get game data from server
function loadGameData() {
  gameId = sessionStorage.getItem('multiplayerGameId');
  roomCode = sessionStorage.getItem('multiplayerRoomCode');
  
  // get player name first
  const userData = localStorage.getItem('player');
  if (userData) {
    currentUser = JSON.parse(userData);
  }
  
  if (!gameId || !currentUser) {
    toast('Game or user not found', 'error');
    setTimeout(() => window.location.href = 'dashboard.html', 1500);
    return;
  }
  
  // Fetch game state from API with user_id
  fetch(`/api/multiplayer/game/${gameId}/state?user_id=${currentUser.id || currentUser.user_id}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        toast(data.error, 'error');
        return;
      }
      
      boardSize = data.board_size || 9;
      difficulty = data.difficulty || 1;
      
      // Use your_board as the current puzzle state
      puzzle = data.your_board || [];
      solution = data.solution || [];
      board = [...puzzle];
      
      console.log('Game data loaded:', { boardSize, difficulty, puzzleLength: puzzle.length });
      
      // Update UI
      document.getElementById('size-label').textContent = boardSize + '×' + boardSize;
      const diffNames = { 1: 'Easy', 2: 'Medium', 3: 'Hard' };
      document.getElementById('diff-badge').textContent = diffNames[difficulty];
      document.getElementById('diff-badge').className = 'diff-badge diff-' + 
        (difficulty === 1 ? 'easy' : difficulty === 2 ? 'medium' : 'hard');
      
      // Load opponent info
      if (data.opponent) {
        document.getElementById('opponent-name-board').textContent = data.opponent.username || 'Opponent';
      }
      
      gameActive = true;
      
      // setup the board display
      initializeBoard();
      initializeNumpad();
      startTimer();
      startPolling();
    })
    .catch(err => {
      console.error('Error loading game:', err);
      toast('Failed to load game', 'error');
    });
}

// setup the board
function initializeBoard() {
  const el = document.getElementById('board');
  if (!el) {
    console.error('Board container not found');
    return;
  }
  
  el.innerHTML = '';
  el.dataset.size = boardSize;
  
  const boxSize = boardSize === 4 ? 2 : boardSize === 9 ? 3 : 4;
  const total = boardSize * boardSize;

  for (let idx = 0; idx < total; idx++) {
    const cell = document.createElement('div');
    cell.className = 'sudoku-cell';
    cell.dataset.idx = idx;

    const row = Math.floor(idx / boardSize);
    const col = idx % boardSize;

    // Box borders
    if ((row + 1) % boxSize === 0 && row !== boardSize - 1) {
      cell.classList.add('cell-box-bottom');
    }

    const val = board[idx];

    if (puzzle[idx] !== 0) {
      cell.classList.add('given');
      cell.textContent = val;
    } else if (val !== 0) {
      cell.classList.add('user-fill');
      // Check for errors in real-time if solution is available
      if (solution.length > 0 && val !== solution[idx]) {
        cell.classList.add('error');
      }
      cell.textContent = val;
    }

    // Highlights
    if (idx === selectedCell) {
      cell.classList.add('selected');
    } else if (selectedCell !== null) {
      const selRow = Math.floor(selectedCell / boardSize);
      const selCol = selectedCell % boardSize;
      const selBox = Math.floor(selRow / boxSize) * boxSize + Math.floor(selCol / boxSize);
      const curBox = Math.floor(row / boxSize) * boxSize + Math.floor(col / boxSize);

      if (row === selRow || col === selCol || curBox === selBox) {
        cell.classList.add('highlight');
      }
      // Same number highlight
      if (val !== 0 && val === board[selectedCell]) {
        cell.classList.add('same-num');
      }
    }

    cell.addEventListener('click', () => selectCell(idx));
    el.appendChild(cell);
  }

  updateProgress();
}

// create number buttons
function initializeNumpad() {
  const numpadEl = document.getElementById('numpad');
  if (!numpadEl) return;
  
  numpadEl.innerHTML = '';
  
  // Number buttons
  const nums = boardSize <= 9 ? boardSize : 9;
  for (let n = 1; n <= nums; n++) {
    const btn = document.createElement('button');
    btn.className = 'numpad-btn';
    btn.textContent = n;
    btn.onclick = () => placeNumber(n);
    numpadEl.appendChild(btn);
  }
  
  // If 16x16, add hex-style buttons 10-16
  if (boardSize === 16) {
    for (let n = 10; n <= 16; n++) {
      const btn = document.createElement('button');
      btn.className = 'numpad-btn';
      btn.textContent = n;
      btn.style.fontSize = '12px';
      btn.onclick = () => placeNumber(n);
      numpadEl.appendChild(btn);
    }
  }
  
  // Erase button
  const eraseBtn = document.createElement('button');
  eraseBtn.className = 'numpad-btn erase';
  eraseBtn.textContent = '✕ Erase';
  eraseBtn.onclick = () => placeNumber(0);
  numpadEl.appendChild(eraseBtn);
}

// select a cell
function selectCell(idx) {
  if (!gameActive || gameCompleted) return;
  
  selectedCell = idx;
  initializeBoard(); // Re-render to show highlights
}

// put number in cell
function placeNumber(num) {
  if (selectedCell === null || !gameActive || gameCompleted) return;
  
  const row = Math.floor(selectedCell / boardSize);
  const col = selectedCell % boardSize;
  
  // Check if cell is given
  if (puzzle[selectedCell] !== 0) {
    toast('Cannot modify given cells', 'error');
    return;
  }
  
  // Place the number directly (like single player)
  board[selectedCell] = num;
  
  // Check for errors in real-time
  if (num !== 0 && solution.length > 0 && num !== solution[selectedCell]) {
    errorCount++;
    toast('Incorrect placement', 'warning');
  }
  
  // Re-render board to show the change
  initializeBoard();
  
  // update progress bar
  updateProgress();
  
  // Check if completed
  checkCompletion();
}

// ── Send Move (Not used in current implementation) ──
// Moves are only sent when completing the game
function sendMove() {
  // not used anymore
  return;
}

// update progress bar
function updateProgress() {
  let filled = 0;
  for (let i = 0; i < board.length; i++) {
    if (board[i] !== 0) filled++;
  }
  
  const total = boardSize * boardSize;
  document.getElementById('progress-count').textContent = filled + '/' + total;
  document.getElementById('progress-fill').style.width = (filled / total * 100) + '%';
}

// check if puzzle done
function checkCompletion() {
  let filled = 0;
  for (let i = 0; i < board.length; i++) {
    if (board[i] !== 0) filled++;
  }
  
  if (filled === boardSize * boardSize) {
    // Verify solution
    let isCorrect = true;
    for (let i = 0; i < board.length; i++) {
      if (board[i] !== solution[i]) {
        isCorrect = false;
        break;
      }
    }
    
    if (isCorrect) {
      completeGame();
    }
  }
}

// finish the game
function completeGame() {
  gameCompleted = true;
  gameActive = false;
  clearInterval(timerInterval);
  // keep checking for opponent
  
  // Send completion to server
  const payload = {
    user_id: currentUser.id || currentUser.user_id,
    time_seconds: timeElapsed,
    hints_used: hintsUsed,
    errors_made: errorCount,
    board_state: board
  };
  
  fetch(`/api/multiplayer/game/${gameId}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        toast(data.error, 'error');
        return;
      }
      
      // show win screen
      showResultModal(data);
    })
    .catch(err => {
      console.error('Error completing game:', err);
      toast('Failed to complete game', 'error');
    });
}

// show win screen
function showResultModal(data) {
  // Game is finished (first player to complete wins)
  document.getElementById('result-icon').textContent = '🏆';
  document.getElementById('result-title').textContent = 'PUZZLE SOLVED!';
  document.getElementById('result-time').textContent = formatTime(timeElapsed);
  document.getElementById('result-filled').textContent = (boardSize * boardSize) + '/' + (boardSize * boardSize);
  document.getElementById('result-errors').textContent = errorCount;
  document.getElementById('result-hints').textContent = hintsUsed;
  
  document.getElementById('result-modal').style.display = 'flex';
}

// get a hint
function requestHint() {
  if (!gameActive || gameCompleted || hintsLeft <= 0) {
    toast('No hints left', 'error');
    return;
  }
  
  if (selectedCell === null) {
    toast('Select a cell first', 'error');
    return;
  }
  
  // Reveal solution for selected cell
  board[selectedCell] = solution[selectedCell];
  
  hintsUsed++;
  hintsLeft--;
  document.getElementById('hint-count').textContent = hintsLeft;
  
  // Re-render board to show the hint
  initializeBoard();
  updateProgress();
  checkCompletion();
}

// clear the board
function resetBoard() {
  if (!gameActive || gameCompleted) return;
  
  board = [...puzzle];
  errorCount = 0;
  hintsUsed = 0;
  hintsLeft = 3;
  
  document.querySelectorAll('.cell').forEach((cell, i) => {
    if (puzzle[i] === 0) {
      cell.textContent = '';
      cell.classList.remove('error', 'hint');
    }
  });
  
  document.getElementById('errors-count').textContent = '0';
  document.getElementById('hint-count').textContent = '3';
  updateProgress();
}

// pause game
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

// quit game
function giveUpMultiplayer() {
  if (!gameActive || gameCompleted) return;
  
  document.getElementById('confirm-title').textContent = 'Give Up?';
  document.getElementById('confirm-body').textContent = 
    'Are you sure you want to give up? You will lose this game.';
  document.getElementById('confirm-modal').style.display = 'flex';
  
  window.confirmAction = function() {
    fetch(`/api/multiplayer/game/${gameId}/give-up`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: currentUser.user_id })
    })
      .then(r => r.json())
      .then(data => {
        closeModal('confirm-modal');
        if (data.error) {
          toast(data.error, 'error');
          return;
        }
        toast('You gave up. Game over.', 'info');
        setTimeout(() => window.location.href = 'dashboard.html', 1500);
      })
      .catch(err => {
        console.error('Error:', err);
        toast('Failed to give up', 'error');
      });
  };
}

// start timer
function startTimer() {
  timerInterval = setInterval(() => {
    if (!isPaused && gameActive && !gameCompleted) {
      timeElapsed++;
      document.getElementById('timer-display').textContent = formatTime(timeElapsed);
    }
  }, 1000);
}

// format time display
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
}

// check for opponent updates
function startPolling() {
  // check if opponent finished
  pollingInterval = setInterval(() => {
    if (!gameId || !currentUser) {
      clearInterval(pollingInterval);
      return;
    }
    
    const userId = currentUser.id || currentUser.user_id;
    
    fetch(`/api/multiplayer/game/${gameId}/state?user_id=${userId}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          console.error('Polling error:', data.error);
          return;
        }
        
        // see if opponent done
        if (data.opponent_completed && !opponentCompleted) {
          opponentCompleted = true;
          
          // check if you really finished
          if (!gameCompleted) {
            // see if puzzle solved
            let isComplete = true;
            for (let i = 0; i < board.length; i++) {
              if (board[i] === 0 || board[i] !== solution[i]) {
                isComplete = false;
                break;
              }
            }
            
            if (isComplete) {
              // you finished too
              toast('Opponent finished! Submitting your completion...', 'success');
              setTimeout(() => {
                completeGame();
              }, 1000);
            } else {
              // you didnt finish
              toast('Opponent finished! You did not complete the puzzle.', 'warning');
              setTimeout(() => {
                giveUpMultiplayer();
              }, 2000);
            }
          }
        }
        
        // see if game over
        if (data.status === 'completed' && !gameCompleted) {
          gameCompleted = true;
          gameActive = false;
          clearInterval(pollingInterval);
          clearInterval(timerInterval);
          
          // go to results page
          toast('Game completed! Viewing results...', 'success');
          setTimeout(() => {
            viewResults();
          }, 1500);
        }
      })
      .catch(err => {
        console.error('Polling error:', err);
      });
  }, 2000); // Poll every 2 seconds
}

// show opponent finished message
function showOpponentCompletedNotification(opponentStatus) {
  const card = document.getElementById('opponent-completed-card');
  document.getElementById('opponent-name-notif').textContent = opponentStatus.username || 'Opponent';
  document.getElementById('opponent-final-score').textContent = opponentStatus.score || 0;
  card.style.display = 'block';
}

// go to results page
function viewResults() {
  sessionStorage.setItem('multiplayerGameId', gameId);
  window.location.href = 'results-multiplayer.html';
}

// go back to dashboard
function returnToDashboard() {
  window.location.href = 'dashboard.html';
}

// show notification
function toast(message, type = 'info') {
  const toastEl = document.getElementById('toast');
  toastEl.textContent = message;
  toastEl.className = 'toast show ' + type;
  setTimeout(() => toastEl.classList.remove('show'), 3000);
}

// close popup
function closeModal(modalId) {
  document.getElementById(modalId).style.display = 'none';
}

// Close modal on background click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('overlay')) {
    e.target.style.display = 'none';
  }
});
