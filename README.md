# Nexus PM: An AI-Powered Project Management Dashboard

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?logo=javascript&logoColor=black)
![Chart.js](https://img.shields.io/badge/Chart.js-4.x-FF6384?logo=chartdotjs&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Gemini_AI-2.5_Flash-4A90E2?logo=google&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)

An AI-powered, dual-view project management system that transforms a traditional dashboard into a proactive, conversational assistant. Nexus PM can understand natural language, generate on-demand visualizations, and execute intelligent, role-based managerial actions.

![Manager Dashboard Screenshot](https://i.imgur.com/your-screenshot-url.png)
*(**Recommendation:** Upload a screenshot of your final Manager Dashboard and paste the link here.)*

## 1. Problem Statement

Traditional project management tools are static, data-heavy repositories. Managers and contributors must manually sift through complex tables and filter menus to find information, leading to information overload and slow decision-making. Crucial processes like task assignment are based on manual review, and the system is purely reactive. This project, **Nexus PM**, solves this by creating an intelligent, proactive "co-pilot" that allows users to *converse* with their project data.

## 2. Key Features

### General Features
* **Role-Based Dashboards:** A single login screen routes users to one of two distinct views:
    * **Contributor View:** A personal dashboard focused on individual tasks, stats, and timelines.
    * **Manager View:** A high-level command center for team and project oversight.
* **Secure Authentication:** Backend uses `pbkdf2_sha256` password hashing (`passlib`) to ensure no plain-text passwords are ever stored.

### Contributor AI Assistant
The Contributor's chatbot can:
* **List & Count:** Answer questions like `"show me my high priority tasks"` or `"how many tasks do I have?"`.
* **Handle Complex Queries:** Understand time-based queries (`"what's due in the next 7 days?"`), find long-running tasks, and list overdue tasks with their dependencies.
* **Retrieve Personal Info:** Answer questions like `"what are my skills?"` or `"who is my manager?"`.
* **Visualize Data:** Generate on-demand charts like `"visualize my tasks by priority"`.

### Manager Dashboard & AI Assistant
The Manager's view includes everything the Contributor has, plus:

* **Aggregate Dashboard:** A 2x2 grid of charts showing **Project Health**, **Overall Task Status**, **Resource Utilization**, and **Task Priority**.
* **Tabbed Interface:** Cleanly separates data into **Overview** (charts), **Projects** (paginated table with progress bars), and **Team** (paginated table of contributors).
* **Interactive Kanban & Gantt:** A full-stack, drag-and-drop Kanban board and a time-based Gantt chart to visualize project timelines.
* **Advanced AI Math:** The chatbot can answer complex counting queries about the *entire team*, such as:
    * `"how many contributors are on my team?"`
    * `"how many people know Python?"`
    * `"count the number of contributors who are on leave"`
* **Action-Oriented Commands:** The manager can execute commands:
    * **`create_task`:** `"create a new task 'Test the API' for the 'SOLIDWORKS' project"`
    * **`update_task`:** `"update task ID 145 and set the priority to high"`
    * **`assign_task`:** `"assign task ID 124 to Beth Jones"`
    * **`approve_task`:** `"approve task ID 125"`
* **"ID Safety" Feature:** The assistant will detect ambiguous commands (e.g., "update task 'Design the API'") and **refuse to execute**, prompting the manager for a unique Task ID to ensure data integrity.
* **Intelligent Recommendation Engine:**
    * **Query:** `"who is the best person for task ID 126?"`
    * **Action:** The system analyzes the task's required skills against all *available* contributors' skills and returns a ranked, data-driven recommendation.

## 3. Tech Stack

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, **Vanilla JavaScript (ES6+)** | Lightweight, fast, and responsive user interface. |
| | **Chart.js** | For all dynamic charts and visualizations on dashboards and in the chat. |
| **Backend** | **Python 3.10+** | Core language for all backend logic. |
| | **FastAPI** | A high-performance ASGI framework for building the RESTful API. |
| | **SQLAlchemy** | The Object-Relational Mapper (ORM) for all database interactions. |
| | **Pydantic** | For data validation, settings management, and API schema enforcement. |
| | **Passlib** | For all secure, one-way password hashing (`pbkdf2_sha256`). |
| **Database** | **PostgreSQL** | A robust relational database to store all project and user data. |
| | **pgAdmin 4** | GUI tool for database management and debugging. |
| | **Faker** | Python library used to generate the comprehensive, realistic synthetic dataset. |
| **AI / ML** | **Google Gemini API** (`gemini-2.5-flash`) | The "brain" for both chatbots, used for both Intent Classification and Response Generation (RAG). |
| | **Scikit-learn** | Used to train the **Random Forest Classifier** for Task Risk Prediction. |
| | **Pandas** | Used for feature engineering and data preprocessing for the ML model. |
| **Deployment** | **Docker** | For containerizing the FastAPI backend and PostgreSQL database. |
| | **AWS / Azure** | The target cloud platform for hosting the application, API, and database. |
| | **GitHub Actions** | For automating the CI/CD pipeline (testing and deployment). |

## 4. Local Setup and Installation

Follow these steps to run the project on your local machine.

### **Prerequisites**
* Python 3.10+
* PostgreSQL Server (running on `localhost:5432`)
* An IDE (like VS Code) with the "Live Server" extension for the frontend.

### **Step 1: Set up the PostgreSQL Database**
1.  Install PostgreSQL and start the server.
2.  Open **pgAdmin 4**.
3.  Right-click on **Databases** -> **Create** -> **Database...**
4.  Enter the name `nexus_pm_db` and click **Save**.

### **Step 2: Configure the Backend**
1.  Navigate to the project's **root directory** (`nexus-pm/`).
2.  Create a file named `.env` in the root folder. Copy and paste the following, replacing `'your_password'` with your PostgreSQL password:
    ```
    DATABASE_URL="postgresql://postgres:your_password@localhost/nexus_pm_db"
    GEMINI_API_KEY="your_google_ai_studio_api_key"
    ```
3.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
4.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/Scripts/activate
    ```
    *(**Note:** If your base Conda environment is active, run `conda deactivate` first!)*
5.  Install all required packages:
    ```bash
    pip install -r requirements.txt
    ```

### **Step 3: Populate the Database**
1.  **Crucial Step:** Your database is currently empty. To build the tables and fill them with data, you only need to run **one** script.
2.  Navigate to the `ml/scripts` directory:
    ```bash
    cd ../ml/scripts
    ```
3.  Run the data generation script. This will first **drop and re-create all tables** (to match your `models.py`) and then fill them with comprehensive, testable data.
    ```bash
    python generate_synthetic_data.py
    ```

### **Step 4: Run the Application**
1.  **Start the Backend Server:**
    * Navigate back to the `backend` directory: `cd ../../backend`
    * Run Uvicorn:
        ```bash
        uvicorn app.main:app --reload
        ```
    * Your backend is now running at `http://127.0.0.1:8000`

2.  **Start the Frontend:**
    * Open the `frontend` folder in your code editor.
    * Right-click the `index.html` file and select **"Open with Live Server"**.
    * The application will open in your browser, ready for login.

## 5. Usage (Demo)

You can log in as any user in your database. All users have the default password: **`test123`**.

* **Find a Contributor Email:** Open `pgAdmin` -> `nexus_pm_db` -> `users` table. Find a user with the role `Contributor` and copy their email.
* **Find a Manager Email:** Find a user with the role `Manager` and copy their email.

Log in with one of each to explore the two different dashboards and chatbot capabilities.

## 6. Project Team

* **Ramitha V** (22070126082)
* **Aayush Koul** (22070126003)
* **Rahul Purandare** (22070126080)
* **Saharsh Mehrotra** (22070126093)
