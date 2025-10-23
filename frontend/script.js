// --- CONFIGURATION & GLOBAL STATE ---
const API_BASE_URL = 'http://18.208.157.64:8000/api';
const ITEMS_PER_PAGE = 8;
let allTasks = [], allProjects = [], allContributors = [];
let currentPage = 1, currentProjectsPage = 1, currentTeamPage = 1;

// --- DOM ELEMENTS ---
const loginView = document.getElementById('login-view');
const contributorView = document.getElementById('contributor-view');
const managerView = document.getElementById('manager-view');
const loginForm = document.getElementById('login-form');
const emailInput = document.getElementById('email');
const errorMessage = document.getElementById('error-message');
const logoutButton = document.getElementById('logout-button');
const managerLogoutButton = document.getElementById('manager-logout-button');
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
let statusChartInstance, priorityChartInstance;
let projectHealthChart, overallStatusChart, resourceChart, overallPriorityChart;

// --- EVENT LISTENERS ---
if (loginForm) loginForm.addEventListener('submit', handleLogin);
if (logoutButton) logoutButton.addEventListener('click', showLogin);
if (managerLogoutButton) managerLogoutButton.addEventListener('click', showLogin);
if (prevPageButton) prevPageButton.addEventListener('click', () => { if (currentPage > 1) { currentPage--; renderContributorTasksTable(); } });
if (nextPageButton) nextPageButton.addEventListener('click', () => { if (currentPage < Math.ceil(allTasks.length / ITEMS_PER_PAGE)) { currentPage++; renderContributorTasksTable(); } });
if (chatFab) chatFab.addEventListener('click', () => chatModalContainer.classList.add('visible'));
if (closeChatBtn) closeChatBtn.addEventListener('click', () => chatModalContainer.classList.remove('visible'));
if (chatForm) chatForm.addEventListener('submit', handleChatMessage);

document.querySelectorAll('.tab-link').forEach(button => {
    button.addEventListener('click', () => {
        document.querySelectorAll('.tab-link').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        button.classList.add('active');
        const tabId = button.dataset.tab;
        const tabContent = document.getElementById(tabId);
        if (tabContent) {
            tabContent.classList.add('active');
        }
    });
});

const projectsPrev = document.getElementById('projects-prev-page');
if(projectsPrev) projectsPrev.addEventListener('click', () => { if (currentProjectsPage > 1) { currentProjectsPage--; renderProjectsTable(); } });
const projectsNext = document.getElementById('projects-next-page');
if(projectsNext) projectsNext.addEventListener('click', () => { if (currentProjectsPage < Math.ceil(allProjects.length / ITEMS_PER_PAGE)) { currentProjectsPage++; renderProjectsTable(); } });

const teamPrev = document.getElementById('team-prev-page');
if(teamPrev) teamPrev.addEventListener('click', () => { if (currentTeamPage > 1) { currentTeamPage--; renderContributorsTable(); } });
const teamNext = document.getElementById('team-next-page');
if(teamNext) teamNext.addEventListener('click', () => { if (currentTeamPage < Math.ceil(allContributors.length / ITEMS_PER_PAGE)) { currentTeamPage++; renderContributorsTable(); } });


// --- AUTH & ROUTING ---
async function handleLogin(event) {
    event.preventDefault();
    const email = emailInput.value.trim();
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
        routeUser(userData);
    } catch (error) {
        errorMessage.textContent = error.message;
    }
}

function routeUser(user) {
    if (user.role === 'Manager') {
        showManagerDashboard();
    } else {
        showContributorDashboard();
    }
}

function init() {
    const user = JSON.parse(sessionStorage.getItem('user'));
    if (user) {
        routeUser(user);
    } else {
        showLogin();
    }
}

// --- VIEW MANAGEMENT ---
function showContributorDashboard() {
    loginView.style.display = 'none';
    managerView.style.display = 'none';
    contributorView.style.display = 'flex';
    chatFab.style.display = 'flex';
    fetchAndRenderContributorDashboard();
}

function showManagerDashboard() {
    loginView.style.display = 'none';
    contributorView.style.display = 'none';
    managerView.style.display = 'flex';
    chatFab.style.display = 'flex';
    fetchAndRenderManagerDashboard();
}

function showLogin() {
    sessionStorage.removeItem('user');
    loginView.style.display = 'flex';
    contributorView.style.display = 'none';
    managerView.style.display = 'none';
    chatFab.style.display = 'none';
    chatBody.innerHTML = '<div class="chat-message ai"><p>Hello! How can I help you today?</p></div>';
}

// --- MANAGER DASHBOARD ---
async function fetchAndRenderManagerDashboard() {
    const user = JSON.parse(sessionStorage.getItem('user'));
    if (!user) return;
    document.getElementById('manager-greeting').textContent = `Welcome, ${user.name}`;
    try {
        const [stats, chartsData, projects, contributors] = await Promise.all([
            fetch(`${API_BASE_URL}/manager/overview-stats`).then(res => res.json()),
            fetch(`${API_BASE_URL}/manager/dashboard-charts`).then(res => res.json()),
            fetch(`${API_BASE_URL}/manager/projects-summary`).then(res => res.json()),
            fetch(`${API_BASE_URL}/manager/contributors-summary`).then(res => res.json())
        ]);
        allProjects = projects;
        allContributors = contributors;
        currentProjectsPage = 1;
        currentTeamPage = 1;
        renderManagerStats(stats);
        renderManagerCharts(chartsData);
        renderProjectsTable();
        renderContributorsTable();
    } catch (error) {
        console.error("Failed to load manager dashboard:", error);
    }
}

function renderManagerStats(stats) {
    const statsGrid = document.getElementById('manager-stats-grid');
    statsGrid.innerHTML = `
        <div class="stat-card"><h3>Total Projects</h3><p class="value">${stats.total_projects}</p></div>
        <div class="stat-card"><h3>Contributors</h3><p class="value">${stats.total_contributors}</p></div>
        <div class="stat-card approvals"><h3>Pending Approvals</h3><p class="value">${stats.pending_approvals}</p></div>
    `;
}

function renderManagerCharts(data) {
    if (projectHealthChart) projectHealthChart.destroy();
    const phCtx = document.getElementById('projectHealthChart').getContext('2d');
    projectHealthChart = new Chart(phCtx, {
        type: 'bar',
        data: {
            labels: data.project_health.map(p => p.name.length > 25 ? p.name.substring(0, 25) + '...' : p.name),
            datasets: [{ label: '% Complete', data: data.project_health.map(p => p.completion), backgroundColor: '#4f46e5', borderRadius: 4 }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } }
    });

    if (overallStatusChart) overallStatusChart.destroy();
    const osCtx = document.getElementById('overallStatusChart').getContext('2d');
    overallStatusChart = new Chart(osCtx, {
        type: 'doughnut',
        data: { labels: data.overall_status.labels, datasets: [{ data: data.overall_status.values, backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'], borderColor: '#fff', borderWidth: 4 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { position: 'bottom' } } }
    });

    if (resourceChart) resourceChart.destroy();
    const ruCtx = document.getElementById('resourceChart').getContext('2d');
    resourceChart = new Chart(ruCtx, {
        type: 'bar',
        data: { labels: data.resource_utilization.map(r => r.name), datasets: [{ label: 'Active Tasks Using', data: data.resource_utilization.map(r => r.usage), backgroundColor: '#10b981', borderRadius: 4 }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } } }
    });
    
    if (overallPriorityChart) overallPriorityChart.destroy();
    const opCtx = document.getElementById('overallPriorityChart').getContext('2d');
    overallPriorityChart = new Chart(opCtx, {
        type: 'pie',
        data: { labels: data.overall_priority.labels, datasets: [{ data: data.overall_priority.values, backgroundColor: ['#ef4444', '#f59e0b', '#3b82f6'], borderColor: '#fff', borderWidth: 4 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
    });
}

function renderProjectsTable() {
    const tableBody = document.getElementById('projects-table-body');
    const start = (currentProjectsPage - 1) * ITEMS_PER_PAGE;
    const paginatedItems = allProjects.slice(start, start + ITEMS_PER_PAGE);
    tableBody.innerHTML = paginatedItems.map(p => `<tr><td>${p.name}</td><td><div class="progress-bar-container"><span>${p.completion_percent}%</span><div class="progress-bar-background"><div class="progress-bar" style="width: ${p.completion_percent}%;"></div></div></div></td><td>${p.task_count}</td><td>${p.end_date}</td></tr>`).join('');
    updateProjectsPagination();
}

function updateProjectsPagination() {
    const totalPages = Math.ceil(allProjects.length / ITEMS_PER_PAGE);
    document.getElementById('projects-page-info').textContent = `Page ${currentProjectsPage} of ${totalPages || 1}`;
    document.getElementById('projects-prev-page').disabled = currentProjectsPage === 1;
    document.getElementById('projects-next-page').disabled = currentProjectsPage >= totalPages;
}

function renderContributorsTable() {
    const tableBody = document.getElementById('contributors-table-body');
    const start = (currentTeamPage - 1) * ITEMS_PER_PAGE;
    const paginatedItems = allContributors.slice(start, start + ITEMS_PER_PAGE);
    tableBody.innerHTML = paginatedItems.map(c => `<tr><td>${c.name}</td><td><span class="pill ${c.availability.toLowerCase().replace(' ', '-')}">${c.availability}</span></td><td>${c.skills.join(', ')}</td><td>${c.task_load}</td></tr>`).join('');
    updateTeamPagination();
}

function updateTeamPagination() {
    const totalPages = Math.ceil(allContributors.length / ITEMS_PER_PAGE);
    document.getElementById('team-page-info').textContent = `Page ${currentTeamPage} of ${totalPages || 1}`;
    document.getElementById('team-prev-page').disabled = currentTeamPage === 1;
    document.getElementById('team-next-page').disabled = currentTeamPage >= totalPages;
}

// --- CONTRIBUTOR DASHBOARD FUNCTIONS ---
async function fetchAndRenderContributorDashboard() {
    const user = JSON.parse(sessionStorage.getItem('user'));
    if (!user) return;
    try {
        const response = await fetch(`${API_BASE_URL}/users/${user.user_id}/dashboard`);
        if (!response.ok) throw new Error('Could not load dashboard data.');
        const data = await response.json();
        allTasks = data.tasks;
        currentPage = 1;
        renderContributorDashboard(data);
    } catch (error) {
        console.error('Failed to load contributor dashboard:', error);
    }
}

function renderContributorDashboard(data) {
    document.getElementById('user-greeting').textContent = `Welcome, ${data.user_info.name}`;
    document.getElementById('total-tasks').textContent = data.stats.total_tasks;
    document.getElementById('tasks-todo').textContent = data.stats.tasks_todo;
    document.getElementById('tasks-inprogress').textContent = data.stats.tasks_inprogress;
    document.getElementById('tasks-done').textContent = data.stats.tasks_done;
    renderStatusChart(data.stats);
    renderPriorityChart(allTasks);
    renderContributorTasksTable();
}

function renderContributorTasksTable() {
    const tableBody = document.getElementById('tasks-table-body');
    tableBody.innerHTML = '';
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const paginatedTasks = allTasks.slice(start, start + ITEMS_PER_PAGE);
    paginatedTasks.forEach(task => {
        const row = tableBody.insertRow();
        row.innerHTML = `<td>${task.title}</td><td><span class="status-pill status-${task.status.toLowerCase().replace(' ', '-')}">${task.status}</span></td><td><span class="priority-pill priority-${task.priority.toLowerCase()}">${task.priority}</span></td>`;
    });
    updateContributorPagination();
}

function updateContributorPagination() {
    const totalPages = Math.ceil(allTasks.length / ITEMS_PER_PAGE);
    pageInfoSpan.textContent = `Page ${currentPage} of ${totalPages || 1}`;
    prevPageButton.disabled = currentPage === 1;
    nextPageButton.disabled = currentPage >= totalPages;
}

// --- SHARED FUNCTIONS ---
function renderStatusChart(stats) {
    if (statusChartInstance) statusChartInstance.destroy();
    const ctx = document.getElementById('statusChart')?.getContext('2d');
    if (!ctx) return;
    statusChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['To Do', 'In Progress', 'Done'],
            datasets: [{ data: [stats.tasks_todo, stats.tasks_inprogress, stats.tasks_done], backgroundColor: ['#f59e0b', '#3b82f6', '#10b981'], borderColor: '#fff', borderWidth: 4 }]
        },
        options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { display: true, position: 'bottom' } } }
    });
}

function renderPriorityChart(tasks) {
    if (priorityChartInstance) priorityChartInstance.destroy();
    const priorityCounts = tasks.reduce((acc, task) => { acc[task.priority] = (acc[task.priority] || 0) + 1; return acc; }, { 'High': 0, 'Medium': 0, 'Low': 0 });
    const ctx = document.getElementById('priorityChart')?.getContext('2d');
    if (!ctx) return;
    priorityChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(priorityCounts),
            datasets: [{ label: 'Task Count', data: Object.values(priorityCounts), backgroundColor: ['#ef4444', '#f59e0b', '#3b82f6'], borderRadius: 4 }]
        },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } } }
    });
}

// --- (All chat functions remain here, unchanged) ---
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
        const responseData = await response.json();
        const answer = responseData.answer;
        if (answer.output_type === 'visualization') {
            renderVisualizationMessage(answer.data);
        } else {
            appendMessage(formatTextResponse(answer.data), 'ai', true);
        }
    } catch (error) {
        appendMessage(`<p>Sorry, I encountered an error.</p>`, 'ai', true);
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
    const chartHtml = `<div class="chat-visualization"><h4>${chartData.title}</h4><div class="chart-wrapper-chat"><canvas id="${chartId}"></canvas></div></div>`;
    appendMessage(chartHtml, 'ai', true);
    setTimeout(() => {
        const ctx = document.getElementById(chartId)?.getContext('2d');
        if (!ctx) return;
        new Chart(ctx, {
            type: chartData.chart_type,
            data: { labels: chartData.labels, datasets: [{ label: chartData.title, data: chartData.values, backgroundColor: ['#4f46e5', '#f59e0b', '#10b981', '#ef4444', '#3b82f6', '#64748b'], borderColor: '#fff', borderWidth: chartData.chart_type === 'doughnut' ? 4 : 0, borderRadius: chartData.chart_type === 'bar' ? 4 : 0, }] },
            options: { responsive: true, maintainAspectRatio: false, indexAxis: chartData.chart_type === 'bar' ? 'y' : 'x', plugins: { legend: { display: chartData.chart_type !== 'bar', position: 'bottom' } }, scales: { x: { display: chartData.chart_type === 'bar', beginAtZero: true }, y: { display: chartData.chart_type === 'bar' } } }
        });
    }, 100);
}

function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'typing-indicator';
    indicator.className = 'chat-message ai';
    indicator.innerHTML = `<div class="typing-indicator"><span></span><span></span><span></span></div>`;
    chatBody.appendChild(indicator);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

function formatTextResponse(data) {
    let html = `<p>${data.introduction}</p>`;
    if (data.items && data.items.length > 0) {
        html += '<ul>' + data.items.map(item => `<li>${item}</li>`).join('') + '</ul>';
    }
    return html;
}

async function handleChatMessage(event) {
    event.preventDefault();
    const question = chatInput.value.trim();
    if (!question) return;

    appendMessage(question, 'user');
    chatInput.value = '';
    chatInput.disabled = true;
    showTypingIndicator();

    const user = JSON.parse(sessionStorage.getItem('user'));
    
    // --- ROUTING LOGIC ---
    const isManager = user.role === 'Manager';
    const endpoint = isManager ? `${API_BASE_URL}/manager-chat` : `${API_BASE_URL}/chat`;
    const body = isManager ? { question, manager_id: user.user_id } : { question, user_id: user.user_id };

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (!response.ok) throw new Error('Failed to get a response.');
        
        const responseData = await response.json();
        const answer = responseData.answer;

        if (answer.output_type === 'visualization') {
            renderVisualizationMessage(answer.data);
        } else {
            const htmlContent = formatTextResponse(answer.data); 
            appendMessage(htmlContent, 'ai', true);
        }

    } catch (error) {
        appendMessage('<p>Sorry, I encountered an error. Please try again.</p>', 'ai', true);
        console.error(error);
    } finally {
        removeTypingIndicator();
        chatInput.disabled = false;
        chatInput.focus();
    }
}

function renderVisualizationMessage(chartData) {
    if (!chartData || !chartData.values || chartData.values.length === 0) {
        appendMessage("<p>No data available to display a chart for this request.</p>", 'ai', true);
        return;
    }
    const chartId = `chart-${Date.now()}`;
    const chartHtml = `<div class="chat-visualization"><h4>${chartData.title}</h4><div class="chart-wrapper-chat"><canvas id="${chartId}"></canvas></div></div>`;
    appendMessage(chartHtml, 'ai', true);

    const chartColors = ['#4f46e5', '#f59e0b', '#10b981', '#ef4444', '#3b82f6', '#64748b', '#9333ea', '#facc15'];

    setTimeout(() => {
        const ctx = document.getElementById(chartId)?.getContext('2d');
        if (!ctx) return;
        
        // Dynamic options based on chart type
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { 
                    display: chartData.chart_type !== 'bar',
                    position: 'bottom' 
                } 
            },
        };

        if (chartData.chart_type === 'bar') {
            options.indexAxis = 'y'; // Make bar charts horizontal for readability
            options.scales = { x: { beginAtZero: true, ticks: { stepSize: 1 } } };
        }
        
        new Chart(ctx, {
            type: chartData.chart_type,
            data: { 
                labels: chartData.labels, 
                datasets: [{ 
                    label: chartData.title, 
                    data: chartData.values, 
                    backgroundColor: chartColors, 
                    borderColor: '#fff', 
                    borderWidth: chartData.chart_type === 'doughnut' ? 4 : 0, 
                    borderRadius: chartData.chart_type === 'bar' ? 4 : 0, 
                }] 
            },
            options: options
        });
    }, 100);
}


// --- INITIALIZE THE APP ---
init();
