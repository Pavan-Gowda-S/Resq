"""
Rescue Matching Agent Module.
Discovers and matches rescue teams to extraction tasks.
"""
from agents.rescue_matching.agent import run_rescue_matching
from agents.rescue_matching.schemas import RescueTeamRecommendation, RescueMatchResult
from agents.rescue_matching.matcher import match_rescue_teams

__all__ = [
    "run_rescue_matching",
    "RescueTeamRecommendation",
    "RescueMatchResult",
    "match_rescue_teams"
]
