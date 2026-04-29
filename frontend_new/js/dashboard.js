// sudoku duel dashboard code

// get player data or go back to login
const saved = localStorage.getItem('player');
if (!saved) {
  window.location.replace('index.html');
}
let player = { id: 1, name: 'Player', wins: 0, loss: 0 };
if (saved) {
  try { player = JSON.parse(saved); } catch(e) {
    localStorage.removeItem('player');
    window.location.replace('index.html');
  }
}

// setup header with player info
function initHeader() {
  const name = player.name || player.username || 'Player';
  const wins = player.wins || 0;
  const loss = player.loss || player.losses || 0;
  const wr   = wins + loss > 0 ? Math.round(wins / (wins + loss) * 100) : 0;

  const el = (id) => document.getElementById(id);

  el('hdr-name') && (el('hdr-name').textContent = name);
  el('hdr-wins') && (el('hdr-wins').textContent = wins + 'W');

  el('stats-title') && (el('stats-title').textContent = name.toUpperCase() + "'S STATS");
  el('stat-wins')  && (el('stat-wins').textContent  = wins);
  el('stat-loss')  && (el('stat-loss').textContent  = loss);
  el('stat-wr')    && (el('stat-wr').textContent    = wr + '%');
  el('stat-time')  && (el('stat-time').textContent  = player.best_time || '—');

  el('lb-me-name') && (el('lb-me-name').innerHTML = name + ' <span style="font-size:11px;color:var(--accent)">← You</span>');
}

// switch between different sections
function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.sidebar-btn').forEach(b => b.classList.remove('active'));

  const sec = document.getElementById('sec-' + name);
  if (sec) sec.classList.add('active');

  document.querySelectorAll('.nav-btn').forEach(b => {
    if (b.textContent.toLowerCase().includes(name)) b.classList.add('active');
  });
  document.querySelectorAll('.sidebar-btn').forEach(b => {
    if (b.textContent.toLowerCase().includes(name)) b.classList.add('active');
  });
  
  // load leaderboard when tab is clicked
  if (name === 'leaderboard') {
    loadLeaderboard('global');
  }
  
  // load multiplayer data when tab is clicked
  if (name === 'multiplayer') {
    loadMultiplayerLeaderboard();
  }
  
  // load friends when tab is clicked
  if (name === 'friends') {
    renderFriends();
  }
}

// game settings
let selSize = 9;
let selDiff = 1;

function openSinglePlayer() {
  // show difficulty selection popup
  document.getElementById('sp-options').style.display = 'block';
  document.getElementById('mp-options').style.display = 'none';
}

function openMultiplayer() {
  window.location.href = 'multiplayer.html';
}

function setSize(s) {
  selSize = s;
  document.querySelectorAll('#size-row .pill').forEach(p => p.classList.remove('active'));
  event.target.classList.add('active');
}

function setDiff(d) {
  selDiff = d;
  document.querySelectorAll('#diff-row .pill').forEach(p => p.classList.remove('active'));
  event.target.classList.add('active');
}

function startGame() {
  toast('Generating ' + selSize + '×' + selSize + ' puzzle…', 'info');
  setTimeout(() => {
    window.location.href = 'game.html?size=' + selSize + '&diff=' + selDiff;
  }, 700);
}

function joinRoom() {
  const code = document.getElementById('room-code').value.trim();
  if (!code) { toast('Please enter a room code', 'info'); return; }
  toast('Joining room ' + code + '…', 'info');
}

// load past games from database
async function loadRecentGames() {
  const container = document.getElementById('recent-games');
  if (!container) return;
  
  const userId = player.id || player.user_id;
  
  try {
    const response = await fetch(`/api/user/${userId}/history?limit=5`);
    
    if (!response.ok) {
      throw new Error('Failed to load game history');
    }
    
    const data = await response.json();
    const games = data.history || [];
    
    if (games.length === 0) {
      container.innerHTML = "<div style='color:var(--muted);padding:10px;'>No games played yet</div>";
      return;
    }
    
    const diffNames = { 1: 'Easy', 2: 'Medium', 3: 'Hard' };
    
    container.innerHTML = games.map(g => {
      const result = g.completed ? 'win' : 'loss';
      const resultClass = result === 'win' ? 'result-win' : 'result-loss';
      const diffName = diffNames[g.difficulty] || 'Medium';
      
      // format time nicely
      const mins = Math.floor(g.time_seconds / 60);
      const secs = g.time_seconds % 60;
      const timeStr = `${mins}:${String(secs).padStart(2, '0')}`;
      
      return `
        <div class="game-row">
          <div class="game-result ${resultClass}"></div>
          <div class="game-info">
            <div class="game-vs">Solo ${g.board_size}×${g.board_size} <span style="font-size:11px;color:var(--text2)">· ${diffName}</span></div>
            <div class="game-meta">Time: ${timeStr}</div>
          </div>
          <div class="game-score" style="color:${result==='win'?'var(--green)':'var(--danger)'}">${g.score} pts</div>
        </div>
      `;
    }).join('');
  } catch (error) {
    console.error('Error loading recent games:', error);
    container.innerHTML = "<div style='color:var(--muted);padding:10px;'>Failed to load recent games</div>";
  }
}

function renderRecentGames() {
  // kept for backward compatibility
  // now we use loadRecentGames() which gets data from database
  loadRecentGames();
}

// friends management
let pendingRemove    = '';
let pendingChallenge = '';



function renderFriends() {
  const onlineEl  = document.getElementById('online-friends');
  const allEl     = document.getElementById('all-friends');
  const recEl     = document.getElementById('recommendations');
  const pendingEl = document.getElementById('pending-list');
  if (!onlineEl) return;

  loadFriendsList();
  loadRecommendations();
  loadPendingRequests();
}

async function loadFriendsList() {
  const userId = player.id || player.user_id;
  const allEl = document.getElementById('all-friends');
  
  try {
    const response = await fetch(`/api/user/${userId}/friends`);
    if (!response.ok) throw new Error('Failed to load friends');
    
    const data = await response.json();
    const friends = data.friends || [];
    
    if (friends.length === 0) {
      allEl.innerHTML = '';
      return;
    }
    
    const friendRow = (f) => `
      <div class="friend-row">
        <div class="avatar">${f.display_name.charAt(0).toUpperCase()}</div>
        <div class="friend-info">
          <div class="friend-name"><span class="online-dot"></span>${f.display_name}</div>
          <div class="friend-stat">${f.total_wins || 0}W</div>
        </div>
        <div class="friend-actions">
          <button class="btn-sm btn-remove" onclick="removeFriend('${f.display_name}')">Remove</button>
        </div>
      </div>`;
    
    allEl.innerHTML = friends.map(friendRow).join('');
  } catch (error) {
    console.error('Error loading friends:', error);
    allEl.innerHTML = '<div style="color:var(--muted);padding:10px;">Failed to load friends</div>';
  }
}

async function loadRecommendations() {
  const userId = player.id || player.user_id;
  const recEl = document.getElementById('recommendations');
  
  try {
    const response = await fetch(`/api/user/${userId}/recommendations`);
    if (!response.ok) throw new Error('Failed to load recommendations');
    
    const data = await response.json();
    const recommendations = data.recommendations || [];
    
    if (recommendations.length === 0) {
      recEl.innerHTML = '<div style="color:var(--muted);padding:10px;">No recommendations yet. Add more friends!</div>';
      return;
    }
    
    const recRow = (r) => `
      <div class="rec-row">
        <div class="avatar" style="width:38px;height:38px;font-size:16px;background:rgba(232,255,71,0.1);color:var(--accent)">${r.display_name.charAt(0).toUpperCase()}</div>
        <div class="rec-info">
          <div class="rec-name">${r.display_name}</div>
          <div class="rec-meta">${r.total_wins || 0}W</div>
          <div class="mutual-tag">${r.mutual_friends} mutual friend${r.mutual_friends > 1 ? 's' : ''}</div>
        </div>
        <button class="btn-sm btn-add" onclick="addFriend('${r.display_name}')">+ Add</button>
      </div>`;
    
    recEl.innerHTML = recommendations.map(recRow).join('');
  } catch (error) {
    console.error('Error loading recommendations:', error);
    recEl.innerHTML = '<div style="color:var(--muted);padding:10px;">Failed to load recommendations</div>';
  }
}

async function loadPendingRequests() {
  const userId = player.id || player.user_id;
  const pendingEl = document.getElementById('pending-list');
  
  try {
    const response = await fetch(`/api/user/${userId}/pending-requests`);
    if (!response.ok) throw new Error('Failed to load pending requests');
    
    const data = await response.json();
    const requests = data.pending_requests || [];
    
    if (requests.length === 0) {
      pendingEl.innerHTML = '<div style="color:var(--muted);padding:10px;">No pending requests</div>';
      return;
    }
    
    const requestRow = (r) => `
      <div class="friend-row">
        <div class="avatar">${r.display_name.charAt(0).toUpperCase()}</div>
        <div class="friend-info">
          <div class="friend-name">${r.display_name}</div>
          <div class="friend-stat">${r.total_wins || 0}W</div>
        </div>
        <div class="friend-actions">
          <button class="btn-sm btn-challenge" onclick="acceptFriendRequest(${r.user_id})">✓ Accept</button>
          <button class="btn-sm btn-remove" onclick="rejectFriendRequest(${r.user_id})">✗ Reject</button>
        </div>
      </div>`;
    
    pendingEl.innerHTML = requests.map(requestRow).join('');
  } catch (error) {
    console.error('Error loading pending requests:', error);
    pendingEl.innerHTML = '<div style="color:var(--muted);padding:10px;">Failed to load requests</div>';
  }
}

async function acceptFriendRequest(friendId) {
  const userId = player.id || player.user_id;
  
  try {
    const response = await fetch('/api/friends/accept', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        friend_id: friendId
      })
    });
    
    if (!response.ok) throw new Error('Failed to accept request');
    
    toast('Friend request accepted!', 'success');
    loadPendingRequests();
    loadFriendsList();
  } catch (error) {
    console.error('Error accepting request:', error);
    toast('Failed to accept request', 'error');
  }
}

function rejectFriendRequest(friendId) {
  toast('Friend request rejected', 'info');
  loadPendingRequests();
}

function challengeFriend(name) {
  pendingChallenge = name;
  document.getElementById('challenge-name').textContent = name;
  document.getElementById('challenge-modal').classList.add('show');
}
function sendChallenge() {
  closeModal('challenge-modal');
  toast('Challenge sent to ' + pendingChallenge + '!', 'success');
}
function removeFriend(name) {
  pendingRemove = name;
  document.getElementById('remove-name').textContent = name;
  document.getElementById('remove-modal').classList.add('show');
}
function confirmRemove() {
  closeModal('remove-modal');
  toast(pendingRemove + ' removed from friends', 'info');
}

async function addFriend(name) {
  const userId = player.id || player.user_id;
  
  try {
    const response = await fetch('/api/friends/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        friend_username: name
      })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      // Check if it's a duplicate request error
      if (data.detail && data.detail.includes('already exists')) {
        toast('Friend request already sent to ' + name, 'info');
      } else {
        toast('Error: ' + (data.detail || 'Failed to send friend request'), 'error');
      }
      return;
    }
    
    toast('Friend request sent to ' + name + '!', 'success');
    event.target.textContent = 'Sent ✓';
    event.target.disabled = true;
  } catch (error) {
    console.error('Error sending friend request:', error);
    toast('Failed to send friend request', 'error');
  }
}

function searchPlayer() {
  const q = document.getElementById('friend-search').value.trim();
  if (!q) { toast('Enter a username to search', 'info'); return; }
  const box  = document.getElementById('search-results');
  const list = document.getElementById('search-list');
  box.style.display = 'block';
  list.innerHTML = `
    <div class="friend-row">
      <div class="avatar">${q[0].toUpperCase()}</div>
      <div class="friend-info">
        <div class="friend-name">${q}</div>
      </div>
      <button class="btn-sm btn-add" onclick="addFriend('${q}')">+ Add</button>
    </div>`;
}


function renderLeaderboard(data) {
  const el = document.getElementById('lb-list');
  if (!el) {
    console.error('lb-list element not found');
    return;
  }
  
  console.log('renderLeaderboard called with', data.length, 'entries');
  
  if (!data || data.length === 0) {
    el.innerHTML = '<div style="color:var(--muted);padding:20px;text-align:center;">No leaderboard data yet. Play some games!</div>';
    return;
  }
  
  const currentPlayer = player.id || player.user_id;
  console.log('Current player ID:', currentPlayer);
  
  let html = '';
  data.forEach((r, index) => {
    const rank = r.rank_position || index + 1;
    const rankCls = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : '';
    const isMe = r.user_id === currentPlayer || r.username === player.username;
    const displayName = r.display_name || r.name || r.username || 'Unknown';
    const wins = r.total_wins || r.wins || 0;
    const winRate = r.win_rate || r.wr || 0;
    const bestTime = r.best_time || r.best_time_9x9 || null;
    
    // make time look nice
    let timeStr = '—';
    if (bestTime && bestTime > 0) {
      const mins = Math.floor(bestTime / 60);
      const secs = bestTime % 60;
      timeStr = `${mins}:${String(secs).padStart(2, '0')}`;
    }
    
    html += `
    <div class="lb-row ${isMe ? 'me' : ''}">
      <div class="lb-rank ${rankCls}">${rank}</div>
      <div class="lb-avatar">${displayName.charAt(0).toUpperCase()}</div>
      <div class="lb-name">${displayName}${isMe ? ' <span style="font-size:11px;color:var(--accent)">← You</span>' : ''}</div>
      <div class="lb-stat lb-wins">${wins}W</div>
      <div class="lb-stat lb-wr">${Math.round(winRate)}%</div>
    </div>`;
  });
  
  el.innerHTML = html;
  console.log('Leaderboard rendered successfully');
}

async function loadLeaderboard(type = 'global') {
  const el = document.getElementById('lb-list');
  if (!el) {
    console.error('Leaderboard element not found!');
    return;
  }
  
  try {
    let endpoint = '/api/leaderboard/global';
    
    if (type === 'weekly') {
      endpoint = '/api/leaderboard/weekly';
    } else if (type === 'friends') {
      const userId = player.id || player.user_id;
      if (!userId) {
        el.innerHTML = '<div style="color:var(--muted);padding:20px;text-align:center;">Please log in to see friends leaderboard</div>';
        return;
      }
      endpoint = `/api/leaderboard/friends/${userId}`;
    }
    
    console.log('Loading leaderboard from:', endpoint);
    el.innerHTML = '<div style="color:var(--muted);padding:20px;text-align:center;">Loading...</div>';
    
    const response = await fetch(endpoint);
    
    console.log('Response status:', response.status);
    
    if (!response.ok) {
      throw new Error(`Failed to load leaderboard: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Leaderboard data received:', data);
    const leaderboard = data.leaderboard || [];
    console.log('Rendering', leaderboard.length, 'entries');
    
    if (leaderboard.length === 0) {
      el.innerHTML = '<div style="color:var(--muted);padding:20px;text-align:center;">No players yet. Play some games!</div>';
      return;
    }
    
    renderLeaderboard(leaderboard);
  } catch (error) {
    console.error('Error loading leaderboard:', error);
    el.innerHTML = '<div style="color:var(--danger);padding:20px;text-align:center;">Failed to load leaderboard: ' + error.message + '</div>';
  }
}

function setLbTab(tab, btn) {
  document.querySelectorAll('.lb-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadLeaderboard(tab);
  toast('Loading ' + tab + ' leaderboard...', 'info');
}

// popup helpers
function closeModal(id) {
  document.getElementById(id).classList.remove('show');
}
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.overlay').forEach(o => {
    o.addEventListener('click', function(e) {
      if (e.target === this) this.classList.remove('show');
    });
  });
});

// show notification message
let toastTimer;
function toast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className   = 'toast show ' + (type || 'info');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.classList.remove('show'); }, 2500);
}

// log out user
function doLogout() {
  localStorage.removeItem('player');
  window.location.href = 'index.html';
}

// start the page
document.addEventListener('DOMContentLoaded', () => {
  initHeader();
  renderRecentGames();
  // leaderboard loads when user clicks the tab
});


// multiplayer functions

function goToMultiplayerLobby() {
  window.location.href = 'multiplayer.html';
}

function loadMultiplayerStats() {
  const userData = localStorage.getItem('user');
  if (!userData) return;
  
  const user = JSON.parse(userData);
  
  // get multiplayer stats from server
  fetch(`/api/multiplayer/stats/${user.user_id}`)
    .then(r => r.json())
    .then(data => {
      document.getElementById('mp-stat-wins').textContent = data.multiplayer_wins || 0;
      document.getElementById('mp-stat-losses').textContent = data.multiplayer_losses || 0;
      document.getElementById('mp-stat-wr').textContent = (data.win_rate || 0).toFixed(1) + '%';
      document.getElementById('mp-stat-best').textContent = data.best_score || 0;
    })
    .catch(err => console.error('Error loading multiplayer stats:', err));
}

function loadMultiplayerHistory() {
  const userData = localStorage.getItem('user');
  if (!userData) return;
  
  const user = JSON.parse(userData);
  
  // get multiplayer history from server
  fetch(`/api/multiplayer/history/${user.user_id}`)
    .then(r => r.json())
    .then(data => {
      const container = document.getElementById('mp-recent-games');
      if (!data.history || data.history.length === 0) {
        container.innerHTML = '<div style="color:var(--text2); padding:16px; text-align:center;">No multiplayer games yet</div>';
        return;
      }
      
      container.innerHTML = data.history.map(game => `
        <div class="game-item" style="padding:12px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:600;">${game.opponent.username}</div>
            <div style="font-size:12px; color:var(--text2);">${new Date(game.played_at).toLocaleDateString()}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-weight:600; color:${game.result === 'win' ? 'var(--green)' : 'var(--danger)'};">${game.result.toUpperCase()}</div>
            <div style="font-size:12px; color:var(--text2);">${game.your_score} vs ${game.opponent_score}</div>
          </div>
        </div>
      `).join('');
    })
    .catch(err => console.error('Error loading multiplayer history:', err));
}

function loadMultiplayerLeaderboard() {
  // get multiplayer leaderboard from server
  fetch('/api/multiplayer/leaderboard')
    .then(r => r.json())
    .then(data => {
      const container = document.getElementById('mp-lb-list');
      if (!data.leaderboard || data.leaderboard.length === 0) {
        container.innerHTML = '<div style="color:var(--text2); padding:16px; text-align:center;">No leaderboard data yet</div>';
        return;
      }
      
      container.innerHTML = data.leaderboard.map((player, idx) => `
        <div class="lb-row" style="display:grid; grid-template-columns:32px 1fr 70px 70px; gap:12px; padding:12px; border-bottom:1px solid var(--border); align-items:center;">
          <div style="text-align:center; font-weight:600; color:var(--text2);">${idx + 1}</div>
          <div style="font-weight:600;">${player.username}</div>
          <div style="text-align:right; color:var(--accent);">${player.wins}</div>
          <div style="text-align:right; color:var(--green);">${player.best_score}</div>
        </div>
      `).join('');
    })
    .catch(err => console.error('Error loading multiplayer leaderboard:', err));
}
