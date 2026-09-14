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

STUDY_KNOWLEDGE_BASE = {
    "binary search": {
        "title": "Binary Search (Divide & Conquer)",
        "eli10": "Imagine searching for a word in a dictionary. You open it right in the middle! If your word comes earlier, you ignore the right half. You repeat this until you find it.",
        "points": [
            "Prerequisite: Array must be sorted.",
            "Time Complexity: Best O(1), Average/Worst O(log N).",
            "Space Complexity: O(1) iterative, O(log N) recursive."
        ],
        "exam_tip": "Frequently asked viva question: Why is binary search faster than linear search? Ans: It cuts the search space in half with every single comparison!"
    },
    "deadlock": {
        "title": "Deadlock in Operating Systems",
        "eli10": "Imagine two cars facing each other on a single-lane bridge. Neither can move forward until the other backs up, but neither wants to back up. Both are stuck forever!",
        "points": [
            "4 Coffman Conditions: Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait.",
            "Handling: Prevention, Avoidance (Banker's Algorithm), Detection & Recovery.",
            "Deadlock vs Starvation: In deadlock no process makes progress; in starvation low-priority process waits indefinitely."
        ],
        "exam_tip": "Always write down all 4 Coffman conditions in exam questions—professors look for these 4 exact terms!"
    },
    "polymorphism": {
        "title": "Polymorphism in OOP",
        "eli10": "Poly = Many, Morph = Forms. Like a person: they can be a student at college, a customer in a shop, and a driver in a car. One entity, different behaviors!",
        "points": [
            "Compile-time (Static): Method Overloading and Operator Overloading.",
            "Run-time (Dynamic): Method Overriding using virtual functions/interfaces.",
            "Benefit: Code reusability and flexibility."
        ],
        "exam_tip": "In Java/C++, runtime polymorphism is achieved through method overriding and dynamic method dispatch."
    },
    "normalization": {
        "title": "Database Normalization (1NF, 2NF, 3NF, BCNF)",
        "eli10": "Organizing your messy study desk into neat labeled drawers so you don't keep duplicate copies of the same notes everywhere.",
        "points": [
            "Goal: Eliminate redundant data and prevent Insertion, Update, and Deletion anomalies.",
            "1NF: Atomic values (no repeating groups).",
            "2NF: In 1NF + No partial dependency (non-prime attributes fully dependent on candidate key).",
            "3NF: In 2NF + No transitive dependency (non-prime dependent on non-prime)."
        ],
        "exam_tip": "Remember: 2NF removes partial dependency, 3NF removes transitive dependency."
    },
    "tcp vs udp": {
        "title": "TCP vs UDP (Computer Networks)",
        "eli10": "TCP is like a registered post letter with acknowledgment receipt. UDP is like shouting across a crowded room—fast, but no guarantee they heard you!",
        "points": [
            "TCP: Connection-oriented, reliable, 3-way handshake, flow/congestion control. Used in HTTP, FTP, Email.",
            "UDP: Connectionless, unreliable, lightweight, faster. Used in Live Video streaming, Gaming, DNS, VoIP."
        ],
        "exam_tip": "Remember 3-way handshake: SYN -> SYN-ACK -> ACK."
    }
}

HELPDESK_KNOWLEDGE = {
    "bonafide": "📄 **Bonafide Certificate Procedure:**\n1. Go to College Admin Block (Room 102) or submit online at ERP portal under 'Student Requests'.\n2. Processing time: 2 working days.\n3. Fee: ₹50 at accounts section.",
    "exam form": "📝 **Exam Form & Fee Information:**\n• Regular Exam Fee: ₹1,800 per semester.\n• Submission Portal: ERP -> Examination Tab -> 'Register Subjects'.\n• Deadline: Sept 25th (Zero Late Fee) | Sept 30th (₹500 Late Fee).",
    "fee": "💳 **College Fee Payment:**\n• Fees can be paid via NetBanking, UPI, or Challan through the official ERP portal.\n• For installments or scholarship adjustments, visit Academic Block Account Section (Counter 3).",
    "hostel": "🏠 **Hostel & Mess Schedule:**\n• Breakfast: 07:30 AM - 09:00 AM\n• Lunch: 12:30 PM - 02:00 PM\n• Dinner: 07:30 PM - 09:30 PM\n• Night In-Time: 09:30 PM (Biometric entry required).",
    "library": "📖 **Central Library Rules:**\n• Timings: 08:30 AM - 09:00 PM (Monday to Saturday).\n• Book borrowing limit: 4 books for 14 days.\n• Late return fine: ₹2 per day per book.",
    "scholarship": "🎓 **Scholarship Desk:**\n• National Scholarship Portal (NSP) & State Post-Matric schemes open till Oct 15th.\n• Verification desk: Scholarship Cell (Admin Block, 2nd Floor)."
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/student', methods=['GET'])
def get_student():
    data = load_data()
    active_stu = get_active_student(data)
    
    all_students = [
        {"id": s["id"], "name": s["name"], "roll_no": s["roll_no"], "branch": s.get("branch", "")}
        for s in data.get('students', [])
    ]
    
    return jsonify({
        "student": active_stu,
        "all_students": all_students,
        "subjects": active_stu.get('subjects', []) if active_stu else [],
        "timetable": data.get('timetable', []),
        "notices": data.get('notices', []),
        "health_tips": data.get('health_tips', [])
    })

@app.route('/api/student/switch', methods=['POST'])
def switch_student():
    payload = request.json or {}
    target_id = payload.get('student_id')
    data = load_data()
    
    found = any(s['id'] == target_id for s in data.get('students', []))
    if found:
        data['active_student_id'] = target_id
        save_data(data)
        return jsonify({"success": True, "message": "Switched active student."})
    return jsonify({"success": False, "message": "Student not found."}), 404

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    payload = request.json or {}
    sub_id = payload.get('subject_id')
    status = payload.get('status', 'present').lower()
    
    data = load_data()
    active_stu = get_active_student(data)
    if not active_stu:
        return jsonify({"success": False, "message": "No active student."}), 404
        
    updated_sub = None
    target_att = active_stu.get('target_attendance', 75)
    
    for sub in active_stu.get('subjects', []):
        if sub['id'] == sub_id:
            sub['total'] += 1
            if status == 'present':
                sub['attended'] += 1
            sub['percentage'] = round((sub['attended'] / sub['total']) * 100, 2)
            sub['status'] = 'safe' if sub['percentage'] >= target_att else 'warning'
            updated_sub = sub
            break
            
    if updated_sub:
        tot_att = sum(s['attended'] for s in active_stu.get('subjects', []))
        tot_all = sum(s['total'] for s in active_stu.get('subjects', []))
        overall_pct = round((tot_att / tot_all) * 100, 2) if tot_all else 0
        save_data(data)
        
        needed = calculate_classes_needed(updated_sub['attended'], updated_sub['total'], target_att)
        return jsonify({
            "success": True,
            "subject": updated_sub,
            "overall_percentage": overall_pct,
            "classes_needed": needed,
            "message": f"Attendance marked for {updated_sub['name']} as {status.upper()}."
        })
    return jsonify({"success": False, "message": "Subject not found."}), 404

# --- FACULTY / ADMIN PORTAL ENDPOINTS ---

@app.route('/api/admin/student/add', methods=['POST'])
def add_new_student():
    payload = request.json or {}
    name = payload.get('name', '').strip()
    roll_no = payload.get('roll_no', '').strip()
    branch = payload.get('branch', '').strip()
    semester = payload.get('semester', '').strip()
    
    if not name or not roll_no:
        return jsonify({"success": False, "message": "Student Name and Roll Number are required."}), 400
        
    data = load_data()
    new_id = roll_no.replace(' ', '').upper()
    
    # Check if student with same roll number exists
    for s in data.get('students', []):
        if s['id'] == new_id:
            return jsonify({"success": False, "message": f"Student with Roll No '{roll_no}' already exists."}), 400
            
    new_student = {
        "id": new_id,
        "name": name,
        "roll_no": roll_no,
        "branch": branch or "Computer Science",
        "semester": semester or "1st Semester",
        "target_attendance": 75,
        "subjects": []
    }
    
    data.setdefault('students', []).append(new_student)
    data['active_student_id'] = new_id
    save_data(data)
    
    return jsonify({"success": True, "message": f"Student '{name}' added successfully!", "student": new_student})

@app.route('/api/admin/student/delete', methods=['POST'])
def delete_student():
    payload = request.json or {}
    stu_id = payload.get('student_id')
    data = load_data()
    students = data.get('students', [])
    
    if len(students) <= 1:
        return jsonify({"success": False, "message": "Cannot delete the only student in the system."}), 400
        
    data['students'] = [s for s in students if s['id'] != stu_id]
    if data.get('active_student_id') == stu_id:
        data['active_student_id'] = data['students'][0]['id']
        
    save_data(data)
    return jsonify({"success": True, "message": "Student removed successfully."})

@app.route('/api/admin/student/update', methods=['POST'])
def update_student():
    payload = request.json or {}
    data = load_data()
    active_stu = get_active_student(data)
    if not active_stu:
        return jsonify({"success": False, "message": "No active student."}), 404
        
    if 'name' in payload and payload['name'].strip():
        active_stu['name'] = payload['name'].strip()
    if 'roll_no' in payload and payload['roll_no'].strip():
        active_stu['roll_no'] = payload['roll_no'].strip()
    if 'branch' in payload and payload['branch'].strip():
        active_stu['branch'] = payload['branch'].strip()
    if 'semester' in payload and payload['semester'].strip():
        active_stu['semester'] = payload['semester'].strip()
            
    save_data(data)
    return jsonify({"success": True, "message": "Student profile updated!", "student": active_stu})

@app.route('/api/admin/subject/add', methods=['POST'])
def add_subject():
    payload = request.json or {}
    name = payload.get('name', '').strip()
    code = payload.get('code', '').strip()
    faculty = payload.get('faculty', '').strip()
    attended = int(payload.get('attended', 0) or 0)
    total = int(payload.get('total', 0) or 0)
    
    if not name or not code:
        return jsonify({"success": False, "message": "Subject Name and Code are required."}), 400
        
    data = load_data()
    active_stu = get_active_student(data)
    if not active_stu:
        return jsonify({"success": False, "message": "Please add a student first."}), 400
        
    sub_id = code.lower().replace('-', '').replace(' ', '')
    pct = round((attended / total * 100), 2) if total > 0 else 100.0
    status = 'safe' if pct >= active_stu.get('target_attendance', 75) else 'warning'
    
    new_sub = {
        "id": sub_id,
        "name": name,
        "code": code,
        "faculty": faculty or "Faculty Assigned",
        "attended": attended,
        "total": total,
        "percentage": pct,
        "status": status
    }
    
    active_stu.setdefault('subjects', []).append(new_sub)
    save_data(data)
    return jsonify({"success": True, "message": f"Subject '{name}' added for {active_stu['name']}!", "subject": new_sub})

@app.route('/api/admin/subject/delete', methods=['POST'])
def delete_subject():
    payload = request.json or {}
    sub_id = payload.get('subject_id')
    data = load_data()
    active_stu = get_active_student(data)
    if active_stu:
        active_stu['subjects'] = [s for s in active_stu.get('subjects', []) if s['id'] != sub_id]
        save_data(data)
    return jsonify({"success": True, "message": "Subject removed."})

@app.route('/api/admin/timetable/add', methods=['POST'])
def add_timetable():
    payload = request.json or {}
    time = payload.get('time', '').strip()
    subject = payload.get('subject', '').strip()
    room = payload.get('room', '').strip()
    faculty = payload.get('faculty', '').strip()
    
    if not time or not subject:
        return jsonify({"success": False, "message": "Time and Subject are required."}), 400
        
    data = load_data()
    new_lecture = {
        "time": time,
        "subject": subject,
        "code": payload.get('code', 'CS-GEN'),
        "room": room or "Lecture Hall",
        "faculty": faculty or "Faculty",
        "status": "upcoming"
    }
    
    data.setdefault('timetable', []).append(new_lecture)
    save_data(data)
    return jsonify({"success": True, "message": f"Lecture '{subject}' scheduled at {time}!", "lecture": new_lecture})

@app.route('/api/admin/timetable/delete', methods=['POST'])
def delete_timetable():
    payload = request.json or {}
    index = payload.get('index', 0)
    data = load_data()
    if 0 <= index < len(data.get('timetable', [])):
        data['timetable'].pop(index)
        save_data(data)
        return jsonify({"success": True, "message": "Lecture removed from schedule."})
    return jsonify({"success": False, "message": "Invalid index."}), 400

@app.route('/api/admin/notice/add', methods=['POST'])
def add_notice():
    payload = request.json or {}
    title = payload.get('title', '').strip()
    content = payload.get('content', '').strip()
    badge = payload.get('badge', 'Notice')
    
    if not title or not content:
        return jsonify({"success": False, "message": "Title and Content are required."}), 400
        
    data = load_data()
    new_notice = {
        "id": len(data.get('notices', [])) + 1,
        "title": title,
        "date": "Today",
        "badge": badge,
        "content": content
    }
    data.setdefault('notices', []).insert(0, new_notice)
    save_data(data)
    return jsonify({"success": True, "message": "Notice posted successfully!", "notice": new_notice})

@app.route('/api/admin/reset', methods=['POST'])
def reset_all_data():
    data = {
        "active_student_id": "DEFAULT",
        "students": [
            {
                "id": "DEFAULT",
                "name": "Harshit Sharma",
                "roll_no": "Roll Number",
                "branch": "Your Branch",
                "semester": "Semester",
                "target_attendance": 75,
                "subjects": []
            }
        ],
        "notices": [],
        "timetable": [],
        "health_tips": [
            "Drink at least 500ml water every 2 hours of study.",
            "20-20-20 Rule: Every 20 mins, look at something 20 feet away for 20 seconds.",
            "Take a 5-minute deep breathing break to reduce cortisol and reset your focus.",
            "Swap sugary energy drinks with almonds, fruits, or green tea for steady alertness."
        ]
    }
    save_data(data)
    return jsonify({"success": True, "message": "All data reset to clean slate!"})

# --- CHATBOT / AI COPILOT ENDPOINT ---

@app.route('/api/chat', methods=['POST'])
def chat():
    payload = request.json or {}
    user_msg = payload.get('message', '').strip()
    msg_lower = user_msg.lower()
    
    data = load_data()
    active_stu = get_active_student(data)
    student_name = active_stu.get('name', 'Student') if active_stu else 'Student'
    subjects = active_stu.get('subjects', []) if active_stu else []
    timetable = data.get('timetable', [])
    notices = data.get('notices', [])
    target = active_stu.get('target_attendance', 75) if active_stu else 75
    
    # 1. HELPDESK INTENTS
    for key, text in HELPDESK_KNOWLEDGE.items():
        if key in msg_lower:
            return jsonify({
                "reply": f"🏛️ **Campus Helpdesk Assistant:**\n\n{text}\n\n*Need more help? Visit Student Affairs in Admin Block Room 102.*",
                "action": None
            })

    if any(k in msg_lower for k in ['notice', 'circular', 'announcement', 'event']):
        if notices:
            notice_text = "📢 **Latest College Notices & Announcements:**\n\n"
            for n in notices[:3]:
                notice_text += f"• **[{n['badge']}] {n['title']}** ({n['date']})\n  {n['content']}\n\n"
            return jsonify({"reply": notice_text, "action": None})
        else:
            return jsonify({"reply": "📢 No official college notices currently posted. Check back later!", "action": None})

    # 2. ATTENDANCE INTENT
    if any(k in msg_lower for k in ['attendance', 'present', 'absent', 'shortage', 'percentage', 'bunk']):
        if not subjects:
            return jsonify({
                "reply": f"📊 **No subjects registered for {student_name} yet!**\n\nPlease switch to **'Faculty / Admin Mode'** above to add subjects.",
                "action": None
            })
            
        mark_present_match = re.search(r'mark\s+(.*?)\s+(present|absent)', msg_lower)
        if mark_present_match:
            sub_query = mark_present_match.group(1).strip()
            status = mark_present_match.group(2).strip()
            
            target_sub = None
            for s in subjects:
                if sub_query in s['name'].lower() or sub_query in s['id']:
                    target_sub = s
                    break
                    
            if target_sub:
                target_sub['total'] += 1
                if status == 'present':
                    target_sub['attended'] += 1
                target_sub['percentage'] = round((target_sub['attended'] / target_sub['total']) * 100, 2)
                target_sub['status'] = 'safe' if target_sub['percentage'] >= target else 'warning'
                save_data(data)
                
                needed = calculate_classes_needed(target_sub['attended'], target_sub['total'], target)
                alert_text = f"⚠️ Warning: Attendance is {target_sub['percentage']}%! You need to attend next {needed} classes consecutively to cross 75%." if target_sub['status'] == 'warning' else "✅ You are safely above the 75% threshold!"
                
                return jsonify({
                    "reply": f"✅ **Marked {status.upper()}** for **{target_sub['name']}**!\n\n• **Updated Stats:** {target_sub['attended']}/{target_sub['total']} classes ({target_sub['percentage']}%)\n• {alert_text}",
                    "action": "refresh_data"
                })
        
        for s in subjects:
            if s['id'] in msg_lower or s['name'].lower() in msg_lower:
                needed = calculate_classes_needed(s['attended'], s['total'], target)
                status_icon = "⚠️" if s['percentage'] < target else "✅"
                advice = f"You are below the 75% rule! Attend the next **{needed} classes** consecutively to clear the shortage." if s['percentage'] < target else "You are safe! You can afford to miss 1-2 classes if urgent."
                return jsonify({
                    "reply": f"{status_icon} **{s['name']} Attendance Summary**:\n\n• **Current:** {s['attended']}/{s['total']} lectures ({s['percentage']}%)\n• **Faculty:** {s['faculty']}\n• **Status:** {s['status'].upper()}\n• **Advice:** {advice}",
                    "action": None
                })
                
        tot_att = sum(s['attended'] for s in subjects)
        tot_all = sum(s['total'] for s in subjects)
        overall = round((tot_att / tot_all) * 100, 2) if tot_all else 0
        
        warning_list = [s for s in subjects if s['percentage'] < target]
        warning_msg = ""
        if warning_list:
            warning_msg = "\n\n🚨 **Subjects Requiring Immediate Attention (< 75%):**\n"
            for w in warning_list:
                req = calculate_classes_needed(w['attended'], w['total'], target)
                warning_msg += f"• **{w['name']}**: {w['percentage']}% (Need +{req} lectures)\n"
        else:
            warning_msg = "\n\n🎉 Great job! You are above 75% in all registered subjects!"
            
        return jsonify({
            "reply": f"📊 **{student_name}'s Overall Attendance Report**:\n\n• **Total Lectures:** {tot_att} / {tot_all}\n• **Overall Percentage:** **{overall}%** (Target: {target}%){warning_msg}\n\n*Tip: Say 'Mark <Subject> present' to log today's class!*",
            "action": None
        })

    # 3. TIMETABLE INTENT
    if any(k in msg_lower for k in ['timetable', 'schedule', 'class', 'lecture', 'room', 'next class']):
        if not timetable:
            return jsonify({
                "reply": "📅 **No classes scheduled in timetable yet!**\n\nSwitch to **'Faculty / Admin Mode'** to add daily lecture timings.",
                "action": None
            })
            
        if 'next' in msg_lower:
            next_class = next((item for item in timetable if item['status'] in ['upcoming', 'ongoing']), timetable[0])
            return jsonify({
                "reply": f"⏰ **Next Upcoming Class**:\n\n• **Subject:** {next_class['subject']} ({next_class['code']})\n• **Time:** {next_class['time']}\n• **Venue:** {next_class['room']}\n• **Faculty:** {next_class['faculty']}",
                "action": None
            })
            
        schedule_text = "📅 **Today's Class Schedule**:\n\n"
        for idx, item in enumerate(timetable, 1):
            badge = "🟢 Ongoing" if item['status'] == 'ongoing' else ("⚪ Done" if item['status'] == 'completed' else "🔵 Upcoming")
            schedule_text += f"**{idx}. {item['time']}** — {item['subject']}\n   📍 {item['room']} | 👨‍🏫 {item['faculty']} [{badge}]\n\n"
            
        return jsonify({
            "reply": schedule_text,
            "action": None
        })

    # 4. HEALTH & WELLNESS INTENT
    if any(k in msg_lower for k in ['stress', 'health', 'tired', 'sleep', 'anxious', 'headache', 'diet', 'water', 'breathe', 'relax']):
        return jsonify({
            "reply": "🧘 **Student Wellness & Stress Buster Check-In**:\n\n1. **4-7-8 Breathing Technique:** Inhale quietly through your nose for 4s, hold breath for 7s, exhale completely through mouth for 8s. Repeat 4 times.\n2. **Screen Eye Relief (20-20-20):** Shift your eyes to look at an object 20 feet away for 20 seconds.\n3. **Hydration:** A quick glass of water restores brain focus within 5 minutes.\n4. **Exam Stress Reality Check:** Remember that an exam tests what you know on paper today, not your true capability or self-worth. Take it one topic at a time!\n\n*Click the 'Stress Buster' button to start guided meditation!*",
            "action": "open_breathing"
        })

    # 5. STUDY BUDDY INTENT
    for key, info in STUDY_KNOWLEDGE_BASE.items():
        if key in msg_lower:
            points_text = "\n".join([f"• {p}" for p in info['points']])
            return jsonify({
                "reply": f"📚 **Study Buddy Breakdown: {info['title']}**\n\n💡 **Simplified Explanation:**\n{info['eli10']}\n\n🔑 **Key Exam Points:**\n{points_text}\n\n🎯 **Exam/Viva Pro-Tip:**\n{info['exam_tip']}",
                "action": None
            })

    # 6. DEFAULT GREETINGS / HELP
    return jsonify({
        "reply": f"👋 **Hello {student_name}! I'm CampusGenie**, your AI Student Copilot.\n\nHere is how I can assist you today:\n1. 📊 **Attendance Tracker:** Ask *'What is my attendance?'* or say *'Mark <subject> present'*.\n2. 📅 **Smart Timetable:** Ask *'What is my next class?'* or *'Show today's timetable'*.\n3. 🏛️ **Campus Helpdesk:** Ask about *'Bonafide certificate'*, *'Exam form fee'*, or *'Hostel mess'*.\n4. 📚 **Study Buddy:** Ask *'Explain binary search'* or *'Explain deadlock'*.\n5. 🧘 **Health & Wellness:** Ask *'Exam stress relief tips'*.\n\nWhat would you like to check right now?",
        "action": None
    })

if __name__ == '__main__':
    print("[+] CampusGenie server starting on http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000)
