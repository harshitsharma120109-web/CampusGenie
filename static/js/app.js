let currentData = null;

document.addEventListener("DOMContentLoaded", () => {
    fetchStudentData();
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
    toast.className = `pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl text-white text-xs font-semibold bg-gradient-to-r ${colors[type]} border border-white/10`;
    toast.style.cssText = "transform:translateY(16px);opacity:0;transition:all 0.3s ease;";
    toast.innerHTML = `<i class="fa-solid ${icons[type]} text-sm shrink-0"></i><span>${escapeHtml(message)}</span>`;

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

// ── View Switcher ──────────────────────────────────────────────────────────
function switchView(mode) {
    const adminSection = document.getElementById("facultyAdminSection");
    const btnStudent = document.getElementById("btnStudentMode");
    const btnAdmin = document.getElementById("btnAdminMode");

    if (mode === 'admin') {
        adminSection.classList.remove("hidden");
        btnAdmin.className = "px-3 py-1 text-xs font-bold rounded-lg bg-indigo-600 text-white shadow-sm transition-all";
        btnStudent.className = "px-3 py-1 text-xs font-bold rounded-lg text-slate-400 hover:text-slate-200 transition-all";
    } else {
        adminSection.classList.add("hidden");
        btnStudent.className = "px-3 py-1 text-xs font-bold rounded-lg bg-indigo-600 text-white shadow-sm transition-all";
        btnAdmin.className = "px-3 py-1 text-xs font-bold rounded-lg text-slate-400 hover:text-slate-200 transition-all";
    }
}

// ── Fetch Data ─────────────────────────────────────────────────────────────
async function fetchStudentData() {
    try {
        const res = await fetch("/api/student");
        const data = await res.json();
        currentData = data;
        renderDashboard(data);
    } catch (err) {
        console.error("Failed to load student data", err);
    }
}

// ── Switch Student ─────────────────────────────────────────────────────────
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
            fetchStudentData();
        }
    } catch (err) {
        console.error("Failed to switch student:", err);
    }
}

// ── Render Dashboard ───────────────────────────────────────────────────────
function renderDashboard(data) {
    if (!data) return;

    const student = data.student || {};
    const allStudents = data.all_students || [];

    // Header Dropdown
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

    // Populate Marks Student Dropdown in Admin Panel
    const marksStudentSelect = document.getElementById("marksStudentSelect");
    if (marksStudentSelect) {
        marksStudentSelect.innerHTML = `<option value="" disabled selected>Select Student</option>`;
        (data.all_students || []).forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.id;
            opt.innerText = `${s.name} (${s.roll_no})`;
            if (s.id === (data.student || {}).id) opt.selected = true;
            marksStudentSelect.appendChild(opt);
        });
    }

    // Populate Marks Subject Dropdown in Admin Panel
    const marksSubSelect = document.getElementById("marksSubjectSelect");
    if (marksSubSelect) {
        marksSubSelect.innerHTML = `<option value="" disabled selected>Select Subject</option>`;
        (data.raw_subjects || []).forEach(sub => {
            const opt = document.createElement("option");
            opt.value = sub.id;
            opt.innerText = `${sub.name} (${sub.code})`;
            marksSubSelect.appendChild(opt);
        });
    }

    // Active Student Bio
    if (document.getElementById("activeStudentNameDisplay"))
        document.getElementById("activeStudentNameDisplay").innerText = student.name || "Student";
    if (document.getElementById("activeStudentRollDisplay"))
        document.getElementById("activeStudentRollDisplay").innerText = student.roll_no || "--";
    if (document.getElementById("activeStudentInfoDisplay"))
        document.getElementById("activeStudentInfoDisplay").innerText = `${student.branch || 'CSE'} • ${student.semester || '5th Sem'}`;
    if (document.getElementById("studentAvatarInitials")) {
        const initials = (student.name || "ST").split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
        document.getElementById("studentAvatarInitials").innerText = initials;
    }

    // Overall Status Badge
    const subjects = data.subjects || [];
    const totAttended = subjects.reduce((sum, s) => sum + s.attended, 0);
    const totClasses = subjects.reduce((sum, s) => sum + s.total, 0);
    const overallPct = totClasses > 0 ? ((totAttended / totClasses) * 100).toFixed(1) : 0;
    const target = student.target_attendance || 75;

    const overallBadge = document.getElementById("overallBadge");
    if (overallBadge) {
        if (subjects.length === 0) {
            overallBadge.className = "text-xs px-3 py-1 rounded-full font-bold bg-slate-800 text-slate-400";
            overallBadge.innerText = "No Subjects Registered";
        } else if (parseFloat(overallPct) < target) {
            overallBadge.className = "text-xs px-3 py-1 rounded-full font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
            overallBadge.innerText = `⚠️ Shortage: ${overallPct}% (Req. ${target}%)`;
        } else {
            overallBadge.className = "text-xs px-3 py-1 rounded-full font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
            overallBadge.innerText = `✅ Attendance: ${overallPct}% (Safe)`;
        }
    }

    // ── 1. SUBJECT ATTENDANCE & MARKS MATRIX ──
    renderSubjects(subjects, target);

    // ── 2. LECTURE TIMETABLE ──
    renderTimetable(data.timetable || []);

    // ── 3. NOTICES BOARD ──
    renderNotices(data.notices || []);

    // ── 4. OPPORTUNITIES BOARD ──
    renderOpportunities(data.opportunities || []);

    // ── 5. FACULTY MANAGEMENT TABLE (if admin section visible) ──
    renderFacultyManagementTable(data);
}

// ── Render Subject Cards with Shortage Alert ────────────────────────────────
function renderSubjects(subjects, target) {
    const subContainer = document.getElementById("subjectsContainer");
    if (!subContainer) return;
    subContainer.innerHTML = "";

    if (subjects.length === 0) {
        subContainer.innerHTML = `
            <div class="p-6 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-slate-400 space-y-1">
                <p class="text-xs font-semibold text-slate-300">No subjects registered yet.</p>
                <p class="text-[11px] text-slate-500">Switch to 'Faculty Hub' above to add subjects to the curriculum.</p>
            </div>
        `;
        return;
    }

    subjects.forEach(sub => {
        const isSafe = sub.percentage >= target;
        const attStatusColor = isSafe ? "emerald" : "amber";
        const attStatusText = isSafe ? "✅ Safe" : "⚠️ Shortage";

        const isPassed = sub.result === "Pass";
        const marksColor = isPassed ? "emerald" : (sub.result === "Fail" ? "rose" : "slate");

        // Calculate classes needed for 75%
        const needed = calcClassesNeeded(sub.attended, sub.total, target);
        const shortageAlert = !isSafe && needed > 0
            ? `<div class="mt-2 flex items-center gap-1.5 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <i class="fa-solid fa-triangle-exclamation text-amber-400 text-[10px]"></i>
                    <span class="text-[10px] text-amber-300 font-semibold">
                        Attend <strong>${needed}</strong> consecutive class${needed !== 1 ? 'es' : ''} to reach ${target}% target
                    </span>
               </div>`
            : (isSafe && sub.total > 0
                ? `<div class="mt-2 flex items-center gap-1.5 p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                        <i class="fa-solid fa-circle-check text-emerald-400 text-[10px]"></i>
                        <span class="text-[10px] text-emerald-300 font-semibold">
                            You can skip up to <strong>${calcMaxBunks(sub.attended, sub.total, target)}</strong> more class${calcMaxBunks(sub.attended, sub.total, target) !== 1 ? 'es' : ''} and stay at ${target}%
                        </span>
                   </div>`
                : "");

        // Progress bar with 75% threshold marker
        const pct = Math.min(sub.percentage, 100);
        const card = document.createElement("div");
        card.className = `p-4 rounded-xl bg-slate-950/60 border ${isSafe ? 'border-slate-800/90' : 'border-amber-500/20'} hover:border-slate-700 transition-all flex flex-col md:flex-row md:items-start justify-between gap-4`;
        card.innerHTML = `
            <div class="flex-1">
                <div class="flex items-center space-x-2 flex-wrap gap-y-1">
                    <span class="font-extrabold text-sm text-slate-100">${sub.name}</span>
                    <span class="text-xs text-indigo-400 font-mono font-semibold">(${sub.code})</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-${attStatusColor}-500/20 text-${attStatusColor}-400 border border-${attStatusColor}-500/30">
                        ${attStatusText}
                    </span>
                    <span class="text-[10px] px-2.5 py-0.5 rounded-full font-bold bg-${marksColor}-500/20 text-${marksColor}-400 border border-${marksColor}-500/30">
                        Marks: ${sub.score}/${sub.total_marks} [${sub.result}]
                    </span>
                </div>

                <div class="text-[11px] text-slate-400 mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-0.5">
                    <span>👨‍🏫 <strong class="text-slate-300">${sub.faculty}</strong></span>
                    <span>•</span>
                    <span>Attended: <strong class="text-slate-200">${sub.attended}</strong>/<strong class="text-slate-200">${sub.total}</strong> lectures</span>
                    <span>•</span>
                    <span class="font-bold text-${attStatusColor}-400">${sub.percentage}%</span>
                </div>

                <!-- Progress Bar with 75% threshold marker -->
                <div class="relative w-full bg-slate-800 rounded-full h-2 mt-2.5 overflow-visible">
                    <div class="bg-${attStatusColor}-500 h-2 rounded-full transition-all duration-500" style="width: ${pct}%"></div>
                    <!-- 75% threshold line -->
                    <div class="absolute top-0 h-2 border-l-2 border-white/40 border-dashed" style="left: ${target}%;"></div>
                    <span class="absolute -top-4 text-[9px] text-slate-500 font-mono" style="left: calc(${target}% - 8px);">${target}%</span>
                </div>

                ${shortageAlert}
            </div>

            <div class="flex items-center space-x-2 shrink-0 mt-1">
                <button onclick="logAttendance('${sub.id}', 'present')" title="Mark Present for ${sub.name}" class="px-2.5 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold flex items-center space-x-1 transition-all">
                    <i class="fa-solid fa-plus text-[10px]"></i>
                    <span>Present</span>
                </button>
                <button onclick="logAttendance('${sub.id}', 'absent')" title="Mark Absent for ${sub.name}" class="px-2.5 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-bold flex items-center space-x-1 transition-all">
                    <i class="fa-solid fa-minus text-[10px]"></i>
                    <span>Absent</span>
                </button>
            </div>
        `;
        subContainer.appendChild(card);
    });
}

// ── Attendance Math Helpers ────────────────────────────────────────────────
function calcClassesNeeded(attended, total, target = 75) {
    const req = target * total - 100 * attended;
    if (req <= 0) return 0;
    return Math.ceil(req / (100 - target));
}

function calcMaxBunks(attended, total, target = 75) {
    // max absent while keeping (attended / (total + x)) * 100 >= target
    // attended / (total + x) >= target/100  →  x <= attended*100/target - total
    const max = Math.floor((attended * 100) / target) - total;
    return Math.max(0, max);
}

// ── Render Timetable with Status Colors ────────────────────────────────────
function renderTimetable(timetable) {
    const ttContainer = document.getElementById("timetableContainer");
    if (!ttContainer) return;
    ttContainer.innerHTML = "";

    if (timetable.length === 0) {
        ttContainer.innerHTML = `
            <div class="p-5 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-slate-500 text-xs">
                No classes scheduled. Add lecture slots from Faculty Hub.
            </div>
        `;
        return;
    }

    const statusConfig = {
        completed: { badge: "Completed", badgeClass: "bg-slate-700 text-slate-400", iconClass: "bg-slate-700/40 border-slate-700/40 text-slate-500", rowBorder: "border-slate-800/60" },
        ongoing:   { badge: "● Live Now", badgeClass: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse", iconClass: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", rowBorder: "border-emerald-500/20" },
        upcoming:  { badge: "Upcoming", badgeClass: "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30", iconClass: "bg-indigo-500/10 border-indigo-500/20 text-indigo-300", rowBorder: "border-slate-800/80" }
    };

    timetable.forEach((item, idx) => {
        const cfg = statusConfig[item.status] || statusConfig.upcoming;
        const typeIcon = item.type === "Practical" ? "fa-flask" : "fa-chalkboard";

        const row = document.createElement("div");
        row.className = `p-3.5 rounded-xl bg-slate-950/50 border ${cfg.rowBorder} flex items-center justify-between text-xs transition-all hover:border-slate-700`;
        row.innerHTML = `
            <div class="flex items-center space-x-3.5">
                <div class="w-10 h-10 rounded-xl ${cfg.iconClass} border flex flex-col items-center justify-center font-bold shrink-0">
                    <i class="fa-solid ${typeIcon} text-xs"></i>
                </div>
                <div>
                    <div class="flex items-center space-x-2">
                        <span class="font-extrabold text-slate-100 text-xs">${item.subject}</span>
                        <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">${item.type || 'Theory'}</span>
                    </div>
                    <div class="text-[11px] text-slate-400 mt-0.5 flex flex-wrap gap-x-2">
                        <span>⏰ <strong class="text-slate-300">${item.time}</strong></span>
                        <span>•</span>
                        <span>📍 <strong class="text-cyan-300">${item.room}</strong></span>
                        <span>•</span>
                        <span>👨‍🏫 <strong class="text-slate-300">${item.faculty}</strong></span>
                    </div>
                </div>
            </div>
            <div>
                <span class="text-[10px] px-2.5 py-1 rounded-full font-semibold ${cfg.badgeClass}">${cfg.badge}</span>
            </div>
        `;
        ttContainer.appendChild(row);
    });
}

// ── Render Notices Board ────────────────────────────────────────────────────
function renderNotices(notices) {
    const noticesContainer = document.getElementById("noticesContainer");
    if (!noticesContainer) return;
    noticesContainer.innerHTML = "";

    if (notices.length === 0) {
        noticesContainer.innerHTML = `<p class="text-[11px] text-slate-500 text-center py-2">No active notices from college administration.</p>`;
        return;
    }

    notices.forEach(n => {
        const urgentClass = n.badge === "Urgent"
            ? "border-rose-500/30 bg-rose-500/5"
            : "border-slate-800/80 bg-slate-950/40";
        const badgeClass = n.badge === "Urgent"
            ? "bg-rose-500/20 text-rose-400 border-rose-500/30"
            : "bg-slate-700 text-slate-300";

        const div = document.createElement("div");
        div.className = `p-3 rounded-xl border ${urgentClass} text-xs`;
        div.innerHTML = `
            <div class="flex items-center justify-between mb-1">
                <span class="font-bold text-slate-100">${n.title}</span>
                <span class="text-[10px] px-2 py-0.5 rounded-full border font-semibold ${badgeClass}">${n.badge || 'Notice'}</span>
            </div>
            <p class="text-slate-400 leading-relaxed">${n.content}</p>
            <p class="text-[10px] text-slate-500 mt-1">📅 ${n.date}</p>
        `;
        noticesContainer.appendChild(div);
    });
}

// ── Render Opportunities Board ─────────────────────────────────────────────
function renderOpportunities(opps) {
    const oppContainer = document.getElementById("opportunitiesContainer");
    if (!oppContainer) return;
    oppContainer.innerHTML = "";

    if (opps.length === 0) {
        oppContainer.innerHTML = `
            <div class="p-5 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-slate-500 text-xs">
                No active hackathons or jobs posted yet. Faculty can post from above.
            </div>
        `;
        return;
    }

    opps.forEach(o => {
        const card = document.createElement("div");
        card.className = "p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs";
        card.innerHTML = `
            <div class="flex-1">
                <div class="flex items-center space-x-2 flex-wrap gap-y-1">
                    <span class="font-bold text-slate-100">${o.title}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">${o.category}</span>
                    ${o.badge ? `<span class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/20">${o.badge}</span>` : ""}
                </div>
                <p class="text-[11px] text-slate-400 mt-1 leading-relaxed">${o.desc || ''}</p>
                <p class="text-[10px] text-amber-300 font-mono mt-1">⏰ Deadline: ${o.deadline}</p>
            </div>
            <div class="shrink-0">
                <a href="${o.link}" target="_blank" rel="noopener" class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center space-x-1.5 transition-all shadow-md shadow-indigo-600/25">
                    <span>Apply / View</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
            </div>
        `;
        oppContainer.appendChild(card);
    });
}

// ── Faculty Management Table (ALL students × subjects) ────────────────────
async function renderFacultyManagementTable(data) {
    const tableContainer = document.getElementById("facultyMgmtTableContainer");
    if (!tableContainer) return;

    // Fetch full data for every student from the admin endpoint
    let allStudents = [];
    let subjects = data.raw_subjects || [];
    try {
        const res = await fetch("/api/admin/all_students");
        const adminData = await res.json();
        allStudents = adminData.students || [];
        if (adminData.subjects && adminData.subjects.length > 0) subjects = adminData.subjects;
    } catch (e) {
        allStudents = [data.student].filter(Boolean);
    }

    if (allStudents.length === 0 || subjects.length === 0) {
        tableContainer.innerHTML = `<p class="text-xs text-slate-500 text-center py-4">Enroll students and add subjects to view the management table.</p>`;
        return;
    }

    const target = 75;

    // Build header columns per subject
    const subHeaders = subjects.map(s =>
        `<th class="px-3 py-2.5 font-semibold text-center min-w-[120px]">${s.name}<br><span class="font-mono text-[10px] text-indigo-400">${s.code}</span></th>`
    ).join("");

    // Build one row per student
    const rows = allStudents.map(stu => {
        const attMap = stu.attendance || {};
        const marksMap = stu.marks || {};
        const subCells = subjects.map(sub => {
            const att = attMap[sub.id] || { attended: 0, total: 0, percentage: 0 };
            const mark = marksMap[sub.id] || { score: "—", total: 100, status: "Pending" };
            const isSafe = att.percentage >= target;
            const attBadge = att.total > 0
                ? (isSafe
                    ? `<span class="text-emerald-400 font-bold">${att.percentage}%</span>`
                    : `<span class="text-amber-400 font-bold">⚠️ ${att.percentage}%</span>`)
                : `<span class="text-slate-600">—</span>`;
            const markBadge = mark.status === "Pass"
                ? `<span class="text-emerald-400 font-bold">${mark.score}/${mark.total}</span>`
                : mark.status === "Fail"
                ? `<span class="text-rose-400 font-bold">${mark.score}/${mark.total} ✗</span>`
                : `<span class="text-slate-500 italic">Pending</span>`;
            return `<td class="px-3 py-2.5 text-center text-[11px]">
                <div>${attBadge}</div>
                <div class="text-[10px] text-slate-500">${att.attended}/${att.total} cls</div>
                <div class="mt-0.5">${markBadge}</div>
            </td>`;
        }).join("");

        const totalAtt = subjects.reduce((s, sub) => s + (attMap[sub.id] || {attended:0}).attended, 0);
        const totalCls = subjects.reduce((s, sub) => s + (attMap[sub.id] || {total:0}).total, 0);
        const overallPct = totalCls > 0 ? ((totalAtt / totalCls) * 100).toFixed(1) : "—";
        const overallBadgeHtml = totalCls > 0
            ? (parseFloat(overallPct) >= target
                ? `<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">${overallPct}% ✅</span>`
                : `<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400">⚠️ ${overallPct}%</span>`)
            : `<span class="text-slate-500 text-[10px]">No data</span>`;

        return `<tr class="border-b border-slate-800/60 hover:bg-slate-900/30 transition-colors">
            <td class="px-3 py-2.5 font-bold text-slate-200 whitespace-nowrap">${stu.name}</td>
            <td class="px-3 py-2.5 font-mono text-indigo-300 text-[10px] whitespace-nowrap">${stu.roll_no}</td>
            <td class="px-3 py-2.5 text-slate-400 text-[10px] whitespace-nowrap">${stu.branch || '—'}<br>${stu.semester || ''}</td>
            <td class="px-3 py-2.5 text-center">${overallBadgeHtml}</td>
            ${subCells}
        </tr>`;
    }).join("");

    tableContainer.innerHTML = `
        <div class="overflow-x-auto rounded-xl border border-slate-800">
            <table class="w-full text-xs">
                <thead>
                    <tr class="bg-slate-900/80 text-slate-400 text-left sticky top-0 z-10">
                        <th class="px-3 py-2.5 font-semibold whitespace-nowrap">Student</th>
                        <th class="px-3 py-2.5 font-semibold whitespace-nowrap">Roll No</th>
                        <th class="px-3 py-2.5 font-semibold whitespace-nowrap">Branch / Sem</th>
                        <th class="px-3 py-2.5 font-semibold text-center whitespace-nowrap">Overall Att.</th>
                        ${subHeaders}
                    </tr>
                </thead>
                <tbody class="text-slate-300">
                    ${rows}
                </tbody>
            </table>
        </div>
        <p class="text-[10px] text-slate-600 mt-2 text-right">Each cell: Attendance % • Classes Attended • Exam Marks (Pass/Fail)</p>
    `;
}

// ── Log Attendance (+ Present / - Absent) ─────────────────────────────────
async function logAttendance(subId, status) {
    if (!currentData || !currentData.student) return;
    try {
        const res = await fetch("/api/attendance/mark", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id: currentData.student.id,
                subject_id: subId,
                status: status
            })
        });
        const result = await res.json();
        if (result.success) {
            const statusLabel = status === "present" ? "✅ Present" : "❌ Absent";
            showToast(`${statusLabel} marked for ${subId.toUpperCase()} — ${result.percentage}%`, status === "present" ? "success" : "warning");

            const warningNote = result.status === "warning"
                ? `\n⚠️ **Attendance Shortage!** Need **${result.classes_needed}** more consecutive classes to reach ${currentData.student.target_attendance || 75}%.`
                : "";
            appendBotMessage(`📝 **Attendance Logged** — ${result.student_name}\n• Subject: **${subId.toUpperCase()}** → Marked **${status.toUpperCase()}**\n• Updated: ${result.attended}/${result.total} (${result.percentage}%) — **${result.status.toUpperCase()}**${warningNote}`, null);
            fetchStudentData();
        }
    } catch (err) {
        console.error("Error updating attendance:", err);
        showToast("Failed to log attendance", "error");
    }
}

// ── Admin Form Handlers ────────────────────────────────────────────────────
async function handleAdminAddStudent(e) {
    e.preventDefault();
    const name = document.getElementById("newStudentName").value.trim();
    const roll_no = document.getElementById("newStudentRoll").value.trim();
    const branch = document.getElementById("newStudentBranch").value.trim();
    const semester = document.getElementById("newStudentSemester").value.trim();

    try {
        const res = await fetch("/api/admin/student/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, roll_no, branch, semester })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            e.target.reset();
            fetchStudentData();
        } else {
            showToast(data.message, "error");
        }
    } catch (err) {
        showToast("Failed to add student", "error");
    }
}

async function handleAdminAddSubject(e) {
    e.preventDefault();
    const name = document.getElementById("adminSubName").value.trim();
    const code = document.getElementById("adminSubCode").value.trim();
    const faculty = document.getElementById("adminSubFaculty").value.trim();

    try {
        const res = await fetch("/api/admin/subject/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, code, faculty })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            e.target.reset();
            fetchStudentData();
        } else {
            showToast(data.message || "Failed to add subject", "error");
        }
    } catch (err) {
        showToast("Failed to add subject", "error");
    }
}

async function handleAdminUpdateMarks(e) {
    e.preventDefault();
    const studentEl = document.getElementById("marksStudentSelect");
    const student_id = studentEl ? studentEl.value : (currentData && currentData.student ? currentData.student.id : null);
    if (!student_id) {
        showToast("Please select a student!", "warning");
        return;
    }

    const sub_id = document.getElementById("marksSubjectSelect").value;
    const score = document.getElementById("marksScoreInput").value;
    const total = document.getElementById("marksTotalInput").value || 100;

    try {
        const res = await fetch("/api/admin/marks/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id: student_id,
                subject_id: sub_id,
                score: score,
                total: total
            })
        });
        const data = await res.json();
        if (data.success) {
            const type = data.status === "Pass" ? "success" : "warning";
            showToast(data.message, type);
            fetchStudentData();
        } else {
            showToast(data.message, "error");
        }
    } catch (err) {
        showToast("Failed to update marks", "error");
    }
}

async function handleAdminAddTimetable(e) {
    e.preventDefault();
    const time = document.getElementById("adminTtTime").value.trim();
    const subject = document.getElementById("adminTtSub").value.trim();
    const room = document.getElementById("adminTtRoom").value.trim();
    const faculty = (document.getElementById("adminTtFaculty") || {}).value || "";
    const type = (document.getElementById("adminTtType") || {}).value || "Theory";

    try {
        const res = await fetch("/api/admin/timetable/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ time, subject, room, faculty, type })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            e.target.reset();
            fetchStudentData();
        } else {
            showToast(data.message || "Failed to schedule lecture", "error");
        }
    } catch (err) {
        showToast("Failed to schedule lecture", "error");
    }
}

async function handleAdminAddNotice(e) {
    e.preventDefault();
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
            e.target.reset();
            fetchStudentData();
        } else {
            showToast(data.message || "Failed to post notice", "error");
        }
    } catch (err) {
        showToast("Failed to post notice", "error");
    }
}

async function handleAdminAddOpportunity(e) {
    e.preventDefault();
    const title = document.getElementById("oppTitle").value.trim();
    const deadline = document.getElementById("oppDeadline").value.trim();
    const link = document.getElementById("oppLink").value.trim();

    try {
        const res = await fetch("/api/admin/opportunity/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title, deadline, link })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            e.target.reset();
            fetchStudentData();
        } else {
            showToast(data.message || "Failed to post opportunity", "error");
        }
    } catch (err) {
        showToast("Failed to post opportunity", "error");
    }
}

// ── Chatbot ────────────────────────────────────────────────────────────────
async function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById("chatInput");
    const msg = input.value.trim();
    if (!msg) return;

    appendUserMessage(msg);
    input.value = "";

    const typingId = showTypingIndicator();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        removeTypingIndicator(typingId);
        appendBotMessage(data.reply, data.action);
    } catch (err) {
        removeTypingIndicator(typingId);
        appendBotMessage("⚠️ Unable to connect to server. Ensure `python app.py` is running.");
    }
}

function sendQuickPrompt(text) {
    document.getElementById("chatInput").value = text;
    handleChatSubmit(new Event("submit"));
}

function appendUserMessage(text) {
    const container = document.getElementById("chatMessages");
    const msgDiv = document.createElement("div");
    msgDiv.className = "flex justify-end";
    msgDiv.innerHTML = `<div class="chat-user-bubble">${escapeHtml(text)}</div>`;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

function appendBotMessage(markdownText, action) {
    const container = document.getElementById("chatMessages");
    const msgDiv = document.createElement("div");
    msgDiv.className = "flex items-start space-x-2.5";

    // Choose avatar colour based on message type
    const avatarClass = action === "health"
        ? "bg-rose-600"
        : action === "academic"
        ? "bg-indigo-600"
        : "bg-indigo-600";
    const avatarIcon = action === "health"
        ? "fa-heart-pulse"
        : action === "academic"
        ? "fa-book-open"
        : "fa-robot";

    // Structured markdown renderer
    const formatted = renderMarkdown(markdownText);

    msgDiv.innerHTML = `
        <div class="w-6 h-6 rounded-lg ${avatarClass} flex items-center justify-center text-white text-[10px] shrink-0 mt-0.5 shadow-sm">
            <i class="fa-solid ${avatarIcon}"></i>
        </div>
        <div class="chat-bot-bubble space-y-1">${formatted}</div>
    `;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

// ── Markdown renderer for chat bot messages ────────────────────────────────
function renderMarkdown(text) {
    if (!text) return '';

    // Split into lines, process each
    const lines = text.split('\n');
    const out = [];
    let inCode = false;

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];

        // Fenced code block toggle (``` ... ```)
        if (line.trim().startsWith('```')) {
            if (!inCode) {
                out.push('<pre class="bg-slate-950 border border-slate-700/60 rounded-lg px-3 py-2 text-[10px] text-cyan-300 overflow-x-auto font-mono mt-1 mb-1">');
                inCode = true;
            } else {
                out.push('</pre>');
                inCode = false;
            }
            continue;
        }
        if (inCode) {
            out.push(escapeHtml(line));
            continue;
        }

        // Horizontal rule --- (section divider)
        if (line.trim() === '---') {
            out.push('<hr class="border-slate-700/50 my-2">');
            continue;
        }

        // ### Heading
        if (line.startsWith('### ')) {
            const headText = renderInline(line.slice(4));
            out.push(`<p class="font-extrabold text-slate-100 text-[12px] mt-1">${headText}</p>`);
            continue;
        }

        // ## Heading
        if (line.startsWith('## ')) {
            const headText = renderInline(line.slice(3));
            out.push(`<p class="font-extrabold text-slate-50 text-[13px] mt-1">${headText}</p>`);
            continue;
        }

        // Bullet line starting with • or - or *
        if (/^[•\-\*] /.test(line.trim())) {
            const content = renderInline(line.trim().slice(2));
            out.push(`<div class="flex items-start gap-1.5 text-[11px]"><span class="text-indigo-400 mt-0.5 shrink-0">•</span><span>${content}</span></div>`);
            continue;
        }

        // Empty line → spacer
        if (line.trim() === '') {
            out.push('<div class="h-1"></div>');
            continue;
        }

        // Italic-only disclaimer lines (wrapped in * ... *)
        if (line.trim().startsWith('*') && line.trim().endsWith('*') && !line.trim().startsWith('**')) {
            out.push(`<p class="text-[10px] text-slate-500 italic">${renderInline(line)}</p>`);
            continue;
        }

        // Regular paragraph line
        out.push(`<p class="text-[11px] leading-relaxed">${renderInline(line)}</p>`);
    }

    if (inCode) out.push('</pre>');  // close unclosed code block
    return out.join('');
}

// ── Inline markdown: **bold**, *italic*, `code` ────────────────────────────
function renderInline(text) {
    return escapeHtml(text)
        // inline `code` — must come BEFORE bold/italic to avoid double-escaping
        .replace(/`([^`]+)`/g, '<code class="bg-slate-950 text-cyan-300 font-mono rounded px-1 text-[10px]">$1</code>')
        // **bold**
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-slate-100">$1</strong>')
        // *italic*
        .replace(/\*(.*?)\*/g, '<em class="text-slate-300">$1</em>');
}

function showTypingIndicator() {
    const container = document.getElementById("chatMessages");
    const id = "typing-" + Date.now();
    const div = document.createElement("div");
    div.id = id;
    div.className = "flex items-start space-x-2.5";
    div.innerHTML = `
        <div class="w-6 h-6 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 text-[10px] shrink-0 mt-0.5">
            <i class="fa-solid fa-ellipsis animate-pulse"></i>
        </div>
        <div class="chat-bot-bubble py-2 px-3 text-slate-400 text-[11px] italic">CampusGenie is thinking...</div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const elem = document.getElementById(id);
    if (elem) elem.remove();
}

function clearChat() {
    const container = document.getElementById("chatMessages");
    container.innerHTML = `
        <div class="flex items-start space-x-2.5">
            <div class="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center text-white text-[10px] shrink-0 mt-0.5">
                <i class="fa-solid fa-bolt"></i>
            </div>
            <div class="chat-bot-bubble">Chat cleared! Ask about academic doubts, health/medicines, marks, or timetable.</div>
        </div>
    `;
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return (text || '').replace(/[&<>"']/g, m => map[m]);
}
