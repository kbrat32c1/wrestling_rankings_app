from app import db, Wrestler, Match  # Assuming Wrestler and Match are directly in app.py

# Define the previous season ID
previous_season_id = 1

# Reset Elo ratings for all wrestlers in the previous season
def reset_elo_ratings():
    previous_wrestlers = Wrestler.query.filter_by(season_id=previous_season_id).all()
    for wrestler in previous_wrestlers:
        wrestler.elo_rating = 1500  # Default starting Elo
    db.session.commit()
    print("Reset Elo ratings for all wrestlers in the previous season.")

# Update Elo ratings based on matches
def process_matches():
    matches = Match.query.filter_by(season_id=previous_season_id).order_by(Match.date).all()
    print(f"Found {len(matches)} matches in the {previous_season_id} season.")
    
    for match in matches:
        wrestler1 = Wrestler.query.get(match.wrestler1_id)
        wrestler2 = Wrestler.query.get(match.wrestler2_id)

        if not wrestler1 or not wrestler2:
            print(f"Match {match.id} has missing wrestlers. Skipping.")
            continue

        # Initialize opponent Elo ratings if not set
        wrestler1.elo_rating = wrestler1.elo_rating or 1500
        wrestler2.elo_rating = wrestler2.elo_rating or 1500

        # Calculate expected scores
        expected1 = 1 / (1 + 10 ** ((wrestler2.elo_rating - wrestler1.elo_rating) / 400))
        expected2 = 1 / (1 + 10 ** ((wrestler1.elo_rating - wrestler2.elo_rating) / 400))

        # Determine actual scores
        actual1 = 1 if match.winner_id == wrestler1.id else 0
        actual2 = 1 if match.winner_id == wrestler2.id else 0

        # Update Elo ratings
        k_factor = 32
        wrestler1.elo_rating += k_factor * (actual1 - expected1)
        wrestler2.elo_rating += k_factor * (actual2 - expected2)

        print(f"Processed match {match.id}: {wrestler1.name} ({wrestler1.elo_rating:.2f}) vs {wrestler2.name} ({wrestler2.elo_rating:.2f})")

    db.session.commit()
    print("Elo ratings updated for all matches.")

# Execute the steps
if __name__ == "__main__":
    reset_elo_ratings()
    process_matches()
