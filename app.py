from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import math
import logging
import csv
import io
import traceback
import difflib
from io import TextIOWrapper
from datetime import timezone

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wrestling.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Prevents caching of static files
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Required for flash messages

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = app.logger

WEIGHT_CLASSES = [125, 133, 141, 149, 157, 165, 174, 184, 197, 285]

# List of Division 3 schools with wrestling programs
D3_WRESTLING_SCHOOLS = [
    "Adrian College", "Albion College", "Alfred State", "Alma College", "Alvernia University",
    "Augsburg University", "Augustana (IL)", "Aurora University", "Averett University",
    "Baldwin Wallace", "Bridgewater State University", "Brockport State", "Buena Vista",
    "Carthage College", "Case Western Reserve", "Castleton University", "Centenary (NJ)",
    "Central College", "Chicago", "Coast Guard", "Coe College", "Concordia (WI)",
    "Concordia - Moorhead", "Cornell College", "Defiance College", "Delaware Valley",
    "Dubuque", "Elizabethtown", "Elmhurst University", "Elmira", "Eureka College",
    "Ferrum College", "Fontboone University", "Gettysburg", "Greensboro College",
    "Heidelberg", "Hiram College", "Hunter College", "Huntingdon College",
    "Illinois Wesleyan", "Ithaca", "John Carroll University", "Johns Hopkins",
    "Johnson & Wales", "Keystone College", "King's College (PA)", "Lakeland",
    "Linfield University", "Loras College", "Luther College", "Lycoming", "Manchester",
    "Marymount University", "McDaniel", "Messiah", "Millikin",
    "Milwaukee School of Engineering", "Mount St. Joseph", "Mount Union", "Muhlenberg",
    "Muskingum", "Nebraska Wesleyan University", "New England College",
    "New Jersey City University", "New York University", "North Central (IL)", "Norwich",
    "Ohio Northern", "Ohio Wesleyan University", "Olivet", "Oneonta State",
    "Otterbein Univeristy", "Penn State Behrend", "Pennsylvania College of Technology",
    "Pittsburg - Bradford", "Plymouth State", "Rhode Island College", "Roanoke College",
    "Rochester Institute of Technology", "Roger Williams", "Schreiner University",
    "Shenandoah University", "Simpson College", "Southern Maine", "Southern Virginia",
    "Springfield", "St. John Fisher College", "St. Johns (MN)", "St. Vincent College",
    "Stevens Institute of Technology", "SUNY - Cortland", "SUNY - Oswego",
    "The College of New Jersey", "Thiel", "Trine University", "Trinity (CT)",
    "U.S. Merchant Marine", "University of Scranton", "University of the Ozarks",
    "Ursinus College", "Utica University", "Wabash", "Wartburg College",
    "Washington and Jefferson", "Washington and Lee", "Waynesburg", "Wesleyan (CT)",
    "Western New England", "Westminister", "Wheaton (IL)", "Wilkes", "Williams College",
    "Wilmington (OH)", "Wisconsin - Eau Claire", "Wisconsin - La Crosse",
    "Wisconsin - Oshkosh", "Wisconsin - Platteville", "Wisconsin - Stevens Point",
    "Wisconsin - Whitewater", "Worcester Polytechnic", "York College (PA)"
]

# Models
class Wrestler(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    school = db.Column(db.String(100), nullable=False)
    weight_class = db.Column(db.Integer, nullable=False)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    elo_rating = db.Column(db.Float, default=1500)

    matches_as_wrestler1 = db.relationship('Match', foreign_keys='Match.wrestler1_id', backref='wrestler1', lazy='dynamic')
    matches_as_wrestler2 = db.relationship('Match', foreign_keys='Match.wrestler2_id', backref='wrestler2', lazy='dynamic')

    @property
    def total_matches(self):
        return self.wins + self.losses

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'school': self.school,
            'weight_class': self.weight_class,
            'wins': self.wins,
            'losses': self.losses,
            'elo_rating': self.elo_rating,
            'total_matches': self.total_matches
        }

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    wrestler1_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)
    wrestler2_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)
    win_type = db.Column(db.String(20), nullable=False)

    winner = db.relationship('Wrestler', foreign_keys=[winner_id], backref='matches_won')

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d'),  # Format as a string for easy display
            'wrestler1_id': self.wrestler1_id,
            'wrestler2_id': self.wrestler2_id,
            'winner_id': self.winner_id,
            'win_type': self.win_type
        }


# Elo rating functions
def expected_score(rating_a, rating_b):
    return 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))

def update_elo(rating, expected, actual, k_factor=32):
    return rating + k_factor * (actual - expected)

def recalculate_elo(wrestler):
    """
    Recalculate the Elo rating for the given wrestler based on their match history.
    """
    logger.info(f"Recalculating Elo for {wrestler.name}")
    
    # Reset the wrestler's Elo rating to the base value of 1500
    wrestler.elo_rating = 1500

    # Fetch all matches where the wrestler was either wrestler1 or wrestler2
    matches = list(wrestler.matches_as_wrestler1) + list(wrestler.matches_as_wrestler2)

    # If no matches, return early
    if not matches:
        logger.info(f"No matches found for {wrestler.name}. Elo remains {wrestler.elo_rating}")
        return

    # Convert any timezone-aware datetime to naive datetime (if necessary)
    for match in matches:
        if match.date.tzinfo is not None:
            match.date = match.date.astimezone(timezone.utc).replace(tzinfo=None)

    # Sort matches by date to recalculate Elo in chronological order
    matches.sort(key=lambda x: x.date)

    # Recalculate Elo for each match
    for match in matches:
        opponent = match.wrestler2 if match.wrestler1_id == wrestler.id else match.wrestler1
        expected = expected_score(wrestler.elo_rating, opponent.elo_rating)
        actual = 1 if match.winner_id == wrestler.id else 0

        # Update Elo rating based on match result
        wrestler.elo_rating = update_elo(wrestler.elo_rating, expected, actual)

        logger.info(f"Match on {match.date} against {opponent.name}: expected {expected:.4f}, actual {actual}. Updated Elo: {wrestler.elo_rating:.2f}")

    # Log the final recalculated Elo rating
    logger.info(f"Final Elo for {wrestler.name}: {wrestler.elo_rating}")
    db.session.commit()




# Flexible date parsing function
def parse_date(date_str):
    date_str = date_str.strip()  # Strip any extra spaces
    date_formats = ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d']  # List of possible date formats

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date '{date_str}' is not in a recognized format. Supported formats: {date_formats}")

# Helper function for logging skipped matches
def log_skipped_match(wrestler1, wrestler2, date, reason):
    app.logger.warning(f"Skipping match between {wrestler1} and {wrestler2} on {date}: {reason}")

# Enhanced function for getting or creating a wrestler with fuzzy matching
def get_or_create_wrestler(name, school, weight_class):
    name = name.strip().title()  # Normalize name (capitalize properly, remove extra spaces)
    school = school.strip().title()  # Normalize school name
    
    # Attempt to find a wrestler with close match to prevent duplicates from small errors
    wrestler = Wrestler.query.filter(
        db.func.lower(Wrestler.name) == name.lower(),
        db.func.lower(Wrestler.school) == school.lower(),
        Wrestler.weight_class == int(weight_class)
    ).first()

    if not wrestler:
        # If no exact match, log the missing wrestler and create a new one
        app.logger.info(f"Creating new wrestler: {name} from {school}")
        wrestler = Wrestler(name=name, school=school, weight_class=int(weight_class), wins=0, losses=0, elo_rating=1500)
        db.session.add(wrestler)
        db.session.commit()
    return wrestler

# Function to validate and process CSV
def validate_and_process_csv(file):
    try:
        csv_file = TextIOWrapper(file, encoding='utf-8')
        csv_reader = csv.DictReader(csv_file)

        required_headers = ['Date', 'Wrestler1', 'School1', 'Wrestler2', 'School2', 'WeightClass', 'Winner', 'WinType']
        
        # Ensure the file has the correct headers
        if set(required_headers).difference(set(csv_reader.fieldnames)):
            missing_headers = list(set(required_headers).difference(set(csv_reader.fieldnames)))
            flash(f"Missing required columns in CSV: {', '.join(missing_headers)}", 'error')
            return False

        # Process rows one by one to handle large CSVs efficiently
        for row_num, row in enumerate(csv_reader, start=1):
            try:
                wrestler1_name = row['Wrestler1'].strip().title()
                school1_name = row['School1'].strip().title()
                wrestler2_name = row['Wrestler2'].strip().title()
                school2_name = row['School2'].strip().title()
                weight_class = row['WeightClass'].strip()
                winner_name = row['Winner'].strip().title()
                win_type = row['WinType'].strip()

                # Validate weight class
                if not weight_class.isdigit() or int(weight_class) not in WEIGHT_CLASSES:
                    flash(f"Invalid weight class at row {row_num}: {weight_class}", 'error')
                    continue

                # Parse the date using the flexible date parsing function
                try:
                    raw_date = row['Date']
                    match_date = parse_date(raw_date)
                except ValueError as e:
                    flash(f"Invalid date format at row {row_num}: {raw_date} ({str(e)})", 'error')
                    continue

                # Validate other fields
                if not wrestler1_name or not school1_name or not wrestler2_name or not school2_name or not winner_name or not win_type:
                    flash(f"Missing required fields at row {row_num}", 'error')
                    continue

                if wrestler1_name == wrestler2_name and school1_name == school2_name:
                    flash(f"Invalid match (self-match) at row {row_num}", 'error')
                    continue

                # Get or create wrestlers
                wrestler1 = get_or_create_wrestler(wrestler1_name, school1_name, weight_class)
                wrestler2 = get_or_create_wrestler(wrestler2_name, school2_name, weight_class)

                # Validate winner
                if winner_name not in [wrestler1.name, wrestler2.name]:
                    flash(f"Winner does not match wrestler1 or wrestler2 at row {row_num}", 'error')
                    continue

                # Check for existing match
                existing_match = Match.query.filter_by(
                    wrestler1_id=wrestler1.id,
                    wrestler2_id=wrestler2.id,
                    date=match_date
                ).first()

                if existing_match:
                    flash(f"Duplicate match detected: {wrestler1.name} vs {wrestler2.name} on {match_date}", 'info')
                    continue  # Skip if the match already exists

                # Create and add new match
                winner = wrestler1 if winner_name == wrestler1.name else wrestler2
                new_match = Match(
                    date=match_date,
                    wrestler1_id=wrestler1.id,
                    wrestler2_id=wrestler2.id,
                    winner_id=winner.id,
                    win_type=win_type
                )
                db.session.add(new_match)

                # Update win/loss records
                if winner == wrestler1:
                    wrestler1.wins += 1
                    wrestler2.losses += 1
                else:
                    wrestler2.wins += 1
                    wrestler1.losses += 1

                # Recalculate Elo ratings for both wrestlers
                recalculate_elo(wrestler1)
                recalculate_elo(wrestler2)

                # Commit changes after processing each row
                db.session.commit()

            except Exception as e:
                flash(f"Error processing row {row_num}: {str(e)}", 'error')
                db.session.rollback()
                continue

        flash(f"CSV file processed successfully!", 'success')
        return True

    except Exception as e:
        flash(f"An error occurred during CSV validation: {str(e)}", 'error')
        return False


# Routes
@app.route('/')
def home():
    weight_class_data = []
    for weight in WEIGHT_CLASSES:
        wrestlers = Wrestler.query.filter_by(weight_class=weight).order_by(Wrestler.elo_rating.desc()).limit(5).all()
        weight_class_data.append({
            'weight': weight,
            'wrestlers': wrestlers
        })
    
    return render_template('home.html', weight_class_data=weight_class_data)

@app.route('/rankings/<int:weight_class>')
def rankings(weight_class):
    if weight_class not in WEIGHT_CLASSES:
        flash('Invalid weight class', 'error')
        return redirect(url_for('home'))
    
    wrestlers = Wrestler.query.filter_by(weight_class=weight_class).all()
    
    # Sort wrestlers first by whether they have matches, then by Elo rating
    ranked_wrestlers = sorted(wrestlers, key=lambda w: (w.total_matches > 0, w.elo_rating), reverse=True)
    
    return render_template('rankings.html', weight_class=weight_class, wrestlers=ranked_wrestlers)


@app.route('/wrestler/<int:wrestler_id>')
def wrestler_detail(wrestler_id):
    wrestler = Wrestler.query.get_or_404(wrestler_id)
    
    # Calculate wins and losses dynamically based on matches
    matches_wrestler1 = Match.query.filter_by(wrestler1_id=wrestler_id).all()
    matches_wrestler2 = Match.query.filter_by(wrestler2_id=wrestler_id).all()
    
    # Wins are matches where this wrestler is the winner
    wins = len([match for match in matches_wrestler1 if match.winner_id == wrestler_id]) + \
           len([match for match in matches_wrestler2 if match.winner_id == wrestler_id])
    
    # Losses are matches where this wrestler is the loser
    losses = len([match for match in matches_wrestler1 if match.winner_id != wrestler_id]) + \
             len([match for match in matches_wrestler2 if match.winner_id != wrestler_id])
    
    # Get match details for display
    matches = matches_wrestler1 + matches_wrestler2
    match_details = []
    for match in matches:
        opponent = match.wrestler2 if match.wrestler1_id == wrestler_id else match.wrestler1
        result = "Win" if match.winner_id == wrestler_id else "Loss"
        match_details.append({
            'id': match.id,
            'date': match.date,
            'opponent': opponent,
            'result': result,
            'win_type': match.win_type
        })

    # Render the wrestler profile, displaying the dynamic win/loss record
    return render_template('wrestler_detail.html', wrestler=wrestler, matches=match_details, wins=wins, losses=losses)


@app.route('/add_wrestler', methods=['GET', 'POST'])
def add_wrestler():
    if request.method == 'POST':
        name = request.form['name'].strip()
        school = request.form['school'].strip()
        weight_class = int(request.form['weight_class'])

        # Check if the wrestler already exists
        existing_wrestler = Wrestler.query.filter_by(name=name, school=school, weight_class=weight_class).first()
        if existing_wrestler:
            flash(f'Wrestler {name} from {school} in the {weight_class} weight class already exists.', 'error')
            return render_template('add_wrestler.html', weight_classes=WEIGHT_CLASSES, schools=D3_WRESTLING_SCHOOLS)

        if not name or school not in D3_WRESTLING_SCHOOLS or weight_class not in WEIGHT_CLASSES:
            flash('Please fill out all fields correctly.', 'error')
            return render_template('add_wrestler.html', weight_classes=WEIGHT_CLASSES, schools=D3_WRESTLING_SCHOOLS)

        new_wrestler = Wrestler(
            name=name,
            school=school,
            weight_class=weight_class,
            elo_rating=1500  # Starting Elo rating
        )
        db.session.add(new_wrestler)
        db.session.commit()

        # Track the last action in session for undo
        session['last_action'] = {
            'action': 'add_wrestler',
            'wrestler_id': new_wrestler.id
        }

        flash(f'Wrestler {name} added successfully!', 'success')
        logger.info(f"Added new wrestler: {new_wrestler.name}, School: {new_wrestler.school}, Weight Class: {new_wrestler.weight_class}")
        return redirect(url_for('home'))

    return render_template('add_wrestler.html', weight_classes=WEIGHT_CLASSES, schools=D3_WRESTLING_SCHOOLS)


@app.route('/add_match', methods=['GET', 'POST'])
def add_match():
    if request.method == 'POST':
        try:
            wrestler1_id = int(request.form['wrestler1_id'])
            wrestler2_id = int(request.form['wrestler2_id'])
            winner_id = int(request.form['winner_id'])
            date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            win_type = request.form['win_type']

            # Fetch wrestler data from the database
            wrestler1 = Wrestler.query.get(wrestler1_id)
            wrestler2 = Wrestler.query.get(wrestler2_id)

            # Check if both wrestlers exist
            if not wrestler1 or not wrestler2:
                flash('One or both wrestlers not found.', 'error')
                return redirect(url_for('add_match'))

            # Check if a match already exists between these two wrestlers on the same date
            existing_match = Match.query.filter_by(wrestler1_id=wrestler1_id, wrestler2_id=wrestler2_id, date=date).first()
            if existing_match:
                flash(f'Match between {wrestler1.name} and {wrestler2.name} on {date.strftime("%Y-%m-%d")} already exists.', 'error')
                return redirect(url_for('add_match'))

            # Validate that wrestlers are not the same and are in the same weight class
            if wrestler1.id == wrestler2.id:
                flash('A wrestler cannot compete against themselves.', 'error')
                return redirect(url_for('add_match'))

            if wrestler1.weight_class != wrestler2.weight_class:
                flash('Wrestlers must be in the same weight class to compete.', 'error')
                return redirect(url_for('add_match'))

            # Create and add new match
            new_match = Match(
                date=date,
                wrestler1_id=wrestler1_id,
                wrestler2_id=wrestler2_id,
                winner_id=winner_id,
                win_type=win_type
            )
            db.session.add(new_match)

            # Update the win/loss records
            if winner_id == wrestler1.id:
                wrestler1.wins += 1
                wrestler2.losses += 1
            else:
                wrestler2.wins += 1
                wrestler1.losses += 1

            # Commit match and wrestler updates
            db.session.commit()

            # Recalculate Elo ratings for both wrestlers
            recalculate_elo(wrestler1)
            recalculate_elo(wrestler2)

            # Flash success message and redirect to the homepage
            flash(f'Match added: {wrestler1.name} vs {wrestler2.name}', 'success')
            return redirect(url_for('home'))

        except Exception as e:
            # If an error occurs, rollback the transaction and show an error message
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('add_match'))

    # For GET requests, render the add_match form
    wrestlers = Wrestler.query.order_by(Wrestler.weight_class, Wrestler.name).all()
    serialized_wrestlers = [
        {
            'id': w.id,
            'name': w.name,
            'school': w.school,
            'weight_class': w.weight_class,
            'display_name': f"{w.name} ({w.school}) - {w.weight_class} lbs"
        } for w in wrestlers
    ]

    # Render the form with wrestler data
    return render_template('add_match.html', wrestlers=serialized_wrestlers, weight_classes=WEIGHT_CLASSES)



@app.route('/edit_match/<int:match_id>', methods=['GET', 'POST'])
def edit_match(match_id):
    match = Match.query.get_or_404(match_id)
    
    if request.method == 'POST':
        try:
            match.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            match.wrestler1_id = int(request.form['wrestler1_id'])
            match.wrestler2_id = int(request.form['wrestler2_id'])
            new_winner_id = int(request.form['winner_id'])
            match.win_type = request.form['win_type']

            wrestler1 = Wrestler.query.get(match.wrestler1_id)
            wrestler2 = Wrestler.query.get(match.wrestler2_id)

            # Revert old win/loss records
            old_winner = Wrestler.query.get(match.winner_id)
            old_loser = wrestler1 if old_winner == wrestler2 else wrestler2
            old_winner.wins -= 1
            old_loser.losses -= 1

            # Update new win/loss records
            match.winner_id = new_winner_id
            new_winner = Wrestler.query.get(new_winner_id)
            new_loser = wrestler1 if new_winner == wrestler2 else wrestler2
            new_winner.wins += 1
            new_loser.losses += 1

            db.session.commit()

            # Recalculate Elo ratings for both wrestlers
            recalculate_elo(wrestler1)
            recalculate_elo(wrestler2)

            flash('Match has been updated.', 'success')
            logger.info(f"Updated match: {wrestler1.name} vs {wrestler2.name}, Winner: {new_winner.name}")
            return redirect(url_for('wrestler_detail', wrestler_id=match.wrestler1_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
            logger.error(f"Error updating match: {str(e)}")
            return redirect(url_for('edit_match', match_id=match.id))

    wrestlers = Wrestler.query.order_by(Wrestler.weight_class, Wrestler.name).all()
    return render_template('edit_match.html', match=match, wrestlers=wrestlers)


@app.route('/edit_wrestler/<int:wrestler_id>', methods=['GET', 'POST'])
def edit_wrestler(wrestler_id):
    wrestler = Wrestler.query.get_or_404(wrestler_id)
    
    if request.method == 'POST':
        wrestler.name = request.form['name'].strip()
        wrestler.school = request.form['school'].strip()
        wrestler.weight_class = int(request.form['weight_class'])

        if not wrestler.name or wrestler.school not in D3_WRESTLING_SCHOOLS or wrestler.weight_class not in WEIGHT_CLASSES:
            flash('Please fill out all fields correctly.', 'error')
            return render_template('edit_wrestler.html', wrestler=wrestler, weight_classes=WEIGHT_CLASSES, schools=D3_WRESTLING_SCHOOLS)
        
        db.session.commit()
        flash(f'Wrestler {wrestler.name} has been updated.', 'success')
        logger.info(f"Updated wrestler: {wrestler.name}, School: {wrestler.school}, Weight Class: {wrestler.weight_class}")
        return redirect(url_for('wrestler_detail', wrestler_id=wrestler.id))
    
    return render_template('edit_wrestler.html', wrestler=wrestler, weight_classes=WEIGHT_CLASSES, schools=D3_WRESTLING_SCHOOLS)

@app.route('/delete_wrestler/<int:wrestler_id>', methods=['POST'])
def delete_wrestler(wrestler_id):
    wrestler = Wrestler.query.get_or_404(wrestler_id)

    # Store wrestler data and matches for undo
    wrestler_data = wrestler.to_dict()
    matches = wrestler.matches_as_wrestler1.all() + wrestler.matches_as_wrestler2.all()
    match_data = [match.to_dict() for match in matches]

    session['last_action'] = {
        'action': 'delete_wrestler',
        'wrestler_data': wrestler_data,
        'matches': match_data
    }

    # Delete the matches and adjust opponents' win/loss and Elo
    for match in matches:
        opponent = match.wrestler2 if match.wrestler1_id == wrestler.id else match.wrestler1
        if match.winner_id == wrestler.id:
            opponent.losses -= 1
        else:
            opponent.wins -= 1
        recalculate_elo(opponent)  # Recalculate Elo for opponent after match deletion
        db.session.delete(match)

    db.session.delete(wrestler)
    db.session.commit()

    flash(f'Wrestler {wrestler.name} and all their matches have been deleted.', 'success')
    return redirect(url_for('home'))



@app.route('/delete_match/<int:match_id>', methods=['POST'])
def delete_match(match_id):
    match = Match.query.get_or_404(match_id)
    wrestler1 = Wrestler.query.get(match.wrestler1_id)
    wrestler2 = Wrestler.query.get(match.wrestler2_id)

    # Revert win/loss records before deleting the match
    if match.winner_id == wrestler1.id:
        wrestler1.wins -= 1
        wrestler2.losses -= 1
    elif match.winner_id == wrestler2.id:
        wrestler2.wins -= 1
        wrestler1.losses -= 1

    db.session.delete(match)
    db.session.commit()

    # Recalculate Elo ratings for both wrestlers after match deletion
    recalculate_elo(wrestler1)
    recalculate_elo(wrestler2)

    flash(f'Match between {wrestler1.name} and {wrestler2.name} has been deleted.', 'success')
    return redirect(url_for('wrestler_detail', wrestler_id=wrestler1.id))



from datetime import datetime

@app.route('/undo', methods=['POST'])
def undo():
    last_action = session.get('last_action')
    if not last_action:
        flash('No action to undo!', 'warning')
        return redirect(url_for('home'))

    action = last_action.get('action')
    if action == 'delete_wrestler':
        wrestler_data = last_action.get('wrestler_data')
        restored_wrestler = Wrestler(
            id=wrestler_data['id'],
            name=wrestler_data['name'],
            school=wrestler_data['school'],
            weight_class=wrestler_data['weight_class'],
            wins=wrestler_data['wins'],
            losses=wrestler_data['losses'],
            elo_rating=wrestler_data['elo_rating']
        )
        db.session.add(restored_wrestler)
        db.session.commit()

        # Restore matches and convert the 'date' field back to a datetime object
        for match_data in last_action.get('matches', []):
            restored_match = Match(
                id=match_data['id'],
                wrestler1_id=match_data['wrestler1_id'],
                wrestler2_id=match_data['wrestler2_id'],
                winner_id=match_data['winner_id'],
                date=datetime.strptime(match_data['date'], '%Y-%m-%d'),  # Convert back to datetime
                win_type=match_data['win_type']
            )
            db.session.add(restored_match)

        db.session.commit()

        # Recalculate Elo for restored wrestler
        recalculate_elo(restored_wrestler)

        # Also recalculate Elo for opponents of the restored matches
        for match_data in last_action.get('matches', []):
            opponent_id = match_data['wrestler2_id'] if match_data['wrestler1_id'] == restored_wrestler.id else match_data['wrestler1_id']
            opponent = Wrestler.query.get(opponent_id)
            recalculate_elo(opponent)

        flash(f'Wrestler {restored_wrestler.name} and their matches have been restored.', 'success')

    session.pop('last_action', None)
    return redirect(url_for('home'))



@app.route('/upload_csv', methods=['GET', 'POST'])
def upload_csv():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            try:
                added_matches = []

                # Process the CSV file
                csv_file = TextIOWrapper(file, encoding='utf-8')
                csv_reader = csv.DictReader(csv_file)

                required_headers = ['Date', 'Wrestler1', 'School1', 'Wrestler2', 'School2', 'WeightClass', 'Winner', 'WinType']
                missing_headers = [header for header in required_headers if header not in csv_reader.fieldnames]
                if missing_headers:
                    flash(f"Missing required columns in CSV: {', '.join(missing_headers)}", 'error')
                    return redirect(url_for('upload_csv'))

                for row_num, row in enumerate(csv_reader, start=1):
                    try:
                        # Parse and format the date
                        match_date = parse_date(row['Date'])
                        formatted_date = match_date.strftime('%Y-%m-%d')

                        # Get or create wrestler1 and wrestler2
                        wrestler1 = get_or_create_wrestler(row['Wrestler1'], row['School1'], row['WeightClass'])
                        wrestler2 = get_or_create_wrestler(row['Wrestler2'], row['School2'], row['WeightClass'])

                        # Check if the match already exists by looking for matches with the same date, wrestlers, and weight class
                        existing_match = Match.query.filter_by(
                            wrestler1_id=wrestler1.id,
                            wrestler2_id=wrestler2.id,
                            date=match_date
                        ).first()

                        if existing_match:
                            # Log or display that this match already exists, so it won't be added again
                            flash(f"Match between {wrestler1.name} and {wrestler2.name} on {formatted_date} already exists.", 'info')
                            continue  # Skip adding the match

                        # Determine the winner
                        winner = wrestler1 if row['Winner'] == row['Wrestler1'] else wrestler2

                        # Create the match
                        match = Match(
                            date=match_date,
                            wrestler1_id=wrestler1.id,
                            wrestler2_id=wrestler2.id,
                            winner_id=winner.id,
                            win_type=row['WinType']
                        )
                        db.session.add(match)

                        # Update win/loss records
                        if winner == wrestler1:
                            wrestler1.wins += 1
                            wrestler2.losses += 1
                        else:
                            wrestler2.wins += 1
                            wrestler1.losses += 1

                        # Commit the new match and the wrestler updates
                        db.session.commit()
                        added_matches.append(match.id)  # Track the added match

                        # Recalculate Elo ratings for both wrestlers involved
                        recalculate_elo(wrestler1)
                        recalculate_elo(wrestler2)

                    except Exception as e:
                        db.session.rollback()
                        flash(f"Error processing row {row_num}: {str(e)}", 'error')
                        logger.error(f"Error processing row {row_num}: {str(e)}")
                        return redirect(url_for('upload_csv'))

                flash(f'Successfully processed {len(added_matches)} new matches.', 'success')
                return redirect(url_for('home'))

            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred while processing the CSV: {str(e)}', 'error')
                logger.error(f"An error occurred while processing the CSV: {str(e)}")
                return redirect(url_for('upload_csv'))

    return render_template('upload_csv.html')



@app.route('/export_rankings')
def export_rankings():
    try:
        output = io.StringIO()
        writer = csv.writer(output)

        # Write CSV headers
        writer.writerow(['Weight Class', 'Rank', 'Name', 'School', 'Wins', 'Losses', 'Elo Rating'])

        # Export rankings for each weight class
        for weight_class in WEIGHT_CLASSES:
            wrestlers = Wrestler.query.filter_by(weight_class=weight_class).all()
            ranked_wrestlers = sorted(wrestlers, key=lambda w: (w.total_matches > 0, w.elo_rating), reverse=True)

            for rank, wrestler in enumerate(ranked_wrestlers, 1):
                writer.writerow([
                    weight_class,
                    rank,
                    wrestler.name,
                    wrestler.school,
                    wrestler.wins,
                    wrestler.losses,
                    f"{wrestler.elo_rating:.2f}"
                ])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='wrestling_rankings.csv'
        )
    except Exception as e:
        logger.error(f"Error in export_rankings: {str(e)}")
        return f"An error occurred: {str(e)}", 500
    
@app.route('/export_wrestlers')
def export_wrestlers():
    try:
        output = io.StringIO()
        writer = csv.writer(output)

        # Write CSV headers
        writer.writerow(['ID', 'Name', 'School', 'Weight Class', 'Wins', 'Losses', 'Elo Rating'])

        # Query all wrestlers and write their data
        wrestlers = Wrestler.query.order_by(Wrestler.weight_class, Wrestler.name).all()
        for wrestler in wrestlers:
            writer.writerow([
                wrestler.id,
                wrestler.name,
                wrestler.school,
                wrestler.weight_class,
                wrestler.wins,
                wrestler.losses,
                f"{wrestler.elo_rating:.2f}"
            ])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='wrestlers.csv'
        )
    except Exception as e:
        logger.error(f"Error in export_wrestlers: {str(e)}")
        logger.error(traceback.format_exc())
        return f"An error occurred: {str(e)}", 500
    
@app.route('/export_matches')
def export_matches():
    try:
        output = io.StringIO()
        writer = csv.writer(output)

        # Write CSV headers
        writer.writerow(['ID', 'Date', 'Wrestler 1', 'Wrestler 2', 'Winner', 'Win Type'])

        # Query all matches and write their data
        matches = Match.query.order_by(Match.date).all()
        for match in matches:
            writer.writerow([
                match.id,
                match.date.strftime('%Y-%m-%d'),
                Wrestler.query.get(match.wrestler1_id).name,
                Wrestler.query.get(match.wrestler2_id).name,
                Wrestler.query.get(match.winner_id).name,
                match.win_type
            ])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='matches.csv'
        )
    except Exception as e:
        logger.error(f"Error in export_matches: {str(e)}")
        logger.error(traceback.format_exc())
        return f"An error occurred: {str(e)}", 500
    
@app.route('/bulk_delete_wrestlers', methods=['POST'])
def bulk_delete_wrestlers():
    wrestler_ids = request.form.getlist('wrestler_ids')  # Get the list of wrestler IDs from the form

    if not wrestler_ids:
        flash('No wrestlers selected for deletion.', 'warning')
        return redirect(url_for('rankings', weight_class=request.form.get('weight_class'))) 

    wrestlers = Wrestler.query.filter(Wrestler.id.in_(wrestler_ids)).all()

    # List to store deleted wrestler data
    deleted_wrestlers_data = []

    for wrestler in wrestlers:
        # Get all matches where this wrestler participated
        matches_as_wrestler1 = wrestler.matches_as_wrestler1.all()
        matches_as_wrestler2 = wrestler.matches_as_wrestler2.all()

        # Prepare data for undo functionality
        wrestler_data = wrestler.to_dict()
        wrestler_data['matches'] = [
            {
                'id': match.id,
                'wrestler1_id': match.wrestler1_id,
                'wrestler2_id': match.wrestler2_id,
                'winner_id': match.winner_id,
                'date': match.date.isoformat(),
                'win_type': match.win_type
            }
            for match in matches_as_wrestler1 + matches_as_wrestler2
        ]
        deleted_wrestlers_data.append(wrestler_data)

        # Delete the matches
        for match in matches_as_wrestler1 + matches_as_wrestler2:
            opponent = match.wrestler2 if match.wrestler1_id == wrestler.id else match.wrestler1
            if match.winner_id == wrestler.id:
                opponent.losses -= 1
            else:
                opponent.wins -= 1
            recalculate_elo(opponent)
            db.session.delete(match)

        # Delete the wrestler
        db.session.delete(wrestler)

    # Store deleted wrestler data for undo functionality
    session['last_action'] = {
        'action': 'bulk_delete_wrestlers',
        'deleted_wrestlers': deleted_wrestlers_data,
        'weight_class': request.form.get('weight_class')
    }

    db.session.commit()

    flash(f'Successfully deleted {len(wrestlers)} wrestler(s) and their associated matches.', 'success')
    return redirect(url_for('rankings', weight_class=wrestlers[0].weight_class if wrestlers else 125))

@app.route('/clear_data', methods=['POST'])
def clear_data():
    try:
        # Clear all matches first
        db.session.query(Match).delete()
        db.session.commit()

        # Clear all wrestlers after matches
        db.session.query(Wrestler).delete()
        db.session.commit()

        flash('All data has been cleared successfully.', 'success')
    except Exception as e:
        db.session.rollback()  # Rollback in case of any errors
        flash(f'An error occurred while clearing data: {str(e)}', 'error')

    return redirect(url_for('home'))



if __name__ == '__main__':
    app.run(debug=True)
