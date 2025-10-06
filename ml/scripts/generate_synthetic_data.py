import os
import sys
import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session

# Add the backend directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))

from app.db.session import SessionLocal
from app.db import models

# --- CONFIGURATION (FOR COMPREHENSIVE TESTING) ---
NUM_USERS = 25
TASKS_PER_PROJECT = 45
MAX_DEPENDENCIES_PER_TASK = 1
APPROVAL_PERCENTAGE = 0.4
COMMENT_PERCENTAGE = 0.7

# --- DATA POOLS ---
SKILL_NAMES = ['C++', 'Python', 'CAD Modeling', 'FEA', 'PLM Config', 'Cloud Arch', 'React.js', 'SOLIDWORKS API', 'Kernel Dev', 'DevOps', 'Database Design']
AVAILABILITY_CHOICES = ['Available', 'Available', 'Available', 'Busy', 'On Leave']

# --- FINAL FIX: Contextual, project-related comments ---
COMMENT_TEXTS = [
    "This design looks solid, but let's double-check the performance impact before merging.",
    "I'm currently blocked on this. I need the final API specifications from the other team.",
    "Implementation is complete. This task is now ready for the QA team to review.",
    "I've found a minor bug in the rendering pipeline. The logs are attached to the ticket for review.",
    "Do we have the updated UX mockups for this properties panel? The current ones are outdated.",
    "The latest version of the geometry kernel library is causing a conflict here. Rolling back for now.",
    "The performance benchmarks for the cloud migration are looking very promising.",
    "This task is more complex than initially estimated. Requesting a deadline extension of 3 days.",
    "The API documentation is complete and has been published to Confluence."
]

# --- Larger, Unique Task Pool ---
TASK_TEMPLATES = [
    {"title": "Draft Initial Design Document for V6 Kernel", "description": "Outline the proposed architecture for the next-generation geometry kernel.", "skills": ["C++", "Kernel Dev"]},
    {"title": "Implement User Authentication Endpoint", "description": "Develop the secure login and token generation endpoint using JWT.", "skills": ["Python", "Cloud Arch"]},
    {"title": "Map ERP Data Fields to ENOVIA Schema", "description": "Analyze and map the client's ERP data schema for integration.", "skills": ["PLM Config"]},
    {"title": "Profile Memory Leaks in Large Assemblies", "description": "Use performance analysis tools to identify memory leaks when loading large CAD assemblies.", "skills": ["C++"]},
    {"title": "Fix Z-Fighting Artifact in Rendering", "description": "Adjust clipping planes in the rendering pipeline to resolve Z-fighting issues.", "skills": ["SOLIDWORKS API"]},
    {"title": "Create React Components for Properties Panel", "description": "Build reusable React components for the new properties panel.", "skills": ["React.js"]},
    {"title": "Write Automated Tests for Meshing Algorithm", "description": "Develop unit and integration tests for the new meshing algorithm.", "skills": ["Python"]},
    {"title": "Document the New Supply Chain API Endpoints", "description": "Create detailed OpenAPI (Swagger) documentation for all new endpoints.", "skills": ["PLM Config"]},
    {"title": "Set Up CI/CD Pipeline for Cloud Migration", "description": "Configure the Azure DevOps pipeline to automate the build and deployment.", "skills": ["Cloud Arch", "DevOps"]},
    {"title": "Perform FEA Simulation on New Bracket Design", "description": "Run a static stress analysis on the new bracket design using SIMULIA.", "skills": ["FEA"]},
    {"title": "Refactor Legacy Import Module for STEP AP242", "description": "Update the data import service to support the modern STEP AP242 file format.", "skills": ["C++"]},
    {"title": "Develop UI for Task Assignment View", "description": "Implement the frontend view for managers to assign tasks.", "skills": ["React.js"]},
    {"title": "Test Database Performance Under Load", "description": "Run load tests on the PostgreSQL database.", "skills": ["Database Design"]},
    {"title": "Design a Scalable Cloud Architecture", "description": "Create a detailed architecture diagram for cloud deployment.", "skills": ["Cloud Arch"]},
    {"title": "Implement a Caching Strategy for User Profiles", "description": "Use Redis to cache user profiles, reducing database load.", "skills": ["Python", "DevOps"]},
]

fake = Faker()

def generate_data(db: Session):
    print("--- Starting Comprehensive Data Refresh ---")
    # Deletion logic
    print("Deleting old data...")
    db.query(models.Approval).delete()
    db.query(models.Comment).delete()
    db.execute(models.task_skill_requirements_table.delete())
    db.execute(models.user_skills_table.delete())
    db.execute(models.task_resource_requirements_table.delete())
    db.execute(models.task_dependencies_table.delete())
    db.query(models.Task).delete()
    db.query(models.Project).delete()
    db.query(models.User).delete()
    db.query(models.Skill).delete()
    db.query(models.Resource).delete()
    db.commit()

    # --- 1. Create Lookup Data & Users ---
    print("Creating skills, resources, and users...")
    skills_map = {name: models.Skill(name=name) for name in SKILL_NAMES}
    db.add_all(skills_map.values())
    db.commit()

    users = []
    for _ in range(NUM_USERS):
        name = fake.name()
        user_skills = random.sample(list(skills_map.values()), k=random.randint(2, 5))
        user = models.User(name=name, email=f"{name.lower().replace(' ', '.')}@nexus-pm.corp", role=random.choice(['Manager', 'Contributor']), skills=user_skills, availability_status=random.choice(AVAILABILITY_CHOICES))
        users.append(user)
    db.add_all(users)
    db.commit()
    managers = [u for u in users if u.role == 'Manager']

    # --- 2. Create Projects & Tasks with Specific Scenarios ---
    print("Creating projects and tasks with specific scenarios...")
    all_tasks = []
    
    project_names = ["3DEXPERIENCE Platform Migration", "SOLIDWORKS 2026 Rollout", "CATIA V6 Kernel Optimization"]
    for proj_name in project_names:
        proj_start = datetime.now() - timedelta(days=random.randint(60, 90))
        project = models.Project(name=proj_name, description=f"Initiative for {proj_name}.", start_date=proj_start, end_date=proj_start + timedelta(days=180))
        db.add(project)
        db.commit()

        shuffled_templates = random.sample(TASK_TEMPLATES, len(TASK_TEMPLATES))
        
        for i in range(TASKS_PER_PROJECT):
            template = shuffled_templates[i % len(shuffled_templates)]
            status = random.choice(['To Do', 'In Progress', 'Done'])
            priority = random.choice(['High', 'Medium', 'Low'])
            
            # Intelligent Date & Status Generation
            actual_start, actual_end = None, None
            if i < 5: # Overdue Tasks
                status = random.choice(['To Do', 'In Progress'])
                est_end = datetime.now() - timedelta(days=random.randint(5, 15))
                est_start = est_end - timedelta(days=10)
            elif 5 <= i < 10: # Long-running In Progress tasks
                status = 'In Progress'
                actual_start = datetime.now() - timedelta(days=random.randint(8, 15))
                est_start = actual_start - timedelta(days=5)
                est_end = datetime.now() + timedelta(days=random.randint(10, 20))
            elif 10 <= i < 15: # Tasks Due in Next 7 Days
                est_end = datetime.now() + timedelta(days=random.randint(0, 7))
                est_start = est_end - timedelta(days=10)
            elif 15 <= i < 20: # Upcoming Milestones
                priority = 'High'
                status = random.choice(['To Do', 'In Progress'])
                est_end = datetime.now() + timedelta(days=random.randint(8, 14))
                est_start = est_end - timedelta(days=15)
            else: # Standard future tasks
                est_start = datetime.now() + timedelta(days=random.randint(1, 30))
                est_end = est_start + timedelta(days=random.randint(10, 30))
            
            if status == 'In Progress' and not actual_start:
                actual_start = fake.date_time_between(start_date=est_start, end_date=datetime.now())
            elif status == 'Done':
                actual_start = fake.date_time_between(start_date=est_start, end_date=est_end)
                if actual_start: actual_end = fake.date_time_between(start_date=actual_start, end_date=est_end)

            task = models.Task(
                title=template["title"], description=template["description"],
                status=status, priority=priority,
                project_id=project.project_id, assignee_id=random.choice(users).user_id,
                estimated_start_date=est_start, estimated_end_date=est_end,
                actual_start_date=actual_start, actual_end_date=actual_end,
                required_skills=[skills_map[s_name] for s_name in template.get("skills", [])]
            )
            all_tasks.append(task)
            
    db.add_all(all_tasks)
    db.commit()

    # --- 3. Create Dependencies, Approvals, and Comments ---
    print("Creating dependencies, approvals, and comments...")
    for task in all_tasks:
        # Dependencies
        possible_prereqs = [p for p in all_tasks if p.project_id == task.project_id and p.task_id != task.task_id and p.estimated_end_date < task.estimated_start_date]
        if possible_prereqs and random.random() < 0.3:
            task.dependencies = random.sample(possible_prereqs, k=min(len(possible_prereqs), MAX_DEPENDENCIES_PER_TASK))
        
        # Approvals
        if random.random() < APPROVAL_PERCENTAGE and managers:
            status = random.choice(['Pending', 'Approved', 'Rejected'])
            timestamp = fake.date_time_this_month() if status != 'Pending' else None
            db.add(models.Approval(task_id=task.task_id, approver_id=random.choice(managers).user_id, status=status, timestamp=timestamp))
            
        # Comments
        if random.random() < COMMENT_PERCENTAGE:
            db.add(models.Comment(text=random.choice(COMMENT_TEXTS), task_id=task.task_id, user_id=random.choice(users).user_id))

    db.commit()
    print("--- Data Generation Complete! ---")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        generate_data(db)
    finally:
        db.close()