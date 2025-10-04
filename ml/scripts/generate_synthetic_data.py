import os
import sys
import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))
from app.db.session import SessionLocal
from app.db import models

# --- CONFIGURATION ---
NUM_USERS = 25
APPROVAL_PERCENTAGE = 0.3
COMMENT_PERCENTAGE = 0.6

# --- DATA POOLS ---
SKILL_NAMES = ['C++', 'Python', 'CAD Modeling', 'FEA', 'PLM Config', 'Cloud Arch', 'React.js', 'SOLIDWORKS API', 'Kernel Dev', 'DevOps']
RESOURCE_NAMES = [
    {"name": "High-Performance Compute Server", "type": "Server"},
    {"name": "SIMULIA License Seat", "type": "Software License"},
]
TASK_TEMPLATES = [
    {"title": "Design the new meshing algorithm", "description": "Create the technical design document for the new Delaunay triangulation algorithm.", "skills": ["C++", "Kernel Dev"]},
    {"title": "Develop the user authentication module", "description": "Implement OAuth 2.0 and JWT token handling for secure user login.", "skills": ["Python", "Cloud Arch"]},
    {"title": "Integrate the supply chain API", "description": "Connect the ENOVIA PLM system with the client's existing ERP system.", "skills": ["PLM Config", "Python"]},
    {"title": "Optimize memory usage in the geometry kernel", "description": "Profile and refactor the core geometry kernel to reduce memory footprint.", "skills": ["C++", "Kernel Dev"], "resources": ["High-Performance Compute Server"]},
    {"title": "Fix the bug in the rendering pipeline", "description": "Address the Z-fighting visual artifact when transparent objects overlap.", "skills": ["C++", "SOLIDWORKS API"]},
]
COMMENT_TEXTS = [
    "Looks good, but can we review the performance impact?", "I'm blocked on this, waiting for the API specs.",
    "This is complete and ready for QA.", "Found a minor bug, I've attached the logs.",
]
# --- NEW: Realistic availability statuses ---
AVAILABILITY_CHOICES = ['Available', 'Available', 'Available', 'Busy', 'On Leave'] # Skewed towards 'Available'

fake = Faker()

def generate_data(db: Session):
    print("--- Starting Full Data Refresh with Advanced Prerequisites ---")
    print("Deleting old data...")
    db.query(models.Approval).delete()
    db.query(models.Comment).delete()
    db.execute(models.task_skill_requirements_table.delete())
    db.execute(models.user_skills_table.delete()) # Explicitly clear the user_skills link table
    db.execute(models.task_resource_requirements_table.delete())
    db.execute(models.task_dependencies_table.delete())
    db.query(models.Task).delete()
    db.query(models.Project).delete()
    db.query(models.User).delete()
    db.query(models.Skill).delete()
    db.query(models.Resource).delete()
    db.commit()

    # --- 1. Create Lookup Data: Skills & Resources ---
    print("Creating skills and resources...")
    skills_map = {name: models.Skill(name=name) for name in SKILL_NAMES}
    db.add_all(skills_map.values())
    resources = [models.Resource(name=r["name"], type=r["type"]) for r in RESOURCE_NAMES]
    db.add_all(resources)
    db.commit()

    # --- 2. Create Users and assign them skills ---
    print("Creating users and assigning skills...")
    users = []
    for _ in range(NUM_USERS):
        name = fake.name()
        # --- FIX: Assign skill objects correctly ---
        user_skills = random.sample(list(skills_map.values()), k=random.randint(2, 5))
        user = models.User(
            name=name, email=f"{name.lower().replace(' ', '.')}@nexus-pm.corp",
            role=random.choice(['Manager', 'Contributor']),
            skills=user_skills, # This now correctly links to the Skill objects
            availability_status=random.choice(AVAILABILITY_CHOICES) # --- FIX: Use varied statuses ---
        )
        users.append(user)
    db.add_all(users)
    db.commit()
    managers = [u for u in users if u.role == 'Manager']

    # --- 3. Create Projects, Tasks, and link prerequisites ---
    print("Creating projects and tasks with logical dates...")
    all_tasks = []
    for proj_name in ["3DEXPERIENCE Platform Migration", "SOLIDWORKS 2026 Rollout", "CATIA V6 Kernel Optimization"]:
        proj_start = fake.date_time_this_year(before_now=True, after_now=False)
        project = models.Project(
            name=proj_name,
            description=f"Initiative for {proj_name}.",
            start_date=proj_start,
            end_date=proj_start + timedelta(days=random.randint(120, 365))
        )
        db.add(project)
        db.commit()

        for _ in range(30):
            template = random.choice(TASK_TEMPLATES)
            status = random.choice(['To Do', 'In Progress', 'Done'])
            est_start = fake.date_time_between(start_date=project.start_date, end_date=project.end_date)
            est_end = est_start + timedelta(days=random.randint(10, 30))

            actual_start, actual_end = None, None
            if status == 'In Progress':
                actual_start = fake.date_time_between(start_date=est_start, end_date=datetime.now())
            elif status == 'Done':
                actual_start = fake.date_time_between(start_date=est_start, end_date=est_end)
                if actual_start:
                    actual_end = fake.date_time_between(start_date=actual_start, end_date=est_end)

            task = models.Task(
                title=template["title"], description=template["description"],
                status=status, priority=random.choice(['High', 'Medium', 'Low']),
                project_id=project.project_id, assignee_id=random.choice(users).user_id,
                estimated_start_date=est_start, estimated_end_date=est_end,
                actual_start_date=actual_start, actual_end_date=actual_end,
                required_skills=[skills_map[s_name] for s_name in template.get("skills", [])],
                required_resources=[r for r in resources if r.name in template.get("resources", [])]
            )
            all_tasks.append(task)
    db.add_all(all_tasks)
    db.commit()

    # --- 4. Create Task Dependencies, Approvals, and Comments ---
    print("Creating dependencies, approvals, and comments...")
    for task in all_tasks:
        possible_prereqs = [p for p in all_tasks if p.project_id == task.project_id and p.task_id != task.task_id and p.estimated_end_date < task.estimated_start_date]
        if possible_prereqs:
            task.dependencies = random.sample(possible_prereqs, k=random.randint(0, 1))
        
        if random.random() < APPROVAL_PERCENTAGE and managers:
            approval_status = random.choice(['Pending', 'Approved', 'Rejected'])
            timestamp = None
            if approval_status != 'Pending':
                timestamp = fake.date_time_this_month()
            approval = models.Approval(task_id=task.task_id, approver_id=random.choice(managers).user_id, status=approval_status, timestamp=timestamp)
            db.add(approval)
            
        if random.random() < COMMENT_PERCENTAGE:
            comment = models.Comment(
                text=random.choice(COMMENT_TEXTS), task_id=task.task_id,
                user_id=random.choice(users).user_id,
                timestamp=fake.date_time_between(start_date=task.estimated_start_date) if task.estimated_start_date else datetime.now()
            )
            db.add(comment)

    db.commit()
    print("--- Data Generation Complete! ---")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        generate_data(db)
    finally:
        db.close()