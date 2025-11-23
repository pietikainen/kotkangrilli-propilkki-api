"""
Statistics and leaderboard endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.database import get_db
from app.models import LeaderboardEntry, SpeciesStats, LakeStats, CompetitionCatch

router = APIRouter(prefix="/api/stats", tags=["statistics"])

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=100),
    lake: Optional[str] = None
):
    """
    Get top players leaderboard
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        where_clause = "WHERE disqualified = false"
        if lake:
            where_clause += f" AND lake = %s"
        
        query = f"""
            SELECT 
                player_name,
                SUM(fish_count) as total_fish,
                SUM(total_weight_grams) as total_weight_grams,
                COUNT(DISTINCT timestamp) as competitions_count,
                MAX(player_reported_biggest) as biggest_catch
            FROM competition_catches
            {where_clause}
            GROUP BY player_name
            ORDER BY total_weight_grams DESC
            LIMIT %s
        """
        
        params = [lake, limit] if lake else [limit]
        cur.execute(query, params)
        
        results = cur.fetchall()
        return results

@router.get("/species", response_model=List[SpeciesStats])
def get_species_stats(lake: Optional[str] = None):
    """
    Get statistics by species
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        where_clause = "WHERE disqualified = false"
        if lake:
            where_clause += f" AND lake = %s"
        
        query = f"""
            SELECT 
                species,
                SUM(fish_count) as total_caught,
                SUM(total_weight_grams) as total_weight_grams,
                AVG(total_weight_grams::float / NULLIF(fish_count, 0)) as avg_weight_grams
            FROM competition_catches
            {where_clause}
            GROUP BY species
            ORDER BY total_caught DESC
        """
        
        params = [lake] if lake else []
        cur.execute(query, params)
        
        results = cur.fetchall()
        return results

@router.get("/lakes", response_model=List[LakeStats])
def get_lake_stats():
    """
    Get statistics by lake
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                lake,
                SUM(fish_count) as total_fish,
                COUNT(DISTINCT timestamp) as total_competitions,
                COUNT(DISTINCT species) as unique_species
            FROM competition_catches
            WHERE disqualified = false
            GROUP BY lake
            ORDER BY total_fish DESC
        """
        
        cur.execute(query)
        results = cur.fetchall()
        return results

@router.get("/recent", response_model=List[CompetitionCatch])
def get_recent_catches(
    limit: int = Query(default=20, ge=1, le=100),
    player: Optional[str] = None
):
    """
    Get most recent catches
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        where_clause = ""
        params = []
        
        if player:
            where_clause = "WHERE player_name = %s"
            params.append(player)
        
        query = f"""
            SELECT *
            FROM competition_catches
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        params.append(limit)
        cur.execute(query, params)
        
        results = cur.fetchall()
        return results
