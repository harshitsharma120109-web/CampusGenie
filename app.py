import sys
import os
import json
import re
from flask import Flask, render_template, request, jsonify

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'student_data.json')

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_active_student(data):
    students = data.get('students', [])
    active_id = data.get('active_student_id')
    for s in students:
        if s['id'] == active_id:
            return s
    if students:
        data['active_student_id'] = students[0]['id']
        return students[0]
    return None

def calculate_classes_needed(attended, total, target=75):
    req = target * total - 100 * attended
    if req <= 0:
        return 0
    import math
    return math.ceil(req / (100 - target))

STUDY_KNOWLEDGE = {
    "binary search": {
        "title": "Binary Search (Divide & Conquer)",
        "explanation": "Works on a sorted array by repeatedly dividing the search interval in half. Compares target value to the middle element; if unequal, eliminates the half in which the target cannot lie.",
        "complexity": "Time: O(log N) | Space: O(1) iterative",
        "exam_tip": "Viva Question: Why is it faster than Linear Search? Because every step halves the search space from N to N/2 to N/4!"
    },
    "deadlock": {
        "title": "Deadlock in Operating Systems",
        "explanation": "A state where a set of processes are blocked because each process is holding a resource and waiting for another resource acquired by some other process.",
        "complexity": "4 Conditions: Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait",
        "exam_tip": "Important 10-marker: Banker's Algorithm is used for Deadlock Avoidance by maintaining a safe state."
    },
    "polymorphism": {
        "title": "Polymorphism in OOP",
        "explanation": "Ability of a message/method to be displayed in more than one form. Achieved via Compile-time (Method Overloading) and Runtime (Method Overriding via Virtual Functions).",
        "complexity": "Types: Static vs Dynamic Binding",
        "exam_tip": "In Java/C++, method overriding is runtime polymorphism achieved through dynamic method dispatch."
    },
    "normalization": {
        "title": "Database Normalization (1NF, 2NF, 3NF, BCNF)",
        "explanation": "Technique to organize database tables to reduce data redundancy and eliminate insert, update, and delete anomalies.",
        "complexity": "1NF: Atomic values | 2NF: No partial dependency | 3NF: No transitive dependency",
        "exam_tip": "2NF removes partial dependency on candidate keys; 3NF removes transitive dependencies."
    },
    "tcp vs udp": {
        "title": "TCP vs UDP (Networking)",
        "explanation": "TCP is connection-oriented, reliable with 3-way handshake and packet acknowledgments. UDP is connectionless, faster, with no acknowledgment (best for live gaming & streaming).",
        "complexity": "TCP: Heavyweight/Reliable | UDP: Lightweight/Fast",
        "exam_tip": "Remember: TCP uses SYN -> SYN-ACK -> ACK handshake before data transmission."
    }
}

HEALTH_SYMPTOMS = {
    "fever": {
        "condition": "Mild Viral Fever / Temperature",
        "first_aid": "Paracetamol (PCM 500mg/650mg) after food if temperature > 99.5°F. Keep a wet cloth sponge on the forehead.",
        "home_remedy": "Drink warm water, electrobion/electral ORS, and take full bed rest. Avoid cold/chilled beverages.",
        "doctor_alert": "If fever persists beyond 48 hours or crosses 102°F with severe shivering, visit the College Medical Room immediately."
    },
    "headache": {
        "condition": "Tension Headache / Screen Eye Strain",
        "first_aid": "Take a 20-minute screen break in a dark room. Mild balm (Amrutanjan/Vicks) on temples. If severe, Paracetamol 500mg.",
        "home_remedy": "Drink 2 large glasses of water immediately (dehydration is the #1 student cause). Do gentle neck stretching.",
        "doctor_alert": "If accompanied by vomiting or vision blurriness, visit a doctor right away."
    },
    "cold": {
        "condition": "Common Cold & Sore Throat",
        "first_aid": "Steam inhalation with water 2 times a day. Antihistamine like Cetirizine 10mg at bedtime if sneezing heavily.",
        "home_remedy": "Warm salt water gargle 3 times a day for sore throat. Drink hot ginger-tulsi tea or warm honey water.",
        "doctor_alert": "If chest congestion or breathing difficulty occurs, consult campus physician."
    },
    "cough": {
        "condition": "Dry / Wet Cough & Throat Irritation",
        "first_aid": "Strepsils/Koflet lozenge for throat irritation. Steam inhalation.",
        "home_remedy": "Warm turmeric milk (Haldi doodh) before sleeping. 1 spoon honey with black pepper.",
        "doctor_alert": "If cough lasts more than 1 week with blood in sputum, visit a doctor."
    },
    "stomach": {
        "condition": "Stomach Ache / Acidity / Food Discomfort",
        "first_aid": "Antacid gel (Digene / Gelusil 2 teaspoons) or Pantoprazole 40mg before breakfast if hyperacidity.",
        "home_remedy": "Drink buttermilk (Chhachh) or coconut water. Eat simple plain Khichdi. Avoid spicy mess food.",
        "doctor_alert": "If severe sharp pain in the lower right abdomen (appendix risk), rush to hospital immediately."
    },
    "acidity": {
        "condition": "Acid Reflux / Heartburn",
        "first_aid": "Eno or Digene / Gelusil syrup 10ml. Avoid lying down flat immediately after eating.",
        "home_remedy": "Cold milk (without sugar) provides instant relief. Sip fennel seed (Saunf) water.",
        "doctor_alert": "If persistent burning pain radiates to jaw or left arm, seek emergency medical care."
    },
    "stress": {
        "condition": "Exam Anxiety & Mental Fatigue",
        "first_aid": "Guided 4-7-8 Breathing: Inhale 4s, Hold 7s, Exhale 8s. Take a 15-minute walk outside in fresh air.",
        "home_remedy": "Listen to calming music, hydrate well, and remind yourself that exams don't define your destiny.",
        "doctor_alert": "Reach out to College Student Counselor or helpline if feeling completely overwhelmed."
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/student', methods=['GET'])
def get_student():
    data = load_data()
    active_stu = get_active_student(data)
    
    all_students = [
        {"id": s["id"], "name": s["name"], "roll_no": s["roll_no"], "branch": s.get("branch", ""), "semester": s.get("semester", "")}
        for s in data.get('students', [])
    ]
    
    subjects_list = data.get('subjects', [])
    
    # Format active student attendance and marks
    att_map = active_stu.get('attendance', {}) if active_stu else {}
    marks_map = active_stu.get('marks', {}) if active_stu else {}
    
    formatted_subjects = []
    for sub in subjects_list:
        sub_id = sub['id']
        sub_att = att_map.get(sub_id, {"attended": 0, "total": 0, "percentage": 100.0, "status": "safe"})
        sub_marks = marks_map.get(sub_id, {"score": "-", "total": 100, "status": "Pending"})
        
        formatted_subjects.append({
            "id": sub_id,
            "code": sub.get('code', ''),
            "name": sub.get('name', ''),
            "faculty": sub.get('faculty', ''),
            "attended": sub_att.get('attended', 0),
            "total": sub_att.get('total', 0),
            "percentage": sub_att.get('percentage', 100.0),
            "status": sub_att.get('status', 'safe'),
            "score": sub_marks.get('score', '-'),
            "total_marks": sub_marks.get('total', 100),
            "result": sub_marks.get('status', 'Pending')
        })
    
    return jsonify({
        "student": active_stu,
        "all_students": all_students,
        "subjects": formatted_subjects,
        "raw_subjects": subjects_list,
        "timetable": data.get('timetable', []),
        "opportunities": data.get('opportunities', []),
        "notices": data.get('notices', [])
    })

@app.route('/api/student/switch', methods=['POST'])
def switch_student():
    payload = request.json or {}
    target_id = payload.get('student_id')
    data = load_data()
    
    for s in data.get('students', []):
        if s['id'] == target_id:
            data['active_student_id'] = target_id
            save_data(data)
            return jsonify({"success": True, "message": f"Switched to {s['name']}."})
    return jsonify({"success": False, "message": "Student not found."}), 404

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    payload = request.json or {}
    student_id = payload.get('student_id')
    sub_id = payload.get('subject_id')
    status = payload.get('status', 'present').lower()
    
    data = load_data()
    students = data.get('students', [])
    
    target_stu = None
    if student_id:
        target_stu = next((s for s in students if s['id'] == student_id), None)
    if not target_stu:
        target_stu = get_active_student(data)
        
    if not target_stu:
        return jsonify({"success": False, "message": "No student found."}), 404
        
    att_dict = target_stu.setdefault('attendance', {})
    sub_att = att_dict.setdefault(sub_id, {"attended": 0, "total": 0, "percentage": 100.0, "status": "safe"})
    
    sub_att['total'] += 1
    if status == 'present':
        sub_att['attended'] += 1
    sub_att['percentage'] = round((sub_att['attended'] / sub_att['total']) * 100, 2)
    sub_att['status'] = 'safe' if sub_att['percentage'] >= target_stu.get('target_attendance', 75) else 'warning'
    
    save_data(data)
    
    needed = calculate_classes_needed(sub_att['attended'], sub_att['total'], target_stu.get('target_attendance', 75))
    return jsonify({
        "success": True,
        "student_name": target_stu['name'],
        "subject_id": sub_id,
        "attended": sub_att['attended'],
        "total": sub_att['total'],
        "percentage": sub_att['percentage'],
        "status": sub_att['status'],
        "classes_needed": needed,
        "message": f"Marked {status.upper()} for {target_stu['name']}!"
    })

# --- FACULTY ADMIN ACTIONS ---

@app.route('/api/admin/student/add', methods=['POST'])
def add_student():
    payload = request.json or {}
    name = payload.get('name', '').strip()
    roll_no = payload.get('roll_no', '').strip()
    branch = payload.get('branch', 'CSE').strip()
    semester = payload.get('semester', '5th Sem').strip()
    
    if not name or not roll_no:
        return jsonify({"success": False, "message": "Name and Roll No are required."}), 400
        
    data = load_data()
    stu_id = roll_no.replace(' ', '').upper()
    
    for s in data.get('students', []):
        if s['id'] == stu_id:
            return jsonify({"success": False, "message": f"Roll No {roll_no} already exists."}), 400
            
    new_stu = {
        "id": stu_id,
        "name": name,
        "roll_no": roll_no,
        "branch": branch,
        "semester": semester,
        "target_attendance": 75,
        "attendance": {},
        "marks": {}
    }
    data.setdefault('students', []).append(new_stu)
    data['active_student_id'] = stu_id
    save_data(data)
    return jsonify({"success": True, "message": f"Student '{name}' registered!", "student": new_stu})

@app.route('/api/admin/marks/update', methods=['POST'])
def update_marks():
    payload = request.json or {}
    student_id = payload.get('student_id')
    sub_id = payload.get('subject_id')
    score = payload.get('score')
    total = payload.get('total', 100)
    
    try:
        score_val = float(score)
        total_val = float(total)
    except Exception:
        return jsonify({"success": False, "message": "Invalid numeric score."}), 400
        
    pass_status = "Pass" if (score_val / total_val * 100) >= 40 else "Fail"
    
    data = load_data()
    target_stu = next((s for s in data.get('students', []) if s['id'] == student_id), None)
    if not target_stu:
        return jsonify({"success": False, "message": "Student not found."}), 404
        
    marks_dict = target_stu.setdefault('marks', {})
    marks_dict[sub_id] = {
        "score": int(score_val) if score_val.is_integer() else score_val,
        "total": int(total_val) if total_val.is_integer() else total_val,
        "status": pass_status
    }
    save_data(data)
    return jsonify({
        "success": True,
        "message": f"Updated marks for {target_stu['name']}: {score}/{total} ({pass_status})",
        "status": pass_status
    })

@app.route('/api/admin/subject/add', methods=['POST'])
def add_subject():
    payload = request.json or {}
    name = payload.get('name', '').strip()
    code = payload.get('code', '').strip()
    faculty = payload.get('faculty', '').strip()
    
    if not name or not code:
        return jsonify({"success": False, "message": "Subject Name and Code required."}), 400
        
    data = load_data()
    sub_id = code.lower().replace('-', '').replace(' ', '')
    new_sub = {
        "id": sub_id,
        "code": code,
        "name": name,
        "faculty": faculty or "Faculty Assigned"
    }
    data.setdefault('subjects', []).append(new_sub)
    save_data(data)
    return jsonify({"success": True, "message": f"Subject '{name}' added to college curriculum!", "subject": new_sub})

@app.route('/api/admin/timetable/add', methods=['POST'])
def add_timetable():
    payload = request.json or {}
    time = payload.get('time', '').strip()
    subject = payload.get('subject', '').strip()
    room = payload.get('room', '').strip()
    faculty = payload.get('faculty', '').strip()
    cls_type = payload.get('type', 'Theory').strip()
    
    if not time or not subject:
        return jsonify({"success": False, "message": "Time and Subject required."}), 400
        
    data = load_data()
    new_lecture = {
        "time": time,
        "subject": subject,
        "code": payload.get('code', 'CS-50X'),
        "room": room or "Lecture Hall",
        "faculty": faculty or "Faculty Assigned",
        "type": cls_type,
        "status": "upcoming"
    }
    data.setdefault('timetable', []).append(new_lecture)
    save_data(data)
    return jsonify({"success": True, "message": f"Lecture scheduled at {time} in {room}!", "lecture": new_lecture})

@app.route('/api/admin/opportunity/add', methods=['POST'])
def add_opportunity():
    payload = request.json or {}
    title = payload.get('title', '').strip()
    category = payload.get('category', 'Hackathon').strip()
    deadline = payload.get('deadline', 'Soon').strip()
    link = payload.get('link', '#').strip()
    desc = payload.get('desc', '').strip()
    
    if not title:
        return jsonify({"success": False, "message": "Title is required."}), 400
        
    data = load_data()
    new_opp = {
        "id": len(data.get('opportunities', [])) + 1,
        "title": title,
        "category": category,
        "badge": "Faculty Verified",
        "deadline": deadline,
        "link": link,
        "desc": desc
    }
    data.setdefault('opportunities', []).insert(0, new_opp)
    save_data(data)
    return jsonify({"success": True, "message": f"Opportunity '{title}' posted for students!", "opportunity": new_opp})

# --- AI COPILOT CHATBOT ---

@app.route('/api/chat', methods=['POST'])
def chat():
    payload = request.json or {}
    user_msg = payload.get('message', '').strip()
    msg_lower = user_msg.lower()
    
    data = load_data()
    active_stu = get_active_student(data)
    student_name = active_stu.get('name', 'Student') if active_stu else 'Student'
    
    # 1. HEALTH & SYMPTOMS CHECKER (First Aid & Medicine)
    for symptom_key, info in HEALTH_SYMPTOMS.items():
        if symptom_key in msg_lower:
            return jsonify({
                "reply": f"🩺 **Campus Health AI — Symptom Triage**\n\n• **Identified Concern:** {info['condition']}\n\n💊 **First-Aid & Safe Medicine Guidance:**\n{info['first_aid']}\n\n🍵 **Home Remedies & Comfort:**\n{info['home_remedy']}\n\n🚨 **When to See a Doctor:**\n{info['doctor_alert']}\n\n*(Note: This is AI first-aid support. Please visit the Campus Clinic in Health Block Room 04 for prescription care.)*",
                "action": None
            })

    # 2. ACADEMIC DOUBT SOLVER
    for study_key, s_info in STUDY_KNOWLEDGE.items():
        if study_key in msg_lower:
            return jsonify({
                "reply": f"📚 **AI Academic Tutor: {s_info['title']}**\n\n💡 **Core Concept:**\n{s_info['explanation']}\n\n⚡ **Complexity / Properties:**\n{s_info['complexity']}\n\n🎯 **Exam & Viva Pro-Tip:**\n{s_info['exam_tip']}",
                "action": None
            })

    # 3. MARKS & RESULT QUERIES
    if any(k in msg_lower for k in ['mark', 'score', 'pass', 'fail', 'result', 'grade']):
        marks_map = active_stu.get('marks', {}) if active_stu else {}
        sub_list = data.get('subjects', [])
        
        reply_lines = [f"📋 **Academic Performance & Results for {student_name}:**\n"]
        for s in sub_list:
            m = marks_map.get(s['id'], {"score": "Not Declared", "total": 100, "status": "Pending"})
            badge = "🟢 Pass" if m['status'] == 'Pass' else ("🔴 Fail" if m['status'] == 'Fail' else "⚪ Pending")
            reply_lines.append(f"• **{s['name']}** ({s['code']}): {m['score']}/{m['total']} [{badge}]")
            
        return jsonify({"reply": "\n".join(reply_lines), "action": None})

    # 4. HACKATHONS & JOBS
    if any(k in msg_lower for k in ['hackathon', 'job', 'internship', 'placement', 'contest', 'opportunity']):
        opps = data.get('opportunities', [])
        if opps:
            opp_text = "🚀 **Active Hackathons & Job Opportunities:**\n\n"
            for o in opps[:3]:
                opp_text += f"• **[{o['category']}] {o['title']}**\n  ⏰ Deadline: {o['deadline']}\n  🔗 Link: {o['link']}\n\n"
            return jsonify({"reply": opp_text, "action": None})

    # 5. ATTENDANCE QUERIES
    if any(k in msg_lower for k in ['attendance', 'bunk', 'shortage', 'present', 'absent']):
        att_map = active_stu.get('attendance', {}) if active_stu else {}
        sub_list = data.get('subjects', [])
        target = active_stu.get('target_attendance', 75)
        
        reply_lines = [f"📊 **Attendance Status for {student_name}:**\n"]
        for s in sub_list:
            a = att_map.get(s['id'], {"attended": 0, "total": 0, "percentage": 100.0, "status": "safe"})
            status_icon = "⚠️ Shortage" if a['percentage'] < target else "✅ Safe"
            reply_lines.append(f"• **{s['name']}**: {a['attended']}/{a['total']} ({a['percentage']}%) — {status_icon}")
            
        return jsonify({"reply": "\n".join(reply_lines), "action": None})

    # 6. TIMETABLE & CLASS LOCATION QUERIES
    if any(k in msg_lower for k in ['timetable', 'schedule', 'class', 'lecture', 'where', 'kahan', 'room', 'teacher']):
        tt = data.get('timetable', [])
        if tt:
            tt_lines = ["📅 **Class & Lecture Locations for Today:**\n"]
            for idx, c in enumerate(tt, 1):
                tt_lines.append(f"**{idx}. {c['time']}** — {c['subject']} ({c.get('type', 'Theory')})\n   📍 **Venue:** {c['room']}\n   👨‍🏫 **Faculty:** {c['faculty']}\n")
            return jsonify({"reply": "\n".join(tt_lines), "action": None})

    # 7. DEFAULT GREETING
    return jsonify({
        "reply": f"👋 **Hello {student_name}! I'm CampusGenie AI**, your 360° College Copilot.\n\nAsk me anything:\n• 📚 **Academic Doubts:** *'Explain binary search'* or *'What is deadlock in OS?'*\n• 🩺 **Health & Medicine:** *'Fever remedies'*, *'Headache relief'*, *'Stomach ache advice'*\n• 📋 **Results & Marks:** *'Show my marks'*, *'Am I pass in OS?'*\n• 🚀 **Opportunities:** *'Show latest hackathons and internships'*\n• 📅 **Class Venue:** *'Where is my next lecture?'*",
        "action": None
    })

if __name__ == '__main__':
    print("[+] CampusGenie Ultimate Server starting on http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000)
