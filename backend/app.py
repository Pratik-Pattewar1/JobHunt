import os  # 1. ADD THIS IMPORT
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash

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
  
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '2300030969'
app.config['MYSQL_DB'] = 'user_system'
  
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
            cursor.execute('SELECT * FROM user WHERE email = % s AND password = % s', (email, password, ))
            user = cursor.fetchone()
            if user:
                session['loggedin'] = True
                session['userid'] = user['userid']
                session['name'] = user['name']
                session['email'] = user['email']
                mesage = 'Logged in successfully !'

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
                cursor.execute('INSERT INTO user VALUES (NULL, % s, % s, % s)', (userName, email, password, ))
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



@app.route('/jobs')
def all_jobs():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM job')
        jobs = cursor.fetchall()
        return render_template('jobs.html', jobs=jobs)
    return redirect(url_for('login'))
    

@app.route('/apply-job', methods=['GET', 'POST'])
def apply_job():
    if 'loggedin' in session:
        if request.method == 'POST':
            email = session['email']
            job_title = request.form['jobTitle']
            job_role = request.form['jobRole']
            skills = request.form['skills']

            cursor = mysql.connection.cursor()
            cursor.execute('INSERT INTO applied_job (email, job_title, job_role, skills) VALUES (%s, %s, %s, %s)',
                           (email, job_title, job_role, skills))
            mysql.connection.commit()

            flash('Job successfully posted!', 'success')
            return redirect(url_for('apply_job'))
        else:
            return render_template('apply-job.html')
    else:
        return redirect(url_for('login'))



# Job posted by admin only
@app.route('/job-post', methods=['GET', 'POST'])
def job_post():
    print(session['email'])
    if 'loggedin' in session and session['email'] == 'pratikpattewar1@gmail.com':
        if request.method == 'POST':
            job_title = request.form['jobTitle']
            job_role = request.form['jobRole']
            skills = request.form['skills']
            qualifications = request.form['qualifications']
            vacancy = request.form['vacancy']
            last_date = request.form['lastDate']

            cursor = mysql.connection.cursor()
            cursor.execute('INSERT INTO job (job_title, job_role, skills, qualifications, vacancy, last_date) VALUES (%s, %s, %s, %s, %s, %s)',
                           (job_title, job_role, skills, qualifications, vacancy, last_date))
            mysql.connection.commit()

            flash('Job successfully posted!', 'success')
            return redirect(url_for('job_post'))
        else:
            return render_template('job-post.html')
    else:
        return redirect(url_for('login'))

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