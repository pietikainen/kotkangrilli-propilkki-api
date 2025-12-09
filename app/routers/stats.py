"""
Tournament statistics and leaderboard endpoints
Rewritten to use new tournament schema (competitions, users, fish_catches, etc.)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.database import get_db
from app.models import (
    LeaderboardEntry, SpeciesStats, LakeStats, CompetitionCatch, 
    SpeciesRecord, TopCatch, SpeciesRecordList, FishCatch
)

router = APIRouter(prefix="/api/stats", tags=["statistics"])

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=100),
    lake: Optional[str] = None
):
    """
    Get top players leaderboard with biggest catch species
    Uses: users, competition_participants, fish_catches, competitions, fish_species
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        lake_filter = ""
        params = []
        if lake:
            lake_filter = "AND c.lake = %s"
            params.append(lake)
        
        query = f"""
            WITH player_catches AS (
                SELECT 
                    u.base_nickname as player_name,
                    SUM(fc.count) as total_fish,
                    SUM(fc.total_weight) as total_weight_grams,
                    COUNT(DISTINCT fc.competition_id) as competitions_count,
                    MAX(fc.largest_weight) as biggest_catch
                FROM users u
                JOIN fish_catches fc ON u.id = fc.user_id
                JOIN competitions c ON fc.competition_id = c.id
                {lake_filter}
                GROUP BY u.id, u.base_nickname
            ),
            player_biggest_species AS (
                SELECT DISTINCT ON (u.base_nickname)
                    u.base_nickname,
                    fs.name as biggest_catch_species
                FROM users u
                JOIN fish_catches fc ON u.id = fc.user_id
                JOIN fish_species fs ON fc.species_id = fs.id
                JOIN competitions c ON fc.competition_id = c.id
                {lake_filter}
                ORDER BY u.base_nickname, fc.largest_weight DESC
            )
            SELECT 
                pc.player_name,
                pc.total_fish,
                pc.total_weight_grams,
                pc.competitions_count,
                pc.biggest_catch,
                pbs.biggest_catch_species
            FROM player_catches pc
            LEFT JOIN player_biggest_species pbs ON pc.player_name = pbs.base_nickname
            ORDER BY pc.total_weight_grams DESC
            LIMIT %s
        """
        
        params.append(limit)
        cur.execute(query, params)
        
        results = cur.fetchall()
        return results

@router.get("/species", response_model=List[SpeciesStats])
def get_species_stats(lake: Optional[str] = None):
    """
    Get statistics by species
    Uses: fish_species, fish_catches, competitions
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        lake_filter = ""
        params = []
        if lake:
            lake_filter = "WHERE c.lake = %s"
            params.append(lake)
        
        query = f"""
            SELECT 
                fs.name as species,
                SUM(fc.count) as total_caught,
                SUM(fc.total_weight) as total_weight_grams,
                AVG(fc.total_weight::float / NULLIF(fc.count, 0)) as avg_weight_grams
            FROM fish_species fs
            JOIN fish_catches fc ON fs.id = fc.species_id
            JOIN competitions c ON fc.competition_id = c.id
            {lake_filter}
            GROUP BY fs.name
            ORDER BY total_caught DESC
        """
        
        cur.execute(query, params)
        
        results = cur.fetchall()
        return results

@router.get("/lakes", response_model=List[LakeStats])
def get_lake_stats():
    """
    Get statistics by lake
    Uses: competitions, fish_catches, fish_species
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                c.lake,
                COALESCE(SUM(fc.count), 0) as total_fish,
                COUNT(DISTINCT c.id) as total_competitions,
                COUNT(DISTINCT fc.species_id) as unique_species
            FROM competitions c
            LEFT JOIN fish_catches fc ON c.id = fc.competition_id
            GROUP BY c.lake
            ORDER BY total_fish DESC
        """
        
        cur.execute(query)
        results = cur.fetchall()
        return results

@router.get("/recent", response_model=List[FishCatch])
def get_recent_catches(
    limit: int = Query(default=20, ge=1, le=100),
    player: Optional[str] = None
):
    """
    Get most recent catches
    Uses: fish_catches, users, fish_species, competitions
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        player_filter = ""
        params = []
        
        if player:
            player_filter = "WHERE u.base_nickname = %s"
            params.append(player)
        
        query = f"""
            SELECT 
                u.base_nickname as player_name,
                fs.name as species,
                fc.count,
                fc.total_weight,
                fc.largest_weight,
                c.lake as competition_lake,
                c.start_time as competition_time
            FROM fish_catches fc
            JOIN users u ON fc.user_id = u.id
            JOIN fish_species fs ON fc.species_id = fs.id
            JOIN competitions c ON fc.competition_id = c.id
            {player_filter}
            ORDER BY c.start_time DESC
            LIMIT %s
        """
        
        params.append(limit)
        cur.execute(query, params)
        
        results = cur.fetchall()
        return results

@router.get("/species/{species}/record", response_model=SpeciesRecord)
def get_species_record(species: str):
    """
    Get the biggest catch record for a specific species
    Uses: fish_catches, fish_species, users, competitions
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                fs.name as species,
                u.base_nickname as player_name,
                fc.largest_weight as weight_grams,
                c.lake,
                c.start_time as timestamp
            FROM fish_catches fc
            JOIN fish_species fs ON fc.species_id = fs.id
            JOIN users u ON fc.user_id = u.id
            JOIN competitions c ON fc.competition_id = c.id
            WHERE fs.name = %s
            ORDER BY fc.largest_weight DESC
            LIMIT 1
        """
        
        cur.execute(query, [species])
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"No catches found for species: {species}")
        
        return result

@router.get("/top-catches", response_model=List[TopCatch])
def get_top_catches(limit: int = Query(default=10, ge=1, le=100)):
    """
    Get top catches by weight across all species
    Uses: fish_catches, users, fish_species, competitions
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                u.base_nickname as player_name,
                c.lake,
                fs.name as species,
                fc.largest_weight as weight_grams,
                c.start_time as timestamp
            FROM fish_catches fc
            JOIN users u ON fc.user_id = u.id
            JOIN fish_species fs ON fc.species_id = fs.id
            JOIN competitions c ON fc.competition_id = c.id
            ORDER BY fc.largest_weight DESC
            LIMIT %s
        """
        
        cur.execute(query, [limit])
        results = cur.fetchall()
        return results

@router.get("/species-records", response_model=List[SpeciesRecordList])
def get_species_records():
    """
    Get the biggest catch for each unique species (kalalaji, paino, kalastaja, järvi, päivämäärä)
    Uses: fish_catches, fish_species, users, competitions
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT DISTINCT ON (fs.name)
                fs.name as species,
                fc.largest_weight as weight_grams,
                u.base_nickname as player_name,
                c.lake,
                c.start_time as timestamp
            FROM fish_catches fc
            JOIN fish_species fs ON fc.species_id = fs.id
            JOIN users u ON fc.user_id = u.id
            JOIN competitions c ON fc.competition_id = c.id
            ORDER BY fs.name, fc.largest_weight DESC
        """
        
        cur.execute(query)
        results = cur.fetchall()
        return results

@router.get("/competitions")
def get_competitions(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    """
    Get list of all competitions that have results
    Returns competitions ordered by start_time (newest first)
    Uses: competitions, competition_participants, users, fish_catches, fish_species
    """
    from app.models import CompetitionSummary, CompetitionResult
    from typing import List
    
    with get_db() as conn:
        cur = conn.cursor()
        
        # Get list of competition IDs with results
        comp_ids_query = """
            SELECT DISTINCT c.id, c.start_time
            FROM competitions c
            WHERE EXISTS (
                SELECT 1 FROM competition_participants cp
                WHERE cp.competition_id = c.id AND cp.rank IS NOT NULL
            )
            ORDER BY c.start_time DESC
            LIMIT %s OFFSET %s
        """
        
        cur.execute(comp_ids_query, [limit, offset])
        comp_ids = [row['id'] for row in cur.fetchall()]
        
        if not comp_ids:
            return []
        
        # Get competition details
        comp_query = """
            SELECT 
                c.id,
                c.lake,
                c.start_time,
                c.duration_minutes,
                c.difficulty,
                c.game_mode,
                c.ice_condition,
                c.season,
                c.time_of_day,
                COUNT(DISTINCT cp.user_id) as total_participants
            FROM competitions c
            LEFT JOIN competition_participants cp ON c.id = cp.competition_id
            WHERE c.id = ANY(%s)
            GROUP BY c.id
            ORDER BY c.start_time DESC
        """
        
        cur.execute(comp_query, [comp_ids])
        comps_data = cur.fetchall()
        
        competitions: List[CompetitionSummary] = []
        
        for comp_row in comps_data:
            comp_id = comp_row['id']
            
            # Get results for this competition
            results_query = """
                SELECT 
                    cp.rank,
                    u.base_nickname as player_name,
                    COALESCE(cp.total_weight, 0) as total_weight,
                    COALESCE(cp.disqualified, false) as disqualified
                FROM competition_participants cp
                JOIN users u ON cp.user_id = u.id
                WHERE cp.competition_id = %s
                    AND cp.rank IS NOT NULL
                ORDER BY cp.rank
            """
            
            cur.execute(results_query, [comp_id])
            results_data = cur.fetchall()
            
            results = [
                CompetitionResult(
                    rank=row['rank'],
                    player_name=row['player_name'],
                    total_weight=row['total_weight'],
                    disqualified=row['disqualified']
                )
                for row in results_data
            ]
            
            # Get biggest fish for this competition
            biggest_fish_query = """
                SELECT 
                    fs.name as species,
                    fc.largest_weight as weight,
                    u.base_nickname as player_name
                FROM fish_catches fc
                JOIN fish_species fs ON fc.species_id = fs.id
                JOIN users u ON fc.user_id = u.id
                WHERE fc.competition_id = %s
                ORDER BY fc.largest_weight DESC
                LIMIT 1
            """
            
            cur.execute(biggest_fish_query, [comp_id])
            biggest_fish = cur.fetchone()
            
            competitions.append(
                CompetitionSummary(
                    competition_id=comp_row['id'],
                    lake=comp_row['lake'],
                    start_time=comp_row['start_time'],
                    duration_minutes=comp_row['duration_minutes'],
                    difficulty=comp_row['difficulty'],
                    game_mode=comp_row['game_mode'],
                    ice_condition=comp_row['ice_condition'],
                    season=comp_row['season'],
                    time_of_day=comp_row['time_of_day'],
                    results=results,
                    total_participants=comp_row['total_participants'],
                    biggest_fish_species=biggest_fish['species'] if biggest_fish else None,
                    biggest_fish_weight=biggest_fish['weight'] if biggest_fish else None,
                    biggest_fish_player=biggest_fish['player_name'] if biggest_fish else None
                )
            )
        
        return competitions

@router.get("/latest-competition")
def get_latest_competition():
    """
    Get the results of the latest COMPLETED competition
    Returns the latest competition WITH results (has ranked participants)
    Uses: competitions, competition_participants, users
    """
    from app.models import LatestCompetitionResults, CompetitionResult, CurrentParticipant
    from datetime import datetime, timezone
    import pytz
    
    with get_db() as conn:
        cur = conn.cursor()
        
        # Get the latest competition with results (has participants with rank)
        comp_query = """
            SELECT 
                c.id,
                c.lake,
                c.start_time,
                c.duration_minutes,
                c.difficulty,
                c.game_mode,
                c.ice_condition,
                c.season,
                c.time_of_day
            FROM competitions c
            WHERE EXISTS (
                SELECT 1 FROM competition_participants cp
                WHERE cp.competition_id = c.id AND cp.rank IS NOT NULL
            )
            ORDER BY c.start_time DESC
            LIMIT 1
        """
        
        cur.execute(comp_query)
        comp_data = cur.fetchone()
        
        if not comp_data:
            raise HTTPException(status_code=404, detail="No completed competitions found")
        
        comp_id = comp_data['id']
        start_time = comp_data['start_time']
        duration_minutes = comp_data['duration_minutes']
        
        # Calculate elapsed and remaining time
        if start_time.tzinfo is None:
            start_time = pytz.UTC.localize(start_time)
        
        now = datetime.now(timezone.utc)
        elapsed = (now - start_time).total_seconds() / 60
        elapsed_minutes = max(0, int(elapsed))
        time_remaining = duration_minutes - elapsed_minutes
        time_remaining_minutes = max(0, time_remaining)
        
        # Get participants and their results (with rank)
        results_query = """
            SELECT 
                cp.rank,
                u.base_nickname as player_name,
                COALESCE(cp.total_weight, 0) as total_weight,
                COALESCE(cp.disqualified, false) as disqualified
            FROM competition_participants cp
            JOIN users u ON cp.user_id = u.id
            WHERE cp.competition_id = %s
                AND cp.rank IS NOT NULL
            ORDER BY cp.rank
        """
        
        cur.execute(results_query, [comp_id])
        results_data = cur.fetchall()
        
        results = [
            CompetitionResult(
                rank=row['rank'],
                player_name=row['player_name'],
                total_weight=row['total_weight'],
                disqualified=row['disqualified']
            )
            for row in results_data
        ]
        
        return LatestCompetitionResults(
            competition_id=comp_data['id'],
            lake=comp_data['lake'],
            start_time=start_time,
            duration_minutes=duration_minutes,
            difficulty=comp_data['difficulty'],
            game_mode=comp_data['game_mode'],
            ice_condition=comp_data['ice_condition'],
            season=comp_data['season'],
            time_of_day=comp_data['time_of_day'],
            results=results,
            elapsed_minutes=elapsed_minutes,
            time_remaining_minutes=time_remaining_minutes
        )

@router.get("/current-competition")
def get_current_competition():
    """
    Get information about the currently RUNNING competition
    Returns the latest competition WITHOUT results (no ranked participants)
    Returns {"message": "pause"} if no such competition exists
    Uses: competitions, competition_participants, users
    """
    from app.models import CurrentCompetitionInfo, CurrentParticipant
    from datetime import datetime, timezone
    import pytz
    
    with get_db() as conn:
        cur = conn.cursor()
        
        # Get the latest competition without results (no participants with rank)
        comp_query = """
            SELECT 
                c.id,
                c.lake,
                c.start_time,
                c.duration_minutes,
                c.difficulty,
                c.game_mode,
                c.ice_condition,
                c.season,
                c.time_of_day
            FROM competitions c
            WHERE NOT EXISTS (
                SELECT 1 FROM competition_participants cp
                WHERE cp.competition_id = c.id AND cp.rank IS NOT NULL
            )
            ORDER BY c.start_time DESC
            LIMIT 1
        """
        
        cur.execute(comp_query)
        comp_data = cur.fetchone()
        
        if not comp_data:
            return {"message": "pause"}
        
        comp_id = comp_data['id']
        start_time = comp_data['start_time']
        duration_minutes = comp_data['duration_minutes']
        
        # Calculate elapsed and remaining time (based on competition start time, not real time)
        if start_time.tzinfo is None:
            start_time = pytz.UTC.localize(start_time)
        
        now = datetime.now(timezone.utc)
        elapsed = (now - start_time).total_seconds() / 60
        elapsed_minutes = max(0, int(elapsed))
        time_remaining = duration_minutes - elapsed_minutes
        time_remaining_minutes = max(0, time_remaining)
        
        # Get participants who joined during this competition
        participants_query = """
            SELECT 
                u.base_nickname as player_name,
                cp.joined_at,
                cp.left_at
            FROM competition_participants cp
            JOIN users u ON cp.user_id = u.id
            WHERE cp.competition_id = %s
            ORDER BY cp.joined_at
        """
        
        cur.execute(participants_query, [comp_id])
        participants_data = cur.fetchall()
        
        participants = [
            CurrentParticipant(
                player_name=row['player_name'],
                joined_at=row['joined_at'],
                is_active=(row['left_at'] is None)
            )
            for row in participants_data
        ]
        
        return CurrentCompetitionInfo(
            competition_id=comp_data['id'],
            lake=comp_data['lake'],
            start_time=start_time,
            duration_minutes=duration_minutes,
            difficulty=comp_data['difficulty'],
            game_mode=comp_data['game_mode'],
            ice_condition=comp_data['ice_condition'],
            season=comp_data['season'],
            time_of_day=comp_data['time_of_day'],
            participants=participants,
            elapsed_minutes=elapsed_minutes,
            time_remaining_minutes=time_remaining_minutes
        )
