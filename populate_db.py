from app import app, db, Wrestler, Match, WEIGHT_CLASSES, expected_score, update_elo
import random
from datetime import datetime, timedelta

# Sample data
first_names = ["John", "Mike", "David", "Chris", "Alex", "Sam", "Pat", "Jake", "Tom", "Ryan",
               "Emily", "Sarah", "Jessica", "Amanda", "Olivia", "Emma", "Sophia", "Ava", "Mia", "Isabella"]
last_names = ["Smith", "Johnson", "Lee", "Wilson", "Taylor", "Anderson", "Murphy", "Brown", "Davis", "White",
              "Chen", "Garcia", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Ramirez"]

schools = ["Iowa State", "Penn State", "Ohio State", "Oklahoma State", "Michigan", 
           "Cornell", "Nebraska", "Missouri", "Arizona State", "North Carolina State"]
win_types = ["Decision", "Major Decision", "Technical Fall", "Fall", "Forfeit", "Injury Default"]

def generate_unique_name():
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

def create_sample_wrestlers():
    for weight_class in WEIGHT_CLASSES:
        for _ in range(5):  # Create 5 wrestlers for each weight class
            name = generate_unique_name()
            school = random.choice(schools)
            wrestler = Wrestler(
                name=name, 
                school=school, 
                weight_class=weight_class, 
                wins=0, 
                losses=0,
                elo_rating=1500  # Initial Elo rating
            )
            db.session.add(wrestler)
    db.session.commit()

def create_sample_matches():
    start_date = datetime(2023, 11, 1)  # Start of wrestling season
    end_date = datetime(2024, 3, 31)    # End of wrestling season
    
    for weight_class in WEIGHT_CLASSES:
        wrestlers = Wrestler.query.filter_by(weight_class=weight_class).all()
        
        for _ in range(20):  # Create 20 matches for each weight class
            wrestler1, wrestler2 = random.sample(wrestlers, 2)
            winner = random.choice([wrestler1, wrestler2])
            match_date = random_date(start_date, end_date)
            win_type = random.choice(win_types)
            
            match = Match(
                date=match_date,
                wrestler1_id=wrestler1.id,
                wrestler2_id=wrestler2.id,
                winner_id=winner.id,
                win_type=win_type
            )
            db.session.add(match)
            
            # Update Elo ratings
            expected_1 = expected_score(wrestler1.elo_rating, wrestler2.elo_rating)
            expected_2 = 1 - expected_1
            
            actual_1 = 1 if winner.id == wrestler1.id else 0
            actual_2 = 1 - actual_1
            
            wrestler1.elo_rating = update_elo(wrestler1.elo_rating, expected_1, actual_1)
            wrestler2.elo_rating = update_elo(wrestler2.elo_rating, expected_2, actual_2)
            
            # Update win/loss records
            if winner == wrestler1:
                wrestler1.wins += 1
                wrestler2.losses += 1
            else:
                wrestler2.wins += 1
                wrestler1.losses += 1
            
            print(f"Match: {wrestler1.name} vs {wrestler2.name}, Winner: {winner.name}")
            print(f"Updated Elo ratings: {wrestler1.name}: {wrestler1.elo_rating:.2f}, {wrestler2.name}: {wrestler2.elo_rating:.2f}")
    
    db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        # Clear existing data
        db.session.query(Match).delete()
        db.session.query(Wrestler).delete()
        db.session.commit()

        print("Creating sample wrestlers...")
        create_sample_wrestlers()
        print("Creating sample matches...")
        create_sample_matches()
        print("Sample data has been added to the database with correct NCAA weight classes and updated Elo ratings.")