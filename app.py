import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8-sig')
    except Exception:
        pass
import json
import os
import re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'student_data.json')

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8-sig') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def calculate_classes_needed(attended, total, target=75):
    # (attended + x) / (total + x) >= target / 100
    # 100*attended + 100x >= target*total + target*x
    # (100 - target)*x >= target*total - 100*attended
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/student', methods=['GET'])
def get_student():
    data = load_data()
    return jsonify(data)

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    payload = request.json or {}
    sub_id = payload.get('subject_id')
    status = payload.get('status', 'present').lower()
    
    data = load_data()
    updated_sub = None
    
    for sub in data.get('subjects', []):
        if sub['id'] == sub_id:
            sub['total'] += 1
            if status == 'present':
                sub['attended'] += 1
            sub['percentage'] = round((sub['attended'] / sub['total']) * 100, 2)
            sub['status'] = 'safe' if sub['percentage'] >= data['student']['target_attendance'] else 'warning'
            updated_sub = sub
            break
            
    if updated_sub:
        # Calculate overall
        tot_att = sum(s['attended'] for s in data['subjects'])
        tot_all = sum(s['total'] for s in data['subjects'])
        overall_pct = round((tot_att / tot_all) * 100, 2) if tot_all else 0
        save_data(data)
        
        needed = calculate_classes_needed(updated_sub['attended'], updated_sub['total'])
        return jsonify({
            "success": True,
            "subject": updated_sub,
            "overall_percentage": overall_pct,
            "classes_needed": needed,
            "message": f"Attendance marked for {updated_sub['name']} as {status.upper()}."
        })
    return jsonify({"success": False, "message": "Subject not found."}), 404

@app.route('/api/chat', methods=['POST'])
def chat():
    payload = request.json or {}
    user_msg = payload.get('message', '').strip()
    msg_lower = user_msg.lower()
    
    data = load_data()
    subjects = data.get('subjects', [])
    timetable = data.get('timetable', [])
    target = data.get('student', {}).get('target_attendance', 75)
    
    # 1. ATTENDANCE INTENT
    if any(k in msg_lower for k in ['attendance', 'present', 'absent', 'shortage', 'percentage', 'bunk']):
        # Check if marking attendance
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
                
                needed = calculate_classes_needed(target_sub['attended'], target_sub['total'])
                alert_text = f"⚠️ Warning: Attendance is {target_sub['percentage']}%! You need to attend the next {needed} consecutive classes to reach 75%." if target_sub['status'] == 'warning' else "✅ You are safely above the 75% threshold!"
                
                return jsonify({
                    "reply": f"✅ **Marked {status.upper()}** for **{target_sub['name']}**!\n\n• **Updated Stats:** {target_sub['attended']}/{target_sub['total']} classes ({target_sub['percentage']}%)\n• {alert_text}",
                    "action": "refresh_data"
                })
        
        # Check specific subject attendance
        for s in subjects:
            if s['id'] in msg_lower or s['name'].lower() in msg_lower:
                needed = calculate_classes_needed(s['attended'], s['total'])
                status_icon = "⚠️" if s['percentage'] < target else "✅"
                advice = f"You are below the 75% rule! Attend the next **{needed} classes** consecutively to clear the shortage." if s['percentage'] < target else "You are safe! You can afford to miss 1-2 classes if urgent."
                return jsonify({
                    "reply": f"{status_icon} **{s['name']} Attendance Summary**:\n\n• **Current:** {s['attended']}/{s['total']} lectures ({s['percentage']}%)\n• **Faculty:** {s['faculty']}\n• **Status:** {s['status'].upper()}\n• **Advice:** {advice}",
                    "action": None
                })
                
        # Overall Attendance
        tot_att = sum(s['attended'] for s in subjects)
        tot_all = sum(s['total'] for s in subjects)
        overall = round((tot_att / tot_all) * 100, 2) if tot_all else 0
        
        warning_list = [s for s in subjects if s['percentage'] < target]
        warning_msg = ""
        if warning_list:
            warning_msg = "\n\n🚨 **Subjects Requiring Immediate Attention (< 75%):**\n"
            for w in warning_list:
                req = calculate_classes_needed(w['attended'], w['total'])
                warning_msg += f"• **{w['name']}**: {w['percentage']}% (Need +{req} lectures)\n"
        else:
            warning_msg = "\n\n🎉 Great job! You are above 75% in all registered subjects!"
            
        return jsonify({
            "reply": f"📊 **Your Overall Attendance Report**:\n\n• **Total Lectures:** {tot_att} / {tot_all}\n• **Overall Percentage:** **{overall}%** (Target: {target}%){warning_msg}\n\n*Tip: Say 'Mark OS present' or 'Mark DSA absent' to log today's class!*",
            "action": None
        })

    # 2. TIMETABLE INTENT
    if any(k in msg_lower for k in ['timetable', 'schedule', 'class', 'lecture', 'room', 'next class']):
        if 'next' in msg_lower:
            next_class = next((item for item in timetable if item['status'] in ['upcoming', 'ongoing']), timetable[0])
            return jsonify({
                "reply": f"⏰ **Your Next Upcoming Class**:\n\n• **Subject:** {next_class['subject']} ({next_class['code']})\n• **Time:** {next_class['time']}\n• **Venue:** {next_class['room']}\n• **Faculty:** {next_class['faculty']}",
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

    # 3. HEALTH & WELLNESS INTENT
    if any(k in msg_lower for k in ['stress', 'health', 'tired', 'sleep', 'anxious', 'headache', 'diet', 'water', 'breathe', 'relax']):
        return jsonify({
            "reply": "🧘 **Student Wellness & Stress Buster Check-In**:\n\n1. **4-7-8 Breathing Technique:** Inhale quietly through your nose for 4s, hold breath for 7s, exhale completely through mouth for 8s. Repeat 4 times.\n2. **Screen Eye Relief (20-20-20):** Shift your eyes to look at an object 20 feet away for 20 seconds.\n3. **Hydration:** A quick glass of water restores brain focus within 5 minutes.\n4. **Exam Stress Reality Check:** Remember that an exam tests what you know on paper today, not your true capability or self-worth. Take it one topic at a time!\n\n*Click the 'Start Breathing' button on the dashboard for a guided 1-minute meditation circle!*",
            "action": "open_breathing"
        })

    # 4. STUDY BUDDY INTENT (Knowledge base or Smart Explainer)
    for key, info in STUDY_KNOWLEDGE_BASE.items():
        if key in msg_lower:
            points_text = "\n".join([f"• {p}" for p in info['points']])
            return jsonify({
                "reply": f"📚 **Study Buddy Breakdown: {info['title']}**\n\n💡 **Simplified Explanation:**\n{info['eli10']}\n\n🔑 **Key Exam Points:**\n{points_text}\n\n🎯 **Exam/Viva Pro-Tip:**\n{info['exam_tip']}",
                "action": None
            })

    if any(k in msg_lower for k in ['study', 'explain', 'doubt', 'notes', 'exam tips', 'concept']):
        return jsonify({
            "reply": f"🤖 **Study Buddy at your service!**\n\nI can explain core engineering and computer science concepts in simple language with exam tips. Try asking me:\n\n• *'Explain binary search'*\n• *'What is deadlock in OS?'*\n• *'Explain polymorphism in simple words'*\n• *'Explain normalization 1NF, 2NF, 3NF'*\n• *'TCP vs UDP difference for exam'*",
            "action": None
        })

    # 5. DEFAULT / GREETINGS / HELP
    return jsonify({
        "reply": "👋 **Hello Rahul! I'm CampusGenie**, your AI Student Copilot.\n\nHere is how I can assist you today:\n1. 📊 **Attendance Tracker:** Ask *'What is my attendance?'* or say *'Mark OS present'*.\n2. 📅 **Smart Timetable:** Ask *'What is my next class?'* or *'Show today's timetable'*.\n3. 📚 **Study Buddy:** Ask *'Explain binary search'* or *'Explain deadlock'*.\n4. 🧘 **Health & Wellness:** Ask *'Exam stress relief tips'* or *'Hydration check'*.\n\nWhat would you like to check right now?",
        "action": None
    })

if __name__ == '__main__':
    print("🚀 CampusGenie server starting on http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000)

