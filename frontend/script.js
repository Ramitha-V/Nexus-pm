// --- CONFIGURATION & GLOBAL STATE ---
const API_BASE_URL = 'http://127.0.0.1:8000/api';
const TASKS_PER_PAGE = 8;
let allTasks = [];
let currentPage = 1;

// --- DOM ELEMENTS ---
const loginView = document.getElementById('login-view');
const dashboardView = document.getElementById('dashboard-view');
const loginForm = document.getElementById('login-form');
const emailInput = document.getElementById('email');
const errorMessage = document.getElementById('error-message');
const logoutButton = document.getElementById('logout-button');
const prevPageButton = document.getElementById('prev-page');
const nextPageButton = document.getElementById('next-page');
const pageInfoSpan = document.getElementById('page-info');
const chatFab = document.getElementById('chat-fab');
const chatModalContainer = document.getElementById('chat-modal-container');
const closeChatBtn = document.getElementById('close-chat-btn');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatBody = document.getElementById('chat-body');

// --- CHART INSTANCES ---
let statusChartInstance = null;
let priorityChartInstance = null;

// --- EVENT LISTENERS ---
loginForm.addEventListener('submit', handleLogin);
logoutButton.addEventListener('click', showLogin);
prevPageButton.addEventListener('click', () => {
    if (currentPage > 1) {
        currentPage--;
        renderTasksTable();
    }
});
nextPageButton.addEventListener('click', () => {
    const totalPages = Math.ceil(allTasks.length / TASKS_PER_PAGE);
    if (currentPage < totalPages) {
        currentPage++;
        renderTasksTable();
    }
});
chatFab.addEventListener('click', () => chatModalContainer.classList.add('visible'));
closeChatBtn.addEventListener('click', () => chatModalContainer.classList.remove('visible'));
chatForm.addEventListener('submit', handleChatMessage);

// --- AUTH & DATA FETCHING ---
async function handleLogin(event) {
    event.preventDefault();
    const email = emailInput.value;
    errorMessage.textContent = '';
    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        if (!response.ok) throw new Error('User not found. Please check your email.');
        const userData = await response.json();
        sessionStorage.setItem('user', JSON.stringify(userData));
        showDashboard();
    } catch (error) {
        errorMessage.textContent = error.message;
    }
}

async function fetchAndRenderDashboard() {
    const user = JSON.parse(sessionStorage.getItem('user'));
    if (!user) return;
    try {
        const response = await fetch(`${API_BASE_URL}/users/${user.user_id}/dashboard`);
        if (!response.ok) throw new Error('Could not load dashboard data.');
        const data = await response.json();
        allTasks = data.tasks;
        currentPage = 1;
        renderDashboard(data);
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        alert('Failed to load dashboard data. Please try again later.');
    }
}

// --- UI RENDERING ---
function renderDashboard(data) {
    document.getElementById('user-greeting').textContent = `Welcome, ${data.user_info.name}`;
    document.getElementById('total-tasks').textContent = data.stats.total_tasks;
    document.getElementById('tasks-todo').textContent = data.stats.tasks_todo;
    document.getElementById('tasks-inprogress').textContent = data.stats.tasks_inprogress;
    document.getElementById('tasks-done').textContent = data.stats.tasks_done;
    renderStatusChart(data.stats);
    renderPriorityChart(allTasks);
    renderTasksTable();
}

function renderTasksTable() {
    const tableBody = document.getElementById('tasks-table-body');
    tableBody.innerHTML = '';
    const start = (currentPage - 1) * TASKS_PER_PAGE;
    const end = start + TASKS_PER_PAGE;
    const paginatedTasks = allTasks.slice(start, end);
    paginatedTasks.forEach(task => {
        const row = tableBody.insertRow();
        const statusClass = `status-${task.status.toLowerCase().replace(' ', '-')}`;
        const priorityClass = `priority-${task.priority.toLowerCase()}`;
        row.innerHTML = `
            <td>${task.title}</td>
            <td><span class="status-pill ${statusClass}">${task.status}</span></td>
            <td><span class="priority-pill ${priorityClass}">${task.priority}</span></td>
        `;
    });
    updatePaginationControls();
}

function updatePaginationControls() {
    const totalPages = Math.ceil(allTasks.length / TASKS_PER_PAGE);
    pageInfoSpan.textContent = `Page ${currentPage} of ${totalPages || 1}`;
    prevPageButton.disabled = currentPage === 1;
    nextPageButton.disabled = currentPage === totalPages || totalPages === 0;
}

// --- CHART RENDERING ---
function renderStatusChart(stats) {
    if (statusChartInstance) statusChartInstance.destroy();
    const ctx = document.getElementById('statusChart').getContext('2d');
    statusChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['To Do', 'In Progress', 'Done'],
            datasets: [{
                data: [stats.tasks_todo, stats.tasks_inprogress, stats.tasks_done],
                backgroundColor: ['#f59e0b', '#3b82f6', '#10b981'],
                borderColor: '#ffffff',
                borderWidth: 4
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { display: true, position: 'bottom' } } }
    });
}

function renderPriorityChart(tasks) {
    if (priorityChartInstance) priorityChartInstance.destroy();
    const priorityCounts = tasks.reduce((acc, task) => {
        acc[task.priority] = (acc[task.priority] || 0) + 1;
        return acc;
    }, { 'High': 0, 'Medium': 0, 'Low': 0 });
    const ctx = document.getElementById('priorityChart').getContext('2d');
    priorityChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(priorityCounts),
            datasets: [{
                label: 'Task Count',
                data: Object.values(priorityCounts),
                backgroundColor: ['#ef4444', '#f59e0b', '#3b82f6'],
                borderRadius: 4
            }]
        },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } }
    });
}

// --- CHAT FUNCTIONS ---
async function handleChatMessage(event) {
    event.preventDefault();
    const question = chatInput.value.trim();
    if (!question) return;

    appendMessage(question, 'user');
    chatInput.value = '';
    chatInput.disabled = true;

    showTypingIndicator();

    const user = JSON.parse(sessionStorage.getItem('user'));

    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, user_id: user.user_id })
        });

        if (!response.ok) throw new Error('Failed to get a response.');
        
        const data = await response.json();
        // The 'answer' is now a structured object { introduction, tasks }
        const htmlContent = formatAIResponse(data.answer); 
        
        appendMessage(htmlContent, 'ai', true); // Pass true to render as HTML

    } catch (error) {
        appendMessage('<p>Sorry, I encountered an error. Please try again.</p>', 'ai', true);
        console.error(error);
    } finally {
        removeTypingIndicator();
        chatInput.disabled = false;
        chatInput.focus();
    }
}

function appendMessage(content, sender, isHTML = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    
    if (isHTML) {
        // Safely set the inner HTML
        messageDiv.innerHTML = content;
    } else {
        const p = document.createElement('p');
        p.textContent = content;
        messageDiv.appendChild(p);
    }
    
    chatBody.appendChild(messageDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'chat-message ai';
    indicator.id = 'typing-indicator';
    indicator.innerHTML = `
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    chatBody.appendChild(indicator);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

// This is the new, reliable formatting function
function formatAIResponse(answer) {
    // Sanitize the introduction to prevent potential XSS issues
    const safeIntro = document.createElement('p');
    safeIntro.textContent = answer.introduction;

    let html = safeIntro.outerHTML;

    // If there are tasks, build an unordered list
    if (answer.tasks && answer.tasks.length > 0) {
        html += '<ul>';
        answer.tasks.forEach(task => {
            const safeLi = document.createElement('li');
            safeLi.textContent = task;
            html += safeLi.outerHTML;
        });
        html += '</ul>';
    }
    return html;
}

// --- VIEW MANAGEMENT ---
function showDashboard() {
    loginView.style.display = 'none';
    dashboardView.style.display = 'flex';
    fetchAndRenderDashboard();
}

function showLogin() {
    sessionStorage.removeItem('user');
    loginView.style.display = 'flex';
    dashboardView.style.display = 'none';
    allTasks = [];
}

// --- INITIALIZATION ---
function init() {
    if (sessionStorage.getItem('user')) {
        showDashboard();
    } else {
        showLogin();
    }
}

init();

