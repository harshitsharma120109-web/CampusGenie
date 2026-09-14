let currentData = null;
let breathingInterval = null;

// Initial Load
document.addEventListener("DOMContentLoaded", () => {
    fetchStudentData();
});

// View Switcher (Student vs Faculty/Admin)
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

// Fetch Student Data & Render
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

// Handle Switching Student from Dropdown
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

// Render Dashboard (Multi-Student aware)
function renderDashboard(data) {
    if (!data) return;

    const student = data.student || {};
    const allStudents = data.all_students || [];

    // Populate Student Switcher Dropdown in Header
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

    // Active Student Details Card
    const nameDisplay = document.getElementById("activeStudentNameDisplay");
    const rollDisplay = document.getElementById("activeStudentRollDisplay");
    const infoDisplay = document.getElementById("activeStudentInfoDisplay");
    const avatarInitials = document.getElementById("studentAvatarInitials");

    if (nameDisplay) nameDisplay.innerText = student.name || "No Student Selected";
    if (rollDisplay) rollDisplay.innerText = `Roll: ${student.roll_no || '--'}`;
    if (infoDisplay) infoDisplay.innerText = `${student.branch || 'Branch'} • ${student.semester || 'Semester'}`;
    if (avatarInitials) {
        const initials = (student.name || "ST").split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
        avatarInitials.innerText = initials;
    }

    // Welcome Header in Chatbot
    const welcomeHeading = document.getElementById("chatWelcomeHeading");
    if (welcomeHeading) {
        welcomeHeading.innerText = `Welcome ${student.name || 'Student'}! 👋 I'm your AI Copilot.`;
    }

    // Overall Attendance
    const subjects = data.subjects || [];
    const totAttended = subjects.reduce((sum, s) => sum + s.attended, 0);
    const totClasses = subjects.reduce((sum, s) => sum + s.total, 0);
    const overallPct = totClasses > 0 ? ((totAttended / totClasses) * 100).toFixed(1) : 0;
    const target = student.target_attendance || 75;

    const overallPctElem = document.getElementById("overallPercentage");
    const overallBadge = document.getElementById("overallBadge");
    const overallSummary = document.getElementById("overallSummaryText");

    overallPctElem.innerText = subjects.length > 0 ? `${overallPct}%` : "0%";

    if (subjects.length === 0) {
        overallBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-bold bg-slate-800 text-slate-400";
        overallBadge.innerText = "No Subjects";
        overallSummary.innerHTML = `Switch to <strong>Faculty / Admin Mode</strong> above to add subjects.`;
    } else if (overallPct < target) {
        overallBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
        overallBadge.innerText = "Shortage Alert";
        overallSummary.innerHTML = `<span class="text-amber-400 font-semibold">⚠️ Attention:</span> You are ${ (target - overallPct).toFixed(1) }% below the 75% rule.`;
    } else {
        overallBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        overallBadge.innerText = "Safe & Eligible";
        overallSummary.innerHTML = `<span class="text-emerald-400 font-semibold">✅ Eligible:</span> Meets exam attendance criteria!`;
    }

    // Scheduled Classes Count & Hint
    const timetable = data.timetable || [];
    const totalClassesCount = document.getElementById("totalClassesCount");
    const nextClassHint = document.getElementById("nextClassHint");

    if (totalClassesCount) totalClassesCount.innerText = timetable.length;
    if (nextClassHint) {
        if (timetable.length > 0) {
            nextClassHint.innerText = `Next: ${timetable[0].subject} (${timetable[0].time})`;
        } else {
            nextClassHint.innerText = "No classes scheduled yet";
        }
    }

    // Render Subjects
    const subContainer = document.getElementById("subjectsContainer");
    subContainer.innerHTML = "";

    if (subjects.length === 0) {
        subContainer.innerHTML = `
            <div class="p-6 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-slate-400 space-y-2">
                <i class="fa-solid fa-book-open text-2xl text-slate-600"></i>
                <p class="text-xs font-semibold text-slate-300">No subjects registered for ${student.name || 'this student'}.</p>
                <p class="text-[11px] text-slate-500">Click <strong>'Faculty / Admin Mode'</strong> above to add college subjects and start tracking attendance.</p>
            </div>
        `;
    } else {
        subjects.forEach(sub => {
            const isSafe = sub.percentage >= target;
            const statusColor = isSafe ? "emerald" : "amber";
            const statusText = isSafe ? "Safe" : "Warning (<75%)";

            const card = document.createElement("div");
            card.className = "p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3";
            card.innerHTML = `
                <div class="flex-1">
                    <div class="flex items-center space-x-2">
                        <span class="font-bold text-xs text-slate-100">${sub.name}</span>
                        <span class="text-[10px] text-slate-400 font-mono">(${sub.code})</span>
                        <span class="text-[10px] px-2 py-0.2 rounded-full font-semibold bg-${statusColor}-500/20 text-${statusColor}-400 border border-${statusColor}-500/30">
                            ${statusText}
                        </span>
                    </div>
                    <div class="text-[11px] text-slate-400 mt-1 flex items-center gap-3">
                        <span>👨‍🏫 ${sub.faculty}</span>
                        <span>•</span>
                        <span class="font-medium text-slate-300"><strong>${sub.attended}</strong> attended of <strong>${sub.total}</strong> (${sub.percentage}%)</span>
                    </div>
                    <div class="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
                        <div class="bg-${statusColor}-500 h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(sub.percentage, 100)}%"></div>
                    </div>
                </div>

                <div class="flex items-center space-x-2 shrink-0">
                    <button onclick="logAttendance('${sub.id}', 'present')" title="Mark Present" class="px-2.5 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-semibold flex items-center space-x-1 transition-all">
                        <i class="fa-solid fa-plus text-[10px]"></i>
                        <span>Present</span>
                    </button>
                    <button onclick="logAttendance('${sub.id}', 'absent')" title="Mark Absent" class="px-2.5 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold flex items-center space-x-1 transition-all">
                        <i class="fa-solid fa-minus text-[10px]"></i>
                        <span>Absent</span>
                    </button>
                    <button onclick="deleteSubject('${sub.id}')" title="Delete Subject" class="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all">
                        <i class="fa-solid fa-trash-can text-xs"></i>
                    </button>
                </div>
            `;
            subContainer.appendChild(card);
        });
    }

    // Render Timetable
    const ttContainer = document.getElementById("timetableContainer");
    ttContainer.innerHTML = "";

    if (timetable.length === 0) {
        ttContainer.innerHTML = `
            <div class="p-5 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-slate-400 space-y-1">
                <p class="text-xs font-semibold text-slate-300">No classes in timetable yet.</p>
                <p class="text-[11px] text-slate-500">Add lecture timings from Admin Mode.</p>
            </div>
        `;
    } else {
        timetable.forEach((item, idx) => {
            const row = document.createElement("div");
            row.className = `p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 flex items-center justify-between text-xs transition-all`;
            row.innerHTML = `
                <div class="flex items-center space-x-3">
                    <span class="font-mono text-indigo-400 font-semibold text-[11px] w-36">${item.time}</span>
                    <div>
                        <p class="font-bold text-slate-200">${item.subject}</p>
                        <p class="text-[10px] text-slate-400">📍 ${item.room} • ${item.faculty}</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">Scheduled</span>
                    <button onclick="deleteTimetable(${idx})" title="Remove lecture" class="text-slate-500 hover:text-rose-400 p-1">
                        <i class="fa-solid fa-xmark text-xs"></i>
                    </button>
                </div>
            `;
            ttContainer.appendChild(row);
        });
    }

    // Render Notices
    const noticesContainer = document.getElementById("noticesContainer");
    if (noticesContainer) {
        noticesContainer.innerHTML = "";
        const notices = data.notices || [];
        if (notices.length === 0) {
            noticesContainer.innerHTML = `
                <div class="p-4 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-slate-500 text-xs">
                    No active notices posted.
                </div>
            `;
        } else {
            notices.forEach(n => {
                const item = document.createElement("div");
                item.className = "p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-start space-x-3 text-xs";
                item.innerHTML = `
                    <div class="w-2 h-2 rounded-full bg-amber-400 mt-1.5 shrink-0"></div>
                    <div class="flex-1">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-200">${n.title}</span>
                            <span class="text-[10px] px-2 py-0.2 rounded-full bg-amber-500/20 text-amber-300 font-mono">${n.date}</span>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-1">${n.content}</p>
                    </div>
                `;
                noticesContainer.appendChild(item);
            });
        }
    }
}

// Log Attendance (+ Present / - Absent)
async function logAttendance(subId, status) {
    try {
        const res = await fetch("/api/attendance/mark", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subject_id: subId, status: status })
        });
        const result = await res.json();
        if (result.success) {
            appendBotMessage(`📝 **Quick Attendance Update:**\nMarked **${status.toUpperCase()}** for **${result.subject.name}**.\n• Current: ${result.subject.attended}/${result.subject.total} (${result.subject.percentage}%)\n• Overall: ${result.overall_percentage}%`);
            fetchStudentData();
        }
    } catch (err) {
        console.error("Error updating attendance:", err);
    }
}

// Admin / Faculty Handlers
async function handleAdminAddStudent(e) {
    e.preventDefault();
    const name = document.getElementById("newStudentName").value.trim();
    const roll_no = document.getElementById("newStudentRoll").value.trim();
    const branch = document.getElementById("newStudentBranch").value.trim();
    const semester = document.getElementById("newStudentSem").value.trim();

    try {
        const res = await fetch("/api/admin/student/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, roll_no, branch, semester })
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

async function handleDeleteCurrentStudent() {
    if (!currentData || !currentData.student) return;
    const stu = currentData.student;
    if (!confirm(`Are you sure you want to delete student "${stu.name}" (${stu.roll_no})?`)) return;

    try {
        const res = await fetch("/api/admin/student/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_id: stu.id })
        });
        const data = await res.json();
        if (data.success) {
            alert("🗑️ Student removed.");
            fetchStudentData();
        } else {
            alert("⚠️ " + data.message);
        }
    } catch (err) {
        alert("Failed to delete student");
    }
}

async function handleAdminAddSubject(e) {
    e.preventDefault();
    const name = document.getElementById("adminSubName").value.trim();
    const code = document.getElementById("adminSubCode").value.trim();
    const faculty = document.getElementById("adminSubFaculty").value.trim();
    const attended = document.getElementById("adminSubAttended").value || 0;
    const total = document.getElementById("adminSubTotal").value || 0;

    try {
        const res = await fetch("/api/admin/subject/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, code, faculty, attended, total })
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

async function deleteSubject(subId) {
    if (!confirm("Are you sure you want to delete this subject?")) return;
    try {
        const res = await fetch("/api/admin/subject/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subject_id: subId })
        });
        const data = await res.json();
        if (data.success) fetchStudentData();
    } catch (err) {
        alert("Failed to delete");
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

async function deleteTimetable(idx) {
    try {
        const res = await fetch("/api/admin/timetable/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ index: idx })
        });
        const data = await res.json();
        if (data.success) fetchStudentData();
    } catch (err) {
        console.error("Failed to delete timetable item", err);
    }
}

async function handleAdminAddNotice(e) {
    e.preventDefault();
    const title = document.getElementById("adminNoticeTitle").value.trim();
    const content = document.getElementById("adminNoticeContent").value.trim();

    try {
        const res = await fetch("/api/admin/notice/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title, content, badge: "Notice" })
        });
        const data = await res.json();
        if (data.success) {
            alert("📢 " + data.message);
            e.target.reset();
            fetchStudentData();
        }
    } catch (err) {
        alert("Failed to post notice");
    }
}

async function handleResetAllData() {
    if (!confirm("Are you sure you want to reset all data back to clean template?")) return;
    try {
        const res = await fetch("/api/admin/reset", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            alert("🧹 All data cleared!");
            fetchStudentData();
        }
    } catch (err) {
        alert("Failed to reset");
    }
}

// Chatbot Functions
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

        if (data.action === "refresh_data") {
            fetchStudentData();
        } else if (data.action === "open_breathing") {
            setTimeout(openBreathingModal, 1200);
        }
    } catch (err) {
        removeTypingIndicator(typingId);
        appendBotMessage("⚠️ Unable to connect to CampusGenie server. Make sure `python app.py` is running.");
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
            <div class="chat-bot-bubble">Chat cleared! Ask me anything about helpdesk, attendance, timetable, or doubts.</div>
        </div>
    `;
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return (text || '').replace(/[&<>"']/g, m => map[m]);
}

// 4-7-8 Breathing Modal Logic
function openBreathingModal() {
    const modal = document.getElementById("breathingModal");
    modal.classList.remove("hidden");
    runBreathingCycle();
}

function closeBreathingModal() {
    const modal = document.getElementById("breathingModal");
    modal.classList.add("hidden");
    if (breathingInterval) clearTimeout(breathingInterval);
}

function runBreathingCycle() {
    const circle = document.getElementById("breathingCircle");
    const text = document.getElementById("breathingActionText");

    circle.className = "w-28 h-28 rounded-full border-2 border-teal-400 flex items-center justify-center shadow-xl breathe-inhale";
    text.innerText = "Inhale (4s)";

    breathingInterval = setTimeout(() => {
        circle.className = "w-28 h-28 rounded-full border-2 border-amber-400 flex items-center justify-center shadow-xl breathe-hold";
        text.innerText = "Hold (7s)";

        breathingInterval = setTimeout(() => {
            circle.className = "w-28 h-28 rounded-full border-2 border-indigo-400 flex items-center justify-center shadow-xl breathe-exhale";
            text.innerText = "Exhale (8s)";

            breathingInterval = setTimeout(runBreathingCycle, 8000);
        }, 7000);
    }, 4000);
}
