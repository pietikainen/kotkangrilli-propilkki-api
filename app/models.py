"""
Pydantic models for API requests/responses
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CompetitionCatch(BaseModel):
    id: int
    timestamp: datetime
    lake: str
    player_name: str
    species: str
    fish_count: int
    total_weight_grams: int
    player_reported_biggest: Optional[int]
    disqualified: bool
    source_file: Optional[str]

class LeaderboardEntry(BaseModel):
    player_name: str
    total_fish: int
    total_weight_grams: int
    competitions_count: int
    biggest_catch: Optional[int]
    biggest_catch_species: Optional[str]

class SpeciesRecord(BaseModel):
    species: str
    player_name: str
    weight_grams: int
    lake: str
    timestamp: datetime

class SpeciesRecordList(BaseModel):
    species: str
    weight_grams: int
    player_name: str
    lake: str
    timestamp: datetime

class TopCatch(BaseModel):
    player_name: str
    lake: str
    species: str
    weight_grams: int
    timestamp: datetime

class SpeciesStats(BaseModel):
    species: str
    total_caught: int
    total_weight_grams: int
    avg_weight_grams: float

class LakeStats(BaseModel):
    lake: str
    total_fish: int
    total_competitions: int
    unique_species: int

# Player session models (no IP addresses exposed)
class PlayerSession(BaseModel):
    id: int
    player_name: str
    joined_at: datetime
    left_at: Optional[datetime]
    session_duration_seconds: Optional[int]
    player_version: Optional[str]

class PlayerSessionStats(BaseModel):
    player_name: str
    total_sessions: int
    total_playtime_seconds: int
    total_playtime_hours: float
    avg_session_duration_seconds: Optional[int]
    first_seen: datetime
    last_seen: datetime

class TopPlayer(BaseModel):
    player_name: str
    total_sessions: int
    total_playtime_hours: float
    avg_session_hours: float

class DailyActivity(BaseModel):
    date: str  # YYYY-MM-DD format
    total_sessions: int
    unique_players: int
    total_playtime_hours: float

class HourlyActivity(BaseModel):
    hour: int  # 0-23
    total_sessions: int
    avg_session_duration_minutes: float

class PlayerEfficiency(BaseModel):
    player_name: str
    total_playtime_hours: float
    total_fish: int
    total_weight_grams: int
    fish_per_hour: float
    grams_per_hour: float
    competitions_count: int
