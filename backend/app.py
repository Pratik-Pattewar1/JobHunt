import os  # 1. ADD THIS IMPORT
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
load_dotenv()

from chat import get_response

from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

# 2. UPDATE THIS LINE to point to your frontend folder
app = Flask(__name__,
            template_folder="../frontend/templates",
            static_folder="../frontend/static")

app.secret_key = 'xyzsdfg'
# ... leave everything else exactly as it was ...
  
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


@app.route('/login', methods =['GET', 'POST'])
def login():
    if 'loggedin' in session:
        return redirect(url_for('home'))
    else:
        mesage = ''
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
                return redirect(url_for('home'))
            else:
                mesage = 'Incorrect email or password'

            if user:
                session['loggedin'] = True
                session['userid'] = user['userid']
                session['name'] = user['name']
                session['email'] = user['email']
                session['role'] = user['role']     # ⭐ NEW LINE

                return redirect(url_for('home'))

            else:
                mesage = 'Please enter correct email / password !'

        return render_template('login.html', mesage = mesage)

  
@app.route('/logout')
def logout():
    if 'loggedin' in session:
        session.pop('loggedin', None)
        session.pop('userid', None)
        session.pop('email', None)
        # return redirect(url_for('login'))
    return redirect(url_for('home'))

  
@app.route('/register', methods =['GET', 'POST'])
def register():
    if 'loggedin' in session:
        return redirect(url_for('home'))
    else:
        mesage = ''
        if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form :
            userName = request.form['name']
            password = request.form['password']
            email = request.form['email']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM user WHERE email = % s', (email, ))
            account = cursor.fetchone()
            if account:
                mesage = 'Account already exists !'
            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                mesage = 'Invalid email address !'
            elif not userName or not password or not email:
                mesage = 'Please fill out the form !'
            else:
                hashed_password = generate_password_hash(password)
                cursor.execute(
                    'INSERT INTO user (name, email, password, role) VALUES (%s, %s, %s, %s)',
                    (userName, email, hashed_password, 'user')
                )

                mysql.connection.commit()

                mesage = 'You have successfully registered !'
                return redirect(url_for('login'))
        elif request.method == 'POST':
            mesage = 'Please fill out the form !'
        return render_template('register.html', mesage = mesage)



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

    # When user submits form
    if request.method == 'POST':
        name = request.form['name']
        qualification = request.form['qualification']
        skills = request.form['skills']

        cursor.execute("""
            UPDATE user 
            SET name=%s, qualification=%s, skills=%s
            WHERE email=%s
        """, (name, qualification, skills, email))

        mysql.connection.commit()

        session['name'] = name   # update navbar too

        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    # Show existing data
    cursor.execute("SELECT * FROM user WHERE email=%s", (email,))
    user_profile = cursor.fetchone()

    return render_template("edit-profile.html", user=user_profile)


@app.route('/jobs')
def all_jobs():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM job')
        jobs = cursor.fetchall()
        return render_template('jobs.html', jobs=jobs)
    return redirect(url_for('login'))
    

@app.route('/apply-job', methods=['GET', 'POST'])
@app.route('/apply-job', methods=['GET', 'POST'])
def apply_job():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        email = session['email']
        job_title = request.form['jobTitle']
        job_role = request.form['jobRole']
        skills = request.form['skills']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check if already applied
        cursor.execute("""
            SELECT * FROM applied_job 
            WHERE email=%s AND job_title=%s
        """, (email, job_title))

        existing = cursor.fetchone()

        if existing:
            flash("You have already applied for this job.", "warning")
            return redirect(url_for('applied_jobs'))

        # Insert new application
        cursor.execute("""
            INSERT INTO applied_job (email, job_title, job_role, skills, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (email, job_title, job_role, skills, "Pending"))

        mysql.connection.commit()

        flash("Application submitted successfully!", "success")
        return redirect(url_for('applied_jobs'))

    return render_template('apply-job.html')



# Job posted by admin only
@app.route('/job-post', methods=['GET', 'POST'])
def job_post():

    # Check if logged in
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Allow only admin
    if session.get('role') != 'admin':
        flash('Access denied. Admins only!', 'danger')
        return redirect(url_for('home'))

    # ---- ADMIN ONLY BELOW ----
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


@app.route('/admin')
def admin_dashboard():

    # Must be logged in
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Must be admin
    if session.get('role') != 'admin':
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('home'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get all jobs
    cursor.execute("SELECT * FROM job")
    jobs = cursor.fetchall()

    # Get all applicants
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


@app.route('/admin/applicants')
def admin_applicants():
    if 'loggedin' in session and session['email'] == 'pratikpattewar1@gmail.com':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT applied_job.id, applied_job.email, applied_job.job_title,
                   applied_job.job_role, applied_job.skills, applied_job.status,
                   user.name
            FROM applied_job
            JOIN user ON applied_job.email = user.email
        """)
        applicants = cursor.fetchall()
        return render_template('admin-applicants.html', applicants=applicants)
    else:
        return redirect(url_for('login'))


@app.route('/admin/update_status/<int:app_id>/<string:new_status>')
def update_status(app_id, new_status):
    if 'loggedin' in session and session['email'] == 'pratikpattewar1@gmail.com':
        cursor = mysql.connection.cursor()
        cursor.execute(
            "UPDATE applied_job SET status=%s WHERE id=%s",
            (new_status, app_id)
        )
        mysql.connection.commit()
        return redirect('/admin/applicants')
    else:
        return redirect(url_for('login'))

# Chatbot response data fetching
@app.post("/predict")
def predict():
    text = request.get_json().get("message")
    response = get_response(text)
    message = {"answer": response}
    return jsonify(message)

# ending of chatbot response data fetching

    
if __name__ == "__main__":
    app.run(debug=True)