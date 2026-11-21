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
    googleSigninBtn: document.getElementById('google-signin-btn'),
    webviewWarning: document.getElementById('webview-warning'),
    loginWarning: document.getElementById('login-warning'),
    loginLoading: document.getElementById('login-loading'),
    loginError: document.getElementById('login-error'),
    errorText: document.getElementById('error-text'),
    
    mobileMenuBtn: document.getElementById('mobile-menu-btn'),
    headerRight: document.getElementById('header-right'),
    usernameDisplay: document.getElementById('username-display'),
    userBadge: document.getElementById('user-badge'),
    logoutBtn: document.getElementById('logout-btn'),
    usersBtn: document.getElementById('users-btn'),
    usersPanel: document.getElementById('users-panel'),
    closeUsersBtn: document.getElementById('close-users-btn'),
    addUserForm: document.getElementById('add-user-form'),
    newUserEmail: document.getElementById('new-user-email'),
    newUserTelegram: document.getElementById('new-user-telegram'),
    newUserRole: document.getElementById('new-user-role'),
    userMgmtMsg: document.getElementById('user-mgmt-msg'),
    usersTableBody: document.getElementById('users-table-body'),
    deleteBtn: document.getElementById('delete-btn'),
    exportBtn: document.getElementById('export-btn'),
    
    searchPlate: document.getElementById('search-plate'),
    refreshBtn: document.getElementById('refresh-btn'),
    colSelectorTrigger: document.getElementById('col-selector-trigger'),
    colSelectorDropdown: document.getElementById('col-selector-dropdown'),
    checkboxGroup: document.querySelector('.checkbox-group'),
    
    tableHeaders: document.getElementById('table-headers'),
    tableBody: document.getElementById('table-body'),
    mobileCardsContainer: document.getElementById('mobile-cards-container'),
    
    imageModal: document.getElementById('image-modal'),
    modalImage: document.getElementById('modal-image'),
    modalLoading: document.getElementById('modal-loading'),
    modalPlate: document.getElementById('modal-plate'),
    modalConfidence: document.getElementById('modal-confidence'),
    modalVehicle: document.getElementById('modal-vehicle'),
    modalTimestamp: document.getElementById('modal-timestamp'),
    modalClose: document.querySelector('.modal-close')
};

let gsiInitialized = false;
let gsiClientIdCache = '';
let lastRenderedGoogleBtnWidth = 0;

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    detectRestrictedWebview();
    initGoogleSignIn();
    checkSession();
    registerEventListeners();
    initColumnCheckboxes();
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').catch(() => {});
    }
});

function detectRestrictedWebview() {
    const ua = navigator.userAgent || '';
    if (/FBAN|FBAV|Instagram|Line\/|MicroMessenger|Snapchat/i.test(ua) && dom.webviewWarning) {
        dom.webviewWarning.classList.remove('hidden');
    }
}

// --- AUTHENTICATION FLOWS (Google OAuth 2.0) ---

async function initGoogleSignIn() {
    try {
        const res = await fetch('/api/auth/config');
        const cfg = await res.json();
        const clientId = (cfg.google_client_id || '').trim();
        if (!clientId) {
            if (dom.loginWarning) dom.loginWarning.classList.remove('hidden');
            return;
        }
        gsiClientIdCache = clientId;
        renderGoogleButtonWithRetry(clientId, 0);
    } catch (e) {
        console.error('Failed to fetch Google Auth config:', e);
    }
}

function computeGoogleButtonWidth() {
    const container = dom.googleSigninBtn;
    const available = container ? Math.floor(container.getBoundingClientRect().width) : Math.floor(window.innerWidth - 72);
    return Math.max(220, Math.min(340, available || 280));
}

function renderResponsiveGoogleButton() {
    if (!dom.googleSigninBtn || !window.google || !window.google.accounts || !window.google.accounts.id) return;
    const width = computeGoogleButtonWidth();
    if (Math.abs(width - lastRenderedGoogleBtnWidth) < 8 && lastRenderedGoogleBtnWidth > 0) return;
    lastRenderedGoogleBtnWidth = width;
    dom.googleSigninBtn.innerHTML = '';
    window.google.accounts.id.renderButton(dom.googleSigninBtn, {
        theme: 'outline',
        size: 'large',
        width: width,
        text: 'signin_with',
        shape: 'rectangular',
        logo_alignment: 'left'
    });
}

function renderGoogleButtonWithRetry(clientId, attempt) {
    if (window.google && window.google.accounts && window.google.accounts.id) {
        if (!gsiInitialized) {
            window.google.accounts.id.initialize({
                client_id: clientId,
                callback: handleGoogleCredentialResponse,
                context: 'signin',
                ux_mode: 'popup',
                auto_select: false,
                itp_support: true,
                use_fedcm_for_prompt: true
            });
            gsiInitialized = true;
        }
        renderResponsiveGoogleButton();
    } else if (attempt < 25) {
        setTimeout(() => renderGoogleButtonWithRetry(clientId, attempt + 1), 200);
    }
}

let googleBtnResizeTimer;
window.addEventListener('resize', () => {
    if (!gsiInitialized || !dom.loginView || !dom.loginView.classList.contains('active')) return;
    clearTimeout(googleBtnResizeTimer);
    googleBtnResizeTimer = setTimeout(renderResponsiveGoogleButton, 180);
});

async function handleGoogleCredentialResponse(response) {
    dom.loginError.classList.add('hidden');
    if (dom.loginLoading) dom.loginLoading.classList.remove('hidden');
    if (dom.googleSigninBtn) dom.googleSigninBtn.classList.add('hidden');

    try {
        const res = await fetch('/api/auth/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential: response.credential })
        });
        const data = await res.json();

        if (res.ok) {
            transitionToDashboard(data.user);
        } else {
            showLoginError(data.error || 'Authentication failed. Access denied.');
        }
    } catch (err) {
        showLoginError('Network error. Cannot reach server.');
    } finally {
        if (dom.loginLoading) dom.loginLoading.classList.add('hidden');
        if (dom.googleSigninBtn) dom.googleSigninBtn.classList.remove('hidden');
    }
}

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

function closeMobileNav() {
    if (!dom.headerRight || !dom.mobileMenuBtn) return;
    dom.headerRight.classList.remove('open');
    dom.mobileMenuBtn.setAttribute('aria-expanded', 'false');
    dom.mobileMenuBtn.innerHTML = '<i class="fa-solid fa-bars"></i>';
}

function getSelectedDetectionIds() {
    const tableChecked = dom.tableBody ? Array.from(dom.tableBody.querySelectorAll('.row-checkbox:checked')) : [];
    const cardChecked = dom.mobileCardsContainer ? Array.from(dom.mobileCardsContainer.querySelectorAll('.mobile-row-checkbox:checked')) : [];
    const idSet = new Set();
    [...tableChecked, ...cardChecked].forEach(cb => {
        const parsed = parseInt(cb.value, 10);
        if (!Number.isNaN(parsed)) idSet.add(parsed);
    });
    return Array.from(idSet);
}

function syncRowCheckbox(id, checked) {
    if (dom.tableBody) {
        const tCb = dom.tableBody.querySelector(`.row-checkbox[value="${id}"]`);
        if (tCb) tCb.checked = checked;
    }
    if (dom.mobileCardsContainer) {
        const cCb = dom.mobileCardsContainer.querySelector(`.mobile-row-checkbox[value="${id}"]`);
        if (cCb) cCb.checked = checked;
    }
}

function registerEventListeners() {
    // Mobile Navigation Menu Toggle
    if (dom.mobileMenuBtn && dom.headerRight) {
        dom.mobileMenuBtn.addEventListener('click', () => {
            const isOpen = dom.headerRight.classList.toggle('open');
            dom.mobileMenuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            dom.mobileMenuBtn.innerHTML = isOpen
                ? '<i class="fa-solid fa-xmark"></i>'
                : '<i class="fa-solid fa-bars"></i>';
        });
    }

    // Logout Click
    dom.logoutBtn.addEventListener('click', async () => {
        try {
            closeMobileNav();
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

    // Admin Users & Permissions Toggle (Admin only - Tier 3)
    if (dom.usersBtn) {
        dom.usersBtn.addEventListener('click', () => {
            dom.usersPanel.classList.toggle('hidden');
            if (!dom.usersPanel.classList.contains('hidden')) {
                fetchAuthorizedUsers();
            }
        });
    }

    if (dom.closeUsersBtn) {
        dom.closeUsersBtn.addEventListener('click', () => {
            dom.usersPanel.classList.add('hidden');
        });
    }

    if (dom.addUserForm) {
        dom.addUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = dom.newUserEmail.value.trim();
            const role = dom.newUserRole.value;
            const telegramId = dom.newUserTelegram ? dom.newUserTelegram.value.trim() : '';
            if (!email) return;
            await saveUserPermission(email, role, telegramId, true);
        });
    }

    // Delete Button Click (Admin / Manager)
    dom.deleteBtn.addEventListener('click', async () => {
        const ids = getSelectedDetectionIds();
        if (ids.length === 0) {
            alert('Please select at least one sighting to delete.');
            return;
        }
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
        const selectedIds = getSelectedDetectionIds();
        
        if (selectedIds.length > 0) {
            queryParams.append('ids', selectedIds.join(','));
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

    // Image Panning on Mouse Move & Touch Move (when zoomed)
    const imgContainer = dom.modalImage.parentElement;
    if (imgContainer) {
        const updatePanOrigin = (clientX, clientY) => {
            if (!dom.modalImage.classList.contains('zoomed')) return;
            const rect = imgContainer.getBoundingClientRect();
            const x = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
            const y = Math.max(0, Math.min(100, ((clientY - rect.top) / rect.height) * 100));
            dom.modalImage.style.transformOrigin = `${x}% ${y}%`;
        };

        imgContainer.addEventListener('mousemove', (e) => {
            updatePanOrigin(e.clientX, e.clientY);
        });

        imgContainer.addEventListener('touchmove', (e) => {
            if (dom.modalImage.classList.contains('zoomed') && e.touches.length === 1) {
                e.preventDefault();
                updatePanOrigin(e.touches[0].clientX, e.touches[0].clientY);
            }
        }, { passive: false });
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
    
    // Toggle delete button visibility based on role (Manager & Admin: Tier 2 & Tier 3)
    if (user.role === 'admin' || user.role === 'manager') {
        dom.deleteBtn.classList.remove('hidden');
    } else {
        dom.deleteBtn.classList.add('hidden');
    }

    // Toggle Users & Permissions button based on role (Admin only: Tier 3)
    if (dom.usersBtn) {
        if (user.role === 'admin') {
            dom.usersBtn.classList.remove('hidden');
        } else {
            dom.usersBtn.classList.add('hidden');
            if (dom.usersPanel) dom.usersPanel.classList.add('hidden');
        }
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
    if (dom.usersBtn) dom.usersBtn.classList.add('hidden');
    if (dom.usersPanel) dom.usersPanel.classList.add('hidden');
    dom.dashboardView.classList.remove('active');
    dom.loginView.classList.add('active');
    closeMobileNav();
    if (gsiInitialized) {
        lastRenderedGoogleBtnWidth = 0;
        requestAnimationFrame(renderResponsiveGoogleButton);
    }
}

// --- ADMIN USER & PERMISSION MANAGEMENT (TIER 3) ---

function showUserMgmtFeedback(text, isError = false) {
    if (!dom.userMgmtMsg) return;
    dom.userMgmtMsg.innerText = text;
    dom.userMgmtMsg.className = `user-mgmt-msg ${isError ? 'error' : 'success'}`;
    dom.userMgmtMsg.classList.remove('hidden');
    setTimeout(() => {
        dom.userMgmtMsg.classList.add('hidden');
    }, 4000);
}

async function fetchAuthorizedUsers() {
    if (!state.user || state.user.role !== 'admin') return;
    try {
        const res = await fetch('/api/users');
        if (!res.ok) throw new Error('Failed to load users');
        const users = await res.json();
        renderAuthorizedUsers(users);
    } catch (e) {
        console.error('Error fetching users:', e);
        if (dom.usersTableBody) {
            dom.usersTableBody.innerHTML = `<tr><td colspan="4" class="text-center" style="color: var(--color-danger);">Failed to load user list.</td></tr>`;
        }
    }
}

function renderAuthorizedUsers(users) {
    if (!dom.usersTableBody) return;
    if (!users || users.length === 0) {
        dom.usersTableBody.innerHTML = `<tr><td colspan="5" class="text-center">No authorized users found.</td></tr>`;
        return;
    }

    const currentEmail = (state.user && state.user.username || '').toLowerCase();
    let html = '';
    users.forEach(u => {
        const isSelf = u.email.toLowerCase() === currentEmail;
        const tgVal = u.telegram_id || '';
        html += `
            <tr>
                <td>
                    <strong>${u.email}</strong>
                    ${isSelf ? '<span class="role-badge admin" style="margin-left:8px;">You</span>' : ''}
                </td>
                <td>
                    <select class="role-select role-select-inline" onchange="saveUserPermission('${u.email}', this.value, null, false)" ${isSelf ? 'disabled title="You cannot demote your own active Admin account"' : ''}>
                        <option value="viewer" ${u.role === 'viewer' ? 'selected' : ''}>VIEWER</option>
                        <option value="manager" ${u.role === 'manager' ? 'selected' : ''}>MANAGER</option>
                        <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>ADMIN</option>
                    </select>
                </td>
                <td>
                    <div class="tg-inline-group">
                        <input
                            type="text"
                            class="tg-inline-input"
                            value="${tgVal}"
                            placeholder="Not linked"
                            inputmode="numeric"
                            onkeydown="if(event.key==='Enter'){event.preventDefault(); this.blur();}"
                            onchange="saveUserPermission('${u.email}', '${u.role}', this.value.trim(), false)"
                        >
                    </div>
                </td>
                <td>${u.added_at || '---'}</td>
                <td class="text-right">
                    ${isSelf ? '<span style="color: var(--color-text-dim); font-size: 0.8rem;">Active Admin</span>' : `
                        <button class="btn btn-danger btn-sm" onclick="removeAuthorizedUser('${u.email}')">
                            <i class="fa-solid fa-user-minus"></i> <span>Remove</span>
                        </button>
                    `}
                </td>
            </tr>
        `;
    });
    dom.usersTableBody.innerHTML = html;
}

async function saveUserPermission(email, role, telegramId = null, clearInput = false) {
    try {
        const payload = { email, role };
        if (telegramId !== null && telegramId !== undefined) {
            payload.telegram_id = telegramId;
        }
        const res = await fetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            if (clearInput) {
                if (dom.newUserEmail) dom.newUserEmail.value = '';
                if (dom.newUserTelegram) dom.newUserTelegram.value = '';
            }
            showUserMgmtFeedback(data.message || 'User permissions updated.', false);
            if (data.users) renderAuthorizedUsers(data.users);
            else fetchAuthorizedUsers();
        } else {
            showUserMgmtFeedback(data.error || 'Failed to update user.', true);
            fetchAuthorizedUsers();
        }
    } catch (e) {
        showUserMgmtFeedback('Network error updating user permissions.', true);
    }
}

async function removeAuthorizedUser(email) {
    if (!confirm(`Remove dashboard access for ${email}?`)) return;
    try {
        const res = await fetch('/api/users', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (res.ok) {
            showUserMgmtFeedback(data.message || `Removed ${email}`, false);
            if (data.users) renderAuthorizedUsers(data.users);
            else fetchAuthorizedUsers();
        } else {
            showUserMgmtFeedback(data.error || 'Failed to remove user.', true);
        }
    } catch (e) {
        showUserMgmtFeedback('Network error removing user.', true);
    }
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
            if (dom.mobileCardsContainer) {
                dom.mobileCardsContainer.querySelectorAll('.mobile-row-checkbox').forEach(cb => {
                    cb.checked = e.target.checked;
                });
            }
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
        if (dom.mobileCardsContainer) {
            dom.mobileCardsContainer.innerHTML = `<div class="mobile-card-empty">Loading sightings database...</div>`;
        }
        
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
        if (dom.mobileCardsContainer) {
            dom.mobileCardsContainer.innerHTML = `<div class="mobile-card-empty" style="color: var(--color-danger);"><i class="fa-solid fa-circle-xmark"></i> Failed to query database logs.</div>`;
        }
    }
}

function renderTableBody() {
    if (state.detections.length === 0) {
        dom.tableBody.innerHTML = `<tr><td colspan="${state.visibleColumns.length + 2}" class="text-center">No sightings found matching filters.</td></tr>`;
        if (dom.mobileCardsContainer) {
            dom.mobileCardsContainer.innerHTML = `<div class="mobile-card-empty">No sightings found matching filters.</div>`;
        }
        return;
    }
    
    // Reset select-all checkbox when reloading content
    const selectAll = document.getElementById('select-all-checkbox');
    if (selectAll) selectAll.checked = false;
    
    let html = '';
    let cardsHtml = '';
    state.detections.forEach(item => {
        html += `<tr class="table-row-hover">`;
        
        // 0. Row Selection Checkbox
        html += `
            <td>
                <input type="checkbox" class="row-checkbox" value="${item.id}" onchange="syncRowCheckbox(${item.id}, this.checked)" onclick="event.stopPropagation()">
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

        // 3. Synchronized Mobile Card rendering (<= 768px)
        const plateText = item.plate_number || 'UNKNOWN';
        const confVal = (item.confidence !== null && item.confidence !== undefined) ? parseFloat(item.confidence) : null;
        let confBadgeHtml = '';
        if (confVal !== null && !Number.isNaN(confVal)) {
            const confClass = confVal >= 90 ? 'conf-high' : (confVal >= 75 ? 'conf-med' : 'conf-low');
            confBadgeHtml = `<span class="${confClass}">${confVal.toFixed(1)}%</span>`;
        }

        const specParts = [];
        ['vehicle_color', 'vehicle_make', 'vehicle_model', 'year', 'body_type'].forEach(field => {
            if (item[field]) {
                const s = String(item[field]);
                specParts.push(s.charAt(0).toUpperCase() + s.slice(1));
            }
        });
        const specsText = specParts.length > 0 ? specParts.join(' · ') : 'Vehicle details unavailable';

        const thumbHtml = item.file_id
            ? `<div class="vehicle-thumbnail sighting-card-thumb" onclick="openModal('${item.file_id}', ${item.id})"><img src="/api/media/thumbnail/${item.file_id}" alt="Vehicle" loading="lazy"></div>`
            : `<div class="vehicle-thumbnail sighting-card-thumb no-image"><i class="fa-solid fa-car" style="color: var(--color-text-dim); font-size: 1.35rem; display: flex; align-items: center; justify-content: center; height: 100%;"></i></div>`;

        const cardOpenAttr = item.file_id ? `onclick="openModal('${item.file_id}', ${item.id})"` : '';

        cardsHtml += `
            <article class="sighting-card">
                <div class="sighting-card-check">
                    <input type="checkbox" class="mobile-row-checkbox" value="${item.id}" aria-label="Select sighting ${plateText}" onchange="syncRowCheckbox(${item.id}, this.checked)" onclick="event.stopPropagation()">
                </div>
                ${thumbHtml}
                <div class="sighting-card-body" ${cardOpenAttr}>
                    <div class="sighting-card-top">
                        <span class="plate-badge">${plateText}</span>
                        ${confBadgeHtml}
                    </div>
                    <div class="sighting-card-specs">${specsText}</div>
                    <div class="sighting-card-meta">
                        ${item.detection_date ? `<span><i class="fa-regular fa-calendar"></i>${item.detection_date}</span>` : ''}
                        ${item.detection_time ? `<span><i class="fa-regular fa-clock"></i>${item.detection_time}</span>` : ''}
                    </div>
                </div>
            </article>
        `;
    });
    
    dom.tableBody.innerHTML = html;
    if (dom.mobileCardsContainer) {
        dom.mobileCardsContainer.innerHTML = cardsHtml;
    }
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
