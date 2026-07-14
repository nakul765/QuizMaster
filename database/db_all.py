from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='user')
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    coins = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    profile_image = db.Column(db.String(255), default='default_user.png')
    last_activity_date = db.Column(db.Date, nullable=True)
    
    purchases = db.relationship('UserPurchase', backref='buyer', lazy=True)

class Admin(db.Model):
    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.String(500), default="default_admin.png")
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

class Quizes(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    xp_reward = db.Column(db.Integer, default=0)
    coins = db.Column(db.Integer, default=0)
    time_limit = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class history(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    User_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    quiz_name = db.Column(db.String(100))
    quiz_category = db.Column(db.String(50))
    score = db.Column(db.Integer)
    correct_answer = db.Column(db.Integer)
    wrong_answer = db.Column(db.Integer)
    xp_earned = db.Column(db.Integer)
    coins_earned = db.Column(db.Integer)
    time_taken = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Questions(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    optiona = db.Column(db.String(255))
    optionb = db.Column(db.String(255))
    optionc = db.Column(db.String(255))
    optiond = db.Column(db.String(255))
    answer = db.Column(db.String(255))
    explanation = db.Column(db.Text)

class DailyChallengeHistory(db.Model):
    __tablename__ = 'daily_challenge_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    challenge_date = db.Column(db.Date, default=datetime.utcnow().date)
    score = db.Column(db.Integer)
    correct = db.Column(db.Integer)
    wrong = db.Column(db.Integer)
    unanswered = db.Column(db.Integer)
    coins_earned = db.Column(db.Integer)
    xp_earned = db.Column(db.Integer)
    time_taken = db.Column(db.Integer)

class ShopItem(db.Model):
    __tablename__ = 'shop_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(255))
    is_unique = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchasers = db.relationship('UserPurchase', backref='item', lazy=True)

class UserPurchase(db.Model):
    __tablename__ = 'user_purchases'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('shop_items.id'), nullable=False)
    coins_paid = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Completed')