from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from functools import wraps
import firebase_admin
from firebase_admin import credentials, auth
from collections import Counter
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# MongoDB configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/university_db"
mongo = PyMongo(app)

# Initialize Firebase Admin SDK
cred = credentials.Certificate("placementsdb-52580-firebase-adminsdk-bpn2o-13b94a68ac.json")
firebase_admin.initialize_app(cred)

# Login required decorator
def login_required(allowed_types):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_type' not in session or 'user_id' not in session:
                return redirect(url_for('login'))
            if session['user_type'] not in allowed_types:
                return redirect(url_for('unauthorized'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/verify_token', methods=['POST'])
def verify_token():
    try:
        # Get the token and user type from the request
        data = request.get_json()
        id_token = data.get('idToken')
        user_type = data.get('userType')

        if not id_token or not user_type:
            return jsonify({'error': 'Missing idToken or userType'}), 400

        # Verify the Firebase ID token
        decoded_token = auth.verify_id_token(id_token)
        user_id = decoded_token['uid']
        email = decoded_token['email']

        # Verify email domain for specific user types (optional)
        if user_type == 'students' and not email.endswith('@spit.ac.in'):
            return jsonify({'error': 'Please use your college email address'}), 403

        # Store user information in session
        session['user_id'] = user_id
        session['user_type'] = user_type
        session['email'] = email

        # Return success response with redirect URL
        return jsonify({
            'success': True,
            'redirect': url_for(f'{user_type}_home') 
        })

    except auth.InvalidIdTokenError:
        return jsonify({'error': 'Invalid ID token'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/students_home')
@login_required(['students'])
def students_home():
    students_data = list(mongo.db.students.find())
    return render_template('students_home.html', students=students_data)

@app.route('/companies_home')
@login_required(['companies'])
def companies_home():
    companies_data = list(mongo.db.companies.find())
    return render_template('companies_home.html', companies=companies_data)

@app.route('/tpo_home')
@login_required(['tpo'])
def tpo_home():
    return render_template('tpo_home.html')

@app.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html', user_type=session.get('user_type'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Routes for handling MongoDB collections
@app.route('/students')
@login_required(['tpo', 'companies'])
def students():
    students_data = list(mongo.db.students.find())
    total_students = len(students_data)
    total_publications = sum(len(student.get('publications', [])) for student in students_data)
    placed_students = len([s for s in students_data if len(s.get('projects', [])) > 0])
    total_projects = sum(len(student.get('projects', [])) for student in students_data)
    avg_projects = round(total_projects / total_students if total_students > 0 else 0, 1)
    
    all_skills = [skill for student in students_data for skill in student.get('skills', [])]
    skill_counts = Counter(all_skills)
    max_skill_count = max(skill_counts.values()) if skill_counts else 1
    top_skills = skill_counts.most_common(5)
    
    courses = list(mongo.db.courses.find())
    course_stats = [
        {
            'name': course.get('name', 'Unknown Course'),
            'student_count': mongo.db.students.count_documents({'courses': course.get('course_id')})
        }
        for course in courses
    ]
    
    unique_skills = sorted(set(all_skills))

    return render_template(
        'students.html',
        students=students_data,
        total_students=total_students,
        placed_students=placed_students,
        avg_projects=avg_projects,
        total_publications=total_publications,
        top_skills=top_skills,
        skills=unique_skills,
        courses=course_stats,
        max_skill_count=max_skill_count,
        user_type=session.get('user_type')
    )

@app.route('/companies', methods=['GET', 'POST'])
@login_required(['tpo', 'students'])
def companies():
    if request.method == 'POST':
        company_id = request.form.get('company_id')

        if mongo.db.companies.find_one({'company_id': company_id}):
            return jsonify({'error': f"Company with ID {company_id} already exists."}), 400

        company = {
            'company_id': company_id,
            'name': request.form.get('name'),
            'location': request.form.get('location'),
            'industry': request.form.get('industry'),
            'projects': [],
            'average_ctc': float(request.form.get('average_ctc', 0)),
            'created_at': datetime.utcnow()
        }

        mongo.db.companies.insert_one(company)
        return jsonify({'message': f"Company {company['name']} added successfully!"}), 201

    companies = list(mongo.db.companies.find().sort('name'))
    total_companies = len(companies)
    total_projects = sum(len(company.get('projects', [])) for company in companies)
    active_companies = len([company for company in companies if company.get('projects')])

    active_company_stats = {}
    for company in companies:
        if company.get('projects'):
            industry = company.get('industry')
            if industry:
                active_company_stats[industry] = active_company_stats.get(industry, 0) + 1

    industries = sorted(set(company.get('industry') for company in companies if company.get('industry')))

    return render_template(
        'companies.html',
        companies=companies,
        total_companies=total_companies,
        active_companies=active_companies,
        total_projects=total_projects,
        industries=industries,
        active_company_stats=active_company_stats.items(),
        user_type=session.get('user_type')
    )

@app.route('/company_profile/<company_id>')
@login_required(['tpo', 'students'])
def company_profile(company_id):
    company = mongo.db.companies.find_one({'company_id': company_id})
    if not company:
        return "Company not found", 404

    # Find scheduled interviews for the company
    interviews = list(mongo.db.interviews.find({'company_id': company_id}))

    # Pass interviews only if they exist
    return render_template('company_profile.html',
                           company=company,
                           interviews=interviews if interviews else None)


@app.route('/projects', methods=['GET', 'POST'])
@login_required(['tpo', 'companies', 'students'])
def projects():
    if request.method == 'POST':
        project = {
            'project_id': request.form.get('project_id'),
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'company_id': request.form.get('company_id'),
            'student_ids': request.form.getlist('student_ids'),
            'skills_required': request.form.getlist('skills_required'),
            'created_at': datetime.utcnow()
        }
        mongo.db.projects.insert_one(project)

        mongo.db.companies.update_one(
            {'company_id': project['company_id']},
            {'$push': {'projects': project['project_id']}}
        )

        for student_id in project['student_ids']:
            mongo.db.students.update_one(
                {'student_id': student_id},
                {'$push': {'projects': project['project_id']}}
            )
            
        return redirect(url_for('projects'))
    
    projects = list(mongo.db.projects.find())
    companies = list(mongo.db.companies.find())
    students = list(mongo.db.students.find())
    return render_template('projects.html', 
                         projects=projects,
                         companies=companies,
                         students=students)

@app.route('/help')
def help():
    return render_template('help.html', user_type=session.get('user_type'))

@app.route('/interviews', methods=['GET', 'POST'])
@login_required(['tpo', 'companies', 'students'])
def interviews():
    if request.method == 'POST':
        interview = {
            'interview_id': request.form.get('interview_id'),
            'company_id': request.form.get('company_id'),
            'date': request.form.get('date'),
            'time': request.form.get('time'),
            'student_ids': request.form.getlist('student_ids'),
            'created_at': datetime.utcnow()
        }
        mongo.db.interviews.insert_one(interview)

        mongo.db.companies.update_one(
            {'company_id': interview['company_id']},
            {'$push': {'interviews': interview['interview_id']}}
        )

        for student_id in interview['student_ids']:
            mongo.db.students.update_one(
                {'student_id': student_id},
                {'$push': {'interviews': interview['interview_id']}}
            )
        
        return redirect(url_for('interviews'))
    
    interviews = list(mongo.db.interviews.find())
    companies = list(mongo.db.companies.find())
    students = list(mongo.db.students.find())
    return render_template('interviews.html', 
                           interviews=interviews,
                           companies=companies,
                           students=students)

if __name__ == '__main__':
    app.run(debug=True)
