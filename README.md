# 🎓 CampusGenie — 360° Smart Campus ERP & AI Student Copilot
> **SkillUp Hackathon in collaboration with IBM SkillsBuild**  
> **Track:** Track 1 — Student AI Track (EdTech + Productivity + Student Wellness)  
> **Developed using:** IBM Bob AI IDE  
> 
> 📄 **Official Document on IBM Bob Usage:** [Read IBM_BOB_USAGE.md](./IBM_BOB_USAGE.md)

---

## 📌 Problem Statement & Why It Matters
College students juggle multiple responsibilities every day—attending lectures, avoiding the strict **75% minimum attendance rule**, tracking daily schedules, preparing for exams, managing sudden hostel illnesses, and searching for career opportunities.

**CampusGenie** unifies **Academic Attendance, Exam Results, Timetables, AI Doubt Solving, Health First-Aid, and Verified Job Opportunities** into a single glassmorphic dashboard.

---

## 🚀 Key Features

### 1. 📊 Subject Attendance & Exam Marks Matrix
- Real-time subject-wise percentage calculation.
- Automated alert triggers when attendance dips below 75%.
- **Actionable Recovery Calculation:** Tells the student the exact number of consecutive lectures needed to clear shortage (e.g., *"You need to attend next 2 OS lectures"*).
- **Exam Marks & Grades:** Tracks scores out of 100 with automated **Pass / Fail** evaluation.
- 1-click **Present / Absent** logging for teachers and students.

### 2. 📅 Dynamic Timetable & Lecture Tracker
- Displays scheduled classes with time, lecture halls/labs, and faculty names.
- Complete details: **Who** takes the class, **Where** it takes place, and **When**.

### 3. 📚 AI Academic Doubt Solver
- "Explain Like I'm 10" simple conceptual breakdowns for CS & Engineering topics.
- Direct exam pro-tips and frequently asked viva questions (Deadlock, Binary Search, DBMS Normalization, OOP Polymorphism, TCP/UDP).

### 4. 🩺 AI Health & Symptom Triage (First-Aid & Medicines)
- Symptom-based triage (fever, headache, cold, stomach ache, acidity, stress).
- Recommends safe over-the-counter (OTC) first-aid medicines, home remedies, and campus clinic warning flags.

### 5. 🏆 Hackathons & Jobs Opportunities Board
- Curated board for national hackathons, coding contests, and internships with direct apply links.

### 6. 👨‍🏫 Faculty Administration & Multi-Student Roster
- Add unlimited students and switch between student profiles with one click.
- Enter student exam marks, schedule classes, and broadcast college notices.

---

## 🛠️ Tech Stack
- **Development Environment:** IBM Bob AI IDE
- **Backend:** Python 3.12, Flask REST API
- **Frontend:** Responsive Glassmorphic UI (Tailwind CSS, FontAwesome 6, Vanilla JavaScript)
- **Data Layer:** Local JSON state store (`data/student_data.json`)
- **Documentation:** [IBM_BOB_USAGE.md](./IBM_BOB_USAGE.md)

---

## 💻 How to Run CampusGenie

```bash
# 1. Clone repository
git clone https://github.com/harshitsharma120109-web/CampusGenie.git
cd CampusGenie

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run server
python app.py

# 4. Open in browser: http://127.0.0.1:5000
```
