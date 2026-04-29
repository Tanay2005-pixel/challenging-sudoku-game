// sudoku duel multiplayer lobby code

let currentUser = null;
let currentGameId = null;
let currentRoomCode = null;
let lobbySize = 9;
let lobbyDiff = 1;
let pollingInterval = null;

// initialize lobby
document.addEventListener('DOMContentLoaded', function() {
  loadUserInfo();
  loadMultiplayerStats();
});

// get player info
function loadUserInfo() {
  const userData = localStorage.getItem('player');
  if (userData) {
    currentUser = JSON.parse(userData);
    document.getElementById('hdr-name').textContent = currentUser.username || 'Player';
    document.getElementById('hdr-wins').textContent = (currentUser.wins || 0) + 'W';
  }
}

// get multiplayer stats
function loadMultiplayerStats() {
  if (!currentUser || !currentUser.id) {
    console.log('No user loaded yet, skipping stats');
    return;
  }
  
  // Fetch multiplayer stats from API
  fetch(`/api/multiplayer/stats/${currentUser.id}`)
    .then(r => r.json())
    .then(data => {
      document.getElementById('mp-wins').textContent = data.multiplayer_wins || 0;
      document.getElementById('mp-wr').textContent = (data.win_rate || 0).toFixed(1) + '%';
    })
    .catch(err => console.error('Error loading stats:', err));
}

// choose puzzle size
function setLobbySize(size) {
  lobbySize = size;
  document.querySelectorAll('.size-row .pill').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('settings-size').textContent = size + '×' + size;
  document.getElementById('size-label').textContent = size + '×' + size;
}

// choose difficulty
function setLobbyDiff(diff) {
  lobbyDiff = diff;
  document.querySelectorAll('.diff-row .pill').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');
  
  const diffNames = { 1: 'Easy', 2: 'Medium', 3: 'Hard' };
  document.getElementById('settings-diff').textContent = diffNames[diff];
  document.getElementById('diff-badge').textContent = diffNames[diff];
  document.getElementById('diff-badge').className = 'diff-badge diff-' + 
    (diff === 1 ? 'easy' : diff === 2 ? 'medium' : 'hard');
}

// make a new room
function createRoom() {
  if (!currentUser) {
    toast('Please log in first', 'error');
    return;
  }

  console.log('Creating room with:', { user_id: currentUser.id || currentUser.user_id, board_size: lobbySize, difficulty: lobbyDiff });

  const payload = {
    user_id: currentUser.id || currentUser.user_id,  // Support both 'id' and 'user_id'
    board_size: lobbySize,
    difficulty: lobbyDiff
  };

  fetch('/api/multiplayer/room/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(r => {
      console.log('Response status:', r.status);
      return r.json();
    })
    .then(data => {
      console.log('Response data:', data);
      
      if (data.error) {
        toast(data.error, 'error');
        return;
      }
      
      currentGameId = data.game_id;
      currentRoomCode = data.room_code;
      
      console.log('Room created:', { game_id: currentGameId, room_code: currentRoomCode });
      
      // Show room info
      const roomInfoEl = document.getElementById('room-info');
      const roomCodeEl = document.getElementById('room-code-display');
      const waitingEl = document.getElementById('waiting-screen');
      
      console.log('Elements found:', { 
        roomInfo: !!roomInfoEl, 
        roomCode: !!roomCodeEl, 
        waiting: !!waitingEl 
      });
      
      if (roomInfoEl) roomInfoEl.style.display = 'block';
      if (roomCodeEl) roomCodeEl.textContent = currentRoomCode;
      if (waitingEl) waitingEl.style.display = 'block';
      
      toast('Room created! Code: ' + currentRoomCode, 'success');
      
      // check for updates for opponent
      startLobbyPolling();
    })
    .catch(err => {
      console.error('Error creating room:', err);
      toast('Failed to create room', 'error');
    });
}

// join existing room
function joinRoom() {
  if (!currentUser) {
    toast('Please log in first', 'error');
    return;
  }

  const roomCode = document.getElementById('join-room-code').value.toUpperCase().trim();
  if (!roomCode) {
    toast('Please enter a room code', 'error');
    return;
  }

  const payload = {
    user_id: currentUser.id || currentUser.user_id,  // Support both 'id' and 'user_id'
    room_code: roomCode
  };

  fetch('/api/multiplayer/room/join', {
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
      
      currentGameId = data.game_id;
      currentRoomCode = roomCode;
      
      // Show opponent info
      displayOpponentInfo(data.opponent);
      document.getElementById('opponent-info').style.display = 'block';
      
      // Update settings
      lobbySize = data.board_size;
      lobbyDiff = data.difficulty;
      document.getElementById('settings-size').textContent = lobbySize + '×' + lobbySize;
      document.getElementById('settings-diff').textContent = 
        ['Easy', 'Medium', 'Hard'][lobbyDiff - 1];
      
      toast('Joined room! Waiting for opponent to be ready…', 'success');
      
      // check for updates for game start
      startLobbyPolling();
    })
    .catch(err => {
      console.error('Error joining room:', err);
      toast('Failed to join room', 'error');
    });
}

// show opponent info
function displayOpponentInfo(opponent) {
  if (!opponent) {
    console.warn('No opponent data provided');
    return;
  }
  
  const elements = {
    'opponent-name': opponent.username || 'Opponent',
    'opponent-wins': (opponent.wins || 0) + 'W',
    'opponent-wr': (opponent.win_rate || 0).toFixed(1) + '%',
    'opponent-name-board': opponent.username || 'Opponent'
  };
  
  for (const [id, value] of Object.entries(elements)) {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = value;
    }
  }
}

// copy room code
function copyRoomCode() {
  const code = document.getElementById('room-code-display').textContent;
  navigator.clipboard.writeText(code).then(() => {
    toast('Room code copied to clipboard!', 'success');
  });
}

// check for opponent joining
function startLobbyPolling() {
  if (pollingInterval) clearInterval(pollingInterval);
  
  pollingInterval = setInterval(() => {
    if (!currentGameId) return;
    
    fetch(`/api/multiplayer/room/${currentRoomCode}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          clearInterval(pollingInterval);
          toast(data.error, 'error');
          return;
        }
        
        // Check if both players are ready
        if (data.players && data.players.length === 2) {
          const opponent = data.players.find(p => p.user_id !== currentUser.user_id);
          if (opponent) {
            displayOpponentInfo(opponent);
            document.getElementById('opponent-info').style.display = 'block';
            document.getElementById('start-btn').disabled = false;
            document.getElementById('start-btn').textContent = 'START GAME';
          }
        }
        
        // Check if game has started
        if (data.status === 'in_progress') {
          clearInterval(pollingInterval);
          startMultiplayerGame();
        }
      })
      .catch(err => console.error('Polling error:', err));
  }, 2000);
}

// begin multiplayer game
function startMultiplayerGame() {
  if (!currentGameId) {
    toast('Game ID not found', 'error');
    return;
  }
  
  // Update game status to in_progress
  fetch(`/api/multiplayer/room/${currentRoomCode}/status`)
    .then(r => r.json())
    .then(data => {
      if (data.players && data.players.length < 2) {
        toast('Waiting for opponent to join...', 'warning');
        return;
      }
      
      // Store game info in session
      sessionStorage.setItem('multiplayerGameId', currentGameId);
      sessionStorage.setItem('multiplayerRoomCode', currentRoomCode);
      sessionStorage.setItem('multiplayerBoardSize', lobbySize);
      sessionStorage.setItem('multiplayerDifficulty', lobbyDiff);
      
      // Navigate to multiplayer game
      window.location.href = 'game-multiplayer.html';
    })
    .catch(err => {
      console.error('Error starting game:', err);
      toast('Failed to start game', 'error');
    });
}

// quit game
function giveUpMultiplayer() {
  if (!currentGameId) return;
  
  document.getElementById('confirm-title').textContent = 'Give Up?';
  document.getElementById('confirm-body').textContent = 
    'Are you sure you want to give up? You will lose this game.';
  document.getElementById('confirm-modal').style.display = 'flex';
  
  window.confirmAction = function() {
    fetch(`/api/multiplayer/game/${currentGameId}/give-up`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: currentUser.id || currentUser.user_id })
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
