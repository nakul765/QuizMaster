from flask import render_template, redirect, request, session
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from database.db_all import *
from . import auth

@auth.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        first_name = request.form['first_name'].title().strip()
        last_name = request.form['last_name'].title().strip()
        email = request.form['email'].lower().strip()
        password = request.form['password'].strip()
        xp = 50
        coins = 150
        level = 1
        role = 'user'

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return redirect('/login')

        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
            xp=xp,
            coins=coins,
            level=level,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        session.clear()

        session["user_id"] = new_user.id
        session["first_name"] = new_user.first_name
        session["role"] = new_user.role
        session['xp'] = new_user.xp
        session["coins"] = new_user.coins
        session['level'] = new_user.level

        return redirect('/index')

    return render_template('auth/signup.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email'].lower().strip()
        password = request.form['password'].strip()

        admin = Admin.query.filter_by(
            email=email,
            password=password
        ).first()

        if admin:

            session.clear()

            session["user_id"] = admin.id
            session["first_name"] = "Admin"
            session["role"] = "admin"

            return redirect('/admin')
        
        user = User.query.filter_by(
            email=email,
            password=password
        ).first()

        if user:

            session.clear()

            session["user_id"] = user.id
            session["first_name"] = user.first_name
            session["role"] = user.role
            session["xp"] = user.xp
            session["coins"] = user.coins
            session["level"] = user.level

            return redirect('/index')

        return redirect('/signup')

    return render_template('auth/login.html')


@auth.route('/logout')
def logout():
    session.clear()
    return redirect('/index')