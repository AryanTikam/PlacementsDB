from flask import Flask, redirect, render_template, url_for, request, jsonify
from collections import Counter
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)

# MongoDB configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/university_db"
mongo = PyMongo(app)

# Database Models/Schema
class DatabaseSchema:
    @staticmethod
    def init_db():
        # Create collections if they don't exist
        collections = ['students', 'companies', 'projects', 'skills', 
                      'courses', 'certificates', 'publications']
        
        for collection in collections:
            if collection not in mongo.db.list_collection_names():
                mongo.db.create_collection(collection)
        
        # Create indexes for better query performance
        mongo.db.students.create_index("student_id", unique=True)
        mongo.db.companies.create_index("company_id", unique=True)
        mongo.db.projects.create_index("project_id", unique=True)

# Routes with MongoDB integration
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/students')
def students():
    # Get all students from MongoDB
    students_data = list(mongo.db.students.find())

    # Calculate statistics
    total_students = len(students_data)
    total_publications = sum(len(student.get('publications', [])) for student in students_data)
    placed_students = len([s for s in students_data if len(s.get('projects', [])) > 0])  # Example metric
    
    # Calculate average projects per student
    total_projects = sum(len(student.get('projects', [])) for student in students_data)
    avg_projects = round(total_projects / total_students if total_students > 0 else 0, 1)
    
    # Get all unique skills and count their frequency
    all_skills = []
    for student in students_data:
        all_skills.extend(student.get('skills', []))
    
    # Calculate skill counts and maximum count
    skill_counts = Counter(all_skills)
    max_skill_count = max(skill_counts.values()) if skill_counts else 1
    top_skills = [(skill, count) for skill, count in skill_counts.most_common(5)]
    
    # Get all courses and calculate student counts for each course
    courses = list(mongo.db.courses.find())
    course_stats = []
    for course in courses:
        course_name = course.get('name', 'Unknown Course')
        course_id = course.get('course_id')  # Use 'course_id' field as a string

        # Count students enrolled in this course
        student_count = mongo.db.students.count_documents({'courses': course_id})
        course_stats.append({'name': course_name, 'student_count': student_count})


    # Get unique skills for filter
    unique_skills = sorted(list(set(all_skills)))
    
    return render_template(
        'students.html',
        students=students_data,
        total_students=total_students,
        placed_students=placed_students,
        avg_projects=avg_projects,
        total_publications=total_publications,
        top_skills=top_skills,
        skills=unique_skills,
        courses=course_stats,  # Use course_stats for the template
        max_skill_count=max_skill_count  # Add this new variable
    )

@app.route('/companies', methods=['GET', 'POST'])
def companies():
    if request.method == 'POST':
        # Get company data from the form
        company_id = request.form.get('company_id')
        
        # Check for existing company
        existing_company = mongo.db.companies.find_one({'company_id': company_id})
        if existing_company:
            return jsonify({'error': f"Company with ID {company_id} already exists."}), 400
        
        # Create a new company document
        company = {
            'company_id': company_id,
            'name': request.form.get('name'),
            'location': request.form.get('location'),
            'industry': request.form.get('industry'),
            'projects': [],
            'created_at': datetime.utcnow()
        }
        
        # Insert the new company into the database
        mongo.db.companies.insert_one(company)
        return jsonify({'message': f"Company {company['name']} added successfully!"}), 201

    # Handle GET request to fetch all companies
    companies = list(mongo.db.companies.find().sort('name'))  # Sort by company name
    
    # Calculate statistics
    total_companies = len(companies)
    total_projects = sum(len(company.get('projects', [])) for company in companies)
    
    # Calculate active companies (those with projects)
    active_companies = len([company for company in companies if company.get('projects')])

    # Calculate active company stats by industry
    active_company_stats = {}
    for company in companies:
        if company.get('projects'):  # Check if the company has any projects
            industry = company.get('industry')
            if industry:
                active_company_stats[industry] = active_company_stats.get(industry, 0) + 1

    # Get unique industries for the filter
    industries = sorted(list(set(company.get('industry') for company in companies if company.get('industry'))))

    return render_template(
        'companies.html', 
        companies=companies,
        total_companies=total_companies,
        active_companies=active_companies,
        total_projects=total_projects,
        industries=industries,
        active_company_stats=active_company_stats.items(),  # Pass as items for easier iteration
    )

@app.route('/projects', methods=['GET', 'POST'])
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
        
        # Update company's projects
        mongo.db.companies.update_one(
            {'company_id': project['company_id']},
            {'$push': {'projects': project['project_id']}}
        )
        
        # Update students' projects
        for student_id in project['student_ids']:
            mongo.db.students.update_one(
                {'student_id': student_id},
                {'$push': {'projects': project['project_id']}}
            )
            
        return redirect(url_for('projects'))
    
    projects = mongo.db.projects.find()
    companies = mongo.db.companies.find()
    students = mongo.db.students.find()
    return render_template('projects.html', 
                         projects=projects,
                         companies=companies,
                         students=students)

@app.route('/help')
def help():
    return render_template('help.html')

# API endpoints for CRUD operations
@app.route('/api/students/<student_id>', methods=['GET'])
def get_student(student_id):
    student = mongo.db.students.find_one({'student_id': student_id})
    if student:
        student['_id'] = str(student['_id'])
        return jsonify(student)
    return jsonify({'error': 'Student not found'}), 404

@app.route('/api/companies/<company_id>', methods=['GET'])
def get_company(company_id):
    company = mongo.db.companies.find_one({'company_id': company_id})
    if company:
        company['_id'] = str(company['_id'])
        return jsonify(company)
    return jsonify({'error': 'Company not found'}), 404

# Helper function to initialize the database
def init_database():
    schema = DatabaseSchema()
    schema.init_db()

if __name__ == "__main__":
    init_database()  # Initialize database collections and indexes
    app.run(debug=True)
