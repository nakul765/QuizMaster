from flask import render_template, redirect, request, session
from datetime import datetime
from database.db_all import *
from . import admin

@admin.route('/add_quiz', methods=['GET','POST'])
def add_quiz():
    if request.method == 'POST':

        title = request.form['title'].title().strip()
        description = request.form['description'].lower().strip()
        category = request.form['category']
        time_limit = request.form['time_limit']
        xp_reward = request.form['xp_reward'] 
        coins = request.form['coins']

        new_quiz = Quizes(title=title,
                        description=description,
                        category=category,
                        time_limit=time_limit,
                        xp_reward=xp_reward,
                        coins=coins)

        db.session.add(new_quiz)
        db.session.commit()

        return redirect('/admin')

@admin.route('/delete_quiz/<int:id>')
def delete_quiz(id):
    quiz = Quizes.query.get_or_404(id)
    if quiz:
        db.session.delete(quiz)
        db.session.commit()
        return redirect('/admin')
    return redirect('/admin')


@admin.route('/select_quiz', methods=['POST'])
def select_quiz():
    
    session["selected_quiz"] = int(request.form["select_quiz"])       

    return redirect("/admin")

@admin.route('/add_question', methods=['GET','POST'])
def add_question():
    if request.method == 'POST':
        question = request.form['question']
        optiona = request.form['optiona']
        optionb = request.form['optionb']
        optionc = request.form['optionc']
        optiond = request.form['optiond']
        answer = request.form['answer']
        quiz_id = int(request.form['quiz_id'])

        if(answer == 'optiona'):
            answer = optiona
        elif(answer == 'optionb'):
            answer = optionb
        elif(answer == 'optionc'):
            answer = optionc
        else:
            answer = optiond

        new_question = Questions(
            question=question,
            optiona=optiona,
            optionb=optionb,
            optionc=optionc,
            optiond=optiond,
            answer=answer,
            quiz_id=quiz_id
        )

        db.session.add(new_question)
        db.session.commit()


        return redirect('/admin')
    return redirect('/admin')

@admin.route('/update_question', methods=['POST'])
def update_question():
    if request.method == 'POST':
        
        question_id = request.form["question_id"]

        questions = Questions.query.get_or_404(question_id)

        question = request.form["question"]
        optiona = request.form["optiona"]
        optionb = request.form["optionb"]
        optionc = request.form["optionc"]
        optiond = request.form["optiond"]
        answer = request.form["answer"]
        quiz_id = int(request.form["quiz_id"])

        questions.question = question
        questions.optiona = optiona
        questions.optionb = optionb
        questions.optionc = optionc
        questions.optiond = optiond

        if(answer == 'optiona'):
            questions.answer = optiona
        elif(answer == 'optionb'):
            questions.answer = optionb
        elif(answer == 'optionc'):
            questions.answer = optionc
        else:
            questions.answer = questions.optiond
        

        questions.quiz_id = quiz_id

        db.session.commit()

        return redirect('/admin')
    return redirect('/admin')

@admin.route('/delete_question/<int:id>')
def delete_question(id):
    question = Questions.query.get_or_404(id)
    db.session.delete(question)
    db.session.commit()
    return redirect('/admin')