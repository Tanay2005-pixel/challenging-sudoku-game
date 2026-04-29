// sudoku duel multiplayer results code

let currentUser = null;
let gameId = null;
let resultsData = null;

// initialize results page
document.addEventListener('DOMContentLoaded', function() {
  loadUserInfo();
  loadResults();
});

// get player info
function loadUserInfo() {
  // Try both 'user' and 'player' keys for compatibility
  let userData = localStorage.getItem('user');
  if (!userData) {
    userData = localStorage.getItem('player');
  }
  
  if (userData) {
    currentUser = JSON.parse(userData);
    // Normalize user_id field
    if (!currentUser.user_id && currentUser.id) {
      currentUser.user_id = currentUser.id;
    }
    document.getElementById('hdr-name').textContent = currentUser.username || 'Player';
    document.getElementById('hdr-wins').textContent = (currentUser.wins || 0) + 'W';
  }
}

// get game results
function loadResults() {
  gameId = sessionStorage.getItem('multiplayerGameId');
  
  if (!gameId) {
    toast('Game not found', 'error');
    setTimeout(() => window.location.href = 'dashboard.html', 1500);
    return;
  }
  
  // Fetch results from API
  fetch(`/api/multiplayer/game/${gameId}/results`)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        toast(data.error, 'error');
        return;
      }
      
      resultsData = data;
      displayResults(data);
    })
    .catch(err => {
      console.error('Error loading results:', err);
      toast('Failed to load results', 'error');
    });
}

// show results on screen
function displayResults(data) {
  const winnerId = data.winner_id;
  const isWinner = currentUser && currentUser.user_id === winnerId;
  
  // Find your player data and opponent data
  let yourData = null;
  let opponentData = null;
  
  for (let player of data.players) {
    if (currentUser && player.user_id === currentUser.user_id) {
      yourData = player;
    } else {
      opponentData = player;
    }
  }
  
  if (!yourData) {
    toast('Invalid results data', 'error');
    return;
  }
  
  // see if opponent done the game
  const opponentCompleted = opponentData && opponentData.completed;
  
  // Update winner announcement
  if (isWinner) {
    document.getElementById('winner-icon').textContent = '🏆';
    document.getElementById('winner-title').textContent = 'YOU WIN!';
    document.getElementById('winner-subtitle').textContent = 'Congratulations on your victory!';
  } else if (opponentCompleted) {
    document.getElementById('winner-icon').textContent = '😢';
    document.getElementById('winner-title').textContent = 'YOU LOST';
    document.getElementById('winner-subtitle').textContent = 'Better luck next time!';
  } else {
    document.getElementById('winner-icon').textContent = '🏆';
    document.getElementById('winner-title').textContent = 'YOU WIN!';
    document.getElementById('winner-subtitle').textContent = 'Opponent did not complete the game!';
  }
  
  // Your results
  document.getElementById('your-name').textContent = currentUser.username || 'You';
  document.getElementById('your-badge').textContent = isWinner ? 'WINNER' : 'RUNNER-UP';
  document.getElementById('your-badge').className = 'results-badge ' + (isWinner ? 'winner' : 'loser');
  document.getElementById('your-final-score').textContent = yourData.score || 0;
  document.getElementById('your-final-time').textContent = formatTime(yourData.time_seconds || 0);
  document.getElementById('your-final-errors').textContent = yourData.errors_made || 0;
  document.getElementById('your-final-hints').textContent = yourData.hints_used || 0;
  
  // Opponent results - show "Did not complete" if they didn't finish
  if (opponentData) {
    document.getElementById('opponent-name').textContent = opponentData.username || 'Opponent';
    
    if (opponentCompleted) {
      document.getElementById('opponent-badge').textContent = isWinner ? 'RUNNER-UP' : 'WINNER';
      document.getElementById('opponent-badge').className = 'results-badge ' + (isWinner ? 'loser' : 'winner');
      document.getElementById('opponent-final-score').textContent = opponentData.score || 0;
      document.getElementById('opponent-final-time').textContent = formatTime(opponentData.time_seconds || 0);
      document.getElementById('opponent-final-errors').textContent = opponentData.errors_made || 0;
      document.getElementById('opponent-final-hints').textContent = opponentData.hints_used || 0;
    } else {
      document.getElementById('opponent-badge').textContent = 'DID NOT FINISH';
      document.getElementById('opponent-badge').className = 'results-badge loser';
      document.getElementById('opponent-final-score').textContent = '-';
      document.getElementById('opponent-final-time').textContent = '-';
      document.getElementById('opponent-final-errors').textContent = '-';
      document.getElementById('opponent-final-hints').textContent = '-';
    }
  } else {
    document.getElementById('opponent-name').textContent = 'No Opponent';
    document.getElementById('opponent-badge').textContent = 'N/A';
    document.getElementById('opponent-badge').className = 'results-badge loser';
    document.getElementById('opponent-final-score').textContent = '-';
    document.getElementById('opponent-final-time').textContent = '-';
    document.getElementById('opponent-final-errors').textContent = '-';
    document.getElementById('opponent-final-hints').textContent = '-';
  }
  
  // Comparison details - only show if opponent completed
  if (opponentCompleted) {
    const scoreDiff = yourData.score - opponentData.score;
    const timeDiff = opponentData.time_seconds - yourData.time_seconds;
    const errorDiff = opponentData.errors_made - yourData.errors_made;
    
    document.getElementById('comp-your-score').textContent = yourData.score || 0;
    document.getElementById('comp-opponent-score').textContent = opponentData.score || 0;
    document.getElementById('comp-score-diff').textContent = (scoreDiff > 0 ? '+' : '') + scoreDiff;
    
    document.getElementById('comp-your-time').textContent = formatTime(yourData.time_seconds || 0);
    document.getElementById('comp-opponent-time').textContent = formatTime(opponentData.time_seconds || 0);
    
    const timeDiffEl = document.getElementById('comp-time-diff');
    if (timeDiff > 0) {
      timeDiffEl.textContent = formatTime(timeDiff) + ' faster';
      timeDiffEl.className = 'comparison-diff faster';
    } else {
      timeDiffEl.textContent = formatTime(Math.abs(timeDiff)) + ' slower';
      timeDiffEl.className = 'comparison-diff';
    }
    
    document.getElementById('comp-your-errors').textContent = yourData.errors_made || 0;
    document.getElementById('comp-opponent-errors').textContent = opponentData.errors_made || 0;
    document.getElementById('comp-errors-diff').textContent = (errorDiff > 0 ? '+' : '') + errorDiff;
  } else {
    // Show only your stats if opponent didn't complete
    document.getElementById('comp-your-score').textContent = yourData.score || 0;
    document.getElementById('comp-opponent-score').textContent = '-';
    document.getElementById('comp-score-diff').textContent = 'N/A';
    
    document.getElementById('comp-your-time').textContent = formatTime(yourData.time_seconds || 0);
    document.getElementById('comp-opponent-time').textContent = '-';
    document.getElementById('comp-time-diff').textContent = 'N/A';
    
    document.getElementById('comp-your-errors').textContent = yourData.errors_made || 0;
    document.getElementById('comp-opponent-errors').textContent = '-';
    document.getElementById('comp-errors-diff').textContent = 'N/A';
  }
}

// format time display
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
}

// start new game
function playAgain() {
  window.location.href = 'multiplayer.html';
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
