/* ==========================================================================
   ALPR System v3.0 - Frontend Application State & Controllers
   ========================================================================== */

// Application State
const state = {
    user: null,
    detections: [],
    originalDetections: [],
    searchQuery: '',
    visibleColumns: [
        'plate_number',
        'confidence',
        'vehicle_make',
        'vehicle_model',
        'vehicle_color',
        'detection_date',
        'detection_time'
    ],
    sortBy: null,
    sortOrder: 'none' // 'asc', 'desc', 'none'
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
    deleteBtn: document.getElementById('delete-btn'),
    exportBtn: document.getElementById('export-btn'),
    
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

    // Delete Button Click (Admin only)
    dom.deleteBtn.addEventListener('click', async () => {
        const checkedBoxes = dom.tableBody.querySelectorAll('.row-checkbox:checked');
        if (checkedBoxes.length === 0) {
            alert('Please select at least one sighting to delete.');
            return;
        }

        const ids = Array.from(checkedBoxes).map(cb => parseInt(cb.value));
        const confirmMsg = `Are you sure you want to delete the ${ids.length} selected record(s) from the database? This action is permanent.`;
        if (!confirm(confirmMsg)) {
            return;
        }

        try {
            const response = await fetch('/api/detections/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids })
            });
            const data = await response.json();

            if (response.ok) {
                // Reset master checkbox if checked
                const selectAll = document.getElementById('select-all-checkbox');
                if (selectAll) selectAll.checked = false;
                
                fetchDetections();
            } else {
                alert(data.error || 'Failed to delete records.');
            }
        } catch (e) {
            console.error('Delete API call failed:', e);
            alert('Network error. Failed to reach server.');
        }
    });

    // Export Button Click (Admin & Viewer)
    dom.exportBtn.addEventListener('click', () => {
        const queryParams = new URLSearchParams();
        const checkedBoxes = dom.tableBody.querySelectorAll('.row-checkbox:checked');
        
        if (checkedBoxes.length > 0) {
            const ids = Array.from(checkedBoxes).map(cb => cb.value).join(',');
            queryParams.append('ids', ids);
        } else if (state.searchQuery) {
            queryParams.append('plate', state.searchQuery);
        }
        window.location.href = `/api/detections/export?${queryParams.toString()}`;
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

    // Image Zoom Click Toggle
    dom.modalImage.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent closing the modal
        toggleImageZoom(e);
    });

    // Image Panning on Mouse Move (when zoomed)
    const imgContainer = dom.modalImage.parentElement;
    if (imgContainer) {
        imgContainer.addEventListener('mousemove', (e) => {
            if (dom.modalImage.classList.contains('zoomed')) {
                const rect = imgContainer.getBoundingClientRect();
                const x = ((e.clientX - rect.left) / rect.width) * 100;
                const y = ((e.clientY - rect.top) / rect.height) * 100;
                dom.modalImage.style.transformOrigin = `${x}% ${y}%`;
            }
        });
    }
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
    
    // Toggle delete button visibility based on role (Admin only)
    if (user.role === 'admin') {
        dom.deleteBtn.classList.remove('hidden');
    } else {
        dom.deleteBtn.classList.add('hidden');
    }
    
    dom.loginView.classList.remove('active');
    dom.dashboardView.classList.add('active');
    
    fetchDetections();
}

function transitionToLogin() {
    state.user = null;
    state.detections = [];
    state.originalDetections = [];
    state.sortBy = null;
    state.sortOrder = 'none';
    dom.deleteBtn.classList.add('hidden');
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
    // Table always has a checkbox and "Thumbnail" as the first columns
    let html = '<th><input type="checkbox" id="select-all-checkbox"></th><th>Thumbnail</th>';
    state.visibleColumns.forEach(col => {
        const label = columnLabels[col] || col;
        let iconHtml = '<i class="fa-solid fa-sort sort-icon-disabled"></i>';
        
        if (state.sortBy === col) {
            if (state.sortOrder === 'asc') {
                iconHtml = '<i class="fa-solid fa-sort-up sort-icon-active"></i>';
            } else if (state.sortOrder === 'desc') {
                iconHtml = '<i class="fa-solid fa-sort-down sort-icon-active"></i>';
            }
        }
        
        html += `<th class="sortable-header" data-column="${col}">${label} ${iconHtml}</th>`;
    });
    dom.tableHeaders.innerHTML = html;
    
    // Bind event listener to the newly rendered select-all checkbox
    const selectAll = document.getElementById('select-all-checkbox');
    if (selectAll) {
        selectAll.checked = false;
        selectAll.addEventListener('change', (e) => {
            const checkboxes = dom.tableBody.querySelectorAll('.row-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = e.target.checked;
            });
        });
    }

    // Bind column sort click handlers
    const headers = dom.tableHeaders.querySelectorAll('.sortable-header');
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const col = header.dataset.column;
            handleSortClick(col);
        });
    });
}

function handleSortClick(col) {
    if (state.sortBy === col) {
        if (state.sortOrder === 'none') {
            state.sortOrder = 'asc';
        } else if (state.sortOrder === 'asc') {
            state.sortOrder = 'desc';
        } else {
            state.sortOrder = 'none';
            state.sortBy = null;
        }
    } else {
        state.sortBy = col;
        state.sortOrder = 'asc';
    }
    
    sortDetections();
    renderTableHeaders();
    renderTableBody();
}

function sortDetections() {
    if (!state.sortBy || state.sortOrder === 'none') {
        state.detections = [...state.originalDetections];
        return;
    }

    const col = state.sortBy;
    const isAsc = state.sortOrder === 'asc';

    state.detections.sort((a, b) => {
        // Special case: Sighting Date (sort time in same direction if date is equal)
        if (col === 'detection_date') {
            const dateA = a.detection_date || '';
            const dateB = b.detection_date || '';
            if (dateA !== dateB) {
                return isAsc ? dateA.localeCompare(dateB) : dateB.localeCompare(dateA);
            }
            const timeA = a.detection_time || '';
            const timeB = b.detection_time || '';
            return isAsc ? timeA.localeCompare(timeB) : timeB.localeCompare(timeA);
        }

        // Special case: Sighting Time (sort date in same direction if time is equal)
        if (col === 'detection_time') {
            const timeA = a.detection_time || '';
            const timeB = b.detection_time || '';
            if (timeA !== timeB) {
                return isAsc ? timeA.localeCompare(timeB) : timeB.localeCompare(timeA);
            }
            const dateA = a.detection_date || '';
            const dateB = b.detection_date || '';
            return isAsc ? dateA.localeCompare(dateB) : dateB.localeCompare(dateA);
        }

        // Default sorting for other columns
        let valA = a[col];
        let valB = b[col];

        // Handle numeric sorting for confidence
        if (col === 'confidence') {
            const numA = valA !== null && valA !== undefined ? parseFloat(valA) : -1;
            const numB = valB !== null && valB !== undefined ? parseFloat(valB) : -1;
            return isAsc ? numA - numB : numB - numA;
        }

        // Fallback to string sorting
        const strA = (valA !== null && valA !== undefined ? valA : '').toString().toLowerCase();
        const strB = (valB !== null && valB !== undefined ? valB : '').toString().toLowerCase();
        return isAsc ? strA.localeCompare(strB) : strB.localeCompare(strA);
    });
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
        dom.tableBody.innerHTML = `<tr><td colspan="${state.visibleColumns.length + 2}" class="text-center">Loading sightings database...</td></tr>`;
        
        const response = await fetch(`/api/detections?${params.toString()}`);
        if (!response.ok) {
            if (response.status === 401) {
                transitionToLogin();
                return;
            }
            throw new Error('Server returned error status');
        }
        
        const data = await response.json();
        state.originalDetections = data;
        sortDetections();
        renderTableBody();
    } catch (e) {
        console.error('Failed to load database logs:', e);
        dom.tableBody.innerHTML = `<tr><td colspan="${state.visibleColumns.length + 2}" class="text-center" style="color: var(--color-danger);"><i class="fa-solid fa-circle-xmark"></i> Failed to query database logs.</td></tr>`;
    }
}

function renderTableBody() {
    if (state.detections.length === 0) {
        dom.tableBody.innerHTML = `<tr><td colspan="${state.visibleColumns.length + 2}" class="text-center">No sightings found matching filters.</td></tr>`;
        return;
    }
    
    // Reset select-all checkbox when reloading content
    const selectAll = document.getElementById('select-all-checkbox');
    if (selectAll) selectAll.checked = false;
    
    let html = '';
    state.detections.forEach(item => {
        html += `<tr class="table-row-hover">`;
        
        // 0. Row Selection Checkbox
        html += `
            <td>
                <input type="checkbox" class="row-checkbox" value="${item.id}" onclick="event.stopPropagation()">
            </td>
        `;
        
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
    resetImageZoom();
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
    resetImageZoom();
}

// --- IMAGE ZOOM HELPER FUNCTIONS ---

function toggleImageZoom(e) {
    if (dom.modalImage.classList.contains('zoomed')) {
        resetImageZoom();
    } else {
        dom.modalImage.classList.add('zoomed');
        // Set initial zoom origin on click coordinate
        const container = dom.modalImage.parentElement;
        if (container) {
            const rect = container.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            dom.modalImage.style.transformOrigin = `${x}% ${y}%`;
        }
    }
}

function resetImageZoom() {
    dom.modalImage.classList.remove('zoomed');
    dom.modalImage.style.transform = '';
    dom.modalImage.style.transformOrigin = '';
}
