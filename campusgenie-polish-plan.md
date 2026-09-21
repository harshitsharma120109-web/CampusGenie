# CampusGenie — Polish & Expansion Plan

## Top-Level Overview

The CampusGenie codebase is ~85% production-ready. All core portals (Student, Teacher, HOD, Parent), AI Chat, Attendance, Fees, and Assignments are fully working. This plan polishes and expands four areas without touching any working feature:

1. **AI Tutor Expansion** — Add ~10 more CS topics to `STUDY_KNOWLEDGE` in `app.py`
2. **Health Triage Expansion** — Add ~8 more conditions to `HEALTH_SYMPTOMS` in `app.py`
3. **Sample Data Expansion** — Add more students, subjects, timetable entries, and assignments to `data/student_data.json`
4. **Mobile UI Responsiveness** — Fix layout, padding, and overflow issues in `templates/index.html` and `static/css/style.css`

All changes are additive — no existing logic is modified or removed.

---

## Sub-Task 1: Expand AI Academic Tutor Topics

**Status:** `[ ] pending`

### Intent
`app.py` contains a `STUDY_KNOWLEDGE` dictionary that powers the AI chat tutor. It currently covers 32 CS/Engineering topics. Adding more topics makes the tutor genuinely useful for modern subjects that students ask about.

### Topics to Add (~10)
| Key | Subject |
|-----|---------|
| `cryptography` | Cryptography & Network Security — symmetric/asymmetric, RSA, AES, digital signatures |
| `cloud computing` | Cloud Computing — IaaS/PaaS/SaaS, AWS/Azure/GCP overview, elasticity |
| `machine learning` | Machine Learning basics — supervised/unsupervised, overfitting, bias-variance |
| `neural networks` | Neural Networks & Deep Learning — perceptron, backpropagation, activation functions |
| `blockchain` | Blockchain — distributed ledger, consensus algorithms, smart contracts |
| `iot` | Internet of Things — sensors, protocols (MQTT, CoAP), edge computing |
| `computer graphics` | Computer Graphics — rasterization, OpenGL pipeline, transformations |
| `compiler design` | Compiler Design — lexical analysis, parsing, syntax-directed translation |
| `software testing` | Software Testing — unit/integration/system, black-box vs white-box, TDD |
| `microprocessors` | Microprocessors — 8085/8086 architecture, registers, instruction set |

### Expected Outcomes
- Each new key in `STUDY_KNOWLEDGE` has: `title`, `explanation`, `complexity` (where applicable), `tips` array
- Chat correctly routes questions like "explain blockchain" or "what is cloud computing" to the new entries
- No existing topic is altered

### Todo List
1. Open `app.py` and locate the `STUDY_KNOWLEDGE` dictionary
2. Append the 10 new topic entries at the end of the dictionary
3. Add keyword aliases for each topic in the chat router's topic-matching section (e.g. `"cloud"` → `cloud computing`, `"ml"` → `machine learning`, `"nn"` → `neural networks`)
4. Verify the longest-alias-first sort still works correctly after additions

### Relevant Context
- File: `app.py` — search for `STUDY_KNOWLEDGE`
- The chat router uses `sorted(STUDY_KNOWLEDGE.keys(), key=len, reverse=True)` to match topics — new keys must follow the same pattern

---

## Sub-Task 2: Expand AI Health Triage Conditions

**Status:** `[ ] pending`

### Intent
`app.py` contains a `HEALTH_SYMPTOMS` dictionary with 19 conditions. Adding 8 more covers common student health issues that currently fall through to the web search fallback, returning low-quality results.

### Conditions to Add (~8)
| Key | Condition |
|-----|-----------|
| `nausea` | Nausea — medicine (Domperidone), home remedy (ginger tea, small bland meals), doctor flag if >24h |
| `dizziness` | Dizziness/Vertigo — sit down, hydrate, Cinnarizine; doctor flag if sudden severe |
| `ear pain` | Ear Pain/Earache — warm compress, Otrivin drops; doctor flag if fever or discharge |
| `sunburn` | Sunburn — cool compress, aloe vera gel, avoid sun; doctor flag if blisters |
| `food poisoning` | Food Poisoning — ORS, rest, bland BRAT diet; doctor flag if blood in stool |
| `anxiety` | Anxiety/Panic attack — 4-7-8 breathing, grounding technique; doctor flag if recurring |
| `sore throat` | Sore Throat — warm salt water gargle, Strepsils, honey-ginger; doctor if 3+ days |
| `nose bleed` | Nose Bleed (Epistaxis) — pinch nose, lean forward, cold compress; doctor if >10 min |

### Expected Outcomes
- Each new key in `HEALTH_SYMPTOMS` has: `medicines`, `home_remedy`, `doctor_alert`, `severity`
- Keyword aliases added so "nose bleeding", "vertigo", "panic attack" all route correctly
- Chat responds with structured first-aid info for all 8 new conditions

### Todo List
1. Open `app.py` and locate the `HEALTH_SYMPTOMS` dictionary
2. Append the 8 new condition entries
3. Add keyword aliases in the health router's symptom-detection section
4. Verify no alias collision with existing symptoms

### Relevant Context
- File: `app.py` — search for `HEALTH_SYMPTOMS`
- Same multi-alias mapping pattern used for existing conditions (e.g. `"loose motions"` → `diarrhea`)

---

## Sub-Task 3: Expand Sample Data

**Status:** `[ ] pending`

### Intent
The current dataset has only 3 students, 4 subjects, 4 timetable entries, and 2 assignments. Richer sample data makes the app look more realistic for demos and hackathon judging.

### Additions
| Area | Target |
|------|--------|
| Students | Add 3 more students (total: 6) with varied attendance — some safe, some defaulters |
| Subjects | Add 2 more subjects: Software Engineering (CS-505), Computer Graphics (CS-506) |
| Timetable | Add 4 more time slots including evening practical sessions and Saturday |
| Assignments | Add 2 more assignments (one for DBMS, one for CN) with MCQ questions |
| Opportunities | Add 2 more opportunities (Microsoft Learn Student Ambassador, HackWithInfy) |
| Notices | Add 2 more notices (Mid-Semester Exam schedule, Library clearance) |

### Expected Outcomes
- `data/student_data.json` loads with 6 students, 6 subjects, 8+ timetable entries, 4 assignments
- New students have realistic attendance percentages (mix of safe and warning)
- At least 2 of the new students appear in the HOD Defaulters Radar
- All new entries follow the exact existing JSON schema

### Todo List
1. Read `data/student_data.json` to confirm exact schema
2. Add 3 new student objects following the exact existing schema (attendance, marks, fees objects for all subjects)
3. Add 2 new subject objects; update existing students to include attendance/marks for the new subjects
4. Add 4 new timetable entries
5. Add 2 new assignment objects with questions array
6. Add 2 new opportunities and 2 new notices
7. Validate JSON is well-formed after edits

### Relevant Context
- File: `data/student_data.json`
- Schema reference: See existing `22CS1084` student entry — all new students must follow same structure
- New subjects added here must also be added to every student's `attendance` and `marks` objects

---

## Sub-Task 4: Fix Mobile UI Responsiveness

**Status:** `[ ] pending`

### Intent
On mobile screens the current layout has overflow, padding, and stacking issues. The primary problems are in:
- The top navigation bar (role tabs overflow on small screens)
- The 12-column grid (does not collapse cleanly on mobile)
- The chat sidebar (gets crushed or overflows)
- Subject cards (text wraps poorly at <375px)
- Modal dialogs (extend beyond viewport on small phones)

### Expected Outcomes
- On screens ≤640px (mobile): chat sidebar stacks below the main content panel
- Navigation role-tabs scroll horizontally instead of wrapping/overflowing
- All modals respect max-w-full and scroll internally if tall
- Subject cards use `min-w-0` and `truncate` to prevent text overflow
- No horizontal scroll on the page body at 375px viewport width

### Todo List
1. Read `templates/index.html` — identify the main grid wrapper, nav-tabs, chat sidebar, subject card elements
2. Add `overflow-x-auto` scroll container around role-switcher tabs in the nav bar
3. Change the main content grid from a fixed `grid-cols-12` to `grid-cols-1 lg:grid-cols-12` so it stacks on mobile
4. Add `lg:col-span-7` and `lg:col-span-5` to the content and chat columns respectively (removing unconditional `col-span` values)
5. Add `overflow-hidden min-w-0` to subject cards to prevent text overflow
6. Add `max-w-full overflow-y-auto max-h-screen` to all modal inner containers in `index.html`
7. Add `overflow-x: hidden` to `body` in `static/css/style.css`
8. Test layout at conceptual 375px, 768px, and 1280px breakpoints by reviewing class usage

### Relevant Context
- File: `templates/index.html` — main grid, nav tabs, modals (~1800 lines SPA)
- File: `static/css/style.css` — custom overrides (~100 lines)
- Tailwind breakpoints: `sm` = 640px, `md` = 768px, `lg` = 1024px

---

## Implementation Notes

- All four sub-tasks are independent and can be executed in any order
- Sub-Task 3 (sample data) should be done before Sub-Task 1/2 so the chat tutor can answer questions about the new subjects in context
- Sub-Task 4 (mobile) is purely additive CSS/HTML class changes — no logic changes
- No new dependencies are required for any sub-task
- After each sub-task, manually verify the affected feature in the browser before marking complete
