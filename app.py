from flask import Flask, render_template, redirect, url_for, request, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

# Create Upload folder if not exist
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

class TaskType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class AllocatedPerson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(200))
    task_type_id = db.Column(db.Integer, db.ForeignKey('task_type.id'))
    allocated_person_id = db.Column(db.Integer, db.ForeignKey('allocated_person.id'))
    status = db.Column(db.String(50))
    due_date = db.Column(db.Date)
    complete_date = db.Column(db.Date)
    sla_days = db.Column(db.Integer)
    delay_days = db.Column(db.Integer)
    sla_breach = db.Column(db.String(10))
    priority = db.Column(db.String(20))
    remarks = db.Column(db.Text)
    crm_id = db.Column(db.String(100))
    crm_password = db.Column(db.String(100))
    done_by_admin = db.Column(db.String(100))
    proof_filename = db.Column(db.String(200))
    created_on = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables on first run
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    tasks = Task.query.all()
    return render_template('index.html', tasks=tasks)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(username=request.form['username'], password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    task_types = TaskType.query.all()
    allocated_persons = AllocatedPerson.query.all()
    if request.method == 'POST':
        file = request.files['proof_file']
        filename = None
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        task = Task(
            task_name=request.form['task_name'],
            task_type_id=request.form['task_type_id'],
            allocated_person_id=request.form['allocated_person_id'],
            status=request.form['status'],
            due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d'),
            complete_date=datetime.strptime(request.form['complete_date'], '%Y-%m-%d') if request.form['complete_date'] else None,
            sla_days=request.form['sla_days'],
            delay_days=request.form['delay_days'],
            sla_breach=request.form['sla_breach'],
            priority=request.form['priority'],
            remarks=request.form['remarks'],
            crm_id=request.form['crm_id'],
            crm_password=request.form['crm_password'],
            done_by_admin=request.form['done_by_admin'],
            proof_filename=filename
        )
        db.session.add(task)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_task.html', task_types=task_types, allocated_persons=allocated_persons)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
