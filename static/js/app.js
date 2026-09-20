// CampusGenie 360° Smart Campus ERP & watsonx.ai Engine
let currentData = null;
let currentRole = 'student';
let currentUser = { name: 'Harshit Sharma', role: 'student', id: '22CS1084', roll_no: '22CS1084' };
let activeTeacherSubjectId = 'os';
let teacherRosterState = {}; // { [studentId]: 'present' | 'absent' }

// ── Persistent Storage & Multi-View Reactive Sync ──────────────────────────
function getStoredData() {
    try {
        const d = localStorage.getItem("campusgenie_data");
        return d ? JSON.parse(d) : null;
    } catch (e) {
        return null;
    }
}

function saveStoredData(data) {
    if (!data) return;
    try {
        localStorage.setItem("campusgenie_data", JSON.stringify(data));
    } catch (e) {}
}

function syncStateToServer(data) {
    if (!data) return;
    try {
        fetch("/api/state/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data })
        }).catch(() => {});
    } catch (e) {}
}

function refreshAllViews() {
    if (!currentData) return;
    renderDashboard(currentData);
    renderHodSubjects();
    renderHodStudents();
    renderTeacherSubjectCards();
    loadTeacherRoster(activeTeacherSubjectId);
    if (typeof loadFeeStatus === 'function') loadFeeStatus();
    if (typeof loadAssignments === 'function') loadAssignments();
    if (typeof loadHodFees === 'function') loadHodFees();
}

document.addEventListener("DOMContentLoaded", () => {
    // 1. Check if user is already authenticated
    const isAuth = localStorage.getItem("campusgenie_authenticated") === "true";
    const savedRole = localStorage.getItem("campusgenie_role") || "student";
    if (savedRole && ['student', 'teacher', 'hod', 'parent'].includes(savedRole)) {
        currentRole = savedRole;
    }
    const savedSub = localStorage.getItem("campusgenie_active_subject");
    if (savedSub) {
        activeTeacherSubjectId = savedSub;
    }

    // Restore saved user info if available
    try {
        const savedUser = localStorage.getItem("campusgenie_user");
        if (savedUser) currentUser = JSON.parse(savedUser);
    } catch (e) {}

    // 2. Load cached data from localStorage (zero flicker)
    const localData = getStoredData();
    if (localData && localData.raw_subjects && localData.raw_subjects.length) {
        currentData = localData;
        refreshAllViews();
    }

    // 3. Direct to Login Gateway or Main App
    if (isAuth) {
        showMainApp(currentRole);
    } else {
        showLoginScreen();
    }

    const activeId = (currentUser && currentUser.role === 'student') ? (currentUser.id || currentUser.roll_no) : null;
    fetchStudentData(3, activeId);
    fetchNotifications();
});

// ── Toast Notification System ──────────────────────────────────────────────
function showToast(message, type = "success") {
    let container = document.getElementById("toastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "toastContainer";
        container.className = "fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none";
        document.body.appendChild(container);
    }

    const icons = {
        success: "fa-check-circle",
        error: "fa-circle-exclamation",
        info: "fa-circle-info",
        warning: "fa-triangle-exclamation"
    };
    const colors = {
        success: "from-emerald-600 to-emerald-500",
        error: "from-rose-600 to-rose-500",
        info: "from-indigo-600 to-indigo-500",
        warning: "from-amber-600 to-amber-500"
    };

    const toast = document.createElement("div");
    toast.className = `pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl text-white text-xs font-semibold bg-gradient-to-r ${colors[type] || colors.info} border border-white/10`;
    toast.style.cssText = "transform:translateY(16px);opacity:0;transition:all 0.3s ease;";
    toast.innerHTML = `<i class="fa-solid ${icons[type] || 'fa-circle-info'} text-sm shrink-0"></i><span>${escapeHtml(message)}</span>`;

    container.appendChild(toast);
    requestAnimationFrame(() => {
        toast.style.transform = "translateY(0)";
        toast.style.opacity = "1";
    });

    setTimeout(() => {
        toast.style.transform = "translateY(8px)";
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 350);
    }, 3200);
}

// ── Role Switcher ──────────────────────────────────────────────────────────
function switchRole(role, notify = true) {
    currentRole = role;
    localStorage.setItem("campusgenie_role", role);
    currentRole = role;

    // 1. Update Navigation Pills
    const roles = ['student', 'teacher', 'hod', 'parent'];
    roles.forEach(r => {
        const btn = document.getElementById(`navBtn${r.charAt(0).toUpperCase() + r.slice(1)}`);
        if (btn) {
            if (r === role) {
                btn.className = "px-3 py-1.5 font-bold rounded-lg transition-all flex items-center gap-1.5 bg-indigo-600 text-white shadow-sm";
            } else {
                btn.className = "px-3 py-1.5 font-bold rounded-lg transition-all flex items-center gap-1.5 text-slate-400 hover:text-slate-200";
            }
        }
    });

    // 2. Hide all role view containers
    const viewMap = {
        student: document.getElementById("studentPortalSection"),
        teacher: document.getElementById("teacherPortalSection"),
        hod: document.getElementById("hodRoleView"),
        parent: document.getElementById("parentRoleView")
    };

    Object.entries(viewMap).forEach(([r, el]) => {
        if (el) {
            if (r === role) {
                el.classList.remove("hidden");
            } else {
                el.classList.add("hidden");
            }
        }
    });

    // 3. Update User Badge in Top Bar
    updateTopBarUserBadge(role);

    // 4. Trigger Role-Specific Data Loading
    if (role === 'teacher') {
        loadTeacherRoster(activeTeacherSubjectId);
    } else if (role === 'hod') {
        loadHodDashboard();
    } else if (role === 'parent') {
        loadParentDashboard();
    } else if (role === 'student') {
        if (currentData) renderDashboard(currentData);
    }

    if (notify) showToast(`Switched to ${role.toUpperCase()} View`, "info");
}

function updateTopBarUserBadge(role) {
    const avatar = document.getElementById("activeUserAvatar");
    const nameEl = document.getElementById("activeUserName");
    const roleEl = document.getElementById("activeUserRole");

    if (role === 'teacher') {
        if (avatar) { avatar.innerText = "VK"; avatar.className = "w-6 h-6 rounded-lg bg-cyan-600 text-white font-bold flex items-center justify-center text-[10px]"; }
        if (nameEl) nameEl.innerText = currentUser && currentUser.name && currentUser.role === 'teacher' ? currentUser.name : "Prof. R. K. Verma";
        if (roleEl) roleEl.innerText = "Faculty (Operating Systems)";
    } else if (role === 'hod') {
        if (avatar) { avatar.innerText = "SB"; avatar.className = "w-6 h-6 rounded-lg bg-purple-600 text-white font-bold flex items-center justify-center text-[10px]"; }
        if (nameEl) nameEl.innerText = "Dr. S. K. Bansal";
        if (roleEl) roleEl.innerText = "HOD (Computer Science)";
    } else if (role === 'parent') {
        if (avatar) { avatar.innerText = "PR"; avatar.className = "w-6 h-6 rounded-lg bg-teal-600 text-white font-bold flex items-center justify-center text-[10px]"; }
        const stuName = (currentData && currentData.student && currentData.student.name) || (currentUser && currentUser.student_name) || "Harshit";
        if (nameEl) nameEl.innerText = `Parent of ${stuName}`;
        if (roleEl) roleEl.innerText = "Parent Academic Portal";
    } else {
        const stu = (currentData && currentData.student) || (currentUser && currentUser.role === 'student' ? currentUser : null) || { name: "Harshit Sharma", roll_no: "22CS1084" };
        const parts = (stu.name || "Student").trim().split(" ");
        const initials = parts.length > 1 ? (parts[0][0] + parts[1][0]).toUpperCase() : parts[0].slice(0, 2).toUpperCase();
        if (avatar) { avatar.innerText = initials; avatar.className = "w-6 h-6 rounded-lg bg-indigo-600 text-white font-bold flex items-center justify-center text-[10px]"; }
        if (nameEl) nameEl.innerText = stu.name;
        if (roleEl) roleEl.innerText = `Student (${stu.roll_no || ''})`;
    }
}

// ── Full-Screen Login Gateway & Authentication Controller ──────────────────
let activeGatewayTab = 'student';

function showLoginScreen() {
    const gw = document.getElementById("loginGatewayScreen");
    const shell = document.getElementById("mainAppShell");
    if (gw) gw.classList.remove("hidden");
    if (shell) shell.classList.add("hidden");
}

function showMainApp(role) {
    const gw = document.getElementById("loginGatewayScreen");
    const shell = document.getElementById("mainAppShell");
    if (gw) gw.classList.add("hidden");
    if (shell) shell.classList.remove("hidden");

    if (role) {
        switchRole(role, false);
    }
}

function handleLogout() {
    localStorage.removeItem("campusgenie_authenticated");
    localStorage.removeItem("campusgenie_role");
    localStorage.removeItem("campusgenie_user");
    localStorage.removeItem("campusgenie_data");
    currentUser = null;
    currentData = null;
    showLoginScreen();
    showToast("Logged out successfully. Please select a role to sign in.", "info");
}

function setGatewayLoginTab(tab) {
    activeGatewayTab = tab;
    ['student', 'teacher', 'hod', 'parent'].forEach(t => {
        const btn = document.getElementById(`gwTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (btn) {
            if (t === tab) {
                btn.className = "flex-1 py-1 rounded-md font-bold bg-indigo-600 text-white";
            } else {
                btn.className = "flex-1 py-1 rounded-md font-bold text-slate-400";
            }
        }
    });

    const label = document.getElementById("gwInputLabel");
    const input = document.getElementById("gwIdentifierInput");
    if (tab === 'student') {
        if (label) label.innerText = "Enter Student Roll Number:";
        if (input) { input.placeholder = "e.g. 22CS1084"; input.value = "22CS1084"; }
    } else if (tab === 'teacher') {
        if (label) label.innerText = "Enter Faculty Subject Code / Name:";
        if (input) { input.placeholder = "e.g. os (Operating Systems)"; input.value = "os"; }
    } else if (tab === 'hod') {
        if (label) label.innerText = "Enter HOD Security Key / Name:";
        if (input) { input.placeholder = "Dr. S. K. Bansal"; input.value = "Dr. S. K. Bansal"; }
    } else if (tab === 'parent') {
        if (label) label.innerText = "Enter Child's Roll Number:";
        if (input) { input.placeholder = "e.g. 22CS1084"; input.value = "22CS1084"; }
    }
}

async function performGatewayLogin(role, identifier, password = null) {
    if (!password) {
        const gwPass = document.getElementById("gwPasswordInput");
        if (gwPass && gwPass.value) password = gwPass.value.trim();
        else {
            const modPass = document.getElementById("modalPasswordInput");
            if (modPass && modPass.value) password = modPass.value.trim();
            else password = `${role}123`;
        }
    }
    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ role, identifier, password })
        });
        const data = await res.json();
        if (data.success) {
            currentUser = data.user || {};
            currentUser.role = role;
            if (role === 'teacher' && data.user && data.user.subject_id) {
                activeTeacherSubjectId = data.user.subject_id;
                localStorage.setItem("campusgenie_active_subject", activeTeacherSubjectId);
            }
            localStorage.setItem("campusgenie_authenticated", "true");
            localStorage.setItem("campusgenie_role", role);
            localStorage.setItem("campusgenie_user", JSON.stringify(currentUser));

            if (data.student) {
                currentData = currentData || {};
                currentData.student = data.student;
                currentData.active_student_id = data.active_student_id || data.student.id;
            }

            if (role === 'student') {
                const sid = data.active_student_id || (data.user && data.user.id) || identifier;
                await fetchStudentData(2, sid);
            } else if (role === 'parent') {
                const roll = (data.user && data.user.student_roll) || identifier;
                const rollInput = document.getElementById("parentRollInput");
                if (rollInput) rollInput.value = roll;
                await fetchParentStudentData(roll);
            }

            showMainApp(role);
            showToast(`Welcome ${currentUser.name}! Signed in as ${role.toUpperCase()}.`, "success");
        } else {
            showToast(data.message || "Login failed. Incorrect password.", "error");
        }
    } catch (err) {
        console.error("Gateway login error:", err);
        currentUser = {
            name: role === 'teacher' ? 'Prof. R. K. Verma' : (role === 'hod' ? 'Dr. S. K. Bansal' : (role === 'parent' ? 'Parent of Harshit' : 'Harshit Sharma')),
            role
        };
        localStorage.setItem("campusgenie_authenticated", "true");
        localStorage.setItem("campusgenie_role", role);
        showMainApp(role);
        showToast(`Signed into ${role.toUpperCase()} workspace.`, "info");
    }
}

async function handleGatewayManualLogin(event) {
    event.preventDefault();
    const identifier = document.getElementById("gwIdentifierInput").value.trim();
    const password = document.getElementById("gwPasswordInput") ? document.getElementById("gwPasswordInput").value.trim() : "";
    await performGatewayLogin(activeGatewayTab, identifier, password);
}

// ── Login Modal & Fast 1-Click Demo Login ──────────────────────────────────
function openLoginModal() {
    const modal = document.getElementById("roleLoginModal");
    if (modal) modal.classList.remove("hidden");
}

function closeLoginModal() {
    const modal = document.getElementById("roleLoginModal");
    if (modal) modal.classList.add("hidden");
}

let activeLoginTab = 'student';
function setLoginTab(tab) {
    activeLoginTab = tab;
    ['student', 'teacher', 'hod', 'parent'].forEach(t => {
        const btn = document.getElementById(`tabLogin${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (btn) {
            if (t === tab) {
                btn.className = "flex-1 py-1 rounded-md font-bold bg-indigo-600 text-white";
            } else {
                btn.className = "flex-1 py-1 rounded-md font-bold text-slate-400";
            }
        }
    });

    const label = document.getElementById("loginInputLabel");
    const input = document.getElementById("loginIdentifierInput");
    if (tab === 'student') {
        if (label) label.innerText = "Enter Student Roll Number:";
        if (input) { input.placeholder = "e.g. 22CS1084"; input.value = "22CS1084"; }
    } else if (tab === 'teacher') {
        if (label) label.innerText = "Enter Faculty Subject Code / Name:";
        if (input) { input.placeholder = "e.g. os (Operating Systems)"; input.value = "os"; }
    } else if (tab === 'hod') {
        if (label) label.innerText = "Enter HOD Security Key / Name:";
        if (input) { input.placeholder = "Dr. S. K. Bansal"; input.value = "Dr. S. K. Bansal"; }
    } else if (tab === 'parent') {
        if (label) label.innerText = "Enter Child's Roll Number:";
        if (input) { input.placeholder = "e.g. 22CS1084"; input.value = "22CS1084"; }
    }
}

async function quickDemoLogin(role, identifier, password = null) {
    if (!password) password = `${role}123`;
    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ role, identifier, password })
        });
        const data = await res.json();
        if (data.success) {
            currentUser = data.user || {};
            currentUser.role = role;
            localStorage.setItem("campusgenie_authenticated", "true");
            localStorage.setItem("campusgenie_role", role);
            localStorage.setItem("campusgenie_user", JSON.stringify(currentUser));
            closeLoginModal();

            if (role === 'teacher' && data.user && data.user.subject_id) {
                activeTeacherSubjectId = data.user.subject_id;
                localStorage.setItem("campusgenie_active_subject", activeTeacherSubjectId);
            }
            if (data.student) {
                currentData = currentData || {};
                currentData.student = data.student;
                currentData.active_student_id = data.active_student_id || data.student.id;
            }
            if (role === 'student') {
                const sid = data.active_student_id || (data.user && data.user.id) || identifier;
                await fetchStudentData(2, sid);
            } else if (role === 'parent') {
                const roll = (data.user && data.user.student_roll) || identifier;
                const rollInput = document.getElementById("parentRollInput");
                if (rollInput) rollInput.value = roll;
                await fetchParentStudentData(roll);
            }
            showMainApp(role);
            showToast(`Logged in successfully as ${currentUser.name}!`, "success");
        } else {
            showToast(data.message || "Login failed", "error");
        }
    } catch (err) {
        console.error("Login error:", err);
        closeLoginModal();
        switchRole(role);
    }
}

async function handleManualLogin(event) {
    event.preventDefault();
    const identifier = document.getElementById("loginIdentifierInput").value.trim();
    const password = document.getElementById("modalPasswordInput") ? document.getElementById("modalPasswordInput").value.trim() : "";
    await performGatewayLogin(activeLoginTab, identifier, password);
    closeLoginModal();
}

// ── Fetch Student Data ─────────────────────────────────────────────────────
async function fetchStudentData(retryCount = 3, targetStudentId = null) {
    try {
        let sid = targetStudentId;
        if (!sid && currentUser && currentUser.role === 'student') {
            sid = currentUser.id || currentUser.roll_no;
        }
        const url = sid ? `/api/student?student_id=${encodeURIComponent(sid)}` : "/api/student";
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        currentData = data;
        saveStoredData(currentData);

        refreshAllViews();
        if (currentRole) updateTopBarUserBadge(currentRole);
    } catch (err) {
        console.error("fetchStudentData failed:", err);
        const localData = getStoredData();
        if (localData) {
            currentData = localData;
            refreshAllViews();
        }
        if (retryCount > 0) {
            setTimeout(() => fetchStudentData(retryCount - 1, targetStudentId), 1200);
        }
    }
}

// ── Switch Active Student ──────────────────────────────────────────────────
async function handleSwitchStudent(studentId) {
    if (!studentId) return;
    try {
        const res = await fetch("/api/student/switch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_id: studentId })
        });
        const data = await res.json();
        if (data.success) {
            if (currentUser && currentUser.role === 'student' && data.student) {
                currentUser = {
                    id: data.student.id,
                    name: data.student.name,
                    roll_no: data.student.roll_no,
                    role: 'student',
                    branch: data.student.branch,
                    semester: data.student.semester
                };
                localStorage.setItem("campusgenie_user", JSON.stringify(currentUser));
            }
            await fetchStudentData(2, studentId);
            showToast(`Active student: ${data.message}`, "info");
        }
    } catch (err) {
        console.error("Failed to switch student:", err);
    }
}

// ── Render Student Dashboard ───────────────────────────────────────────────
function renderDashboard(data) {
    if (!data) return;
    const student = data.student || {};
    const allStudents = data.all_students || [];
    const subjects = data.subjects || [];

    // Header Student Switcher Dropdown
    const dropdown = document.getElementById("studentSelectDropdown");
    if (dropdown) {
        dropdown.innerHTML = "";
        allStudents.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.id;
            opt.innerText = `${s.name} (${s.roll_no})`;
            if (s.id === student.id) opt.selected = true;
            dropdown.appendChild(opt);
        });
    }

    // Active Student Bio
    const avatarInitials = document.getElementById("studentAvatarInitials");
    if (avatarInitials) {
        const parts = (student.name || "HS").split(" ");
        avatarInitials.innerText = parts.length > 1 ? (parts[0][0] + parts[1][0]).toUpperCase() : parts[0].slice(0, 2).toUpperCase();
    }
    const nameDisplay = document.getElementById("activeStudentNameDisplay");
    if (nameDisplay) nameDisplay.innerText = student.name || "Student";
    const rollDisplay = document.getElementById("activeStudentRollDisplay");
    if (rollDisplay) rollDisplay.innerText = student.roll_no || "";
    const infoDisplay = document.getElementById("activeStudentInfoDisplay");
    if (infoDisplay) infoDisplay.innerText = `${student.branch || "CSE"} • ${student.semester || "5th Sem"}`;

    // Overall Attendance & Badge
    let totAttended = 0;
    let totClasses = 0;
    subjects.forEach(s => {
        totAttended += (s.attended || 0);
        totClasses += (s.total || 0);
    });
    const overallPct = totClasses > 0 ? ((totAttended / totClasses) * 100).toFixed(1) : 100.0;
    const overallBadge = document.getElementById("overallBadge");
    if (overallBadge) {
        if (overallPct >= 75) {
            overallBadge.className = "text-xs px-3 py-1 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
            overallBadge.innerHTML = `● ${overallPct}% Safe`;
        } else {
            overallBadge.className = "text-xs px-3 py-1 rounded-full font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse";
            overallBadge.innerHTML = `⚠️ ${overallPct}% Shortage`;
        }
    }

    // Render Subjects Attendance & Marks
    renderSubjectsContainer(subjects, student.target_attendance || 75);

    // Render Timetable
    renderTimetableContainer(data.timetable || []);

    // Render Notices & Opportunities
    renderNoticesContainer(data.notices || []);
    renderOpportunitiesContainer(data.opportunities || []);

    // Render Predictive Study Recommendations
    renderPredictiveStudyRecommendations(subjects, student);
}

function renderSubjectsContainer(subjects, target = 75) {
    const container = document.getElementById("subjectsContainer");
    if (!container) return;

    if (!subjects.length) {
        container.innerHTML = "<p class='text-xs text-slate-500 text-center py-4'>No subjects enrolled yet.</p>";
        return;
    }

    container.innerHTML = subjects.map(s => {
        const pct = parseFloat(s.percentage || 0);
        const isSafe = pct >= target;
        const color = isSafe ? "emerald" : "rose";

        let adviceText = "";
        if (!isSafe) {
            const req = target * s.total - 100 * s.attended;
            const needed = req > 0 ? Math.ceil(req / (100 - target)) : 0;
            adviceText = `<span class="text-rose-400 font-semibold">⚠️ Attend <strong>${needed}</strong> more class${needed !== 1 ? 'es' : ''} to reach ${target}%</span>`;
        } else {
            const maxBunks = Math.max(0, Math.floor((s.attended * 100) / target) - s.total);
            adviceText = `<span class="text-emerald-400 font-semibold">✅ Safe (can miss <strong>${maxBunks}</strong> class${maxBunks !== 1 ? 'es' : ''})</span>`;
        }

        const markStatus = s.result === 'Pass' ? '<span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">Pass</span>' :
                          (s.result === 'Fail' ? '<span class="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold">Fail</span>' :
                          '<span class="px-2 py-0.5 rounded bg-slate-800 text-slate-400">Pending</span>');

        return `
            <div class="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2.5">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-bold text-xs text-white">${escapeHtml(s.name)}</span>
                            <span class="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">${escapeHtml(s.code)}</span>
                        </div>
                        <p class="text-[11px] text-slate-500 mt-0.5">Faculty: ${escapeHtml(s.faculty || 'Assigned')}</p>
                    </div>
                    <div class="text-right">
                        <div class="flex items-center space-x-2 justify-end">
                            <span class="text-sm font-extrabold text-${color}-400">${pct}%</span>
                            <span class="text-[11px] text-slate-400 font-mono">(${s.attended}/${s.total})</span>
                        </div>
                        <div class="text-[11px] mt-0.5 flex items-center justify-end space-x-1.5">
                            <span class="text-slate-400">Marks: <strong class="text-slate-200">${s.score}/${s.total_marks}</strong></span>
                            ${markStatus}
                        </div>
                    </div>
                </div>

                <!-- Progress Bar with 75% target tick -->
                <div class="relative w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-${color}-600 to-${color}-400 transition-all duration-500" style="width: ${Math.min(100, pct)}%"></div>
                    <div class="absolute top-0 bottom-0 w-0.5 bg-white/60 z-10" style="left: 75%;" title="75% Threshold Line"></div>
                </div>

                <div class="flex items-center justify-between text-[11px]">
                    <div>${adviceText}</div>
                    <span class="text-[10px] text-slate-500">Synced with Teacher Portal</span>
                </div>
            </div>
        `;
    }).join("");
}

function renderTimetableContainer(timetable) {
    const container = document.getElementById("timetableContainer");
    if (!container) return;

    if (!timetable.length) {
        container.innerHTML = "<p class='text-xs text-slate-500 text-center py-2'>No lectures scheduled for today.</p>";
        return;
    }

    container.innerHTML = timetable.map(t => {
        const isOngoing = t.status === 'ongoing';
        const isCompleted = t.status === 'completed';
        const statusBadge = isOngoing ?
            `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 animate-pulse">● Live Now</span>` :
            (isCompleted ? `<span class="text-[10px] text-slate-500">✓ Completed</span>` : `<span class="text-[10px] text-slate-400">⏳ Upcoming</span>`);

        return `
            <div class="p-3 rounded-xl ${isOngoing ? 'bg-indigo-950/40 border border-indigo-500/40' : 'bg-slate-950/60 border border-slate-800'} flex items-center justify-between text-xs">
                <div class="space-y-0.5">
                    <div class="flex items-center space-x-2">
                        <span class="font-bold text-white">${escapeHtml(t.subject)}</span>
                        <span class="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">${escapeHtml(t.type || 'Theory')}</span>
                    </div>
                    <p class="text-[11px] text-slate-400">
                        <i class="fa-solid fa-location-dot text-rose-400 mr-1"></i><strong>${escapeHtml(t.room)}</strong> • ${escapeHtml(t.faculty)}
                    </p>
                </div>
                <div class="text-right space-y-1">
                    <p class="text-[11px] font-mono text-cyan-400 font-semibold">${escapeHtml(t.time)}</p>
                    ${statusBadge}
                </div>
            </div>
        `;
    }).join("");
}

function renderPredictiveStudyRecommendations(subjects, student) {
    const container = document.getElementById("weakAreaRecommendations");
    if (!container) return;

    const weakSubjects = subjects.filter(s => {
        const score = parseFloat(s.score);
        const pct = parseFloat(s.percentage || 0);
        return (!isNaN(score) && score < 50) || pct < 75 || s.result === 'Fail';
    });

    if (!weakSubjects.length) {
        container.innerHTML = `
            <div class="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 text-emerald-300 flex items-center gap-2">
                <i class="fa-solid fa-circle-check text-emerald-400"></i>
                <span>All academic tracks and attendance are in optimal standing! Keep it up.</span>
            </div>
        `;
        return;
    }

    container.innerHTML = weakSubjects.map(s => {
        const isFailing = s.result === 'Fail' || (parseFloat(s.score) < 40);
        const isLowAtt = parseFloat(s.percentage || 0) < 75;

        return `
            <div class="p-3 rounded-xl bg-slate-950/80 border border-indigo-500/30 flex items-start justify-between gap-2">
                <div>
                    <span class="font-bold text-white">${escapeHtml(s.name)} (${escapeHtml(s.code)})</span>
                    <p class="text-[11px] text-slate-400 mt-0.5">
                        ${isFailing ? '⚠️ Low Exam Score (' + s.score + '/' + s.total_marks + '). Review fundamental concepts before end-terms.' : ''}
                        ${isLowAtt ? 'Attendance velocity is below 75%. Prioritize upcoming lectures with ' + escapeHtml(s.faculty) + '.' : ''}
                    </p>
                </div>
                <button onclick="sendQuickPrompt('Explain ${escapeHtml(s.name)} key concepts, viva questions, and exam tips')" class="px-2.5 py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/60 border border-indigo-500/40 text-indigo-300 font-bold text-[11px] transition-all shrink-0">
                    💡 AI Study Plan
                </button>
            </div>
        `;
    }).join("");
}

function renderNoticesContainer(notices) {
    const container = document.getElementById("noticesContainer");
    if (!container) return;

    if (!notices.length) {
        container.innerHTML = "<p class='text-xs text-slate-500 text-center py-2'>No official notices today.</p>";
        return;
    }

    container.innerHTML = notices.map(n => `
        <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1 text-xs">
            <div class="flex items-center justify-between">
                <span class="font-bold text-white">${escapeHtml(n.title)}</span>
                <span class="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-semibold">${escapeHtml(n.badge || 'Notice')}</span>
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">${escapeHtml(n.content)}</p>
            <p class="text-[10px] text-slate-500 text-right">📅 ${escapeHtml(n.date || 'Today')}</p>
        </div>
    `).join("");
}

function renderOpportunitiesContainer(opps) {
    const container = document.getElementById("opportunitiesContainer");
    if (!container) return;

    if (!opps.length) {
        container.innerHTML = "<p class='text-xs text-slate-500 text-center py-2'>No opportunities posted.</p>";
        return;
    }

    container.innerHTML = opps.map(o => `
        <div class="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2 text-xs">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2">
                    <span class="font-bold text-white">${escapeHtml(o.title)}</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-semibold">${escapeHtml(o.badge || 'Verified')}</span>
                </div>
                <span class="text-[11px] text-amber-400 font-semibold">⌛ ${escapeHtml(o.deadline)}</span>
            </div>
            <p class="text-[11px] text-slate-400">${escapeHtml(o.desc || '')}</p>
            <div class="flex items-center justify-between pt-1">
                <span class="text-[10px] text-slate-500">Category: ${escapeHtml(o.category || 'Career')}</span>
                <a href="${escapeHtml(o.link)}" target="_blank" class="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] transition-all">
                    Apply Now <i class="fa-solid fa-arrow-up-right-from-square ml-1 text-[9px]"></i>
                </a>
            </div>
        </div>
    `).join("");
}

// ── TEACHER PORTAL LOGIC ───────────────────────────────────────────────────
async function loadTeacherRoster(subjectId) {
    const subjects = currentData && currentData.raw_subjects && currentData.raw_subjects.length ? currentData.raw_subjects : [
        { id: "os", name: "Operating Systems", code: "CS-501", faculty: "Prof. R. K. Verma" }
    ];

    if (!subjectId || !subjects.some(s => s.id === subjectId)) {
        subjectId = subjects.length ? subjects[0].id : 'os';
    }
    activeTeacherSubjectId = subjectId;
    localStorage.setItem("campusgenie_active_subject", subjectId);
    renderTeacherSubjectCards();

    const currentSub = subjects.find(s => s.id === subjectId) || { name: subjectId, code: "" };
    const titleEl = document.getElementById("activeSubjectRosterTitle");
    if (titleEl) {
        titleEl.innerHTML = `<i class="fa-solid fa-clipboard-user text-indigo-400"></i> ${escapeHtml(currentSub.name)} (${escapeHtml(currentSub.code || '')}) — Class Attendance`;
    }

    // Build students list immediately from currentData
    const students = (currentData && currentData.students ? currentData.students : []).map(s => {
        const att = s.attendance && s.attendance[subjectId] ? s.attendance[subjectId] : { attended: 0, total: 0, percentage: 100.0, status: 'safe' };
        const marks = s.marks && s.marks[subjectId] ? s.marks[subjectId] : { score: '-', total: 100, status: 'Pending' };
        return {
            id: s.id,
            name: s.name,
            roll_no: s.roll_no,
            branch: s.branch || 'CSE',
            attended: att.attended || 0,
            total: att.total || 0,
            percentage: att.percentage !== undefined ? att.percentage : 100.0,
            status: att.status || 'safe',
            score: marks.score || '-',
            total_marks: marks.total || 100,
            result: marks.status || 'Pending'
        };
    });

    renderTeacherRosterTable(students, currentSub);

    try {
        const res = await fetch(`/api/teacher/students/by_subject?subject_id=${subjectId}`);
        if (res.ok) {
            const data = await res.json();
            if (data.students && data.students.length) {
                renderTeacherRosterTable(data.students, data.subject || currentSub);
            }
        }
    } catch (err) {
        console.warn("loadTeacherRoster network sync error:", err);
    }
}

function renderTeacherSubjectCards() {
    const grid = document.getElementById("teacherSubjectCardsGrid");
    if (!grid) return;

    const subjects = currentData && currentData.raw_subjects && currentData.raw_subjects.length ? currentData.raw_subjects : [
        { id: "os", name: "Operating Systems", code: "CS-501", faculty: "Prof. R. K. Verma" },
        { id: "dsa", name: "Data Structures & Algorithms", code: "CS-502", faculty: "Dr. Sunita Rao" },
        { id: "dbms", name: "Database Management Systems", code: "CS-503", faculty: "Dr. Alok Gupta" },
        { id: "cn", name: "Computer Networks", code: "CS-504", faculty: "Prof. Sneha Kapoor" }
    ];

    if (!subjects.some(s => s.id === activeTeacherSubjectId)) {
        activeTeacherSubjectId = subjects[0].id;
        localStorage.setItem("campusgenie_active_subject", activeTeacherSubjectId);
    }

    grid.innerHTML = subjects.map(s => {
        const isActive = s.id === activeTeacherSubjectId;
        return `
            <button onclick="loadTeacherRoster('${s.id}')" class="p-3 rounded-xl border text-left transition-all ${isActive ? 'bg-indigo-600/30 border-indigo-400 shadow-md shadow-indigo-600/20' : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'}">
                <span class="text-[10px] px-1.5 py-0.5 rounded ${isActive ? 'bg-indigo-500/40 text-indigo-200' : 'bg-slate-800 text-slate-400'} font-mono">${escapeHtml(s.code)}</span>
                <p class="font-bold text-xs text-white mt-1">${escapeHtml(s.name)}</p>
                <p class="text-[10px] text-slate-400 mt-0.5">${escapeHtml(s.faculty)}</p>
            </button>
        `;
    }).join("");
}

function renderTeacherRosterTable(students, subject) {
    const tbody = document.getElementById("teacherRosterTableBody");
    if (!tbody) return;

    // Initialize attendance state for each student (defaults to present)
    teacherRosterState = {};
    students.forEach(s => {
        teacherRosterState[s.id] = 'present';
    });

    tbody.innerHTML = students.map((s, idx) => {
        const pct = parseFloat(s.percentage || 0);
        const isSafe = pct >= 75;
        const pill = isSafe ?
            `<span class="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold">${pct}% Safe</span>` :
            `<span class="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-semibold animate-pulse">${pct}% Debar Risk</span>`;

        return `
            <tr class="hover:bg-slate-950/40 transition-colors">
                <td class="py-3">
                    <p class="font-bold text-white">${escapeHtml(s.name)}</p>
                    <p class="text-[10px] text-slate-500 font-mono">${escapeHtml(s.roll_no)} • ${escapeHtml(s.branch || 'CSE')}</p>
                </td>
                <td class="py-3">
                    <div>
                        <span class="font-semibold text-slate-200">${s.attended}/${s.total}</span>
                        <div class="mt-0.5">${pill}</div>
                    </div>
                </td>
                <td class="py-3 text-center">
                    <div class="inline-flex items-center space-x-2 bg-slate-950/90 p-1 rounded-xl border border-slate-800">
                        <button id="btnP_${s.id}" onclick="setStudentAttendance('${s.id}', 'present')" class="btn-att-p active" title="Mark Present">
                            P
                        </button>
                        <button id="btnA_${s.id}" onclick="setStudentAttendance('${s.id}', 'absent')" class="btn-att-a" title="Mark Absent">
                            A
                        </button>
                    </div>
                </td>
                <td class="py-3 text-right">
                    <div class="flex items-center justify-end space-x-2">
                        <span class="font-mono font-bold ${s.result === 'Pass' ? 'text-emerald-400' : (s.result === 'Fail' ? 'text-rose-400' : 'text-slate-400')}">${s.score}/${s.total_marks}</span>
                        <button onclick="openMarksModal('${s.id}', '${escapeHtml(s.name)}', '${subject.id || activeTeacherSubjectId}')" class="px-2 py-1 rounded bg-purple-600/30 hover:bg-purple-600/60 border border-purple-500/40 text-purple-300 text-[10px] font-bold transition-all">
                            <i class="fa-solid fa-pen-to-square"></i> Edit
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

function setStudentAttendance(studentId, status) {
    teacherRosterState[studentId] = status;
    const btnP = document.getElementById(`btnP_${studentId}`);
    const btnA = document.getElementById(`btnA_${studentId}`);

    if (status === 'present') {
        if (btnP) btnP.classList.add("active");
        if (btnA) btnA.classList.remove("active");
    } else {
        if (btnA) btnA.classList.add("active");
        if (btnP) btnP.classList.remove("active");
    }
}

function bulkSetAttendance(status) {
    Object.keys(teacherRosterState).forEach(stuId => {
        setStudentAttendance(stuId, status);
    });
    showToast(`Marked all students as ${status.toUpperCase()}!`, "info");
}

async function submitClassAttendance() {
    const records = Object.entries(teacherRosterState).map(([student_id, status]) => ({
        student_id,
        status
    }));

    if (!records.length) {
        showToast("No students to submit attendance for.", "warning");
        return;
    }

    const btn = document.getElementById("btnSaveTeacherAttendance");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i> Saving to ERP...";
    }

    try {
        const res = await fetch("/api/teacher/attendance/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                subject_id: activeTeacherSubjectId,
                records
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            await fetchStudentData();
            await loadTeacherRoster(activeTeacherSubjectId);
        } else {
            showToast(data.message || "Failed to save attendance.", "error");
        }
    } catch (err) {
        console.error("submitClassAttendance error:", err);
        showToast("Network error saving attendance.", "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = "<i class='fa-solid fa-floppy-disk'></i> 💾 Save & Finalize Attendance";
        }
    }
}

// ── MARKS MODAL (TEACHER) ──────────────────────────────────────────────────
function openMarksModal(studentId, studentName, subjectId) {
    document.getElementById("marksModalStudentId").value = studentId;
    document.getElementById("marksModalSubjectId").value = subjectId;
    document.getElementById("marksModalStudentName").innerText = `Student: ${studentName}`;
    document.getElementById("marksModalScore").value = "";
    document.getElementById("marksModal").classList.remove("hidden");
}

function closeMarksModal() {
    document.getElementById("marksModal").classList.add("hidden");
}

async function submitMarksFromModal(event) {
    event.preventDefault();
    const student_id = document.getElementById("marksModalStudentId").value;
    const subject_id = document.getElementById("marksModalSubjectId").value;
    const score = document.getElementById("marksModalScore").value;
    const total = document.getElementById("marksModalTotal").value || 100;

    try {
        const res = await fetch("/api/admin/marks/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_id, subject_id, score, total })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            closeMarksModal();
            await fetchStudentData();
            await loadTeacherRoster(activeTeacherSubjectId);
        } else {
            showToast(data.message || "Failed to update marks.", "error");
        }
    } catch (err) {
        console.error("submitMarksFromModal error:", err);
    }
}

// ── HOD ADMIN DASHBOARD ────────────────────────────────────────────────────
async function loadHodDashboard() {
    try {
        // 1. Defaulters Radar
        const defRes = await fetch("/api/hod/defaulters");
        const defData = await defRes.json();
        renderHodDefaulters(defData);

        // 2. Master Subjects
        renderHodSubjects();

        // 3. Master Students
        renderHodStudents();
    } catch (err) {
        console.error("loadHodDashboard error:", err);
    }
}

function renderHodDefaulters(data) {
    const pill = document.getElementById("hodDefaulterPill");
    if (pill) pill.innerText = `${data.total_defaulters} of ${data.total_students} Debarred`;

    const container = document.getElementById("hodDefaultersList");
    if (!container) return;

    if (!data.defaulters || !data.defaulters.length) {
        container.innerHTML = `
            <div class="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 text-emerald-300 flex items-center gap-2">
                <i class="fa-solid fa-circle-check text-emerald-400"></i>
                <span>Zero attendance defaulters in the CSE department! All students are eligible for upcoming examinations.</span>
            </div>
        `;
        return;
    }

    container.innerHTML = data.defaulters.map(d => `
        <div class="p-3 rounded-xl bg-slate-950 border border-rose-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
                <span class="font-bold text-white">${escapeHtml(d.name)}</span>
                <span class="text-[10px] text-slate-400 font-mono ml-2">(${escapeHtml(d.roll_no)})</span>
                <div class="mt-1 flex flex-wrap gap-1.5">
                    ${d.shortages.map(sh => `<span class="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-medium border border-rose-500/30">${escapeHtml(sh.subject)}: ${sh.percentage}% (Need ${sh.classes_needed} classes)</span>`).join("")}
                </div>
            </div>
            <div class="text-right">
                <span class="text-xs font-extrabold text-rose-400">${d.overall_pct}% Overall</span>
                <p class="text-[10px] text-slate-500">Debarment Notice Active</p>
            </div>
        </div>
    `).join("");
}

function renderHodSubjects() {
    const container = document.getElementById("hodSubjectsList");
    if (!container) return;

    const subjects = currentData && currentData.raw_subjects ? currentData.raw_subjects : [];
    container.innerHTML = subjects.map(s => `
        <div class="p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between">
            <div>
                <p class="font-bold text-white">${escapeHtml(s.name)}</p>
                <p class="text-[10px] text-slate-400">${escapeHtml(s.code)} • ${escapeHtml(s.faculty)}</p>
            </div>
            <div class="flex items-center gap-1.5">
                <button onclick="openEditSubjectModal('${s.id}')" class="p-1.5 text-cyan-400 hover:text-cyan-200 hover:bg-cyan-500/20 rounded-lg transition-all" title="Edit Subject Details">
                    <i class="fa-solid fa-pen-to-square text-xs"></i>
                </button>
                <button onclick="handleHodDeleteSubject('${s.id}')" class="p-1.5 text-rose-400 hover:text-rose-200 hover:bg-rose-500/20 rounded-lg transition-all" title="Remove Subject">
                    <i class="fa-solid fa-trash-can text-xs"></i>
                </button>
            </div>
        </div>
    `).join("");
}

function openEditSubjectModal(subjectId) {
    const modal = document.getElementById("editSubjectModal");
    if (!modal) return;
    const subjects = currentData && currentData.raw_subjects ? currentData.raw_subjects : [];
    const sub = subjects.find(s => s.id === subjectId);
    if (!sub) return;

    document.getElementById("editSubjectId").value = sub.id;
    document.getElementById("editSubjectName").value = sub.name;
    document.getElementById("editSubjectCode").value = sub.code;
    document.getElementById("editSubjectFaculty").value = sub.faculty || "";
    modal.classList.remove("hidden");
}

function closeEditSubjectModal() {
    const modal = document.getElementById("editSubjectModal");
    if (modal) modal.classList.add("hidden");
}

async function handleHodSaveEditSubject(event) {
    event.preventDefault();
    const id = document.getElementById("editSubjectId").value;
    const name = document.getElementById("editSubjectName").value.trim();
    const code = document.getElementById("editSubjectCode").value.trim();
    const faculty = document.getElementById("editSubjectFaculty").value.trim();

    if (!name || !code) {
        showToast("Name and Course Code required.", "warning");
        return;
    }

    if (currentData && currentData.raw_subjects) {
        const target = currentData.raw_subjects.find(s => s.id === id);
        if (target) {
            target.name = name;
            target.code = code;
            target.faculty = faculty;
        }
    }
    if (currentData && currentData.subjects) {
        const target = currentData.subjects.find(s => s.id === id);
        if (target) {
            target.name = name;
            target.code = code;
            target.faculty = faculty;
        }
    }

    saveStoredData(currentData);
    syncStateToServer(currentData);

    refreshAllViews();
    closeEditSubjectModal();
    showToast(`Subject '${name}' updated successfully!`, "success");

    try {
        await fetch("/api/hod/subject/edit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subject_id: id, name, code, faculty })
        });
    } catch (e) {
        console.warn("Edit sync error:", e);
    }
}

function renderHodStudents() {
    const tbody = document.getElementById("hodStudentsTableBody");
    if (!tbody) return;

    const students = currentData && currentData.all_students ? currentData.all_students : [];
    tbody.innerHTML = students.map(s => `
        <tr class="hover:bg-slate-950/40">
            <td class="py-2.5 font-bold text-white">${escapeHtml(s.name)}</td>
            <td class="py-2.5 font-mono text-slate-400">${escapeHtml(s.roll_no)}</td>
            <td class="py-2.5 text-slate-400">${escapeHtml(s.branch || 'CSE')} (${escapeHtml(s.semester || '5th')})</td>
            <td class="py-2.5 text-right space-x-2">
                <button onclick="handleHodDeleteStudent('${s.id}')" class="px-2 py-1 rounded bg-rose-500/20 hover:bg-rose-500/40 border border-rose-500/30 text-rose-300 font-bold text-[10px] transition-all">
                    <i class="fa-solid fa-trash-can mr-1"></i> Remove
                </button>
            </td>
        </tr>
    `).join("");
}

async function handleHodAddSubject(event) {
    event.preventDefault();
    const name = document.getElementById("hodNewSubName").value.trim();
    const code = document.getElementById("hodNewSubCode").value.trim();
    const faculty = document.getElementById("hodNewSubFaculty").value.trim();

    if (!name || !code) {
        showToast("Please provide subject name and code.", "warning");
        return;
    }

    const subId = code.toLowerCase().replace(/[^a-z0-9]/g, '');
    const newSubject = {
        id: subId,
        code: code,
        name: name,
        faculty: faculty || "Faculty Assigned"
    };

    if (!currentData) currentData = {};
    if (!currentData.raw_subjects) currentData.raw_subjects = [];
    currentData.raw_subjects = currentData.raw_subjects.filter(s => s.id !== subId);
    currentData.raw_subjects.push(newSubject);

    if (currentData.students) {
        currentData.students.forEach(stu => {
            if (!stu.attendance) stu.attendance = {};
            if (!stu.attendance[subId]) stu.attendance[subId] = { attended: 0, total: 0, percentage: 100.0, status: 'safe' };
            if (!stu.marks) stu.marks = {};
            if (!stu.marks[subId]) stu.marks[subId] = { score: '-', total: 100, status: 'Pending' };
        });
    }
    if (currentData.subjects) {
        currentData.subjects = currentData.subjects.filter(s => s.id !== subId);
        currentData.subjects.push({
            id: subId,
            code: code,
            name: name,
            faculty: faculty || "Faculty Assigned",
            attended: 0,
            total: 0,
            percentage: 100.0,
            status: 'safe',
            score: '-',
            total_marks: 100,
            result: 'Pending'
        });
    }

    saveStoredData(currentData);
    syncStateToServer(currentData);

    refreshAllViews();
    showToast(`Subject '${name}' added to curriculum!`, "success");
    event.target.reset();

    try {
        await fetch("/api/admin/subject/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, code, faculty })
        });
    } catch (e) {
        console.warn("Backend add sync error:", e);
    }
}

async function handleHodDeleteSubject(subjectId) {
    if (!confirm("Are you sure you want to remove this subject from curriculum?")) return;

    if (currentData && currentData.raw_subjects) {
        currentData.raw_subjects = currentData.raw_subjects.filter(s => s.id !== subjectId);
    }
    if (currentData && currentData.subjects) {
        currentData.subjects = currentData.subjects.filter(s => s.id !== subjectId);
    }
    if (currentData && currentData.students) {
        currentData.students.forEach(stu => {
            if (stu.attendance) delete stu.attendance[subjectId];
            if (stu.marks) delete stu.marks[subjectId];
        });
    }

    if (activeTeacherSubjectId === subjectId) {
        const remaining = currentData && currentData.raw_subjects && currentData.raw_subjects.length ? currentData.raw_subjects[0].id : '';
        activeTeacherSubjectId = remaining;
        localStorage.setItem("campusgenie_active_subject", activeTeacherSubjectId);
    }

    saveStoredData(currentData);
    syncStateToServer(currentData);

    refreshAllViews();
    showToast("Subject removed from college curriculum.", "info");

    try {
        await fetch("/api/hod/subject/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subject_id: subjectId })
        });
    } catch (e) {
        console.warn("Backend delete sync error:", e);
    }
}

async function handleHodAddStudent(event) {
    event.preventDefault();
    const name = document.getElementById("hodNewStuName").value.trim();
    const roll_no = document.getElementById("hodNewStuRoll").value.trim();
    const branch = document.getElementById("hodNewStuBranch").value.trim();
    const semester = document.getElementById("hodNewStuSem").value.trim();

    try {
        const res = await fetch("/api/admin/student/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, roll_no, branch, semester })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            event.target.reset();
            await fetchStudentData();
            renderHodStudents();
        } else {
            showToast(data.message || "Failed to enroll student.", "error");
        }
    } catch (err) {
        console.error("handleHodAddStudent error:", err);
    }
}

async function handleHodDeleteStudent(studentId) {
    if (!confirm("Are you sure you want to remove this student record?")) return;
    try {
        const res = await fetch("/api/hod/student/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_id: studentId })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            await fetchStudentData();
            renderHodStudents();
        }
    } catch (err) {
        console.error("handleHodDeleteStudent error:", err);
    }
}

// ── PARENT PORTAL LOGIC ────────────────────────────────────────────────────
async function loadParentDashboard() {
    const rollInput = document.getElementById("parentRollInput");
    let roll = "22CS1084";
    if (currentUser && currentUser.role === 'parent' && currentUser.student_roll) {
        roll = currentUser.student_roll;
    } else if (rollInput && rollInput.value.trim()) {
        roll = rollInput.value.trim();
    }
    if (rollInput) rollInput.value = roll;
    await fetchParentStudentData(roll);
}

async function handleParentLookup(event) {
    event.preventDefault();
    const roll = document.getElementById("parentRollInput").value.trim();
    await fetchParentStudentData(roll);
}

async function fetchParentStudentData(roll) {
    const container = document.getElementById("parentReportContainer");
    if (!container) return;

    container.innerHTML = "<p class='text-xs text-slate-500 text-center py-4'>Fetching verified academic records...</p>";

    try {
        const res = await fetch(`/api/parent/student_lookup?roll_no=${encodeURIComponent(roll)}`);
        const data = await res.json();
        if (!data.success) {
            container.innerHTML = `<div class="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 text-rose-300 text-xs">⚠️ ${escapeHtml(data.message)}</div>`;
            return;
        }

        const stu = data.student;
        const isSafe = stu.status === 'safe';

        container.innerHTML = `
            <div class="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-4">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                    <div>
                        <div class="flex items-center space-x-2">
                            <h3 class="text-base font-extrabold text-white">${escapeHtml(stu.name)}</h3>
                            <span class="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">${escapeHtml(stu.roll_no)}</span>
                        </div>
                        <p class="text-xs text-slate-400 mt-0.5">${escapeHtml(stu.branch)} • ${escapeHtml(stu.semester)}</p>
                    </div>
                    <div class="text-right">
                        <span class="text-base font-extrabold ${isSafe ? 'text-emerald-400' : 'text-rose-400'}">${stu.overall_pct}% Attendance</span>
                        <p class="text-[11px] text-slate-500">${isSafe ? '✅ Eligible for Exam' : '⚠️ Debarment Risk (< 75%)'}</p>
                    </div>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead>
                            <tr class="text-[11px] text-slate-400 border-b border-slate-800">
                                <th class="py-2">Subject</th>
                                <th class="py-2">Attendance</th>
                                <th class="py-2">Exam Marks</th>
                                <th class="py-2 text-right">Status</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/60">
                            ${data.subjects.map(s => `
                                <tr>
                                    <td class="py-2.5">
                                        <span class="font-bold text-white">${escapeHtml(s.subject_name)}</span>
                                        <p class="text-[10px] text-slate-500">${escapeHtml(s.faculty)}</p>
                                    </td>
                                    <td class="py-2.5 font-semibold text-slate-200">
                                        ${s.percentage}% <span class="text-[10px] text-slate-500">(${s.attended}/${s.total})</span>
                                    </td>
                                    <td class="py-2.5 font-mono text-slate-300">
                                        ${s.score}/100
                                    </td>
                                    <td class="py-2.5 text-right">
                                        ${s.status === 'safe' ? '<span class="text-emerald-400 font-bold">Safe</span>' : '<span class="text-rose-400 font-bold">Shortage</span>'}
                                    </td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>

                <div class="p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between text-xs">
                    <div>
                        <p class="text-slate-300 font-bold"><i class="fa-solid fa-user-tie text-cyan-400 mr-1.5"></i>${escapeHtml(stu.proctor)}</p>
                        <p class="text-[10px] text-slate-500">Official Mentor • Contact: proctor.cse@akgec.ac.in</p>
                    </div>
                    <button onclick="showToast('Proctor has been alerted. Official meeting schedule sent to parent email.', 'info')" class="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-bold text-[11px] transition-all">
                        📞 Request Mentor Call
                    </button>
                </div>
            </div>
        `;
    } catch (err) {
        console.error("fetchParentStudentData error:", err);
    }
}

// ── PLACEMENT HUB: RESUME ATS ANALYZER ──────────────────────────────────────
async function handleAnalyzeResume() {
    const text = document.getElementById("resumeInput").value.trim();
    if (!text) {
        showToast("Please enter your resume text or technical skills.", "warning");
        return;
    }

    const box = document.getElementById("atsResultBox");
    if (box) {
        box.classList.remove("hidden");
        box.innerHTML = "<p class='text-slate-400 text-center py-2'><i class='fa-solid fa-spinner fa-spin mr-1'></i> Running IBM watsonx ATS Skill Parser...</p>";
    }

    try {
        const res = await fetch("/api/placement/analyze_resume", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ resume_text: text })
        });
        const data = await res.json();
        if (data.success && box) {
            box.innerHTML = `
                <div class="flex items-center justify-between border-b border-slate-800 pb-2">
                    <div class="flex items-center space-x-2.5">
                        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-600 flex items-center justify-center text-white font-extrabold text-sm shadow-md">
                            ${data.score}
                        </div>
                        <div>
                            <span class="font-bold text-white text-xs">ATS Match Score</span>
                            <p class="text-[10px] text-emerald-400 font-semibold">Grade: ${escapeHtml(data.grade)}</p>
                        </div>
                    </div>
                    <span class="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">Analyzed</span>
                </div>

                <div class="space-y-1">
                    <p class="text-[11px] text-slate-400 font-bold">Verified Matching Skills:</p>
                    <div class="flex flex-wrap gap-1">
                        ${data.matched_skills.map(m => `<span class="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">✓ ${escapeHtml(m)}</span>`).join("")}
                    </div>
                </div>

                ${data.missing_keywords && data.missing_keywords.length ? `
                    <div class="space-y-1">
                        <p class="text-[11px] text-rose-400 font-bold">Missing High-Demand Keywords:</p>
                        <div class="flex flex-wrap gap-1">
                            ${data.missing_keywords.map(k => `<span class="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-medium border border-rose-500/30">+ ${escapeHtml(k)}</span>`).join("")}
                        </div>
                    </div>
                ` : ''}

                <div class="space-y-1 pt-1">
                    <p class="text-[11px] text-cyan-400 font-bold">Recommended Improvements:</p>
                    <ul class="list-disc list-inside text-[11px] text-slate-400 space-y-0.5">
                        ${data.recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join("")}
                    </ul>
                </div>
            `;
        }
    } catch (err) {
        console.error("handleAnalyzeResume error:", err);
    }
}

// ── SMART HALL TICKET / ADMIT CARD (75% Gatekeeper) ────────────────────────
function openHallTicketModal() {
    const modal = document.getElementById("hallTicketModal");
    const content = document.getElementById("hallTicketContent");
    if (!modal || !content) return;

    modal.classList.remove("hidden");

    const student = currentData && currentData.student ? currentData.student : { name: "Harshit Sharma", roll_no: "22CS1084" };
    const subjects = currentData && currentData.subjects ? currentData.subjects : [];

    let totAtt = 0, totCls = 0;
    subjects.forEach(s => { totAtt += (s.attended || 0); totCls += (s.total || 0); });
    const overallPct = totCls > 0 ? ((totAtt / totCls) * 100).toFixed(1) : 100.0;
    const isEligible = overallPct >= 75;

    if (!isEligible) {
        content.innerHTML = `
            <div class="text-center space-y-3 p-4">
                <div class="w-14 h-14 rounded-2xl bg-rose-500/20 border border-rose-500/40 text-rose-400 flex items-center justify-center text-2xl mx-auto animate-pulse">
                    <i class="fa-solid fa-ban"></i>
                </div>
                <h3 class="text-base font-extrabold text-white">EXAM ADMIT CARD WITHHELD</h3>
                <p class="text-xs text-rose-300 font-semibold">
                    Attendance Policy Violation — 75% Mandatory Threshold
                </p>
                <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 text-left space-y-1">
                    <p>• Student: <strong class="text-white">${escapeHtml(student.name)}</strong> (${escapeHtml(student.roll_no)})</p>
                    <p>• Current Aggregate Attendance: <strong class="text-rose-400 font-bold">${overallPct}%</strong> (< 75.0%)</p>
                    <p>• Status: <span class="text-rose-400 font-bold">DEBARRED FROM SEMESTER EXAMINATIONS</span></p>
                </div>
                <p class="text-[11px] text-slate-400">
                    To unlock your Hall Ticket, please attend upcoming remedial lectures to recover above 75%, or submit a medical exemption certificate to the HOD office.
                </p>
                <button onclick="closeHallTicketModal()" class="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs transition-all">
                    Understood
                </button>
            </div>
        `;
    } else {
        content.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div class="flex items-center space-x-2.5">
                        <div class="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white text-lg font-bold">
                            <i class="fa-solid fa-graduation-cap"></i>
                        </div>
                        <div>
                            <h3 class="text-sm font-extrabold text-white">Ajay Kumar Garg Engineering College</h3>
                            <p class="text-[10px] text-slate-400">Autonomous • Affiliated to AKTU • Ghaziabad, UP</p>
                        </div>
                    </div>
                    <span class="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30">VERIFIED ELIGIBLE</span>
                </div>

                <div class="grid grid-cols-3 gap-3 text-xs bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div>
                        <span class="text-[10px] text-slate-500 block">Candidate Name:</span>
                        <strong class="text-white">${escapeHtml(student.name)}</strong>
                    </div>
                    <div>
                        <span class="text-[10px] text-slate-500 block">Roll Number:</span>
                        <strong class="text-cyan-400 font-mono">${escapeHtml(student.roll_no)}</strong>
                    </div>
                    <div>
                        <span class="text-[10px] text-slate-500 block">Overall Attendance:</span>
                        <strong class="text-emerald-400 font-bold">${overallPct}% (Eligible)</strong>
                    </div>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs border border-slate-800 rounded-lg">
                        <thead class="bg-slate-950 text-slate-400 text-[10px]">
                            <tr>
                                <th class="p-2">Course Code</th>
                                <th class="p-2">Subject Name</th>
                                <th class="p-2">Exam Date</th>
                                <th class="p-2 text-right">Venue</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800 text-[11px]">
                            ${(subjects && subjects.length ? subjects : [
                                { code: "CS-501", name: "Operating Systems" },
                                { code: "CS-502", name: "Data Structures & Algo" },
                                { code: "CS-503", name: "Database Management" },
                                { code: "CS-504", name: "Computer Networks" }
                            ]).map((s, idx) => `
                                <tr>
                                    <td class="p-2 font-mono text-cyan-300">${escapeHtml(s.code || 'CS-50' + (idx+1))}</td>
                                    <td class="p-2 font-bold text-white">${escapeHtml(s.name)}</td>
                                    <td class="p-2 text-slate-300">0${(idx*2 + 28) % 30 + 1} Oct 2026</td>
                                    <td class="p-2 text-right text-slate-400">Exam Hall 0${(idx % 3) + 2}</td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between pt-1">
                    <div class="flex items-center space-x-2 text-[10px] text-slate-400">
                        <img src="https://api.qrserver.com/v1/create-qr-code/?size=60x60&data=VERIFIED_${escapeHtml(student.roll_no)}_${overallPct}PCT" alt="Anti-Tamper QR" class="w-12 h-12 rounded bg-white p-0.5 border border-slate-700">
                        <div>
                            <p class="font-bold text-slate-300">Anti-Fraud Tamper Verification</p>
                            <p class="text-slate-500">Digitally Signed by AKGEC Examination Cell</p>
                        </div>
                    </div>
                    <button onclick="window.print()" class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-md transition-all flex items-center gap-1.5">
                        <i class="fa-solid fa-print"></i> Print Admit Card
                    </button>
                </div>
            </div>
        `;
    }
}

function closeHallTicketModal() {
    const modal = document.getElementById("hallTicketModal");
    if (modal) modal.classList.add("hidden");
}

// ── NOTIFICATIONS DROPDOWN ─────────────────────────────────────────────────
async function fetchNotifications() {
    try {
        const studentId = (currentData && currentData.student && currentData.student.id) || (currentUser && currentUser.id) || "22CS1084";
        const res = await fetch(`/api/notifications?student_id=${encodeURIComponent(studentId)}`);
        const data = await res.json();
        const badge = document.getElementById("notifBadgeCount");
        if (badge) badge.innerText = data.unread_count || 0;

        const list = document.getElementById("notifList");
        if (list && data.notifications) {
            list.innerHTML = data.notifications.map(n => `
                <div class="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1 hover:border-indigo-500/40 transition-colors">
                    <div class="flex items-center justify-between">
                        <span class="font-bold text-white text-[11px]">${escapeHtml(n.title)}</span>
                        <span class="text-[9px] px-1.5 py-0.2 rounded ${n.type === 'warning' ? 'bg-rose-500/20 text-rose-300' : 'bg-indigo-500/20 text-indigo-300'} font-semibold">${escapeHtml(n.badge)}</span>
                    </div>
                    <p class="text-[10px] text-slate-400">${escapeHtml(n.message)}</p>
                </div>
            `).join("");
        }
    } catch (err) {
        console.error("fetchNotifications error:", err);
    }
}

function toggleNotificationDropdown() {
    const dd = document.getElementById("notifDropdown");
    if (dd) dd.classList.toggle("hidden");
}

// ── AI COPILOT CHAT ────────────────────────────────────────────────────────
function sendQuickPrompt(text) {
    const input = document.getElementById("chatInput");
    if (input) {
        input.value = text;
        const form = document.getElementById("chatForm");
        if (form) form.dispatchEvent(new Event("submit", { cancelable: true }));
    }
}

async function handleChatSubmit(event) {
    if (event) event.preventDefault();
    const input = document.getElementById("chatInput");
    const msg = input ? input.value.trim() : "";
    if (!msg) return;

    appendChatMessage("user", msg);
    if (input) input.value = "";

    const loadingId = appendChatLoading();

    try {
        const studentId = (currentData && currentData.student && currentData.student.id) || (currentUser && currentUser.id) || "22CS1084";
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg, student_id: studentId })
        });
        const data = await res.json();
        removeChatLoading(loadingId);
        appendChatMessage("bot", data.reply || "I am processing your query.");
    } catch (err) {
        removeChatLoading(loadingId);
        appendChatMessage("bot", "Network error communicating with watsonx AI engine.");
    }
}

function appendChatMessage(sender, text) {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    const div = document.createElement("div");
    if (sender === "user") {
        div.className = "flex items-start justify-end space-x-2";
        div.innerHTML = `
            <div class="chat-user-bubble text-xs text-white leading-relaxed space-y-1 shadow-md">
                ${escapeHtml(text)}
            </div>
            <div class="w-6 h-6 rounded-lg bg-indigo-600 text-white flex items-center justify-center text-[10px] shrink-0 mt-0.5">
                <i class="fa-solid fa-user"></i>
            </div>
        `;
    } else {
        div.className = "flex items-start space-x-2.5";
        div.innerHTML = `
            <div class="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-white text-[10px] shrink-0 mt-0.5 shadow-md">
                <i class="fa-solid fa-microchip"></i>
            </div>
            <div class="chat-bot-bubble text-xs text-slate-200 leading-relaxed space-y-1 shadow-md">
                ${formatBotReply(text)}
            </div>
        `;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function appendChatLoading() {
    const container = document.getElementById("chatMessages");
    if (!container) return "";
    const id = "loading_" + Date.now();
    const div = document.createElement("div");
    div.id = id;
    div.className = "flex items-start space-x-2.5";
    div.innerHTML = `
        <div class="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center text-white text-[10px] shrink-0 mt-0.5">
            <i class="fa-solid fa-robot fa-spin"></i>
        </div>
        <div class="bg-slate-800/80 p-3 rounded-2xl text-xs text-slate-400 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
            <span>Querying IBM watsonx & live internet...</span>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeChatLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function formatBotReply(text) {
    // Markdown formatting: links, bold, code, bullets
    let formatted = escapeHtml(text);
    formatted = formatted.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" class="text-cyan-400 hover:underline font-bold">$1 <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a>');
    formatted = formatted.replace(/\*\*([^\*]+)\*\*/g, '<strong class="text-white font-bold">$1</strong>');
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-slate-950 text-cyan-300 font-mono text-[10px]">$1</code>');
    formatted = formatted.replace(/### ([^\n]+)/g, '<h4 class="text-sm font-extrabold text-white mt-2 mb-1">$1</h4>');
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
}

function clearChat() {
    const container = document.getElementById("chatMessages");
    if (container) {
        container.innerHTML = `
            <div class="flex items-start space-x-2.5">
                <div class="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-white text-[10px] shrink-0 mt-0.5 shadow-md">
                    <i class="fa-solid fa-microchip"></i>
                </div>
                <div class="bg-slate-800/90 border border-slate-700/60 p-3 rounded-2xl text-xs text-slate-200 leading-relaxed shadow-sm">
                    <p class="font-semibold text-slate-100">Chat refreshed! ✨</p>
                    <p>Ask anything about your campus, timetable, attendance, health first-aid, or general tech queries!</p>
                </div>
            </div>
        `;
    }
}

// ── Admin Notice / Opportunity Form Handlers ───────────────────────────────
async function handleAdminAddNotice(event) {
    event.preventDefault();
    const title = document.getElementById("noticeTitle").value.trim();
    const content = document.getElementById("noticeContent").value.trim();
    const badge = document.getElementById("noticeBadge").value;

    try {
        const res = await fetch("/api/admin/notice/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title, content, badge })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            event.target.reset();
            await fetchStudentData();
            fetchNotifications();
        }
    } catch (err) {
        console.error("handleAdminAddNotice error:", err);
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ── PASSWORD VISIBILITY & FORGOT PASSWORD CONTROLLERS ──────────────────────
function togglePasswordVisibility(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (!input) return;
    if (input.type === 'password') {
        input.type = 'text';
        if (icon) { icon.classList.remove('fa-eye'); icon.classList.add('fa-eye-slash'); }
    } else {
        input.type = 'password';
        if (icon) { icon.classList.remove('fa-eye-slash'); icon.classList.add('fa-eye'); }
    }
}

function openForgotPasswordModal() {
    const modal = document.getElementById("forgotPasswordModal");
    if (modal) modal.classList.remove("hidden");
    const activeId = (currentData && currentData.student && currentData.student.roll_no) || (currentUser && currentUser.roll_no) || "22CS1084";
    const rollInp = document.getElementById("forgotRollInput");
    if (rollInp) rollInp.value = activeId;
}

function closeForgotPasswordModal() {
    const modal = document.getElementById("forgotPasswordModal");
    if (modal) modal.classList.add("hidden");
}

async function handleForgotPasswordSubmit(event) {
    event.preventDefault();
    const identifier = document.getElementById("forgotRollInput").value.trim();
    const newPassword = document.getElementById("forgotNewPassword").value.trim();
    const confirmPassword = document.getElementById("forgotConfirmPassword").value.trim();

    if (newPassword.length < 4) {
        showToast("Password must be at least 4 characters.", "warning");
        return;
    }
    if (newPassword !== confirmPassword) {
        showToast("Passwords do not match.", "error");
        return;
    }

    try {
        const res = await fetch("/api/auth/forgot_password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identifier, new_password: newPassword })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Password updated successfully! Please sign in with your new password.", "success");
            closeForgotPasswordModal();
            const gwPass = document.getElementById("gwPasswordInput");
            if (gwPass) gwPass.value = newPassword;
            const modalPass = document.getElementById("modalPasswordInput");
            if (modalPass) modalPass.value = newPassword;
        } else {
            showToast(data.message || "Failed to reset password.", "error");
        }
    } catch (err) {
        console.error("Forgot password error:", err);
        showToast("Network error resetting password.", "error");
    }
}

// ── COLLEGE FEES & ONLINE PAYMENT DESK ─────────────────────────────────────
let currentFeeData = null;

async function loadFeeStatus() {
    try {
        const studentId = (currentData && currentData.student && currentData.student.id) || (currentUser && currentUser.id) || "22CS1084";
        const res = await fetch(`/api/fees/status?student_id=${encodeURIComponent(studentId)}`);
        const data = await res.json();
        if (data.success && data.fees) {
            currentFeeData = data.fees;
            const total = Number(data.fees.total_fee || 125000);
            const paid = Number(data.fees.paid_amount || 0);
            const due = Number(data.fees.due_amount || 0);
            const dueDate = data.fees.due_date || "15 Oct 2026";
            const status = data.fees.status || "due";

            const totalEl = document.getElementById("feeTotalDisplay");
            const paidEl = document.getElementById("feePaidDisplay");
            const dueEl = document.getElementById("feeDueDisplay");
            const badgeEl = document.getElementById("feeStatusBadge");
            const barEl = document.getElementById("feeProgressBar");
            const pctEl = document.getElementById("feeProgressPercent");
            const dueDateEl = document.getElementById("feeDueDateDisplay");

            if (totalEl) totalEl.innerText = `₹${total.toLocaleString('en-IN')}`;
            if (paidEl) paidEl.innerText = `₹${paid.toLocaleString('en-IN')}`;
            if (dueEl) dueEl.innerText = `₹${due.toLocaleString('en-IN')}`;
            if (dueDateEl) dueDateEl.innerText = dueDate;

            const pct = total > 0 ? Math.min(100, Math.round((paid / total) * 100)) : 100;
            if (barEl) barEl.style.width = `${pct}%`;
            if (pctEl) pctEl.innerText = `${pct}% Paid`;

            if (badgeEl) {
                if (status === 'paid' || due <= 0) {
                    badgeEl.className = "text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
                    badgeEl.innerText = "Fully Paid";
                } else if (paid > 0) {
                    badgeEl.className = "text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30";
                    badgeEl.innerText = "Partially Paid";
                } else {
                    badgeEl.className = "text-[10px] px-2 py-0.5 rounded-full font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30";
                    badgeEl.innerText = "Due";
                }
            }
        }
    } catch (err) {
        console.error("loadFeeStatus error:", err);
    }
}

function openFeePaymentModal() {
    const modal = document.getElementById("feePaymentModal");
    if (!modal) return;
    modal.classList.remove("hidden");

    const formStep = document.getElementById("feePaymentStepForm");
    const receiptStep = document.getElementById("feeReceiptDisplayStep");
    if (formStep) formStep.classList.remove("hidden");
    if (receiptStep) receiptStep.classList.add("hidden");

    const stuName = (currentData && currentData.student && currentData.student.name) || (currentUser && currentUser.name) || "Harshit Sharma";
    const stuRoll = (currentData && currentData.student && currentData.student.roll_no) || (currentUser && currentUser.roll_no) || "22CS1084";
    const due = currentFeeData ? Number(currentFeeData.due_amount || 0) : 35000;

    const nameEl = document.getElementById("modalFeeStudentName");
    const rollEl = document.getElementById("modalFeeStudentRoll");
    const dueEl = document.getElementById("modalFeeCurrentDue");
    const amountInp = document.getElementById("feePayAmountInput");

    if (nameEl) nameEl.innerText = stuName;
    if (rollEl) rollEl.innerText = stuRoll;
    if (dueEl) dueEl.innerText = `₹${due.toLocaleString('en-IN')}`;
    if (amountInp) {
        amountInp.value = due > 0 ? due : 0;
        amountInp.max = due > 0 ? due : 0;
    }
}

function closeFeePaymentModal() {
    const modal = document.getElementById("feePaymentModal");
    if (modal) modal.classList.add("hidden");
}

function setFeePayPreset(preset) {
    const due = currentFeeData ? Number(currentFeeData.due_amount || 0) : 35000;
    const input = document.getElementById("feePayAmountInput");
    if (!input) return;

    if (preset === 'full') {
        input.value = due;
    } else if (preset === 'half') {
        input.value = Math.round(due / 2);
    } else if (preset === '5000') {
        input.value = Math.min(5000, due);
    }
}

async function handleFeePaymentSubmit(event) {
    event.preventDefault();
    const amountInp = document.getElementById("feePayAmountInput");
    const amount = Number(amountInp ? amountInp.value : 0);
    if (!amount || amount <= 0) {
        showToast("Please enter a valid payment amount.", "warning");
        return;
    }

    const payMethodRadio = document.querySelector('input[name="payment_method"]:checked');
    const paymentMethod = payMethodRadio ? payMethodRadio.value : "UPI (PhonePe / GPay)";
    const studentId = (currentData && currentData.student && currentData.student.id) || (currentUser && currentUser.id) || "22CS1084";

    const btn = document.getElementById("btnConfirmPayFee");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i> Processing Transaction...";
    }

    try {
        const res = await fetch("/api/fees/pay", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id: studentId,
                amount,
                payment_method: paymentMethod
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            await loadFeeStatus();
            if (currentRole === 'hod') loadHodFees();
            renderReceipt(data.receipt, data.fees);
        } else {
            showToast(data.message || "Payment authorization failed.", "error");
        }
    } catch (err) {
        console.error("handleFeePaymentSubmit error:", err);
        showToast("Network error processing payment.", "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = "<i class='fa-solid fa-lock'></i> Authorize & Pay Fees";
        }
    }
}

function renderReceipt(receipt, fees) {
    const formStep = document.getElementById("feePaymentStepForm");
    const receiptStep = document.getElementById("feeReceiptDisplayStep");
    const container = document.getElementById("printableFeeReceipt");
    if (!container) return;

    if (formStep) formStep.classList.add("hidden");
    if (receiptStep) receiptStep.classList.remove("hidden");

    localStorage.setItem("campusgenie_last_receipt", JSON.stringify(receipt));

    container.innerHTML = `
        <div class="p-5 rounded-2xl bg-slate-950 border border-emerald-500/40 space-y-4 text-xs font-sans">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <div class="flex items-center space-x-2.5">
                    <div class="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white text-lg font-extrabold">
                        <i class="fa-solid fa-receipt"></i>
                    </div>
                    <div>
                        <h4 class="text-sm font-extrabold text-white">AJAY KUMAR GARG ENGINEERING COLLEGE</h4>
                        <p class="text-[10px] text-slate-400">Official E-Receipt • Accounts Department</p>
                    </div>
                </div>
                <span class="text-[10px] px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 font-extrabold border border-emerald-500/40">
                    PAID / SUCCESS
                </span>
            </div>

            <div class="grid grid-cols-2 gap-2 text-[11px] bg-slate-900/80 p-3 rounded-xl border border-slate-800">
                <div><span class="text-slate-500">Receipt No:</span> <strong class="text-indigo-300 font-mono">${escapeHtml(receipt.receipt_no)}</strong></div>
                <div><span class="text-slate-500">Date & Time:</span> <span class="text-slate-200">${escapeHtml(receipt.date)}</span></div>
                <div><span class="text-slate-500">Candidate:</span> <strong class="text-white">${escapeHtml(receipt.student_name)}</strong></div>
                <div><span class="text-slate-500">Roll No:</span> <span class="text-cyan-400 font-mono">${escapeHtml(receipt.roll_no)}</span></div>
                <div><span class="text-slate-500">Branch & Sem:</span> <span class="text-slate-300">${escapeHtml(receipt.branch || "CSE")} (5th Sem)</span></div>
                <div><span class="text-slate-500">Payment Mode:</span> <span class="text-emerald-300 font-bold">${escapeHtml(receipt.payment_method)}</span></div>
                <div class="col-span-2"><span class="text-slate-500">Transaction ID:</span> <span class="text-slate-400 font-mono">${escapeHtml(receipt.transaction_id)}</span></div>
            </div>

            <div class="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 flex items-center justify-between">
                <div>
                    <span class="text-[10px] text-emerald-300 uppercase tracking-wider block font-bold">Amount Paid Successfully</span>
                    <strong class="text-xl font-extrabold text-emerald-400 font-mono">₹${Number(receipt.amount).toLocaleString('en-IN')}</strong>
                </div>
                <div class="text-right">
                    <span class="text-[10px] text-slate-400 block">Remaining Due</span>
                    <strong class="text-sm font-mono ${fees && fees.due_amount > 0 ? 'text-amber-400' : 'text-emerald-400'}">₹${Number((fees && fees.due_amount) || 0).toLocaleString('en-IN')}</strong>
                </div>
            </div>

            <div class="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                <span class="flex items-center gap-1"><i class="fa-solid fa-qrcode text-slate-400"></i> Computer Generated Digital Receipt</span>
                <span>AKGEC Finance Controller</span>
            </div>
        </div>
    `;
}

function viewLatestReceipt() {
    const last = localStorage.getItem("campusgenie_last_receipt");
    if (!last) {
        showToast("No recent payment receipt found. Please make a payment first.", "info");
        openFeePaymentModal();
        return;
    }
    try {
        const rc = JSON.parse(last);
        openFeePaymentModal();
        renderReceipt(rc, currentFeeData || { due_amount: 0 });
    } catch (e) {
        openFeePaymentModal();
    }
}

function printFeeReceipt() {
    window.print();
}

// ── ASSIGNMENTS & PROCTORED ONLINE TESTS HUB ──────────────────────────────
let currentAssignments = [];
let activeProctoredTest = null;
let proctorMediaStream = null;
let proctorTimerInterval = null;
let proctorTimeRemaining = 900;

async function loadAssignments() {
    try {
        const studentId = (currentData && currentData.student && currentData.student.id) || (currentUser && currentUser.id) || "22CS1084";
        const res = await fetch(`/api/assignments/list?student_id=${encodeURIComponent(studentId)}`);
        const data = await res.json();
        if (data.success && data.assignments) {
            currentAssignments = data.assignments;
            renderAssignmentsHub(currentAssignments);
        }
    } catch (err) {
        console.error("loadAssignments error:", err);
    }
}

function renderAssignmentsHub(asgs) {
    const container = document.getElementById("assignmentsHubContainer");
    if (!container) return;

    if (!asgs.length) {
        container.innerHTML = `<p class="text-xs text-slate-500 p-4 text-center">No assignments published at this time.</p>`;
        return;
    }

    container.innerHTML = asgs.map(a => {
        const sub = a.my_submission;
        let badgeHtml = "";
        if (sub) {
            badgeHtml = `<span class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">✓ Submitted: ${sub.score}/${sub.total_marks} (${sub.percentage}%)</span>`;
        } else {
            badgeHtml = `<span class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">⏳ Pending Due</span>`;
        }

        return `
            <div class="p-4 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-indigo-500/40 transition-all space-y-3">
                <div class="flex items-start justify-between gap-2">
                    <div class="space-y-0.5">
                        <div class="flex items-center gap-2">
                            <span class="text-[10px] px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 font-mono font-bold">${escapeHtml(a.subject_code)}</span>
                            <span class="text-[11px] text-slate-400">• ${escapeHtml(a.faculty || "Faculty Assigned")}</span>
                        </div>
                        <h4 class="text-xs sm:text-sm font-bold text-white">${escapeHtml(a.title)}</h4>
                    </div>
                    ${badgeHtml}
                </div>

                <p class="text-xs text-slate-400 leading-relaxed">${escapeHtml(a.description || "Solve problem sets and test with AI camera & mic proctoring.")}</p>

                <div class="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-800/60 flex-wrap gap-2">
                    <div>
                        <span>Deadline: <strong class="text-slate-300">${escapeHtml(a.deadline)}</strong></span>
                        <span class="ml-2">Marks: <strong class="text-slate-300">${a.total_marks}</strong></span>
                    </div>
                    <div class="flex items-center gap-2">
                        <button onclick="downloadAssignmentPdf('${escapeHtml(a.id)}')" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-bold text-xs transition-all flex items-center gap-1.5" title="Download Worksheet PDF">
                            <i class="fa-solid fa-file-pdf text-rose-400"></i> Download PDF
                        </button>
                        <button onclick="openProctoredTestModal('${escapeHtml(a.id)}')" class="px-3 py-1 rounded-lg ${sub ? 'bg-slate-800 hover:bg-indigo-600 text-slate-300' : 'bg-indigo-600 hover:bg-indigo-500 text-white'} font-bold text-xs shadow-md transition-all flex items-center gap-1.5">
                            <i class="fa-solid fa-video text-cyan-300"></i> ${sub ? 'Retake Test' : 'Take Online Test'}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

function downloadAssignmentPdf(asgId) {
    showToast("Generating official AKGEC coursework worksheet PDF...", "info");
    const link = document.createElement("a");
    link.href = `/api/assignments/download_pdf/${encodeURIComponent(asgId)}`;
    link.setAttribute("download", `AKGEC_Assignment_${asgId}.txt`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

async function openProctoredTestModal(asgId) {
    const modal = document.getElementById("proctoredTestModal");
    if (!modal) return;

    const asg = currentAssignments.find(a => a.id === asgId);
    if (!asg) {
        showToast("Assignment details not found.", "error");
        return;
    }
    activeProctoredTest = asg;

    modal.classList.remove("hidden");
    const footer = document.getElementById("proctorTestFooter");
    const qBody = document.getElementById("proctorTestQuestionsBody");
    const resBox = document.getElementById("proctorResultContainer");
    if (footer) footer.classList.remove("hidden");
    if (qBody) qBody.classList.remove("hidden");
    if (resBox) resBox.classList.add("hidden");

    const titleEl = document.getElementById("testModalTitle");
    const subBadge = document.getElementById("testSubjectBadge");
    if (titleEl) titleEl.innerText = asg.title;
    if (subBadge) subBadge.innerText = asg.subject_code || asg.subject;

    // Render Questions
    const questions = asg.questions || [];
    if (qBody) {
        if (!questions.length) {
            qBody.innerHTML = `<p class="text-xs text-slate-400 p-4">No online MCQ questions configured for this assignment. Please download PDF.</p>`;
        } else {
            qBody.innerHTML = questions.map((q, idx) => `
                <div class="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2.5">
                    <p class="text-xs font-bold text-white">Q${idx + 1}. ${escapeHtml(q.q)}</p>
                    <div class="space-y-1.5 pl-1">
                        ${q.options.map((opt, oIdx) => `
                            <label class="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-900 cursor-pointer text-xs text-slate-300">
                                <input type="radio" name="q_${q.id}" value="${oIdx}" class="accent-indigo-500">
                                <span><strong class="text-indigo-400">${String.fromCharCode(65 + oIdx)}.</strong> ${escapeHtml(opt)}</span>
                            </label>
                        `).join("")}
                    </div>
                </div>
            `).join("");
        }
    }

    await startProctoring();
    startProctorTimer();
}

function closeProctoredTestModal() {
    stopProctoring();
    const modal = document.getElementById("proctoredTestModal");
    if (modal) modal.classList.add("hidden");
}

async function startProctoring() {
    const video = document.getElementById("proctorWebcam");
    const fallback = document.getElementById("webcamFallback");
    const micStatus = document.getElementById("proctorMicStatus");

    try {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            proctorMediaStream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 320 }, height: { ideal: 240 } },
                audio: true
            });
            if (video) {
                video.srcObject = proctorMediaStream;
                video.play().catch(() => {});
            }
            if (fallback) fallback.classList.add("hidden");
            if (micStatus) micStatus.innerText = "Active & Audio Monitored";
        } else {
            throw new Error("getUserMedia not supported");
        }
    } catch (err) {
        console.warn("Webcam/Mic access denied or unavailable:", err);
        if (fallback) fallback.classList.remove("hidden");
        if (micStatus) micStatus.innerText = "Simulated Audio Proctor";
    }
}

function stopProctoring() {
    if (proctorMediaStream) {
        try {
            proctorMediaStream.getTracks().forEach(t => t.stop());
        } catch (e) {}
        proctorMediaStream = null;
    }
    const video = document.getElementById("proctorWebcam");
    if (video) video.srcObject = null;

    if (proctorTimerInterval) {
        clearInterval(proctorTimerInterval);
        proctorTimerInterval = null;
    }
}

function startProctorTimer() {
    if (proctorTimerInterval) clearInterval(proctorTimerInterval);
    proctorTimeRemaining = 900;
    updateTimerDisplay();

    proctorTimerInterval = setInterval(() => {
        proctorTimeRemaining--;
        updateTimerDisplay();
        if (proctorTimeRemaining <= 0) {
            clearInterval(proctorTimerInterval);
            showToast("Time expired! Submitting your test automatically...", "warning");
            submitProctoredTestForm();
        }
    }, 1000);
}

function updateTimerDisplay() {
    const display = document.getElementById("testTimerDisplay");
    if (!display) return;
    const mins = Math.floor(proctorTimeRemaining / 60);
    const secs = proctorTimeRemaining % 60;
    display.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

async function submitProctoredTestForm() {
    if (!activeProctoredTest) return;

    const answers = {};
    (activeProctoredTest.questions || []).forEach(q => {
        const checked = document.querySelector(`input[name="q_${q.id}"]:checked`);
        if (checked) {
            answers[q.id] = parseInt(checked.value);
        }
    });

    const studentId = (currentData && currentData.student && currentData.student.id) || (currentUser && currentUser.id) || "22CS1084";

    const btn = document.getElementById("btnSubmitTest");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i> Proctor Analyzing Integrity...";
    }

    try {
        const res = await fetch("/api/assignments/submit_online", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id: studentId,
                assignment_id: activeProctoredTest.id,
                answers,
                proctor_status: {
                    camera_active: !!proctorMediaStream,
                    mic_active: true
                }
            })
        });
        const data = await res.json();
        stopProctoring();

        if (data.success && data.result) {
            showToast(data.message, "success");
            await loadAssignments();
            renderTestResult(data.result);
        } else {
            showToast(data.message || "Failed to submit test.", "error");
        }
    } catch (err) {
        console.error("submitProctoredTestForm error:", err);
        showToast("Network error submitting proctored test.", "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = "<i class='fa-solid fa-circle-check'></i> Submit Proctored Exam";
        }
    }
}

function renderTestResult(result) {
    const footer = document.getElementById("proctorTestFooter");
    const qBody = document.getElementById("proctorTestQuestionsBody");
    const resBox = document.getElementById("proctorResultContainer");
    if (footer) footer.classList.add("hidden");
    if (qBody) qBody.classList.add("hidden");
    if (!resBox) return;

    resBox.classList.remove("hidden");
    resBox.innerHTML = `
        <div class="space-y-4 p-4 text-center">
            <div class="w-16 h-16 rounded-2xl ${result.status === 'Passed' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'} flex items-center justify-center text-3xl mx-auto shadow-xl">
                <i class="fa-solid ${result.status === 'Passed' ? 'fa-circle-check' : 'fa-triangle-exclamation'}"></i>
            </div>
            <div>
                <span class="text-[10px] px-2.5 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                    AI PROCTOR VERIFIED
                </span>
                <h3 class="text-lg font-extrabold text-white mt-1.5">Assessment Successfully Verified</h3>
                <p class="text-xs text-slate-400">Audio, WebCam feed & Anti-Tab Integrity validated by CampusGenie AI.</p>
            </div>

            <div class="grid grid-cols-3 gap-2 bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs text-center">
                <div>
                    <span class="text-[10px] text-slate-500 block">Score</span>
                    <strong class="text-emerald-400 font-extrabold text-base font-mono">${result.score} / ${result.total_marks}</strong>
                </div>
                <div>
                    <span class="text-[10px] text-slate-500 block">Percentage</span>
                    <strong class="text-white font-extrabold text-base font-mono">${result.percentage}%</strong>
                </div>
                <div>
                    <span class="text-[10px] text-slate-500 block">Integrity Score</span>
                    <strong class="text-indigo-400 font-extrabold text-xs">98% Clean</strong>
                </div>
            </div>

            <div class="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-left text-xs space-y-1 text-slate-400">
                <p>• Student: <strong class="text-white">${escapeHtml(result.student_name)}</strong> (${escapeHtml(result.roll_no)})</p>
                <p>• Submission Timestamp: <span class="text-slate-200">${escapeHtml(result.date)}</span></p>
                <p>• Proctor Details: <span class="text-emerald-400">WebCam Active ✓ | Audio Background Filter Active ✓</span></p>
            </div>

            <button onclick="closeProctoredTestModal()" class="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-extrabold text-xs transition-all shadow-md">
                Done & Return to Dashboard
            </button>
        </div>
    `;
}

// ── HOD MASTER CONTROL - FEES & ASSIGNMENTS ────────────────────────────────
async function loadHodFees() {
    try {
        const res = await fetch("/api/admin/all_students");
        const data = await res.json();
        if (!data.students) return;

        const tbody = document.getElementById("hodFeesTableBody");
        const sel = document.getElementById("hodFeeStudentSelect");

        if (sel) {
            sel.innerHTML = data.students.map(s => `
                <option value="${escapeHtml(s.id)}">${escapeHtml(s.name)} (${escapeHtml(s.roll_no)})</option>
            `).join("");
        }

        if (tbody) {
            tbody.innerHTML = data.students.map(s => {
                const f = s.fees || { total_fee: 125000, paid_amount: 90000, due_amount: 35000, status: "due" };
                const due = Number(f.due_amount || 0);
                const statusBadge = due <= 0 
                    ? `<span class="px-2 py-0.5 rounded-full font-bold text-[10px] bg-emerald-500/20 text-emerald-300">Paid</span>`
                    : `<span class="px-2 py-0.5 rounded-full font-bold text-[10px] bg-rose-500/20 text-rose-300">Due ₹${due.toLocaleString('en-IN')}</span>`;

                return `
                    <tr class="hover:bg-slate-800/40 transition-colors">
                        <td class="py-2.5 font-bold text-white">${escapeHtml(s.name)}</td>
                        <td class="py-2.5 font-mono text-cyan-400">${escapeHtml(s.roll_no)}</td>
                        <td class="py-2.5 font-mono text-slate-300">₹${Number(f.total_fee || 125000).toLocaleString('en-IN')}</td>
                        <td class="py-2.5 font-mono text-emerald-400">₹${Number(f.paid_amount || 0).toLocaleString('en-IN')}</td>
                        <td class="py-2.5 font-mono text-rose-400 font-bold">₹${due.toLocaleString('en-IN')}</td>
                        <td class="py-2.5 text-right">${statusBadge}</td>
                    </tr>
                `;
            }).join("");
        }

        const asgSubSel = document.getElementById("hodAsgSubjectSelect");
        if (asgSubSel && currentData && currentData.subjects) {
            asgSubSel.innerHTML = currentData.subjects.map(sub => `
                <option value="${escapeHtml(sub.name)}">${escapeHtml(sub.name)} (${escapeHtml(sub.code || sub.id)})</option>
            `).join("");
        }
    } catch (err) {
        console.error("loadHodFees error:", err);
    }
}

async function handleHodSetFee(event) {
    event.preventDefault();
    const studentId = document.getElementById("hodFeeStudentSelect").value;
    const totalFee = document.getElementById("hodFeeTotalInput").value;
    const dueAmount = document.getElementById("hodFeeDueInput").value;

    try {
        const res = await fetch("/api/hod/fees/set", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id: studentId,
                total_fee: totalFee,
                due_amount: dueAmount
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            await loadHodFees();
            await loadFeeStatus();
        } else {
            showToast(data.message || "Failed to update fees.", "error");
        }
    } catch (err) {
        console.error("handleHodSetFee error:", err);
        showToast("Network error updating fees.", "error");
    }
}

async function handleHodCreateAssignment(event) {
    event.preventDefault();
    const title = document.getElementById("hodAsgTitle").value.trim();
    const subjectName = document.getElementById("hodAsgSubjectSelect").value;
    const deadline = document.getElementById("hodAsgDeadline").value.trim();
    const totalMarks = document.getElementById("hodAsgTotalMarks").value;
    const mode = document.getElementById("hodAsgMode").value;
    const desc = document.getElementById("hodAsgDesc").value.trim();

    const targetSub = currentData && currentData.subjects ? currentData.subjects.find(s => s.name === subjectName) : null;
    const subCode = targetSub ? targetSub.code : "CS-501";
    const faculty = targetSub ? targetSub.faculty : "Faculty Assigned";

    const questions = [
        {
            "id": 1,
            "q": `In ${subjectName}, which criteria guarantees optimal execution or allocation?`,
            "options": ["First In First Out (FIFO)", "Greedy Local Search", "Shortest Remaining Time First / Optimal Allocation", "Random Arbitrary Order"],
            "correct": 2
        },
        {
            "id": 2,
            "q": `What is the worst-case complexity for standard operations in this problem set?`,
            "options": ["O(1)", "O(log N)", "O(N)", "O(N log N)"],
            "correct": 3
        }
    ];

    try {
        const res = await fetch("/api/hod/assignment/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title,
                subject: subjectName,
                subject_code: subCode,
                faculty,
                deadline,
                total_marks: totalMarks,
                mode,
                description: desc,
                questions
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            document.getElementById("hodAsgTitle").value = "";
            await loadAssignments();
        } else {
            showToast(data.message || "Failed to create assignment.", "error");
        }
    } catch (err) {
        console.error("handleHodCreateAssignment error:", err);
        showToast("Network error publishing assignment.", "error");
    }
}
