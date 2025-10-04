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

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to get a response.');
        }
        
        const responseData = await response.json();
        const answer = responseData.answer;

        if (answer.output_type === 'visualization') {
            renderVisualizationMessage(answer.data);
        } else {
            const htmlContent = formatTextResponse(answer.data); 
            appendMessage(htmlContent, 'ai', true);
        }

    } catch (error) {
        appendMessage(`<p>Sorry, I encountered an error: ${error.message}</p>`, 'ai', true);
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
        messageDiv.innerHTML = content;
    } else {
        const p = document.createElement('p');
        p.textContent = content;
        messageDiv.appendChild(p);
    }
    chatBody.appendChild(messageDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function renderVisualizationMessage(chartData) {
    if (!chartData || !chartData.values || chartData.values.length === 0) {
        appendMessage("<p>No data available to display a chart for this request.</p>", 'ai', true);
        return;
    }

    const chartId = `chart-${Date.now()}`;
    const chartHtml = `
        <div class="chat-visualization">
            <h4>${chartData.title}</h4>
            <div class="chart-wrapper-chat">
                <canvas id="${chartId}"></canvas>
            </div>
        </div>
    `;
    appendMessage(chartHtml, 'ai', true);

    const chartColors = ['#4f46e5', '#f59e0b', '#10b981', '#ef4444', '#3b82f6', '#64748b'];

    setTimeout(() => {
        const ctx = document.getElementById(chartId)?.getContext('2d');
        if (!ctx) return;
        
        new Chart(ctx, {
            type: chartData.chart_type,
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: chartData.title,
                    data: chartData.values,
                    backgroundColor: chartColors,
                    borderColor: '#ffffff',
                    borderWidth: chartData.chart_type === 'doughnut' ? 4 : 0,
                    borderRadius: chartData.chart_type === 'bar' ? 4 : 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: chartData.chart_type === 'bar' ? 'y' : 'x',
                plugins: { 
                    legend: { 
                        display: chartData.chart_type !== 'bar',
                        position: 'bottom' 
                    } 
                },
                scales: {
                    x: { display: chartData.chart_type === 'bar', beginAtZero: true },
                    y: { display: chartData.chart_type === 'bar' }
                }
            }
        });
    }, 100);
}


function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'chat-message ai';
    indicator.id = 'typing-indicator';
    indicator.innerHTML = `<div class="typing-indicator"><span></span><span></span><span></span></div>`;
    chatBody.appendChild(indicator);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

function formatTextResponse(data) {
    const safeIntro = document.createElement('p');
    safeIntro.textContent = data.introduction;
    let html = safeIntro.outerHTML;

    if (data.items && data.items.length > 0) {
        html += '<ul>';
        data.items.forEach(item => {
            const safeLi = document.createElement('li');
            safeLi.textContent = item;
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