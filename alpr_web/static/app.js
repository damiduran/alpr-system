/* ==========================================================================
   ALPR System v3.0 - Frontend Application State & Controllers
   ========================================================================== */

// Application State
const state = {
    user: null,
    detections: [],
    searchQuery: '',
    visibleColumns: [
        'plate_number',
        'confidence',
        'vehicle_make',
        'vehicle_model',
        'vehicle_color',
        'detection_date',
        'detection_time'
    ]
};

// Column Label Map
const columnLabels = {
    'plate_number': 'Plate Number',
    'confidence': 'Confidence',
    'vehicle_make': 'Make',
    'vehicle_model': 'Model',
    'vehicle_color': 'Color',
    'body_type': 'Body Type',
    'orientation': 'Orientation',
    'year': 'Year',
    'detection_date': 'Sighting Date',
    'detection_time': 'Sighting Time'
};

// DOM Elements Cache
const dom = {
    loginView: document.getElementById('login-view'),
    dashboardView: document.getElementById('dashboard-view'),
    loginForm: document.getElementById('login-form'),
    usernameInput: document.getElementById('username'),
    passwordInput: document.getElementById('password'),
    loginError: document.getElementById('login-error'),
    errorText: document.getElementById('error-text'),
    
    usernameDisplay: document.getElementById('username-display'),
    userBadge: document.getElementById('user-badge'),
    logoutBtn: document.getElementById('logout-btn'),
    
    searchPlate: document.getElementById('search-plate'),
    refreshBtn: document.getElementById('refresh-btn'),
    colSelectorTrigger: document.getElementById('col-selector-trigger'),
    colSelectorDropdown: document.getElementById('col-selector-dropdown'),
    checkboxGroup: document.querySelector('.checkbox-group'),
    
    tableHeaders: document.getElementById('table-headers'),
    tableBody: document.getElementById('table-body'),
    
    imageModal: document.getElementById('image-modal'),
    modalImage: document.getElementById('modal-image'),
    modalLoading: document.getElementById('modal-loading'),
    modalPlate: document.getElementById('modal-plate'),
    modalConfidence: document.getElementById('modal-confidence'),
    modalVehicle: document.getElementById('modal-vehicle'),
    modalTimestamp: document.getElementById('modal-timestamp'),
    modalClose: document.querySelector('.modal-close')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    checkSession();
    registerEventListeners();
    initColumnCheckboxes();
});

// --- AUTHENTICATION FLOWS ---

async function checkSession() {
    try {
        const response = await fetch('/api/auth/me');
        const data = await response.json();
        
        if (data.authenticated) {
            transitionToDashboard(data.user);
        } else {
            transitionToLogin();
        }
    } catch (e) {
        console.error('Session check failed:', e);
        transitionToLogin();
    }
}

function registerEventListeners() {
    // Login Submit
    dom.loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        dom.loginError.classList.add('hidden');
        
        const username = dom.usernameInput.value;
        const password = dom.passwordInput.value;
        
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();
            
            if (response.ok) {
                dom.passwordInput.value = '';
                transitionToDashboard(data.user);
            } else {
                showLoginError(data.error || 'Authentication failed');
            }
        } catch (err) {
            showLoginError('Network error. Cannot reach server.');
        }
    });

    // Logout Click
    dom.logoutBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
            transitionToLogin();
        } catch (e) {
            console.error('Logout failed:', e);
        }
    });

    // Toggle Column Dropdown
    dom.colSelectorTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        dom.colSelectorDropdown.classList.toggle('hidden');
    });

    // Hide Dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!dom.colSelectorDropdown.classList.contains('hidden') && 
            !dom.colSelectorDropdown.contains(e.target) && 
            e.target !== dom.colSelectorTrigger) {
            dom.colSelectorDropdown.classList.add('hidden');
        }
    });

    // Search input (debounced)
    let searchDebounceTimeout;
    dom.searchPlate.addEventListener('input', () => {
        clearTimeout(searchDebounceTimeout);
        searchDebounceTimeout = setTimeout(() => {
            state.searchQuery = dom.searchPlate.value.trim();
            fetchDetections();
        }, 300); // 300ms delay
    });

    // Refresh Button Click
    dom.refreshBtn.addEventListener('click', () => {
        fetchDetections();
    });

    // Image Modal Close
    dom.modalClose.addEventListener('click', () => closeModal());
    dom.imageModal.addEventListener('click', (e) => {
        if (e.target === dom.imageModal) closeModal();
    });
    
    // Close Modal on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

function showLoginError(message) {
    dom.errorText.innerText = message;
    dom.loginError.classList.remove('hidden');
}

function transitionToDashboard(user) {
    state.user = user;
    dom.usernameDisplay.innerText = user.username;
    
    // Set role badge styles
    dom.userBadge.innerText = user.role;
    dom.userBadge.className = `role-badge ${user.role}`;
    
    dom.loginView.classList.remove('active');
    dom.dashboardView.classList.add('active');
    
    fetchDetections();
}

function transitionToLogin() {
    state.user = null;
    state.detections = [];
    dom.dashboardView.classList.remove('active');
    dom.loginView.classList.add('active');
}

// --- COLUMN SELECTOR LOGIC ---

function initColumnCheckboxes() {
    const checkboxes = dom.checkboxGroup.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => {
        // Set checked status based on initial state
        cb.checked = state.visibleColumns.includes(cb.value);
        
        // Listen for checkbox updates
        cb.addEventListener('change', () => {
            const checkedValues = [];
            checkboxes.forEach(c => {
                if (c.checked) checkedValues.push(c.value);
            });
            state.visibleColumns = checkedValues;
            
            // Re-render table structure and fetch filtered data
            renderTableHeaders();
            fetchDetections();
        });
    });
    renderTableHeaders();
}

function renderTableHeaders() {
    // Table always has "Thumbnail" as the first column
    let html = '<th>Thumbnail</th>';
    state.visibleColumns.forEach(col => {
        const label = columnLabels[col] || col;
        html += `<th>${label}</th>`;
    });
    dom.tableHeaders.innerHTML = html;
}

// --- DATA FETCHING & RENDER ---

async function fetchDetections() {
    if (!state.user) return;
    
    // Construct query parameters
    const params = new URLSearchParams();
    if (state.searchQuery) {
        params.append('plate', state.searchQuery);
    }
    
    // Select specific columns to reduce data transfer
    if (state.visibleColumns.length > 0) {
        params.append('columns', state.visibleColumns.join(','));
    }
    
    try {
        dom.tableBody.innerHTML = `<tr><td colspan="${state.visibleColumns.length + 1}" class="text-center">Loading sightings database...</td></tr>`;
        
        const response = await fetch(`/api/detections?${params.toString()}`);
        if (!response.ok) {
            if (response.status === 401) {
                transitionToLogin();
                return;
            }
            throw new Error('Server returned error status');
        }
        
        const data = await response.json();
        state.detections = data;
        renderTableBody();
    } catch (e) {
        console.error('Failed to load database logs:', e);
        dom.tableBody.innerHTML = `<tr><td colspan="${state.visibleColumns.length + 1}" class="text-center" style="color: var(--color-danger);"><i class="fa-solid fa-circle-xmark"></i> Failed to query database logs.</td></tr>`;
    }
}

function renderTableBody() {
    if (state.detections.length === 0) {
        dom.tableBody.innerHTML = `<tr><td colspan="${state.visibleColumns.length + 1}" class="text-center">No sightings found matching filters.</td></tr>`;
        return;
    }
    
    let html = '';
    state.detections.forEach(item => {
        html += `<tr class="table-row-hover">`;
        
        // 1. Thumbnail rendering
        if (item.file_id) {
            html += `
                <td>
                    <div class="vehicle-thumbnail" onclick="openModal('${item.file_id}', ${item.id})">
                        <img src="/api/media/thumbnail/${item.file_id}" alt="Vehicle" loading="lazy">
                    </div>
                </td>
            `;
        } else {
            html += `
                <td>
                    <div class="vehicle-thumbnail no-image">
                        <i class="fa-solid fa-car" style="color: var(--color-text-dim); font-size: 1.2rem; display: flex; align-items: center; justify-content: center; height: 100%;"></i>
                    </div>
                </td>
            `;
        }
        
        // 2. Visible Columns rendering
        state.visibleColumns.forEach(col => {
            let val = item[col];
            if (val === undefined || val === null || val === '') {
                val = '<span style="color: var(--color-text-dim);">---</span>';
            }
            
            // Format column values for aesthetics
            if (col === 'plate_number' && item[col]) {
                html += `<td><span class="plate-badge">${item[col]}</span></td>`;
            } else if (col === 'confidence' && item[col] !== null) {
                const conf = parseFloat(item[col]);
                let confClass = 'conf-low';
                if (conf >= 90) confClass = 'conf-high';
                else if (conf >= 75) confClass = 'conf-med';
                html += `<td><span class="${confClass}">${conf.toFixed(1)}%</span></td>`;
            } else if (col === 'vehicle_make' || col === 'vehicle_model' || col === 'vehicle_color') {
                // Capitalize first letters for cleaner display
                const capVal = typeof val === 'string' ? val.charAt(0).toUpperCase() + val.slice(1) : val;
                html += `<td>${capVal}</td>`;
            } else {
                html += `<td>${val}</td>`;
            }
        });
        
        html += `</tr>`;
    });
    
    dom.tableBody.innerHTML = html;
}

// --- IMAGE MODAL CONTROLLERS ---

function openModal(fileId, recordId) {
    // Find record details in local cache
    const item = state.detections.find(d => d.id === recordId);
    if (!item) return;
    
    // Set text elements
    dom.modalPlate.innerText = item.plate_number || 'UNKNOWN';
    
    const confidence = item.confidence ? parseFloat(item.confidence) : null;
    dom.modalConfidence.innerText = confidence ? `${confidence.toFixed(1)}%` : '---';
    dom.modalConfidence.className = ''; // reset class
    if (confidence) {
        if (confidence >= 90) dom.modalConfidence.classList.add('conf-high');
        else if (confidence >= 75) dom.modalConfidence.classList.add('conf-med');
        else dom.modalConfidence.classList.add('conf-low');
    }
    
    // Format specs make/model/color/year
    const specs = [];
    if (item.vehicle_color) specs.push(item.vehicle_color.charAt(0).toUpperCase() + item.vehicle_color.slice(1));
    if (item.vehicle_make) specs.push(item.vehicle_make.charAt(0).toUpperCase() + item.vehicle_make.slice(1));
    if (item.vehicle_model) specs.push(item.vehicle_model.charAt(0).toUpperCase() + item.vehicle_model.slice(1));
    if (item.year) specs.push(item.year);
    dom.modalVehicle.innerText = specs.length > 0 ? specs.join(' ') : '---';
    
    // Format date & time
    const timeInfo = [];
    if (item.detection_date) timeInfo.push(item.detection_date);
    if (item.detection_time) timeInfo.push(item.detection_time);
    dom.modalTimestamp.innerText = timeInfo.length > 0 ? timeInfo.join(' at ') : '---';
    
    // Show modal
    dom.imageModal.classList.add('active');
    dom.modalLoading.style.display = 'block';
    dom.modalImage.style.opacity = '0';
    
    // Set source image path
    dom.modalImage.src = `/api/media/full/${fileId}`;
    
    dom.modalImage.onload = () => {
        dom.modalLoading.style.display = 'none';
        dom.modalImage.style.opacity = '1';
        dom.modalImage.style.transition = 'opacity 0.3s ease';
    };
    
    dom.modalImage.onerror = () => {
        dom.modalLoading.style.display = 'none';
        dom.modalImage.alt = 'Failed to load high-resolution image.';
    };
}

function closeModal() {
    dom.imageModal.classList.remove('active');
    dom.modalImage.src = '';
}
