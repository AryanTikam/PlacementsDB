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

        session.clear()
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

    return render_template('companies_home.html', 
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
    students_data = list(mongo.db.students.aggregate([
        {
            '$lookup': {
                'from': 'companies',
                'localField': 'student_id',
                'foreignField': 'students_placed',
                'as': 'placed_by'
            }
        },
        {
            '$project': {
                'student_id': 1,
                'name': 1,
                'email': 1,
                'phone': 1,
                'address': 1,
                'skills': 1,
                'projects': 1,
                'courses': 1,
                'certificates': 1,
                'publications': 1,
                'cgpa': 1,
                'placed_by': {
                    '$map': {
                        'input': '$placed_by',
                        'as': 'company',
                        'in': '$$company.name'
                    }
                }
            }
        }
    ]))
    companies_data = list(mongo.db.companies.find())

    total_students = len(students_data)
    total_publications = sum(len(student.get('publications', [])) for student in students_data)
    # Collect all student IDs in the students_placed arrays across all companies
    placed_student_ids = set()
    for company in companies_data:
        placed_student_ids.update(company.get('students_placed', []))
    # Count students who appear in the placed_student_ids set
    placed_students = len([s for s in students_data if s.get('student_id') in placed_student_ids])
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
        companies=companies_data,
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

@app.route('/students/<student_id>')
@login_required(['tpo', 'companies'])
def student_profile(student_id):
    student = mongo.db.students.find_one({'student_id': student_id})
    if not student:
        return "Student not found", 404

    # Find companies that have placed this student
    placed_by = list(mongo.db.companies.find({'students_placed': student_id}))

    # Find projects the student has worked on
    projects = list(mongo.db.projects.find({'student_ids': student_id}))
    for project in projects:
        project['company_name'] = mongo.db.companies.find_one({'company_id': project['company_id']})['name']

    # Find publications the student has authored
    publications = list(mongo.db.publications.find({'authors': student_id}))

    return render_template('student_profile.html',
                           student=student,
                           placed_by=placed_by,
                           projects=projects,
                           publications=publications,
                           user_type=session.get('user_type'))

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
    active_companies = len([company for company in companies if company.get('students_placed')])

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
        'projects': ['student_ids', 'skills_required'],
        'companies': ['projects', 'interviews', 'students_placed'],
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

def is_student_placed(student_id):
    """Check if a student is already placed by any company"""
    placed_companies = mongo.db.companies.find({'students_placed': student_id})
    return mongo.db.companies.count_documents({'students_placed': student_id}) > 0

def update_project_references(project_data):
    """Update project references in students and companies collections."""
    project_id = project_data.get('project_id')
    company_id = project_data.get('company_id')
    student_ids = project_data.get('student_ids', [])

    # Update company projects
    if company_id:
        mongo.db.companies.update_one(
            {'company_id': company_id},
            {'$addToSet': {'projects': project_id}}
        )

    # Update student projects
    for student_id in student_ids:
        mongo.db.students.update_one(
            {'student_id': student_id},
            {'$addToSet': {'projects': project_id}}
        )

def update_entity_project_references(entity_type, entity_data):
    """Update project references in the projects collection based on changes in students or companies."""
    if entity_type == 'students':
        student_id = entity_data.get('student_id')
        project_ids = entity_data.get('projects', [])
        
        # Update each project with the student_id
        for project_id in project_ids:
            mongo.db.projects.update_one(
                {'project_id': project_id},
                {'$addToSet': {'student_ids': student_id}}
            )

    elif entity_type == 'companies':
        company_id = entity_data.get('company_id')
        project_ids = entity_data.get('projects', [])

        # Update each project with the company_id
        for project_id in project_ids:
            mongo.db.projects.update_one(
                {'project_id': project_id},
                {'$set': {'company_id': company_id}}
            )

def get_validation_rules():
    """Define validation rules for each entity type based on MongoDB schema"""
    return {
        'students': {
            'required': ['student_id', 'name', 'email', 'phone', 'address', 'cgpa'],
            'types': {
                'cgpa': float,
                'phone': str,
                'address': str,
                'email': str
            }
        },
        'companies': {
            'required': ['company_id', 'name', 'location', 'industry', 'contact_email', 'average_ctc'],
            'types': {
                'average_ctc': float,
                'contact_email': str
            }
        },
        'projects': {
            'required': ['project_id', 'title', 'description', 'start_date', 'company_id', 'student_ids', 'status'],
            'types': {
                'start_date': 'date',
                'student_ids': list
            }
        },
        'skills': {
            'required': ['skill_id', 'name', 'category'],
            'types': {}
        },
        'courses': {
            'required': ['course_id', 'name', 'credits', 'duration_weeks'],
            'types': {
                'credits': int,
                'duration_weeks': int
            }
        },
        'certificates': {
            'required': ['certificate_id', 'name', 'issuing_authority', 'valid_till'],
            'types': {
                'valid_till': 'date'
            }
        },
        'publications': {
            'required': ['publication_id', 'title', 'authors', 'journal', 'publication_date', 'doi'],
            'types': {
                'publication_date': 'date',
                'authors': list
            }
        },
        'interviews': {
            'required': ['interview_id', 'company_id', 'date', 'time', 'location', 'interviewer', 'student_ids'],
            'types': {
                'date': 'date',
                'student_ids': list
            }
        }
    }

def validate_entity_data(entity_type, data):
    """
    Validate entity data against defined rules
    Returns (is_valid, error_message)
    """
    rules = get_validation_rules().get(entity_type)
    if not rules:
        return False, f"Unknown entity type: {entity_type}"

    # Check required fields
    for field in rules['required']:
        if field not in data or not data[field] or data[field].strip() == "":
            return False, f"Required field '{field}' is missing or empty"

    # Validate types
    for field, expected_type in rules['types'].items():
        if field in data and data[field]:
            try:
                if expected_type == 'date':
                    # Date validation is handled by convert_string_to_date
                    if not convert_string_to_date(data[field]):
                        return False, f"Invalid date format for field '{field}'"
                elif expected_type == list:
                    # Convert string to list if needed
                    if isinstance(data[field], str):
                        data[field] = convert_string_to_array(data[field])
                    if not isinstance(data[field], list):
                        return False, f"Field '{field}' must be a list"
                else:
                    # Numeric and other type validations
                    value = data[field]
                    if expected_type == float:
                        float_val = float(value)
                        if field == 'cgpa' and (float_val < 6 or float_val > 10):
                            return False, "CGPA must be between 6 and 10"
                        if field == 'average_ctc' and float_val < 0:
                            return False, "Average CTC cannot be negative"
                    elif expected_type == int:
                        int_val = int(value)
                        if int_val < 0:
                            return False, f"Field '{field}' cannot be negative"
            except (ValueError, TypeError):
                return False, f"Invalid type for field '{field}'. Expected {expected_type.__name__}"

    return True, None

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
        new_entity_data = request.form.to_dict()

        # Validate the data
        is_valid, error_message = validate_entity_data(entity_type, new_entity_data)
        if not is_valid:
            return jsonify({'error': error_message}), 400

        try:
            # Process data before inserting
            processed_data = process_entity_data(entity_type, new_entity_data)
            
            # Additional business logic checks
            if entity_type == 'companies':
                placed_students = convert_string_to_array(processed_data.get('students_placed', []))
                for student_id in placed_students:
                    if is_student_placed(student_id):
                        return jsonify({
                            'error': f'Student {student_id} is already placed by another company'
                        }), 400

            # Insert the processed entity into the database
            result = collection.insert_one(processed_data)
            
            # Update related collections if needed
            if entity_type == 'projects':
                update_project_references(processed_data)
            elif entity_type in ['students', 'companies']:
                update_entity_project_references(entity_type, processed_data)

            return jsonify({
                'success': True, 
                'message': f'{entity_type.title()} added successfully', 
                'id': str(result.inserted_id)
            }), 201

        except Exception as e:
            return jsonify({'error': str(e)}), 500

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
        
        # Validate the data
        is_valid, error_message = validate_entity_data(entity_type, update_data)
        if not is_valid:
            return jsonify({'error': error_message}), 400

        try:
            # Process data before updating
            processed_data = process_entity_data(entity_type, update_data)
            
            # Additional business logic checks
            if entity_type == 'companies':
                new_placed_students = convert_string_to_array(processed_data.get('students_placed', []))
                current_company = collection.find_one({id_field: entity_id})
                current_placed_students = current_company.get('students_placed', []) if current_company else []
                
                # Check only newly added students
                new_additions = [s for s in new_placed_students if s not in current_placed_students]
                
                for student_id in new_additions:
                    if is_student_placed(student_id):
                        return jsonify({
                            'error': f'Student {student_id} is already placed by another company'
                        }), 400

            # Update the entity in the database
            result = collection.update_one(
                {id_field: entity_id}, 
                {'$set': processed_data}
            )

            if result.matched_count == 0:
                return jsonify({'error': 'Entity not found'}), 404
            
            # Update related collections if needed
            if entity_type == 'projects':
                update_project_references(processed_data)
            elif entity_type in ['students', 'companies']:
                update_entity_project_references(entity_type, processed_data)

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
            entity_data[key] = value.strftime('%Y-%m-%d')

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
            mongo.db.companies.update_many(
                {'students_placed': entity_id},
                {'$pull': {'students_placed': entity_id}}
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

# Add this function to app.py
def categorize_company(ctc):
    """Categorize company based on CTC"""
    if ctc > 2000000:  # > 20 LPA
        return 'Elite'
    elif ctc > 1200000:  # > 12 LPA
        return 'Super Dream'
    elif ctc > 800000:  # > 8 LPA
        return 'Dream'
    else:
        return 'Normal'

@app.route('/placement_analytics')
@login_required(['tpo'])
def placement_analytics():
    # Get all companies and their placement data
    companies = list(mongo.db.companies.find())
    
    # Calculate company categories based on CTC
    company_categories = {
        'Normal': {'count': 0, 'total_ctc': 0},
        'Dream': {'count': 0, 'total_ctc': 0},
        'Super Dream': {'count': 0, 'total_ctc': 0},
        'Elite': {'count': 0, 'total_ctc': 0}
    }
    
    for company in companies:
        category = categorize_company(company.get('average_ctc', 0))
        company_categories[category]['count'] += 1
        company_categories[category]['total_ctc'] += company.get('average_ctc', 0)
    
    # Calculate average CTC for each category
    average_ctc_by_category = {
        category: (info['total_ctc'] / info['count']) if info['count'] > 0 else 0
        for category, info in company_categories.items()
    }

    # Calculate placed vs unplaced students
    total_students = mongo.db.students.count_documents({})
    
    # Get unique placed students across all companies
    placed_students = set()
    for company in companies:
        placed_students.update(company.get('students_placed', []))
    
    placed_count = len(placed_students)
    unplaced_count = total_students - placed_count
    
    placement_stats = {
        'placed': placed_count,
        'unplaced': unplaced_count,
        'total': total_students,
        'placed_percentage': round((placed_count / total_students * 100), 1) if total_students > 0 else 0
    }
    
    # Get companies count by category
    company_stats = []
    for category, count in company_categories.items():
        company_stats.append({
            'category': category,
            'count': count['count'],
            'average_ctc': average_ctc_by_category[category],
            'percentage': round((count['count'] / len(companies) * 100), 1) if companies else 0
        })
    
    return render_template(
        'placement_analytics.html',
        placement_stats=placement_stats,
        company_stats=company_stats,
        average_ctc_by_category=average_ctc_by_category,  # Pass the average CTC data
        user_type=session.get('user_type')
    )

if __name__ == '__main__':
    app.run(debug=True)
