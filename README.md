# 🎓 CampusGenie — All-in-One AI Student Copilot
> **SkillUp Hackathon in collaboration with IBM SkillsBuild**  
> **Track:** Track 1 — Student AI Track (EdTech + Productivity + Student Wellness)  
> **Developed using:** IBM Bob AI Environment

---

## 📌 Problem Statement & Why It Matters
College students juggle multiple responsibilities every day—attending lectures, avoiding the strict **75% minimum attendance rule**, tracking daily schedules, preparing for exams, and handling acute academic stress. 

Currently, students have to check separate ERP portals for attendance, browse through messy WhatsApp groups for timetables, and struggle alone with exam anxiety. 

**CampusGenie** solves this by providing a unified, intelligent AI Copilot that combines **Campus Administration, Academic Learning, and Mental Wellness** into a single glassmorphic dashboard.

---

## 🚀 Key Features

### 1. 📊 Smart Attendance Manager & 75% Rule Alert
- Real-time subject-wise percentage calculation.
- Automated alert triggers when attendance dips below 75%.
- **Actionable Recovery Calculation:** Tells the student the exact number of consecutive lectures needed to clear attendance shortage (e.g., *"You need to attend next 2 OS lectures"*).
- Instant 1-click **Present / Absent** logging.

### 2. 📅 Dynamic Timetable & Lecture Tracker
- Displays today's scheduled classes with time, lecture halls, and faculty names.
- Live badges indicating **Ongoing**, **Upcoming**, or **Completed** sessions.
- Natural language queries: *"What's my next lecture?"*

### 3. 📚 AI Study Buddy & Doubt Solver
- "Explain Like I'm 10" simple conceptual breakdowns for CS & Engineering topics.
- Direct exam pro-tips and frequently asked viva questions (Deadlock, Binary Search, DBMS Normalization, OOP Polymorphism, TCP/UDP).

### 4. 🧘 Student Wellness & 4-7-8 Breathing Reset
- Integrated stress-buster module.
- Guided 1-minute 4-7-8 deep breathing modal to soothe exam anxiety and regain focus.
- 20-20-20 screen eye strain rules and healthy study snack advice.

---

## 🛠️ Tech Stack & IBM Bob Integration
- **Development Environment:** IBM Bob AI IDE
- **Backend:** Python 3.12, Flask REST API
- **Frontend:** Modern Responsive Glassmorphic UI (Tailwind CSS, FontAwesome 6, Vanilla JavaScript)
- **Data Layer:** Local JSON state store (`student_data.json`)

---

## 💻 How to Run CampusGenie

### Inside IBM Bob:
1. Open **IBM Bob**.
2. Click **File -> Open Folder** and select `C:\Users\manoj\.gemini\antigravity\scratch\campus_genie`.
3. Open Bob's built-in terminal: `Ctrl + \`` (or `Terminal -> New Terminal`).
4. Run:
   ```bash
   python app.py
   ```
5. Open your browser and visit:
   ```
   http://127.0.0.1:5000
   ```

---

## 🎤 2-Minute Presentation Pitch for Judges (Hindi / Hinglish Script)

> *"Good afternoon respected judges!*  
> *Hamara project hai **CampusGenie — All-in-One AI Student Copilot**, jise humne **IBM Bob** environment ke andar develop kiya hai under **Track 1: Student AI Track**.*  
> 
> *Har college student ki sabse badi daily problem hoti hai **75% attendance rule maintain karna**, daily lecture timetable track karna, aur exam time par doubts aur mental stress manage karna.*  
> 
> *CampusGenie in sabhi cheezon ko ek single intelligent AI platform par solve karta hai:*  
> *1. Ye student ki subject-wise attendance track karta hai aur shortage aane par exact calculation batata hai ki kitni classes attend karni padengi.*  
> *2. Student simple bhasha mein chatbot se puch sakta hai ki 'Mera agla lecture kaun sa hai?' ya 'Binary search simple bhasha me samjhao'.*  
> *3. Humne isme **Student Wellness Module** bhi add kiya hai jisme guided 4-7-8 breathing exercise aur exam stress relief tips hain.*  
> 
> *Is tarah CampusGenie sirf ek administrative tool nahi, balki har student ka complete 24/7 AI buddy ban jaata hai. Thank you!"*
