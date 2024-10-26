from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timezone
from functools import wraps
import math
import logging
import csv
import io
import difflib
from io import TextIOWrapper
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import event
import json
import os
from flask_login import LoginManager

app = Flask(__name__)

# Use the DATABASE_URL environment variable or fallback to SQLite for local testing
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/wrestling.db')

# Other configurations
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


# Initialize the database
db = SQLAlchemy(app)
app.app_context().push()

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
    "Bridgewater State University": ["Bridgewater State", "BSU", "Bridgewater"],
    "Johnson & Wales University": ["Johnson & Wales", "JWU", "Johnson Wales", "Johnson and Wales"],
    "Maine Maritime Academy": ["Maine Maritime", "MMA"],
    "New England College": ["New England College", "NEC"],
    "Norwich University": ["Norwich"],
    "Plymouth State University": ["Plymouth State", "PSU", "Plymouth"],
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
    "Worcester Polytechnic Institute": ["Worcester Poly", "WPI", "Worcester Polytechnic"],
    "Alfred State University": ["Alfred State"],
    "Centenary University": ["Centenary", "Centenary (NJ)"],
    "Elmira College": ["Elmira"],
    "Ithaca College": ["Ithaca"],
    "Keystone College": ["Keystone"],
    "Lycoming College": ["Lycoming"],
    "New Jersey City University": ["NJCU", "New Jersey City"],
    "Penn State Erie, The Behrend College": ["Penn State Erie", "Behrend College", "PSU Behrend", "Penn State Behrend"],
    "Pennsylvania College of Technology": ["Penn College of Tech", "Penn Tech"],
    "Rochester Institute of Technology": ["RIT", "Rochester Tech"],
    "St. John's Fisher University": ["St. John's Fisher", "SJFC", "St. John Fisher"],
    "Stevens Institute of Technology": ["Stevens Tech", "Stevens"],
    "SUNY - Brockport": ["Brockport", "SUNY Brockport"],
    "SUNY - Cortland": ["Cortland", "SUNY Cortland", "Cortland State"],
    "SUNY - Oneonta": ["Oneonta", "SUNY Oneonta", "Oneonta State"],
    "SUNY - Oswego": ["Oswego", "SUNY Oswego", "Oswego State"],
    "University of Pittsburgh at Bradford": ["Pitt Bradford", "University of Pittsburgh Bradford", "Pitt-Bradford"],
    "Hunter College": ["Hunter"],
    "Wilkes University": ["Wilkes"],
    "Alvernia University": ["Alvernia"],
    "Delaware Valley College": ["Delaware Valley", "Del Val"],
    "Elizabethtown College": ["Elizabethtown", "E-town"],
    "Gettysburg College": ["Gettysburg"],
    "Johns Hopkins University": ["Johns Hopkins", "Hopkins", "JHU"],
    "King's College": ["King's", "King`s (PA)"],
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
    "York College of Pennsylvania": ["York College PA", "York PA", "York (PA)"],
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
    "Saint Vincent College": ["St. Vincent", "Saint Vincent", "St. Vincent College"],
    "Shenandoah University": ["Shenandoah"],
    "Southern Virginia University": ["Southern Virginia", "SVU"],
    "Thiel College": ["Thiel"],
    "University of Mount Union": ["Mount Union", "UMU"],
    "Washington & Jefferson College": ["Washington & Jefferson", "W&J"],
    "Washington and Lee University": ["Washington and Lee", "W&L", "Washington & Lee"],
    "Waynesburg University": ["Waynesburg"],
    "Wilmington College": ["Wilmington"],
    "Adrian College": ["Adrian"],
    "Albion College": ["Albion"],
    "Alma College": ["Alma"],
    "Aurora University": ["Aurora"],
    "Case Western Reserve University": ["Case Western", "CWRU", "Case Western Reserve"],
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
    "Wheaton College": ["Wheaton", "Wheaton (IL)"],
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
    "Saint Johns University": ["Saint Johns", "St. Johns", "SJU", "St. Johns (MN)"],
    "University of Wisconsin-Eau Claire": ["Wisconsin-Eau Claire", "Wisconsin Eau Claire", "UW Eau Claire"],
    "University of Wisconsin-La Crosse": ["Wisconsin La Crosse", "UW La Crosse", "Wisconsin-La Crosse"],
    "University of Wisconsin-Oshkosh": ["Wisconsin Oshkosh", "UW Oshkosh", "Wisconsin-Oshkosh"],
    "University of Wisconsin-Platteville": ["Wisconsin Platteville", "UW Platteville", "Wisconsin-Platteville"],
    "University of Wisconsin-Stevens Point": ["Wisconsin Stevens Point", "UW Stevens Point", "Wisconsin-Stevens Point"]
}


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Models

class Season(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=False)  # Add this field

    # Relationships
    matches = db.relationship('Match', backref='season', lazy=True)



class Wrestler(db.Model):
    __tablename__ = 'wrestler'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    school = db.Column(db.String(100), nullable=False)
    weight_class = db.Column(db.Integer, nullable=False)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    falls = db.Column(db.Integer, default=0)  # Field for falls
    tech_falls = db.Column(db.Integer, default=0)  # Field for technical falls
    major_decisions = db.Column(db.Integer, default=0)  # Field for major decisions
    elo_rating = db.Column(db.Float, default=1500)
    rpi = db.Column(db.Float, default=0)
    dominance_score = db.Column(db.Float, nullable=False, default=0.0)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    graduating = db.Column(db.Boolean, default=False)  # Field for graduating status
    year_in_school = db.Column(db.String(20), nullable=True, default='Freshman')  # Field for year in school

    # Relationship to Season
    season = db.relationship('Season', backref='wrestlers')

    # Bidirectional relationships to matches (as wrestler1 or wrestler2) with back_populates
    matches_as_wrestler1 = db.relationship('Match', foreign_keys='Match.wrestler1_id', back_populates='wrestler1', lazy='dynamic')
    matches_as_wrestler2 = db.relationship('Match', foreign_keys='Match.wrestler2_id', back_populates='wrestler2', lazy='dynamic')

    @property
    def total_matches(self):
        return self.wins + self.losses

    @property
    def hybrid_score(self):
        if self.elo_rating is not None and self.rpi is not None:
            return (0.5 * self.elo_rating) + (0.5 * self.rpi)
        return None

    def calculate_dominance_score(self):
        matches = self.matches_as_wrestler1.all() + self.matches_as_wrestler2.all()
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

        self.dominance_score = round(total_score / match_count, 2) if match_count > 0 else 0

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
            'dominance_score': self.dominance_score,
            'season_id': self.season_id,
            'graduating': self.graduating,  # Include graduating status
            'year_in_school': self.year_in_school  # Include year in school
        }

    def graduate(self):
        """Mark this wrestler as graduating."""
        self.graduating = True

    def update_year_in_school(self):
        """Update the wrestler's year in school for the next season."""
        if self.year_in_school == 'Freshman':
            self.year_in_school = 'Sophomore'
        elif self.year_in_school == 'Sophomore':
            self.year_in_school = 'Junior'
        elif self.year_in_school == 'Junior':
            self.year_in_school = 'Senior'
        elif self.year_in_school == 'Senior':
            self.graduate()

    def increment_falls(self):
        """Increment the falls count and log the update."""
        self.falls += 1
        app.logger.info(f"Incremented falls for {self.name}. New falls count: {self.falls}")

    def increment_tech_falls(self):
        """Increment the technical falls count and log the update."""
        self.tech_falls += 1
        app.logger.info(f"Incremented tech falls for {self.name}. New tech falls count: {self.tech_falls}")

    def increment_major_decisions(self):
        """Increment the major decisions count and log the update."""
        self.major_decisions += 1
        app.logger.info(f"Incremented major decisions for {self.name}. New major decisions count: {self.major_decisions}")




class Match(db.Model):
    __tablename__ = 'match'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Foreign key to Season model
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)

    # Wrestlers involved in the match
    wrestler1_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)
    wrestler2_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)

    # Relationships to wrestlers with back_populates to establish bidirectional relationship
    wrestler1 = db.relationship('Wrestler', foreign_keys=[wrestler1_id], back_populates='matches_as_wrestler1')
    wrestler2 = db.relationship('Wrestler', foreign_keys=[wrestler2_id], back_populates='matches_as_wrestler2')

    # Winner of the match
    winner_id = db.Column(db.Integer, db.ForeignKey('wrestler.id'), nullable=False)
    winner = db.relationship('Wrestler', foreign_keys=[winner_id], backref='matches_won')

    # Win type and score details
    win_type = db.Column(db.String(20), nullable=False)
    wrestler1_score = db.Column(db.Integer, nullable=False, default=0)
    wrestler2_score = db.Column(db.Integer, nullable=False, default=0)
    match_time = db.Column(db.Time, nullable=True)

    # Additional match result columns
    fall = db.Column(db.Boolean, default=False)
    technical_fall = db.Column(db.Boolean, default=False)
    major_decision = db.Column(db.Boolean, default=False)
    decision = db.Column(db.Boolean, default=False)
    injury_default = db.Column(db.Boolean, default=False)
    sudden_victory = db.Column(db.Boolean, default=False)
    double_overtime = db.Column(db.Boolean, default=False)  # New field for 2-OT win
    medical_forfeit = db.Column(db.Boolean, default=False)  # New field for Medical Forfeit win
    disqualification = db.Column(db.Boolean, default=False)  # New field for disqualification win
    tiebreaker_1 = db.Column(db.Boolean, default=False)  # Field for Tiebreaker 1 win
    tiebreaker_2 = db.Column(db.Boolean, default=False)  # Field for Tiebreaker 2 win

    def calculate_win_type(self):
        # Recognize variations of 'Sudden Victory', 'Double Overtime', 'Tiebreaker' etc.
        if self.fall:
            self.win_type = 'Fall'
        elif self.technical_fall:
            self.win_type = 'Technical Fall'
        elif self.injury_default:
            self.win_type = 'Injury Default'
        elif self.sudden_victory:
            self.win_type = 'SV-1'  # Sudden Victory will be represented as 'SV-1'
        elif self.double_overtime:
            self.win_type = '2-OT'  # Handle Double Overtime
        elif self.tiebreaker_1:
            self.win_type = 'TB-1'  # Handle Tiebreaker 1
        elif self.tiebreaker_2:
            self.win_type = 'TB-2'  # Handle Tiebreaker 2
        elif self.medical_forfeit:
            self.win_type = 'Medical Forfeit'  # Handle Medical Forfeit
        elif self.disqualification:
            self.win_type = 'Disqualification'  # Handle disqualification
        else:
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

        # Set the corresponding boolean flags based on the win_type
        self.fall = self.win_type == 'Fall'
        self.technical_fall = self.win_type == 'Technical Fall'
        self.major_decision = self.win_type == 'Major Decision'
        self.decision = self.win_type == 'Decision'
        self.injury_default = self.win_type == 'Injury Default'
        self.sudden_victory = self.win_type in ['SV-1', 'Sudden Victory', 'Sudden Victory - 1']  # Include variations
        self.double_overtime = self.win_type in ['2-OT', 'Double Overtime',]
        self.tiebreaker_1 = self.win_type in ['TB-1', 'Tiebreaker - 1', 'tiebreaker - 1']
        self.tiebreaker_2 = self.win_type in ['TB-2', 'Tiebreaker - 2 (Riding Time)', 'tiebreaker - 2 (riding time)' ]
        self.medical_forfeit = self.win_type == 'Medical Forfeit'
        self.disqualification = self.win_type == 'Disqualification'

    def to_dict(self):
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
            'injury_default': self.injury_default,
            'sudden_victory': self.sudden_victory,
            'double_overtime': self.double_overtime,
            'tiebreaker_1': self.tiebreaker_1,
            'tiebreaker_2': self.tiebreaker_2,
            'medical_forfeit': self.medical_forfeit,
            'disqualification': self.disqualification,  # Include disqualification in dictionary output
            'season_id': self.season_id  # Include the season in match details
        }






# SQLAlchemy event listeners
@event.listens_for(Match, 'before_insert')
def before_insert_listener(mapper, connection, target):
    target.calculate_win_type()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Admin functionality

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
    detailed_feedback = db.Column(db.JSON, nullable=False)  # Store detailed feedback as JSON
    match_ids = db.Column(db.JSON, nullable=False)  # Store added match IDs as a JSON array for reversion
    is_reverted = db.Column(db.Boolean, nullable=False, default=False)  # Track if the report has been reverted

    def to_dict(self):
        # Convert the detailed_feedback and match_ids to appropriate formats if necessary
        feedback = self.detailed_feedback if isinstance(self.detailed_feedback, list) else []
        match_ids = self.match_ids if isinstance(self.match_ids, list) else []

        return {
            'id': self.id,
            'uploaded_at': self.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
            'total_matches': self.total_matches,
            'added_matches': self.added_matches,
            'skipped_duplicates': self.skipped_duplicates,
            'row_errors': self.row_errors,
            'detailed_feedback': feedback,
            'match_ids': match_ids,
            'is_reverted': self.is_reverted
        }

logger = logging.getLogger(__name__)

def expected_score(rating_a, rating_b):
    return 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))

def update_elo(rating, expected, actual, k_factor=32):
    return rating + k_factor * (actual - expected)

def recalculate_elo(wrestler_id, season_id):
    # Fetch the wrestler by ID
    wrestler = Wrestler.query.get(wrestler_id)
    if not wrestler:
        logger.error(f"Wrestler with ID {wrestler_id} not found.")
        return

    logger.info(f"Recalculating Elo for {wrestler.name}")

    # Initialize the wrestler's Elo rating based on the number of matches
    matches = Match.query.filter(
        (Match.wrestler1_id == wrestler.id) | (Match.wrestler2_id == wrestler.id),
        Match.season_id == season_id
    ).all()

    if not matches:
        wrestler.elo_rating = 1500
        logger.info(f"No matches found for {wrestler.name}. Setting Elo to {wrestler.elo_rating}")
        db.session.commit()
        return

    # Store Elo updates in a list to minimize database writes
    elo_updates = []

    # Iterate through the matches to recalculate the Elo rating
    for match in matches:
        opponent = match.wrestler2 if match.wrestler1_id == wrestler.id else match.wrestler1
        
        # Ensure opponent has a valid Elo rating
        opponent.elo_rating = opponent.elo_rating or 1500  # Default Elo rating if not set

        expected = expected_score(wrestler.elo_rating, opponent.elo_rating)
        actual = 1 if match.winner_id == wrestler.id else 0
        
        # Update the wrestler's Elo rating
        new_rating = update_elo(wrestler.elo_rating, expected, actual)
        
        logger.info(f"Match on {match.date.strftime('%Y-%m-%d')} against {opponent.name}: expected {expected:.4f}, actual {actual}. Updated Elo: {new_rating:.2f}")

        # Store the updated rating for the wrestler
        elo_updates.append((wrestler, new_rating))

    # Apply all updates in a single commit
    try:
        for wrestler, new_rating in elo_updates:
            wrestler.elo_rating = new_rating
        db.session.commit()
        logger.info(f"Elo ratings updated successfully for wrestler {wrestler.name}.")
    except Exception as e:
        db.session.rollback()  # Rollback if there was an error
        logger.error(f"Error committing Elo updates for {wrestler.name}: {str(e)}")


# RPI calculation functions
MIN_MATCHES = 3

def calculate_rpi(wrestler_id, season_id):
    wrestler = Wrestler.query.get(wrestler_id)  # Fetch the wrestler by ID

    # Check if the wrestler has enough matches for RPI calculation
    if wrestler.total_matches < MIN_MATCHES:
        logger.info(f"{wrestler.name} has fewer than {MIN_MATCHES} matches. RPI not calculated.")
        return 0, 0, 0, 0

    win_percentage = wrestler.wins / max(wrestler.total_matches, 1)

    # Fetch matches for the specified season
    matches_as_wrestler1 = Match.query.filter_by(wrestler1_id=wrestler_id, season_id=season_id).all()
    matches_as_wrestler2 = Match.query.filter_by(wrestler2_id=wrestler_id, season_id=season_id).all()

    opponents = set(match.wrestler2 if match.wrestler1_id == wrestler.id else match.wrestler1
                    for match in matches_as_wrestler1 + matches_as_wrestler2)

    # Calculate opponent win percentage
    if opponents:
        opponent_win_percentage = sum(opponent.wins / max(opponent.total_matches, 1) for opponent in opponents) / len(opponents)
    else:
        opponent_win_percentage = 0

    opponent_opponents = set()
    for opponent in opponents:
        opponent_opponents.update(
            match.wrestler2 if match.wrestler1_id == opponent.id else match.wrestler1
            for match in opponent.matches_as_wrestler1.all() + opponent.matches_as_wrestler2.all()
        )

    # Calculate opponent of opponent win percentage
    if opponent_opponents:
        opponent_opponent_win_percentage = sum(opp_op.wins / max(opp_op.total_matches, 1) for opp_op in opponent_opponents) / len(opponent_opponents)
    else:
        opponent_opponent_win_percentage = 0

    # Calculate RPI
    rpi = 0.25 * win_percentage + 0.5 * opponent_win_percentage + 0.25 * opponent_opponent_win_percentage

    logger.info(f"RPI for {wrestler.name}: {rpi:.3f}")
    return rpi, win_percentage, opponent_win_percentage, opponent_opponent_win_percentage

def recalculate_rpi(wrestler_id, season_id):
    rpi, win_percentage, opponent_win_percentage, opponent_opponent_win_percentage = calculate_rpi(wrestler_id, season_id)
    wrestler = Wrestler.query.get(wrestler_id)
    wrestler.rpi = rpi
    db.session.commit()

    logger.info(f"RPI recalculated for {wrestler.name}: {rpi:.3f}")
    return rpi

def recalculate_hybrid(wrestler_id, season_id):
    wrestler = Wrestler.query.get(wrestler_id)
    """
    Recalculate the hybrid score for the given wrestler.
    The hybrid score is a combination of Elo rating and RPI.
    It is calculated as: hybrid_score = 0.5 * Elo rating + 0.5 * RPI.
    This function does not need to set the hybrid_score directly as it is a property.
    """
    if wrestler.elo_rating is not None and wrestler.rpi is not None:
        # Calculate the hybrid score using the property method
        hybrid_score = wrestler.hybrid_score  # Automatically uses the latest Elo and RPI values
        logger.info(f"{wrestler.name}: Hybrid Score recalculated to {hybrid_score}")
    else:
        logger.info(f"{wrestler.name}: Hybrid Score cannot be calculated due to missing values")
    
    db.session.commit()



# Helper function to calculate Dominance Score
def calculate_dominance_score(wrestler_id, season_id):
    wrestler = Wrestler.query.get(wrestler_id)
    
    # Fetch matches for the wrestler in the specified season
    matches = Match.query.filter(
        (Match.wrestler1_id == wrestler.id) | (Match.wrestler2_id == wrestler.id),
        Match.season_id == season_id
    ).all()

    total_score = 0
    match_count = len(matches)

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

    if match_count == 0:
        logger.info(f"{wrestler.name} has no matches. Dominance score set to 0.")
        return 0  # Avoid division by zero if the wrestler has no matches

    # Calculate the average dominance score across all matches
    return round(total_score / match_count, 2)  # Round to 2 decimal places for readability

def recalculate_dominance(wrestler_id, season_id):
    """
    Recalculates and updates the dominance score for a given wrestler.
    """
    wrestler = Wrestler.query.get(wrestler_id)

    # Calculate dominance score
    dominance_score = calculate_dominance_score(wrestler_id, season_id)
    wrestler.dominance_score = dominance_score  # Save it back to the wrestler

    db.session.commit()  # Commit the changes to the database
    logger.info(f"Dominance score for {wrestler.name} recalculated: {dominance_score}")
    
    return wrestler.dominance_score



def get_stat_leaders(stat_column, season_id=None, limit=10, weight_class=None):
    """
    Fetch top wrestlers based on a specific stat (falls, tech falls, major decisions)
    using their manually updated stats in the Wrestler model.

    Parameters:
        stat_column (str): The stat to rank wrestlers by (e.g., 'falls', 'tech_falls', 'major_decisions')
        season_id (int): The ID of the season to filter by. Defaults to None (all seasons).
        limit (int): The number of top wrestlers to return. Defaults to 10.
        weight_class (int): The weight class to filter by. Defaults to None (all weight classes).

    Returns:
        List of top wrestlers and their stat counts.
    """
    # Map the input stat_column to the actual column names in the Wrestler model
    stat_mapping = {
        'Fall': Wrestler.falls,
        'Technical Fall': Wrestler.tech_falls,
        'Major Decision': Wrestler.major_decisions
    }

    # Ensure the stat_column is valid
    if stat_column not in stat_mapping:
        raise ValueError(f"Invalid stat_column: {stat_column}")

    # Construct the base query using manually updated stats
    query = db.session.query(Wrestler).filter(stat_mapping[stat_column] > 0)

    # If a season is provided, filter by the selected season
    if season_id:
        query = query.filter(Wrestler.season_id == season_id)

    # If a weight class is provided, filter by the selected weight class
    if weight_class:
        query = query.filter(Wrestler.weight_class == weight_class)

    # Order by the specific stat count and limit the results
    query = query.order_by(stat_mapping[stat_column].desc()).limit(limit)

    # Return the list of wrestlers and their stat counts
    return [(wrestler, getattr(wrestler, stat_mapping[stat_column].key)) for wrestler in query.all()]


# Utility functions and decorators (admin_required goes here)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):  # Check if the user is admin
            flash('Access denied: Admins only.', 'danger')
            return redirect(url_for('home'))  # Redirect to home
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


def get_weight_class_data(season_id=None):
    weight_class_data = []
    for weight in WEIGHT_CLASSES:
        # Filter wrestlers by season if a season_id is provided
        if season_id:
            wrestlers = Wrestler.query.filter_by(weight_class=weight, season_id=season_id).order_by(Wrestler.elo_rating.desc()).limit(5).all()
        else:
            wrestlers = Wrestler.query.filter_by(weight_class=weight).order_by(Wrestler.elo_rating.desc()).limit(5).all()
        
        weight_class_data.append({
            'weight': weight,
            'wrestlers': wrestlers
        })
    return weight_class_data


def calculate_wins_losses(wrestler_id, season_id):
    matches = Match.query.filter(
        (Match.wrestler1_id == wrestler_id) | (Match.wrestler2_id == wrestler_id),
        Match.season_id == season_id
    ).all()

    wins = 0
    losses = 0

    for match in matches:
        if match.winner_id == wrestler_id:
            wins += 1
        else:
            losses += 1

    return wins, losses


def recalculate_wrestler_stats(wrestler_id, season_id):
    # Fetch the wrestler first
    wrestler = Wrestler.query.get(wrestler_id)
    
    if not wrestler:  # Ensure wrestler exists
        logging.warning(f"Wrestler with ID {wrestler_id} does not exist.")
        return  # Early exit if wrestler does not exist

    # Fetch matches for the wrestler in the selected season
    matches = Match.query.filter(
        (Match.wrestler1_id == wrestler_id) | (Match.wrestler2_id == wrestler_id),
        Match.season_id == season_id
    ).all()

    # Initialize stats
    falls = 0
    tech_falls = 0
    major_decisions = 0

    # Loop through each match to calculate falls, tech falls, and major decisions
    for match in matches:
        if match.winner_id == wrestler_id:
            if match.win_type == 'Fall':
                falls += 1
            elif match.win_type == 'Technical Fall':
                tech_falls += 1
            elif match.win_type == 'Major Decision':
                major_decisions += 1

    # Update the wrestler's stats
    wrestler.falls = falls
    wrestler.tech_falls = tech_falls
    wrestler.major_decisions = major_decisions

    try:
        db.session.commit()  # Save changes
        logging.info(f"Wrestler {wrestler.name} (ID: {wrestler_id}) stats updated: Falls={falls}, Tech_Falls={tech_falls}, Major_Decisions={major_decisions}.")
    except Exception as e:
        logging.error(f"Error updating stats for wrestler {wrestler.name} (ID: {wrestler_id}): {str(e)}")
        db.session.rollback()  # Rollback if there was an error

def get_team_scores(season_id):
    """
    Calculate team scores for the entire division based on the ranking of individual wrestlers.
    """
    teams = {}

    # Fetch all wrestlers for the specified season, grouped by weight class
    weight_classes = set([wrestler.weight_class for wrestler in Wrestler.query.filter_by(season_id=season_id).all()])

    for weight_class in weight_classes:
        # Get all wrestlers for the weight class in the given season, ordered by Elo
        wrestlers = Wrestler.query.filter_by(weight_class=weight_class, season_id=season_id).order_by(Wrestler.elo_rating.desc()).all()

        # Loop through the top 8 wrestlers (rank 1 to 8)
        for rank, wrestler in enumerate(wrestlers[:8], start=1):
            team_name = wrestler.school
            points = calculate_points(rank)  # Use your point calculation based on dynamic ranking

            if team_name in teams:
                teams[team_name] += points
            else:
                teams[team_name] = points

    # Return a sorted list of teams by points in descending order
    return sorted(teams.items(), key=lambda x: x[1], reverse=True)



def get_regional_team_scores(season_id, region):
    """
    Calculate team scores based on the same scoring structure but limited to a specific region.
    Include all teams from the selected region, even if they have zero points.
    """
    teams = {}

    # Initialize teams from the selected region with zero points
    for team_name, team_info in D3_WRESTLING_SCHOOLS.items():
        if team_info.get('region') == region:
            teams[team_name] = 0

    # Fetch all wrestlers for the specified season, grouped by weight class, and filtered by region
    weight_classes = set([wrestler.weight_class for wrestler in Wrestler.query.filter_by(season_id=season_id).all()])

    for weight_class in weight_classes:
        # Get all wrestlers for the weight class in the given season, ordered by Elo, and filter by region
        wrestlers = [
            wrestler for wrestler in Wrestler.query.filter_by(weight_class=weight_class, season_id=season_id).order_by(Wrestler.elo_rating.desc()).all()
            if D3_WRESTLING_SCHOOLS.get(wrestler.school, {}).get('region') == region
        ]

        # Loop through the top 8 wrestlers (rank 1 to 8) and calculate team points
        for rank, wrestler in enumerate(wrestlers[:8], start=1):
            team_name = wrestler.school
            points = calculate_points(rank)  # Use the same scoring logic here
            if team_name in teams:
                teams[team_name] += points
            else:
                teams[team_name] = points

    # Return a sorted list of teams by points in descending order
    return sorted(teams.items(), key=lambda x: x[1], reverse=True)


def calculate_points(rank):
    """
    Returns points based on the rank.
    """
    if rank == 1:
        return 16
    elif rank == 2:
        return 12
    elif rank == 3:
        return 10
    elif rank == 4:
        return 9
    elif rank == 5:
        return 7
    elif rank == 6:
        return 6
    elif rank == 7:
        return 2
    elif rank == 8:
        return 1
    else:
        return 0





@app.route('/landing')
def landing():
    # Log out any currently logged-in user
    logout_user()
    return render_template('landing.html')

@app.route('/')
def home():
    print("Accessing the home route...")
    
    # Redirect to landing page if not logged in
    if not current_user.is_authenticated:
        print("User is not authenticated. Redirecting to landing.")
        return redirect(url_for('landing'))
    
    # Check if the user is an admin
    is_admin = current_user.is_admin

    # Get all available seasons, ordered by start_date descending
    seasons = Season.query.order_by(Season.start_date.desc()).all()

    # Get the most recent season
    recent_season = seasons[0] if seasons else None

    # Get the selected season from the URL or default to the most recent season
    selected_season_id = request.args.get('season_id')

    if not selected_season_id and recent_season:
        # Default to the most recent season if no season is selected
        selected_season_id = recent_season.id

    # Fetch the selected season object
    selected_season = Season.query.get(selected_season_id) if selected_season_id else recent_season

    if not selected_season:
        flash('No seasons found. Please create a new season to proceed.', 'warning')
        return redirect(url_for('manage_seasons'))

    # Initialize weight_class_data for storing wrestlers by weight class
    weight_class_data = []

    if selected_season:
        # Fetch weight class data
        for weight in WEIGHT_CLASSES:
            wrestlers = Wrestler.query.filter_by(weight_class=weight, season_id=selected_season.id)\
                                      .order_by(Wrestler.elo_rating.desc())\
                                      .limit(5)\
                                      .all()
            weight_class_data.append({
                'weight': weight,
                'wrestlers': wrestlers
            })

    # Render the home template with season data
    return render_template('home.html',
                           weight_class_data=weight_class_data,
                           seasons=seasons,
                           selected_season=selected_season,
                           selected_season_id=selected_season.id if selected_season else None,
                           recent_season=recent_season,
                           is_admin=is_admin)

@app.route('/viewer-home')
def viewer_home():
    print("Accessing the viewer home route...")
    
    # Treat this as a non-admin view
    is_admin = False

    # Get all available seasons, ordered by start_date descending
    seasons = Season.query.order_by(Season.start_date.desc()).all()

    # Get the most recent season
    recent_season = seasons[0] if seasons else None

    # Get the selected season from the URL or default to the most recent season
    selected_season_id = request.args.get('season_id')

    if not selected_season_id and recent_season:
        # Default to the most recent season if no season is selected
        selected_season_id = recent_season.id

    # Fetch the selected season object
    selected_season = Season.query.get(selected_season_id) if selected_season_id else recent_season

    if not selected_season:
        flash('No seasons found. Please create a new season to proceed.', 'warning')
        return redirect(url_for('manage_seasons'))

    # Initialize weight_class_data for storing wrestlers by weight class
    weight_class_data = []

    if selected_season:
        # Fetch weight class data
        for weight in WEIGHT_CLASSES:
            wrestlers = Wrestler.query.filter_by(weight_class=weight, season_id=selected_season.id)\
                                      .order_by(Wrestler.elo_rating.desc())\
                                      .limit(5)\
                                      .all()
            weight_class_data.append({
                'weight': weight,
                'wrestlers': wrestlers
            })

    # Render the home template with season data, but treat as a non-admin view
    return render_template('home.html',
                           weight_class_data=weight_class_data,
                           seasons=seasons,
                           selected_season=selected_season,
                           selected_season_id=selected_season.id if selected_season else None,
                           recent_season=recent_season,
                           is_admin=is_admin)


@app.route('/team-rankings', methods=['GET'])
def team_rankings():
    # Your existing logic for fetching and displaying team rankings
    selected_season_id = request.args.get('season_id')
    selected_region = request.args.get('region')

    # Fetch all seasons for the dropdown
    seasons = Season.query.order_by(Season.start_date.desc()).all()

    # Default to the first available season if none is selected
    if not selected_season_id:
        selected_season = seasons[0] if seasons else None
    else:
        selected_season = Season.query.get(selected_season_id)

    if not selected_season:
        flash("No seasons available.", "error")
        return redirect(url_for('home'))

    # Get the name for the selected season
    selected_season_name = selected_season.name if selected_season else 'N/A'

    # If a region is selected, fetch regional team scores, otherwise get overall team scores
    if selected_region:
        team_scores = get_regional_team_scores(selected_season.id, int(selected_region))
    else:
        team_scores = get_team_scores(selected_season.id)

    # Fetch available regions for the dropdown
    available_regions = sorted({info['region'] for info in D3_WRESTLING_SCHOOLS.values()})

    return render_template('team_rankings.html',
                           team_scores=team_scores,
                           selected_season_id=selected_season.id,
                           selected_region=selected_region,
                           seasons=seasons,
                           selected_season_name=selected_season_name,
                           available_regions=available_regions)




@app.route('/rankings/<int:weight_class>')
def rankings(weight_class):
    import time
    start_time = time.time()  # Start the timer for performance measurement

    selected_season_id = request.args.get('season_id')  # Get the selected season ID from the query string

    # Ensure there's a valid selected season
    if not selected_season_id:
        recent_season = Season.query.order_by(Season.start_date.desc()).first()
        selected_season_id = recent_season.id if recent_season else None

    selected_season = Season.query.get(selected_season_id)
    if not selected_season:
        return "Selected season not found", 404  # Error handling

    # Fetch all wrestlers for the given weight class and season
    wrestlers_query = Wrestler.query.filter_by(weight_class=weight_class, season_id=selected_season_id)
    wrestlers = wrestlers_query.all()

    # Log the number of wrestlers found
    print(f"Wrestlers found: {len(wrestlers)}")
    
    # Assign region and conference based on the school
    for wrestler in wrestlers:
        wrestler_details = D3_WRESTLING_SCHOOLS.get(wrestler.school)
        if wrestler_details:
            wrestler.region = wrestler_details.get("region", "Unknown")
            wrestler.conference = wrestler_details.get("conference", "Unknown")
        else:
            wrestler.region = "Unknown"
            wrestler.conference = "Unknown"
            print(f"School '{wrestler.school}' not found in D3_WRESTLING_SCHOOLS")

    # Print wrestler details for debugging
    for wrestler in wrestlers:
        print(f"Wrestler: {wrestler.name}, School: {wrestler.school}, Region: {wrestler.region}, Conference: {wrestler.conference}")

    sort_by = request.args.get('sort_by', 'elo')  # Default to Elo sorting
    selected_region = request.args.get('region', None)
    selected_conference = request.args.get('conference', None)

    # Get unique regions and conferences from D3_WRESTLING_SCHOOLS
    regions = sorted(set(school_data["region"] for school_data in D3_WRESTLING_SCHOOLS.values()))
    conferences = sorted(set(school_data["conference"] for school_data in D3_WRESTLING_SCHOOLS.values()))

    # Filter by selected region if applicable
    if selected_region:
        wrestlers = [wrestler for wrestler in wrestlers if wrestler.region == int(selected_region)]
        print(f"Filtered by region: {selected_region}, Wrestlers count: {len(wrestlers)}")

    # Filter by selected conference if applicable
    if selected_conference:
        wrestlers = [wrestler for wrestler in wrestlers if wrestler.conference == selected_conference]
        print(f"Filtered by conference: {selected_conference}, Wrestlers count: {len(wrestlers)}")

    # Ensure that we still have wrestlers after filtering
    print(f"Total wrestlers after filtering: {len(wrestlers)}")

    # Calculate wins and losses for each wrestler
    for wrestler in wrestlers:
        wins, losses = calculate_wins_losses(wrestler.id, selected_season_id)
        wrestler.wins = wins
        wrestler.losses = losses

    # Calculate Dominance Score for each wrestler
    for wrestler in wrestlers:
        matches_wrestler1 = Match.query.filter_by(wrestler1_id=wrestler.id, season_id=selected_season_id).all()
        matches_wrestler2 = Match.query.filter_by(wrestler2_id=wrestler.id, season_id=selected_season_id).all()
        matches = matches_wrestler1 + matches_wrestler2
        total_points = 0
        total_matches = len(matches)

        # Calculate dominance score
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

        wrestler.dominance_score = total_points / total_matches if total_matches > 0 else 0

    # Handle sorting
    if sort_by == 'rpi':
        wrestlers = sorted(wrestlers, key=lambda w: (w.rpi is None, w.rpi), reverse=True)
    elif sort_by == 'hybrid':
        wrestlers = sorted(wrestlers, key=lambda w: (w.hybrid_score is None, w.hybrid_score), reverse=True)
    elif sort_by == 'dominance':
        wrestlers = sorted(wrestlers, key=lambda w: (w.dominance_score is None, w.dominance_score), reverse=True)
    elif sort_by == 'region':
        wrestlers = sorted(wrestlers, key=lambda w: (w.region is None, w.region))
    elif sort_by == 'conference':
        wrestlers = sorted(wrestlers, key=lambda w: (w.conference is None, w.conference))
    else:
        wrestlers = sorted(wrestlers, key=lambda w: (w.elo_rating is None, w.elo_rating), reverse=True)

    # Calculate win percentage
    for wrestler in wrestlers:
        wrestler.win_percentage = (wrestler.wins / max(wrestler.total_matches, 1)) * 100  # Convert to percentage

    # Clear filter flag
    clear_filters = bool(selected_region or selected_conference)

    # Check if the user is an admin
    is_admin = current_user.is_authenticated and current_user.is_admin  # Adjust based on your auth system

    # Log query time for performance analysis
    print(f"Query time: {time.time() - start_time:.2f} seconds")  # Log query time

    return render_template('rankings.html',
                           weight_class=weight_class,
                           wrestlers=wrestlers,
                           sort_by=sort_by,
                           selected_region=selected_region,
                           selected_conference=selected_conference,
                           clear_filters=clear_filters,
                           regions=regions,
                           conferences=conferences,
                           selected_season_id=selected_season_id,
                           selected_season=selected_season,
                           is_admin=is_admin)  # Pass the is_admin flag


@app.route('/wrestler/<int:wrestler_id>', methods=['GET', 'POST'])
def wrestler_detail(wrestler_id):
    # Get the selected season from query parameters
    selected_season_id = request.args.get('season_id')

    # Ensure selected_season_id is provided, fallback if necessary
    if not selected_season_id:
        flash('Season ID is missing!', 'error')
        return redirect(url_for('home'))  # Redirect or handle the error if season_id is missing

    # Fetch the wrestler by ID, filtered by the selected season
    wrestler = Wrestler.query.filter_by(id=wrestler_id, season_id=selected_season_id).first_or_404()

    # Handle POST request for updating stats
    if request.method == 'POST':
        # Get falls, tech falls, and major decisions from the form
        falls = request.form.get('falls', type=int)
        tech_falls = request.form.get('tech_falls', type=int)
        major_decisions = request.form.get('major_decisions', type=int)

        # Update the wrestler's stats
        wrestler.falls = falls
        wrestler.tech_falls = tech_falls
        wrestler.major_decisions = major_decisions

        try:
            db.session.commit()
            flash('Stats updated successfully!', 'success')
            # Redirect to the wrestler's detail page to reflect the changes
            return redirect(url_for('wrestler_detail', wrestler_id=wrestler.id, season_id=selected_season_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the stats: {str(e)}', 'error')

    # Fetch the selected season
    selected_season = Season.query.get(selected_season_id)

    # Cross-reference the school to assign region and conference
    school_info = D3_WRESTLING_SCHOOLS.get(wrestler.school, {})
    wrestler_region = school_info.get("region", "Unknown")
    wrestler_conference = school_info.get("conference", "Unknown")

    # Get wins and losses using the utility function
    wins, losses = calculate_wins_losses(wrestler_id, selected_season_id)

    # Query for all wrestlers in the same weight class and season
    all_wrestlers_in_weight_class = Wrestler.query.filter_by(weight_class=wrestler.weight_class, season_id=selected_season_id).all()

    # Sort wrestlers by Elo, RPI, Hybrid, and Dominance Score and determine the ranks
    sorted_by_elo = sorted(all_wrestlers_in_weight_class, key=lambda w: w.elo_rating, reverse=True)
    sorted_by_rpi = sorted(all_wrestlers_in_weight_class, key=lambda w: w.rpi if w.rpi else 0, reverse=True)
    sorted_by_hybrid = sorted(all_wrestlers_in_weight_class, key=lambda w: w.hybrid_score if w.hybrid_score else 0, reverse=True)
    sorted_by_dominance = sorted(all_wrestlers_in_weight_class, key=lambda w: recalculate_dominance(w.id, selected_season_id), reverse=True)

    # Find the ranks of the current wrestler
    elo_rank = sorted_by_elo.index(wrestler) + 1
    rpi_rank = sorted_by_rpi.index(wrestler) + 1
    hybrid_rank = sorted_by_hybrid.index(wrestler) + 1
    dominance_rank = sorted_by_dominance.index(wrestler) + 1

    # Get stats and ranks using the same logic as the leaderboards
    fall_leaders = get_stat_leaders('Fall', selected_season_id)
    tech_fall_leaders = get_stat_leaders('Technical Fall', selected_season_id)
    major_decision_leaders = get_stat_leaders('Major Decision', selected_season_id)

    # Calculate the wrestler's rank for each stat (or None if not ranked)
    fall_rank = next((rank for rank, (wrestler_obj, _) in enumerate(fall_leaders, 1) if wrestler_obj.id == wrestler_id), None)
    tech_fall_rank = next((rank for rank, (wrestler_obj, _) in enumerate(tech_fall_leaders, 1) if wrestler_obj.id == wrestler_id), None)
    major_decision_rank = next((rank for rank, (wrestler_obj, _) in enumerate(major_decision_leaders, 1) if wrestler_obj.id == wrestler_id), None)

    # Use updated values for falls, tech falls, and major decisions for rendering
    falls = wrestler.falls  # Ensure using the updated value
    tech_falls = wrestler.tech_falls  # Ensure using the updated value
    major_decisions = wrestler.major_decisions  # Ensure using the updated value

    # Log the values for troubleshooting
    app.logger.info(f"Wrestler {wrestler.name}: Falls = {falls}, Fall Rank = {fall_rank}")
    app.logger.info(f"Wrestler {wrestler.name}: Tech Falls = {tech_falls}, Tech Fall Rank = {tech_fall_rank}")
    app.logger.info(f"Wrestler {wrestler.name}: Major Decisions = {major_decisions}, Major Decision Rank = {major_decision_rank}")

    # Query for matches where the wrestler is wrestler1 or wrestler2 within the selected season
    matches_wrestler1 = Match.query.filter_by(wrestler1_id=wrestler_id, season_id=selected_season_id).all()
    matches_wrestler2 = Match.query.filter_by(wrestler2_id=wrestler_id, season_id=selected_season_id).all()

    # Combine the matches into one list
    matches = matches_wrestler1 + matches_wrestler2

    # Initialize variables for tracking dominance score
    total_points = 0
    total_matches = len(matches)  # Total number of matches

    # Prepare list for match details to be rendered
    match_details = []

    # Loop through each match to calculate dominance score
    for match in matches:
        # Identify the opponent
        if match.wrestler1_id == wrestler_id:
            opponent = match.wrestler2
            is_winner = match.winner_id == wrestler_id
        else:
            opponent = match.wrestler1
            is_winner = match.winner_id == wrestler_id

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
    dominance_score = total_points / total_matches if total_matches > 0 else 0

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
                           conference=wrestler_conference,
                           selected_season=selected_season,
                           selected_season_id=selected_season_id)  # Ensure season_id is passed correctly



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
            # Log incoming form data for debugging
            app.logger.info(f"Form data: {request.form}")

            # Validate and extract form data
            wrestler1_id = int(request.form['wrestler1_id'])
            wrestler2_id = int(request.form['wrestler2_id'])
            winner_id = int(request.form['winner_id'])
            date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            win_type = request.form['win_type']
            wrestler1_score = int(request.form['wrestler1_score'])  # Ensure this field exists
            wrestler2_score = int(request.form['wrestler2_score'])  # Ensure this field exists
            season_id = int(request.form['season_id'])  # Get the season_id from the form

            # Fetch wrestler data from the database
            wrestler1 = Wrestler.query.get(wrestler1_id)
            wrestler2 = Wrestler.query.get(wrestler2_id)

            if not wrestler1 or not wrestler2:
                flash('One or both wrestlers not found.', 'error')
                return redirect(url_for('add_match'))

            if wrestler1.id == wrestler2.id:
                flash('A wrestler cannot compete against themselves.', 'error')
                return redirect(url_for('add_match'))

            if wrestler1.weight_class != wrestler2.weight_class:
                flash('Wrestlers must be in the same weight class to compete.', 'error')
                return redirect(url_for('add_match'))

            # Check if a match already exists
            existing_match = Match.query.filter_by(
                wrestler1_id=wrestler1_id,
                wrestler2_id=wrestler2_id,
                date=date,
                season_id=season_id
            ).first()

            if existing_match:
                flash(f'Match between {wrestler1.name} and {wrestler2.name} on {date.strftime("%Y-%m-%d")} already exists.', 'error')
                return redirect(url_for('add_match'))

            # Handle optional match time for specific win types
            match_time = None
            if win_type in ['Fall', 'Technical Fall']:
                match_time_input = request.form.get('match_time', '')
                if not match_time_input:
                    flash('Match time is required for falls and technical falls.', 'error')
                    return redirect(url_for('add_match'))
                
                # Convert match time to a string in MM:SS format
                try:
                    minutes, seconds = map(int, match_time_input.split(':'))
                    match_time = f"{minutes}:{seconds:02}"
                except ValueError:
                    flash('Invalid match time format. Please use MM:SS.', 'error')
                    return redirect(url_for('add_match'))

            # Create the new match
            new_match = Match(
                date=date,
                wrestler1_id=wrestler1_id,
                wrestler2_id=wrestler2_id,
                winner_id=winner_id,
                win_type=win_type,
                wrestler1_score=wrestler1_score,
                wrestler2_score=wrestler2_score,
                match_time=match_time,
                season_id=season_id
            )
            db.session.add(new_match)

            # Update win/loss records
            if winner_id == wrestler1.id:
                wrestler1.wins += 1
                wrestler2.losses += 1
            else:
                wrestler2.wins += 1
                wrestler1.losses += 1

            # Commit the new match and updates
            db.session.commit()

            # Recalculate stats for both wrestlers with the season_id
            recalculate_elo(wrestler1.id, season_id)
            recalculate_elo(wrestler2.id, season_id)
            recalculate_rpi(wrestler1.id, season_id)
            recalculate_rpi(wrestler2.id, season_id)
            recalculate_hybrid(wrestler1.id, season_id)
            recalculate_hybrid(wrestler2.id, season_id)
            recalculate_dominance(wrestler1.id, season_id)
            recalculate_dominance(wrestler2.id, season_id)
            recalculate_wrestler_stats(wrestler1.id, season_id)
            recalculate_wrestler_stats(wrestler2.id, season_id)

            flash(f'Match added: {wrestler1.name} vs {wrestler2.name}', 'success')
            return redirect(url_for('home', season_id=season_id))

        except Exception as e:
            db.session.rollback()  # Rollback the session on error
            app.logger.error(f"Error adding match: {str(e)}")  # Log the error
            app.logger.error(f"Form data: {request.form}")  # Log the form data that caused the error
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('add_match'))

    # Fetch wrestlers and render the template for GET requests
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
    return render_template('add_match.html', wrestlers=serialized_wrestlers, weight_classes=WEIGHT_CLASSES, seasons=Season.query.all(), season_id=request.args.get('season_id'))




from datetime import datetime, time

@app.route('/edit_match/<int:match_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_match(match_id):
    match = Match.query.get_or_404(match_id)

    if request.method == 'POST':
        try:
            # Log the incoming form data
            app.logger.info(f"Form Data: {request.form}")

            # Get form data
            match.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            match.wrestler1_id = int(request.form['wrestler1_id'])
            match.wrestler2_id = int(request.form['wrestler2_id'])
            match.wrestler1_score = int(request.form['wrestler1_score'])
            match.wrestler2_score = int(request.form['wrestler2_score'])
            new_winner_id = int(request.form['winner_id'])
            match.win_type = request.form['win_type']

            # Handle match_time
            match_time_str = request.form.get('match_time')
            if match.win_type in ['Decision', 'Major Decision']:
                # For Decision and Major Decision, clear match_time
                match.match_time = None
            elif match_time_str:
                # Parse match_time in MM:SS format
                try:
                    minutes, seconds = map(int, match_time_str.split(':'))
                    match.match_time = f"{minutes}:{seconds:02}"  # Ensure two digits for seconds
                except ValueError:
                    flash('Invalid match time format. Please use MM:SS.', 'error')
                    return redirect(url_for('edit_match', match_id=match.id, season_id=match.season_id))
            else:
                match.match_time = None

            # Include season_id from the form or fallback to the current match's season
            season_id = request.form.get('season_id', match.season_id)
            if season_id:
                season_id = int(season_id)
            else:
                app.logger.error("Missing season_id in form data!")
                flash('Missing season_id, please try again.', 'error')
                return redirect(url_for('edit_match', match_id=match.id, season_id=match.season_id))

            # Fetch wrestlers
            wrestler1 = Wrestler.query.get(match.wrestler1_id)
            wrestler2 = Wrestler.query.get(match.wrestler2_id)

            if not wrestler1 or not wrestler2:
                flash('Wrestlers not found. Please verify the input.', 'error')
                return redirect(url_for('edit_match', match_id=match.id, season_id=season_id))

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

            # Recalculate stats for both wrestlers
            recalculate_elo(wrestler1.id, season_id)
            recalculate_elo(wrestler2.id, season_id)
            recalculate_rpi(wrestler1.id, season_id)
            recalculate_rpi(wrestler2.id, season_id)
            recalculate_hybrid(wrestler1.id, season_id)
            recalculate_hybrid(wrestler2.id, season_id)
            recalculate_dominance(wrestler1.id, season_id)
            recalculate_dominance(wrestler2.id, season_id)
            recalculate_wrestler_stats(wrestler1.id, season_id)
            recalculate_wrestler_stats(wrestler2.id, season_id)

            # Commit all changes
            db.session.commit()

            flash('Match has been updated.', 'success')
            return redirect(url_for('wrestler_detail', wrestler_id=wrestler1.id, season_id=season_id))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error occurred: {str(e)}")
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('edit_match', match_id=match.id, season_id=match.season_id))

    wrestlers = Wrestler.query.order_by(Wrestler.weight_class, Wrestler.name).all()
    return render_template('edit_match.html', match=match, wrestlers=wrestlers, seasons=Season.query.all())



@app.route('/edit_wrestler/<int:wrestler_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_wrestler(wrestler_id):
    wrestler = Wrestler.query.get_or_404(wrestler_id)

    # Capture the season_id from query parameters
    season_id = request.args.get('season_id')

    if request.method == 'POST':
        # Get the updated values from the form
        new_name = request.form['name'].strip()
        new_school = request.form['school'].strip()
        new_weight_class = int(request.form['weight_class'])
        new_year_in_school = request.form['year_in_school']  # New field for year in school

        # Check if the weight class has changed
        weight_class_changed = wrestler.weight_class != new_weight_class

        # Update the wrestler's details
        wrestler.name = new_name
        wrestler.school = new_school
        wrestler.year_in_school = new_year_in_school

        # If the weight class changes, reset the Elo, RPI, and other stats
        if weight_class_changed:
            wrestler.weight_class = new_weight_class
            wrestler.elo_rating = 1500  # Reset Elo to default starting value
            wrestler.rpi = 0
            wrestler.dominance_score = 0
            wrestler.wins = 0
            wrestler.losses = 0
            wrestler.falls = 0
            wrestler.tech_falls = 0
            wrestler.major_decisions = 0

        # Validate the form fields
        if not wrestler.name or wrestler.school not in D3_WRESTLING_SCHOOLS or wrestler.weight_class not in WEIGHT_CLASSES:
            flash('Please fill out all fields correctly.', 'error')
            return render_template('edit_wrestler.html', wrestler=wrestler, weight_classes=WEIGHT_CLASSES, schools=D3_WRESTLING_SCHOOLS, season_id=season_id)

        # Commit changes to the database
        try:
            db.session.commit()
            flash(f'Wrestler {wrestler.name} has been updated.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating wrestler: {str(e)}', 'error')
            return render_template('edit_wrestler.html', wrestler=wrestler, weight_classes=WEIGHT_CLASSES, schools=D3_WRESTLING_SCHOOLS, season_id=season_id)

        # Redirect back to the wrestler detail page
        return redirect(url_for('wrestler_detail', wrestler_id=wrestler.id, season_id=season_id))

    return render_template('edit_wrestler.html', wrestler=wrestler, weight_classes=WEIGHT_CLASSES, schools=D3_WRESTLING_SCHOOLS, season_id=season_id)


@app.route('/delete_wrestler/<int:wrestler_id>', methods=['POST'])
@login_required
@admin_required
def delete_wrestler(wrestler_id):
    wrestler = Wrestler.query.get_or_404(wrestler_id)

    # Get the current season ID from the request
    current_season_id = request.args.get('season_id')  # Assuming you pass the current season ID in the query parameters

    # Get matches for the current season
    matches = wrestler.matches_as_wrestler1.filter_by(season_id=current_season_id).all() + \
              wrestler.matches_as_wrestler2.filter_by(season_id=current_season_id).all()

    # Adjust win/loss and stats for opponents in all matches
    for match in matches:
        opponent = match.wrestler2 if match.wrestler1_id == wrestler.id else match.wrestler1

        if match.winner_id == wrestler.id:
            opponent.losses -= 1
        else:
            opponent.wins -= 1

        # Recalculate stats for opponent
        recalculate_elo(opponent.id, current_season_id)
        recalculate_rpi(opponent.id, current_season_id)
        recalculate_hybrid(opponent.id, current_season_id)
        recalculate_dominance(opponent.id, current_season_id)

        # Recalculate wrestler stats for opponents (still necessary)
        recalculate_wrestler_stats(opponent.id, current_season_id)

        # Delete the match from the database
        db.session.delete(match)

    # Delete the wrestler after processing their matches
    db.session.delete(wrestler)
    db.session.commit()

    flash(f'Wrestler {wrestler.name} and all their matches in the current season have been deleted.', 'success')
    return redirect(url_for('home', season_id=current_season_id))



@app.route('/delete_match/<int:match_id>', methods=['POST'])
@login_required
@admin_required
def delete_match(match_id):
    # Fetch the match and wrestlers involved
    match = Match.query.get_or_404(match_id)
    wrestler1 = Wrestler.query.get(match.wrestler1_id)
    wrestler2 = Wrestler.query.get(match.wrestler2_id)

    # Check and revert win/loss records before deleting the match
    if match.winner_id == wrestler1.id:
        wrestler1.wins -= 1
        wrestler2.losses -= 1
    elif match.winner_id == wrestler2.id:
        wrestler2.wins -= 1
        wrestler1.losses -= 1

    # Determine the current season based on the match
    season_id = match.season_id  # Assuming each match has a season_id field

    # Delete the match from the database
    db.session.delete(match)

    # Recalculate stats for both wrestlers after match deletion
    recalculate_wrestler_stats(wrestler1.id, season_id)
    recalculate_wrestler_stats(wrestler2.id, season_id)

    # Recalculate Elo, RPI, Hybrid, and Dominance for both wrestlers
    recalculate_elo(wrestler1.id, season_id)
    recalculate_elo(wrestler2.id, season_id)
    recalculate_rpi(wrestler1.id, season_id)
    recalculate_rpi(wrestler2.id, season_id)
    recalculate_hybrid(wrestler1.id, season_id)
    recalculate_hybrid(wrestler2.id, season_id)
    recalculate_dominance(wrestler1.id, season_id)
    recalculate_dominance(wrestler2.id, season_id)

    # Commit the changes to the database
    db.session.commit()

    # Flash a success message
    flash(f'Match between {wrestler1.name} and {wrestler2.name} has been deleted.', 'success')

    # Get the wrestler_id and season_id from the request arguments, defaulting to wrestler1 if not provided
    wrestler_id = request.args.get('wrestler_id', default=wrestler1.id)
    season_id = request.args.get('season_id')

    # Redirect back to the wrestler details page, using the correct season
    return redirect(url_for('wrestler_detail', wrestler_id=wrestler_id, season_id=season_id))




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
    date_formats = ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d']  # Prioritize your date format

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()  # Return a date object
        except ValueError:
            continue  # Try the next format if the current one fails

    # If none of the formats work, raise an error with all expected formats
    raise ValueError(f"Date '{date_str}' is not in a recognized format. Supported formats: {', '.join(date_formats)}")



def get_or_create_wrestler(name, school, weight_class, season_id):
    """
    This function normalizes the name and school, checks for an existing wrestler
    in the given season, and creates a new one if none exists.
    """
    name = name.strip().title()  # Normalize wrestler name (capitalize properly, remove extra spaces)
    
    # Normalize the school name using the alias normalization function
    school = normalize_school_name(school)

    # Attempt to find a wrestler in the database for the specific season to prevent duplicates
    wrestler = Wrestler.query.filter(
        db.func.lower(Wrestler.name) == name.lower(),
        db.func.lower(Wrestler.school) == school.lower(),
        Wrestler.weight_class == int(weight_class),
        Wrestler.season_id == season_id  # Ensure the wrestler is tied to the correct season
    ).first()

    if not wrestler:
        # If no match found, log the new wrestler creation and create a new record
        app.logger.info(f"Creating new wrestler: {name} from {school} for season {season_id}")
        wrestler = Wrestler(
            name=name, 
            school=school, 
            weight_class=int(weight_class), 
            season_id=season_id,  # Assign to the given season
            wins=0, 
            losses=0, 
            elo_rating=1500,  # Default Elo rating
            rpi=0.0,
            dominance_score=0.0,  # Initialize other stats
            falls=0,  # Initialize falls
            tech_falls=0,  # Initialize tech falls
            major_decisions=0  # Initialize major decisions
        )
        db.session.add(wrestler)
        db.session.commit()
    
    return wrestler

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
                win_type = row['WinType'].strip().lower()  # Convert to lowercase for consistency

                # Parse the date using the flexible date parsing function
                try:
                    raw_date = row['Date']
                    match_date = parse_date(raw_date)  # Use the parse_date function
                except ValueError as e:
                    detailed_feedback.append(f"Row {row_num}: Invalid date format '{raw_date}' ({str(e)}).")
                    row_errors += 1
                    continue

                # Assign the correct season based on the match date
                season = Season.query.filter(Season.start_date <= match_date, Season.end_date >= match_date).first()
                if not season:
                    detailed_feedback.append(f"Row {row_num}: No matching season found for date {match_date}.")
                    row_errors += 1
                    continue
                
                season_id = season.id  # Define season_id here

                # Initialize flags for different types of wins
                match_time = None
                win_flags = {
                    "decision": False,
                    "major_decision": False,
                    "fall": False,
                    "technical_fall": False,
                    "injury_default": False,
                    "sudden_victory": False,
                    "double_overtime": False,
                    "tiebreaker_1": False,
                    "tiebreaker_2": False,
                    "medical_forfeit": False,
                    "disqualification": False,
                }

                # Handle win types and match times
                win_type_mapping = {
                    'decision': 'decision',
                    'dec': 'decision',
                    'major decision': 'major_decision',
                    'major': 'major_decision',
                    'fall': 'fall',
                    'pin': 'fall',
                    'technical fall': 'technical_fall',
                    'tech fall': 'technical_fall',
                    'injury default': 'injury_default',
                    'injury': 'injury_default',
                    'sudden victory': 'sudden_victory',
                    'sv-1': 'sudden_victory',
                    'sudden victory - 1': 'sudden_victory',
                    'tiebreaker': 'tiebreaker_1',
                    'tie breaker': 'tiebreaker_1',
                    'tb-1': 'tiebreaker_1',
                    'tb-2': 'tiebreaker_2',
                    'tiebreaker - 1': 'tiebreaker_1',  # New addition for 'tiebreaker - 1'
                    'tiebreaker - 2 (riding time)': 'tiebreaker_2',  # New addition for 'tiebreaker - 2'
                    'medical forfeit': 'medical_forfeit',
                    'med forfeit': 'medical_forfeit',
                    'disqualification': 'disqualification',
                    'dq': 'disqualification'
                }

                if win_type in win_type_mapping:
                    win_flags[win_type_mapping[win_type]] = True

                    # Match time handling for fall and technical fall
                    if win_flags["fall"] or win_flags["technical_fall"]:
                        try:
                            match_time = datetime.strptime(row['Match_Time'].strip(), '%M:%S').time()
                        except ValueError:
                            detailed_feedback.append(f"Row {row_num}: Invalid match time format for '{win_type}' win type.")
                            row_errors += 1
                            continue
                else:
                    valid_win_types = ", ".join(win_type_mapping.keys())
                    detailed_feedback.append(f"Row {row_num}: Unrecognized win type '{win_type}'. Valid win types are: {valid_win_types}.")
                    row_errors += 1
                    continue

                # Validate weight class
                if weight_class not in WEIGHT_CLASSES:
                    detailed_feedback.append(f"Row {row_num}: Invalid weight class '{weight_class}'.")
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

                # Get or create wrestlers for the season
                wrestler1 = get_or_create_wrestler(wrestler1_name, school1_name, weight_class, season_id)
                wrestler2 = get_or_create_wrestler(wrestler2_name, school2_name, weight_class, season_id)

                # Normalize and strip names to ensure they are compared correctly (case-insensitive)
                wrestler1_name_normalized = wrestler1.name.strip().lower()
                wrestler2_name_normalized = wrestler2.name.strip().lower()
                winner_name_normalized = winner_name.strip().lower()

                # Validate winner name
                if winner_name_normalized not in [wrestler1_name_normalized, wrestler2_name_normalized]:
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
                existing_match = Match.query.filter(
                    db.or_(
                        db.and_(
                            Match.wrestler1_id == wrestler1.id,
                            Match.wrestler2_id == wrestler2.id
                        ),
                        db.and_(
                            Match.wrestler1_id == wrestler2.id,
                            Match.wrestler2_id == wrestler1.id
                        )
                    ),
                    Match.date == match_date,
                    Match.wrestler1_score == wrestler1_score,
                    Match.wrestler2_score == wrestler2_score,
                    Match.win_type == win_type,
                    Match.season_id == season_id,
                    db.or_(
                        Match.match_time == match_time,
                        Match.match_time == None
                    )
                ).first()

                if existing_match:
                    detailed_feedback.append(f"Row {row_num}: Duplicate match detected (already exists).")
                    skipped_duplicates += 1
                    continue

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
                    match_time=match_time,
                    **win_flags,  # Unpack win flags directly
                    season_id=season_id  # Use season_id
                )
                db.session.add(new_match)
                db.session.flush()

                match_ids.append(new_match.id)

                # Update win/loss records and increment falls/tech falls/major decisions
                if winner == wrestler1:
                    wrestler1.wins += 1
                    wrestler2.losses += 1
                    if win_flags["fall"]:
                        wrestler1.falls += 1  # Increment falls for wrestler1
                    if win_flags["technical_fall"]:
                        wrestler1.tech_falls += 1  # Increment tech falls for wrestler1
                    if win_flags["major_decision"]:
                        wrestler1.major_decisions += 1  # Increment major decisions for wrestler1
                else:
                    wrestler2.wins += 1
                    wrestler1.losses += 1
                    if win_flags["fall"]:
                        wrestler2.falls += 1  # Increment falls for wrestler2
                    if win_flags["technical_fall"]:
                        wrestler2.tech_falls += 1  # Increment tech falls for wrestler2
                    if win_flags["major_decision"]:
                        wrestler2.major_decisions += 1  # Increment major decisions for wrestler2

                # After adding the match and updating win/loss records, recalculate statistics
                recalculate_elo(wrestler1.id, season_id)
                recalculate_elo(wrestler2.id, season_id)
                recalculate_rpi(wrestler1.id, season_id)
                recalculate_rpi(wrestler2.id, season_id)
                recalculate_hybrid(wrestler1.id, season_id)
                recalculate_hybrid(wrestler2.id, season_id)
                recalculate_dominance(wrestler1.id, season_id)
                recalculate_dominance(wrestler2.id, season_id)

                # Commit after processing each match
                db.session.commit()
                added_matches += 1
                detailed_feedback.append(
                    f"Row {row_num}: Match added successfully: '{wrestler1_name}' (Weight Class: {weight_class}) vs '{wrestler2_name}' (Weight Class: {weight_class}) with win type '{win_type}'."
                )

            except Exception as e:
                detailed_feedback.append(
                    f"Row {row_num}: Error processing match for '{wrestler1_name}' (Weight Class: {weight_class}) vs '{wrestler2_name}' (Weight Class: {weight_class}) ({str(e)})."
                )
                row_errors += 1
                db.session.rollback()
                continue

        # Save the CSV upload report to the database
        try:
            upload_report = CSVUploadReport(
                user_id=user_id,
                total_matches=added_matches + skipped_duplicates + row_errors,
                added_matches=added_matches,
                skipped_duplicates=skipped_duplicates,
                row_errors=row_errors,
                detailed_feedback=json.dumps(detailed_feedback),
                match_ids=json.dumps(match_ids)
            )
            db.session.add(upload_report)
            db.session.commit()

            logging.info(f"CSV upload report saved successfully with report ID: {upload_report.id}")
        except Exception as e:
            logging.error(f"Error saving CSV upload report: {str(e)}")
            db.session.rollback()

        flash(f"CSV file processed successfully! {added_matches} matches added, {skipped_duplicates} duplicates skipped, {row_errors} errors encountered.", 'success')
        session['csv_feedback'] = detailed_feedback

        return True

    except Exception as e:
        flash(f"An error occurred during CSV processing: {str(e)}", 'error')
        logging.error(f"An error occurred during CSV processing: {str(e)}")
        return False


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

    # Filter by search term if provided
    if search:
        reports_query = reports_query.filter(
            (CSVUploadReport.detailed_feedback.ilike(f'%{search}%')) |
            (CSVUploadReport.total_matches.ilike(f'%{search}%'))
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
                # Check if `detailed_feedback` is already a list
                if not isinstance(report.detailed_feedback, list):
                    # Parse the feedback from JSON format
                    report.detailed_feedback = json.loads(report.detailed_feedback)
            except json.JSONDecodeError:
                # Handle JSON parsing error, set as empty if it fails
                report.detailed_feedback = []
        else:
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
    selected_season_id = request.form.get('season_id')  # Fetch the selected season ID

    if not wrestler_ids:
        flash('No wrestlers selected for deletion.', 'warning')
        return redirect(url_for('rankings', weight_class=request.form.get('weight_class'))) 

    # Ensure wrestlers are fetched from the current season
    wrestlers = Wrestler.query.filter(Wrestler.id.in_(wrestler_ids), Wrestler.season_id == selected_season_id).all()

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

        # Delete the matches and update opponent stats
        for match in matches_as_wrestler1 + matches_as_wrestler2:
            opponent = match.wrestler2 if match.wrestler1_id == wrestler.id else match.wrestler1
            if match.winner_id == wrestler.id:
                opponent.losses -= 1
            else:
                opponent.wins -= 1
            recalculate_elo(opponent.id, selected_season_id)  # Recalculate opponent's Elo after updating wins/losses
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

    # Get the weight class of the first wrestler deleted
    if wrestlers:
        weight_class = wrestlers[0].weight_class

        # Recalculate stats for all remaining wrestlers in the same weight class
        remaining_wrestlers = Wrestler.query.filter_by(weight_class=weight_class, season_id=selected_season_id).all()
        for wrestler in remaining_wrestlers:
            recalculate_wrestler_stats(wrestler.id, selected_season_id)  # Recalculate all relevant stats for remaining wrestlers

    # Flash message and redirect to rankings page
    flash(f'Successfully deleted {len(wrestlers)} wrestler(s) and their associated matches.', 'success')
    return redirect(url_for('rankings', weight_class=weight_class))


@app.route('/clear_data', methods=['POST'])
@login_required
@admin_required
def clear_data():
    # Get the selected season from the request
    selected_season_id = request.args.get('season_id')

    if not selected_season_id:
        flash('No season selected for clearing data.', 'error')
        return redirect(url_for('home'))

    try:
        # Clear matches for the selected season
        db.session.query(Match).filter_by(season_id=selected_season_id).delete()
        db.session.commit()

        # Clear wrestlers for the selected season
        db.session.query(Wrestler).filter_by(season_id=selected_season_id).delete()
        db.session.commit()

        flash(f'All data for the selected season (Season ID: {selected_season_id}) has been cleared successfully.', 'success')
    except Exception as e:
        db.session.rollback()  # Rollback in case of any errors
        flash(f'An error occurred while clearing data for the selected season: {str(e)}', 'error')

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
                # Call the function to process the CSV and get feedback
                feedback, success = validate_and_process_csv(file)

                # If processing was successful
                if success:
                    flash('CSV uploaded and processed successfully!', 'success')
                else:
                    session['csv_feedback'] = feedback  # Store feedback in session
                    flash('CSV upload failed. Check the feedback for details.', 'error')
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload a CSV file.', 'error')

        return redirect(url_for('upload_csv'))

    # For GET request, show the form and fetch feedback from the session
    csv_feedback = session.get('csv_feedback', None)  # Get feedback if it exists
    return render_template('upload_csv.html', csv_feedback=csv_feedback)


@app.route('/search', methods=['GET'])
def search_wrestler():
    query = request.args.get('query', '')
    season_id = request.args.get('season_id', None)  # Get the season_id from query string

    if query:
        # Search for wrestlers whose names match the query (case-insensitive) and join with the season table
        wrestlers = Wrestler.query.join(Season).filter(Wrestler.name.ilike(f"%{query}%")).all()
    else:
        wrestlers = []

    wrestler_data = [{
        'name': wrestler.name,
        'school': wrestler.school,
        'weight_class': wrestler.weight_class,
        'season': wrestler.season.name,  # Season name
        'season_year': wrestler.season.start_date.year,  # Season year for more clarity
        'id': wrestler.id,
        'season_id': wrestler.season_id  # Include the season_id in the data
    } for wrestler in wrestlers]

    # Render a template to show the search results
    return render_template('search_results.html', query=query, wrestler_data=wrestler_data, season_id=season_id)


@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('query', '')
    season_id = request.args.get('season_id', None)  # Get the season_id from query string

    if query:
        # Find wrestlers whose names match the query (case-insensitive search) and join with the season table
        wrestlers = Wrestler.query.join(Season).filter(Wrestler.name.ilike(f"%{query}%")).all()

        # Extract wrestler names, seasons, and their IDs to return as suggestions
        wrestler_names = [{"name": f"{wrestler.name} ({wrestler.season.name} {wrestler.season.start_date.year})",  # Display both season name and year
                           "id": wrestler.id,
                           "season_id": wrestler.season_id}  # Include season_id in the result
                          for wrestler in wrestlers]
    else:
        wrestler_names = []

    return jsonify(wrestler_names)


@app.route('/global-leaderboards', methods=['GET'])
def global_leaderboards():
    # Fetch all seasons for the dropdown
    seasons = Season.query.order_by(Season.start_date.desc()).all()
    logger.info(f"Available seasons: {[season.name for season in seasons]}")

    # Get the selected season from the request, default to the first available season if none is selected
    selected_season_id = request.args.get('season_id')
    if selected_season_id:
        current_season = Season.query.get(selected_season_id)
    else:
        current_season = seasons[0] if seasons else None

    # Check if current_season is None and handle the error
    if not current_season:
        flash("No seasons available.", "error")
        return redirect(url_for('home'))  # Redirect to the home page or an appropriate page

    # Get the name for the current season
    current_season_name = current_season.name if current_season else 'N/A'

    # Log current season info
    logger.info(f"Current season: {current_season_name}")

    # Get the selected weight class from the request
    selected_weight_class = request.args.get('weight_class')

    # Fetch top wrestlers for each win type and the selected season using updated stat tracking
    fall_leaders = get_stat_leaders('Fall', season_id=current_season.id, weight_class=selected_weight_class, limit=20)
    tech_fall_leaders = get_stat_leaders('Technical Fall', season_id=current_season.id, weight_class=selected_weight_class, limit=20)
    major_decision_leaders = get_stat_leaders('Major Decision', season_id=current_season.id, weight_class=selected_weight_class, limit=20)

    # Find the top 20 most dominant wrestlers for the selected season and weight class
    most_dominant_wrestlers = Wrestler.query.filter_by(season_id=current_season.id)

    # If a weight class is selected, filter by weight class
    if selected_weight_class:
        most_dominant_wrestlers = most_dominant_wrestlers.filter_by(weight_class=selected_weight_class)

    most_dominant_wrestlers = most_dominant_wrestlers.order_by(Wrestler.dominance_score.desc()).limit(20).all()

    # Pass weight classes to the template
    weight_classes = WEIGHT_CLASSES  # Assuming this is defined in your app

    # Render the global leaderboard template with all data
    return render_template(
        'global_leaderboards.html',
        fall_leaders=fall_leaders,
        tech_fall_leaders=tech_fall_leaders,
        major_decision_leaders=major_decision_leaders,
        most_dominant_wrestlers=most_dominant_wrestlers,
        current_season_name=current_season_name,
        seasons=seasons,
        selected_season_id=current_season.id,
        selected_weight_class=selected_weight_class,
        weight_classes=weight_classes
    )









@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # Check if the user exists and the password is correct
        if user and user.check_password(password):
            login_user(user)  # Logs the user in

            # Set session variable to indicate admin status
            session['is_admin'] = user.is_admin

            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))  # Redirect to the homepage after login
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()  # This logs the user out
    session.pop('is_admin', None)  # Clear admin status
    flash('Logged out successfully!', 'success')
    return redirect(url_for('landing'))  # Redirect to landing page after logoutedirect(url_for('landing'))  # Redirect to the landing page after logout




# This function can be used to create a new admin user
@app.route('/create_admin')
def create_admin():
    if User.query.filter_by(username='admin').first() is None:
        # Define new user details and set the is_admin flag
        new_user = User(
            username='admin',
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

    # Get the selected season from the request (if applicable)
    selected_season_id = request.form.get('season_id')  # Get the season_id from the form data
    if not selected_season_id:
        flash('No season selected for updating stats.', 'error')
        return redirect(url_for('home'))

    try:
        # Loop through all wrestlers for the selected season
        wrestlers = Wrestler.query.filter_by(season_id=selected_season_id).all()
        for wrestler in wrestlers:
            logger.info(f'Updating stats for wrestler: {wrestler.name}, ID: {wrestler.id}')  # Log wrestler being processed

            # Reset specific stats to recalculate them
            wrestler.falls = 0
            wrestler.tech_falls = 0
            wrestler.major_decisions = 0

            # Fetch all matches for the wrestler in the selected season
            matches = Match.query.filter(
                ((Match.wrestler1_id == wrestler.id) | (Match.wrestler2_id == wrestler.id)) &
                (Match.season_id == selected_season_id)
            ).all()
            
            # Recalculate falls, tech falls, and major decisions
            for match in matches:
                if match.winner_id == wrestler.id:
                    if match.win_type == 'Fall':
                        wrestler.falls += 1
                    elif match.win_type == 'Technical Fall':
                        wrestler.tech_falls += 1
                    elif match.win_type == 'Major Decision':
                        wrestler.major_decisions += 1

        # Commit all changes to the database at once
        db.session.commit()
        flash(f'Falls, Tech Falls, and Major Decisions for Season {selected_season_id} have been successfully updated!', 'success')
    except Exception as e:
        # Rollback changes in case of an error
        db.session.rollback()
        flash(f'An error occurred during the update process: {str(e)}', 'error')

    return redirect(url_for('home'))



@app.route('/add_season', methods=['POST'])
@login_required
def add_season():
    if not current_user.is_admin:
        flash('Only admins can add seasons!', 'danger')
        return redirect(url_for('home'))

    # Get form data
    season_name = request.form.get('season_name')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    # Validate form fields
    if not season_name or not start_date_str or not end_date_str:
        flash('All fields are required: season name, start date, and end date.', 'danger')
        return redirect(url_for('manage_seasons'))

    try:
        # Convert string dates to Python date objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # Deactivate current active season if there is one
        current_active_season = Season.query.filter_by(is_active=True).first()
        if current_active_season:
            current_active_season.is_active = False

        # Create and activate the new season
        new_season = Season(
            name=season_name,
            start_date=start_date,
            end_date=end_date,
            is_active=True  # New season starts as active
        )

        # Add the new season to the database
        db.session.add(new_season)
        db.session.commit()

        flash(f'Season "{season_name}" has been added and activated!', 'success')

    except ValueError as e:
        flash(f'Error parsing dates: {e}', 'danger')

    return redirect(url_for('manage_seasons'))


@app.route('/admin/remove_graduates', methods=['POST'])
@login_required
def remove_graduates():
    if not current_user.is_admin:
        flash('Only admins can remove graduating wrestlers!', 'danger')
        return redirect(url_for('home'))

    # Query all graduating wrestlers
    graduating_wrestlers = Wrestler.query.filter_by(graduating=True).all()

    # Remove them from the database
    for wrestler in graduating_wrestlers:
        db.session.delete(wrestler)

    db.session.commit()

    flash('Graduating wrestlers removed from the system!', 'success')

    # Ensure season_id is included when redirecting
    season_id = request.args.get('season_id')
    return redirect(url_for('home', season_id=season_id))


@app.route('/push_wrestlers_to_new_season', methods=['POST'])
@login_required
@admin_required
def push_wrestlers_to_new_season():
    current_season_id = request.form.get('current_season_id')
    new_season_id = request.form.get('new_season_id')

    if not current_season_id or not new_season_id:
        flash('Invalid season selection.', 'danger')
        return redirect(url_for('manage_seasons'))

    # Query for the wrestlers in the current season
    wrestlers = Wrestler.query.filter_by(season_id=current_season_id).all()

    if not wrestlers:
        flash('No wrestlers found in the current season.', 'danger')
        return redirect(url_for('manage_seasons'))

    def get_next_year_in_school(current_year):
        next_year = {
            'FR': 'SO',
            'SO': 'JR',
            'JR': 'SR',
            'SR': 'SR'  # Seniors stay seniors
        }
        return next_year.get(current_year, 'FR')  # Default to FR if unknown

    # Iterate through wrestlers and push them to the new season
    for wrestler in wrestlers:
        # Check if the wrestler is graduating or not returning
        graduating = 'graduating_{}'.format(wrestler.id) in request.form

        if graduating or wrestler.year_in_school == 'SR':  # Don't push seniors or graduating wrestlers
            continue  # Skip this wrestler if they're graduating or a senior

        # Update year in school (incrementing for next season)
        new_year_in_school = get_next_year_in_school(
            request.form.get(f'year_in_school_{wrestler.id}', wrestler.year_in_school)
        )

        # Check if this wrestler already exists in the new season to prevent duplicates
        existing_wrestler = Wrestler.query.filter_by(
            name=wrestler.name,
            school=request.form.get(f'school_{wrestler.id}', wrestler.school),
            weight_class=request.form.get(f'weight_class_{wrestler.id}', wrestler.weight_class),
            season_id=new_season_id
        ).first()

        if existing_wrestler:
            # Wrestler already exists, skip adding this one
            continue

        # Create new wrestler entry for the new season
        new_wrestler = Wrestler(
            name=wrestler.name,
            school=request.form.get(f'school_{wrestler.id}', wrestler.school),
            weight_class=request.form.get(f'weight_class_{wrestler.id}', wrestler.weight_class),
            year_in_school=new_year_in_school,  # Use the updated year in school
            elo_rating=wrestler.elo_rating,  # Carry over the Elo rating from the previous season
            season_id=new_season_id,
            graduating=False  # Reset graduating status for the new season
        )
        db.session.add(new_wrestler)

    try:
        db.session.commit()
        flash('Wrestlers have been successfully pushed to the new season!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error pushing wrestlers to the new season: {e}', 'danger')

    return redirect(url_for('manage_seasons'))


import logging

@app.route('/manage_seasons')
@login_required
def manage_seasons():
    if not current_user.is_admin:
        flash('Only admins can manage seasons!', 'danger')
        return redirect(url_for('home'))

    # Get all seasons to populate the dropdown
    seasons = Season.query.order_by(Season.start_date.desc()).all()

    # Get the selected season from the dropdown
    selected_season_id = request.args.get('season_id')
    selected_season = Season.query.get(selected_season_id) if selected_season_id else None

    grouped_wrestlers = {}

    if selected_season:
        # Fetch all wrestlers for the selected season
        wrestlers = Wrestler.query.filter_by(season_id=selected_season.id).all()

        # Group wrestlers by the official school name
        for wrestler in wrestlers:
            # Match wrestler school to the correct official name from D3_WRESTLING_SCHOOLS
            official_name = next(
                (school for school in D3_WRESTLING_SCHOOLS if wrestler.school.lower() == school.lower()), 
                wrestler.school
            )

            # Add wrestler to the grouped_wrestlers under the official school name
            if official_name not in grouped_wrestlers:
                grouped_wrestlers[official_name] = []
            grouped_wrestlers[official_name].append(wrestler)

    # Sort the grouped_wrestlers dictionary by official school name alphabetically
    grouped_wrestlers = dict(sorted(grouped_wrestlers.items()))

    # Ensure wrestlers within each school are sorted by weight class
    for school in grouped_wrestlers:
        grouped_wrestlers[school].sort(key=lambda w: w.weight_class)

    # Hardcoded options for schools and weight classes
    school_options = list(D3_WRESTLING_SCHOOLS.keys())
    weight_class_options = [125, 133, 141, 149, 157, 165, 174, 184, 197, 285]

    return render_template(
        'manage_seasons.html',
        seasons=seasons,
        selected_season=selected_season,
        grouped_wrestlers=grouped_wrestlers,
        school_options=school_options,
        weight_class_options=weight_class_options,
        normalize_school_name=normalize_school_name  # Pass the function to the template
    )



# Allowed file extension (CSV)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'





@app.route('/delete_season/<int:season_id>', methods=['POST'])
@login_required
def delete_season(season_id):
    if not current_user.is_admin:
        flash('Only admins can delete seasons!', 'danger')
        return redirect(url_for('manage_seasons'))

    # Fetch the season to delete
    season = Season.query.get_or_404(season_id)

    try:
        # Delete all related data (like wrestlers, matches) before deleting the season
        # Adjust the logic based on how relationships are defined in your models
        Wrestler.query.filter_by(season_id=season.id).delete()
        db.session.delete(season)
        db.session.commit()
        flash(f'Season "{season.name}" and its related data have been deleted!', 'success')
    except Exception as e:
        flash(f'Error deleting season: {e}', 'danger')
        db.session.rollback()

    return redirect(url_for('manage_seasons'))

@app.route('/set_active_season', methods=['POST'])
@login_required
@admin_required
def set_active_season():
    if not current_user.is_admin:
        flash('Only admins can perform this action!', 'danger')
        return redirect(url_for('manage_seasons'))

    # Get the selected season ID from the form
    selected_season_id = request.form.get('season_id')

    if not selected_season_id:
        flash('No season selected.', 'danger')
        return redirect(url_for('manage_seasons'))

    # Find the selected season in the database
    selected_season = Season.query.get(selected_season_id)

    if not selected_season:
        flash('Selected season not found.', 'danger')
        return redirect(url_for('manage_seasons'))

    # Unmark all other seasons as inactive
    all_seasons = Season.query.all()
    for season in all_seasons:
        season.is_active = False

    # Mark the selected season as active
    selected_season.is_active = True

    # Save the changes to the database
    db.session.commit()

    flash(f'Active season set to {selected_season.name}.', 'success')
    return redirect(url_for('manage_seasons'))









if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print(f"Database created at: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.run(debug=True)
