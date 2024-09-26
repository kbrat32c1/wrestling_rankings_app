from glicko2 import Glicko2
from wrestler_data import WrestlingDatabase
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

def weekly_update(db: WrestlingDatabase, glicko: Glicko2, start_date: datetime, end_date: datetime):
    weekly_matches = [m for m in db.matches if start_date <= m.date < end_date]

    wrestler_matches: Dict[str, List[Tuple[str, int]]] = {}
    for match in weekly_matches:
        winner_id = match.winner_id
        loser_id = match.wrestler1_id if winner_id == match.wrestler2_id else match.wrestler2_id
        
        if winner_id not in wrestler_matches:
            wrestler_matches[winner_id] = []
        if loser_id not in wrestler_matches:
            wrestler_matches[loser_id] = []
        
        wrestler_matches[winner_id].append((loser_id, 1))  # 1 for win
        wrestler_matches[loser_id].append((winner_id, 0))  # 0 for loss

    for wrestler_id, matches in wrestler_matches.items():
        wrestler = db.wrestlers[wrestler_id]
        outcomes = [(db.wrestlers[opp_id].rating, db.wrestlers[opp_id].rd, result) for opp_id, result in matches]
        
        new_rating, new_rd, new_vol = glicko.update_rating(wrestler.rating, wrestler.rd, wrestler.vol, outcomes)
        
        wrestler.rating = new_rating
        wrestler.rd = new_rd
        wrestler.vol = new_vol

    rankings = {}
    for weight_class in set(w.weight_class for w in db.wrestlers.values()):
        wrestlers = db.get_wrestlers_by_weight_class(weight_class)
        rankings[weight_class] = sorted(wrestlers, key=lambda w: w.rating, reverse=True)

    return rankings