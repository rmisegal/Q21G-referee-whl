-- Area: RLGM
-- PRD: docs/prd-rlgm.md
-- RLGM Database Schema
-- ====================
-- Tables for tracking season lifecycle, assignments, and broadcasts.

-- Seasons table: tracks referee's participation in seasons
CREATE TABLE IF NOT EXISTS referee_seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id TEXT NOT NULL UNIQUE,
    league_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    -- Status: pending, registered, active, completed, rejected
    registered_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assignments table: stores match assignments for each round
CREATE TABLE IF NOT EXISTS round_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    round_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    player1_id TEXT NOT NULL,
    player1_email TEXT NOT NULL,
    player2_id TEXT NOT NULL,
    player2_email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    -- Status: pending, in_progress, completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(season_id, round_number, match_id)
);

-- Match results table: stores completed game results
CREATE TABLE IF NOT EXISTS match_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id TEXT NOT NULL,
    round_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    winner_id TEXT,
    is_draw INTEGER NOT NULL DEFAULT 0,
    player1_id TEXT NOT NULL,
    player1_score INTEGER NOT NULL,
    player2_id TEXT NOT NULL,
    player2_score INTEGER NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reported_at TIMESTAMP,
    UNIQUE(season_id, match_id)
);

-- Broadcasts received table: for idempotency checking
CREATE TABLE IF NOT EXISTS broadcasts_received (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    broadcast_id TEXT NOT NULL UNIQUE,
    message_type TEXT NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed INTEGER NOT NULL DEFAULT 1
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_assignments_season
    ON round_assignments(season_id);
CREATE INDEX IF NOT EXISTS idx_assignments_round
    ON round_assignments(season_id, round_number);
CREATE INDEX IF NOT EXISTS idx_results_season
    ON match_results(season_id);
CREATE INDEX IF NOT EXISTS idx_broadcasts_type
    ON broadcasts_received(message_type);
