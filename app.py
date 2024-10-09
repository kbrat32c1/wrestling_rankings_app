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
import json

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wrestling.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Initialize the database
db = SQLAlchemy(app)

# Initialize Flask-Migrate for handling migrations
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
D3_WRESTLING_SCHOOLS = {
    # Region 1 (18 schools)
    "Bridgewater State University": {"region": 1, "conference": "NECWA"},
    "Johnson & Wales University": {"region": 1, "conference": "NECWA"},
    "Maine Maritime Academy": {"region": 1, "conference": "NECWA"},
    "New England College": {"region": 1, "conference": "NECWA"},
    "Norwich University": {"region": 1, "conference": "NECWA"},
    "Plymouth State University": {"region": 1, "conference": "NECWA"},
    "Rhode Island College": {"region": 1, "conference": "NECWA"},
    "Roger Williams University": {"region": 1, "conference": "NECWA"},
    "Springfield College": {"region": 1, "conference": "NECWA"},
    "Trinity College": {"region": 1, "conference": "NECWA"},
    "University of Southern Maine": {"region": 1, "conference": "NECWA"},
    "US Coast Guard Academy": {"region": 1, "conference": "NECWA"},
    "Utica College": {"region": 1, "conference": "SUNYAC"},
    "Castleton": {"region": 1, "conference": "NECWA"},
    "Wesleyan University": {"region": 1, "conference": "NECWA"},
    "Western New England University": {"region": 1, "conference": "NECWA"},
    "Williams College": {"region": 1, "conference": "NECWA"},
    "Worcester Polytechnic Institute": {"region": 1, "conference": "NECWA"},

    # Region 2 (19 schools)
    "Alfred State University": {"region": 2, "conference": "AMCC"},
    "Centenary University": {"region": 2, "conference": "AEC"},
    "Elmira College": {"region": 2, "conference": "Empire"},
    "Ithaca College": {"region": 2, "conference": "Empire"},
    "Keystone College": {"region": 2, "conference": "Land."},
    "Lycoming College": {"region": 2, "conference": "Land."},
    "New Jersey City University": {"region": 2, "conference": "NJAC"},
    "Penn State Erie, The Behrend College": {"region": 2, "conference": "AMCC"},
    "Pennsylvania College of Technology": {"region": 2, "conference": "AMCC"},
    "Rochester Institute of Technology": {"region": 2, "conference": "SUNYAC"},
    "St. John's Fisher University": {"region": 2, "conference": "SUNYAC"},
    "Stevens Institute of Technology": {"region": 2, "conference": "MAC"},
    "SUNY - Brockport": {"region": 2, "conference": "SUNYAC"},
    "SUNY - Cortland": {"region": 2, "conference": "SUNYAC"},
    "SUNY - Oneonta": {"region": 2, "conference": "SUNYAC"},
    "SUNY - Oswego": {"region": 2, "conference": "SUNYAC"},
    "University of Pittsburgh at Bradford": {"region": 2, "conference": "AMCC"},
    "Hunter College": {"region": 2, "conference": "CUNYAC"},
    "Wilkes University": {"region": 2, "conference": "Land."},

    # Region 3 (18 schools)
    "Alvernia University": {"region": 3, "conference": "MAC"},
    "Delaware Valley College": {"region": 3, "conference": "MAC"},
    "Elizabethtown College": {"region": 3, "conference": "Land."},
    "Gettysburg College": {"region": 3, "conference": "Cent."},
    "Johns Hopkins University": {"region": 3, "conference": "Cent."},
    "King's College": {"region": 3, "conference": "MAC"},
    "Marymount University": {"region": 3, "conference": "AEC"},
    "McDaniel College": {"region": 3, "conference": "Cent."},
    "Messiah University": {"region": 3, "conference": "MAC"},
    "Misericordia University": {"region": 3, "conference": "MAC"},
    "Muhlenberg College": {"region": 3, "conference": "Cent."},
    "New York University": {"region": 3, "conference": "UAA"},
    "Penn State Altoona": {"region": 3, "conference": "AMCC"},
    "The College of New Jersey": {"region": 3, "conference": "NJAC"},
    "University of Scranton": {"region": 3, "conference": "Land."},
    "Ursinus College": {"region": 3, "conference": "Cent."},
    "US Merchant Marine Academy": {"region": 3, "conference": "Cent."},
    "York College of Pennsylvania": {"region": 3, "conference": "MAC"},

    # Region 4 (20 schools)
    "Averett University": {"region": 4, "conference": "ODAC"},
    "Baldwin Wallace University": {"region": 4, "conference": "OAC"},
    "Ferrum College": {"region": 4, "conference": "ODAC"},
    "Greensboro College": {"region": 4, "conference": "ODAC"},
    "Heidelberg University": {"region": 4, "conference": "OAC"},
    "Hiram College": {"region": 4, "conference": "NCAC"},
    "Muskingum University": {"region": 4, "conference": "OAC"},
    "Ohio Northern University": {"region": 4, "conference": "OAC"},
    "Otterbein University": {"region": 4, "conference": "OAC"},
    "Randolph College": {"region": 4, "conference": "ODAC"},
    "Roanoke College": {"region": 4, "conference": "ODAC"},
    "Saint Vincent College": {"region": 4, "conference": "PAC"},
    "Shenandoah University": {"region": 4, "conference": "ODAC"},
    "Southern Virginia University": {"region": 4, "conference": "ODAC"},
    "Thiel College": {"region": 4, "conference": "PAC"},
    "University of Mount Union": {"region": 4, "conference": "OAC"},
    "Washington & Jefferson College": {"region": 4, "conference": "PAC"},
    "Washington and Lee University": {"region": 4, "conference": "ODAC"},
    "Waynesburg University": {"region": 4, "conference": "PAC"},
    "Wilmington College": {"region": 4, "conference": "OAC"},

    # Region 5 (18 schools)
    "Adrian College": {"region": 5, "conference": "MIAA"},
    "Albion College": {"region": 5, "conference": "MIAA"},
    "Alma College": {"region": 5, "conference": "MIAA"},
    "Aurora University": {"region": 5, "conference": "CCIW"},
    "Case Western Reserve University": {"region": 5, "conference": "UAA"},
    "Elmhurst College": {"region": 5, "conference": "CCIW"},
    "John Carroll University": {"region": 5, "conference": "OAC"},
    "Manchester University": {"region": 5, "conference": "HCAC"},
    "Millikin University": {"region": 5, "conference": "CCIW"},
    "Mount St. Joseph University": {"region": 5, "conference": "HCAC"},
    "North Central College": {"region": 5, "conference": "CCIW"},
    "Ohio Wesleyan University": {"region": 5, "conference": "NCAC"},
    "Olivet College": {"region": 5, "conference": "MIAA"},
    "Trine University": {"region": 5, "conference": "MIAA"},
    "University of Chicago": {"region": 5, "conference": "UAA"},
    "University of Wisconsin-Whitewater": {"region": 5, "conference": "WIAC"},
    "Wabash College": {"region": 5, "conference": "HCAC"},
    "Wheaton College": {"region": 5, "conference": "CCIW"},

    # Region 6 (18 schools)
    "Blackburn College": {"region": 6, "conference": "SLIAC"},
    "Buena Vista University": {"region": 6, "conference": "ARC"},
    "Central College": {"region": 6, "conference": "ARC"},
    "Coe College": {"region": 6, "conference": "ARC"},
    "Cornell College": {"region": 6, "conference": "MWC"},
    "Eureka College": {"region": 6, "conference": "SLIAC"},
    "Fontbonne University": {"region": 6, "conference": "SLIAC"},
    "Huntingdon College": {"region": 6, "conference": "CCS"},
    "Illinois Wesleyan University": {"region": 6, "conference": "CCIW"},
    "Loras College": {"region": 6, "conference": "ARC"},
    "Luther College": {"region": 6, "conference": "ARC"},
    "Nebraska Wesleyan University": {"region": 6, "conference": "ARC"},
    "Schreiner University": {"region": 6, "conference": "SLIAC"},
    "Simpson College": {"region": 6, "conference": "ARC"},
    "University of Dubuque": {"region": 6, "conference": "ARC"},
    "University of the Ozarks": {"region": 6, "conference": "SLIAC"},
    "Wartburg College": {"region": 6, "conference": "ARC"},
    "Westminster": {"region": 6, "conference": "SLIAC"},

    # Region 7 (16 schools)
    "Augsburg University": {"region": 7, "conference": "MIAC"},
    "Augustana College": {"region": 7, "conference": "CCIW"},
    "Carthage College": {"region": 7, "conference": "CCIW"},
    "Concordia College - Moorhead": {"region": 7, "conference": "MIAC"},
    "Concordia University Wisconsin": {"region": 7, "conference": "CCIW"},
    "Lakeland University": {"region": 7, "conference": "CCIW"},
    "Linfield University": {"region": 7, "conference": "NWC"},
    "Milwaukee School of Engineering": {"region": 7, "conference": "CCIW"},
    "Northland College": {"region": 7, "conference": "WIAC"},
    "Pacific University": {"region": 7, "conference": "NWC"},
    "Saint Johns University": {"region": 7, "conference": "WIAC"},
    "University of Wisconsin-Eau Claire": {"region": 7, "conference": "WIAC"},
    "University of Wisconsin-La Crosse": {"region": 7, "conference": "WIAC"},
    "University of Wisconsin-Oshkosh": {"region": 7, "conference": "WIAC"},
    "University of Wisconsin-Platteville": {"region": 7, "conference": "WIAC"},
    "University of Wisconsin-Stevens Point": {"region": 7, "conference": "WIAC"}
}


SCHOOL_ALIASES = {
    "Bridgewater State University": ["Bridgewater State", "BSU"],
    "Johnson & Wales University": ["Johnson & Wales", "JWU", "Johnson Wales", "Johnson and Wales"],
    "Maine Maritime Academy": ["Maine Maritime", "MMA"],
    "New England College": ["New England College", "NEC"],
    "Norwich University": ["Norwich"],
    "Plymouth State University": ["Plymouth State", "PSU"],
    "Rhode Island College": ["Rhode Island", "RIC"],
    "Roger Williams University": ["Roger Williams", "RWU"],
    "Springfield College": ["Springfield"],
    "Trinity College": ["Trinity", "Trinity (CT)"],
    "University of Southern Maine": ["Southern Maine", "USM"],
    "US Coast Guard Academy": ["Coast Guard", "USCGA", "U.S. Coast Guard Academy"],
    "Utica College": ["Utica"],
    "Castleton": ["Castleton University"],
    "Wesleyan University": ["Wesleyan", "Wesleyan (CT)"],
    "Western New England University": ["Western New England", "WNE"],
    "Williams College": ["Williams"],
    "Worcester Polytechnic Institute": ["Worcester Poly", "WPI"],
    "Alfred State University": ["Alfred State"],
    "Centenary University": ["Centenary", "Centenary (NJ)"],
    "Elmira College": ["Elmira"],
    "Ithaca College": ["Ithaca"],
    "Keystone College": ["Keystone"],
    "Lycoming College": ["Lycoming"],
    "New Jersey City University": ["NJCU", "New Jersey City"],
    "Penn State Erie, The Behrend College": ["Penn State Erie", "Behrend College", "PSU Behrend"],
    "Pennsylvania College of Technology": ["Penn College of Tech", "Penn Tech"],
    "Rochester Institute of Technology": ["RIT", "Rochester Tech"],
    "St. John's Fisher University": ["St. John's Fisher", "SJFC"],
    "Stevens Institute of Technology": ["Stevens Tech", "Stevens"],
    "SUNY - Brockport": ["Brockport", "SUNY Brockport"],
    "SUNY - Cortland": ["Cortland", "SUNY Cortland"],
    "SUNY - Oneonta": ["Oneonta", "SUNY Oneonta"],
    "SUNY - Oswego": ["Oswego", "SUNY Oswego"],
    "University of Pittsburgh at Bradford": ["Pitt Bradford", "University of Pittsburgh Bradford"],
    "Hunter College": ["Hunter"],
    "Wilkes University": ["Wilkes"],
    "Alvernia University": ["Alvernia"],
    "Delaware Valley College": ["Delaware Valley", "Del Val"],
    "Elizabethtown College": ["Elizabethtown", "E-town"],
    "Gettysburg College": ["Gettysburg"],
    "Johns Hopkins University": ["Johns Hopkins", "Hopkins", "JHU"],
    "King's College": ["King's"],
    "Marymount University": ["Marymount"],
    "McDaniel College": ["McDaniel"],
    "Messiah University": ["Messiah"],
    "Misericordia University": ["Misericordia"],
    "Muhlenberg College": ["Muhlenberg"],
    "New York University": ["NYU", "New York U"],
    "Penn State Altoona": ["PSU Altoona", "Penn State Altoona"],
    "The College of New Jersey": ["TCNJ", "College of New Jersey"],
    "University of Scranton": ["Scranton"],
    "Ursinus College": ["Ursinus"],
    "US Merchant Marine Academy": ["Merchant Marine", "USMMA"],
    "York College of Pennsylvania": ["York College PA", "York PA"],
    "Averett University": ["Averett"],
    "Baldwin Wallace University": ["Baldwin Wallace", "BW"],
    "Ferrum College": ["Ferrum"],
    "Greensboro College": ["Greensboro"],
    "Heidelberg University": ["Heidelberg"],
    "Hiram College": ["Hiram"],
    "Muskingum University": ["Muskingum"],
    "Ohio Northern University": ["Ohio Northern", "ONU"],
    "Otterbein University": ["Otterbein"],
    "Randolph College": ["Randolph"],
    "Roanoke College": ["Roanoke"],
    "Saint Vincent College": ["St. Vincent", "Saint Vincent"],
    "Shenandoah University": ["Shenandoah"],
    "Southern Virginia University": ["Southern Virginia", "SVU"],
    "Thiel College": ["Thiel"],
    "University of Mount Union": ["Mount Union", "UMU"],
    "Washington & Jefferson College": ["Washington & Jefferson", "W&J"],
    "Washington and Lee University": ["Washington and Lee", "W&L"],
    "Waynesburg University": ["Waynesburg"],
    "Wilmington College": ["Wilmington"],
    "Adrian College": ["Adrian"],
    "Albion College": ["Albion"],
    "Alma College": ["Alma"],
    "Aurora University": ["Aurora"],
    "Case Western Reserve University": ["Case Western", "CWRU"],
    "Elmhurst College": ["Elmhurst"],
    "John Carroll University": ["John Carroll", "JCU"],
    "Manchester University": ["Manchester"],
    "Millikin University": ["Millikin"],
    "Mount St. Joseph University": ["Mount St. Joseph", "MSJ"],
    "North Central College": ["North Central", "NCC"],
    "Ohio Wesleyan University": ["Ohio Wesleyan"],
    "Olivet College": ["Olivet"],
    "Trine University": ["Trine"],
    "University of Chicago": ["Chicago", "UChicago"],
    "University of Wisconsin-Whitewater": ["Wisconsin Whitewater", "UW Whitewater", "Wisconsin-Whitewater"],
    "Wabash College": ["Wabash"],
    "Wheaton College": ["Wheaton"],
    "Blackburn College": ["Blackburn"],
    "Buena Vista University": ["Buena Vista", "BVU"],
    "Central College": ["Central"],
    "Coe College": ["Coe"],
    "Cornell College": ["Cornell"],
    "Eureka College": ["Eureka"],
    "Fontbonne University": ["Fontbonne"],
    "Huntingdon College": ["Huntingdon"],
    "Illinois Wesleyan University": ["Illinois Wesleyan", "IWU"],
    "Loras College": ["Loras"],
    "Luther College": ["Luther"],
    "Nebraska Wesleyan University": ["Nebraska Wesleyan", "NWU"],
    "Schreiner University": ["Schreiner"],
    "Simpson College": ["Simpson"],
    "University of Dubuque": ["Dubuque"],
    "University of the Ozarks": ["Ozarks", "U of Ozarks"],
    "Wartburg College": ["Wartburg"],
    "Westminster": ["Westminster"],
    "Augsburg University": ["Augsburg"],
    "Augustana College": ["Augustana"],
    "Carthage College": ["Carthage"],
    "Concordia College - Moorhead": ["Concordia Moorhead", "Concordia"],
    "Concordia University Wisconsin": ["Concordia Wisconsin", "CUW"],
    "Lakeland University": ["Lakeland"],
    "Linfield University": ["Linfield"],
    "Milwaukee School of Engineering": ["MSOE", "Milwaukee Engineering"],
    "Northland College": ["Northland"],
    "Pacific University": ["Pacific"],
    "Saint Johns University": ["Saint Johns", "St. Johns", "SJU"],
    "University of Wisconsin-Eau Claire": ["Wisconsin-Eau Claire", "Wisconsin Eau Claire", "UW Eau Claire"],
    "University of Wisconsin-La Crosse": ["Wisconsin La Crosse", "UW La Crosse"],
    "University of Wisconsin-Oshkosh": ["Wisconsin Oshkosh", "UW Oshkosh"],
    "University of Wisconsin-Platteville": ["Wisconsin Platteville", "UW Platteville"],
    "University of Wisconsin-Stevens Point": ["Wisconsin Stevens Point", "UW Stevens Point"]
}


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
    dominance_score = db.Column(db.Float, nullable=False, default=0.0)  # New field

    # Updated relationships using back_populates to avoid overlaps
    matches_as_wrestler1 = db.relationship('Match', foreign_keys='Match.wrestler1_id', lazy='dynamic', back_populates='wrestler1')
    matches_as_wrestler2 = db.relationship('Match', foreign_keys='Match.wrestler2_id', lazy='dynamic', back_populates='wrestler2')

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
        return self.matches_as_wrestler1.filter_by(win_type='Fall').count() + \
               self.matches_as_wrestler2.filter_by(win_type='Fall').count()

    @property
    def tech_falls(self):
        return self.matches_as_wrestler1.filter_by(win_type='Technical Fall').count() + \
               self.matches_as_wrestler2.filter_by(win_type='Technical Fall').count()

    @property
    def major_decisions(self):
        return self.matches_as_wrestler1.filter_by(win_type='Major Decision').count() + \
               self.matches_as_wrestler2.filter_by(win_type='Major Decision').count()

    # Method to recalculate dominance score
    def calculate_dominance_score(self):
        matches = self.matches_as_wrestler1.all() + self.matches_as_wrestler2.all()

        # Assign points based on win type
        total_score = 0
        match_count = len(matches)

        for match in matches:
            if match.winner_id == self.id:
                if match.win_type == 'Fall':
                    total_score += 6
                elif match.win_type == 'Technical Fall':
                    total_score += 5
                elif match.win_type == 'Major Decision':
                    total_score += 4
                elif match.win_type == 'Decision':
                    total_score += 3

        # Avoid division by zero
        if match_count == 0:
            self.dominance_score = 0
        else:
            self.dominance_score = round(total_score / match_count, 2)

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
            'falls': self.falls,
            'tech_falls': self.tech_falls,
            'major_decisions': self.major_decisions,
            'dominance_score': self.dominance_score  # Added to_dict output
        }


class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Wrestlers involved in the match
    wrestler1_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)
    wrestler2_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)

    # Relationships to wrestler using back_populates to avoid conflicts
    wrestler1 = db.relationship('Wrestler', foreign_keys=[wrestler1_id], back_populates='matches_as_wrestler1')
    wrestler2 = db.relationship('Wrestler', foreign_keys=[wrestler2_id], back_populates='matches_as_wrestler2')

    # Winner of the match
    winner_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)
    winner = db.relationship('Wrestler', foreign_keys=[winner_id], backref='matches_won')

    # Type of win (fall, technical fall, major decision, decision, etc.)
    win_type = db.Column(db.String(20), nullable=False)  # Fall, Technical Fall, Major Decision, Decision, Injury Default, SV-1

    # Score tracking for the wrestlers
    wrestler1_score = db.Column(db.Integer, nullable=False, default=0)
    wrestler2_score = db.Column(db.Integer, nullable=False, default=0)

    # Time of match for tracking falls, technical falls, or sudden victory
    match_time = db.Column(db.Time, nullable=True)  # Time the fall, technical fall, or SV-1 occurred (if applicable)

    # Boolean flags for match outcomes
    fall = db.Column(db.Boolean, default=False)
    technical_fall = db.Column(db.Boolean, default=False)
    major_decision = db.Column(db.Boolean, default=False)
    decision = db.Column(db.Boolean, default=False)
    injury_default = db.Column(db.Boolean, default=False)  # New flag for Injury Default
    sudden_victory = db.Column(db.Boolean, default=False)  # New flag for SV-1 (Sudden Victory)

    def calculate_win_type(self):
        """
        Automatically calculate the win type (fall, technical fall, major decision, decision, injury default, or SV-1)
        based on the score and set the relevant fields.
        """
        # If fall, technical fall, injury default, or sudden victory flags are set, prioritize them
        if self.fall:
            self.win_type = 'Fall'
        elif self.technical_fall:
            self.win_type = 'Technical Fall'
        elif self.injury_default:
            self.win_type = 'Injury Default'
        elif self.sudden_victory:
            self.win_type = 'SV-1'
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
        self.injury_default = self.win_type == 'Injury Default'
        self.sudden_victory = self.win_type == 'SV-1'

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
            'decision': self.decision,
            'injury_default': self.injury_default,  # Added to dictionary output
            'sudden_victory': self.sudden_victory   # Added to dictionary output
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
    


class CSVUploadReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Track the user who uploaded the file (optional)
    total_matches = db.Column(db.Integer, nullable=False, default=0)
    added_matches = db.Column(db.Integer, nullable=False, default=0)
    skipped_duplicates = db.Column(db.Integer, nullable=False, default=0)
    row_errors = db.Column(db.Integer, nullable=False, default=0)
    detailed_feedback = db.Column(db.Text, nullable=False)  # Store detailed feedback as JSON or text
    match_ids = db.Column(db.Text, nullable=False)  # Store added match IDs as a JSON array for reversion
    is_reverted = db.Column(db.Boolean, nullable=False, default=False)  # Track if the report has been reverted

def to_dict(self):
    try:
        feedback = json.loads(self.detailed_feedback)
    except json.JSONDecodeError:
        feedback = []  # Fallback if there's an issue with the feedback data

    try:
        match_ids = json.loads(self.match_ids)
    except json.JSONDecodeError:
        match_ids = []  # Fallback if there's an issue with the match_ids data

    return {
        'id': self.id,
        'uploaded_at': self.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
        'total_matches': self.total_matches,
        'added_matches': self.added_matches,
        'skipped_duplicates': self.skipped_duplicates,
        'row_errors': self.row_errors,
        'detailed_feedback': feedback,
        'match_ids': match_ids,
        'is_reverted': self.is_reverted  # **New flag** added to the dictionary output
    }




    

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
    match_count = len(matches)  # Count total matches upfront

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
            # You can add more win types as needed, with default behavior for unrecognized ones

    if match_count == 0:
        return 0  # Avoid division by zero if the wrestler has no matches

    # Calculate the average dominance score across all matches
    return round(total_score / match_count, 2)  # Round to 2 decimal places for readability



def recalculate_dominance(wrestler):
    """
    Recalculates and updates the dominance score for a given wrestler.
    """
    matches = wrestler.matches_as_wrestler1.all() + wrestler.matches_as_wrestler2.all()
    
    # Assign points based on the win type
    total_score = 0
    match_count = len(matches)  # Count total matches upfront

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
            # You can add more win types as needed

    if match_count == 0:
        return 0  # Avoid division by zero if the wrestler has no matches

    # Calculate the average dominance score across all matches
    dominance_score = round(total_score / match_count, 2)  # Round to 2 decimal places for readability
    wrestler.dominance_score = dominance_score  # Save it back to the wrestler

    return dominance_score


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

def normalize_school_name(school_name):
    """
    Converts an alternative school name to the official name if an alias exists.
    If no alias is found, it returns the original name.
    """
    # Clean up any extra spaces
    school_name = school_name.strip()

    # Check if the name is already the official name
    if school_name in D3_WRESTLING_SCHOOLS:
        return school_name
    
    # Check if the name is in the aliases
    for main_name, aliases in SCHOOL_ALIASES.items():
        if school_name in aliases:
            app.logger.info(f"Normalizing '{school_name}' to '{main_name}'")
            return main_name  # Return the official name

    # If no match, return the original name
    app.logger.info(f"No alias found for '{school_name}', using original")
    return school_name


# Assuming D3_WRESTLING_SCHOOLS is a dictionary containing the schools, regions, and conferences

def get_region_and_conference(school_name):
    """
    Get the region and conference for a given school name
    by cross-referencing the D3_WRESTLING_SCHOOLS dictionary.
    """
    # Normalize school name for comparison (in case of case mismatch)
    normalized_school_name = school_name.strip().title()

    # Return region and conference if school is found
    if normalized_school_name in D3_WRESTLING_SCHOOLS:
        return D3_WRESTLING_SCHOOLS[normalized_school_name]["region"], D3_WRESTLING_SCHOOLS[normalized_school_name]["conference"]
    else:
        return None, None  # Return None if the school is not found








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
    selected_region = request.args.get('region', None)
    selected_conference = request.args.get('conference', None)

    # Fetch all wrestlers for the given weight class
    wrestlers = Wrestler.query.filter_by(weight_class=weight_class).all()

    # Assign region and conference based on the school
    for wrestler in wrestlers:
        wrestler_details = D3_WRESTLING_SCHOOLS.get(wrestler.school)
        if wrestler_details:
            wrestler.region = wrestler_details["region"]
            wrestler.conference = wrestler_details["conference"]
        else:
            wrestler.region = "Unknown"
            wrestler.conference = "Unknown"
            print(f"School '{wrestler.school}' not found in D3_WRESTLING_SCHOOLS")

    # Get unique regions and conferences from D3_WRESTLING_SCHOOLS, not just the current wrestlers
    regions = sorted(set(school_data["region"] for school_data in D3_WRESTLING_SCHOOLS.values()))
    conferences = sorted(set(school_data["conference"] for school_data in D3_WRESTLING_SCHOOLS.values()))

    # Filter by selected region or conference if applicable
    if selected_region:
        wrestlers = [wrestler for wrestler in wrestlers if str(wrestler.region) == selected_region]
    if selected_conference:
        wrestlers = [wrestler for wrestler in wrestlers if wrestler.conference == selected_conference]

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
    elif sort_by == 'region':
        wrestlers = sorted(wrestlers, key=lambda w: w.region)  # Sort by region (ascending order)
    elif sort_by == 'conference':
        wrestlers = sorted(wrestlers, key=lambda w: w.conference)  # Sort by conference (alphabetical)
    else:
        wrestlers = sorted(wrestlers, key=lambda w: (w.elo_rating is None, w.elo_rating), reverse=True)

    # Calculate win percentage for each wrestler
    for wrestler in wrestlers:
        wrestler.win_percentage = (wrestler.wins / max(wrestler.total_matches, 1)) * 100  # Convert to percentage

    # Handle clearing filters by checking if both region and conference are None
    if selected_region or selected_conference:
        clear_filters = True
    else:
        clear_filters = False

    # Render the rankings page with all necessary data, passing the current filters and sorting criteria
    return render_template('rankings.html', 
                           weight_class=weight_class, 
                           wrestlers=wrestlers, 
                           sort_by=sort_by,
                           selected_region=selected_region,
                           selected_conference=selected_conference,
                           clear_filters=clear_filters,
                           regions=regions,
                           conferences=conferences)


@app.route('/wrestler/<int:wrestler_id>')
def wrestler_detail(wrestler_id):
    # Fetch the wrestler by ID
    wrestler = Wrestler.query.get_or_404(wrestler_id)

    # Cross-reference the school to assign region and conference
    school_info = D3_WRESTLING_SCHOOLS.get(wrestler.school, {})
    wrestler_region = school_info.get("region", "Unknown")
    wrestler_conference = school_info.get("conference", "Unknown")

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
                           major_decision_rank=major_decision_rank,
                           region=wrestler_region,
                           conference=wrestler_conference)

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

            # Normalize the school names for both wrestlers
            wrestler1.school = normalize_school_name(wrestler1.school)
            wrestler2.school = normalize_school_name(wrestler2.school)

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

            # Recalculate RPI for both wrestlers
            recalculate_rpi(wrestler1)
            recalculate_rpi(wrestler2)

            # Recalculate Hybrid for both wrestlers
            recalculate_hybrid(wrestler1)
            recalculate_hybrid(wrestler2)

            # Recalculate Dominance Score for both wrestlers
            wrestler1.dominance_score = calculate_dominance_score(wrestler1)
            wrestler2.dominance_score = calculate_dominance_score(wrestler2)

            # Commit all changes at once to the database
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

            # Recalculate RPI for both wrestlers
            recalculate_rpi(wrestler1)
            recalculate_rpi(wrestler2)

            # Recalculate Hybrid for both wrestlers
            recalculate_hybrid(wrestler1)
            recalculate_hybrid(wrestler2)

            # Recalculate Dominance Score for both wrestlers
            wrestler1.dominance_score = calculate_dominance_score(wrestler1)
            wrestler2.dominance_score = calculate_dominance_score(wrestler2)

            # Commit all changes at once to the database
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
        
        # Adjust opponent's win/loss record
        if match.winner_id == wrestler.id:
            opponent.losses -= 1
        else:
            opponent.wins -= 1
        
        # Recalculate Elo ratings for the opponent
        recalculate_elo(opponent)
        
        # Recalculate RPI for the opponent
        recalculate_rpi(opponent)
        
        # Recalculate Hybrid for the opponent
        recalculate_hybrid(opponent)
        
        # Recalculate Dominance Score for the opponent
        opponent.dominance_score = calculate_dominance_score(opponent)

        # Delete the match after all recalculations
        db.session.delete(match)

    # Delete the wrestler after processing their matches
    db.session.delete(wrestler)

    # Commit all changes at once to the database
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

    # Recalculate Elo ratings for both wrestlers
    recalculate_elo(wrestler1)
    recalculate_elo(wrestler2)

    # Recalculate RPI for both wrestlers
    recalculate_rpi(wrestler1)
    recalculate_rpi(wrestler2)

    # Recalculate Hybrid for both wrestlers
    recalculate_hybrid(wrestler1)
    recalculate_hybrid(wrestler2)

    # Recalculate Dominance Score for both wrestlers
    wrestler1.dominance_score = calculate_dominance_score(wrestler1)
    wrestler2.dominance_score = calculate_dominance_score(wrestler2)

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
    """
    This function normalizes the name and school, checks for an existing wrestler,
    and creates a new one if none exists.
    """
    name = name.strip().title()  # Normalize wrestler name (capitalize properly, remove extra spaces)
    
    # Normalize the school name using the alias normalization function
    school = normalize_school_name(school)

    # Attempt to find a wrestler in the database with a close match to prevent duplicates from small errors
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



# Function to validate and process the uploaded CSV
def validate_and_process_csv(file, user_id=None):  # Optionally pass the user ID
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
        match_ids = []  # List to track added match IDs

        # Process rows
        for row_num, row in enumerate(csv_reader, start=1):
            try:
                # Process each field and strip whitespace
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
                injury_default = False
                sudden_victory = False
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
                elif win_type == 'Injury Default':
                    injury_default = True
                    try:
                        match_time = datetime.strptime(row['Match_Time'].strip(), '%M:%S').time()  # Time for when injury default happened
                    except ValueError:
                        detailed_feedback.append(f"Row {row_num}: Invalid match time format for 'Injury Default' win type.")
                        row_errors += 1
                        continue
                elif win_type == 'SV-1':  # Sudden Victory - 1st Period
                    sudden_victory = True
                    if row['Match_Time'].strip():
                        try:
                            match_time = datetime.strptime(row['Match_Time'].strip(), '%M:%S').time()
                        except ValueError:
                            detailed_feedback.append(f"Row {row_num}: Invalid match time format for 'SV-1' win type.")
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

                # Normalize school names for both wrestlers
                school1_name = normalize_school_name(school1_name)
                school2_name = normalize_school_name(school2_name)

                # Get or create wrestlers
                wrestler1 = get_or_create_wrestler(wrestler1_name, school1_name, weight_class)
                wrestler2 = get_or_create_wrestler(wrestler2_name, school2_name, weight_class)

                # Normalize and strip names to ensure they are compared correctly (case-insensitive)
                wrestler1_name_normalized = wrestler1.name.strip().lower()
                wrestler2_name_normalized = wrestler2.name.strip().lower()
                winner_name_normalized = winner_name.strip().lower()

                # Validate winner name
                if winner_name_normalized not in [wrestler1_name_normalized, wrestler2_name_normalized]:
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

                # Check for existing match with same date, score, and time (if provided)
                existing_match = Match.query.filter_by(
                    wrestler1_id=wrestler1.id,
                    wrestler2_id=wrestler2.id,
                    date=match_date,
                    wrestler1_score=wrestler1_score,
                    wrestler2_score=wrestler2_score,
                    match_time=match_time  # Differentiating by match time as well
                ).first()

                if existing_match:
                    detailed_feedback.append(f"Row {row_num}: Duplicate match detected (already exists with same date, score, and time).")
                    skipped_duplicates += 1
                    continue  # Skip if the match already exists

                # Create and add new match
                winner = wrestler1 if winner_name_normalized == wrestler1_name_normalized else wrestler2
                new_match = Match(
                    date=match_date,
                    wrestler1_id=wrestler1.id,
                    wrestler2_id=wrestler2.id,
                    winner_id=winner.id,
                    win_type=win_type,
                    wrestler1_score=wrestler1_score,
                    wrestler2_score=wrestler2_score,
                    match_time=match_time,  # Only set match time for applicable win types
                    decision=decision,
                    major_decision=major_decision,
                    fall=fall,
                    technical_fall=technical_fall,
                    injury_default=injury_default,  # Added for Injury Default
                    sudden_victory=sudden_victory  # Added for SV-1
                )
                db.session.add(new_match)
                db.session.flush()  # Get match ID before commit

                # Append the new match ID to the list
                match_ids.append(new_match.id)

                # Update win/loss records
                if winner == wrestler1:
                    wrestler1.wins += 1
                    wrestler2.losses += 1
                else:
                    wrestler2.wins += 1
                    wrestler1.losses += 1

                # Recalculate Elo, RPI, Hybrid, and Dominance Score
                recalculate_elo(wrestler1)
                recalculate_elo(wrestler2)
                recalculate_rpi(wrestler1)
                recalculate_rpi(wrestler2)
                recalculate_hybrid(wrestler1)
                recalculate_hybrid(wrestler2)
                recalculate_dominance(wrestler1)
                recalculate_dominance(wrestler2)

                # Commit after each match is successfully added
                db.session.commit()
                added_matches += 1
                detailed_feedback.append(f"Row {row_num}: Match added successfully.")

            except Exception as e:
                detailed_feedback.append(f"Row {row_num}: Error processing match ({str(e)}).")
                row_errors += 1
                db.session.rollback()  # Rollback only if the current row fails
                continue

        # Save the CSV upload report to the database
        try:
            upload_report = CSVUploadReport(
                user_id=user_id,
                total_matches=added_matches + skipped_duplicates + row_errors,
                added_matches=added_matches,
                skipped_duplicates=skipped_duplicates,
                row_errors=row_errors,
                detailed_feedback=json.dumps(detailed_feedback),  # Convert to JSON
                match_ids=json.dumps(match_ids)  # Convert match IDs to JSON
            )
            db.session.add(upload_report)
            db.session.commit()

            logging.info(f"CSV upload report saved successfully with report ID: {upload_report.id}")
        except Exception as e:
            logging.error(f"Error saving CSV upload report: {str(e)}")
            db.session.rollback()

        # Provide feedback after processing
        flash(f"CSV file processed successfully! {added_matches} matches added, {skipped_duplicates} duplicates skipped, {row_errors} errors encountered.", 'success')
        
        # Optionally, store detailed feedback in session for display on the next page
        session['csv_feedback'] = detailed_feedback

        return True

    except Exception as e:
        flash(f"An error occurred during CSV processing: {str(e)}", 'error')
        logging.error(f"An error occurred during CSV processing: {str(e)}")
        return False


def revert_csv_upload(report_id):
    try:
        # Fetch the CSV upload report by its ID
        upload_report = CSVUploadReport.query.get(report_id)
        if not upload_report:
            flash(f"No upload report found with ID {report_id}", 'error')
            return False

        # Load the match IDs from the report
        match_ids = json.loads(upload_report.match_ids)

        # Fetch all matches to be deleted so we can determine affected wrestlers
        matches = Match.query.filter(Match.id.in_(match_ids)).all()

        if not matches:
            flash(f"No matches found for CSV upload report {report_id}", 'error')
            return False

        # Identify affected wrestlers
        affected_wrestlers = set()
        for match in matches:
            affected_wrestlers.add(match.wrestler1)
            affected_wrestlers.add(match.wrestler2)

        # Delete all matches associated with the upload
        Match.query.filter(Match.id.in_(match_ids)).delete(synchronize_session=False)

        # Mark the report as reverted
        upload_report.is_reverted = True

        # Commit the changes (match deletions and upload report update)
        db.session.commit()

        # Recalculate Elo, RPI, Hybrid Score, and Dominance Score for affected wrestlers
        for wrestler in affected_wrestlers:
            # Check if the wrestler has any remaining matches
            remaining_matches = wrestler.matches_as_wrestler1.count() + wrestler.matches_as_wrestler2.count()
            if remaining_matches == 0:
                # If no remaining matches, delete the wrestler
                db.session.delete(wrestler)
                logger.info(f"Wrestler {wrestler.name} deleted as they have no remaining matches.")
            else:
                # If the wrestler still has matches, recalculate their stats
                recalculate_elo(wrestler)
                recalculate_rpi(wrestler)
                recalculate_hybrid(wrestler)
                recalculate_dominance(wrestler)

        # Commit recalculated wrestler stats and any deletions
        db.session.commit()

        flash(f"Successfully reverted CSV upload {report_id}. Matches deleted: {len(match_ids)}.", 'success')
        return True

    except Exception as e:
        db.session.rollback()  # Rollback if there's an error
        flash(f"An error occurred while reverting CSV upload: {str(e)}", 'error')
        logging.error(f"An error occurred while reverting CSV upload: {str(e)}")
        return False





def save_csv_report(upload_date, report_details):
    # Store the report in session as a list of uploads
    csv_reports = session.get('csv_reports', [])

    # Add the current upload details
    csv_reports.append({
        'upload_date': upload_date,  # Store the date of the upload
        'report_details': report_details  # Store the detailed report (successes and errors)
    })

    # Save back to session
    session['csv_reports'] = csv_reports
   


@app.route('/csv_reports', defaults={'page': 1}, methods=['GET'])
@app.route('/csv_reports/page/<int:page>', methods=['GET'])
@login_required
@admin_required
def csv_reports(page):
    PER_PAGE = 10  # Number of reports to display per page

    # Fetch search and filter parameters from the URL
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')

    # Start building the query for fetching the reports
    reports_query = CSVUploadReport.query.order_by(CSVUploadReport.uploaded_at.desc())

    # Filter by search term if provided (modify fields according to your model)
    if search:
        reports_query = reports_query.filter(
            (CSVUploadReport.detailed_feedback.ilike(f'%{search}%')) |
            (CSVUploadReport.total_matches.ilike(f'%{search}%'))  # Example of adding a match field
        )

    # Filter by status (active or reverted)
    if status == 'active':
        reports_query = reports_query.filter_by(is_reverted=False)
    elif status == 'reverted':
        reports_query = reports_query.filter_by(is_reverted=True)

    # Paginate the query results
    paginated_reports = reports_query.paginate(page=page, per_page=PER_PAGE, error_out=False)

    # Process each report's detailed feedback
    for report in paginated_reports.items:
        if report.detailed_feedback:
            try:
                # Parse the feedback from JSON format
                report.detailed_feedback = json.loads(report.detailed_feedback)
                # Log the feedback content to verify it's fully loaded
                app.logger.info(f"Feedback for report {report.id}: {report.detailed_feedback}")
            except json.JSONDecodeError:
                # Handle JSON parsing error, set as empty if it fails
                report.detailed_feedback = []

            else:
                # Set as empty list if no feedback exists
                report.detailed_feedback = []

    # Log the total number of reports for debugging
    app.logger.info(f"Reports fetched: {paginated_reports.total}, Search: {search}, Status: {status}, Page: {page} of {paginated_reports.pages}")

    # Render the template with paginated reports
    return render_template(
        'csv_reports.html',
        reports=paginated_reports,
        search=search,
        status=status
    )



@app.route('/revert_upload/<int:report_id>', methods=['POST'])
@login_required
@admin_required
def revert_upload(report_id):
    if revert_csv_upload(report_id):
        flash(f"CSV upload {report_id} successfully reverted.", 'success')
    return redirect(url_for('csv_reports'))




    
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




# Route to handle CSV upload and processing
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

    # Find the top 10 most dominant wrestlers
    most_dominant_wrestlers = Wrestler.query.order_by(Wrestler.dominance_score.desc()).limit(10).all()

    return render_template('global_leaderboards.html',
                           fall_leaders=fall_leaders,
                           tech_fall_leaders=tech_fall_leaders,
                           major_decision_leaders=major_decision_leaders,
                           most_dominant_wrestlers=most_dominant_wrestlers)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # Check if the user exists and the password is correct
        if user and check_password_hash(user.password, password):
            login_user(user)  # Logs the user in
            flash('Logged in successfully!', 'success')
            if user.is_admin:
                return redirect(url_for('home'))  # Redirect admin to home page
            else:
                return redirect(url_for('home'))  # Redirect viewer to home page
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

@app.route('/admin/update-all', methods=['POST'])
@login_required  # Ensure the user is logged in
def update_all():
    if not current_user.is_admin:  # Only allow admins to perform this action
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('global_leaderboards'))

    try:
        # Loop through all wrestlers in the database
        wrestlers = Wrestler.query.all()
        for wrestler in wrestlers:
            # Reset wins and losses to recalculate them
            wrestler.wins = 0
            wrestler.losses = 0

            # Fetch all matches the wrestler participated in
            matches = list(wrestler.matches_as_wrestler1.all()) + list(wrestler.matches_as_wrestler2.all())
            
            # Recalculate wins/losses based on match outcomes
            for match in matches:
                if match.winner_id == wrestler.id:
                    wrestler.wins += 1
                else:
                    wrestler.losses += 1

            # Recalculate Elo, RPI, Hybrid, and Dominance Scores for each wrestler
            recalculate_elo(wrestler)
            recalculate_rpi(wrestler)
            recalculate_hybrid(wrestler)
            recalculate_dominance(wrestler)

        # Commit all changes to the database at once
        db.session.commit()
        flash('All rankings, wins/losses, and stats have been successfully updated!', 'success')
    except Exception as e:
        # Rollback changes in case of an error
        db.session.rollback()
        flash(f'An error occurred during the update process: {str(e)}', 'error')

    return redirect(url_for('global_leaderboards'))


if __name__ == '__main__':
    app.run(debug=True)
