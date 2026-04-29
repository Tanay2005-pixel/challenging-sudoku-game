
CREATE DATABASE IF NOT EXISTS sudoku_duel;
USE sudoku_duel;

-- store player accounts
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- save all completed games
CREATE TABLE IF NOT EXISTS game_history (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    board_size INT NOT NULL,
    difficulty INT NOT NULL,
    time_seconds INT NOT NULL,
    hints_used INT DEFAULT 0,
    errors_made INT DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    score INT DEFAULT 0,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_completed (completed),
    INDEX idx_score (score DESC),
    INDEX idx_played_at (played_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- track player performance
CREATE TABLE IF NOT EXISTS user_stats (
    stat_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    total_games INT DEFAULT 0,
    total_wins INT DEFAULT 0,
    total_losses INT DEFAULT 0,
    best_time_4x4 INT NULL,
    best_time_9x9 INT NULL,
    best_time_16x16 INT NULL,
    total_score INT DEFAULT 0,
    average_score DECIMAL(10,2) DEFAULT 0.00,
    win_rate DECIMAL(5,2) DEFAULT 0.00,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_total_score (total_score DESC),
    INDEX idx_win_rate (win_rate DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- manage friend connections
CREATE TABLE IF NOT EXISTS friendships (
    friendship_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    friend_id INT NOT NULL,
    status ENUM('pending', 'accepted', 'blocked') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (friend_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_friendship (user_id, friend_id),
    INDEX idx_user_id (user_id),
    INDEX idx_friend_id (friend_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- store multiplayer game rooms
CREATE TABLE IF NOT EXISTS multiplayer_games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    room_code VARCHAR(6) UNIQUE NOT NULL,
    puzzle_id INT,
    puzzle_data LONGTEXT NOT NULL,
    solution_data LONGTEXT NOT NULL,
    board_size INT NOT NULL,
    difficulty INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    finished_at TIMESTAMP NULL,
    status ENUM('waiting', 'in_progress', 'paused', 'completed', 'cancelled') DEFAULT 'waiting',
    winner_id INT NULL,
    INDEX idx_room_code (room_code),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (winner_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- track each player in multiplayer games
CREATE TABLE IF NOT EXISTS multiplayer_players (
    player_id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    user_id INT NOT NULL,
    board_state LONGTEXT NOT NULL,
    score INT DEFAULT 0,
    time_seconds INT DEFAULT 0,
    hints_used INT DEFAULT 0,
    errors_made INT DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_move_at TIMESTAMP NULL,
    disconnected_at TIMESTAMP NULL,
    FOREIGN KEY (game_id) REFERENCES multiplayer_games(game_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_game_player (game_id, user_id),
    INDEX idx_game_id (game_id),
    INDEX idx_user_id (user_id),
    INDEX idx_completed (completed),
    INDEX idx_disconnected_at (disconnected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- save multiplayer game results
CREATE TABLE IF NOT EXISTS multiplayer_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    player1_id INT NOT NULL,
    player2_id INT NOT NULL,
    winner_id INT NOT NULL,
    player1_score INT NOT NULL,
    player2_score INT NOT NULL,
    player1_time INT NOT NULL,
    player2_time INT NOT NULL,
    board_size INT NOT NULL,
    difficulty INT NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES multiplayer_games(game_id) ON DELETE CASCADE,
    FOREIGN KEY (player1_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (player2_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (winner_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_player1_id (player1_id),
    INDEX idx_player2_id (player2_id),
    INDEX idx_winner_id (winner_id),
    INDEX idx_played_at (played_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



ALTER TABLE game_history ADD COLUMN IF NOT EXISTS multiplayer_game_id INT NULL;
ALTER TABLE game_history ADD COLUMN IF NOT EXISTS opponent_id INT NULL;
ALTER TABLE game_history ADD COLUMN IF NOT EXISTS is_multiplayer BOOLEAN DEFAULT FALSE;

ALTER TABLE game_history ADD FOREIGN KEY IF NOT EXISTS fk_multiplayer_game_id (multiplayer_game_id) REFERENCES multiplayer_games(game_id) ON DELETE SET NULL;
ALTER TABLE game_history ADD FOREIGN KEY IF NOT EXISTS fk_opponent_id (opponent_id) REFERENCES users(user_id) ON DELETE SET NULL;

ALTER TABLE game_history ADD INDEX IF NOT EXISTS idx_is_multiplayer (is_multiplayer);


-- show top players overall
CREATE OR REPLACE VIEW leaderboard_global AS
SELECT 
    u.user_id,
    u.username,
    u.display_name,
    us.total_games,
    us.total_wins,
    us.total_losses,
    us.win_rate,
    us.total_score,
    us.average_score,
    us.best_time_9x9 as best_time,
    RANK() OVER (ORDER BY us.total_score DESC, us.win_rate DESC) as rank_position
FROM users u
INNER JOIN user_stats us ON u.user_id = us.user_id
WHERE u.is_active = TRUE AND us.total_games > 0
ORDER BY us.total_score DESC, us.win_rate DESC
LIMIT 100;

-- show top players this week
CREATE OR REPLACE VIEW leaderboard_weekly AS
SELECT 
    u.user_id,
    u.username,
    u.display_name,
    COUNT(gh.game_id) as games_played,
    SUM(CASE WHEN gh.completed = TRUE THEN 1 ELSE 0 END) as wins,
    SUM(gh.score) as total_score,
    AVG(gh.score) as average_score,
    MIN(gh.time_seconds) as best_time,
    RANK() OVER (ORDER BY SUM(gh.score) DESC) as rank_position
FROM users u
INNER JOIN game_history gh ON u.user_id = gh.user_id
WHERE gh.played_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    AND u.is_active = TRUE
GROUP BY u.user_id, u.username, u.display_name
ORDER BY total_score DESC
LIMIT 100;


DELIMITER //

-- update player stats after finishing a game
CREATE PROCEDURE update_user_stats(
    IN p_user_id INT,
    IN p_board_size INT,
    IN p_time_seconds INT,
    IN p_completed BOOLEAN,
    IN p_score INT
)
BEGIN
    DECLARE v_total_games INT;
    DECLARE v_total_wins INT;
    DECLARE v_total_score INT;
    DECLARE v_win_rate DECIMAL(5,2);
    DECLARE v_avg_score DECIMAL(10,2);
    
    -- create stats row if player is new
    INSERT INTO user_stats (user_id, total_games, total_wins, total_losses, total_score)
    VALUES (p_user_id, 0, 0, 0, 0)
    ON DUPLICATE KEY UPDATE user_id = user_id;
    
    -- add win or loss to player record
    IF p_completed THEN
        UPDATE user_stats 
        SET total_games = total_games + 1,
            total_wins = total_wins + 1,
            total_score = total_score + p_score
        WHERE user_id = p_user_id;
    ELSE
        UPDATE user_stats 
        SET total_games = total_games + 1,
            total_losses = total_losses + 1
        WHERE user_id = p_user_id;
    END IF;
    
    -- save fastest time for each puzzle size
    IF p_completed THEN
        CASE p_board_size
            WHEN 4 THEN
                UPDATE user_stats 
                SET best_time_4x4 = LEAST(COALESCE(best_time_4x4, 999999), p_time_seconds)
                WHERE user_id = p_user_id;
            WHEN 9 THEN
                UPDATE user_stats 
                SET best_time_9x9 = LEAST(COALESCE(best_time_9x9, 999999), p_time_seconds)
                WHERE user_id = p_user_id;
            WHEN 16 THEN
                UPDATE user_stats 
                SET best_time_16x16 = LEAST(COALESCE(best_time_16x16, 999999), p_time_seconds)
                WHERE user_id = p_user_id;
        END CASE;
    END IF;
    
    -- calculate win percentage and average score
    SELECT total_games, total_wins, total_score
    INTO v_total_games, v_total_wins, v_total_score
    FROM user_stats
    WHERE user_id = p_user_id;
    
    SET v_win_rate = IF(v_total_games > 0, (v_total_wins / v_total_games) * 100, 0);
    SET v_avg_score = IF(v_total_games > 0, v_total_score / v_total_games, 0);
    
    UPDATE user_stats 
    SET win_rate = v_win_rate,
        average_score = v_avg_score
    WHERE user_id = p_user_id;
END //

-- update player stats after multiplayer game
CREATE PROCEDURE update_multiplayer_stats(
    IN p_user_id INT,
    IN p_is_winner BOOLEAN,
    IN p_score INT
)
BEGIN
    -- create stats row if player is new
    INSERT INTO user_stats (user_id, total_games, total_wins, total_losses, total_score)
    VALUES (p_user_id, 0, 0, 0, 0)
    ON DUPLICATE KEY UPDATE user_id = user_id;
    
    -- add win or loss to player record
    IF p_is_winner THEN
        UPDATE user_stats 
        SET total_games = total_games + 1,
            total_wins = total_wins + 1,
            total_score = total_score + p_score
        WHERE user_id = p_user_id;
    ELSE
        UPDATE user_stats 
        SET total_games = total_games + 1,
            total_losses = total_losses + 1,
            total_score = total_score + p_score
        WHERE user_id = p_user_id;
    END IF;
    
    -- recalculate win percentage and average score
    UPDATE user_stats 
    SET win_rate = IF(total_games > 0, (total_wins / total_games) * 100, 0),
        average_score = IF(total_games > 0, total_score / total_games, 0)
    WHERE user_id = p_user_id;
END //

DELIMITER ;

-- sample test data
-- test users with password password123
INSERT INTO users (username, display_name, password_hash) VALUES
('john_doe', 'John Doe', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3'),
('jane_smith', 'Jane Smith', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3'),
('mike_wilson', 'Mike Wilson', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3');

-- sample game records
INSERT INTO game_history (user_id, board_size, difficulty, time_seconds, hints_used, errors_made, completed, score) VALUES
(1, 9, 1, 180, 2, 1, TRUE, 850),
(1, 9, 2, 300, 3, 2, TRUE, 720),
(2, 9, 1, 150, 1, 0, TRUE, 920),
(2, 9, 3, 450, 5, 3, TRUE, 650),
(3, 9, 2, 240, 2, 1, TRUE, 800);

-- create stats for test users
INSERT INTO user_stats (user_id) VALUES (1), (2), (3);

-- calculate stats for test games
CALL update_user_stats(1, 9, 180, TRUE, 850);
CALL update_user_stats(1, 9, 300, TRUE, 720);
CALL update_user_stats(2, 9, 150, TRUE, 920);
CALL update_user_stats(2, 9, 450, TRUE, 650);
CALL update_user_stats(3, 9, 240, TRUE, 800);

-- sample multiplayer test data
-- test multiplayer games
INSERT INTO multiplayer_games (room_code, puzzle_data, solution_data, board_size, difficulty, status, winner_id, started_at, finished_at) VALUES
('ABC123', '[0,0,3,0,2,0,6,0,0,9,0,0,3,0,5,0,0,1,0,0,1,8,0,6,4,0,0,0,0,8,1,0,2,9,0,0,7,0,0,0,0,0,0,0,8,0,0,6,7,0,4,2,0,0,0,0,2,6,0,9,5,0,0,8,0,0,4,0,7,0,0,6,0,0,0,0,1,0,2,0,0]', '[1,7,3,9,2,4,6,8,5,9,2,4,3,6,5,7,3,1,5,8,1,8,7,6,4,9,2,4,3,8,1,5,2,9,6,7,7,6,9,2,4,3,5,1,8,2,1,6,7,8,4,2,3,9,3,9,2,6,3,9,5,7,1,8,5,7,4,9,7,1,3,6,6,4,5,5,1,8,2,9,3]', 9, 2, 'completed', 1, '2024-01-15 10:30:00', '2024-01-15 10:45:00'),
('XYZ789', '[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]', '[1,2,3,4,5,6,7,8,9,4,5,6,7,8,9,1,2,3,7,8,9,1,2,3,4,5,6,2,3,4,5,6,7,8,9,1,5,6,7,8,9,1,2,3,4,8,9,1,2,3,4,5,6,7,3,4,5,6,7,8,9,1,2,6,7,8,9,1,2,3,4,5,9,1,2,3,4,5,6,7,8]', 9, 1, 'completed', 2, '2024-01-15 11:00:00', '2024-01-15 11:12:00');

-- test player data for multiplayer games
INSERT INTO multiplayer_players (game_id, user_id, board_state, score, time_seconds, hints_used, errors_made, completed, completed_at, last_move_at) VALUES
(1, 1, '[1,7,3,9,2,4,6,8,5,9,2,4,3,6,5,7,3,1,5,8,1,8,7,6,4,9,2,4,3,8,1,5,2,9,6,7,7,6,9,2,4,3,5,1,8,2,1,6,7,8,4,2,3,9,3,9,2,6,3,9,5,7,1,8,5,7,4,9,7,1,3,6,6,4,5,5,1,8,2,9,3]', 850, 900, 2, 1, TRUE, '2024-01-15 10:45:00', '2024-01-15 10:44:55'),
(1, 2, '[1,7,3,9,2,4,6,8,5,9,2,4,3,6,5,7,3,1,5,8,1,8,7,6,4,9,2,4,3,8,1,5,2,9,6,7,7,6,9,2,4,3,5,1,8,2,1,6,7,8,4,2,3,9,3,9,2,6,3,9,5,7,1,8,5,7,4,9,7,1,3,6,6,4,5,5,1,8,2,9,3]', 720, 1050, 3, 2, TRUE, '2024-01-15 10:47:30', '2024-01-15 10:47:25'),
(2, 2, '[1,2,3,4,5,6,7,8,9,4,5,6,7,8,9,1,2,3,7,8,9,1,2,3,4,5,6,2,3,4,5,6,7,8,9,1,5,6,7,8,9,1,2,3,4,8,9,1,2,3,4,5,6,7,3,4,5,6,7,8,9,1,2,6,7,8,9,1,2,3,4,5,9,1,2,3,4,5,6,7,8]', 920, 720, 1, 0, TRUE, '2024-01-15 11:12:00', '2024-01-15 11:11:55'),
(2, 3, '[1,2,3,4,5,6,7,8,9,4,5,6,7,8,9,1,2,3,7,8,9,1,2,3,4,5,6,2,3,4,5,6,7,8,9,1,5,6,7,8,9,1,2,3,4,8,9,1,2,3,4,5,6,7,3,4,5,6,7,8,9,1,2,6,7,8,9,1,2,3,4,5,9,1,2,3,4,5,6,7,8]', 850, 840, 2, 1, TRUE, '2024-01-15 11:14:00', '2024-01-15 11:13:55');

-- test multiplayer results
INSERT INTO multiplayer_history (game_id, player1_id, player2_id, winner_id, player1_score, player2_score, player1_time, player2_time, board_size, difficulty) VALUES
(1, 1, 2, 1, 850, 720, 900, 1050, 9, 2),
(2, 2, 3, 2, 920, 850, 720, 840, 9, 1);

-- useful queries for checking data
-- see all users
-- SELECT * FROM users;

-- see player stats
-- SELECT * FROM user_stats;

-- see overall leaderboard
-- SELECT * FROM leaderboard_global;

-- see this week leaderboard
-- SELECT * FROM leaderboard_weekly;

-- see game history
-- SELECT * FROM game_history ORDER BY played_at DESC;
