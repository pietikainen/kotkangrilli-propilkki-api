"""
Player session endpoints (join/leave tracking from playlog.txt)
IP addresses are NOT exposed via API for privacy
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.database import get_db
from app.models import (
    PlayerSession, 
    PlayerSessionStats, 
    TopPlayer, 
    DailyActivity, 
    HourlyActivity,
    PlayerEfficiency
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.get("/recent", response_model=List[PlayerSession])
def get_recent_sessions(limit: int = Query(default=20, ge=1, le=100)):
    """
    Get most recent player sessions (no IP addresses)
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                id, player_name, joined_at, left_at, 
                session_duration_seconds, player_version
            FROM player_sessions
            ORDER BY joined_at DESC
            LIMIT %s
        """
        
        cur.execute(query, [limit])
        results = cur.fetchall()
        return results

@router.get("/active", response_model=List[PlayerSession])
def get_active_sessions():
    """
    Get currently active sessions (players who haven't left yet)
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                id, player_name, joined_at, left_at, 
                session_duration_seconds, player_version
            FROM player_sessions
            WHERE left_at IS NULL
            ORDER BY joined_at DESC
        """
        
        cur.execute(query)
        results = cur.fetchall()
        return results

@router.get("/player/{player_name}", response_model=List[PlayerSession])
def get_player_sessions(
    player_name: str,
    limit: int = Query(default=50, ge=1, le=200)
):
    """
    Get session history for a specific player
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                id, player_name, joined_at, left_at, 
                session_duration_seconds, player_version
            FROM player_sessions
            WHERE player_name = %s
            ORDER BY joined_at DESC
            LIMIT %s
        """
        
        cur.execute(query, [player_name, limit])
        results = cur.fetchall()
        
        if not results:
            raise HTTPException(status_code=404, detail=f"No sessions found for player: {player_name}")
        
        return results

@router.get("/stats/{player_name}", response_model=PlayerSessionStats)
def get_player_session_stats(player_name: str):
    """
    Get aggregated session statistics for a player
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                player_name,
                COUNT(*) as total_sessions,
                COALESCE(SUM(session_duration_seconds), 0) as total_playtime_seconds,
                ROUND(COALESCE(SUM(session_duration_seconds), 0) / 3600.0, 2) as total_playtime_hours,
                AVG(session_duration_seconds)::int as avg_session_duration_seconds,
                MIN(joined_at) as first_seen,
                MAX(joined_at) as last_seen
            FROM player_sessions
            WHERE player_name = %s
            GROUP BY player_name
        """
        
        cur.execute(query, [player_name])
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"No sessions found for player: {player_name}")
        
        return result

@router.get("/top-players", response_model=List[TopPlayer])
def get_top_players(limit: int = Query(default=10, ge=1, le=50)):
    """
    Get players ranked by total playtime
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                player_name,
                COUNT(*) as total_sessions,
                ROUND(COALESCE(SUM(session_duration_seconds), 0) / 3600.0, 2) as total_playtime_hours,
                ROUND(AVG(session_duration_seconds) / 3600.0, 2) as avg_session_hours
            FROM player_sessions
            WHERE session_duration_seconds IS NOT NULL
            GROUP BY player_name
            ORDER BY total_playtime_hours DESC
            LIMIT %s
        """
        
        cur.execute(query, [limit])
        results = cur.fetchall()
        return results

@router.get("/daily-activity", response_model=List[DailyActivity])
def get_daily_activity(days: int = Query(default=30, ge=1, le=365)):
    """
    Get daily activity statistics (sessions and unique players per day)
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                DATE(joined_at) as date,
                COUNT(*) as total_sessions,
                COUNT(DISTINCT player_name) as unique_players,
                ROUND(COALESCE(SUM(session_duration_seconds), 0) / 3600.0, 2) as total_playtime_hours
            FROM player_sessions
            WHERE joined_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(joined_at)
            ORDER BY date DESC
        """
        
        cur.execute(query, [days])
        results = cur.fetchall()
        return results

@router.get("/hourly-activity", response_model=List[HourlyActivity])
def get_hourly_activity():
    """
    Get activity by hour of day (when do people play most?)
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                EXTRACT(HOUR FROM joined_at)::int as hour,
                COUNT(*) as total_sessions,
                ROUND(AVG(session_duration_seconds) / 60.0, 1) as avg_session_duration_minutes
            FROM player_sessions
            WHERE session_duration_seconds IS NOT NULL
            GROUP BY EXTRACT(HOUR FROM joined_at)
            ORDER BY hour
        """
        
        cur.execute(query)
        results = cur.fetchall()
        return results

@router.get("/efficiency/{player_name}", response_model=PlayerEfficiency)
def get_player_efficiency(player_name: str):
    """
    Get player efficiency metrics (catches per hour, grams per hour)
    Combines session data with catch data
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            WITH session_stats AS (
                SELECT 
                    player_name,
                    COALESCE(SUM(session_duration_seconds), 0) / 3600.0 as total_playtime_hours
                FROM player_sessions
                WHERE player_name = %s
                GROUP BY player_name
            ),
            catch_stats AS (
                SELECT 
                    player_name,
                    SUM(fish_count) as total_fish,
                    SUM(total_weight_grams) as total_weight_grams,
                    COUNT(DISTINCT timestamp) as competitions_count
                FROM competition_catches
                WHERE player_name = %s AND disqualified = false
                GROUP BY player_name
            )
            SELECT 
                COALESCE(s.player_name, c.player_name) as player_name,
                ROUND(COALESCE(s.total_playtime_hours, 0), 2) as total_playtime_hours,
                COALESCE(c.total_fish, 0) as total_fish,
                COALESCE(c.total_weight_grams, 0) as total_weight_grams,
                ROUND(
                    CASE 
                        WHEN s.total_playtime_hours > 0 THEN c.total_fish / s.total_playtime_hours
                        ELSE 0 
                    END, 
                2) as fish_per_hour,
                ROUND(
                    CASE 
                        WHEN s.total_playtime_hours > 0 THEN c.total_weight_grams / s.total_playtime_hours
                        ELSE 0 
                    END, 
                2) as grams_per_hour,
                COALESCE(c.competitions_count, 0) as competitions_count
            FROM session_stats s
            FULL OUTER JOIN catch_stats c ON s.player_name = c.player_name
        """
        
        cur.execute(query, [player_name, player_name])
        result = cur.fetchone()
        
        if not result or (result['total_playtime_hours'] == 0 and result['total_fish'] == 0):
            raise HTTPException(status_code=404, detail=f"No data found for player: {player_name}")
        
        return result

@router.get("/activity-vs-catches", response_model=List[PlayerEfficiency])
def get_all_players_efficiency(limit: int = Query(default=20, ge=1, le=100)):
    """
    Get efficiency metrics for all players (sorted by grams per hour)
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            WITH session_stats AS (
                SELECT 
                    player_name,
                    COALESCE(SUM(session_duration_seconds), 0) / 3600.0 as total_playtime_hours
                FROM player_sessions
                GROUP BY player_name
            ),
            catch_stats AS (
                SELECT 
                    player_name,
                    SUM(fish_count) as total_fish,
                    SUM(total_weight_grams) as total_weight_grams,
                    COUNT(DISTINCT timestamp) as competitions_count
                FROM competition_catches
                WHERE disqualified = false
                GROUP BY player_name
            )
            SELECT 
                COALESCE(s.player_name, c.player_name) as player_name,
                ROUND(COALESCE(s.total_playtime_hours, 0), 2) as total_playtime_hours,
                COALESCE(c.total_fish, 0) as total_fish,
                COALESCE(c.total_weight_grams, 0) as total_weight_grams,
                ROUND(
                    CASE 
                        WHEN s.total_playtime_hours > 0 THEN c.total_fish / s.total_playtime_hours
                        ELSE 0 
                    END, 
                2) as fish_per_hour,
                ROUND(
                    CASE 
                        WHEN s.total_playtime_hours > 0 THEN c.total_weight_grams / s.total_playtime_hours
                        ELSE 0 
                    END, 
                2) as grams_per_hour,
                COALESCE(c.competitions_count, 0) as competitions_count
            FROM session_stats s
            FULL OUTER JOIN catch_stats c ON s.player_name = c.player_name
            WHERE s.total_playtime_hours > 0 OR c.total_fish > 0
            ORDER BY grams_per_hour DESC
            LIMIT %s
        """
        
        cur.execute(query, [limit])
        results = cur.fetchall()
        return results
