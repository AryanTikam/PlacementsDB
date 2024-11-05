from pymongo import MongoClient
import random
from datetime import datetime, timedelta
import faker
import uuid

# Initialize Faker
fake = faker.Faker()

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['university_db']

# Clear existing data
db.students.drop()
db.companies.drop()
db.projects.drop()
db.skills.drop()
db.courses.drop()
db.certificates.drop()
db.publications.drop()
db.interviews.drop()

# Predefined lists for random selection
skills_list = [
    "Python", "JavaScript", "Java", "C++", "React", "Node.js", "MongoDB",
    "AWS", "Docker", "Kubernetes", "Machine Learning", "Data Analysis",
    "Deep Learning", "DevOps", "Agile", "Scrum", "UI/UX Design",
    "Cloud Computing", "Cybersecurity", "Blockchain"
]

course_names = [
    "Advanced Database Systems", "Machine Learning Fundamentals",
    "Web Development", "Cloud Computing", "Artificial Intelligence",
    "Software Engineering", "Data Structures", "Algorithms",
    "Computer Networks", "Operating Systems", "Cybersecurity Basics",
    "Mobile App Development", "Project Management", "System Design"
]

certificate_names = [
    "AWS Certified Developer", "Google Cloud Professional",
    "MongoDB Certified Developer", "Python Professional Certificate",
    "Java SE 11 Developer", "Certified Kubernetes Administrator",
    "Microsoft Azure Developer", "Certified Scrum Master",
    "CompTIA Security+", "Cisco CCNA"
]

industries = [
    "Technology", "Finance", "Healthcare", "Education", "Manufacturing",
    "Retail", "Consulting", "Entertainment", "Energy", "Telecommunications"
]

# Generate Skills
print("Generating skills...")
skills_data = []
for skill in skills_list:
    skill_doc = {
        'skill_id': str(uuid.uuid4()),
        'name': skill,
        'category': random.choice(['Technical', 'Soft Skills', 'Domain Knowledge'])
    }
    skills_data.append(skill_doc)
db.skills.insert_many(skills_data)

# Generate Companies
print("Generating companies...")
companies_data = []
for i in range(20):
    company = {
        'company_id': f'COMP{str(i+1).zfill(3)}',
        'name': fake.company(),
        'location': fake.city(),
        'industry': random.choice(industries),
        'contact_email': fake.company_email(),
        'phone': fake.phone_number(),
        'website': fake.url(),
        'projects': [],
        'average_ctc': random.randint(50000, 150000),
        'students_placed': []  # Add empty list for students placed
    }
    companies_data.append(company)
db.companies.insert_many(companies_data)

# Generate Courses
print("Generating courses...")
courses_data = []
for course_name in course_names:
    course = {
        'course_id': f'CRS{str(len(courses_data)+1).zfill(3)}',
        'name': course_name,
        'description': fake.text(max_nb_chars=200),
        'credits': random.randint(1, 4),
        'duration_weeks': random.randint(8, 16)
    }
    courses_data.append(course)
db.courses.insert_many(courses_data)

# Generate Certificates
print("Generating certificates...")
certificates_data = []
for cert_name in certificate_names:
    valid_till_date = datetime.utcnow() + timedelta(days=365 * random.randint(1, 3))
    certificate = {
        'certificate_id': f'CERT{str(len(certificates_data)+1).zfill(3)}',
        'name': cert_name,
        'issuing_authority': fake.company(),
        'valid_till': valid_till_date
    }
    certificates_data.append(certificate)
db.certificates.insert_many(certificates_data)

# Generate Students
print("Generating students...")
students_data = []
for i in range(100):
    student = {
        'student_id': f'STU{str(i+1).zfill(3)}',
        'name': fake.name(),
        'email': fake.email(),
        'phone': fake.phone_number(),
        'address': f"{fake.street_address()}, {fake.city()}, {fake.state()} {fake.zipcode()}",
        'skills': random.sample(skills_list, random.randint(3, 8)),
        'projects': [],
        'courses': random.sample([c['course_id'] for c in courses_data], random.randint(2, 5)),
        'certificates': random.sample([c['certificate_id'] for c in certificates_data], random.randint(1, 3)),
        'publications': [],
        'cgpa': round(random.uniform(0, 10), 2)
    }
    students_data.append(student)
db.students.insert_many(students_data)

# Generate Projects
print("Generating projects...")
projects_data = []
for i in range(50):
    start_date = datetime.now() - timedelta(days=random.randint(0, 365))
    project = {
        'project_id': f'PRJ{str(i+1).zfill(3)}',
        'title': fake.catch_phrase(),
        'description': fake.text(max_nb_chars=200),
        'start_date': start_date,
        'end_date': start_date + timedelta(days=random.randint(30, 180)),
        'company_id': random.choice(companies_data)['company_id'],
        'student_ids': random.sample([s['student_id'] for s in students_data], random.randint(2, 5)),
        'skills_required': random.sample(skills_list, random.randint(3, 6)),
        'status': random.choice(['Planning', 'In Progress', 'Completed', 'On Hold']),
        'budget': random.randint(10000, 100000)
    }
    projects_data.append(project)
db.projects.insert_many(projects_data)

# Update company projects
print("Updating company projects...")
for project in projects_data:
    db.companies.update_one(
        {'company_id': project['company_id']},
        {'$push': {'projects': project['project_id']}}
    )

# Update student projects
print("Updating student projects...")
for project in projects_data:
    for student_id in project['student_ids']:
        db.students.update_one(
            {'student_id': student_id},
            {'$push': {'projects': project['project_id']}}
        )

# Generate Publications
print("Generating publications...")
publications_data = []
for i in range(30):
    pub_date = datetime.now() - timedelta(days=random.randint(0, 1095))
    publication = {
        'publication_id': f'PUB{str(i+1).zfill(3)}',
        'title': fake.sentence(),
        'authors': random.sample([s['student_id'] for s in students_data], random.randint(1, 3)),
        'journal': fake.company() + ' Journal',
        'publication_date': pub_date,
        'doi': f'10.{random.randint(1000,9999)}/{uuid.uuid4().hex[:8]}',
        'citations': random.randint(0, 100)
    }
    publications_data.append(publication)
db.publications.insert_many(publications_data)

# Update student publications
print("Updating student publications...")
for publication in publications_data:
    for author_id in publication['authors']:
        db.students.update_one(
            {'student_id': author_id},
            {'$push': {'publications': publication['publication_id']}}
        )

# Generate Interviews
print("Generating interviews...")
interviews_data = []
for i in range(20):
    interview_date = fake.date_between(start_date='today', end_date='+1y')
    interview_datetime = datetime.combine(interview_date, datetime.min.time())
    interview = {
        'interview_id': f'INT{str(i+1).zfill(3)}',
        'company_id': random.choice(companies_data)['company_id'],
        'date': interview_datetime,
        'time': fake.time(),
        'location': fake.city(),
        'interviewer': fake.name(),
        'student_ids': random.sample([s['student_id'] for s in students_data], random.randint(1, 3))
    }
    interviews_data.append(interview)
db.interviews.insert_many(interviews_data)

# Update company interviews
print("Updating company interviews...")
for interview in interviews_data:
    db.companies.update_one(
        {'company_id': interview['company_id']},
        {'$push': {'interviews': interview['interview_id']}}
    )

# Generate Students Placed
print("Generating students placed for each company...")
all_students = [s['student_id'] for s in students_data]
placed_students = set()  # Track students who are already placed

for company in companies_data:
    # Select students who are not yet placed by any company
    available_students = list(set(all_students) - placed_students)
    # Randomly select a subset of students who will be placed by this company
    num_to_place = random.randint(1, min(5, len(available_students)))
    company_placed_students = random.sample(available_students, num_to_place)
    
    # Update the placed_students set to prevent future companies from placing these students
    placed_students.update(company_placed_students)
    
    # Update the company document in MongoDB with the selected placed students
    db.companies.update_one(
        {'company_id': company['company_id']},
        {'$set': {'students_placed': company_placed_students}}
    )

print("Unique student placements across companies have been completed!")

print("Data generation completed!")

# Ensure unique indexes for ID fields in MongoDB
db.students.create_index("student_id", unique=True)
db.companies.create_index("company_id", unique=True)
db.projects.create_index("project_id", unique=True)
db.skills.create_index("skill_id", unique=True)
db.courses.create_index("course_id", unique=True)
db.certificates.create_index("certificate_id", unique=True)
db.publications.create_index("publication_id", unique=True)
db.interviews.create_index("interview_id", unique=True)

# Print some statistics
print(f"Inserted {db.students.count_documents({})} students.")
print(f"Inserted {db.companies.count_documents({})} companies.")
print(f"Inserted {db.projects.count_documents({})} projects.")
print(f"Inserted {db.skills.count_documents({})} skills.")
print(f"Inserted {db.courses.count_documents({})} courses.")
print(f"Inserted {db.certificates.count_documents({})} certificates.")
print(f"Inserted {db.publications.count_documents({})} publications.")
print(f"Inserted {db.interviews.count_documents({})} interviews.")
