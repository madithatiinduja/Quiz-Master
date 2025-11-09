from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Subject, Chapter, Quiz, Question, Score
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def create_admin_user():
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            email='admin@example.com',
            full_name='Admin User',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")

with app.app_context():
    db.create_all()
    create_admin_user()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        user = db.session.get(User, session['user_id'])
        if user.role != 'admin':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Clear any existing session
    if 'user_id' in session:
        session.pop('user_id', None)

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html')

        try:
            user = User.query.filter_by(email=email).first()
            
            # First check if user exists
            if not user:
                flash('No account found with this email.', 'error')
                return render_template('login.html')
            
            # Then verify password
            if not user.check_password(password):
                flash('Incorrect password.', 'error')
                return render_template('login.html')
            
            # If we get here, both email and password are correct
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))

        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        qualification = request.form['qualification']
        dob = request.form['dob']

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'error')
            return render_template('register.html')

        new_user = User(
            email=email,
            full_name=full_name,
            qualification=qualification,
            dob=datetime.strptime(dob, '%Y-%m-%d').date() if dob else None
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = db.session.get(User, session['user_id'])
    subjects = Subject.query.all()
    chapters = Chapter.query.all()
    available_quizzes = Quiz.query.join(Chapter).join(Subject).all()
    
    if user.role == 'admin':
        # Get additional data for admin dashboard
        total_users = User.query.filter_by(role='user').count()
        total_quizzes = Quiz.query.count()
        return render_template('dashboard.html', 
                             current_user=user,
                             subjects=subjects,
                             chapters=chapters,
                             available_quizzes=available_quizzes,
                             total_users=total_users,
                             total_quizzes=total_quizzes,
                             is_admin=True)
    else:
        past_scores = Score.query.filter_by(user_id=user.id).order_by(Score.timestamp.desc()).all()
        return render_template('dashboard.html', 
                             current_user=user, 
                             subjects=subjects,
                             chapters=chapters,
                             available_quizzes=available_quizzes, 
                             past_scores=past_scores,
                             is_admin=False)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/manage_users')
@admin_required
def manage_users():
    users = User.query.order_by(User.role.desc(), User.full_name).all()  # Sort by role (admin first) then name
    return render_template('manage_users.html', users=users)

@app.route('/user/edit/<int:id>', methods=['POST'])
@admin_required
def edit_user(id):
    user = db.session.get(User, id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('manage_users'))
    
    if user.role == 'admin' and user.id != session['user_id']:
        flash('You cannot edit another admin user.', 'error')
        return redirect(url_for('manage_users'))
    
    # Check if email is being changed and if it's already in use
    new_email = request.form['email']
    if new_email != user.email:
        existing_user = User.query.filter_by(email=new_email).first()
        if existing_user:
            flash('Email already in use by another user.', 'error')
            return redirect(url_for('manage_users'))
    
    user.full_name = request.form['full_name']
    user.email = new_email
    if user.role != 'admin':  # Only allow role change for non-admin users
        user.role = request.form['role']
    user.qualification = request.form['qualification']
    dob = request.form['dob']
    try:
        user.dob = datetime.strptime(dob, '%Y-%m-%d').date() if dob else None
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('manage_users'))
    
    try:
        db.session.commit()
        flash('User updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating user. Please try again.', 'error')
    
    return redirect(url_for('manage_users'))

@app.route('/user/delete/<int:id>', methods=['POST'])
@admin_required
def delete_user(id):
    user = db.session.get(User, id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('manage_users'))
    
    if user.role == 'admin':
        flash('Admin users cannot be deleted.', 'error')
        return redirect(url_for('manage_users'))
    
    try:
        # Delete associated scores first
        Score.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        flash('User and associated data deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting user. Please try again.', 'error')
    
    return redirect(url_for('manage_users'))

@app.route('/manage_subjects')
@admin_required
def manage_subjects():
    subjects = Subject.query.all()
    return render_template('manage_subjects.html', subjects=subjects)

@app.route('/manage_quizzes')
@app.route('/quizzes/<int:chapter_id>')
@admin_required
def manage_quizzes(chapter_id=None):
    # Get all chapters for the dropdown
    chapters = Chapter.query.join(Subject).all()
    
    if chapter_id:
        chapter = Chapter.query.get_or_404(chapter_id)
        quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()
        return render_template('manage_quizzes.html', chapter=chapter, quizzes=quizzes, chapters=chapters)
    else:
        # Show all quizzes when no chapter_id is provided
        quizzes = Quiz.query.join(Chapter).join(Subject).all()
        return render_template('manage_quizzes.html', quizzes=quizzes, show_all=True, chapters=chapters)

@app.route('/view_reports')
@admin_required
def view_reports():
    # Get filter parameters
    subject_id = request.args.get('subject_id', type=int)
    user_id = request.args.get('user_id', type=int)

    # Base query for scores with all necessary joins
    query = Score.query.join(Quiz).join(Chapter).join(Subject).join(User)

    # Apply filters if provided
    if subject_id:
        query = query.filter(Subject.id == subject_id)
    if user_id:
        query = query.filter(Score.user_id == user_id)

    # Get all scores with filters applied
    scores = query.order_by(Score.timestamp.desc()).all()

    # Calculate statistics
    stats = {
        'total_attempts': len(scores),
        'avg_score': sum(score.total_score for score in scores) / len(scores) if scores else 0,
        'highest_score': max((score.total_score for score in scores), default=0),
        'lowest_score': min((score.total_score for score in scores), default=0)
    }

    # Get all subjects and users for filters
    subjects = Subject.query.order_by(Subject.name).all()
    users = User.query.filter_by(role='user').order_by(User.full_name).all()

    return render_template('view_reports.html', 
                         scores=scores,
                         stats=stats,
                         subjects=subjects,
                         users=users)

@app.route('/quiz/<int:quiz_id>')
@login_required
def quiz_view(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    return render_template('quiz_view.html', quiz=quiz, questions=questions)

@app.route('/quiz/submit/<int:quiz_id>', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    score = 0
    total_questions = len(questions)
    user_answers = {}
    
    for question in questions:
        user_answer = request.form.get(f'question_{question.id}')
        if user_answer:
            user_answers[str(question.id)] = user_answer
            if int(user_answer) == question.correct_option:
                score += 1
    
    percentage_score = (score / total_questions) * 100 if total_questions > 0 else 0
    
    new_score = Score(
        user_id=session['user_id'],
        quiz_id=quiz_id,
        timestamp=datetime.utcnow(),
        total_score=percentage_score
    )
    new_score.set_answers(user_answers)
    db.session.add(new_score)
    db.session.commit()
    
    return redirect(url_for('quiz_result', quiz_id=quiz_id, score_id=new_score.id))

@app.route('/quiz/<int:quiz_id>/result/<int:score_id>')
@login_required
def quiz_result(quiz_id, score_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    score = Score.query.get_or_404(score_id)
    user = db.session.get(User, session['user_id'])
    
    # Allow access if user is admin or if it's their own score
    if user.role != 'admin' and score.user_id != session['user_id']:
        flash('You do not have permission to view this result.', 'error')
        return redirect(url_for('dashboard'))
    
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    user_answers = score.get_answers()
    result_data = []
    
    for question in questions:
        user_answer = user_answers.get(str(question.id))
        if user_answer:
            is_correct = int(user_answer) == question.correct_option
            selected_option = getattr(question, f'option{user_answer}')
            result_data.append({
                'question': question,
                'selected_answer': selected_option,
                'is_correct': is_correct,
                'correct_answer': getattr(question, f'option{question.correct_option}')
            })
        else:
            result_data.append({
                'question': question,
                'selected_answer': 'Not answered',
                'is_correct': False,
                'correct_answer': getattr(question, f'option{question.correct_option}')
            })
    
    return render_template('results.html', quiz=quiz, score=score, result_data=result_data)


@app.route('/subject/add', methods=['POST'])
@admin_required
def add_subject():
    name = request.form['name']
    description = request.form['description']
    new_subject = Subject(name=name, description=description)
    db.session.add(new_subject)
    db.session.commit()
    flash('Subject added successfully!', 'success')
    return redirect(url_for('manage_subjects'))

@app.route('/subject/edit/<int:id>', methods=['POST'])
@admin_required
def edit_subject(id):
    subject = Subject.query.get_or_404(id)
    subject.name = request.form['name']
    subject.description = request.form['description']
    db.session.commit()
    flash('Subject updated successfully!', 'success')
    return redirect(url_for('manage_subjects'))

@app.route('/subject/delete/<int:id>', methods=['POST'])
@admin_required
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    # First delete all chapters associated with this subject
    Chapter.query.filter_by(subject_id=id).delete()
    # Then delete the subject
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('manage_subjects'))

@app.route('/manage_chapters')
@app.route('/chapters/<int:subject_id>')
@admin_required
def manage_chapters(subject_id=None):
    # Get all subjects for the dropdown
    subjects = Subject.query.all()
    
    if subject_id:
        subject = Subject.query.get_or_404(subject_id)
        chapters = Chapter.query.filter_by(subject_id=subject_id).all()
        return render_template('manage_chapters.html', subject=subject, chapters=chapters, subjects=subjects)
    else:
        # Show all chapters when no subject_id is provided
        chapters = Chapter.query.join(Subject).all()
        return render_template('manage_chapters.html', chapters=chapters, show_all=True, subjects=subjects)


@app.route('/chapter/add', methods=['POST'])
@admin_required
def add_chapter():
    try:
        name = request.form['name']
        description = request.form['description']
        subject_id = request.form['subject_id']
        
        if not subject_id:
            flash('Please select a subject', 'error')
            return redirect(url_for('manage_chapters'))
            
        subject_id = int(subject_id)
        new_chapter = Chapter(name=name, description=description, subject_id=subject_id)
        db.session.add(new_chapter)
        db.session.commit()
        flash('Chapter added successfully!', 'success')
        return redirect(url_for('manage_chapters', subject_id=subject_id))
    except ValueError:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('manage_chapters'))
    except Exception as e:
        flash('Error adding chapter', 'error')
        return redirect(url_for('manage_chapters'))

@app.route('/chapter/edit/<int:id>', methods=['POST'])
@admin_required
def edit_chapter(id):
    chapter = Chapter.query.get_or_404(id)
    chapter.name = request.form['name']
    chapter.description = request.form['description']
    db.session.commit()
    flash('Chapter updated successfully!', 'success')
    return redirect(url_for('manage_chapters', subject_id=chapter.subject_id))

@app.route('/chapter/delete/<int:id>', methods=['POST'])
@admin_required
def delete_chapter(id):
    try:
        chapter = Chapter.query.get_or_404(id)
        subject_id = chapter.subject_id
        
        # First delete all quizzes associated with this chapter
        Quiz.query.filter_by(chapter_id=id).delete()
        
        # Then delete the chapter
        db.session.delete(chapter)
        db.session.commit()
        flash('Chapter deleted successfully!', 'success')
        return redirect(url_for('manage_chapters', subject_id=subject_id))
    except Exception as e:
        db.session.rollback()
        flash('Error deleting chapter. Please try again.', 'error')
        return redirect(url_for('manage_chapters'))


@app.route('/quiz/add', methods=['POST'])
@admin_required
def add_quiz():
    try:
        chapter_id = request.form.get('chapter_id')
        if not chapter_id:
            flash('Please select a chapter', 'error')
            return redirect(url_for('manage_quizzes'))
            
        chapter_id = int(chapter_id)
        title = request.form['title']
        date_of_quiz = datetime.strptime(request.form['date_of_quiz'], '%Y-%m-%d').date()
        time_duration = int(request.form['time_duration'])
        remarks = request.form['remarks']
        
        new_quiz = Quiz(
            title=title,
            chapter_id=chapter_id,
            date_of_quiz=date_of_quiz,
            time_duration=time_duration,
            remarks=remarks
        )
        db.session.add(new_quiz)
        db.session.commit()
        flash('Quiz added successfully!', 'success')
        return redirect(url_for('manage_quizzes', chapter_id=chapter_id))
    except ValueError:
        flash('Invalid data provided. Please check your inputs.', 'error')
        return redirect(url_for('manage_quizzes'))
    except Exception as e:
        flash('Error adding quiz. Please try again.', 'error')
        return redirect(url_for('manage_quizzes'))

@app.route('/quiz/edit/<int:id>', methods=['POST'])
@admin_required
def edit_quiz(id):
    quiz = Quiz.query.get_or_404(id)
    quiz.title = request.form['title']
    quiz.date_of_quiz = datetime.strptime(request.form['date_of_quiz'], '%Y-%m-%d').date()
    quiz.time_duration = int(request.form['time_duration'])
    quiz.remarks = request.form['remarks']
    db.session.commit()
    flash('Quiz updated successfully!', 'success')
    return redirect(url_for('manage_quizzes', chapter_id=quiz.chapter_id))

@app.route('/quiz/delete/<int:id>', methods=['POST'])
@admin_required
def delete_quiz(id):
    try:
        quiz = Quiz.query.get_or_404(id)
        chapter_id = quiz.chapter_id
        
        # First delete all scores associated with this quiz
        Score.query.filter_by(quiz_id=id).delete()
        
        # Then delete all questions associated with this quiz
        Question.query.filter_by(quiz_id=id).delete()
        
        # Finally delete the quiz
        db.session.delete(quiz)
        db.session.commit()
        
        flash('Quiz deleted successfully!', 'success')
        return redirect(url_for('manage_quizzes', chapter_id=chapter_id))
    except Exception as e:
        db.session.rollback()
        flash('Error deleting quiz. Please try again.', 'error')
        return redirect(url_for('manage_quizzes', chapter_id=chapter_id))

@app.route('/questions/<int:quiz_id>')
@admin_required
def manage_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    return render_template('manage_questions.html', quiz=quiz, questions=questions)

@app.route('/question/add/<int:quiz_id>', methods=['POST'])
@admin_required
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    question_statement = request.form['question_statement']
    option1 = request.form['option1']
    option2 = request.form['option2']
    option3 = request.form['option3']
    option4 = request.form['option4']
    correct_option = int(request.form['correct_option'])
    
    new_question = Question(
        quiz_id=quiz_id,
        question_statement=question_statement,
        option1=option1,
        option2=option2,
        option3=option3,
        option4=option4,
        correct_option=correct_option
    )
    db.session.add(new_question)
    db.session.commit()
    flash('Question added successfully!', 'success')
    return redirect(url_for('manage_questions', quiz_id=quiz_id))

@app.route('/question/edit/<int:id>', methods=['POST'])
@admin_required
def edit_question(id):
    question = Question.query.get_or_404(id)
    question.question_statement = request.form['question_statement']
    question.option1 = request.form['option1']
    question.option2 = request.form['option2']
    question.option3 = request.form['option3']
    question.option4 = request.form['option4']
    question.correct_option = int(request.form['correct_option'])
    db.session.commit()
    flash('Question updated successfully!', 'success')
    return redirect(url_for('manage_questions', quiz_id=question.quiz_id))

@app.route('/question/delete/<int:id>', methods=['POST'])
@admin_required
def delete_question(id):
    question = Question.query.get_or_404(id)
    quiz_id = question.quiz_id
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully!', 'success')
    return redirect(url_for('manage_questions', quiz_id=quiz_id))

@app.route('/start_quiz/<int:quiz_id>')
@login_required
def start_quiz(quiz_id):
    # Implement quiz starting logic here
    return f"Start Quiz {quiz_id}"

if __name__ == '__main__':
    app.run(debug=True)

