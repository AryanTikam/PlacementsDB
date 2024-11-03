from flask import Flask, render_template, redirect, url_for, request, session, jsonify, flash
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
        data = request.get_json()
        id_token = data.get('idToken')
        user_type = data.get('userType')

        if not id_token or not user_type:
            return jsonify({'error': 'Missing idToken or userType'}), 400

        decoded_token = auth.verify_id_token(id_token)
        user_id = decoded_token['uid']
        email = decoded_token['email']

        if user_type == 'students' and not email.endswith('@spit.ac.in'):
            return jsonify({'error': 'Please use your college email address'}), 403

        session['user_id'] = user_id
        session['user_type'] = user_type
        session['email'] = email

        return jsonify({'success': True, 'redirect': url_for(f'{user_type}_home')})

    except auth.InvalidIdTokenError:
        return jsonify({'error': 'Invalid ID token'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/students_home')
@login_required(['students'])
def students_home():
    # Get upcoming interviews - next 3 scheduled interviews
    upcoming_interviews = list(mongo.db.interviews.aggregate([
        {
            '$match': {
                'date': {'$gte': datetime.now()}  # Only future interviews
            }
        },
        {
            '$lookup': {
                'from': 'companies',
                'localField': 'company_id',
                'foreignField': 'company_id',
                'as': 'company'
            }
        },
        {
            '$unwind': '$company'
        },
        {
            '$project': {
                'date': 1,
                'time': 1,
                'position': 1,
                'company_name': '$company.name',
                'location': '$company.location'
            }
        },
        {
            '$sort': {'date': 1}
        },
        {
            '$limit': 3
        }
    ]))

    return render_template('students_home.html', 
                            interviews=upcoming_interviews)

@app.route('/companies_home')
@login_required(['companies'])
def companies_home():
    # Get recent publications - latest 3 publications
    recent_publications = list(mongo.db.publications.aggregate([
        {
            '$lookup': {
                'from': 'students',
                'localField': 'authors',
                'foreignField': 'student_id',
                'as': 'student_authors'
            }
        },
        {
            '$project': {
                'title': 1,
                'publication_date': 1,
                'journal': 1,
                'authors': '$student_authors.name'
            }
        },
        {
            '$sort': {'publication_date': -1}
        },
        {
            '$limit': 3
        }
    ]))

    return render_template('students_home.html', 
                            publications=recent_publications)

@app.route('/tpo_home')
@login_required(['tpo'])
def tpo_home():
    # Get upcoming interviews - next 3 scheduled interviews
    upcoming_interviews = list(mongo.db.interviews.aggregate([
        {
            '$match': {
                'date': {'$gte': datetime.now()}  # Only future interviews
            }
        },
        {
            '$lookup': {
                'from': 'companies',
                'localField': 'company_id',
                'foreignField': 'company_id',
                'as': 'company'
            }
        },
        {
            '$unwind': '$company'
        },
        {
            '$project': {
                'date': 1,
                'time': 1,
                'position': 1,
                'company_name': '$company.name',
                'location': '$company.location'
            }
        },
        {
            '$sort': {'date': 1}
        },
        {
            '$limit': 3
        }
    ]))

    # Get recent publications - latest 3 publications
    recent_publications = list(mongo.db.publications.aggregate([
        {
            '$lookup': {
                'from': 'students',
                'localField': 'authors',
                'foreignField': 'student_id',
                'as': 'student_authors'
            }
        },
        {
            '$project': {
                'title': 1,
                'publication_date': 1,
                'journal': 1,
                'authors': '$student_authors.name'
            }
        },
        {
            '$sort': {'publication_date': -1}
        },
        {
            '$limit': 3
        }
    ]))

    return render_template('tpo_home.html',
                            interviews=upcoming_interviews,
                            publications=recent_publications)

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

@app.route('/help')
def help():
    return render_template('help.html', user_type=session.get('user_type'))

# MongoDB collection routes with CRUD
def fetch_collection_data(entity_type):
    entity_map = {
        'students': mongo.db.students,
        'companies': mongo.db.companies,
        'projects': mongo.db.projects,
        'skills': mongo.db.skills,
        'courses': mongo.db.courses,
        'certificates': mongo.db.certificates,
        'publications': mongo.db.publications,
        'interviews': mongo.db.interviews
    }
    return entity_map.get(entity_type)

@app.route('/<entity_type>')
@login_required(['tpo', 'students', 'companies'])
def show_entities(entity_type):
    collection = fetch_collection_data(entity_type)
    if not collection:
        return jsonify({'error': 'Invalid entity type'}), 400

    data = list(collection.find())
    return render_template(f'{entity_type}.html', data=data, user_type=session.get('user_type'))

# Add these helper functions at the top of app.py, after the imports
def convert_string_to_array(value):
    """Convert comma-separated string to array if needed"""
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    return value

def convert_string_to_number(value, convert_to='float'):
    """Convert string to number if needed"""
    if not value:
        return 0
    try:
        return float(value) if convert_to == 'float' else int(value)
    except (ValueError, TypeError):
        return 0

def convert_string_to_date(value):
    """Convert string to datetime if needed"""
    if not value:
        return None
    try:
        # Handle common date formats
        formats = [
            '%Y-%m-%d',           # 2024-01-31
            '%d/%m/%Y',           # 31/01/2024
            '%d-%m-%Y',           # 31-01-2024
            '%Y-%m-%d %H:%M:%S',  # 2024-01-31 14:30:00
            '%Y-%m-%dT%H:%M:%S',  # 2024-01-31T14:30:00
            '%Y-%m-%dT%H:%M:%S.%fZ'  # ISO format with timezone
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
                
        # If none of the formats match, try parsing ISO format
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None

def process_entity_data(entity_type, data):
    """Process entity data based on entity type"""
    processed_data = data.copy()
    
    # Fields that should be arrays
    array_fields = {
        'students': ['skills', 'projects', 'courses', 'certificates', 'publications'],
        'projects': ['students', 'skills'],
        'companies': ['projects', 'interviews'],
        'publications': ['authors'],
        'interviews': ['student_ids']
    }
    
    # Fields that should be numbers
    number_fields = {
        'students': {'cgpa': 'float'},
        'companies': {'average_ctc': 'float'},
        'projects': {'budget': 'float'},
        'courses': {'credits': 'int', 'duration_weeks': 'int'},
        'publications': {'citations': 'int'}
    }
    
    # Fields that should be dates
    date_fields = {
        'projects': ['start_date', 'end_date'],
        'certificates': ['valid_till'],
        'publications': ['publication_date'],
        'interviews': ['date']
    }
    
    # Convert array fields
    if entity_type in array_fields:
        for field in array_fields[entity_type]:
            if field in processed_data:
                processed_data[field] = convert_string_to_array(processed_data[field])
    
    # Convert number fields
    if entity_type in number_fields:
        for field, number_type in number_fields[entity_type].items():
            if field in processed_data:
                processed_data[field] = convert_string_to_number(processed_data[field], number_type)
    
    # Convert date fields
    if entity_type in date_fields:
        for field in date_fields[entity_type]:
            if field in processed_data:
                converted_date = convert_string_to_date(processed_data[field])
                if converted_date:
                    processed_data[field] = converted_date

    return processed_data

# Update the add_entity route
@app.route('/tpo/add/<entity_type>', methods=['GET', 'POST'])
@login_required(['tpo'])
def add_entity(entity_type):
    collection_map = {
        'students': mongo.db.students,
        'companies': mongo.db.companies,
        'projects': mongo.db.projects,
        'skills': mongo.db.skills,
        'courses': mongo.db.courses,
        'certificates': mongo.db.certificates,
        'publications': mongo.db.publications,
        'interviews': mongo.db.interviews
    }

    if entity_type not in collection_map:
        return jsonify({'error': 'Invalid entity type'}), 400

    collection = collection_map[entity_type]

    if request.method == 'POST':
        # Get data from the request
        new_entity_data = request.form.to_dict()
        
        try:
            # Process the data before inserting
            processed_data = process_entity_data(entity_type, new_entity_data)
            
            # Insert the processed entity into the database
            result = collection.insert_one(processed_data)

            return jsonify({
                'success': True, 
                'message': f'{entity_type.title()} added successfully', 
                'id': str(result.inserted_id)
            }), 201

        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Update the edit_entity route to handle date serialization in GET response
@app.route('/tpo/edit/<entity_type>/<entity_id>', methods=['GET', 'POST'])
@login_required(['tpo'])
def edit_entity(entity_type, entity_id):
    collection_map = {
        'students': mongo.db.students,
        'companies': mongo.db.companies,
        'projects': mongo.db.projects,
        'skills': mongo.db.skills,
        'courses': mongo.db.courses,
        'certificates': mongo.db.certificates,
        'publications': mongo.db.publications,
        'interviews': mongo.db.interviews
    }

    id_field_map = {
        'students': 'student_id',
        'companies': 'company_id',
        'projects': 'project_id',
        'skills': 'skill_id',
        'courses': 'course_id',
        'certificates': 'certificate_id',
        'publications': 'publication_id',
        'interviews': 'interview_id'
    }

    if entity_type not in collection_map:
        return jsonify({'error': 'Invalid entity type'}), 400

    collection = collection_map[entity_type]
    id_field = id_field_map[entity_type]

    if request.method == 'POST':
        update_data = request.form.to_dict()
        
        try:
            # Process the data before updating
            processed_data = process_entity_data(entity_type, update_data)
            
            # Update the entity in the database
            result = collection.update_one(
                {id_field: entity_id}, 
                {'$set': processed_data}
            )

            if result.matched_count == 0:
                return jsonify({'error': 'Entity not found'}), 404

            return jsonify({
                'success': True, 
                'message': f'{entity_type.title()} updated successfully'
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Handle GET request
    entity_data = collection.find_one({id_field: entity_id})
    if not entity_data:
        return jsonify({'error': 'Entity not found'}), 404

    # Convert ObjectId and datetime objects to strings for JSON response
    entity_data['_id'] = str(entity_data['_id'])
    for key, value in entity_data.items():
        if isinstance(value, ObjectId):
            entity_data[key] = str(value)
        elif isinstance(value, datetime):
            entity_data[key] = value.strftime('%Y-%m-%d')  # Format date as YYYY-MM-DD

    return jsonify(entity_data)

@app.route('/tpo/delete/<entity_type>/<entity_id>', methods=['DELETE'])
@login_required(['tpo'])
def delete_entity(entity_type, entity_id):
    collection_map = {
        'students': mongo.db.students,
        'companies': mongo.db.companies,
        'projects': mongo.db.projects,
        'skills': mongo.db.skills,
        'courses': mongo.db.courses,
        'certificates': mongo.db.certificates,
        'publications': mongo.db.publications,
        'interviews': mongo.db.interviews
    }

    id_field_map = {
        'students': 'student_id',
        'companies': 'company_id',
        'projects': 'project_id',
        'skills': 'skill_id',
        'courses': 'course_id',
        'certificates': 'certificate_id',
        'publications': 'publication_id',
        'interviews': 'interview_id'
    }

    if entity_type not in collection_map:
        return jsonify({'error': 'Invalid entity type'}), 400

    collection = collection_map[entity_type]
    id_field = id_field_map[entity_type]  # Get the correct ID field for the entity type

    try:
        # Handle cascading deletes based on entity type
        if entity_type == 'students':
            mongo.db.projects.update_many(
                {'student_ids': entity_id},
                {'$pull': {'student_ids': entity_id}}
            )
            mongo.db.publications.update_many(
                {'authors': entity_id},
                {'$pull': {'authors': entity_id}}
            )

        elif entity_type == 'companies':
            projects = mongo.db.projects.find({'company_id': entity_id})
            for project in projects:
                mongo.db.students.update_many(
                    {'projects': project['project_id']},
                    {'$pull': {'projects': project['project_id']}}
                )
            mongo.db.projects.delete_many({'company_id': entity_id})
            mongo.db.interviews.delete_many({'company_id': entity_id})

        elif entity_type == 'projects':
            mongo.db.students.update_many(
                {'projects': entity_id},
                {'$pull': {'projects': entity_id}}
            )
            mongo.db.companies.update_many(
                {'projects': entity_id},
                {'$pull': {'projects': entity_id}}
            )

        elif entity_type == 'interviews':
            mongo.db.companies.update_many(
                {'interviews': entity_id},
                {'$pull': {'interviews': entity_id}}
            )

        # Delete the entity using the correct ID field
        result = collection.delete_one({id_field: entity_id})

        if result.deleted_count == 0:
            return jsonify({'error': 'Entity not found'}), 404

        return jsonify({'success': True, 'message': f'{entity_type.title()} deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': 'An error occurred during deletion.'}), 500
    
# TPO Edit Page Route
@app.route('/tpo_edit')
@login_required(['tpo'])
def tpo_edit():
    collections = {entity: list(fetch_collection_data(entity).find()) for entity in ['students', 'companies', 'projects', 'skills', 'courses', 'certificates', 'publications', 'interviews']}
    return render_template('tpo_edit.html', **collections, user_type=session.get('user_type'))

if __name__ == '__main__':
    app.run(debug=True)
