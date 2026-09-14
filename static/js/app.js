let currentData = null;

document.addEventListener("DOMContentLoaded", () => {
    fetchStudentData();
});

// View Switcher
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

// Fetch Data
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

// Switch Student
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

// Render Dashboard
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
    const nameDisplay = document.getElementById("activeStudentNameDisplay");
    const rollDisplay = document.getElementById("activeStudentRollDisplay");
    const infoDisplay = document.getElementById("activeStudentInfoDisplay");
    const avatarInitials = document.getElementById("studentAvatarInitials");

    if (nameDisplay) nameDisplay.innerText = student.name || "Student";
    if (rollDisplay) rollDisplay.innerText = student.roll_no || "--";
    if (infoDisplay) infoDisplay.innerText = `${student.branch || 'CSE'} • ${student.semester || '5th Sem'}`;
    if (avatarInitials) {
        const initials = (student.name || "ST").split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
        avatarInitials.innerText = initials;
    }

    // Overall Status
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
        } else if (overallPct < target) {
            overallBadge.className = "text-xs px-3 py-1 rounded-full font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
            overallBadge.innerText = `Attendance Shortage: ${overallPct}% (Req. ${target}%)`;
        } else {
            overallBadge.className = "text-xs px-3 py-1 rounded-full font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
            overallBadge.innerText = `Overall Attendance: ${overallPct}% (Safe)`;
        }
    }

    // 1. RENDER SUBJECTS + MARKS + ATTENDANCE MATRIX
    const subContainer = document.getElementById("subjectsContainer");
    subContainer.innerHTML = "";

    if (subjects.length === 0) {
        subContainer.innerHTML = `
            <div class="p-6 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-slate-400 space-y-1">
                <p class="text-xs font-semibold text-slate-300">No subjects registered yet.</p>
                <p class="text-[11px] text-slate-500">Switch to 'Faculty Hub' above to add subjects to the curriculum.</p>
            </div>
        `;
    } else {
        subjects.forEach(sub => {
            const isSafe = sub.percentage >= target;
            const attStatusColor = isSafe ? "emerald" : "amber";
            const attStatusText = isSafe ? "Safe" : "Shortage (<75%)";

            const isPassed = sub.result === "Pass";
            const marksColor = isPassed ? "emerald" : (sub.result === "Fail" ? "rose" : "slate");

            const card = document.createElement("div");
            card.className = "p-4 rounded-xl bg-slate-950/60 border border-slate-800/90 hover:border-slate-700 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4";
            card.innerHTML = `
                <div class="flex-1">
                    <div class="flex items-center space-x-2 flex-wrap gap-y-1">
                        <span class="font-extrabold text-sm text-slate-100">${sub.name}</span>
                        <span class="text-xs text-indigo-400 font-mono font-semibold">(${sub.code})</span>
                        <span class="text-[10px] px-2 py-0.2 rounded-full font-bold bg-${attStatusColor}-500/20 text-${attStatusColor}-400 border border-${attStatusColor}-500/30">
                            ${attStatusText}
                        </span>
                        <!-- Marks / Result Badge -->
                        <span class="text-[10px] px-2.5 py-0.2 rounded-full font-bold bg-${marksColor}-500/20 text-${marksColor}-400 border border-${marksColor}-500/30">
                            Exam Marks: ${sub.score}/${sub.total_marks} [${sub.result}]
                        </span>
                    </div>

                    <div class="text-[11px] text-slate-400 mt-1.5 flex items-center gap-3">
                        <span>👨‍🏫 Faculty: <strong class="text-slate-300">${sub.faculty}</strong></span>
                        <span>•</span>
                        <span>Attendance: <strong class="text-slate-200">${sub.attended}</strong> / <strong class="text-slate-200">${sub.total}</strong> lectures (${sub.percentage}%)</span>
                    </div>

                    <!-- Attendance Progress Bar -->
                    <div class="w-full bg-slate-800 rounded-full h-1.5 mt-2.5 overflow-hidden">
                        <div class="bg-${attStatusColor}-500 h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(sub.percentage, 100)}%"></div>
                    </div>
                </div>

                <!-- Teacher Controls (Attendance + Marks Action) -->
                <div class="flex items-center space-x-2 shrink-0">
                    <button onclick="logAttendance('${sub.id}', 'present')" title="Mark Present" class="px-2.5 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold flex items-center space-x-1 transition-all">
                        <i class="fa-solid fa-plus text-[10px]"></i>
                        <span>Present</span>
                    </button>
                    <button onclick="logAttendance('${sub.id}', 'absent')" title="Mark Absent" class="px-2.5 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-bold flex items-center space-x-1 transition-all">
                        <i class="fa-solid fa-minus text-[10px]"></i>
                        <span>Absent</span>
                    </button>
                </div>
            `;
            subContainer.appendChild(card);
        });
    }

    // 2. RENDER LECTURE TIMETABLE (Who, Where, When)
    const ttContainer = document.getElementById("timetableContainer");
    ttContainer.innerHTML = "";

    const timetable = data.timetable || [];
    if (timetable.length === 0) {
        ttContainer.innerHTML = `
            <div class="p-5 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-slate-500 text-xs">
                No classes scheduled in timetable. Add lecture slots from Faculty Hub.
            </div>
        `;
    } else {
        timetable.forEach((item, idx) => {
            const row = document.createElement("div");
            row.className = `p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80 flex items-center justify-between text-xs transition-all`;
            row.innerHTML = `
                <div class="flex items-center space-x-3.5">
                    <div class="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex flex-col items-center justify-center text-indigo-300 font-bold shrink-0">
                        <i class="fa-regular fa-clock text-xs"></i>
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-extrabold text-slate-100 text-xs">${item.subject}</span>
                            <span class="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 font-mono">${item.type || 'Theory'}</span>
                        </div>
                        <div class="text-[11px] text-slate-400 mt-0.5 space-x-2">
                            <span>⏰ <strong>${item.time}</strong></span>
                            <span>•</span>
                            <span>📍 <strong>${item.room}</strong></span>
                            <span>•</span>
                            <span>👨‍🏫 <strong>${item.faculty}</strong></span>
                        </div>
                    </div>
                </div>
                <div>
                    <span class="text-[10px] px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 font-semibold">Scheduled</span>
                </div>
            `;
            ttContainer.appendChild(row);
        });
    }

    // 3. RENDER HACKATHONS & JOBS OPPORTUNITIES
    const oppContainer = document.getElementById("opportunitiesContainer");
    oppContainer.innerHTML = "";

    const opps = data.opportunities || [];
    if (opps.length === 0) {
        oppContainer.innerHTML = `
            <div class="p-5 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-slate-500 text-xs">
                No active hackathons or jobs posted yet. Faculty can post from above.
            </div>
        `;
    } else {
        opps.forEach(o => {
            const card = document.createElement("div");
            card.className = "p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs";
            card.innerHTML = `
                <div class="flex-1">
                    <div class="flex items-center space-x-2">
                        <span class="font-bold text-slate-100">${o.title}</span>
                        <span class="text-[10px] px-2 py-0.2 rounded-full font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">${o.category}</span>
                    </div>
                    <p class="text-[11px] text-slate-400 mt-1 leading-relaxed">${o.desc}</p>
                    <p class="text-[10px] text-amber-300 font-mono mt-1">⏰ Deadline: ${o.deadline}</p>
                </div>
                <div class="shrink-0">
                    <a href="${o.link}" target="_blank" class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center space-x-1.5 transition-all shadow-md shadow-indigo-600/25">
                        <span>Apply / View</span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                    </a>
                </div>
            `;
            oppContainer.appendChild(card);
        });
    }
}

// Log Attendance (+ Present / - Absent)
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
            appendBotMessage(`📝 **Live Attendance Logged:**\nMarked **${status.toUpperCase()}** for **${result.student_name}** in ${subId.toUpperCase()}.\n• Updated: ${result.attended}/${result.total} (${result.percentage}%)\n• Status: ${result.status.toUpperCase()}`);
            fetchStudentData();
        }
    } catch (err) {
        console.error("Error updating attendance:", err);
    }
}

// Admin Form Handlers
async function handleAdminAddStudent(e) {
    e.preventDefault();
    const name = document.getElementById("newStudentName").value.trim();
    const roll_no = document.getElementById("newStudentRoll").value.trim();
    const branch = document.getElementById("newStudentBranch").value.trim();

    try {
        const res = await fetch("/api/admin/student/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, roll_no, branch })
        });
        const data = await res.json();
        if (data.success) {
            alert("✅ " + data.message);
            e.target.reset();
            fetchStudentData();
        } else {
            alert("⚠️ " + data.message);
        }
    } catch (err) {
        alert("Failed to add student");
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
            alert("✅ " + data.message);
            e.target.reset();
            fetchStudentData();
        }
    } catch (err) {
        alert("Failed to add subject");
    }
}

async function handleAdminUpdateMarks(e) {
    e.preventDefault();
    if (!currentData || !currentData.student) return alert("Please select a student first!");
    
    const sub_id = document.getElementById("marksSubjectSelect").value;
    const score = document.getElementById("marksScoreInput").value;
    const total = document.getElementById("marksTotalInput").value || 100;

    try {
        const res = await fetch("/api/admin/marks/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id: currentData.student.id,
                subject_id: sub_id,
                score: score,
                total: total
            })
        });
        const data = await res.json();
        if (data.success) {
            alert("✅ " + data.message);
            fetchStudentData();
        } else {
            alert("⚠️ " + data.message);
        }
    } catch (err) {
        alert("Failed to update marks");
    }
}

async function handleAdminAddTimetable(e) {
    e.preventDefault();
    const time = document.getElementById("adminTtTime").value.trim();
    const subject = document.getElementById("adminTtSub").value.trim();
    const room = document.getElementById("adminTtRoom").value.trim();

    try {
        const res = await fetch("/api/admin/timetable/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ time, subject, room })
        });
        const data = await res.json();
        if (data.success) {
            alert("✅ " + data.message);
            e.target.reset();
            fetchStudentData();
        }
    } catch (err) {
        alert("Failed to schedule lecture");
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
            alert("🚀 " + data.message);
            e.target.reset();
            fetchStudentData();
        }
    } catch (err) {
        alert("Failed to post opportunity");
    }
}

// Chatbot Handling
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
        appendBotMessage(data.reply);
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

function appendBotMessage(markdownText) {
    const container = document.getElementById("chatMessages");
    const msgDiv = document.createElement("div");
    msgDiv.className = "flex items-start space-x-2.5";
    
    let formatted = escapeHtml(markdownText)
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');

    msgDiv.innerHTML = `
        <div class="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center text-white text-[10px] shrink-0 mt-0.5 shadow-sm">
            <i class="fa-solid fa-robot"></i>
        </div>
        <div class="chat-bot-bubble space-y-1.5">${formatted}</div>
    `;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
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
