from flask import Flask, render_template, redirect, request, session, Blueprint, abort, send_file, flash, url_for
from datetime import datetime, timedelta
import random
import json
from io import BytesIO
from collections import defaultdict
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Circle, String

from auth import auth
from admin import admin
from database.db_all import db, User, Quizes, history, Questions, DailyChallengeHistory, ShopItem, UserPurchase
import os

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret_key')

database_url = os.getenv("DATABASE_URL")

if database_url:
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "mysql+pymysql://root:@localhost/quiz"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
def create_default_admin():
    admin = User.query.filter_by(role="admin").first()

    if not admin:
        new_admin = User(
            first_name="Admin",
            last_name="User",
            email="admin@gmail.com",
            password="admin@gmail.com",
            role="admin",
            xp=0,
            coins=0,
            level=1,
            streak=0,
            profile_image="default_admin.png"
        )

        db.session.add(new_admin)
        db.session.commit()
with app.app_context():
    db.create_all()
    create_default_admin()

app.register_blueprint(auth)
app.register_blueprint(admin)



def get_level_requirement(level):
    if level == 1:
        return 100
    elif level == 2:
        return 200
    elif level == 3:
        return 350
    elif level == 4:
        return 500
    elif level == 5:
        return 700
    elif level == 6:
        return 900
    elif level == 7:
        return 1100
    elif level == 8:
        return 1300
    elif level == 9:
        return 1500
    elif level == 10:
        return 1800
    return level * 150

def get_level_title(level):
    if level >= 100:
        return "Quiz God"
    elif level >= 75:
        return "Mythic"
    elif level >= 50:
        return "Legend"
    elif level >= 30:
        return "Grand Master"
    elif level >= 20:
        return "Quiz Master"
    elif level >= 10:
        return "Quiz Warrior"
    elif level >= 5:
        return "Explorer"
    return "Beginner"

def add_xp(user, earned_xp):
    user.xp = user.xp or 0
    user.level = user.level or 1
    user.coins = user.coins or 0
    
    old_level = user.level
    user.xp += earned_xp
    level_up_occurred = False
    
    bonus_coins = 0
    unlocked_badges = []
    unlocked_themes = []
    unlocked_frames = []
    
    while user.xp >= get_level_requirement(user.level):
        user.xp -= get_level_requirement(user.level)
        user.level += 1
        level_up_occurred = True
        
        bonus_coins += 100
        
        if user.level % 5 == 0:
            unlocked_badges.append(f"Badge Lvl {user.level}")
        if user.level % 10 == 0:
            unlocked_themes.append(f"Theme Lvl {user.level}")
        if user.level % 20 == 0:
            unlocked_frames.append(f"Frame Lvl {user.level}")

    user.coins += bonus_coins
    current_requirement = get_level_requirement(user.level)
    
    return {
        "level_up": level_up_occurred,
        "old_level": old_level,
        "new_level": user.level,
        "xp_required": current_requirement,
        "bonus_coins": bonus_coins,
        "unlocked_badge": unlocked_badges[-1] if unlocked_badges else None,
        "unlocked_theme": unlocked_themes[-1] if unlocked_themes else None,
        "unlocked_frame": unlocked_frames[-1] if unlocked_frames else None,
        "title": get_level_title(user.level)
    }

def get_daily_challenge_seed_data():
    today_str = datetime.utcnow().strftime("%Y%m%d")
    random.seed(int(today_str))
    return {
        'coins': random.choice([150, 200, 300, 400, 500]),
        'xp': random.choice([100, 200, 300, 400, 500]),
        'difficulty': random.choice(['Easy', 'Medium', 'Hard'])
    }

def resolve_correct_letter(q):
    stored = (q.answer or "").strip()
    if stored.upper() in ("A", "B", "C", "D"):
        return stored.upper()
    option_map = {"A": q.optiona, "B": q.optionb, "C": q.optionc, "D": q.optiond}
    for letter, text in option_map.items():
        if text and text.strip().upper() == stored.upper():
            return letter
    return None

def generate_pdf_certificate_blob(user, quiz, attempt):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    
    style_logo = ParagraphStyle('CertLogo', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#6366f1'), alignment=1, spaceAfter=15)
    style_title = ParagraphStyle('CertTitle', parent=styles['Normal'], fontName='Times-BoldItalic', fontSize=28, leading=32, textColor=colors.HexColor('#1e293b'), alignment=1, spaceAfter=15)
    style_subtitle = ParagraphStyle('CertSubtitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#94a3b8'), alignment=1, spaceAfter=20)
    style_name = ParagraphStyle('CertName', parent=styles['Normal'], fontName='Times-Bold', fontSize=24, leading=28, textColor=colors.HexColor('#1e1b4b'), alignment=1, spaceAfter=15)
    style_body = ParagraphStyle('CertBody', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=16, textColor=colors.HexColor('#475569'), alignment=1, spaceAfter=25)

    story = [Spacer(1, 20)]
    story.append(Paragraph("✦ QUIZMASTER PRO ✦", style_logo))
    story.append(Paragraph("Certificate of Achievement", style_title))
    story.append(Paragraph("THIS CREDENTIAL REGISTRY HONORS THE SUCCESSFUL COMPLETION OF VERIFICATION CRITERIA", style_subtitle))
    story.append(Spacer(1, 10))
    
    full_name = f"{user.first_name} {user.last_name}"
    story.append(Paragraph(full_name, style_name))
    story.append(Spacer(1, 5))
    
    cert_id = f"QM-{user.id:03d}-{quiz.id:03d}-{attempt.id:04d}"
    completion_date = attempt.date.strftime("%d %B %Y") if hasattr(attempt, 'date') and attempt.date else "08 July 2026"
    
    body_text = f"For demonstrating academic proficiency in <b>{quiz.title}</b> under the specialized category <b>{quiz.category}</b> with an evaluation accuracy score of <b>{attempt.score}%</b>."
    story.append(Paragraph(body_text, style_body))
    story.append(Spacer(1, 15))
    
    meta_style_left = ParagraphStyle('MetaL', fontName='Helvetica-Bold', fontSize=8, leading=12, textColor=colors.HexColor('#64748b'))
    meta_data = [[Paragraph(f"Final Score: <b>{attempt.score}/100 ({attempt.score}%)</b><br/>Validation Hash: <b>{cert_id}</b><br/>Issue Date: <b>{completion_date}</b>", meta_style_left), ""]]
    
    badge_drawing = Drawing(120, 60)
    badge_drawing.add(Circle(60, 30, 24, strokeColor=colors.HexColor('#f59e0b'), strokeWidth=3, fillColor=colors.HexColor('#fffbeb')))
    badge_drawing.add(Circle(60, 30, 20, strokeColor=colors.HexColor('#d97706'), strokeWidth=1, fillColor=colors.transparent))
    badge_drawing.add(String(46, 27, "VERIFIED", fontName="Helvetica-Bold", fontSize=6, fillColor=colors.HexColor('#b45309')))
    
    meta_table = Table([[meta_data[0][0], badge_drawing]], colWidths=[500, 220])
    meta_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'BOTTOM'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
    story.append(meta_table)

    def draw_certificate_borders(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#1e1b4b'))
        canvas.setLineWidth(4)
        canvas.rect(16, 16, 760, 580)
        canvas.setStrokeColor(colors.HexColor('#312e81'))
        canvas.setLineWidth(1)
        canvas.rect(22, 22, 748, 568)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.setFillColor(colors.HexColor('#312e81'))
        canvas.drawString(28, 572, "✦")
        canvas.drawString(752, 572, "✦")
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_certificate_borders)
    buffer.seek(0)
    return buffer

@app.context_processor
def inject_user_data():
    if 'user_id' not in session:
        return {}
    user = User.query.get(session['user_id'])
    if not user:
        return {}
    lvl = user.level or 1
    current_xp = user.xp or 0
    req_xp = get_level_requirement(lvl)
    progress_pct = int((current_xp / req_xp) * 100) if req_xp > 0 else 0
    purchased_ids = [p.item_id for p in user.purchases]
    return {
        "user": user,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": user.role,
        "level": lvl,
        "xp": current_xp,
        "coins": user.coins or 0,
        "streak": user.streak or 0,
        "xp_required": req_xp,
        "level_percent": progress_pct,
        "level_title": get_level_title(lvl),
        "total_quiz": getattr(user, "total_quiz", 0),
        "correct_answers": getattr(user, "correct_answers", 0),
        "wrong_answers": getattr(user, "wrong_answers", 0),
        "purchased_ids": purchased_ids
    }

@app.route('/')
def home():
    return render_template('landing.html')

def get_recent_activity(user_history, limit=5):
    recent = list(reversed(user_history))[:limit]
    return [
        {
            "quiz_name": h.quiz_name,
            "score": h.score,
            "xp": h.xp_earned,
            "coins": h.coins_earned,
            "date": h.date.strftime('%d %b %Y')
        }
        for h in recent
    ]

def get_quick_stats(user, user_history, daily_history, category_scores):
    if user_history:
        scores = [h.score for h in user_history]
        highest_score = max(scores)
        lowest_score = min(scores)
        average_score = round(sum(scores) / len(scores), 1)
        fastest_quiz = min(user_history, key=lambda h: h.time_taken).time_taken
        longest_quiz = max(user_history, key=lambda h: h.time_taken).time_taken
    else:
        highest_score = lowest_score = average_score = 0
        fastest_quiz = longest_quiz = 0
    if category_scores:
        category_averages = {
            cat: sum(scores) / len(scores) for cat, scores in category_scores.items()
        }
        best_category = max(category_averages, key=category_averages.get)
        worst_category = min(category_averages, key=category_averages.get)
    else:
        best_category = worst_category = "N/A"
    return {
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "average_score": average_score,
        "best_category": best_category,
        "worst_category": worst_category,
        "fastest_quiz": fastest_quiz,
        "longest_quiz": longest_quiz,
        "daily_challenges_completed": len(daily_history),
        "current_streak": user.streak or 0
    }

def get_top_performers(limit=5):
    top_users = User.query.order_by(
        User.level.desc(), User.xp.desc(), User.coins.desc()
    ).limit(limit).all()
    return [
        {
            "name": f"{u.first_name} {u.last_name}",
            "level": u.level or 1,
            "xp": u.xp or 0,
            "avatar": u.profile_image or "default_user.png"
        }
        for u in top_users
    ]

@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get_or_404(session['user_id'])
    user_history = history.query.filter_by(User_id=user.id).order_by(history.date.asc()).all()
    daily_history = DailyChallengeHistory.query.filter_by(user_id=user.id).all()
    user.level = user.level or 1
    user.xp = user.xp or 0
    user.coins = user.coins or 0
    level_title = get_level_title(user.level)
    xp_required = get_level_requirement(user.level)
    xp_progress_percent = int((user.xp / xp_required) * 100) if xp_required else 0
    today_date = datetime.utcnow().strftime('%B %d, %Y')
    total_xp_earned = sum(h.xp_earned for h in user_history) + sum(d.xp_earned for d in daily_history)
    quizzes_attempted = len(user_history)
    total_seconds = sum(h.time_taken for h in user_history)
    study_hours = round(total_seconds / 3600, 1)
    global_rank = calculate_global_rank(user)
    total_correct = sum(h.correct_answer for h in user_history) + sum(d.correct for d in daily_history)
    total_wrong = sum(h.wrong_answer for h in user_history) + sum(d.wrong for d in daily_history)
    total_answered = total_correct + total_wrong
    accuracy = int((total_correct * 100) / total_answered) if total_answered > 0 else 0
    weekday_map = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
    practice_seconds_by_day = defaultdict(int)
    today = datetime.utcnow().date()
    for i in range(7):
        day = today - timedelta(days=6-i)
        practice_seconds_by_day[day.strftime('%Y-%m-%d')] = 0
    for h in user_history:
        h_date_str = h.date.strftime('%Y-%m-%d')
        if h_date_str in practice_seconds_by_day:
            practice_seconds_by_day[h_date_str] += h.time_taken
    chart_days_labels = []
    chart_hours_data = []
    for day_str in sorted(practice_seconds_by_day.keys()):
        dt = datetime.strptime(day_str, '%Y-%m-%d')
        chart_days_labels.append(weekday_map[dt.weekday()])
        chart_hours_data.append(round(practice_seconds_by_day[day_str] / 3600, 2))
    recent_attempts = user_history[-6:]
    chart_score_labels = [f"Quiz {idx+1}" for idx in range(len(recent_attempts))]
    chart_score_data = [h.score for h in recent_attempts]
    category_scores = defaultdict(list)
    for h in user_history:
        category_scores[h.quiz_category].append(h.score)
    chart_cat_labels = list(category_scores.keys())[:6]
    chart_cat_data = [int(sum(scores)/len(scores)) for cat, scores in category_scores.items() if cat in chart_cat_labels]
    chart_progress_labels = [h.date.strftime('%b') for h in recent_attempts]
    chart_progress_data = []
    running_total_score = 0
    for idx, h in enumerate(recent_attempts):
        running_total_score += h.score
        chart_progress_data.append(int(running_total_score / (idx + 1)))
    recent_activity = get_recent_activity(user_history, limit=5)
    quick_stats = get_quick_stats(user, user_history, daily_history, category_scores)
    top_performers = get_top_performers(limit=5)
    daily_reward = get_daily_challenge_seed_data()
    return render_template(
        'home/index.html',
        first_name=user.first_name,
        streak=user.streak or 0,
        today_date=today_date,
        level=user.level,
        level_title=level_title,
        xp_current=user.xp,
        xp_required=xp_required,
        xp_progress_percent=xp_progress_percent,
        coins=user.coins,
        total_xp_earned=total_xp_earned,
        quizzes_attempted=quizzes_attempted,
        study_hours=study_hours,
        global_rank=global_rank,
        accuracy=accuracy,
        chart_days_labels=json.dumps(chart_days_labels),
        chart_hours_data=json.dumps(chart_hours_data),
        chart_score_labels=json.dumps(chart_score_labels),
        chart_score_data=json.dumps(chart_score_data),
        chart_cat_labels=json.dumps(chart_cat_labels),
        chart_cat_data=json.dumps(chart_cat_data),
        chart_progress_labels=json.dumps(chart_progress_labels),
        chart_progress_data=json.dumps(chart_progress_data),
        recent_activity=recent_activity,
        quick_stats=quick_stats,
        top_performers=top_performers,
        daily_reward=daily_reward
    )

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('home/dashboard.html')

@app.route('/explore_quizes')
def explore_quizes():
    if 'user_id' not in session:
        return redirect('/login')
    quiz_length = Quizes.query.count()
    recent_quizes = Quizes.query.order_by(Quizes.created_at.desc()).limit(4).all()
    return render_template('quiz/explore_quizes.html', quiz_length=quiz_length, recent_quizes=recent_quizes)

@app.route('/practice_arena')
def practice_arena():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('practice/practice_arena.html')

@app.route('/achivements')
def achivements():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('community/achivements.html')

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('settings/settings.html')

@app.route('/puzzle_zone')
def puzzle_zone():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('practice/puzzle_zone.html')

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/all_quizes')
def all_quizes():
    quizes = Quizes.query.all()
    return render_template('quiz/all_quizes.html', quizes=quizes)

@app.route('/quiz_history', methods=['GET', 'POST'])
def quiz_history():
    if 'user_id' not in session:
        return redirect('/login')
    history_log = history.query.filter_by(User_id=session.get('user_id')).all()
    return render_template('quiz/quiz_history.html', history_log=history_log)

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('role') == 'user':
        return redirect('/index')
    quizes = Quizes.query.all()
    selected_quiz = None
    quiz_questions = []
    selected_quiz_id = session.get("selected_quiz")
    if selected_quiz_id:
        selected_quiz = Quizes.query.get(selected_quiz_id)
        if selected_quiz:
            quiz_questions = Questions.query.filter_by(quiz_id=selected_quiz.id).all()
    return render_template(
        "admin/admin.html",
        quizes=quizes,
        selected_quiz=selected_quiz,
        quiz_questions=quiz_questions
    )

@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session:
        return redirect('/login')
    users = User.query.filter(User.role != "admin").order_by(User.level.desc(),User.xp.desc(),User.coins.desc()).all()
    return render_template('community/leaderboard.html', top3=users[:3], others=users[3:])

@app.route('/download_certificate/<int:attempt_id>')
def download_certificate(attempt_id):
    if 'user_id' not in session:
        return redirect('/login')
    attempt = history.query.get_or_404(attempt_id)
    if attempt.User_id != session['user_id']:
        abort(403)
    user = User.query.get_or_404(attempt.User_id)
    quiz = Quizes.query.get_or_404(attempt.quiz_id)
    pdf_buffer = generate_pdf_certificate_blob(user, quiz, attempt)
    filename = f"Certificate_{user.first_name}_{user.last_name}_{quiz.title}".replace(" ", "_") + ".pdf"
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)

@app.route('/quiz_exam/<int:quiz_id>')
def quiz_exam(quiz_id):
    if 'user_id' not in session:
        return redirect('/login')
    quiz = Quizes.query.get_or_404(quiz_id)
    questions = Questions.query.filter_by(quiz_id=quiz_id).all()
    return render_template('quiz/quiz_exam.html', questions=questions, quiz=quiz)

@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect('/login')
    quiz = Quizes.query.get_or_404(quiz_id)
    questions = Questions.query.filter_by(quiz_id=quiz_id).all()
    total_questions = len(questions)
    time_taken = int(request.form.get("time_taken", 0))
    if total_questions == 0:
        return redirect('/explore_quizes')
    wrong = 0
    correct = 0
    unanswered = 0
    review_data = []
    for question in questions:
        user_answer = request.form.get(f"question_{question.id}")
        if not user_answer:
            status = 'skipped'
            unanswered += 1
            user_selected = None
        else:
            user_selected = user_answer.strip()
            if user_selected == question.answer.strip():
                status = 'correct'
                correct += 1
            else:
                status = 'wrong'
                wrong += 1
        review_data.append({
            'question_text': question.question,
            'user_answer': user_selected,
            'correct_answer': question.answer,
            'explanation': getattr(question, 'explanation', 'Python offering clear object orchestration layer structures.'),
            'status': status
        })
    user_score = int((correct * 100) / total_questions)
    user_xp_earned = int((correct * quiz.xp_reward) / total_questions)
    total_coins_earned = int((correct * quiz.coins) / total_questions)
    user = User.query.get(session.get('user_id'))
    user.coins = (user.coins or 0) + int(total_coins_earned)
    update_user_streak(user)
    xp_report = add_xp(user, user_xp_earned)
    attempt_entry = history(
        User_id=user.id,
        quiz_id=quiz.id,
        quiz_name=quiz.title,
        quiz_category=quiz.category,
        score=user_score,
        correct_answer=correct,
        wrong_answer=wrong,
        xp_earned=user_xp_earned,
        coins_earned=int(total_coins_earned),
        time_taken=time_taken,
        completed_at=datetime.utcnow(),
        date=datetime.utcnow()
    )
    db.session.add(attempt_entry)
    db.session.commit()
    history_log = history.query.filter_by(User_id=user.id, quiz_id=quiz_id).order_by(history.date.desc()).all()
    return render_template(
        'quiz/result.html',
        quiz=quiz,
        quiz_title=quiz.title,
        quiz_category=quiz.category,
        quiz_timelimit=quiz.time_limit,
        user_score=user_score,
        user_level=user.level,
        questions=questions,
        correct=correct,
        wrong=wrong,
        unanswered_count=unanswered,
        user_marks=correct,
        total_quiz_marks=total_questions,
        user_xp=user_xp_earned,
        total_coins=int(total_coins_earned),
        user_name=user.first_name,
        user_surname=user.last_name,
        user_email=user.email,
        role=user.role,
        xp=user.xp,
        review_data=review_data,
        attempt_id=attempt_entry.id,
        history_log=history_log,
        xp_report=xp_report
    )

@app.route('/daily_challenge')
def daily_challenge():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template("practice/daily_challenge.html")

@app.route('/challenge')
def challenge():
    if 'user_id' not in session:
        return redirect('/login')
    meta = get_daily_challenge_seed_data()
    all_questions = Questions.query.all()
    if not all_questions:
        return redirect('/daily_challenge')
    random.shuffle(all_questions)
    selected_questions = all_questions[:20]
    session["daily_questions"] = [q.id for q in selected_questions]
    return render_template(
        "practice/challenge.html",
        questions=selected_questions,
        challenge_meta=meta
    )

@app.route('/submit_daily_challenge', methods=['POST'])
def submit_daily_challenge():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get_or_404(session['user_id'])
    meta = get_daily_challenge_seed_data()
    question_ids = session.get("daily_questions", [])
    questions = [Questions.query.get(qid) for qid in question_ids if Questions.query.get(qid)]
    if not questions:
        return redirect('/challenge')
    correct = 0
    wrong = 0
    unanswered = 0
    for q in questions:
        ans = request.form.get(f"question_{q.id}")
        correct_letter = resolve_correct_letter(q)
        if not ans:
            unanswered += 1
        elif correct_letter and ans.strip().upper() == correct_letter:
            correct += 1
        else:
            wrong += 1
    total = len(questions)
    score = int((correct * 100) / total)
    final_coins = int((correct * meta["coins"]) / total)
    final_xp = int((correct * meta["xp"]) / total)
    user.coins = (user.coins or 0) + final_coins
    update_user_streak(user)
    xp_report = add_xp(user, final_xp)
    history_entry = DailyChallengeHistory(
        user_id=user.id,
        challenge_date=datetime.utcnow().date(),
        score=score,
        correct=correct,
        wrong=wrong,
        unanswered=unanswered,
        coins_earned=final_coins,
        xp_earned=final_xp,
        time_taken=int(request.form.get("time_taken_elapsed", 0))
    )
    db.session.add(history_entry)
    db.session.commit()
    session.pop("daily_questions", None)
    history_log = DailyChallengeHistory.query.filter_by(user_id=user.id).order_by(DailyChallengeHistory.challenge_date.desc()).all()
    return render_template(
        "practice/challenge_result.html",
        user_name=user.first_name,
        user_surname=user.last_name,
        user_score=score,
        correct=correct,
        wrong=wrong,
        unanswered=unanswered,
        total_questions=total,
        history=history_log,
        xp_report=xp_report
    )

def update_user_streak(user):
    today = datetime.utcnow().date()
    if user.streak is None:
        user.streak = 0
    if not user.last_activity_date:
        user.streak = 1
        user.last_activity_date = today
        return
    if user.last_activity_date == today:
        return
    yesterday = today - timedelta(days=1)
    if user.last_activity_date == yesterday:
        user.streak += 1
        if user.streak == 7:
            user.coins = (user.coins or 0) + 100
        elif user.streak == 30:
            user.coins = (user.coins or 0) + 500
    else:
        user.streak = 1
    user.last_activity_date = today

def calculate_global_rank(user):
    better_users = User.query.filter(
        (User.level > user.level) |
        ((User.level == user.level) & (User.xp > user.xp)) |
        ((User.level == user.level) & (User.xp == user.xp) & (User.coins > user.coins))
    ).count()
    return better_users + 1

@app.route('/shop')
def shop():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get_or_404(session['user_id'])
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    sort = request.args.get('sort', 'newest')
    query = ShopItem.query
    if search:
        query = query.filter(ShopItem.name.like(f"%{search}%"))
    if category:
        query = query.filter(ShopItem.category == category)
    if sort == 'low_high':
        query = query.order_by(ShopItem.price.asc())
    elif sort == 'high_low':
        query = query.order_by(ShopItem.price.desc())
    else:
        query = query.order_by(ShopItem.created_at.desc())
    items = query.all()
    purchased_ids = [p.item_id for p in user.purchases]
    return render_template(
        'shop/shop.html',
        items=items,
        coins=user.coins,
        purchased_ids=purchased_ids,
        search=search,
        category=category,
        sort=sort
    )

@app.route('/shop/purchase/<int:item_id>', methods=['POST'])
def purchase_item(item_id):
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get_or_404(session['user_id'])
    item = ShopItem.query.get_or_404(item_id)
    if item.stock <= 0:
        flash('Item is out of stock.', 'error')
        return redirect(url_for('shop'))
    if user.coins < item.price:
        flash('Insufficient coins.', 'error')
        return redirect(url_for('shop'))
    if item.is_unique:
        already_owned = UserPurchase.query.filter_by(user_id=user.id, item_id=item.id).first()
        if already_owned:
            flash('You already own this unique item.', 'error')
            return redirect(url_for('shop'))
    user.coins -= item.price
    item.stock -= 1
    purchase = UserPurchase(
        user_id=user.id,
        item_id=item.id,
        coins_paid=item.price,
        quantity=1,
        purchase_date=datetime.utcnow(),
        status='Completed'
    )
    db.session.add(purchase)
    db.session.commit()
    flash('Purchase successful!', 'success')
    return redirect(url_for('shop'))

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get_or_404(session['user_id'])
    search = request.args.get('search', '')
    filt = request.args.get('filter', 'all')
    sort = request.args.get('sort', 'newest')
    query = UserPurchase.query.filter_by(user_id=user.id)
    if search:
        query = query.join(ShopItem).filter(ShopItem.name.like(f"%{search}%"))
    now = datetime.utcnow()
    if filt == 'today':
        query = query.filter(UserPurchase.purchase_date >= now.replace(hour=0, minute=0, second=0, microsecond=0))
    elif filt == 'week':
        query = query.filter(UserPurchase.purchase_date >= now - timedelta(days=7))
    elif filt == 'month':
        query = query.filter(UserPurchase.purchase_date >= now - timedelta(days=30))
    if sort == 'oldest':
        query = query.order_by(UserPurchase.purchase_date.asc())
    elif sort == 'highest_price':
        query = query.order_by(UserPurchase.coins_paid.desc())
    elif sort == 'lowest_price':
        query = query.order_by(UserPurchase.coins_paid.asc())
    else:
        query = query.order_by(UserPurchase.purchase_date.desc())
    purchases = query.all()
    return render_template(
        'shop/orders.html',
        purchases=purchases,
        search=search,
        filter=filt,
        sort=sort
    )

@app.route('/admin/shop')
def admin_shop():
    if 'user_id' not in session or session.get('role') == 'user':
        return redirect('/index')
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    stock_status = request.args.get('stock_status', '')
    sort = request.args.get('sort', 'newest')
    query = ShopItem.query
    if search:
        query = query.filter(ShopItem.name.like(f"%{search}%"))
    if category:
        query = query.filter(ShopItem.category == category)
    if stock_status == 'in_stock':
        query = query.filter(ShopItem.stock > 5)
    elif stock_status == 'low_stock':
        query = query.filter(ShopItem.stock > 0, ShopItem.stock <= 5)
    elif stock_status == 'out_of_stock':
        query = query.filter(ShopItem.stock <= 0)
    if sort == 'oldest':
        query = query.order_by(ShopItem.created_at.asc())
    elif sort == 'highest_price':
        query = query.order_by(ShopItem.price.desc())
    elif sort == 'lowest_price':
        query = query.order_by(ShopItem.price.asc())
    else:
        query = query.order_by(ShopItem.created_at.desc())
    items = query.all()
    total_purchases_count = UserPurchase.query.count()
    editing_id = request.args.get('edit')
    editing_item = None
    if editing_id:
        editing_item = ShopItem.query.get(editing_id)
    return render_template(
        'admin/admin_shop.html',
        items=items,
        total_purchases_count=total_purchases_count,
        search=search,
        category=category,
        stock_status=stock_status,
        sort=sort,
        editing_item=editing_item
    )

@app.route('/admin/shop/add', methods=['POST'])
def add_item():
    if 'user_id' not in session or session.get('role') == 'user':
        return redirect('/index')
    name = request.form.get('name')
    description = request.form.get('description')
    price = int(request.form.get('price', 0))
    stock = int(request.form.get('stock', 0))
    category = request.form.get('category')
    image_url = request.form.get('image_url')
    is_unique = True if request.form.get('is_unique') else False
    item = ShopItem(
        name=name,
        description=description,
        price=price,
        stock=stock,
        category=category,
        image_url=image_url,
        is_unique=is_unique
    )
    db.session.add(item)
    db.session.commit()
    flash('Product entry created successfully.', 'success')
    return redirect(url_for('admin_shop'))

@app.route('/admin/shop/update/<int:item_id>', methods=['POST'])
def update_item(item_id):
    if 'user_id' not in session or session.get('role') == 'user':
        return redirect('/index')
    item = ShopItem.query.get_or_404(item_id)
    item.name = request.form.get('name')
    item.description = request.form.get('description')
    item.price = int(request.form.get('price', 0))
    item.stock = int(request.form.get('stock', 0))
    item.category = request.form.get('category')
    item.image_url = request.form.get('image_url')
    item.is_unique = True if request.form.get('is_unique') else False
    db.session.commit()
    flash('Product entry updated successfully.', 'success')
    return redirect(url_for('admin_shop'))

@app.route('/admin/shop/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'user_id' not in session or session.get('role') == 'user':
        return redirect('/index')
    item = ShopItem.query.get_or_404(item_id)
    UserPurchase.query.filter_by(item_id=item_id).delete()
    db.session.delete(item)
    db.session.commit()
    flash('Product entry purged successfully.', 'success')
    return redirect(url_for('admin_shop'))

@app.route('/admin/orders')
def admin_orders():
    if 'user_id' not in session or session.get('role') == 'user':
        return redirect('/index')
    search = request.args.get('search', '')
    filt = request.args.get('filter', 'all')
    sort = request.args.get('sort', 'newest')
    query = UserPurchase.query.join(User)
    if search:
        query = query.filter((User.first_name.like(f"%{search}%")) | (User.last_name.like(f"%{search}%")))
    now = datetime.utcnow()
    if filt == 'today':
        query = query.filter(UserPurchase.purchase_date >= now.replace(hour=0, minute=0, second=0, microsecond=0))
    elif filt == 'week':
        query = query.filter(UserPurchase.purchase_date >= now - timedelta(days=7))
    elif filt == 'month':
        query = query.filter(UserPurchase.purchase_date >= now - timedelta(days=30))
    if sort == 'oldest':
        query = query.order_by(UserPurchase.purchase_date.asc())
    elif sort == 'highest_price':
        query = query.order_by(UserPurchase.coins_paid.desc())
    elif sort == 'lowest_price':
        query = query.order_by(UserPurchase.coins_paid.asc())
    else:
        query = query.order_by(UserPurchase.purchase_date.desc())
    orders = query.all()
    return render_template('admin_orders.html', orders=orders, search=search, filter=filt, sort=sort)

@app.route('/inventory')
def inventory():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get_or_404(session['user_id'])
    purchases = UserPurchase.query.filter_by(user_id=user.id).all()
    unique_items = []
    seen_ids = set()
    for p in purchases:
        if p.item.is_unique and p.item_id not in seen_ids:
            unique_items.append(p.item)
            seen_ids.add(p.item_id)
    return render_template('shop/inventory.html', items=unique_items)

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or session.get('role') == 'user':
        return redirect('/index')

    search = request.args.get('search', '')
    filt = request.args.get('filter', 'all')

    total_users = User.query.count()
    total_admins = User.query.filter_by(role='admin').count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_coins = db.session.query(db.func.sum(User.coins)).scalar() or 0
    avg_level = db.session.query(db.func.avg(User.level)).scalar() or 1
    avg_level = round(float(avg_level), 1)

    query = User.query

    if search:
        query = query.filter(
            (User.first_name.like(f"%{search}%")) |
            (User.last_name.like(f"%{search}%")) |
            (User.email.like(f"%{search}%"))
        )

    if filt == 'admins':
        query = query.filter_by(role='admin')
    elif filt == 'students':
        query = query.filter_by(role='user')
    elif filt == 'highest_level':
        query = query.order_by(User.level.desc())
    elif filt == 'lowest_level':
        query = query.order_by(User.level.asc())
    elif filt == 'newest':
        query = query.order_by(User.created_at.desc())
    elif filt == 'oldest':
        query = query.order_by(User.created_at.asc())

    users = query.all()

    history_counts = {r[0]: r[1] for r in db.session.query(history.User_id, db.func.count(history.id)).group_by(history.User_id).all()}
    challenge_counts = {r[0]: r[1] for r in db.session.query(DailyChallengeHistory.user_id, db.func.count(DailyChallengeHistory.id)).group_by(DailyChallengeHistory.user_id).all()}

    for u in users:
        u.total_quizzes = history_counts.get(u.id, 0)
        u.total_challenges = challenge_counts.get(u.id, 0)
        u.achievements_count = (u.level // 5) + (u.level // 10) + (u.level // 20)

    return render_template(
        'admin/admin_user.html',
        users=users,
        search=search,
        filter=filt,
        stats={
            "total_users": total_users,
            "total_admins": total_admins,
            "total_coins": total_coins,
            "avg_level": avg_level
        }
    )

@app.route('/admin/users/edit/<int:user_id>', methods=['POST'])
def admin_edit_user(user_id):
    if 'user_id' not in session or session.get('role') == 'user':
        return redirect('/index')

    user = User.query.get_or_404(user_id)
    email = request.form.get('email')
    
    duplicate = User.query.filter(User.email == email, User.id != user_id).first()
    if duplicate:
        flash('Email address is already registered to another user account.', 'error')
        return redirect(url_for('admin_users'))

    level = int(request.form.get('level', 1))
    xp = int(request.form.get('xp', 0))
    coins = int(request.form.get('coins', 0))
    streak = int(request.form.get('streak', 0))

    if level < 1 or xp < 0 or coins < 0 or streak < 0:
        flash('Level, XP, Coins, and Streak values must be non-negative operational balances.', 'error')
        return redirect(url_for('admin_users'))

    user.first_name = request.form.get('first_name')
    user.last_name = request.form.get('last_name')
    user.email = email
    user.role = request.form.get('role')
    user.level = level
    user.xp = xp
    user.coins = coins
    user.streak = streak
    user.profile_image = request.form.get('profile_image')

    password = request.form.get('password')
    if password and password.strip():
        user.password = password.strip()

    db.session.commit()
    flash('User profile parameters synchronized successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'user_id' not in session or session.get('role') == 'user':
        return redirect('/index')

    user = User.query.get_or_404(user_id)

    if user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Operation denied. Cannot purge the last remaining platform administrator record.', 'error')
            return redirect(url_for('admin_users'))

    history.query.filter_by(User_id=user_id).delete()
    DailyChallengeHistory.query.filter_by(user_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User record cleared successfully.', 'success')
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    app.run()