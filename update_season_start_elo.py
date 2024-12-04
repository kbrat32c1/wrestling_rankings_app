from app import db, Wrestler

# Retrieve all wrestlers from season 1
wrestlers_season_1 = Wrestler.query.filter_by(season_id=1).all()

# Map season 1 Elo to season 18
for wrestler_season_1 in wrestlers_season_1:
    # Find the corresponding wrestler in season 18
    wrestler_season_18 = Wrestler.query.filter_by(
        name=wrestler_season_1.name, season_id=18).first()
    
    if wrestler_season_18:
        # Update Season Start Elo in season 18
        wrestler_season_18.season_start_elo = wrestler_season_1.elo_rating

db.session.commit()
print("Season Start Elo updated for all wrestlers in season 18.")
