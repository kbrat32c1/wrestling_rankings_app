from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime

@dataclass
class Wrestler:
    id: str
    name: str
    school: str
    weight_class: int
    rating: float = 1500
    rd: float = 350
    vol: float = 0.06
    wins: int = 0
    losses: int = 0

@dataclass
class Match:
    date: datetime
    weight_class: int
    wrestler1_id: str
    wrestler2_id: str
    winner_id: str
    win_type: str  # 'decision', 'major_decision', 'tech_fall', 'pin'

class WrestlingDatabase:
    def __init__(self):
        self.wrestlers: Dict[str, Wrestler] = {}
        self.matches: List[Match] = []

    def add_wrestler(self, wrestler: Wrestler):
        self.wrestlers[wrestler.id] = wrestler

    def add_match(self, match: Match):
        self.matches.append(match)
        
        winner = self.wrestlers[match.winner_id]
        loser_id = match.wrestler1_id if match.winner_id == match.wrestler2_id else match.wrestler2_id
        loser = self.wrestlers[loser_id]
        
        winner.wins += 1
        loser.losses += 1

    def get_wrestlers_by_weight_class(self, weight_class: int) -> List[Wrestler]:
        return [w for w in self.wrestlers.values() if w.weight_class == weight_class]

    # New method to calculate wrestling rankings
    def wrestling_rankings(self, weight_class: int) -> List[Wrestler]:
        wrestlers_in_class = self.get_wrestlers_by_weight_class(weight_class)
        # Sort wrestlers by rating, from highest to lowest
        return sorted(wrestlers_in_class, key=lambda w: w.rating, reverse=True)

# Example usage
if __name__ == "__main__":
    # Initialize the database
    db = WrestlingDatabase()

    # Add sample wrestlers
    db.add_wrestler(Wrestler(id="1", name="John Doe", school="School A", weight_class=125))
    db.add_wrestler(Wrestler(id="2", name="Jane Smith", school="School B", weight_class=125, rating=1600))

    # Get and print the rankings for the 125 lbs weight class
    rankings = db.wrestling_rankings(125)
    for wrestler in rankings:
        print(f"Name: {wrestler.name}, Rating: {wrestler.rating}")
