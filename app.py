from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class TaskType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class AllocatedPerson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(150), nullable=False)
    task_type_id = db.Column(db.Integer, db.ForeignKey('task_type.id'))
    allocated_person_id = db.Column(db.Integer, db.ForeignKey('allocated_person.id'))
    status = db.Column(db.String(50))
    due_date = db.Column(db.DateTime)
    complete_date = db.Column(db.DateTime)
    priority = db.Column(db.String(50))
    remarks = db.Column(db.Text)
    crm_id = db.Column(db.String(100))
    crm_password = db.Column(db.String(100))
    done_by_admin = db.Column(db.Boolean, default=False)
    proof_filename = db.Column(db.String(200))
    created_on = db.Column(db.DateTime, default=datetime.utcnow)

    task_type = db.relationship('TaskType', backref='tasks')
    allocated_person = db.relationship('AllocatedPerson', backref='tasks')

    @property
    def sla_days(self):
        if self.due_date and self.created_on:
            return (self.due_date - self.created_on).days
        return None

    @property
    def delay_days(self):
        if self.complete_date and self.due_date:
            return (self.complete_date - self.due_date).days
        return None

    @property
    def sla_breach(self):
        if self.delay_days and self.delay_days > 0:
            return "Yes"
        return "No"

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    tasks = Task.query.all()
    return render_template('dashboard.html', tasks=tasks)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        return 'Invalid Credentials'
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

@app.route('/masters', methods=['GET', 'POST'])
def masters():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    task_types = TaskType.query.all()
    allocated_persons = AllocatedPerson.query.all()

    if request.method == 'POST':
        if request.form.get('new_task_type'):
            db.session.add(TaskType(name=request.form['new_task_type']))
        if request.form.get('new_allocated_person'):
            db.session.add(AllocatedPerson(name=request.form['new_allocated_person']))
        db.session.commit()
        return redirect(url_for('masters'))

    return render_template('masters.html', task_types=task_types, allocated_persons=allocated_persons)

@app.route('/add', methods=['GET', 'POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    task_types = TaskType.query.all()
    allocated_persons = AllocatedPerson.query.all()

    if request.method == 'POST':
        file = request.files['proof']
        filename = None
        if file and file.filename != '':
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d') if request.form['due_date'] else None
        complete_date = datetime.strptime(request.form['complete_date'], '%Y-%m-%d') if request.form['complete_date'] else None

        new_task = Task(
            task_name=request.form['task_name'],
            task_type_id=request.form['task_type'],
            allocated_person_id=request.form['allocated_person'],
            status=request.form['status'],
            due_date=due_date,
            complete_date=complete_date,
            priority=request.form['priority'],
            remarks=request.form['remarks'],
            crm_id=request.form['crm_id'],
            crm_password=request.form['crm_password'],
            done_by_admin=('done_by_admin' in request.form),
            proof_filename=filename
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('add_task.html', task_types=task_types, allocated_persons=allocated_persons)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Create folders if not exist
if not os.path.exists('uploads'):
    os.makedirs('uploads')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
