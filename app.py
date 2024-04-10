# Standard library imports
import asyncio
import os
import re
import subprocess
import threading
from io import BytesIO
from flask import Response
from tempfile import mkstemp, NamedTemporaryFile

# Third-party imports
import uuid
import matplotlib
from flask import send_from_directory

from flask import Flask, jsonify, flash, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from fpdf import FPDF
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Email, Length
import matplotlib.pyplot as plt
import networkx as nx
import aiohttp

# Local application/library specific imports
from dotenv import load_dotenv
import pdf_parser
from mind_map_generator import generate_mind_map

# Set matplotlib backend
matplotlib.use('Agg')

load_dotenv()
app = Flask(__name__)
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI')
app.secret_key = os.environ.get('SECRET_KEY')
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False) 

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    correct = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('answers', lazy='dynamic'))
    question = db.relationship('Question', backref=db.backref('answers', lazy='dynamic'))

class UserAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_content = db.Column(db.Text, nullable=False)
    user_answer = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<UserAnswer {self.question_content}, {self.is_correct}>'
    
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email')])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6, message='Password should be at least 6 characters long')])

def get_current_user_id():
    return session.get('user_id')



@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if not username or not password:
            flash('All fields are required', 'danger')
            return render_template('login.html')

        if user and user.check_password(password):
            session["user_id"] = user.id  # Set user_id in session
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")  # Error message

    return render_template("login.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)  # Instantiate the form
    if request.method == 'POST' and form.validate():  # Check if it's a POST request and the form is valid
        username = form.username.data
        email = form.email.data
        password = form.password.data

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful', 'success')
        return redirect(url_for('login'))
    else:
        for field, errors in form.errors.items():  # Iterate over form errors
            for error in errors:
                flash(f"Error in the {getattr(form, field).label.text} field - {error}", 'danger')

    return render_template('register.html', form=form)  # Pass the form to the template

@app.route('/logout')
def logout():
    # Remove user_id from session
    session.pop('user_id', None)
    flash('You have been logged out.')
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/sum')
def sum():
    return render_template('summary.html')

@app.route('/audio')
def audio():
    return render_template('audio.html')

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/script')
def script():
    return render_template('script.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/essay')
def essay():
    return render_template('essay.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

def add_to_pdf(pdf, text):
    # This function can be expanded to handle different styles like headings, lists, etc.
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text)


@app.route('/generate-script', methods=['POST'])
def generate_script():
    pdf_file = request.files['pdfFile']
    if pdf_file:
        fd, temp_path = mkstemp()
        os.close(fd)
        pdf_file.save(temp_path)

        try:
            pdf_content = pdf_parser.extract_text_from_pdf(temp_path)
            os.unlink(temp_path)

            # Segment the PDF content
            segments = pdf_parser.segment_text_by_headings(pdf_content, max_tokens_per_segment=4096)

            # Create a new PDF instance
            pdf = FPDF()
            pdf.add_page()

            # Process each segment
            for segment in segments:
                script_segment = pdf_parser.generate_condensed_script(segment)
                script_segment = script_segment.encode('latin-1', 'ignore').decode('latin-1')
                add_to_pdf(pdf, script_segment)

            # Create temporary PDF file
            with NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                pdf.output(temp_pdf.name)
                temp_pdf_path = temp_pdf.name  # Store the file path

            # Send the file
            directory, filename = os.path.split(temp_pdf_path)
            response = send_from_directory(directory, filename, as_attachment=True)

            # Clean up the temporary file after a short delay
            threading.Timer(1, lambda: os.remove(temp_pdf_path) if os.path.exists(temp_pdf_path) else None).start()

            return response
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            print(f"Error: {e}")
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "No file uploaded"}), 400


@app.route('/parse-pdf', methods=['POST'])
def parse_pdf():
    pdf_file = request.files['pdfFile']
    question_type = request.form['questionType']  # Retrieve the question type from the form data
    session['question_type'] = question_type

    if pdf_file:
        fd, temp_path = mkstemp()
        os.close(fd)  # Close the file descriptor
        pdf_file.save(temp_path)

        try:
            pdf_content = pdf_parser.extract_text_from_pdf(temp_path)
            questions = pdf_parser.generate_questions(pdf_content, question_type=question_type, num_questions=1)  # Pass the question type to the function
            context = pdf_parser.clean_text(pdf_content)
            context_segmented = " ".join(pdf_parser.segment_text(context))
            os.unlink(temp_path)  # Delete the temp file
            session['questions'] = questions
            session['context'] = context_segmented
            return jsonify({"question": questions[0]})
        except Exception as e:
            os.unlink(temp_path)  # Delete the temp file in case of an exception
            return f'Error: {str(e)}'
    else:
        return 'No file uploaded'
    


@app.route('/submit-answer', methods=['POST'])
def submit_answers():
    data = request.json
    question = data['question']
    user_answer = data['answer']
    user_id = session.get('user_id', None)

    if not user_id:
        return jsonify({"evaluation": "Error: User not logged in."}), 401

    context_segmented = session.get('context', '')

    if context_segmented:
        evaluation = pdf_parser.evaluate_answer(context_segmented, question, user_answer)

        # Update logic to check if the answer is correct
        is_correct = 'this answer is correct' in evaluation.lower() or 'yes, this is correct' in evaluation.lower()
        is_incorrect = 'this answer is not correct' in evaluation.lower() or 'no, this is not correct' in evaluation.lower()

        if is_correct:
            correctness = True
        elif is_incorrect:
            correctness = False
        else:
            correctness = None  # Unclear if correct or incorrect

        # Debugging print statements
        print(f"Evaluation: {evaluation}")
        print(f"Is Correct: {correctness}")

        if correctness is not None:
            new_answer = UserAnswer(
                question_content=question,
                user_answer=user_answer,
                is_correct=correctness,
                user_id=user_id
            )
            db.session.add(new_answer)
            db.session.commit()

        return jsonify({"evaluation": evaluation, "is_correct": correctness})
    else:
        return jsonify({"evaluation": "Error: Context not found. Please try again."})
    
    
@app.route('/get-new-question', methods=['GET'])
def get_new_question():
    # Assuming you have a way to get or store the context from the PDF
    context_segmented = session.get('context', '')
    question_type = session.get('question_type', 'multiple_choice')

    if context_segmented:
        questions = pdf_parser.generate_questions(context_segmented, question_type, num_questions=1)
        if questions:
            return jsonify({"question": questions[0]})
        else:
            return jsonify({"question": "Failed to generate a new question."})
    else:
        return jsonify({"question": "No context available."})
    
@app.route('/get-progress', methods=['GET'])
def get_progress():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    user_id = session['user_id']
    user_answers = UserAnswer.query.filter_by(user_id=user_id).all()
    total_answered = len(user_answers)
    incorrect_answers = len([answer for answer in user_answers if not answer.is_correct])
    

    return jsonify({'total_answered': total_answered, 'incorrect_answers': incorrect_answers})   
@app.route('/revision', methods=['GET'])
def revision():
    user_id = session.get('user_id', None)
    if not user_id:
        flash("Please log in to access revision mode.", "warning")
        return redirect(url_for('login'))
    
    user_answers = UserAnswer.query.filter_by(user_id=user_id).all()
    total_questions = len(user_answers)
    correct_answers = len([a for a in user_answers if a.is_correct])
    incorrect_answers = total_questions - correct_answers

    return render_template('revision.html', user_answers=user_answers, 
                           total_questions=total_questions, 
                           correct_answers=correct_answers, 
                           incorrect_answers=incorrect_answers)

@app.route('/upload-essay', methods=['GET', 'POST'])
def upload_essay():
    feedback_list = None  # Initialize an empty feedback list

    if request.method == 'POST':
        essay_file = request.files.get('essayFile')
        if essay_file:
            # Validate file type and handle the upload
            if not allowed_file(essay_file.filename):
                flash('Only PDF files are allowed.', 'error')
                return render_template('essay.html')

            # Extract text from the PDF file and analyze it
            try:
                essay_text = pdf_parser.extract_text_from_pdf(essay_file)
                if essay_text:
                    feedback_list = pdf_parser.analyze_pdf_essay(essay_text)
                else:
                    flash('Failed to extract text from file.', 'error')
            except Exception as e:
                flash(f'Error processing file: {e}', 'error')

        else:
            flash('No file uploaded.', 'error')

    # Render the same template whether feedback is available or not
    return render_template('essay.html', feedback_list=feedback_list)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

app.config['WHISPER_MODEL'] = pdf_parser.initialize_model()

@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        file_stream = BytesIO()
        file.save(file_stream)
        file_stream.seek(0)

        # Use FFmpeg to extract audio and save to a temporary WAV file
        temp_audio_path = 'temp_audio.wav'
        subprocess.run([r'c:\FFmpeg\bin\ffmpeg.exe', '-i', '-', '-ar', '16000', '-ac', '1', temp_audio_path], input=file_stream.read())

        # Transcribe the audio file
        transcription = pdf_parser.transcribe_audio(app.config['WHISPER_MODEL'], temp_audio_path)

        # Optionally, delete the temporary file here
        # os.remove(temp_audio_path)

        return jsonify({'transcription': transcription}), 200

@app.route('/summary', methods=['GET', 'POST'])
def summary():
    summary_result = ""
    if request.method == 'POST':
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            summary_result = pdf_parser.summarize_pdf(file)
        elif 'text' in request.form:
            text = request.form.get('text')
            summary_result = pdf_parser.generate_summary(text)

    return render_template('summary.html', summary=summary_result)

if __name__ == '__main__':
    app.run(debug=True)
