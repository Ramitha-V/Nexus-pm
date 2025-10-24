import datetime
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Table, Boolean)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# --- ASSOCIATION TABLES ---
task_skill_requirements_table = Table('task_skill_requirements', Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.task_id'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('skills.skill_id'), primary_key=True)
)
user_skills_table = Table('user_skills', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.user_id'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('skills.skill_id'), primary_key=True)
)
task_resource_requirements_table = Table('task_resource_requirements', Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.task_id'), primary_key=True),
    Column('resource_id', Integer, ForeignKey('resources.resource_id'), primary_key=True)
)
task_dependencies_table = Table('task_dependencies', Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.task_id'), primary_key=True),
    Column('dependency_id', Integer, ForeignKey('tasks.task_id'), primary_key=True)
)

# --- LOOKUP TABLES ---
class Skill(Base):
    __tablename__ = 'skills'
    skill_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

class Resource(Base):
    __tablename__ = 'resources'
    resource_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    type = Column(String)
    is_available = Column(Boolean, default=True)

# --- CORE TABLES ---
class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default='Contributor')
    availability_status = Column(String, default='Available')
    hashed_password = Column(String, nullable=False)
    skills = relationship("Skill", secondary=user_skills_table)
    tasks = relationship("Task", back_populates="assignee")
    comments = relationship("Comment", back_populates="author")
    approvals = relationship("Approval", back_populates="approver")

class Project(Base):
    __tablename__ = 'projects'
    project_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    tasks = relationship("Task", back_populates="project")

class Task(Base):
    __tablename__ = 'tasks'
    task_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, default='To Do')
    priority = Column(String, default='Medium')
    
    estimated_start_date = Column(DateTime)
    estimated_end_date = Column(DateTime)
    actual_start_date = Column(DateTime, nullable=True)
    actual_end_date = Column(DateTime, nullable=True)
    
    project_id = Column(Integer, ForeignKey('projects.project_id'))
    assignee_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")
    comments = relationship("Comment", back_populates="task")
    
    approvals = relationship("Approval", back_populates="task")
    required_skills = relationship("Skill", secondary=task_skill_requirements_table)
    required_resources = relationship("Resource", secondary=task_resource_requirements_table)
    
    dependencies = relationship(
        "Task",
        secondary=task_dependencies_table,
        primaryjoin=task_id == task_dependencies_table.c.task_id,
        secondaryjoin=task_id == task_dependencies_table.c.dependency_id,
        backref="dependents"
    )

class Comment(Base):
    __tablename__ = 'comments'
    comment_id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    task_id = Column(Integer, ForeignKey('tasks.task_id'))
    user_id = Column(Integer, ForeignKey('users.user_id'))
    
    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments") # Corrected relationship

class Approval(Base):
    __tablename__ = 'approvals'
    approval_id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default='Pending')
    timestamp = Column(DateTime, nullable=True)
    
    task_id = Column(Integer, ForeignKey('tasks.task_id'))
    approver_id = Column(Integer, ForeignKey('users.user_id'))
    
    task = relationship("Task", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")

def create_tables():
    from app.db.session import engine
    print("Creating/updating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created/updated successfully.")

