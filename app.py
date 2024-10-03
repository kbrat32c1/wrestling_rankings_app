from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from functools import wraps
import math
import logging
import csv
import io
import difflib
from io import TextIOWrapper
from datetime import timezone
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import event
from flask_migrate import Migrate
from flask import jsonify, request



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wrestling.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Initialize database and migration tool
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Models
class Wrestler(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    school = db.Column(db.String(100), nullable=False)
    weight_class = db.Column(db.Integer, nullable=False)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    elo_rating = db.Column(db.Float, default=1500)
    rpi = db.Column(db.Float, default=0)

    matches_as_wrestler1 = db.relationship('Match', foreign_keys='Match.wrestler1_id', backref='wrestler1', lazy='dynamic')
    matches_as_wrestler2 = db.relationship('Match', foreign_keys='Match.wrestler2_id', backref='wrestler2', lazy='dynamic')

    @property
    def total_matches(self):
        return self.wins + self.losses

    @property
    def hybrid_score(self):
        if self.elo_rating is not None and self.rpi is not None:
            return (0.5 * self.elo_rating) + (0.5 * self.rpi)
        return None

    @property
    def falls(self):
        """ Calculate total number of falls for the wrestler. """
        return self.matches_as_wrestler1.filter_by(win_type='Fall').count() + \
               self.matches_as_wrestler2.filter_by(win_type='Fall').count()

    @property
    def tech_falls(self):
        """ Calculate total number of technical falls for the wrestler. """
        return self.matches_as_wrestler1.filter_by(win_type='Technical Fall').count() + \
               self.matches_as_wrestler2.filter_by(win_type='Technical Fall').count()

    @property
    def major_decisions(self):
        """ Calculate total number of major decisions for the wrestler. """
        return self.matches_as_wrestler1.filter_by(win_type='Major Decision').count() + \
               self.matches_as_wrestler2.filter_by(win_type='Major Decision').count()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'school': self.school,
            'weight_class': self.weight_class,
            'wins': self.wins,
            'losses': self.losses,
            'elo_rating': self.elo_rating,
            'RPI': self.rpi,
            'hybrid': self.hybrid_score,
            'total_matches': self.total_matches,
            'falls': self.falls,  # Dynamically calculated
            'tech_falls': self.tech_falls,  # Dynamically calculated
            'major_decisions': self.major_decisions  # Dynamically calculated
        }


class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Wrestlers involved in the match
    wrestler1_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)
    wrestler2_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)
    
    # Winner of the match
    winner_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)
    winner = db.relationship('Wrestler', foreign_keys=[winner_id], backref='matches_won')
    
    # Type of win (fall, technical fall, major decision, decision, etc.)
    win_type = db.Column(db.String(20), nullable=False)  # Fall, Technical Fall, Major Decision, Decision
    
    # Score tracking for the wrestlers
    wrestler1_score = db.Column(db.Integer, nullable=False, default=0)
    wrestler2_score = db.Column(db.Integer, nullable=False, default=0)
    
    # Time of match for tracking falls and technical falls
    match_time = db.Column(db.Time, nullable=True)  # Time the fall or technical fall occurred (if applicable)

    # Boolean flags for match outcomes
    fall = db.Column(db.Boolean, default=False)
    technical_fall = db.Column(db.Boolean, default=False)
    major_decision = db.Column(db.Boolean, default=False)
    decision = db.Column(db.Boolean, default=False)

    def calculate_win_type(self):
        """
        Automatically calculate the win type (fall, technical fall, major decision, or decision)
        based on the score and set the relevant fields.
        """
        # If fall or technical fall flag is manually set, prioritize them
        if self.fall:
            self.win_type = 'Fall'
        elif self.technical_fall:
            self.win_type = 'Technical Fall'
        else:
            # Calculate win type based on score difference
            score_diff = abs(self.wrestler1_score - self.wrestler2_score)
            if score_diff >= 15:
                self.win_type = 'Technical Fall'
                self.technical_fall = True
            elif 8 <= score_diff < 15:
                self.win_type = 'Major Decision'
                self.major_decision = True
            else:
                self.win_type = 'Decision'
                self.decision = True

        # Ensure boolean flags match the win type
        self.fall = self.win_type == 'Fall'
        self.technical_fall = self.win_type == 'Technical Fall'
        self.major_decision = self.win_type == 'Major Decision'
        self.decision = self.win_type == 'Decision'

    def to_dict(self):
        """
        Convert the Match object to a dictionary for easy serialization.
        """
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d'),
            'wrestler1_id': self.wrestler1_id,
            'wrestler2_id': self.wrestler2_id,
            'winner_id': self.winner_id,
            'win_type': self.win_type,
            'wrestler1_score': self.wrestler1_score,
            'wrestler2_score': self.wrestler2_score,
            'match_time': self.match_time.strftime('%M:%S') if self.match_time else None,
            'fall': self.fall,
            'technical_fall': self.technical_fall,
            'major_decision': self.major_decision,
            'decision': self.decision
        }

# SQLAlchemy event listeners
@event.listens_for(Match, 'before_insert')
def before_insert_listener(mapper, connection, target):
    target.calculate_win_type()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)  # Keep email
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Add admin functionality

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    

# Elo rating functions
def expected_score(rating_a, rating_b):
    return 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))

def update_elo(rating, expected, actual, k_factor=32):
    return rating + k_factor * (actual - expected)

def recalculate_elo(wrestler):
    logger.info(f"Recalculating Elo for {wrestler.name}")
    wrestler.elo_rating = 1500
    matches = list(wrestler.matches_as_wrestler1) + list(wrestler.matches_as_wrestler2)

    if not matches:
        logger.info(f"No matches found for {wrestler.name}. Elo remains {wrestler.elo_rating}")
        return

    for match in matches:
        opponent = match.wrestler2 if match.wrestler1_id == wrestler.id else match.wrestler1
        expected = expected_score(wrestler.elo_rating, opponent.elo_rating)
        actual = 1 if match.winner_id == wrestler.id else 0
        wrestler.elo_rating = update_elo(wrestler.elo_rating, expected, actual)
        logger.info(f"Match on {match.date} against {opponent.name}: expected {expected:.4f}, actual {actual}. Updated Elo: {wrestler.elo_rating:.2f}")

    db.session.commit()

# RPI calculation functions
MIN_MATCHES = 3

def calculate_rpi(wrestler):
    if wrestler.total_matches < MIN_MATCHES:
        logger.info(f"{wrestler.name} has fewer than {MIN_MATCHES} matches. RPI not calculated.")
        return 0, 0, 0, 0

    win_percentage = wrestler.wins / max(wrestler.total_matches, 1)
    matches_as_wrestler1 = wrestler.matches_as_wrestler1.all()
    matches_as_wrestler2 = wrestler.matches_as_wrestler2.all()

    opponents = set(match.wrestler2 if match.wrestler1_id == wrestler.id else match.wrestler1
                    for match in matches_as_wrestler1 + matches_as_wrestler2)

    opponent_win_percentage = (sum(opponent.wins / max(opponent.total_matches, 1) for opponent in opponents) / len(opponents)) if opponents else 0

    opponent_opponents = set()
    for opponent in opponents:
        opponent_opponents.update(match.wrestler2 if match.wrestler1_id == opponent.id else match.wrestler1
                                  for match in opponent.matches_as_wrestler1.all() + opponent.matches_as_wrestler2.all())

    opponent_opponent_win_percentage = (sum(opp_op.wins / max(opp_op.total_matches, 1) for opp_op in opponent_opponents) / len(opponent_opponents)) if opponent_opponents else 0

    rpi = 0.25 * win_percentage + 0.5 * opponent_win_percentage + 0.25 * opponent_opponent_win_percentage

    logger.info(f"RPI for {wrestler.name}: {rpi:.3f}")
    return rpi, win_percentage, opponent_win_percentage, opponent_opponent_win_percentage

def recalculate_rpi(wrestler):
    rpi, win_percentage, opponent_win_percentage, opponent_opponent_win_percentage = calculate_rpi(wrestler)
    wrestler.rpi = rpi
    db.session.commit()

    logger.info(f"RPI recalculated for {wrestler.name}: {rpi:.3f}")
    return rpi

def recalculate_hybrid(wrestler):
    """
    Recalculate the hybrid score for the given wrestler.
    The hybrid score is a combination of Elo rating and RPI.
    It is calculated as: hybrid_score = 0.5 * Elo rating + 0.5 * RPI.
    This function does not need to set the hybrid_score directly as it is a property.
    """
    if wrestler.elo_rating is not None and wrestler.rpi is not None:
        hybrid_score = (0.5 * wrestler.elo_rating) + (0.5 * wrestler.rpi)
        logger.info(f"{wrestler.name}: Hybrid Score recalculated to {hybrid_score}")
    else:
        logger.info(f"{wrestler.name}: Hybrid Score cannot be calculated due to missing values")
    
    db.session.commit()

# Helper function to calculate Dominance Score
def calculate_dominance_score(wrestler):
    matches = wrestler.matches_as_wrestler1.all() + wrestler.matches_as_wrestler2.all()
    
    # Assign points based on the win type
    total_score = 0
    match_count = 0

    for match in matches:
        if match.winner_id == wrestler.id:
            if match.win_type == 'Fall':
                total_score += 6
            elif match.win_type == 'Technical Fall':
                total_score += 5
            elif match.win_type == 'Major Decision':
                total_score += 4
            elif match.win_type == 'Decision':
                total_score += 3
            # Other win types can be added here
            match_count += 1
        else:
            # If the wrestler lost, they get 0 points
            match_count += 1  # Still count the match even if they lost

    if match_count == 0:
        return 0  # Avoid division by zero if the wrestler has no matches

    # Calculate the average dominance score across all matches
    return total_score / match_count

def get_stat_leaders(stat_column, limit=10):
    """
    Fetch top wrestlers based on a specific stat (falls, tech falls, major decisions)
    and return their rank and count of matches with that stat.
    """
    query = db.session.query(Wrestler, db.func.count(Match.id).label(f'{stat_column}_count'))\
        .join(Match, db.or_(Wrestler.id == Match.wrestler1_id, Wrestler.id == Match.wrestler2_id))\
        .filter(Match.win_type == stat_column, Wrestler.id == Match.winner_id)\
        .group_by(Wrestler.id)\
        .order_by(db.func.count(Match.id).desc())\
        .all()

    return query[:limit]  # Limit results to top wrestlers


# Utility functions and decorators (admin_required goes here)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

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
    sort_by = request.args.get('sort_by', 'elo')  # Default to Elo sorting

    # Fetch all wrestlers for the given weight class
    wrestlers = Wrestler.query.filter_by(weight_class=weight_class).all()

    # Calculate Dominance Score for each wrestler
    for wrestler in wrestlers:
        matches_wrestler1 = Match.query.filter_by(wrestler1_id=wrestler.id).all()
        matches_wrestler2 = Match.query.filter_by(wrestler2_id=wrestler.id).all()

        # Combine the matches
        matches = matches_wrestler1 + matches_wrestler2
        total_points = 0
        total_matches = len(matches)

        # Calculate the dominance score for the wrestler
        for match in matches:
            if match.winner_id == wrestler.id:
                if match.win_type == 'Fall':
                    total_points += 6
                elif match.win_type == 'Technical Fall':
                    total_points += 5
                elif match.win_type == 'Major Decision':
                    total_points += 4
                elif match.win_type == 'Decision':
                    total_points += 3

        # Avoid division by zero when calculating the dominance score
        wrestler.dominance_score = total_points / total_matches if total_matches > 0 else 0

    # Handle sorting based on the requested criteria
    if sort_by == 'rpi':
        wrestlers = sorted(wrestlers, key=lambda w: (w.rpi is None, w.rpi), reverse=True)
    elif sort_by == 'hybrid':
        wrestlers = sorted(wrestlers, key=lambda w: (w.hybrid_score is None, w.hybrid_score), reverse=True)
    elif sort_by == 'dominance':
        wrestlers = sorted(wrestlers, key=lambda w: (w.dominance_score is None, w.dominance_score), reverse=True)
    else:
        wrestlers = sorted(wrestlers, key=lambda w: (w.elo_rating is None, w.elo_rating), reverse=True)


    # Calculate win percentage for each wrestler
    for wrestler in wrestlers:
        wrestler.win_percentage = (wrestler.wins / max(wrestler.total_matches, 1)) * 100  # Convert to percentage

    # Render the rankings page with all necessary data
    return render_template('rankings.html', 
                           weight_class=weight_class, 
                           wrestlers=wrestlers, 
                           sort_by=sort_by)


@app.route('/wrestler/<int:wrestler_id>')
def wrestler_detail(wrestler_id):
    # Fetch the wrestler by ID
    wrestler = Wrestler.query.get_or_404(wrestler_id)

    # Query for all wrestlers in the same weight class
    all_wrestlers_in_weight_class = Wrestler.query.filter_by(weight_class=wrestler.weight_class).all()

    # Sort wrestlers by Elo, RPI, Hybrid, and Dominance Score and determine the ranks
    sorted_by_elo = sorted(all_wrestlers_in_weight_class, key=lambda w: w.elo_rating, reverse=True)
    sorted_by_rpi = sorted(all_wrestlers_in_weight_class, key=lambda w: w.rpi if w.rpi else 0, reverse=True)
    sorted_by_hybrid = sorted(all_wrestlers_in_weight_class, key=lambda w: w.hybrid_score if w.hybrid_score else 0, reverse=True)
    sorted_by_dominance = sorted(all_wrestlers_in_weight_class, key=lambda w: calculate_dominance_score(w), reverse=True)

    # Find the ranks of the current wrestler
    elo_rank = sorted_by_elo.index(wrestler) + 1
    rpi_rank = sorted_by_rpi.index(wrestler) + 1
    hybrid_rank = sorted_by_hybrid.index(wrestler) + 1
    dominance_rank = sorted_by_dominance.index(wrestler) + 1

    # Get stats and ranks using the same logic as the leaderboards
    fall_leaders = get_stat_leaders('Fall')
    tech_fall_leaders = get_stat_leaders('Technical Fall')
    major_decision_leaders = get_stat_leaders('Major Decision')

    # Calculate the wrestler's rank for each stat (or None if not ranked)
    fall_rank = next((rank for rank, (wrestler_obj, _) in enumerate(fall_leaders, 1) if wrestler_obj.id == wrestler_id), None)
    tech_fall_rank = next((rank for rank, (wrestler_obj, _) in enumerate(tech_fall_leaders, 1) if wrestler_obj.id == wrestler_id), None)
    major_decision_rank = next((rank for rank, (wrestler_obj, _) in enumerate(major_decision_leaders, 1) if wrestler_obj.id == wrestler_id), None)

    # Get the number of falls, technical falls, and major decisions for the wrestler
    falls = next((count for wrestler_obj, count in fall_leaders if wrestler_obj.id == wrestler_id), 0)
    tech_falls = next((count for wrestler_obj, count in tech_fall_leaders if wrestler_obj.id == wrestler_id), 0)
    major_decisions = next((count for wrestler_obj, count in major_decision_leaders if wrestler_obj.id == wrestler_id), 0)

    # Log the values for troubleshooting
    app.logger.info(f"Wrestler {wrestler.name}: Falls = {falls}, Fall Rank = {fall_rank}")
    app.logger.info(f"Wrestler {wrestler.name}: Tech Falls = {tech_falls}, Tech Fall Rank = {tech_fall_rank}")
    app.logger.info(f"Wrestler {wrestler.name}: Major Decisions = {major_decisions}, Major Decision Rank = {major_decision_rank}")

    # Query for matches where the wrestler is wrestler1 or wrestler2
    matches_wrestler1 = Match.query.filter_by(wrestler1_id=wrestler_id).all()
    matches_wrestler2 = Match.query.filter_by(wrestler2_id=wrestler_id).all()

    # Combine the matches into one list
    matches = matches_wrestler1 + matches_wrestler2

    # Initialize variables for tracking wins, losses, and dominance score
    wins = 0
    losses = 0
    total_points = 0
    total_matches = len(matches)  # Total number of matches

    # Prepare list for match details to be rendered
    match_details = []

    # Loop through each match to calculate wins, losses, and dominance score
    for match in matches:
        # Identify the opponent
        if match.wrestler1_id == wrestler_id:
            opponent = match.wrestler2
            is_winner = match.winner_id == wrestler_id
        else:
            opponent = match.wrestler1
            is_winner = match.winner_id == wrestler_id

        # Count wins and losses
        if is_winner:
            wins += 1
        else:
            losses += 1

        # Calculate points for the dominance score based on win type (Fall, Technical Fall, Major Decision, Decision)
        if is_winner:
            if match.win_type == 'Fall':
                total_points += 6
            elif match.win_type == 'Technical Fall':
                total_points += 5
            elif match.win_type == 'Major Decision':
                total_points += 4
            elif match.win_type == 'Decision':
                total_points += 3

        # Collect match details for display in the template
        match_details.append({
            'id': match.id,
            'date': match.date,
            'opponent': opponent,
            'result': 'Win' if is_winner else 'Loss',
            'win_type': match.win_type,
            'wrestler1_score': match.wrestler1_score,
            'wrestler2_score': match.wrestler2_score,
            'match_time': match.match_time if match.match_time else "N/A"
        })

    # Avoid division by zero when calculating the dominance score
    if total_matches > 0:
        dominance_score = total_points / total_matches
    else:
        dominance_score = 0

    # Render the wrestler profile template with all the calculated data, including rankings and individual stats
    return render_template('wrestler_detail.html', 
                           wrestler=wrestler, 
                           matches=match_details, 
                           wins=wins, 
                           losses=losses, 
                           dominance_score=dominance_score,
                           elo_rank=elo_rank,
                           rpi_rank=rpi_rank,
                           hybrid_rank=hybrid_rank,
                           dominance_rank=dominance_rank,
                           falls=falls,
                           fall_rank=fall_rank,
                           tech_falls=tech_falls,
                           tech_fall_rank=tech_fall_rank,
                           major_decisions=major_decisions,
                           major_decision_rank=major_decision_rank)


@app.route('/add_wrestler', methods=['GET', 'POST'])
@login_required
@admin_required
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
@login_required
@admin_required
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

            # recalculate RPI
            recalculate_rpi(wrestler1)
            recalculate_rpi(wrestler2)

            # recalculate Hybrid
            recalculate_hybrid(wrestler1)
            recalculate_hybrid(wrestler2)      

            # Commit the RPI updates
            db.session.commit()

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
@login_required
@admin_required
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

            # recalculate RPI
            recalculate_rpi(wrestler1)
            recalculate_rpi(wrestler2)

            # recalculate Hybrid
            recalculate_hybrid(wrestler1)
            recalculate_hybrid(wrestler2) 

            # Commit the RPI updates
            db.session.commit()

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
@login_required
@admin_required
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

        # Recalculate RPI for the wrestler in case any match-related data is affected
        # Recalculate Elo ratings for both wrestlers
        recalculate_elo(wrestler1)
        recalculate_elo(wrestler2)

        # recalculate RPI
        recalculate_rpi(wrestler1)
        recalculate_rpi(wrestler2)

        # recalculate Hybrid
        recalculate_hybrid(wrestler1)
        recalculate_hybrid(wrestler2) 
        
        db.session.commit()

        flash(f'Wrestler {wrestler.name} has been updated.', 'success')
        logger.info(f"Updated wrestler: {wrestler.name}, School: {wrestler.school}, Weight Class: {wrestler.weight_class}")
        return redirect(url_for('wrestler_detail', wrestler_id=wrestler.id))
    
    return render_template('edit_wrestler.html', wrestler=wrestler, weight_classes=WEIGHT_CLASSES, schools=D3_WRESTLING_SCHOOLS)

@app.route('/delete_wrestler/<int:wrestler_id>', methods=['POST'])
@login_required
@admin_required
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
        # Recalculate Elo ratings for both wrestlers
            recalculate_elo(wrestler1)
            recalculate_elo(wrestler2)

            # recalculate RPI
            recalculate_rpi(wrestler1)
            recalculate_rpi(wrestler2)

            # recalculate Hybrid
            recalculate_hybrid(wrestler1)
            recalculate_hybrid(wrestler2) 
        db.session.delete(match)

    db.session.delete(wrestler)
    db.session.commit()

    flash(f'Wrestler {wrestler.name} and all their matches have been deleted.', 'success')
    return redirect(url_for('home'))


@app.route('/delete_match/<int:match_id>', methods=['POST'])
@login_required
@admin_required
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

    # Delete the match from the database
    db.session.delete(match)

    # Recalculate Elo ratings, RPI, and Hybrid for both wrestlers
    recalculate_elo(wrestler1)
    recalculate_elo(wrestler2)
    
    recalculate_rpi(wrestler1)
    recalculate_rpi(wrestler2)
    
    recalculate_hybrid(wrestler1)
    recalculate_hybrid(wrestler2)

    # Commit all changes at once to the database
    db.session.commit()

    flash(f'Match between {wrestler1.name} and {wrestler2.name} has been deleted.', 'success')

    # Get wrestler_id from the query string parameter
    wrestler_id = request.args.get('wrestler_id')

    # Redirect back to the wrestler's profile
    return redirect(url_for('wrestler_detail', wrestler_id=wrestler_id))


@app.route('/undo', methods=['POST'])
@login_required
@admin_required
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

        # Recalculate Elo and RPI for restored wrestler
        recalculate_elo(restored_wrestler)
        restored_wrestler.rpi = calculate_rpi(restored_wrestler)
        db.session.commit()

        # Also recalculate Elo and RPI for opponents of the restored matches
        for match_data in last_action.get('matches', []):
            opponent_id = match_data['wrestler2_id'] if match_data['wrestler1_id'] == restored_wrestler.id else match_data['wrestler1_id']
            opponent = Wrestler.query.get(opponent_id)
            recalculate_elo(opponent)
            opponent.rpi = calculate_rpi(opponent)
            db.session.commit()

        flash(f'Wrestler {restored_wrestler.name} and their matches have been restored.', 'success')

    session.pop('last_action', None)
    return redirect(url_for('home'))

# Flexible date parsing function
def parse_date(date_str):
    date_str = date_str.strip()  # Strip any extra spaces
    date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y']  # List of possible date formats

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date '{date_str}' is not in a recognized format. Supported formats: {date_formats}")

def get_or_create_wrestler(name, school, weight_class):
    name = name.strip().title()  # Normalize name (capitalize properly, remove extra spaces)
    school = school.strip().title()  # Normalize school name
    
    # Attempt to find a wrestler with a close match to prevent duplicates from small errors
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

# Function to validate and process CSV with fuzzy matching suggestions
import logging
import difflib
from flask import flash, session
from io import TextIOWrapper
from datetime import datetime

def validate_and_process_csv(file):
    try:
        csv_file = TextIOWrapper(file, encoding='utf-8')
        csv_reader = csv.DictReader(csv_file)

        # Strip any extra spaces from the headers
        csv_reader.fieldnames = [header.strip() for header in csv_reader.fieldnames]

        # Ensure required columns exist
        required_headers = ['Date', 'Wrestler1', 'School1', 'Wrestler2', 'School2', 'WeightClass', 'Wrestler1_Score', 'Wrestler2_Score', 'Winner', 'WinType', 'Match_Time']
        missing_headers = list(set(required_headers).difference(set(csv_reader.fieldnames)))
        if missing_headers:
            flash(f"Missing required columns in CSV: {', '.join(missing_headers)}", 'error')
            logging.error(f"Missing columns: {missing_headers}")
            return False

        # Initialize counters and lists to collect feedback
        added_matches = 0
        skipped_duplicates = 0
        row_errors = 0
        detailed_feedback = []

        # Process rows
        for row_num, row in enumerate(csv_reader, start=1):
            try:
                # Processing each field and stripping whitespace
                wrestler1_name = row['Wrestler1'].strip()
                school1_name = row['School1'].strip()
                wrestler2_name = row['Wrestler2'].strip()
                school2_name = row['School2'].strip()
                weight_class = int(row['WeightClass'].strip())
                wrestler1_score = int(row['Wrestler1_Score'].strip())
                wrestler2_score = int(row['Wrestler2_Score'].strip())
                winner_name = row['Winner'].strip()
                win_type = row['WinType'].strip()

                # Initialize flags for different types of wins
                decision = False
                major_decision = False
                fall = False
                technical_fall = False
                match_time = None

                # Handle win types and match times
                if win_type == 'Decision':
                    decision = True
                    match_time = None  # No match time for decisions
                elif win_type == 'Major Decision':
                    major_decision = True
                    match_time = None  # No match time for major decisions
                elif win_type == 'Fall':
                    fall = True
                    try:
                        match_time = datetime.strptime(row['Match_Time'].strip(), '%M:%S').time()  # Use the match time provided
                    except ValueError:
                        detailed_feedback.append(f"Row {row_num}: Invalid match time format for 'Fall' win type.")
                        row_errors += 1
                        continue
                elif win_type == 'Technical Fall':
                    technical_fall = True
                    try:
                        match_time = datetime.strptime(row['Match_Time'].strip(), '%M:%S').time()  # Use the match time provided
                    except ValueError:
                        detailed_feedback.append(f"Row {row_num}: Invalid match time format for 'Technical Fall' win type.")
                        row_errors += 1
                        continue
                else:
                    detailed_feedback.append(f"Row {row_num}: Unrecognized win type '{win_type}'.")
                    row_errors += 1
                    continue

                # Validate weight class
                if weight_class not in WEIGHT_CLASSES:
                    detailed_feedback.append(f"Row {row_num}: Invalid weight class '{weight_class}'.")
                    row_errors += 1
                    continue

                # Parse the date using the flexible date parsing function
                try:
                    raw_date = row['Date']
                    match_date = parse_date(raw_date)
                except ValueError as e:
                    detailed_feedback.append(f"Row {row_num}: Invalid date format '{raw_date}' ({str(e)}).")
                    row_errors += 1
                    continue

                # Validate other fields
                if not all([wrestler1_name, school1_name, wrestler2_name, school2_name, winner_name]):
                    detailed_feedback.append(f"Row {row_num}: Missing required fields.")
                    row_errors += 1
                    continue

                # Get or create wrestlers
                wrestler1 = get_or_create_wrestler(wrestler1_name, school1_name, weight_class)
                wrestler2 = get_or_create_wrestler(wrestler2_name, school2_name, weight_class)

                # Validate winner
                if winner_name not in [wrestler1.name, wrestler2.name]:
                    # Fuzzy match suggestion using difflib
                    possible_winners = [wrestler1.name, wrestler2.name]
                    closest_matches = difflib.get_close_matches(winner_name, possible_winners, n=1)

                    if closest_matches:
                        suggestion = f"Did you mean '{closest_matches[0]}'?"
                    else:
                        suggestion = "No close match found."

                    detailed_feedback.append(f"Row {row_num}: Winner '{winner_name}' does not match wrestler1 or wrestler2. {suggestion}")
                    row_errors += 1
                    continue

                # Check for existing match
                existing_match = Match.query.filter_by(
                    wrestler1_id=wrestler1.id,
                    wrestler2_id=wrestler2.id,
                    date=match_date
                ).first()

                if existing_match:
                    detailed_feedback.append(f"Row {row_num}: Duplicate match detected (already exists).")
                    skipped_duplicates += 1
                    continue  # Skip if the match already exists

                # Create and add new match
                winner = wrestler1 if winner_name == wrestler1.name else wrestler2
                new_match = Match(
                    date=match_date,
                    wrestler1_id=wrestler1.id,
                    wrestler2_id=wrestler2.id,
                    winner_id=winner.id,
                    win_type=win_type,
                    wrestler1_score=wrestler1_score,
                    wrestler2_score=wrestler2_score,
                    match_time=match_time,  # Only set match time for 'Fall' or 'Technical Fall'
                    decision=decision,
                    major_decision=major_decision,
                    fall=fall,
                    technical_fall=technical_fall
                )
                db.session.add(new_match)

                # Update win/loss records
                if winner == wrestler1:
                    wrestler1.wins += 1
                    wrestler2.losses += 1
                else:
                    wrestler2.wins += 1
                    wrestler1.losses += 1

                # Recalculate Elo, RPI, and Hybrid for both wrestlers
                recalculate_elo(wrestler1)
                recalculate_elo(wrestler2)
                recalculate_rpi(wrestler1)
                recalculate_rpi(wrestler2)
                recalculate_hybrid(wrestler1)
                recalculate_hybrid(wrestler2)

                added_matches += 1
                detailed_feedback.append(f"Row {row_num}: Match added successfully.")

            except Exception as e:
                detailed_feedback.append(f"Row {row_num}: Error processing match ({str(e)}).")
                row_errors += 1
                db.session.rollback()  # Rollback only if the current row fails
                continue

        # Commit changes after processing all rows
        db.session.commit()

        # Provide feedback after processing
        flash(f"CSV file processed successfully! {added_matches} matches added, {skipped_duplicates} duplicates skipped, {row_errors} errors encountered.", 'success')
        
        # Optionally, store detailed feedback in session for display on the next page
        session['csv_feedback'] = detailed_feedback

        return True

    except Exception as e:
        flash(f"An error occurred during CSV processing: {str(e)}", 'error')
        logging.error(f"An error occurred during CSV processing: {str(e)}")
        return False


    
@app.route('/export_rankings')
@login_required
@admin_required
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
@login_required
@admin_required
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
@login_required
@admin_required
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
@login_required
@admin_required
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
@login_required
@admin_required
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

#not needed
@app.route('/recalculate_all_rpi')
@login_required
@admin_required
def recalculate_all_rpi():
    wrestlers = Wrestler.query.all()
    for wrestler in wrestlers:
        recalculate_rpi(wrestler)
        recalculate_hybrid(wrestler)
    db.session.commit()
    flash('RPI and Hybrid scores recalculated for all wrestlers.', 'success')
    return redirect(url_for('home'))



@app.route('/upload_csv', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_csv():
    if request.method == 'POST':
        # Clear previous feedback from session before processing a new file
        session.pop('csv_feedback', None)

        # Check if a file was uploaded
        if 'file' not in request.files or request.files['file'].filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        file = request.files['file']

        # Check if the uploaded file is a CSV
        if file.filename.endswith('.csv'):
            try:
                # Call the function to process the CSV
                result = validate_and_process_csv(file)

                # If processing was successful
                if result:
                    flash('CSV uploaded and processed successfully!', 'success')
                else:
                    flash('CSV upload failed. Check the feedback for details.', 'error')
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload a CSV file.', 'error')

        return redirect(url_for('upload_csv'))

    # For GET request, show the form and fetch feedback from the session
    csv_feedback = session.pop('csv_feedback', None)
    return render_template('upload_csv.html', csv_feedback=csv_feedback)

@app.route('/search', methods=['GET'])
def search_wrestler():
    query = request.args.get('query', '')
    if query:
        # Search for wrestlers whose names match the query (case-insensitive)
        wrestlers = Wrestler.query.filter(Wrestler.name.ilike(f"%{query}%")).all()
    else:
        wrestlers = []

    # Render a template to show the search results
    return render_template('search_results.html', query=query, wrestlers=wrestlers)

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('query', '')
    print(f"Received query: {query}")  # Log the query

    if query:
        # Find wrestlers whose names match the query (case-insensitive search)
        wrestlers = Wrestler.query.filter(Wrestler.name.ilike(f"%{query}%")).all()
        print(f"Found wrestlers: {[wrestler.name for wrestler in wrestlers]}")  # Log found wrestlers

        # Extract wrestler names and their IDs to return as suggestions
        wrestler_names = [{"name": wrestler.name, "id": wrestler.id} for wrestler in wrestlers]
    else:
        wrestler_names = []

    # Return the list of wrestler names and IDs as a JSON response
    print(f"Returning suggestions: {wrestler_names}")  # Log the returned suggestions
    return jsonify(wrestler_names)


@app.route('/global-leaderboards', methods=['GET'])
def global_leaderboards():
    # Fetch top wrestlers for each win type using the helper function
    fall_leaders = get_stat_leaders('Fall', limit=10)
    tech_fall_leaders = get_stat_leaders('Technical Fall', limit=10)
    major_decision_leaders = get_stat_leaders('Major Decision', limit=10)

    return render_template('global_leaderboards.html',
                           fall_leaders=fall_leaders,
                           tech_fall_leaders=tech_fall_leaders,
                           major_decision_leaders=major_decision_leaders)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # Check if user exists and the password is correct
        if user and user.check_password(password):
            login_user(user)  # Logs the user in
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

# This function can be used to create a new admin user
@app.route('/create_admin')
def create_admin():
    if User.query.filter_by(username='admin').first() is None:
        # Define new user details and set the is_admin flag
        new_user = User(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('password123', method='pbkdf2:sha256'),  # Secure password hash
            is_admin=True  # Set admin privileges
        )
        db.session.add(new_user)
        db.session.commit()
        return "Admin user created successfully!"
    return "Admin user already exists."

if __name__ == '__main__':
    app.run(debug=True)
