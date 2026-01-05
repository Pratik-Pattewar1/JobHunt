import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

from chat import get_response

from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

app = Flask(__name__,
            template_folder="../frontend/templates",
            static_folder="../frontend/static")
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024   # 5MB max
ALLOWED_EXT = {'pdf', 'doc', 'docx'}

app.secret_key = 'xyzsdfg'

app.config['MYSQL_HOST'] = os.getenv("DB_HOST")
app.config['MYSQL_USER'] = os.getenv("DB_USER")
app.config['MYSQL_PASSWORD'] = os.getenv("DB_PASS")
app.config['MYSQL_DB'] = os.getenv("DB_NAME")

mysql = MySQL(app)


@app.route('/')
def home():
    if 'loggedin' in session:
        return render_template('user.html')
    return render_template('home.html')


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'loggedin' in session:
        return redirect(url_for('home'))

    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['userid'] = user['userid']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']

            flash("Login successful 🎉", "success")
            return redirect(url_for('home'))
        else:
            flash("Incorrect email or password ❌", "danger")

    return render_template('login.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    if 'loggedin' in session:
        session.pop('loggedin', None)
        session.pop('userid', None)
        session.pop('email', None)

        flash("You have been logged out", "info")

    return redirect(url_for('home'))


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'loggedin' in session:
        return redirect(url_for('home'))

    else:
        if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form:
            userName = request.form['name']
            password = request.form['password']
            email = request.form['email']

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
            account = cursor.fetchone()

            if account:
                flash("Account already exists!", "warning")

            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                flash("Invalid email address!", "danger")

            elif not userName or not password or not email:
                flash("Please fill out the form!", "warning")

            else:
                hashed_password = generate_password_hash(password)

                cursor.execute(
                    'INSERT INTO user (name, email, password, role) VALUES (%s, %s, %s, %s)',
                    (userName, email, hashed_password, 'user')
                )

                mysql.connection.commit()

                flash("Registration successful 🎉 Please login.", "success")
                return redirect(url_for('login'))

        return render_template('register.html')


# ---------------- PROFILE ----------------
@app.route('/profile')
def profile():
    if 'loggedin' in session:
        email = session['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        user_profile = cursor.fetchone()
        return render_template('profile.html', user_profile=user_profile)
    else:
        return redirect(url_for('login'))


@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    email = session['email']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        name = request.form['name']
        qualification = request.form['qualification']
        skills = request.form['skills']

        resume_file = request.files.get('resume')
        resume_name = None

        if resume_file and allowed_file(resume_file.filename):
            filename = secure_filename(resume_file.filename)
            resume_name = f"{session['userid']}_{filename}"
            resume_file.save(os.path.join(app.config['UPLOAD_FOLDER'], resume_name))

        if resume_name:
            cursor.execute("""
                UPDATE user
                SET name=%s, qualification=%s, skills=%s, resume=%s
                WHERE email=%s
            """, (name, qualification, skills, resume_name, email))
        else:
            cursor.execute("""
                UPDATE user
                SET name=%s, qualification=%s, skills=%s
                WHERE email=%s
            """, (name, qualification, skills, email))

        mysql.connection.commit()

        session['name'] = name
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    cursor.execute("SELECT * FROM user WHERE email=%s", (email,))
    user_profile = cursor.fetchone()

    return render_template("edit-profile.html", user=user_profile)


# ---------------- JOB LIST ----------------
@app.route('/jobs')
def all_jobs():

    if 'loggedin' not in session:
        return redirect(url_for('login'))

    email = session['email']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # get all jobs
    cursor.execute('SELECT * FROM job')
    jobs = cursor.fetchall()

    # get job titles user applied to
    cursor.execute("""
        SELECT job_title FROM applied_job 
        WHERE email=%s
    """, (email,))

    applied_rows = cursor.fetchall()

    # convert to set
    user_applied_titles = {row['job_title'] for row in applied_rows}

    cursor.close()

    return render_template(
        'jobs.html',
        jobs=jobs,
        user_applied_titles=user_applied_titles
    )




# ---------------- APPLY JOB ----------------
@app.route('/apply/<int:job_id>')
def apply_job(job_id):

    if 'loggedin' not in session:
        return redirect(url_for('login'))

    email = session['email']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1. get job details
    cursor.execute("""
        SELECT * FROM job WHERE id=%s
    """, (job_id,))
    job = cursor.fetchone()

    if not job:
        flash("Job not found", "danger")
        return redirect(url_for('all_jobs'))

    # 2. check if already applied
    cursor.execute("""
        SELECT * FROM applied_job
        WHERE email=%s AND job_title=%s
    """, (email, job['job_title']))

    existing = cursor.fetchone()

    if existing:
        flash("You already applied for this job.", "warning")
        return redirect(url_for('all_jobs'))

    # 3. insert new application
    cursor.execute("""
        INSERT INTO applied_job (email, job_title, job_role, skills, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        email,
        job['job_title'],
        job['job_role'],
        job['skills'],
        "Pending"
    ))

    mysql.connection.commit()
    cursor.close()

    flash("Application submitted successfully!", "success")
    return redirect(url_for('all_jobs'))




# ---------------- ADMIN JOB POST ----------------
@app.route('/job-post', methods=['GET', 'POST'])
def job_post():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        flash('Access denied. Admins only!', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        job_title = request.form['jobTitle']
        job_role = request.form['jobRole']
        skills = request.form['skills']
        qualifications = request.form['qualifications']
        vacancy = request.form['vacancy']
        last_date = request.form['lastDate']

        cursor = mysql.connection.cursor()
        cursor.execute(
            'INSERT INTO job (job_title, job_role, skills, qualifications, vacancy, last_date) VALUES (%s, %s, %s, %s, %s, %s)',
            (job_title, job_role, skills, qualifications, vacancy, last_date)
        )
        mysql.connection.commit()

        flash('Job successfully posted!', 'success')
        return redirect(url_for('job_post'))

    return render_template('job-post.html')


# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin')
def admin_dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('home'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM job")
    jobs = cursor.fetchall()

    cursor.execute("""
        SELECT applied_job.*, user.name 
        FROM applied_job 
        JOIN user 
        ON applied_job.email = user.email
    """)
    applicants = cursor.fetchall()

    return render_template(
        'admin.html',
        jobs=jobs,
        applicants=applicants
    )


@app.route('/approve/<int:id>')
def approve_applicant(id):
    if 'loggedin' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE applied_job SET status='Approved' WHERE id=%s", (id,))
    mysql.connection.commit()

    flash("Application Approved", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/reject/<int:id>')
def reject_applicant(id):
    if 'loggedin' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE applied_job SET status='Rejected' WHERE id=%s", (id,))
    mysql.connection.commit()

    flash("Application Rejected", "danger")
    return redirect(url_for('admin_dashboard'))


# ---------------- USER APPLIED JOBS ----------------
@app.route('/applied-jobs')
def applied_jobs():
    if 'loggedin' in session:
        email = session['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM applied_job WHERE email = %s', (email,))
        applied_jobs = cursor.fetchall()
        return render_template('applied-jobs.html', applied_jobs=applied_jobs)
    else:
        flash('Please login to view applied jobs!', 'error')
        return redirect(url_for('login'))


# ---------------- CHATBOT ----------------
@app.post("/predict")
def predict():
    text = request.get_json().get("message")
    response = get_response(text)
    message = {"answer": response}
    return jsonify(message)


if __name__ == "__main__":
    app.run(debug=True)
