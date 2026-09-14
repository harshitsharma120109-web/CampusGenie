let currentStudentData = null;
let breathingInterval = null;

// Initial Load
document.addEventListener("DOMContentLoaded", () => {
    fetchStudentData();
});

// Fetch Student Data & Render
async function fetchStudentData() {
    try {
        const res = await fetch("/api/student");
        const data = await res.json();
        currentStudentData = data;
        renderDashboard(data);
    } catch (err) {
        console.error("Failed to load student data", err);
    }
}

// Render Dashboard (Overall, Subjects, Timetable)
function renderDashboard(data) {
    if (!data || !data.student) return;

    // Student profile
    const student = data.student;
    const nameElem = document.getElementById("headerStudentName");
    if (nameElem) nameElem.innerText = student.name;

    // Overall Attendance
    const subjects = data.subjects || [];
    const totAttended = subjects.reduce((sum, s) => sum + s.attended, 0);
    const totClasses = subjects.reduce((sum, s) => sum + s.total, 0);
    const overallPct = totClasses > 0 ? ((totAttended / totClasses) * 100).toFixed(1) : 0;

    const overallPctElem = document.getElementById("overallPercentage");
    const overallBadge = document.getElementById("overallBadge");
    const overallSummary = document.getElementById("overallSummaryText");

    overallPctElem.innerText = `${overallPct}%`;

    if (overallPct < student.target_attendance) {
        overallBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
        overallBadge.innerText = "Shortage Alert";
        overallSummary.innerHTML = `<span class="text-amber-400 font-semibold">⚠️ Attention:</span> You are ${ (student.target_attendance - overallPct).toFixed(1) }% below the mandatory 75% rule.`;
    } else {
        overallBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        overallBadge.innerText = "Safe & Eligible";
        overallSummary.innerHTML = `<span class="text-emerald-400 font-semibold">✅ Eligible:</span> You meet university exam attendance norms!`;
    }

    // Render Subjects
    const subContainer = document.getElementById("subjectsContainer");
    subContainer.innerHTML = "";

    subjects.forEach(sub => {
        const isSafe = sub.percentage >= student.target_attendance;
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
                <!-- Progress Bar -->
                <div class="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
                    <div class="bg-${statusColor}-500 h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(sub.percentage, 100)}%"></div>
                </div>
            </div>

            <!-- Quick Action Buttons -->
            <div class="flex items-center space-x-2 shrink-0">
                <button onclick="logAttendance('${sub.id}', 'present')" title="Mark Present" class="px-2.5 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-semibold flex items-center space-x-1 transition-all">
                    <i class="fa-solid fa-plus text-[10px]"></i>
                    <span>Present</span>
                </button>
                <button onclick="logAttendance('${sub.id}', 'absent')" title="Mark Absent" class="px-2.5 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold flex items-center space-x-1 transition-all">
                    <i class="fa-solid fa-minus text-[10px]"></i>
                    <span>Absent</span>
                </button>
            </div>
        `;
        subContainer.appendChild(card);
    });

    // Render Timetable
    const ttContainer = document.getElementById("timetableContainer");
    ttContainer.innerHTML = "";
    (data.timetable || []).forEach(item => {
        let badgeHtml = `<span class="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">Upcoming</span>`;
        let borderClass = "border-slate-800/80";

        if (item.status === "ongoing") {
            badgeHtml = `<span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 animate-pulse font-semibold">Ongoing Now</span>`;
            borderClass = "border-blue-500/40 bg-blue-950/20";
        } else if (item.status === "completed") {
            badgeHtml = `<span class="text-[10px] px-2 py-0.5 rounded-full bg-slate-800/80 text-slate-500">Completed</span>`;
        }

        const row = document.createElement("div");
        row.className = `p-3 rounded-xl bg-slate-950/50 border ${borderClass} flex items-center justify-between text-xs transition-all`;
        row.innerHTML = `
            <div class="flex items-center space-x-3">
                <span class="font-mono text-indigo-400 font-semibold text-[11px] w-36">${item.time}</span>
                <div>
                    <p class="font-bold text-slate-200">${item.subject}</p>
                    <p class="text-[10px] text-slate-400">📍 ${item.room} • ${item.faculty}</p>
                </div>
            </div>
            <div>${badgeHtml}</div>
        `;
        ttContainer.appendChild(row);
    });
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
            // Append note in chat
            appendBotMessage(`📝 **Quick Attendance Update:**\nMarked **${status.toUpperCase()}** for **${result.subject.name}**.\n• Current: ${result.subject.attended}/${result.subject.total} (${result.subject.percentage}%)\n• Overall: ${result.overall_percentage}%`);
            fetchStudentData();
        }
    } catch (err) {
        console.error("Error updating attendance:", err);
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

    // Show typing indicator
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
        appendBotMessage("⚠️ Sorry, unable to connect to CampusGenie server. Please ensure `app.py` is running.");
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
    
    // Parse basic markdown: bold **text**, bullet •, newlines
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
            <div class="chat-bot-bubble">Chat cleared! Ask me anything about attendance, timetable, or study topics.</div>
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

    // Phase 1: Inhale 4s
    circle.className = "w-28 h-28 rounded-full border-2 border-teal-400 flex items-center justify-center shadow-xl breathe-inhale";
    text.innerText = "Inhale (4s)";

    breathingInterval = setTimeout(() => {
        // Phase 2: Hold 7s
        circle.className = "w-28 h-28 rounded-full border-2 border-amber-400 flex items-center justify-center shadow-xl breathe-hold";
        text.innerText = "Hold (7s)";

        breathingInterval = setTimeout(() => {
            // Phase 3: Exhale 8s
            circle.className = "w-28 h-28 rounded-full border-2 border-indigo-400 flex items-center justify-center shadow-xl breathe-exhale";
            text.innerText = "Exhale (8s)";

            breathingInterval = setTimeout(runBreathingCycle, 8000);
        }, 7000);
    }, 4000);
}
