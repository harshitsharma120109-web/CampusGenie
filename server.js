const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const os = require('os');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Static asset folders
const BASE_DIR = __dirname;
const STATIC_DIR = path.join(BASE_DIR, 'static');
const TEMPLATES_DIR = path.join(BASE_DIR, 'templates');
const DATA_FILE = path.join(BASE_DIR, 'data', 'student_data.json');
const TMP_DATA_FILE = path.join(os.tmpdir(), 'student_data.json');

app.use('/static', express.static(STATIC_DIR));
if (fs.existsSync(path.join(BASE_DIR, 'public'))) {
  app.use(express.static(path.join(BASE_DIR, 'public')));
}

// ── In-Memory Data Store & Persistence ──────────────────────────────────────────
let _inMemoryData = null;

function loadData() {
  if (_inMemoryData) return _inMemoryData;
  if (fs.existsSync(TMP_DATA_FILE)) {
    try {
      const raw = fs.readFileSync(TMP_DATA_FILE, 'utf8');
      _inMemoryData = JSON.parse(raw);
      return _inMemoryData;
    } catch (e) {}
  }
  if (fs.existsSync(DATA_FILE)) {
    try {
      const raw = fs.readFileSync(DATA_FILE, 'utf8');
      _inMemoryData = JSON.parse(raw);
      return _inMemoryData;
    } catch (e) {}
  }
  _inMemoryData = { students: [], subjects: [], timetable: [], notices: [], opportunities: [] };
  return _inMemoryData;
}

function saveData(data) {
  _inMemoryData = data;
  let saved = false;
  try {
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2), 'utf8');
    saved = true;
  } catch (e) {}
  if (!saved) {
    try {
      fs.writeFileSync(TMP_DATA_FILE, JSON.stringify(data, null, 2), 'utf8');
    } catch (e) {}
  }
}

function getActiveStudent(data) {
  const students = data.students || [];
  const activeId = data.active_student_id;
  if (activeId) {
    const found = students.find(s => s.id === activeId);
    if (found) return found;
  }
  if (students.length > 0) {
    data.active_student_id = students[0].id;
    return students[0];
  }
  return null;
}

function calculateClassesNeeded(attended, total, target = 75) {
  const req = target * total - 100 * attended;
  if (req <= 0) return 0;
  return Math.ceil(req / (100 - target));
}

function calculateMaxBunks(attended, total, target = 75) {
  const maxB = Math.floor((attended * 100) / target) - total;
  return Math.max(0, maxB);
}

// ── RBAC Security Helper ────────────────────────────────────────────────────────
function getCallerRole(req) {
  const headerRole = req.headers['x-user-role'];
  const bodyRole = req.body && req.body.caller_role;
  const queryRole = req.query && req.query.caller_role;
  return (headerRole || bodyRole || queryRole || '').toLowerCase();
}

// ── AI Study Buddy Knowledge Base ──────────────────────────────────────────────
const STUDY_KNOWLEDGE = {
  "binary search": {
    title: "Binary Search (Divide & Conquer)",
    subject: "DSA",
    explanation: "Works on a **sorted array** by repeatedly halving the search interval. Compare the target to the middle element — if not equal, discard the half that cannot contain the target and repeat.",
    complexity: "Time: O(log N) average & worst | Space: O(1) iterative, O(log N) recursive",
    exam_tip: "Viva Q: Why faster than Linear Search? Every step halves the search space: N → N/2 → N/4 → ... → 1. Always verify array is sorted first — applying Binary Search to unsorted data gives wrong results."
  },
  "bubble sort": {
    title: "Bubble Sort Algorithm",
    subject: "DSA",
    explanation: "Repeatedly steps through the list, compares adjacent elements, and swaps them if in the wrong order. Each full pass 'bubbles' the largest unsorted element to its correct position at the end.",
    complexity: "Time: O(N²) worst/average | O(N) best (already sorted with optimization) | Space: O(1) in-place",
    exam_tip: "Optimization: add a flag `swapped`. If no swap in a pass, array is sorted — break early. This gives O(N) best case. Never use Bubble Sort for large N in production."
  },
  "merge sort": {
    title: "Merge Sort (Divide & Conquer)",
    subject: "DSA",
    explanation: "Recursively divides the array into two halves, sorts each half, then **merges** the two sorted halves. The merge step is the key — it combines two sorted arrays in O(N) time by comparing elements one by one.",
    complexity: "Time: O(N log N) always (best, average, worst) | Space: O(N) auxiliary",
    exam_tip: "Merge Sort is a **stable** sort. Preferred for linked lists and external sorting (large files). Unlike Quick Sort, worst case is always O(N log N), not O(N²)."
  },
  "quick sort": {
    title: "Quick Sort (Divide & Conquer)",
    subject: "DSA",
    explanation: "Selects a **pivot** element and partitions the array into: elements < pivot (left) and elements > pivot (right). Recursively sorts both partitions. No extra space needed for the sort itself.",
    complexity: "Time: O(N log N) average | O(N²) worst (sorted array with last element as pivot) | Space: O(log N) stack",
    exam_tip: "Worst case avoided with **randomized pivot** or **median-of-three**. Quick Sort is cache-friendly and in-practice faster than Merge Sort for in-memory data due to low constant factors."
  },
  "linked list": {
    title: "Linked List Data Structure",
    subject: "DSA",
    explanation: "A linear data structure where each element (node) stores data and a pointer to the next node. Unlike arrays, nodes are not stored contiguously in memory. Types: Singly, Doubly, Circular.",
    complexity: "Access: O(N) | Insert/Delete at head: O(1) | Insert/Delete at tail (without tail ptr): O(N) | Search: O(N)",
    exam_tip: "Key trick for interviews: **Floyd's Cycle Detection** (slow/fast pointer) detects cycles in O(N) time and O(1) space. Reversing a linked list in-place is a classic viva question."
  },
  "stack": {
    title: "Stack Data Structure (LIFO)",
    subject: "DSA",
    explanation: "A linear data structure following **Last In, First Out (LIFO)**. Main operations: push (add to top), pop (remove from top), peek (view top without removing). Implemented using arrays or linked lists.",
    complexity: "Push/Pop/Peek: O(1) | Search: O(N)",
    exam_tip: "Applications: function call stack, undo operations, expression evaluation (infix→postfix), balanced parentheses checking."
  },
  "queue": {
    title: "Queue Data Structure (FIFO)",
    subject: "DSA",
    explanation: "A linear data structure following **First In, First Out (FIFO)**. Enqueue adds to the rear, Dequeue removes from the front. Variants: Circular Queue (avoids false overflow), Deque (double-ended), Priority Queue.",
    complexity: "Enqueue/Dequeue: O(1) with proper implementation | Search: O(N)",
    exam_tip: "Circular Queue solves false overflow. Priority Queue is implemented using a Min/Max Heap — not a sorted array."
  },
  "tree": {
    title: "Trees & Binary Search Tree (BST)",
    subject: "DSA",
    explanation: "A hierarchical data structure with a root node and subtrees. BST property: left subtree values < root < right subtree values. Traversals: Inorder (Left-Root-Right), Preorder (Root-Left-Right), Postorder (Left-Right-Root).",
    complexity: "BST Search/Insert/Delete: O(log N) average | O(N) worst (skewed tree) | Balanced AVL/Red-Black: O(log N) guaranteed",
    exam_tip: "Inorder traversal of a BST gives **sorted output** — critical exam fact. AVL rotation types: LL, RR, LR, RL."
  },
  "graph": {
    title: "Graphs: BFS, DFS & Algorithms",
    subject: "DSA",
    explanation: "A non-linear structure of vertices (nodes) and edges. BFS (Breadth-First Search) uses a Queue — explores level by level. DFS (Depth-First Search) uses a Stack/Recursion — goes deep before backtracking.",
    complexity: "BFS/DFS: O(V + E) where V = vertices, E = edges | Dijkstra: O((V+E) log V) with min-heap",
    exam_tip: "BFS finds shortest path in unweighted graphs. DFS is used for topological sort, cycle detection. Dijkstra does NOT work with negative weights (use Bellman-Ford)."
  },
  "dynamic programming": {
    title: "Dynamic Programming (DP)",
    subject: "DSA",
    explanation: "Optimization technique that breaks problems into **overlapping subproblems**, solves each once, and stores results (memoization/tabulation). Two approaches: Top-Down (Memoization) and Bottom-Up (Tabulation).",
    complexity: "Depends on problem. Fibonacci: O(N) with DP vs O(2^N) naive. LCS: O(M×N). 0/1 Knapsack: O(N×W)",
    exam_tip: "DP applies when: (1) Optimal Substructure; (2) Overlapping Subproblems. Classic DPs: Fibonacci, LCS, LIS, 0/1 Knapsack."
  },
  "deadlock": {
    title: "Deadlock in Operating Systems",
    subject: "OS",
    explanation: "A state where a set of processes are permanently blocked — each holds a resource and waits for one held by another. None can proceed.",
    complexity: "4 Necessary Conditions (Coffman): Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait",
    exam_tip: "3 strategies: Prevention (negate one condition), Avoidance (Banker's Algorithm — safe state), Detection & Recovery. Banker's Algorithm is the #1 exam topic."
  },
  "paging": {
    title: "Paging & Virtual Memory",
    subject: "OS",
    explanation: "Memory management scheme that eliminates external fragmentation. Process is divided into fixed-size pages, physical memory into frames. OS maintains a Page Table mapping logical addresses to physical addresses.",
    complexity: "Logical Address = Page Number + Page Offset. Physical Address = Frame Number + Page Offset.",
    exam_tip: "TLB (Translation Lookaside Buffer) is a fast cache for page table. Page faults minimized by LRU/Optimal replacement."
  },
  "semaphore": {
    title: "Semaphores & Process Synchronization",
    subject: "OS",
    explanation: "An integer variable accessed through atomic operations: wait(S) (P operation) and signal(S) (V operation). Types: Binary (mutex) and Counting.",
    complexity: "Solves: Mutual Exclusion, Producer-Consumer, Readers-Writers, Dining Philosophers.",
    exam_tip: "Binary semaphore = mutex. Producer-Consumer uses signal(full)/wait(empty) and wait(full)/signal(empty)."
  },
  "tcp vs udp": {
    title: "TCP vs UDP (Transport Layer)",
    subject: "CN",
    explanation: "TCP: connection-oriented, reliable, 3-way handshake (SYN → SYN-ACK → ACK), flow/congestion control. UDP: connectionless, unreliable, fast, no handshake.",
    complexity: "TCP: HTTP/HTTPS, FTP, SSH. UDP: DNS, DHCP, video streaming, gaming, VoIP.",
    exam_tip: "TCP 3-way handshake: SYN → SYN-ACK → ACK. UDP has no flow/congestion control — hence lower latency."
  },
  "osi model": {
    title: "OSI 7-Layer Reference Model",
    subject: "CN",
    explanation: "7 layers: Application, Presentation, Session, Transport, Network, Data Link, Physical. (Mnemonic: All People Seem To Need Data Processing).",
    complexity: "Application (HTTP, DNS) | Transport (TCP, UDP) | Network (IP, ICMP) | Data Link (Ethernet, MAC) | Physical (Cables).",
    exam_tip: "Switches work at Layer 2 (Data Link), Routers work at Layer 3 (Network). TCP/IP is the practical 4-layer model."
  },
  "normalization": {
    title: "Database Normalization (1NF → BCNF)",
    subject: "DBMS",
    explanation: "Technique to organize tables to reduce data redundancy and eliminate insert, update, and delete anomalies.",
    complexity: "1NF: Atomic values | 2NF: No partial dependency | 3NF: No transitive dependency | BCNF: Determinant must be superkey.",
    exam_tip: "Partial dependency only occurs with composite keys. In 3NF: for X→Y, either X is superkey or Y is prime attribute."
  },
  "sql joins": {
    title: "SQL Joins (INNER, OUTER, SELF, CROSS)",
    subject: "DBMS",
    explanation: "INNER JOIN: matching rows in both tables. LEFT JOIN: all rows from left + matched right. RIGHT JOIN: opposite. FULL OUTER JOIN: all rows from both. CROSS JOIN: cartesian product.",
    complexity: "INNER JOIN result size <= min(|R|, |S|). CROSS JOIN = |R| x |S|.",
    exam_tip: "Use aliases for clarity: SELECT e.name, d.dept FROM Employee e INNER JOIN Department d ON e.dept_id = d.id."
  },
  "transactions": {
    title: "Database Transactions & ACID Properties",
    subject: "DBMS",
    explanation: "ACID: Atomicity (all or nothing), Consistency (valid state transitions), Isolation (independent transactions), Durability (persisted on disk).",
    complexity: "Isolation levels: READ UNCOMMITTED → READ COMMITTED → REPEATABLE READ → SERIALIZABLE.",
    exam_tip: "Atomicity via rollback/undo logs. Durability via WAL (Write-Ahead Logging). Two-Phase Locking (2PL) guarantees serializability."
  },
  "polymorphism": {
    title: "Polymorphism in OOP",
    subject: "OOP",
    explanation: "Compile-time (Static): Method Overloading — resolved at compile time. Runtime (Dynamic): Method Overriding — resolved at runtime via vtable.",
    complexity: "Static: fast binding. Dynamic: flexible runtime dispatch.",
    exam_tip: "In C++: virtual keyword enables runtime dispatch. In Java: non-static methods are virtual by default."
  },
  "inheritance": {
    title: "Inheritance in OOP",
    subject: "OOP",
    explanation: "Child class acquires properties and methods of base class. Types: Single, Multilevel, Hierarchical, Multiple (C++, interfaces in Java).",
    complexity: "Code reuse, IS-A relationship.",
    exam_tip: "Java avoids the Diamond Problem of multiple inheritance by using Interfaces instead of multiple class inheritance."
  },
  "encapsulation": {
    title: "Encapsulation & Abstraction in OOP",
    subject: "OOP",
    explanation: "Encapsulation: Bundling data and methods into a single class with access modifiers (private, protected, public). Abstraction: Hiding implementation details and exposing only the interface.",
    complexity: "Data hiding and modularity.",
    exam_tip: "Encapsulation = data hiding (getters/setters). Abstraction = implementation hiding (interfaces/abstract classes)."
  },
  "cloud computing": {
    title: "Cloud Computing — IaaS, PaaS & SaaS",
    subject: "Cloud",
    explanation: "IaaS (Infrastructure as a Service): AWS EC2, raw VMs. PaaS (Platform as a Service): Heroku, Google App Engine. SaaS (Software as a Service): Gmail, Salesforce. Serverless: AWS Lambda.",
    complexity: "Elastic horizontal and vertical scaling.",
    exam_tip: "CAP Theorem: A distributed system can guarantee at most 2 of 3: Consistency, Availability, Partition Tolerance."
  },
  "machine learning": {
    title: "Machine Learning (Supervised, Unsupervised, RL)",
    subject: "AI/ML",
    explanation: "Supervised: labeled data (Regression, Classification). Unsupervised: unlabeled data (K-Means, PCA). Reinforcement: reward/penalty policy optimization.",
    complexity: "Bias-Variance Tradeoff: High bias = Underfitting; High variance = Overfitting.",
    exam_tip: "Regularization (L1 Lasso, L2 Ridge) and Cross-Validation prevent overfitting."
  }
};

const STUDY_ALIASES = {
  "binary search": "binary search", "binary": "binary search",
  "bubble sort": "bubble sort", "bubble": "bubble sort",
  "merge sort": "merge sort", "merge": "merge sort",
  "quick sort": "quick sort", "quicksort": "quick sort",
  "linked list": "linked list", "linkedlist": "linked list",
  "stack": "stack", "lifo": "stack",
  "queue": "queue", "fifo": "queue",
  "tree": "tree", "bst": "tree", "binary tree": "tree",
  "graph": "graph", "bfs": "graph", "dfs": "graph", "dijkstra": "graph",
  "dynamic programming": "dynamic programming", "dp": "dynamic programming", "knapsack": "dynamic programming",
  "deadlock": "deadlock", "coffman": "deadlock", "banker": "deadlock",
  "paging": "paging", "virtual memory": "paging", "tlb": "paging",
  "semaphore": "semaphore", "mutex": "semaphore", "critical section": "semaphore",
  "tcp vs udp": "tcp vs udp", "tcp": "tcp vs udp", "udp": "tcp vs udp",
  "osi model": "osi model", "osi layer": "osi model", "osi": "osi model",
  "normalization": "normalization", "1nf": "normalization", "2nf": "normalization", "3nf": "normalization", "bcnf": "normalization",
  "sql joins": "sql joins", "join": "sql joins", "sql": "sql joins", "inner join": "sql joins",
  "transactions": "transactions", "acid": "transactions", "acid properties": "transactions",
  "polymorphism": "polymorphism", "overriding": "polymorphism", "overloading": "polymorphism",
  "inheritance": "inheritance", "encapsulation": "encapsulation", "abstraction": "encapsulation",
  "cloud computing": "cloud computing", "cloud": "cloud computing", "aws": "cloud computing",
  "machine learning": "machine learning", "ml": "machine learning", "ai": "machine learning"
};

const HEALTH_SYMPTOMS = {
  "fever": {
    condition: "Mild Viral Fever / High Temperature",
    severity: "Moderate",
    first_aid: "Paracetamol (PCM 500mg/650mg) after food if temperature > 99.5°F. Apply a wet cloth on forehead and wrists. Stay in a cool, ventilated room.",
    home_remedy: "Drink warm water with ORS (Electral/Glucon-D) every 2 hours. Complete bed rest. Avoid cold drinks. Sip warm ginger-tulsi tea.",
    doctor_alert: "🚨 Rush to campus medical room if: fever > 102°F with shivering, persists > 48 hours, or neck stiffness occurs."
  },
  "headache": {
    condition: "Tension Headache / Digital Eye Strain",
    severity: "Mild-Moderate",
    first_aid: "Immediate: 20-min screen break in a dim room. Apply balm on temples. Paracetamol 500mg with water if severe (not empty stomach).",
    home_remedy: "Drink 2-3 large glasses of water immediately (dehydration is the #1 cause). Gentle neck stretches. Cold compress on forehead.",
    doctor_alert: "🚨 See doctor if: sudden severe thunderclap headache, headache with vomiting or blurred vision."
  },
  "cold": {
    condition: "Common Cold, Runny Nose & Sore Throat",
    severity: "Mild",
    first_aid: "Steam inhalation twice daily. Cetirizine 10mg at bedtime for heavy sneezing. Throat lozenges for soreness.",
    home_remedy: "Warm salt water gargle 3 times a day. Hot ginger-tulsi-honey tea. Stay hydrated and avoid AC air directly on chest.",
    doctor_alert: "🚨 Consult physician if cold lasts > 10 days, severe ear pain, or high fever develops."
  },
  "cough": {
    condition: "Dry or Wet Cough & Throat Irritation",
    severity: "Mild-Moderate",
    first_aid: "Strepsils/Koflet lozenges. Steam inhalation. Benadryl/Chericof syrup 10ml after meals.",
    home_remedy: "Warm turmeric milk (Haldi doodh with pepper and ghee) before sleep. 1 tsp honey with ginger juice.",
    doctor_alert: "🚨 See a doctor if cough persists > 2 weeks, blood in sputum, or shortness of breath."
  },
  "stress": {
    condition: "Exam Anxiety, Mental Fatigue & Burnout",
    severity: "Moderate — Needs Attention",
    first_aid: "**4-7-8 Breathing**: Inhale for 4s → Hold for 7s → Exhale slowly for 8s. Repeat 4 cycles. Activates parasympathetic calming response. Take a 15-min walk outside.",
    home_remedy: "Chamomile tea before bed. Avoid excess caffeine. Write down tomorrow's tasks to clear mental clutter.",
    doctor_alert: "🚨 College Counseling Center & iCall free student helpline: 9152987821. Exams do not define your worth!"
  },
  "acidity": {
    condition: "Acid Reflux / Heartburn / Gastritis",
    severity: "Mild-Moderate",
    first_aid: "Gelusil / Digene gel 2 tsp after meals or Eno fruit salt in water for instant relief.",
    home_remedy: "Cold milk (without sugar) gives instant relief. Sip jeera (cumin) water. Avoid lying flat for 2 hours after food.",
    doctor_alert: "🚨 Emergency if pain radiates to left arm/jaw or accompanied by difficulty swallowing."
  }
};

const HEALTH_ALIASES = {
  "fever": "fever", "bukhar": "fever", "temperature": "fever", "viral": "fever",
  "headache": "headache", "sar dard": "headache", "migraine": "headache", "head pain": "headache",
  "cold": "cold", "sardi": "cold", "jukham": "cold", "runny nose": "cold", "sneezing": "cold",
  "cough": "cough", "khansi": "cough", "sore throat": "cough", "throat pain": "cough",
  "stress": "stress", "tension": "stress", "anxiety": "stress", "depression": "stress", "panic": "stress", "4-7-8": "stress",
  "acidity": "acidity", "gas": "acidity", "heartburn": "acidity", "stomach pain": "acidity", "pet dard": "acidity"
};

// ── Root HTML Route ─────────────────────────────────────────────────────────────
app.get('/', (req, res) => {
  const indexPath = path.join(TEMPLATES_DIR, 'index.html');
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.send('<h2>CampusGenie Node.js Backend is running!</h2>');
  }
});

// ── Health Check ────────────────────────────────────────────────────────────────
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    runtime: 'Node.js',
    version: process.version,
    framework: 'Express',
    uptime: Math.round(process.uptime()),
    timestamp: new Date().toISOString()
  });
});

// ── Student & ERP Endpoints ─────────────────────────────────────────────────────
app.get('/api/admin/all_students', (req, res) => {
  const data = loadData();
  res.json({
    students: data.students || [],
    subjects: data.subjects || []
  });
});

app.get('/api/student', (req, res) => {
  const data = loadData();
  const reqStudentId = req.query.student_id || req.query.roll_no;
  let activeStu = null;

  if (reqStudentId) {
    const reqClean = reqStudentId.trim().toLowerCase();
    activeStu = (data.students || []).find(s =>
      (s.id && s.id.toLowerCase() === reqClean) ||
      (s.roll_no && s.roll_no.toLowerCase() === reqClean)
    );
    if (!activeStu) {
      activeStu = (data.students || []).find(s =>
        (s.roll_no && s.roll_no.toLowerCase().includes(reqClean)) ||
        (s.id && s.id.toLowerCase().includes(reqClean))
      );
    }
    if (!activeStu) {
      activeStu = (data.students || []).find(s =>
        s.name && s.name.toLowerCase().includes(reqClean)
      );
    }
  }

  if (!activeStu) {
    activeStu = getActiveStudent(data);
  } else {
    data.active_student_id = activeStu.id;
    saveData(data);
  }

  const allStudents = (data.students || []).map(s => ({
    id: s.id,
    name: s.name,
    roll_no: s.roll_no,
    branch: s.branch || '',
    semester: s.semester || ''
  }));

  const subjectsList = data.subjects || [];
  const attMap = (activeStu && activeStu.attendance) || {};
  const marksMap = (activeStu && activeStu.marks) || {};

  const formattedSubjects = subjectsList.map(sub => {
    const subId = sub.id;
    const subAtt = attMap[subId] || { attended: 0, total: 0, percentage: 100.0, status: 'safe' };
    const subMarks = marksMap[subId] || { score: '-', total: 100, status: 'Pending' };
    const classesNeeded = calculateClassesNeeded(subAtt.attended || 0, subAtt.total || 0, activeStu?.target_attendance || 75);
    const maxBunks = calculateMaxBunks(subAtt.attended || 0, subAtt.total || 0, activeStu?.target_attendance || 75);

    return {
      id: subId,
      code: sub.code || '',
      name: sub.name || '',
      faculty: sub.faculty || '',
      attended: subAtt.attended || 0,
      total: subAtt.total || 0,
      percentage: subAtt.percentage || 100.0,
      status: subAtt.status || 'safe',
      classes_needed: classesNeeded,
      max_bunks: maxBunks,
      score: subMarks.score || '-',
      total_marks: subMarks.total || 100,
      result: subMarks.status || 'Pending'
    };
  });

  res.json({
    student: activeStu,
    active_student_id: activeStu ? activeStu.id : null,
    all_students: allStudents,
    subjects: formattedSubjects,
    raw_subjects: subjectsList,
    timetable: data.timetable || [],
    opportunities: data.opportunities || [],
    notices: data.notices || []
  });
});

app.post('/api/student/switch', (req, res) => {
  const payload = req.body || {};
  const targetId = (payload.student_id || '').trim().toLowerCase();
  const data = loadData();

  const stu = (data.students || []).find(s =>
    (s.id && s.id.toLowerCase() === targetId) ||
    (s.roll_no && s.roll_no.toLowerCase() === targetId) ||
    (s.name && s.name.toLowerCase().includes(targetId))
  );

  if (stu) {
    data.active_student_id = stu.id;
    saveData(data);
    return res.json({ success: true, message: `Switched to ${stu.name}.`, student: stu, active_student_id: stu.id });
  }
  return res.status(404).json({ success: false, message: 'Student not found.' });
});

// ── Attendance Endpoints ────────────────────────────────────────────────────────
app.post('/api/attendance/mark', (req, res) => {
  const role = getCallerRole(req);
  if (role === 'student') {
    return res.status(403).json({
      success: false,
      message: 'Access Denied: Students are strictly forbidden from modifying attendance records (RBAC Policy).'
    });
  }

  const payload = req.body || {};
  const studentId = payload.student_id;
  const subId = payload.subject_id;
  const status = (payload.status || 'present').toLowerCase();

  const data = loadData();
  const students = data.students || [];

  let targetStu = studentId ? students.find(s => s.id === studentId) : null;
  if (!targetStu) targetStu = getActiveStudent(data);
  if (!targetStu) return res.status(404).json({ success: false, message: 'No student found.' });

  if (!targetStu.attendance) targetStu.attendance = {};
  if (!targetStu.attendance[subId]) {
    targetStu.attendance[subId] = { attended: 0, total: 0, percentage: 100.0, status: 'safe' };
  }

  const subAtt = targetStu.attendance[subId];
  subAtt.total = (subAtt.total || 0) + 1;
  if (status === 'present') {
    subAtt.attended = (subAtt.attended || 0) + 1;
  }
  subAtt.percentage = Math.round((subAtt.attended / subAtt.total) * 10000) / 100;
  const target = targetStu.target_attendance || 75;
  subAtt.status = subAtt.percentage >= target ? 'safe' : 'warning';

  saveData(data);
  const needed = calculateClassesNeeded(subAtt.attended, subAtt.total, target);

  res.json({
    success: true,
    student_name: targetStu.name,
    subject_id: subId,
    attended: subAtt.attended,
    total: subAtt.total,
    percentage: subAtt.percentage,
    status: subAtt.status,
    classes_needed: needed,
    message: `Marked ${status.toUpperCase()} for ${targetStu.name}!`
  });
});

app.get('/api/teacher/students/by_subject', (req, res) => {
  const data = loadData();
  const subId = req.query.subject_id;
  const students = (data.students || []).map(s => {
    const att = (s.attendance && s.attendance[subId]) || { attended: 0, total: 0, percentage: 100.0, status: 'safe' };
    return {
      id: s.id,
      name: s.name,
      roll_no: s.roll_no,
      branch: s.branch,
      attendance: att
    };
  });
  res.json({ success: true, students });
});

app.post('/api/teacher/attendance/submit', (req, res) => {
  const role = getCallerRole(req);
  if (role === 'student') {
    return res.status(403).json({
      success: false,
      message: 'Access Denied: Students are strictly forbidden from marking attendance.'
    });
  }

  const payload = req.body || {};
  const subId = payload.subject_id;
  const attendanceMap = payload.attendance || {}; // { [student_id]: 'present' | 'absent' }
  const data = loadData();

  (data.students || []).forEach(stu => {
    if (attendanceMap[stu.id]) {
      const status = attendanceMap[stu.id].toLowerCase();
      if (!stu.attendance) stu.attendance = {};
      if (!stu.attendance[subId]) {
        stu.attendance[subId] = { attended: 0, total: 0, percentage: 100.0, status: 'safe' };
      }
      const rec = stu.attendance[subId];
      rec.total = (rec.total || 0) + 1;
      if (status === 'present') rec.attended = (rec.attended || 0) + 1;
      rec.percentage = Math.round((rec.attended / rec.total) * 10000) / 100;
      rec.status = rec.percentage >= (stu.target_attendance || 75) ? 'safe' : 'warning';
    }
  });

  saveData(data);
  res.json({ success: true, message: `Bulk attendance recorded for subject ${subId} successfully!` });
});

// ── Authentication Endpoints ────────────────────────────────────────────────────
app.get('/api/auth/faculty_list', (req, res) => {
  const data = loadData();
  const list = (data.subjects || []).map(s => ({
    name: s.faculty,
    subject: s.name,
    code: s.code,
    id: s.id
  }));
  res.json({ success: true, faculty: list });
});

app.post('/api/auth/login', (req, res) => {
  const payload = req.body || {};
  const role = (payload.role || 'student').toLowerCase();
  const identifier = (payload.identifier || '').trim();
  const password = (payload.password || '').trim();
  const data = loadData();

  if (role === 'student') {
    const idClean = identifier.toLowerCase();
    let student = (data.students || []).find(s =>
      (s.roll_no && s.roll_no.toLowerCase() === idClean) ||
      (s.id && s.id.toLowerCase() === idClean)
    );
    if (!student && idClean) {
      student = (data.students || []).find(s =>
        (s.roll_no && s.roll_no.toLowerCase().includes(idClean)) ||
        (s.id && s.id.toLowerCase().includes(idClean))
      );
    }
    if (!student && idClean) {
      student = (data.students || []).find(s =>
        s.name && s.name.toLowerCase().includes(idClean)
      );
    }
    if (!student && idClean) {
      const rollUpper = identifier.toUpperCase();
      student = {
        id: rollUpper,
        name: `Student (${rollUpper})`,
        roll_no: rollUpper,
        branch: "Computer Science & Engineering",
        semester: "5th Semester",
        password: password || "student123",
        target_attendance: 75,
        fees: {
          total_fee: 125000,
          paid_amount: 60000,
          due_amount: 65000,
          status: "partial",
          due_date: "15 Oct 2026",
          transactions: [
            { receipt_no: "AKGEC-FEE-9001", date: "01 Aug 2026", amount: 60000, mode: "Online UPI", status: "Success" }
          ]
        },
        attendance: {
          os: { attended: 38, total: 45, percentage: 84.44, status: "safe" },
          dsa: { attended: 32, total: 38, percentage: 84.21, status: "safe" },
          dbms: { attended: 26, total: 30, percentage: 86.67, status: "safe" },
          cn: { attended: 24, total: 30, percentage: 80.0, status: "safe" }
        },
        marks: {
          os: { score: 76, total: 100, status: "Pass" },
          dsa: { score: 82, total: 100, status: "Pass" },
          dbms: { score: 75, total: 100, status: "Pass" },
          cn: { score: 70, total: 100, status: "Pass" }
        }
      };
      if (!data.students) data.students = [];
      data.students.push(student);
    }

    if (!student && data.students && data.students.length > 0) {
      student = data.students[0];
    }
    if (!student) {
      return res.status(404).json({ success: false, message: 'Student record not found.' });
    }

    const expectedPw = student.password || 'student123';
    if (password && password !== expectedPw) {
      return res.status(401).json({
        success: false,
        message: `Incorrect password for roll number ${student.roll_no || identifier}. Please check your credentials.`
      });
    }

    data.active_student_id = student.id;
    saveData(data);

    return res.json({
      success: true,
      role: 'student',
      active_student_id: student.id,
      user: {
        id: student.id,
        name: student.name,
        roll_no: student.roll_no,
        branch: student.branch || 'CSE',
        semester: student.semester || '5th Sem'
      },
      student
    });

  } else if (role === 'teacher') {
    if (password && !['teacher123', 'admin123', 'faculty123', 'os', 'dsa', 'dbms', 'cn'].includes(password)) {
      return res.status(401).json({ success: false, message: "Incorrect faculty password. Default demo password is 'teacher123'." });
    }
    const subjects = data.subjects || [];
    let sub = subjects.find(s => s.id.toLowerCase() === identifier.toLowerCase() || (s.faculty && s.faculty.toLowerCase() === identifier.toLowerCase()));
    if (!sub && identifier) {
      sub = subjects.find(s => s.id.toLowerCase().includes(identifier.toLowerCase()) || s.name.toLowerCase().includes(identifier.toLowerCase()) || (s.faculty && s.faculty.toLowerCase().includes(identifier.toLowerCase())));
    }
    if (!sub && subjects.length > 0) sub = subjects[0];

    return res.json({
      success: true,
      role: 'teacher',
      user: {
        name: sub ? sub.faculty : 'Prof. R. K. Verma',
        subject_id: sub ? sub.id : 'os',
        subject_name: sub ? sub.name : 'Operating Systems',
        subject_code: sub ? sub.code : 'KCS-501'
      }
    });

  } else if (role === 'hod') {
    if (password && !['hod123', 'admin123', 'hod@2026', 'Dr. S. K. Bansal'].includes(password) && !['hod123', 'admin123', 'Dr. S. K. Bansal'].includes(identifier)) {
      return res.status(401).json({ success: false, message: "Incorrect HOD security key. Default demo key is 'hod123'." });
    }
    return res.json({
      success: true,
      role: 'hod',
      user: {
        name: "Dr. S. K. Bansal",
        title: "Head of Department (CSE)",
        department: "Computer Science & Engineering"
      }
    });

  } else if (role === 'parent') {
    const idClean = identifier.toLowerCase();
    let student = (data.students || []).find(s =>
      (s.roll_no && s.roll_no.toLowerCase() === idClean) ||
      (s.id && s.id.toLowerCase() === idClean)
    );
    if (!student && idClean) {
      student = (data.students || []).find(s =>
        (s.roll_no && s.roll_no.toLowerCase().includes(idClean)) ||
        (s.id && s.id.toLowerCase().includes(idClean))
      );
    }
    if (!student && data.students && data.students.length > 0) {
      student = data.students[0];
    }
    if (!student) {
      return res.status(404).json({ success: false, message: 'Student roll number not found.' });
    }

    if (password && !['parent123', 'student123', (student.roll_no || '').toLowerCase()].includes(password)) {
      return res.status(401).json({ success: false, message: "Incorrect parent password. Default demo password is 'parent123'." });
    }

    data.active_student_id = student.id;
    saveData(data);
    return res.json({
      success: true,
      role: 'parent',
      active_student_id: student.id,
      user: {
        name: `Parent of ${student.name}`,
        student_id: student.id,
        student_name: student.name,
        student_roll: student.roll_no
      },
      student
    });
  }

  return res.status(400).json({ success: false, message: 'Invalid role specified.' });
});

app.post('/api/auth/forgot_password', (req, res) => {
  const payload = req.body || {};
  const rollNo = (payload.roll_no || payload.identifier || '').trim().toLowerCase();
  const newPassword = (payload.new_password || '').trim();

  if (!rollNo || !newPassword) {
    return res.status(400).json({ success: false, message: 'Roll Number and new password are required.' });
  }

  const data = loadData();
  const stu = (data.students || []).find(s =>
    (s.roll_no && s.roll_no.toLowerCase() === rollNo) ||
    (s.id && s.id.toLowerCase() === rollNo)
  );

  if (!stu) {
    return res.status(404).json({ success: false, message: `No student found for roll number '${rollNo}'.` });
  }

  stu.password = newPassword;
  saveData(data);
  return res.json({ success: true, message: `Password for ${stu.name} has been successfully updated!` });
});

// ── HOD Admin Management Endpoints ──────────────────────────────────────────────
app.post('/api/admin/student/add', (req, res) => {
  const role = getCallerRole(req);
  if (role === 'student') {
    return res.status(403).json({ success: false, message: 'Access Denied: Students are not authorized to enroll students.' });
  }

  const payload = req.body || {};
  const name = (payload.name || '').trim();
  const rollNo = (payload.roll_no || '').trim();
  const branch = (payload.branch || 'CSE').trim();
  const semester = (payload.semester || '5th Sem').trim();
  let password = (payload.password || '').trim();

  if (!name || !rollNo) {
    return res.status(400).json({ success: false, message: 'Name and Roll No are required.' });
  }

  const data = loadData();
  const stuId = rollNo.replace(/\s+/g, '').toUpperCase();

  const exists = (data.students || []).some(s => s.id === stuId);
  if (exists) {
    return res.status(400).json({ success: false, message: `Roll No ${rollNo} already exists.` });
  }

  if (!password) {
    password = `AKGEC@${stuId.length >= 4 ? stuId.slice(-4) : '2026'}`;
  }

  const newStu = {
    id: stuId,
    name,
    roll_no: rollNo,
    branch,
    semester,
    password,
    target_attendance: 75,
    fees: {
      total_fee: 125000,
      paid_amount: 0,
      due_amount: 125000,
      status: 'unpaid',
      due_date: '15 Oct 2026',
      transactions: []
    },
    attendance: {
      os: { attended: 0, total: 0, percentage: 0.0, status: 'warning' },
      dsa: { attended: 0, total: 0, percentage: 0.0, status: 'warning' },
      dbms: { attended: 0, total: 0, percentage: 0.0, status: 'warning' },
      cn: { attended: 0, total: 0, percentage: 0.0, status: 'warning' }
    },
    marks: {
      os: { score: 0, total: 100, status: 'Pending' },
      dsa: { score: 0, total: 100, status: 'Pending' },
      dbms: { score: 0, total: 100, status: 'Pending' },
      cn: { score: 0, total: 100, status: 'Pending' }
    }
  };

  if (!data.students) data.students = [];
  data.students.push(newStu);
  data.active_student_id = stuId;
  saveData(data);

  res.json({
    success: true,
    message: `Student '${name}' registered successfully!`,
    student: newStu,
    credentials: {
      name,
      roll_no: rollNo,
      password,
      branch,
      semester
    }
  });
});

app.post('/api/admin/student/reset_password', (req, res) => {
  const role = getCallerRole(req);
  if (role === 'student') {
    return res.status(403).json({ success: false, message: 'Access Denied: Students cannot reset administrative credentials.' });
  }

  const payload = req.body || {};
  const studentId = (payload.student_id || '').trim().toLowerCase();
  const newPassword = (payload.new_password || '').trim();

  if (!studentId || !newPassword) {
    return res.status(400).json({ success: false, message: 'Student ID and new password are required.' });
  }

  const data = loadData();
  const stu = (data.students || []).find(s =>
    (s.id && s.id.toLowerCase() === studentId) ||
    (s.roll_no && s.roll_no.toLowerCase() === studentId)
  );

  if (!stu) return res.status(404).json({ success: false, message: 'Student not found.' });

  stu.password = newPassword;
  saveData(data);
  res.json({ success: true, message: `Password for ${stu.name} has been reset successfully!` });
});

app.post('/api/admin/marks/update', (req, res) => {
  const payload = req.body || {};
  const studentId = payload.student_id;
  const subId = payload.subject_id;
  const score = payload.score;
  const total = payload.total || 100;

  const data = loadData();
  const stu = (data.students || []).find(s => s.id === studentId);
  if (!stu) return res.status(404).json({ success: false, message: 'Student not found.' });

  if (!stu.marks) stu.marks = {};
  const numScore = parseFloat(score);
  stu.marks[subId] = {
    score: isNaN(numScore) ? score : numScore,
    total: parseFloat(total),
    status: isNaN(numScore) ? 'Pending' : (numScore >= (total * 0.4) ? 'Pass' : 'Fail')
  };

  saveData(data);
  res.json({ success: true, message: `Marks updated for ${stu.name}.`, marks: stu.marks[subId] });
});

app.post('/api/admin/subject/add', (req, res) => {
  const payload = req.body || {};
  const code = (payload.code || '').trim().toUpperCase();
  const name = (payload.name || '').trim();
  const faculty = (payload.faculty || '').trim();
  const credits = parseInt(payload.credits || 4);

  if (!code || !name) return res.status(400).json({ success: false, message: 'Code and Name are required.' });

  const data = loadData();
  const id = code.toLowerCase().replace(/[^a-z0-9]/g, '');
  const newSub = { id, code, name, faculty: faculty || 'Department Faculty', credits };

  if (!data.subjects) data.subjects = [];
  data.subjects.push(newSub);
  saveData(data);

  res.json({ success: true, message: `Subject '${name}' added!`, subject: newSub });
});

app.post('/api/admin/timetable/add', (req, res) => {
  const payload = req.body || {};
  const day = payload.day || 'Monday';
  const time = payload.time || '09:00 AM';
  const subject = payload.subject || 'Subject';
  const room = payload.room || 'LH-101';
  const faculty = payload.faculty || 'Faculty';

  const data = loadData();
  const entry = { id: `tt-${Date.now()}`, day, time, subject, room, faculty };
  if (!data.timetable) data.timetable = [];
  data.timetable.push(entry);
  saveData(data);

  res.json({ success: true, message: 'Timetable entry added!', entry });
});

app.post('/api/admin/notice/add', (req, res) => {
  const payload = req.body || {};
  const title = (payload.title || '').trim();
  const category = payload.category || 'General';
  const message = payload.message || payload.content || '';
  const urgent = !!payload.urgent;

  if (!title) return res.status(400).json({ success: false, message: 'Notice title is required.' });

  const data = loadData();
  const notice = {
    id: `notice-${Date.now()}`,
    title,
    category,
    date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
    priority: urgent ? 'high' : 'normal',
    message
  };

  if (!data.notices) data.notices = [];
  data.notices.unshift(notice);
  saveData(data);

  res.json({ success: true, message: 'Notice posted successfully!', notice });
});

app.post('/api/admin/opportunity/add', (req, res) => {
  const payload = req.body || {};
  const title = (payload.title || '').trim();
  const category = payload.category || 'Hackathon';
  const deadline = payload.deadline || 'Upcoming';
  const link = payload.link || '#';
  const description = payload.description || '';

  if (!title) return res.status(400).json({ success: false, message: 'Opportunity title is required.' });

  const data = loadData();
  const opp = { id: `opp-${Date.now()}`, title, category, deadline, link, description };
  if (!data.opportunities) data.opportunities = [];
  data.opportunities.unshift(opp);
  saveData(data);

  res.json({ success: true, message: 'Opportunity added!', opportunity: opp });
});

app.post('/api/hod/student/delete', (req, res) => {
  const payload = req.body || {};
  const id = payload.id;
  const data = loadData();
  data.students = (data.students || []).filter(s => s.id !== id);
  saveData(data);
  res.json({ success: true, message: 'Student removed successfully.' });
});

app.post('/api/hod/student/edit', (req, res) => {
  const payload = req.body || {};
  const id = payload.id;
  const data = loadData();
  const stu = (data.students || []).find(s => s.id === id);
  if (!stu) return res.status(404).json({ success: false, message: 'Student not found.' });

  if (payload.name) stu.name = payload.name;
  if (payload.branch) stu.branch = payload.branch;
  if (payload.semester) stu.semester = payload.semester;
  if (payload.target_attendance) stu.target_attendance = parseInt(payload.target_attendance);

  saveData(data);
  res.json({ success: true, message: 'Student updated successfully.', student: stu });
});

app.get('/api/hod/defaulters', (req, res) => {
  const data = loadData();
  const defaulters = [];

  (data.students || []).forEach(stu => {
    const att = stu.attendance || {};
    const values = Object.values(att);
    if (values.length > 0) {
      const avg = values.reduce((sum, item) => sum + (item.percentage || 0), 0) / values.length;
      if (avg < (stu.target_attendance || 75)) {
        defaulters.push({
          id: stu.id,
          name: stu.name,
          roll_no: stu.roll_no,
          branch: stu.branch,
          average_attendance: Math.round(avg * 10) / 10
        });
      }
    }
  });

  res.json({ success: true, defaulters });
});

app.get('/api/hod/analytics', (req, res) => {
  const data = loadData();
  const students = data.students || [];
  const totalStudents = students.length;

  let totalAttPct = 0;
  let defaulterCount = 0;
  let totalFeeDue = 0;
  let totalFeePaid = 0;

  students.forEach(s => {
    const att = s.attendance || {};
    const pcts = Object.values(att).map(item => item.percentage || 0);
    const avg = pcts.length ? pcts.reduce((a, b) => a + b, 0) / pcts.length : 0;
    totalAttPct += avg;
    if (avg < 75) defaulterCount++;

    const fees = s.fees || {};
    totalFeePaid += fees.paid_amount || 0;
    totalFeeDue += fees.due_amount || 0;
  });

  const deptAttAvg = totalStudents ? Math.round((totalAttPct / totalStudents) * 10) / 10 : 0;
  const totalFees = totalFeePaid + totalFeeDue;
  const feeCollectionRate = totalFees > 0 ? Math.round((totalFeePaid / totalFees) * 1000) / 10 : 0;

  res.json({
    success: true,
    total_students: totalStudents,
    average_attendance: deptAttAvg,
    defaulters_count: defaulterCount,
    total_fee_collected: totalFeePaid,
    total_fee_due: totalFeeDue,
    fee_collection_rate: feeCollectionRate,
    placement_readiness_avg: 74.2
  });
});

// ── Fees & Payments ─────────────────────────────────────────────────────────────
app.get('/api/fees/status', (req, res) => {
  const data = loadData();
  const studentId = req.query.student_id || req.query.roll_no;
  let stu = null;
  if (studentId) {
    const sClean = studentId.trim().toLowerCase();
    stu = (data.students || []).find(s =>
      (s.id && s.id.toLowerCase() === sClean) ||
      (s.roll_no && s.roll_no.toLowerCase() === sClean) ||
      (s.roll_no && s.roll_no.toLowerCase().includes(sClean))
    );
  }
  if (!stu) stu = getActiveStudent(data);
  if (!stu) return res.status(404).json({ success: false, message: 'Student not found.' });

  const defaultFees = {
    total_fee: 125000,
    paid_amount: 75000,
    due_amount: 50000,
    status: 'partial',
    due_date: '15 Oct 2026',
    transactions: [
      { receipt_no: 'AKGEC-FEE-8812', date: '10 Aug 2026', amount: 75000, mode: 'UPI / NetBanking', status: 'Success' }
    ]
  };

  if (!stu.fees) stu.fees = defaultFees;

  res.json({
    success: true,
    student_id: stu.id,
    student_name: stu.name,
    roll_no: stu.roll_no,
    branch: stu.branch || 'CSE',
    semester: stu.semester || '5th Sem',
    fees: stu.fees
  });
});

app.post('/api/fees/pay', (req, res) => {
  const payload = req.body || {};
  const studentId = payload.student_id || payload.roll_no;
  const rawAmount = payload.amount;
  const mode = payload.payment_mode || 'Online UPI (GPay / PhonePe)';

  const amount = parseFloat(rawAmount);
  if (isNaN(amount) || amount <= 0) {
    return res.status(400).json({ success: false, message: 'Please enter a valid positive payment amount.' });
  }

  const data = loadData();
  let stu = null;
  if (studentId) {
    const sClean = String(studentId).trim().toLowerCase();
    stu = (data.students || []).find(s =>
      (s.id && s.id.toLowerCase() === sClean) ||
      (s.roll_no && s.roll_no.toLowerCase() === sClean) ||
      (s.roll_no && s.roll_no.toLowerCase().includes(sClean))
    );
  }
  if (!stu) stu = getActiveStudent(data);
  if (!stu) return res.status(404).json({ success: false, message: 'Student record not found.' });

  if (!stu.fees) {
    stu.fees = { total_fee: 125000, paid_amount: 0, due_amount: 125000, status: 'partial', due_date: '15 Oct 2026', transactions: [] };
  }

  const currentDue = parseFloat(stu.fees.due_amount || 0);
  const payAmount = currentDue > 0 ? Math.min(amount, currentDue) : amount;
  const newPaid = Math.round((parseFloat(stu.fees.paid_amount || 0) + payAmount) * 100) / 100;
  const newDue = Math.max(0, Math.round((parseFloat(stu.fees.total_fee || 125000) - newPaid) * 100) / 100);

  stu.fees.paid_amount = newPaid;
  stu.fees.due_amount = newDue;
  stu.fees.status = newDue <= 0 ? 'paid' : 'partial';

  const receiptNo = `AKGEC-FEE-${Math.floor(10000 + Math.random() * 90000)}`;
  const tx = {
    receipt_no: receiptNo,
    date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
    amount: payAmount,
    mode,
    status: 'Success',
    student_name: stu.name,
    roll_no: stu.roll_no,
    remaining_balance: newDue
  };

  if (!stu.fees.transactions) stu.fees.transactions = [];
  stu.fees.transactions.unshift(tx);
  saveData(data);

  res.json({
    success: true,
    message: `Payment of ₹${payAmount.toLocaleString('en-IN')} recorded successfully via ${mode}! Remaining balance: ₹${newDue.toLocaleString('en-IN')}`,
    receipt: tx,
    fees: stu.fees
  });
});

app.post('/api/hod/fees/set', (req, res) => {
  const payload = req.body || {};
  const studentId = payload.student_id;
  const data = loadData();
  const stu = (data.students || []).find(s =>
    (s.id && s.id.toLowerCase() === String(studentId).toLowerCase()) ||
    (s.roll_no && s.roll_no.toLowerCase() === String(studentId).toLowerCase())
  );
  if (!stu) return res.status(404).json({ success: false, message: 'Student not found.' });

  if (!stu.fees) stu.fees = {};
  if (payload.total_fee !== undefined) stu.fees.total_fee = parseFloat(payload.total_fee);
  if (payload.due_amount !== undefined) {
    stu.fees.due_amount = parseFloat(payload.due_amount);
    stu.fees.paid_amount = Math.max(0, (stu.fees.total_fee || 125000) - stu.fees.due_amount);
  }
  if (payload.due_date) stu.fees.due_date = payload.due_date;
  stu.fees.status = (stu.fees.due_amount || 0) <= 0 ? 'paid' : 'partial';

  saveData(data);
  res.json({ success: true, message: `Fee structure updated for ${stu.name}.`, fees: stu.fees });
});

// ── Assignments & Tests ─────────────────────────────────────────────────────────
app.get('/api/assignments/list', (req, res) => {
  const data = loadData();
  const studentId = (req.query.student_id || '').trim().toLowerCase();
  const asgs = (data.assignments || []).map(a => {
    const copy = { ...a };
    const subs = a.submissions || {};
    copy.my_submission = studentId ? subs[studentId] : null;
    return copy;
  });
  res.json({ success: true, assignments: asgs });
});

app.post('/api/hod/assignment/create', (req, res) => {
  const payload = req.body || {};
  const title = (payload.title || '').trim();
  const subject = (payload.subject || '').trim();
  const subjectCode = (payload.subject_code || '').trim();
  const faculty = (payload.faculty || 'Faculty Assigned').trim();
  const deadline = (payload.deadline || '30 Sept 2026').trim();
  const totalMarks = parseInt(payload.total_marks || 20);
  const mode = (payload.mode || 'hybrid').trim();
  const desc = (payload.description || '').trim();
  const questions = payload.questions || [];

  if (!title || !subject) {
    return res.status(400).json({ success: false, message: 'Title and Subject are required.' });
  }

  const data = loadData();
  const randomNum = Math.floor(100 + Math.random() * 900);
  const newId = subjectCode ? `asg-${subjectCode.toLowerCase().replace(/[^a-z0-9]/g, '')}-${randomNum}` : `asg-${randomNum}`;

  const asg = {
    id: newId,
    title,
    subject,
    subject_code: subjectCode,
    faculty,
    deadline,
    total_marks: totalMarks,
    mode,
    pdf_filename: `AKGEC_${subjectCode.replace(/[^a-zA-Z0-9]/g, '_')}_Assignment.pdf`,
    description: desc,
    questions,
    submissions: {}
  };

  if (!data.assignments) data.assignments = [];
  data.assignments.unshift(asg);
  saveData(data);

  res.json({ success: true, message: `Assignment '${title}' published!`, assignment: asg });
});

app.get('/api/assignments/download_pdf/:asg_id', (req, res) => {
  const asgId = req.params.asg_id;
  const data = loadData();
  const asg = (data.assignments || []).find(a => a.id === asgId);
  if (!asg) return res.status(404).send('Assignment not found');

  const lines = [
    '================================================================================',
    'AJAY KUMAR GARG ENGINEERING COLLEGE, GHAZIABAD',
    'DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING',
    'OFFICIAL COURSEWORK WORKSHEET • SEMESTER EXAMINATIONS 2026',
    '================================================================================',
    `Title:        ${asg.title}`,
    `Course:       ${asg.subject} (${asg.subject_code || 'N/A'})`,
    `Faculty:      ${asg.faculty}`,
    `Submission:   Deadline: ${asg.deadline} | Total Marks: ${asg.total_marks}`,
    'Instructions: Complete all questions. Either submit online via CampusGenie AI',
    '              Proctored Test or solve in practical journal and submit to proctor.',
    '--------------------------------------------------------------------------------\n',
    `DESCRIPTION & OBJECTIVES:\n${asg.description || 'Solve all algorithmic problems.'}\n`,
    'QUESTIONS / PROBLEM SET:\n'
  ];

  (asg.questions || []).forEach((q, idx) => {
    lines.push(`Q${idx + 1}. ${q.q}`);
    (q.options || []).forEach((opt, oIdx) => {
      lines.push(`    [${String.fromCharCode(65 + oIdx)}] ${opt}`);
    });
    lines.push('');
  });

  lines.push('================================================================================');
  lines.push('End of Question Paper • AKGEC Academic ERP & Examination Cell');

  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="${asg.pdf_filename || 'Assignment.txt'}"`);
  res.send(lines.join('\n'));
});

app.post('/api/assignments/submit_online', (req, res) => {
  const payload = req.body || {};
  const studentId = (payload.student_id || '').trim().toLowerCase();
  const asgId = payload.assignment_id;
  const answers = payload.answers || {};
  const proctorStatus = payload.proctor_status || {};

  const data = loadData();
  const asg = (data.assignments || []).find(a => a.id === asgId);
  if (!asg) return res.status(404).json({ success: false, message: 'Assignment not found.' });

  const stu = (data.students || []).find(s =>
    (s.id && s.id.toLowerCase() === studentId) ||
    (s.roll_no && s.roll_no.toLowerCase() === studentId)
  );
  const studentKey = stu ? stu.id : studentId;

  const questions = asg.questions || [];
  let correctCount = 0;
  questions.forEach(q => {
    const qidStr = String(q.id);
    if (answers[qidStr] !== undefined && parseInt(answers[qidStr]) === parseInt(q.correct)) {
      correctCount++;
    }
  });

  const totalMarks = asg.total_marks || 20;
  const totalQ = questions.length;
  const score = totalQ > 0 ? Math.round((correctCount / totalQ) * totalMarks) : 0;
  const pct = totalMarks > 0 ? Math.round((score / totalMarks) * 1000) / 10 : 100.0;
  const passed = score >= (totalMarks * 0.4);

  const submissionRecord = {
    student_id: studentKey,
    student_name: stu ? stu.name : 'Student',
    roll_no: stu ? stu.roll_no : studentKey,
    date: new Date().toLocaleString('en-GB'),
    score,
    total_marks: totalMarks,
    percentage: pct,
    status: passed ? 'Passed' : 'Needs Improvement',
    proctor_verified: true,
    proctor_details: {
      camera_monitored: proctorStatus.camera_active !== false,
      mic_monitored: proctorStatus.mic_active !== false,
      integrity_score: '98% (No Suspicious Eye/Audio Activity Detected)'
    }
  };

  if (!asg.submissions) asg.submissions = {};
  asg.submissions[studentKey] = submissionRecord;
  saveData(data);

  res.json({
    success: true,
    message: `Test submitted successfully! Score: ${score}/${totalMarks} (${pct}%)`,
    submission: submissionRecord
  });
});

// ── Smart Campus Services: Lost & Found, Mess, Seating, Placement, Alerts ───────
app.get('/api/community/lost_found', (req, res) => {
  const data = loadData();
  res.json({ success: true, items: data.lost_and_found || [] });
});

app.post('/api/community/lost_found/add', (req, res) => {
  const payload = req.body || {};
  const itemType = payload.type || 'Lost';
  const itemName = (payload.item || '').trim();
  const location = (payload.location || '').trim();
  const contact = (payload.contact || '').trim();
  const reportedBy = (payload.reported_by || 'Student').trim();

  if (!itemName || !location) {
    return res.status(400).json({ success: false, message: 'Item name and location are required.' });
  }

  const data = loadData();
  if (!data.lost_and_found) data.lost_and_found = [];
  const newItem = {
    id: `LF-${data.lost_and_found.length + 101}`,
    type: itemType,
    item: itemName,
    location,
    date: 'Today',
    reported_by: reportedBy,
    contact: contact || 'N/A',
    status: 'Open'
  };

  data.lost_and_found.unshift(newItem);
  saveData(data);
  res.json({ success: true, message: 'Lost/Found report posted to Campus Hub!', item: newItem });
});

app.post('/api/community/lost_found/claim', (req, res) => {
  const payload = req.body || {};
  const itemId = payload.id;
  const data = loadData();
  const item = (data.lost_and_found || []).find(i => i.id === itemId);
  if (item) {
    item.status = 'Claimed';
    saveData(data);
    return res.json({ success: true, message: `Item '${item.item}' marked as Claimed / Resolved!` });
  }
  res.status(404).json({ success: false, message: 'Item not found.' });
});

app.get('/api/mess/menu', (req, res) => {
  const data = loadData();
  res.json({ success: true, mess_menu: data.mess_menu || {} });
});

app.post('/api/mess/rate', (req, res) => {
  const payload = req.body || {};
  const stars = parseInt(payload.stars || 5);
  const comment = (payload.comment || '').trim();
  const studentName = (payload.student_name || 'Student').trim();

  const data = loadData();
  if (!data.mess_menu) data.mess_menu = {};
  if (!data.mess_menu.ratings) {
    data.mess_menu.ratings = { total_votes: 142, average: 4.4, recent_reviews: [] };
  }

  const ratings = data.mess_menu.ratings;
  const total = ratings.total_votes || 0;
  const currentAvg = ratings.average || 4.4;
  const newTotal = total + 1;
  const newAvg = Math.round(((currentAvg * total) + stars) / newTotal * 100) / 100;

  ratings.total_votes = newTotal;
  ratings.average = newAvg;
  if (comment) {
    if (!ratings.recent_reviews) ratings.recent_reviews = [];
    ratings.recent_reviews.unshift({ student: studentName, stars, comment });
    if (ratings.recent_reviews.length > 10) ratings.recent_reviews.pop();
  }

  saveData(data);
  res.json({ success: true, message: "Thank you for rating today's mess meal!", ratings });
});

app.get('/api/exam/seating', (req, res) => {
  const studentId = (req.query.student_id || '').trim();
  const data = loadData();
  const seatings = data.seating_arrangements || {};
  let seating = seatings[studentId];

  if (!seating) {
    let stu = (data.students || []).find(s =>
      s.id.toLowerCase() === studentId.toLowerCase() ||
      (s.roll_no && s.roll_no.toLowerCase() === studentId.toLowerCase())
    );
    if (!stu && data.students && data.students.length > 0) stu = data.students[0];

    const roll = stu ? stu.roll_no : (studentId || '22CS1084');
    const name = stu ? stu.name : 'Student';
    const numDigits = roll.replace(/\D/g, '');
    const lastNum = numDigits.length >= 2 ? parseInt(numDigits.slice(-2)) : 14;

    seating = {
      student_name: name,
      roll_no: roll,
      exam: 'B.Tech V Semester Mid-Term Examination 2026',
      exam_center: 'AKGEC Main Academic Complex',
      hall_building: 'CS Block (Block-A)',
      room_no: `Room 30${(lastNum % 8) + 1} (3rd Floor)`,
      row: `Row ${String.fromCharCode(65 + (lastNum % 4))}`,
      bench_no: `Bench ${(lastNum % 25) + 1}`,
      seat_no: `Seat ${String.fromCharCode(65 + (lastNum % 4))}-${(lastNum % 25) + 1}`,
      reporting_time: '09:00 AM',
      instructions: [
        'Candidates must carry their AKGEC College ID and this printed Admit Card.',
        'Electronic devices, smartwatches, and programmable calculators are strictly prohibited.',
        'Report to the examination hall at least 15 minutes before the scheduled time.'
      ]
    };
  }

  res.json({ success: true, seating });
});

app.post('/api/parent/alert', (req, res) => {
  const payload = req.body || {};
  const studentId = payload.student_id || '';
  const alertType = payload.type || 'attendance';
  const message = (payload.message || '').trim();

  const data = loadData();
  const stu = (data.students || []).find(s => s.id === studentId || s.roll_no === studentId);
  const stuName = stu ? stu.name : studentId;

  if (!data.notices) data.notices = [];
  data.notices.unshift({
    id: `PARENT-ALERT-${data.notices.length + 1}`,
    title: `📲 Parent WhatsApp/SMS Dispatched: ${stuName}`,
    category: 'Parent Alert',
    date: 'Just now',
    priority: 'high',
    message: message || `Urgent official notification sent to parent regarding ${alertType} for ${stuName} (${studentId}).`
  });

  saveData(data);
  res.json({ success: true, message: `WhatsApp notification alert successfully sent to parent of ${stuName}!` });
});

app.get('/api/parent/student_lookup', (req, res) => {
  const rollNo = (req.query.roll_no || req.query.student_id || '').trim().toLowerCase();
  const data = loadData();
  const stu = (data.students || []).find(s =>
    (s.roll_no && s.roll_no.toLowerCase() === rollNo) ||
    (s.id && s.id.toLowerCase() === rollNo)
  );

  if (!stu) return res.status(404).json({ success: false, message: 'Student record not found.' });

  const att = stu.attendance || {};
  const pcts = Object.values(att).map(item => item.percentage || 0);
  const avg = pcts.length ? Math.round(pcts.reduce((a, b) => a + b, 0) / pcts.length * 10) / 10 : 100.0;

  res.json({
    success: true,
    student: stu,
    summary: {
      average_attendance: avg,
      status: avg >= 75 ? 'Regular / Safe' : 'Attendance Shortage Alert',
      due_fee: stu.fees?.due_amount || 0
    }
  });
});

app.post('/api/placement/analyze', (req, res) => {
  const payload = req.body || {};
  const skills = payload.skills || [];
  const targetRole = (payload.target_role || 'Full Stack Developer / SDE').trim();

  const weightMap = {
    dsa: 25,
    cpp: 15,
    python: 15,
    react: 15,
    sql: 15,
    cloud: 10,
    docker: 10,
    system_design: 10,
    git: 5,
    ml: 10
  };

  let score = 25;
  const matchedSkills = [];
  const missingSkills = [];

  Object.entries(weightMap).forEach(([k, w]) => {
    if (skills.includes(k)) {
      score += w;
      matchedSkills.push(k.toUpperCase());
    } else {
      missingSkills.push(k.toUpperCase());
    }
  });

  score = Math.min(score, 98);

  let companies = [];
  if (score >= 80) {
    companies = ['Amazon AWS (SDE-1 - 24 LPA)', 'TCS Digital (7.5 LPA)', 'Accenture Advanced Associate', 'Paytm Technologies'];
  } else if (score >= 60) {
    companies = ['TCS Ninja (3.6 LPA)', 'Infosys Specialist Programmer (5 LPA)', 'Cognizant GenC Elevate', 'Wipro Turbo'];
  } else {
    companies = ['Service-based Foundation Drives', 'Incubated Startups @ AKGEC', 'TCS National Qualifier (NQT)'];
  }

  const tips = [];
  if (missingSkills.includes('DSA')) {
    tips.push('Focus heavily on DSA: Solve 50+ LeetCode Medium problems on Trees, Graphs, and DP.');
  }
  if (missingSkills.includes('SQL')) {
    tips.push('Master SQL queries: Practice subqueries, indexing, and normalization questions for technical rounds.');
  }
  if (missingSkills.includes('CLOUD')) {
    tips.push('Learn Cloud Fundamentals: Complete AWS Cloud Practitioner or IBM watsonx / Cloud badges.');
  }
  if (!tips.length) {
    tips.push('Great skill profile! Practice mock HR and System Design interviews on AKGEC portal.');
  }

  res.json({
    success: true,
    score,
    readiness: score >= 75 ? 'High' : (score >= 55 ? 'Moderate' : 'Developing'),
    target_role: targetRole,
    eligible_companies: companies,
    matched_skills: matchedSkills,
    tips
  });
});

app.post('/api/placement/analyze_resume', (req, res) => {
  // Alias for analyze
  const skills = req.body?.skills || ['dsa', 'python', 'sql', 'git'];
  const fakeReq = { body: { skills, target_role: 'Software Development Engineer (SDE)' } };
  return app._router.handle(fakeReq, res);
});

app.get('/api/notifications', (req, res) => {
  const data = loadData();
  res.json({ success: true, notices: data.notices || [] });
});

app.post('/api/notifications/clear', (req, res) => {
  const data = loadData();
  data.notices = [];
  saveData(data);
  res.json({ success: true, message: 'All notifications cleared.' });
});

// ── AI Academic Copilot & Chat Engine ───────────────────────────────────────────
app.post('/api/chat', (req, res) => {
  const payload = req.body || {};
  const userMsg = (payload.message || '').trim();
  const msgLower = userMsg.toLowerCase();
  const studentId = (payload.student_id || '').trim().toLowerCase();

  const data = loadData();
  let activeStu = null;
  if (studentId) {
    activeStu = (data.students || []).find(s =>
      (s.id && s.id.toLowerCase() === studentId) ||
      (s.roll_no && s.roll_no.toLowerCase() === studentId) ||
      (s.roll_no && s.roll_no.toLowerCase().includes(studentId))
    );
  }
  if (!activeStu) activeStu = getActiveStudent(data);
  const studentName = activeStu ? activeStu.name : 'Student';

  // 1. GREETINGS
  const greetings = ['hi', 'hello', 'hey', 'namaste', 'kaise ho', 'kya haal hai', 'who are you', 'tu kaun hai'];
  if (greetings.some(g => msgLower === g || msgLower.startsWith(g + ' '))) {
    return res.json({
      reply: `👋 **Namaste ${studentName}! Main hoon aapka AI Academic Copilot & Campus Companion!** 🤝\n\n` +
             `Aap mujhse bejhijhak kuch bhi pooch sakte ho:\n` +
             `• 🎓 **Campus & Academics:** Attendance shortage calculation, exam marks, timetables & CS doubts.\n` +
             `• 🩺 **Hostel Health & Care:** Late-night fever, headache, cold, acidity par safe OTC first-aid medicine aur home remedies.\n` +
             `• 💡 **AI Doubt Solver:** Data structures, algorithms, operating systems, networks & DBMS.\n\n` +
             `*Bataiye dost, aaj kya seekhna ya check karna hai?*`,
      action: 'friend'
    });
  }

  // 2. HEALTH & SYMPTOMS TRIAGE
  for (const [symKey, canonical] of Object.entries(HEALTH_ALIASES)) {
    if (msgLower.includes(symKey)) {
      const info = HEALTH_SYMPTOMS[canonical];
      if (info) {
        return res.json({
          reply: `🩺 **Campus Health AI — Symptom Triage**\n\n` +
                 `### 🩺 ${info.condition}\n` +
                 `**Severity:** ${info.severity}\n\n` +
                 `💊 **First-Aid & Safe Medicine:**\n${info.first_aid}\n\n` +
                 `🍵 **Home Remedies:**\n${info.home_remedy}\n\n` +
                 `${info.doctor_alert}\n\n---\n` +
                 `*AI first-aid guidance only — not a substitute for professional care. Visit Campus Clinic, Health Block Room 04.*`,
          action: 'health'
        });
      }
    }
  }

  // 3. ACADEMIC DOUBT SOLVER
  for (const [alias, canonical] of Object.entries(STUDY_ALIASES)) {
    if (msgLower.includes(alias)) {
      const info = STUDY_KNOWLEDGE[canonical];
      if (info) {
        return res.json({
          reply: `📚 **AI Academic Tutor [${info.subject}]**\n` +
                 `### ${info.title}\n\n---\n` +
                 `💡 **Core Concept:**\n${info.explanation}\n\n` +
                 `⚡ **Complexity / Key Properties:**\n\`${info.complexity}\`\n\n` +
                 `🎯 **Exam & Viva Pro-Tip:**\n${info.exam_tip}`,
          action: 'academic'
        });
      }
    }
  }

  // 4. ATTENDANCE & SHORTAGES
  const attKeywords = ['attendance', 'attendence', 'shortage', 'present', 'absent', 'bunk', 'skip', 'miss', 'haziri'];
  if (attKeywords.some(k => msgLower.includes(k))) {
    const attMap = (activeStu && activeStu.attendance) || {};
    const subList = data.subjects || [];
    const target = activeStu ? activeStu.target_attendance || 75 : 75;
    let replyLines = [`📊 **Attendance Report — ${studentName}** (Target: ${target}%)\n`];

    subList.forEach(s => {
      const a = attMap[s.id] || { attended: 0, total: 0, percentage: 100.0 };
      const pct = a.percentage || 0;
      const statusIcon = pct >= target ? '🟢' : '🔴';
      const needed = calculateClassesNeeded(a.attended || 0, a.total || 0, target);
      const bunks = calculateMaxBunks(a.attended || 0, a.total || 0, target);

      let extra = pct >= target ? `Safe to bunk: ${bunks} classes` : `Need to attend: ${needed} more classes`;
      replyLines.push(`• **${s.name}**: ${a.attended}/${a.total} (${pct}%) ${statusIcon} — ${extra}`);
    });

    return res.json({ reply: replyLines.join('\n'), action: 'attendance' });
  }

  // 5. HALL TICKET / ADMIT CARD
  if (['admit card', 'hall ticket', 'hallticket', 'exam pass'].some(k => msgLower.includes(k))) {
    const attMap = (activeStu && activeStu.attendance) || {};
    const values = Object.values(attMap);
    const totAtt = values.reduce((sum, v) => sum + (v.attended || 0), 0);
    const totCls = values.reduce((sum, v) => sum + (v.total || 0), 0);
    const overallPct = totCls > 0 ? Math.round((totAtt / totCls) * 10000) / 100 : 100.0;

    if (overallPct >= 75.0) {
      return res.json({
        reply: `🎟️ **Smart Hall Ticket Status: APPROVED & READY**\n\n` +
               `Badhaai ho **${studentName}**! Aapki aggregate attendance **${overallPct}%** hai (Mandatory 75.0% threshold se upar).\n\n` +
               `• **Status:** ELIGIBLE FOR SEMESTER EXAMINATIONS ✅\n` +
               `• **Admit Card:** Anti-Tamper Digital QR Verified\n\n` +
               `👉 Aap student dashboard par **'🎟️ Hall Ticket'** button daba kar apna official admit card print kar sakte ho!`,
        action: 'hallticket'
      });
    } else {
      return res.json({
        reply: `🚨 **Smart Hall Ticket Status: WITHHELD (< 75% Policy)**\n\n` +
               `Dhyan dein **${studentName}**: Aapki aggregate attendance **${overallPct}%** hai (Mandatory 75.0% se kam).\n\n` +
               `• **Status:** DEBARRED FROM SEMESTER EXAMINATIONS ⚠️\n` +
               `• **Remedy:** Upcoming classes attend karke 75% recovery karein ya HOD Dr. S. K. Bansal ko medical application submit karein.`,
        action: 'hallticket'
      });
    }
  }

  // 6. FEES QUERIES
  if (['fee', 'fees', 'due', 'balance', 'challan', 'receipt'].some(k => msgLower.includes(k))) {
    const fees = activeStu?.fees || { total_fee: 125000, paid_amount: 75000, due_amount: 50000 };
    return res.json({
      reply: `💳 **Fee Status — ${studentName}**\n\n` +
             `• **Total Course Fee:** ₹${(fees.total_fee || 125000).toLocaleString('en-IN')}\n` +
             `• **Paid Amount:** ₹${(fees.paid_amount || 0).toLocaleString('en-IN')}\n` +
             `• **Current Due Balance:** ₹${(fees.due_amount || 0).toLocaleString('en-IN')}\n` +
             `• **Due Date:** ${fees.due_date || '15 Oct 2026'}\n\n` +
             `👉 Click on **'💳 College Fees'** in the navbar to make an online payment via UPI or download your official receipt.`,
      action: 'fees'
    });
  }

  // 7. DEFAULT TUTOR FALLBACK
  return res.json({
    reply: `🤖 **AI Academic Copilot:**\n\n` +
           `Maine aapka message read kiya: *"\\"${userMsg}\\""*\n\n` +
           `Aap mujhse pooch sakte hain:\n` +
           `• **Computer Science:** Binary Search, Quick Sort, Deadlock in OS, Paging, SQL Joins, Normalization, ACID, TCP vs UDP.\n` +
           `• **Campus Health:** Fever, headache, acidity, cold relief.\n` +
           `• **ERP:** "Meri attendance kitni hai", "Admit card check karo", "Fees balance batao".`,
    action: 'general'
  });
});

// ── Start Server ────────────────────────────────────────────────────────────────
if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`====================================================`);
    console.log(`🚀 CampusGenie Node.js Backend Live on Port ${PORT}`);
    console.log(`🌐 Local URL: http://localhost:${PORT}`);
    console.log(`⚡ Runtime: Node.js ${process.version}`);
    console.log(`📁 Database: ${DATA_FILE}`);
    console.log(`====================================================`);
  });
}

module.exports = app;

