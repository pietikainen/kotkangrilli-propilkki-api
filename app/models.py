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
