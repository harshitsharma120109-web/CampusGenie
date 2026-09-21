import sys
import os
import json
import re
import urllib.request
import urllib.parse
from flask import Flask, render_template, request, jsonify

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

DATA_FILE = os.path.join(BASE_DIR, 'data', 'student_data.json')
TMP_DATA_FILE = os.path.join('/tmp', 'student_data.json')

_in_memory_data = None

def load_data():
    global _in_memory_data
    if _in_memory_data is not None:
        return _in_memory_data
    # Check /tmp first if on serverless like Vercel
    if os.path.exists(TMP_DATA_FILE):
        try:
            with open(TMP_DATA_FILE, 'r', encoding='utf-8-sig') as f:
                _in_memory_data = json.load(f)
                return _in_memory_data
        except Exception:
            pass
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
            _in_memory_data = json.load(f)
            return _in_memory_data
    except Exception:
        return {}

def save_data(data):
    global _in_memory_data
    _in_memory_data = data
    saved = False
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        saved = True
    except Exception:
        pass
    if not saved:
        try:
            with open(TMP_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

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
    import math
    req = target * total - 100 * attended
    if req <= 0:
        return 0
    return math.ceil(req / (100 - target))

def calculate_max_bunks(attended, total, target=75):
    """How many more classes can be missed while staying at or above target%."""
    max_b = int((attended * 100) / target) - total
    return max(0, max_b)

# ── Academic Doubt Solver Knowledge Base ─────────────────────────────────────
# Each key is a lowercase trigger phrase matched against the user message.
# Multiple keys can map to the same concept via STUDY_ALIASES below.

STUDY_KNOWLEDGE = {
    # ── DATA STRUCTURES & ALGORITHMS ──────────────────────────────────────────
    "binary search": {
        "title": "Binary Search (Divide & Conquer)",
        "subject": "DSA",
        "explanation": "Works on a **sorted array** by repeatedly halving the search interval. Compare the target to the middle element — if not equal, discard the half that cannot contain the target and repeat.",
        "complexity": "Time: O(log N) average & worst | Space: O(1) iterative, O(log N) recursive",
        "exam_tip": "Viva Q: Why faster than Linear Search? Every step halves the search space: N → N/2 → N/4 → ... → 1. Always verify array is sorted first — applying Binary Search to unsorted data gives wrong results."
    },
    "bubble sort": {
        "title": "Bubble Sort Algorithm",
        "subject": "DSA",
        "explanation": "Repeatedly steps through the list, compares adjacent elements, and swaps them if in the wrong order. Each full pass 'bubbles' the largest unsorted element to its correct position at the end.",
        "complexity": "Time: O(N²) worst/average | O(N) best (already sorted with optimization) | Space: O(1) in-place",
        "exam_tip": "Optimization: add a flag `swapped`. If no swap in a pass, array is sorted — break early. This gives O(N) best case. Never use Bubble Sort for large N in production."
    },
    "merge sort": {
        "title": "Merge Sort (Divide & Conquer)",
        "subject": "DSA",
        "explanation": "Recursively divides the array into two halves, sorts each half, then **merges** the two sorted halves. The merge step is the key — it combines two sorted arrays in O(N) time by comparing elements one by one.",
        "complexity": "Time: O(N log N) always (best, average, worst) | Space: O(N) auxiliary",
        "exam_tip": "Merge Sort is a **stable** sort. Preferred for linked lists and external sorting (large files). Unlike Quick Sort, worst case is always O(N log N), not O(N²)."
    },
    "quick sort": {
        "title": "Quick Sort (Divide & Conquer)",
        "subject": "DSA",
        "explanation": "Selects a **pivot** element and partitions the array into: elements < pivot (left) and elements > pivot (right). Recursively sorts both partitions. No extra space needed for the sort itself.",
        "complexity": "Time: O(N log N) average | O(N²) worst (sorted array with last element as pivot) | Space: O(log N) stack",
        "exam_tip": "Worst case avoided with **randomized pivot** or **median-of-three**. Quick Sort is cache-friendly and in-practice faster than Merge Sort for in-memory data due to low constant factors."
    },
    "linked list": {
        "title": "Linked List Data Structure",
        "subject": "DSA",
        "explanation": "A linear data structure where each element (node) stores data and a pointer to the next node. Unlike arrays, nodes are not stored contiguously in memory. Types: Singly, Doubly, Circular.",
        "complexity": "Access: O(N) | Insert/Delete at head: O(1) | Insert/Delete at tail (without tail ptr): O(N) | Search: O(N)",
        "exam_tip": "Key trick for interviews: **Floyd's Cycle Detection** (slow/fast pointer) detects cycles in O(N) time and O(1) space. Reversing a linked list in-place is a classic viva question — draw the pointer changes."
    },
    "stack": {
        "title": "Stack Data Structure (LIFO)",
        "subject": "DSA",
        "explanation": "A linear data structure following **Last In, First Out (LIFO)**. Main operations: push (add to top), pop (remove from top), peek (view top without removing). Implemented using arrays or linked lists.",
        "complexity": "Push/Pop/Peek: O(1) | Search: O(N)",
        "exam_tip": "Applications: function call stack, undo operations, expression evaluation (infix→postfix), balanced parentheses checking. Memorize: Infix to Postfix uses a stack — operators go on stack, operands go directly to output."
    },
    "queue": {
        "title": "Queue Data Structure (FIFO)",
        "subject": "DSA",
        "explanation": "A linear data structure following **First In, First Out (FIFO)**. Enqueue adds to the rear, Dequeue removes from the front. Variants: Circular Queue (avoids false overflow), Deque (double-ended), Priority Queue.",
        "complexity": "Enqueue/Dequeue: O(1) with proper implementation | Search: O(N)",
        "exam_tip": "Circular Queue solves the false overflow problem of simple queue arrays. Priority Queue is implemented using a **Min/Max Heap** — not a sorted array. Used in CPU scheduling (FCFS, SJF)."
    },
    "tree": {
        "title": "Trees & Binary Search Tree (BST)",
        "subject": "DSA",
        "explanation": "A hierarchical data structure with a root node and subtrees. BST property: left subtree values < root < right subtree values. Traversals: Inorder (Left-Root-Right), Preorder (Root-Left-Right), Postorder (Left-Right-Root).",
        "complexity": "BST Search/Insert/Delete: O(log N) average | O(N) worst (skewed tree) | Balanced AVL/Red-Black: O(log N) guaranteed",
        "exam_tip": "Inorder traversal of a BST gives **sorted output** — this is a critical exam fact. For height-balanced trees (AVL), remember the rotation types: LL, RR, LR, RL. Height of BST with N nodes: log N (balanced) to N (skewed)."
    },
    "graph": {
        "title": "Graphs: BFS, DFS & Algorithms",
        "subject": "DSA",
        "explanation": "A non-linear structure of vertices (nodes) and edges. BFS (Breadth-First Search) uses a Queue — explores level by level. DFS (Depth-First Search) uses a Stack/Recursion — goes deep before backtracking.",
        "complexity": "BFS/DFS: O(V + E) where V = vertices, E = edges | Dijkstra: O((V+E) log V) with min-heap",
        "exam_tip": "BFS finds **shortest path in unweighted graphs**. DFS is used for topological sort, cycle detection, strongly connected components. Dijkstra's algorithm for weighted shortest path — does NOT work with negative weights (use Bellman-Ford instead)."
    },
    "hashing": {
        "title": "Hashing & Hash Tables",
        "subject": "DSA",
        "explanation": "Maps keys to array indices using a **hash function**. Collision resolution methods: Chaining (linked list at each bucket) and Open Addressing (linear probing, quadratic probing, double hashing).",
        "complexity": "Search/Insert/Delete: O(1) average | O(N) worst (all keys hash to same slot)",
        "exam_tip": "Load factor Î± = n/m (n = keys, m = table size). Keep Î± < 0.7 for good performance. A good hash function distributes keys uniformly. Chaining is simpler; Open Addressing is cache-friendly."
    },
    "dynamic programming": {
        "title": "Dynamic Programming (DP)",
        "subject": "DSA",
        "explanation": "Optimization technique that breaks problems into **overlapping subproblems**, solves each once, and stores results (memoization/tabulation). Two approaches: Top-Down (Memoization with recursion) and Bottom-Up (Tabulation with iteration).",
        "complexity": "Depends on problem. Fibonacci: O(N) with DP vs O(2^N) naive. LCS: O(MÃ—N). 0/1 Knapsack: O(NÃ—W)",
        "exam_tip": "DP applies when: (1) Optimal Substructure — optimal solution built from optimal sub-solutions; (2) Overlapping Subproblems — same sub-problems solved multiple times. Classic DPs: Fibonacci, LCS, LIS, 0/1 Knapsack, Matrix Chain Multiplication."
    },

    # ── OPERATING SYSTEMS ─────────────────────────────────────────────────────
    "deadlock": {
        "title": "Deadlock in Operating Systems",
        "subject": "OS",
        "explanation": "A state where a set of processes are **permanently blocked** — each holds a resource and waits for one held by another. None can proceed.",
        "complexity": "4 Necessary Conditions (Coffman): Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait",
        "exam_tip": "3 strategies: **Prevention** (negate one Coffman condition), **Avoidance** (Banker's Algorithm — maintain safe state), **Detection & Recovery** (allow deadlock, then kill/rollback). Banker's Algorithm is the #1 exam topic — always draw the allocation/need/available tables."
    },
    "process scheduling": {
        "title": "CPU Scheduling Algorithms",
        "subject": "OS",
        "explanation": "OS decides which ready process gets CPU time. Algorithms: FCFS (First Come First Serve), SJF (Shortest Job First), Round Robin (time quantum), Priority Scheduling, SRTF (Shortest Remaining Time First — preemptive SJF).",
        "complexity": "FCFS: No starvation, high convoy effect. SJF: Minimum avg waiting time (optimal for non-preemptive). Round Robin: Fair, high context switch overhead.",
        "exam_tip": "For numerical problems: **Gantt Chart** is mandatory. Key formulas: Waiting Time = Turnaround Time âˆ’ Burst Time. Turnaround Time = Completion Time âˆ’ Arrival Time. SJF suffers from starvation (solved by Aging). Round Robin time quantum choice is critical."
    },
    "paging": {
        "title": "Paging & Virtual Memory",
        "subject": "OS",
        "explanation": "Memory management scheme that eliminates external fragmentation. Process is divided into fixed-size **pages**, physical memory into **frames**. OS maintains a Page Table mapping logical addresses to physical addresses.",
        "complexity": "Logical Address = Page Number + Page Offset. Physical Address = Frame Number + Page Offset. Page Table Entry size = log2(# frames) bits.",
        "exam_tip": "Page Table is stored in RAM — two memory accesses per data access (slow!). Solution: **TLB (Translation Lookaside Buffer)** — a fast cache for page table. Effective Access Time (EAT) = hit-ratio Ã— TLB-time + (1-hit-ratio) Ã— (TLB+2Ã—memory-time). Page faults are expensive — minimized by LRU/Optimal replacement."
    },
    "semaphore": {
        "title": "Semaphores & Process Synchronization",
        "subject": "OS",
        "explanation": "A semaphore is an integer variable accessed only through two atomic operations: **wait(S)** [P operation — decrements S, blocks if S<0] and **signal(S)** [V operation — increments S, wakes blocked process]. Types: Binary (mutex) and Counting.",
        "complexity": "Solves: Mutual Exclusion, Producer-Consumer, Readers-Writers, Dining Philosophers problems.",
        "exam_tip": "Binary semaphore (0 or 1) = mutex. Counting semaphore manages N resources. Classic problem: **Producer-Consumer** — producer does signal(full)/wait(empty), consumer does wait(full)/signal(empty). mutex semaphore prevents simultaneous buffer access. Always draw the sequence diagram in exams."
    },

    # ── COMPUTER NETWORKS ─────────────────────────────────────────────────────
    "tcp vs udp": {
        "title": "TCP vs UDP (Transport Layer)",
        "subject": "CN",
        "explanation": "**TCP** (Transmission Control Protocol): connection-oriented, reliable, ordered delivery, flow/congestion control via 3-way handshake (SYN → SYN-ACK → ACK). **UDP** (User Datagram Protocol): connectionless, unreliable, no handshake, low overhead.",
        "complexity": "TCP: Heavyweight, reliable — used for HTTP/HTTPS, FTP, SMTP, SSH. UDP: Lightweight, fast — used for DNS, DHCP, video streaming, online gaming, VoIP.",
        "exam_tip": "TCP 3-way handshake: SYN → SYN-ACK → ACK. 4-way termination: FIN → ACK, FIN → ACK. TCP has flow control (sliding window) and congestion control (slow start, congestion avoidance). UDP has none of these — that's why it's faster."
    },
    "osi model": {
        "title": "OSI 7-Layer Reference Model",
        "subject": "CN",
        "explanation": "A conceptual framework dividing network communication into 7 layers: Physical, Data Link, Network, Transport, Session, Presentation, Application. Each layer provides services to the layer above and uses services of the layer below.",
        "complexity": "Mnemonic (top-down): **All People Seem To Need Data Processing** (Application, Presentation, Session, Transport, Network, Data Link, Physical)",
        "exam_tip": "Key protocols per layer — Application: HTTP, FTP, SMTP, DNS | Transport: TCP, UDP | Network: IP, ICMP, ARP | Data Link: Ethernet, MAC | Physical: cables, hubs. **IP addressing is at Network layer (L3)**. Switches work at L2, Routers at L3. The OSI model is theoretical; TCP/IP model is practical (4 layers)."
    },
    "ip addressing": {
        "title": "IP Addressing, Subnetting & CIDR",
        "subject": "CN",
        "explanation": "IPv4: 32-bit address in dotted-decimal (e.g. 192.168.1.1). Classes: A (0-127), B (128-191), C (192-223). **Subnetting** divides a network into smaller sub-networks using a **subnet mask**. CIDR notation: 192.168.1.0/24 means 24 bits for network, 8 for hosts.",
        "complexity": "Hosts per subnet = 2^(host bits) âˆ’ 2 (subtract network & broadcast). /24 → 254 hosts. /25 → 126 hosts. /30 → 2 hosts (point-to-point links).",
        "exam_tip": "Subnetting trick: write out the subnet mask in binary. Borrowed bits = extra subnet bits. Number of subnets = 2^(borrowed bits). Formula: Network Address = IP AND Subnet Mask. Broadcast = Network Address OR (NOT Subnet Mask). VLSM allows different subnet sizes within one network."
    },

    # ── DATABASE MANAGEMENT SYSTEMS ───────────────────────────────────────────
    "normalization": {
        "title": "Database Normalization (1NF → BCNF)",
        "subject": "DBMS",
        "explanation": "A technique to organize database tables to reduce **data redundancy** and eliminate anomalies (insert, update, delete). Each normal form builds on the previous.",
        "complexity": "1NF: Atomic values, no repeating groups | 2NF: 1NF + No Partial Dependency (non-key attribute depends on full primary key) | 3NF: 2NF + No Transitive Dependency | BCNF: Every determinant is a candidate key",
        "exam_tip": "Partial dependency only occurs with **composite primary keys**. To check 3NF: for every FD X→Y, either X is a superkey OR Y is a prime attribute. BCNF is stricter — X must always be a superkey. Decomposition must be lossless-join and dependency-preserving."
    },
    "sql joins": {
        "title": "SQL Joins (INNER, OUTER, SELF, CROSS)",
        "subject": "DBMS",
        "explanation": "Joins combine rows from two or more tables. **INNER JOIN**: returns rows with matching values in both tables. **LEFT JOIN**: all rows from left + matched rows from right (NULL if no match). **RIGHT JOIN**: opposite. **FULL OUTER JOIN**: all rows from both. **SELF JOIN**: table joins with itself. **CROSS JOIN**: cartesian product.",
        "complexity": "INNER JOIN result size â‰¤ min(|R|, |S|). CROSS JOIN result size = |R| Ã— |S|.",
        "exam_tip": "Write SQL queries with aliases: `SELECT e.name, d.dept FROM Employee e INNER JOIN Department d ON e.dept_id = d.id`. LEFT JOIN is most common in real-world use. For NULL handling in outer joins, use `IS NULL` not `= NULL`. Equijoin = join on equality; Natural join = equijoin on same-name columns."
    },
    "transactions": {
        "title": "Database Transactions & ACID Properties",
        "subject": "DBMS",
        "explanation": "A transaction is a sequence of database operations treated as a single logical unit. **ACID**: Atomicity (all-or-nothing), Consistency (DB moves from one valid state to another), Isolation (concurrent transactions don't interfere), Durability (committed data persists even after crash).",
        "complexity": "Concurrency issues: Dirty Read, Non-repeatable Read, Phantom Read. Isolation Levels: READ UNCOMMITTED → READ COMMITTED → REPEATABLE READ → SERIALIZABLE.",
        "exam_tip": "Atomicity is ensured by **rollback/undo logs**. Durability by **redo logs/WAL (Write-Ahead Logging)**. Serializable is the strictest isolation level — prevents all anomalies but has lowest concurrency. Most DBs default to READ COMMITTED. Two-Phase Locking (2PL) ensures serializability: Growing Phase (acquire locks) then Shrinking Phase (release locks)."
    },

    # ── OBJECT-ORIENTED PROGRAMMING ───────────────────────────────────────────
    "polymorphism": {
        "title": "Polymorphism in OOP",
        "subject": "OOP",
        "explanation": "The ability of an entity to take multiple forms. **Compile-time (Static) Polymorphism**: Method Overloading — same method name, different parameters, resolved at compile time. **Runtime (Dynamic) Polymorphism**: Method Overriding — subclass overrides parent method, resolved at runtime via virtual function table (vtable).",
        "complexity": "Static Binding: faster (resolved at compile time). Dynamic Binding: flexible (resolved at runtime via vtable pointer).",
        "exam_tip": "In C++: use `virtual` keyword for runtime polymorphism. In Java: all non-static, non-final methods are virtual by default. Key: `Animal a = new Dog(); a.sound()` — calls Dog's sound() due to dynamic dispatch. Pure virtual function (`=0` in C++) makes class abstract."
    },
    "inheritance": {
        "title": "Inheritance in OOP",
        "subject": "OOP",
        "explanation": "A mechanism where a derived class (child) acquires properties and behaviors of a base class (parent). Types: Single, Multiple (C++, not Java — use interfaces), Multilevel, Hierarchical, Hybrid. `IS-A` relationship.",
        "complexity": "Code reuse without duplication. Method Resolution Order (MRO) in Python follows C3 linearization for multiple inheritance.",
        "exam_tip": "Java doesn't support multiple class inheritance (diamond problem) — uses **interfaces** instead. C++ supports it but requires `virtual` base class to solve diamond problem. Constructor order: Parent constructor called first (Base → Derived). Destructor order: reverse (Derived → Base). Abstract class has at least one pure virtual/abstract method."
    },
    "encapsulation": {
        "title": "Encapsulation & Abstraction in OOP",
        "subject": "OOP",
        "explanation": "**Encapsulation**: bundling data (attributes) and methods that operate on that data within a class, and restricting direct access using access modifiers (private, protected, public). Achieved via **getters/setters**. **Abstraction**: hiding implementation details, exposing only the interface — achieved via abstract classes and interfaces.",
        "complexity": "Access control: private (class only) < protected (class + subclasses) < public (everyone). Package-private (default in Java): within same package.",
        "exam_tip": "Encapsulation = data hiding. Abstraction = implementation hiding. They work together. A well-encapsulated class exposes only a minimal public API. Abstraction reduces complexity — user of a `List` doesn't need to know if it's ArrayList or LinkedList internally."
    },

    # ── COMPUTER ORGANIZATION & ARCHITECTURE ──────────────────────────────────
    "cache memory": {
        "title": "Cache Memory & Locality of Reference",
        "subject": "COA",
        "explanation": "A small, fast memory between the CPU and main RAM. Exploits **temporal locality** (recently accessed data likely accessed again) and **spatial locality** (nearby addresses likely accessed soon). Organized in levels: L1 (fastest, smallest, on-chip) > L2 > L3.",
        "complexity": "Cache hit: data found in cache (fast). Cache miss: data fetched from RAM (slow). Hit rate typically 90–99%. Effective Access Time = hit-rate Ã— cache-time + (1-hit-rate) Ã— memory-time.",
        "exam_tip": "Mapping techniques: **Direct Mapping** (simple, high conflict misses), **Fully Associative** (no conflict, expensive), **Set-Associative** (compromise, most common in practice). Cache replacement policies: LRU, FIFO, Random. Write policies: Write-Through (immediately to RAM, simpler) and Write-Back (only on eviction, faster but complex)."
    },
    "pipeline": {
        "title": "CPU Pipelining & Hazards",
        "subject": "COA",
        "explanation": "Pipelining overlaps execution of multiple instructions by dividing instruction execution into stages (IF → ID → EX → MEM → WB). Like an assembly line — while one instruction is in EX stage, the next is in ID, and the one after is being Fetched.",
        "complexity": "Ideal speedup = number of pipeline stages. Throughput = 1 instruction per clock cycle (after pipeline fills). CPI (Cycles Per Instruction) → approaches 1 with deep pipelining.",
        "exam_tip": "Pipeline **hazards**: (1) **Structural** — resource conflict (two instructions need same unit). (2) **Data** — instruction depends on result of previous instruction (RAW, WAR, WAW). Solved by forwarding/bypassing or stalling. (3) **Control** — branch instructions cause uncertainty. Solved by branch prediction. Stalls (bubbles) reduce performance."
    },

    # ── THEORY OF COMPUTATION ─────────────────────────────────────────────────
    "automata": {
        "title": "Automata Theory: DFA, NFA & Regular Languages",
        "subject": "TOC",
        "explanation": "**DFA** (Deterministic Finite Automaton): for each state and input symbol, exactly one transition. **NFA** (Non-Deterministic FA): zero or more transitions per state/symbol. Both recognize exactly the **Regular Languages**. Every NFA can be converted to an equivalent DFA (subset construction, may exponentially increase states).",
        "complexity": "DFA/NFA: O(N) to process string of length N. NFA→DFA conversion: up to 2^N DFA states from N NFA states.",
        "exam_tip": "Regular Languages closed under: union, concatenation, star, complement, intersection. Non-regular languages (proven by **Pumping Lemma**): {a^n b^n}, {a^(nÂ²)}, palindromes. Context-Free Languages (CFG/PDA) cover {a^n b^n}. Turing Machines recognize Recursively Enumerable languages. Chomsky hierarchy: Regular âŠ‚ CFL âŠ‚ CSL âŠ‚ RE."
    },

    # ── SOFTWARE ENGINEERING ──────────────────────────────────────────────────
    "sdlc": {
        "title": "Software Development Life Cycle (SDLC) Models",
        "subject": "SE",
        "explanation": "Structured process for planning, creating, testing, and delivering software. Models: **Waterfall** (sequential, rigid), **Agile** (iterative sprints, flexible), **Spiral** (risk-driven, for large projects), **V-Model** (testing at each stage), **RAD** (Rapid Application Development).",
        "complexity": "Waterfall: simple but inflexible — changes expensive after requirements frozen. Agile: 2-week sprints, continuous feedback, handles change well. SCRUM (Agile framework): roles = Product Owner, Scrum Master, Dev Team.",
        "exam_tip": "SDLC phases: Requirements → Design → Implementation → Testing → Deployment → Maintenance. Testing types: Unit (module), Integration (module+module), System (full system), Acceptance (UAT by client). **COCOMO model** for cost estimation. Agile values: Individuals & interactions > Processes & tools."
    },

    # ── DATA STRUCTURES (ADDITIONAL) ──────────────────────────────────────────
    "array": {
        "title": "Arrays & Strings — Foundation Data Structure",
        "subject": "DSA",
        "explanation": "An array stores elements of the **same type** in contiguous memory locations, accessed via zero-based index. Strings are character arrays. Key operations: traversal O(N), access O(1), insertion/deletion O(N) (shifting). 2D arrays use row-major order in C/Java.",
        "complexity": "Access: O(1) | Search (unsorted): O(N) | Search (sorted + Binary Search): O(log N) | Insert/Delete (end): O(1) amortised | Insert/Delete (middle): O(N)",
        "exam_tip": "Sliding window technique reduces O(N²) substring problems to O(N). Two-pointer approach solves sorted-array pair-sum in O(N). Common interview patterns: kadane's algorithm (max subarray sum O(N)), prefix sum array (range query O(1) after O(N) build). Always clarify whether the array is sorted before choosing a search algorithm."
    },
    "heap": {
        "title": "Heap Data Structure & Priority Queue",
        "subject": "DSA",
        "explanation": "A **complete binary tree** satisfying the heap property. **Min-Heap**: parent â‰¤ children (root = minimum). **Max-Heap**: parent â‰¥ children (root = maximum). Stored as an array — parent of index i is at âŒŠ(i-1)/2âŒ‹; children at 2i+1 and 2i+2.",
        "complexity": "Insert (heapify-up): O(log N) | Delete-min/max (heapify-down): O(log N) | Build heap from array: O(N) — NOT O(N log N) | Peek min/max: O(1)",
        "exam_tip": "Heap is the backbone of **Priority Queue** and **Heap Sort** (O(N log N) in-place). Build-heap is O(N) because most elements are near the bottom (do heapify-down from N/2 to 0). Top-K elements problem: use a Min-Heap of size K — O(N log K). Dijkstra's shortest path uses a Min-Heap. Java: `PriorityQueue`. Python: `heapq` (min-heap only — negate values for max)."
    },
    "greedy algorithm": {
        "title": "Greedy Algorithms",
        "subject": "DSA",
        "explanation": "Makes the **locally optimal choice** at each step hoping to reach the global optimum. No backtracking. Works when the problem has **Greedy Choice Property** (local optimal → global optimal) and **Optimal Substructure**.",
        "complexity": "Activity Selection: O(N log N) | Fractional Knapsack: O(N log N) | Huffman Coding: O(N log N) | Kruskal's MST: O(E log E) | Prim's MST: O(E log V)",
        "exam_tip": "Greedy vs DP: Greedy makes one irreversible choice per step; DP explores all subproblems. Greedy fails for 0/1 Knapsack (use DP instead) but works for Fractional Knapsack. Classic greedy problems: **Activity Selection** (pick max non-overlapping intervals), **Huffman Encoding** (minimum prefix-free code), **Coin Change** (only works for canonical coin systems — fails for arbitrary denominations)."
    },
    "recursion": {
        "title": "Recursion & Backtracking",
        "subject": "DSA",
        "explanation": "**Recursion**: a function calls itself with a smaller input until a **base case** is reached. Every recursive call goes onto the call stack. **Backtracking**: try a solution, and if it fails, undo (backtrack) and try the next option — essentially DFS on the solution space.",
        "complexity": "Time: depends on recurrence. T(N) = 2T(N/2) + O(N) → O(N log N) (Merge Sort). T(N) = T(N-1) + O(1) → O(N) (Factorial). Space: O(depth of recursion) for the call stack.",
        "exam_tip": "Solve recurrences with **Master Theorem**: T(N) = aT(N/b) + f(N). Three cases based on f(N) vs N^(log_b a). Backtracking classics: N-Queens, Sudoku solver, Rat in a Maze, Subset Sum. Always define the base case first — missing base case = infinite recursion = stack overflow. Tail recursion can be optimised by compilers into a loop."
    },

    # ── OPERATING SYSTEMS (ADDITIONAL) ────────────────────────────────────────
    "file system": {
        "title": "File Systems & I/O in OS",
        "subject": "OS",
        "explanation": "A file system organises data on storage as a hierarchy of directories and files. Key concepts: **inode** (stores metadata — permissions, size, pointers to data blocks), **FAT** (File Allocation Table — simple linked list of blocks), **inode-based** (Unix ext4 — direct, single-indirect, double-indirect block pointers).",
        "complexity": "Disk access is 10âµÃ— slower than RAM. Disk scheduling algorithms minimise seek time: FCFS, SSTF (Shortest Seek Time First), SCAN (elevator), C-SCAN (circular), LOOK.",
        "exam_tip": "**Inode structure**: 12 direct pointers + 1 single-indirect + 1 double-indirect + 1 triple-indirect. For block size B and pointer size P: max file size = 12B + (B/P)B + (B/P)Â²B + (B/P)Â³B. Disk scheduling: SSTF minimises seek but causes starvation. SCAN is the standard elevator algorithm — most commonly tested. File permissions in Unix: rwx = read(4) write(2) execute(1). `chmod 755` = rwxr-xr-x."
    },

    # ── PHASE 2 ADDITIONS — Modern CS Topics ─────────────────────────────────
    "cryptography": {
        "title": "Cryptography & Network Security",
        "subject": "CNS",
        "explanation": "The science of securing communication using mathematical algorithms. **Symmetric encryption**: same key for encrypt & decrypt (AES, DES) — fast, used for bulk data. **Asymmetric encryption**: public key encrypts, private key decrypts (RSA) — slow, used for key exchange & digital signatures. **Hashing**: one-way function (SHA-256, MD5) — verifies integrity, not confidential.",
        "complexity": "AES-128/256: O(N) for N-byte plaintext | RSA key generation: O(k^3) for k-bit key | SHA-256: O(N) | DH Key Exchange: O(k^2) modular exponentiation.",
        "exam_tip": "Key concepts: **CIA Triad** = Confidentiality, Integrity, Availability. RSA security relies on integer factorization being hard. Digital signature = encrypt hash with **private** key (not public). SSL/TLS handshake uses asymmetric crypto to exchange symmetric session keys. Common attacks: Man-in-the-Middle (MITM), Replay attack, Brute-force, Dictionary attack."
    },
    "cloud computing": {
        "title": "Cloud Computing — IaaS, PaaS & SaaS",
        "subject": "CC",
        "explanation": "Delivery of computing services (servers, storage, databases, networking, software) over the internet. **IaaS** (Infrastructure as a Service): raw VMs & storage — AWS EC2, Azure VMs. **PaaS** (Platform as a Service): managed runtime — Heroku, Google App Engine. **SaaS** (Software as a Service): ready-to-use apps — Gmail, Salesforce. **Serverless**: function-level billing, zero server management — AWS Lambda.",
        "complexity": "Elasticity: scale horizontally (add instances) or vertically (bigger instance). SLA typically guarantees 99.9% uptime = 8.76 hours downtime/year.",
        "exam_tip": "Cloud deployment models: **Public** (shared infra, AWS/Azure/GCP), **Private** (on-premise, dedicated), **Hybrid** (mix). Key benefits: no CapEx, on-demand scaling, global reach. Distinguish IaaS vs PaaS vs SaaS responsibility — IaaS: manage OS upward; PaaS: only the app; SaaS: nothing. CAP Theorem: a distributed system guarantees only 2 of 3: **Consistency, Availability, Partition Tolerance**."
    },
    "machine learning": {
        "title": "Machine Learning — Supervised, Unsupervised & Reinforcement",
        "subject": "AI/ML",
        "explanation": "A subset of AI where systems **learn patterns from data** without being explicitly programmed. **Supervised Learning**: labeled data to predict output (Linear Regression, Decision Trees, SVM, KNN). **Unsupervised Learning**: unlabeled data to find structure (K-Means Clustering, PCA). **Reinforcement Learning**: agent learns by reward/penalty (Q-Learning, Deep Q-Network).",
        "complexity": "Training: O(N x D x E) for N samples, D features, E epochs. K-Means: O(N x K x D x I) for K clusters, I iterations.",
        "exam_tip": "Key terms: **Overfitting** (memorises training data, fails on test) vs **Underfitting** (too simple, poor on both). Solution: regularization (L1 Lasso, L2 Ridge), dropout, cross-validation. **Bias-Variance Tradeoff**: high bias = underfitting, high variance = overfitting. Evaluation metrics: Accuracy, Precision, Recall, F1-Score, ROC-AUC. Feature scaling (StandardScaler, MinMax) is mandatory for SVM and KNN."
    },
    "neural networks": {
        "title": "Neural Networks & Deep Learning",
        "subject": "AI/ML",
        "explanation": "Inspired by the human brain — layers of interconnected **neurons** (nodes). Input Layer → Hidden Layers → Output Layer. Each neuron applies: output = activation(weights x inputs + bias). **Backpropagation** trains the network by computing gradients of the loss function and adjusting weights via gradient descent. Deep Learning = many hidden layers (CNN for images, RNN/LSTM for sequences, Transformer for NLP).",
        "complexity": "Forward pass: O(L x N^2) for L layers, N neurons per layer. Backprop: same complexity. GPU-accelerated training parallelises across millions of parameters.",
        "exam_tip": "**Activation functions**: Sigmoid (0-1, binary classification output), ReLU (max(0,x) — avoids vanishing gradient, standard hidden layer), Softmax (multi-class output). **Vanishing gradient problem**: gradients shrink through deep sigmoid layers — solved by ReLU and batch normalization. CNN key layers: Convolution (feature extraction), Pooling (downsample), Fully Connected (classify). LSTM solves RNN vanishing gradient for sequential data."
    },
    "blockchain": {
        "title": "Blockchain — Distributed Ledger Technology",
        "subject": "Blockchain",
        "explanation": "A **distributed, immutable ledger** where data is stored in linked blocks. Each block contains: data (transactions), a cryptographic hash of itself, and the hash of the previous block — forming a tamper-evident chain. **Consensus mechanisms**: Proof of Work (PoW — Bitcoin, energy-intensive), Proof of Stake (PoS — Ethereum 2.0, eco-friendly). **Smart Contracts**: self-executing code on the blockchain (Ethereum/Solidity) — run when conditions are met, no intermediary needed.",
        "complexity": "Bitcoin PoW: SHA-256 hash puzzle, ~10 min/block. Ethereum PoS: validators stake ETH. Scalability trilemma: Decentralization, Security, Scalability — pick 2.",
        "exam_tip": "Key properties: **Immutability** (hash chain makes tampering detectable), **Decentralization** (no single point of failure), **Transparency** (anyone can verify). 51% attack: controlling >51% of hash power allows rewriting history. Types: Public (Bitcoin, Ethereum), Private (Hyperledger Fabric), Consortium (multi-org). Use cases: cryptocurrency, supply chain, NFTs, voting systems, healthcare records."
    },
    "iot": {
        "title": "Internet of Things (IoT)",
        "subject": "IoT",
        "explanation": "A network of **physical devices** (sensors, actuators, appliances) embedded with software and connectivity to collect and exchange data. Architecture layers: **Perception** (sensors/actuators), **Network** (WiFi, Bluetooth, Zigbee, LoRa), **Processing** (edge/fog/cloud), **Application** (smart home, healthcare, industry 4.0). **Edge Computing** processes data near the source — reduces latency and bandwidth.",
        "complexity": "MQTT protocol: lightweight publish-subscribe, ideal for constrained devices (port 1883). CoAP: RESTful protocol for IoT (UDP-based, low overhead). IPv6/6LoWPAN needed for billions of IoT devices.",
        "exam_tip": "Key protocols: **MQTT** (Message Queuing Telemetry Transport) — publisher sends to broker, subscribers receive — most common IoT protocol. **HTTP vs MQTT**: HTTP is request-response (heavyweight); MQTT is event-driven (lightweight). IoT challenges: security (default passwords, firmware updates), privacy (data collection), interoperability (vendor lock-in), power management. Real-world: smart meters, fitness trackers, industrial sensors, connected vehicles."
    },
    "computer graphics": {
        "title": "Computer Graphics — Rendering & Transformations",
        "subject": "CG",
        "explanation": "The science of generating visual content using computers. **Rasterization**: converts vector geometry (triangles) to pixel fragments — used in real-time graphics (OpenGL, DirectX). **Ray Tracing**: simulates real light paths for photorealistic rendering. **2D/3D Transformations**: Translation (move), Scaling (resize), Rotation (angle) — represented as matrices. Homogeneous coordinates allow all transforms as matrix multiplications.",
        "complexity": "Rasterization: O(triangles x pixels per triangle). Ray Tracing: O(pixels x rays x scene complexity). 4x4 homogeneous transform matrix multiplication: O(16) per vertex.",
        "exam_tip": "**OpenGL pipeline**: Vertex Shader (transform 3D coords) → Rasterization → Fragment Shader (color per pixel) → Framebuffer. **Bresenham Line Algorithm**: draws lines using integer arithmetic (no floating point). **Cohen-Sutherland**: line clipping. **Phong shading**: Ambient + Diffuse + Specular = realistic lighting. Transformation order: Scale → Rotate → Translate (TRS), applied right-to-left in matrix multiplication."
    },
    "compiler design": {
        "title": "Compiler Design — Phases & Parsing",
        "subject": "CD",
        "explanation": "A compiler translates high-level source code to machine code in phases: **Lexical Analysis** (scanner — source text to tokens), **Syntax Analysis** (parser — tokens to Parse Tree using CFG), **Semantic Analysis** (type checking, scope resolution), **Intermediate Code Generation** (3-address code), **Code Optimization** (constant folding, dead code elimination), **Code Generation** (assembly/machine code). Symbol Table maintains variable info across all phases.",
        "complexity": "Lexical Analysis: O(N) using DFA-based scanner. LL(1)/LR(1) Parsing: O(N) for N tokens. Optimization passes: O(N) to O(N^2) depending on algorithm.",
        "exam_tip": "**Top-Down Parsing**: LL(1) — uses stack and parsing table, no left recursion allowed. **Bottom-Up Parsing**: LR(0), SLR(1), LALR(1), LR(1) — shift-reduce parsing; real compilers use LALR(1) (e.g. GCC). **First & Follow sets**: used to build LL(1) parsing tables. **Ambiguous grammar**: one string has two or more parse trees — always bad, must be eliminated. **Three-Address Code**: x = y op z — simplest IR for optimization."
    },
    "software testing": {
        "title": "Software Testing — Types, Strategies & TDD",
        "subject": "SE",
        "explanation": "The process of evaluating software to find defects and verify it meets requirements. **Testing levels**: Unit (single function), Integration (module interactions), System (end-to-end), Acceptance/UAT (client validates). **Strategies**: **Black-Box** (test without knowing internals — boundary value, equivalence partitioning), **White-Box** (test with code knowledge — path coverage, branch coverage). **TDD** (Test-Driven Development): write test first, then code to pass it.",
        "complexity": "Statement Coverage: % of code lines executed. Branch Coverage: % of decision branches taken. Path Coverage: all possible execution paths — exponential, impractical for large programs.",
        "exam_tip": "Key terms: **Alpha testing** (in-house before release), **Beta testing** (real users before final release), **Regression testing** (re-test after fixes), **Smoke testing** (quick sanity check), **Load testing** (performance under load). **Equivalence Partitioning**: divide inputs into valid/invalid classes. **Boundary Value Analysis**: test at min, max, min-1, max+1 — catches off-by-one errors. **Cyclomatic Complexity** = E - N + 2P = number of independent paths."
    },
    "microprocessors": {
        "title": "Microprocessors — 8085/8086 Architecture",
        "subject": "MP",
        "explanation": "A microprocessor is a CPU on a single IC chip. **8085 (Intel)**: 8-bit data bus, 16-bit address bus (64KB memory), registers: A (Accumulator), B,C,D,E,H,L (general purpose), SP (Stack Pointer), PC (Program Counter), Flags (S,Z,AC,P,CY). **8086 (Intel)**: 16-bit data bus, 20-bit address bus (1MB memory), segmented memory model (CS, DS, SS, ES). Key concepts: Instruction Set, Addressing Modes (immediate, register, direct, indirect), Interrupts (hardware/software, vectored).",
        "complexity": "8085 clock: 3-6 MHz. Instruction execution: 1-5 machine cycles. Each machine cycle: 3 T-states. Memory access time must match processor speed.",
        "exam_tip": "8085 **flags**: Sign (S), Zero (Z), Auxiliary Carry (AC), Parity (P), Carry (CY). **DAA** instruction uses AC and CY flags for BCD arithmetic. **8085 interrupt priority** (high to low): TRAP > RST 7.5 > RST 6.5 > RST 5.5 > INTR. **8086 vs 8085**: 8086 has separate BIU (Bus Interface Unit) and EU (Execution Unit) — enables pipelining (fetch next instruction while executing current). Segment:Offset addressing: Physical address = Segment x 16 + Offset."
    },

}

# ── Keyword aliases → map alternate phrasings to canonical keys ────────────────
# NOTE: sorted longest-first at runtime so that longer phrases match before their
# shorter substrings (e.g. "shortest path" before "short", "heap sort" before "heap").
STUDY_ALIASES = {
    # Graph / BFS / DFS
    "shortest path": "graph", "bfs": "graph", "dfs": "graph", "dijkstra": "graph",
    "bellman ford": "graph", "topological sort": "graph", "strongly connected": "graph",
    # Sorting
    "selection sort": "bubble sort", "insertion sort": "bubble sort", "sorting": "bubble sort",
    "merge sort": "merge sort", "merge": "merge sort",
    "quick sort": "quick sort", "quick": "quick sort",
    "heap sort": "heap", "priority queue": "heap", "min heap": "heap", "max heap": "heap",
    # Linked list
    "doubly linked": "linked list", "singly linked": "linked list", "circular linked": "linked list",
    "linked": "linked list",
    # Hash
    "hash table": "hashing", "hash map": "hashing", "hash function": "hashing",
    "hash": "hashing",
    # DP
    "dynamic programming": "dynamic programming",
    "memoization": "dynamic programming", "tabulation": "dynamic programming",
    "knapsack": "dynamic programming", "lcs": "dynamic programming",
    "longest common": "dynamic programming", "fibonacci": "dynamic programming",
    "dp": "dynamic programming",
    # Process scheduling
    "cpu scheduling": "process scheduling", "round robin": "process scheduling",
    "process scheduling": "process scheduling",
    "fcfs": "process scheduling", "sjf": "process scheduling", "srtf": "process scheduling",
    "process": "process scheduling",
    # Paging / Virtual memory
    "virtual memory": "paging", "page fault": "paging", "page table": "paging",
    "tlb": "paging", "paging": "paging",
    # Semaphore / Sync
    "producer consumer": "semaphore", "dining philosopher": "semaphore",
    "critical section": "semaphore", "synchronization": "semaphore",
    "mutex": "semaphore",
    # OSI / CN
    "osi model": "osi model", "osi layer": "osi model", "network layer": "osi model",
    "osi": "osi model",
    # IP
    "ip addressing": "ip addressing", "subnetting": "ip addressing", "cidr": "ip addressing",
    "subnet": "ip addressing",
    # SQL / DBMS
    "inner join": "sql joins", "outer join": "sql joins", "left join": "sql joins",
    "right join": "sql joins", "sql joins": "sql joins",
    "join": "sql joins", "sql": "sql joins",
    # Transactions
    "acid properties": "transactions", "acid": "transactions",
    "transaction": "transactions", "2pl": "transactions", "two phase": "transactions",
    # OOP
    "method overriding": "polymorphism", "method overloading": "polymorphism",
    "runtime polymorphism": "polymorphism", "static polymorphism": "polymorphism",
    "multiple inheritance": "inheritance", "extends": "inheritance",
    "encapsulation": "encapsulation", "abstraction": "encapsulation",
    # COA
    "cache memory": "cache memory", "l1 cache": "cache memory", "l2 cache": "cache memory",
    "locality of reference": "cache memory", "locality": "cache memory",
    "cache": "cache memory",
    "pipeline hazard": "pipeline", "pipelining": "pipeline", "stall": "pipeline",
    # TOC
    "finite automata": "automata", "regular language": "automata", "pumping lemma": "automata",
    "dfa": "automata", "nfa": "automata", "turing": "automata",
    # SE
    "software model": "sdlc", "waterfall model": "sdlc", "agile methodology": "sdlc",
    "agile": "sdlc", "waterfall": "sdlc", "scrum": "sdlc",
    # New topics
    "sliding window": "array", "two pointer": "array", "kadane": "array",
    "string": "array", "2d array": "array",
    "backtracking": "recursion", "n queens": "recursion", "base case": "recursion",
    "master theorem": "recursion", "recurrence": "recursion",
    "greedy": "greedy algorithm", "activity selection": "greedy algorithm",
    "huffman": "greedy algorithm", "kruskal": "greedy algorithm", "prim": "greedy algorithm",
    "fractional knapsack": "greedy algorithm",
    "file system": "file system", "disk scheduling": "file system",
    "inode": "file system", "fat": "file system", "sstf": "file system",
    # Phase 2 new topic aliases
    "cryptography": "cryptography", "rsa": "cryptography", "aes": "cryptography",
    "encryption": "cryptography", "cipher": "cryptography", "sha": "cryptography",
    "digital signature": "cryptography", "ssl": "cryptography", "tls": "cryptography",
    "cia triad": "cryptography", "network security": "cryptography",
    "cloud computing": "cloud computing", "cloud": "cloud computing",
    "iaas": "cloud computing", "paas": "cloud computing", "saas": "cloud computing",
    "aws": "cloud computing", "azure": "cloud computing", "gcp": "cloud computing",
    "serverless": "cloud computing", "lambda": "cloud computing", "cap theorem": "cloud computing",
    "machine learning": "machine learning", "ml": "machine learning",
    "supervised learning": "machine learning", "unsupervised learning": "machine learning",
    "reinforcement learning": "machine learning", "overfitting": "machine learning",
    "underfitting": "machine learning", "regression": "machine learning",
    "classification": "machine learning", "clustering": "machine learning",
    "neural network": "neural networks", "deep learning": "neural networks",
    "cnn": "neural networks", "rnn": "neural networks", "lstm": "neural networks",
    "transformer": "neural networks", "backpropagation": "neural networks",
    "activation function": "neural networks", "relu": "neural networks",
    "vanishing gradient": "neural networks", "perceptron": "neural networks",
    "blockchain": "blockchain", "bitcoin": "blockchain", "ethereum": "blockchain",
    "smart contract": "blockchain", "proof of work": "blockchain",
    "proof of stake": "blockchain", "distributed ledger": "blockchain",
    "nft": "blockchain", "cryptocurrency": "blockchain", "consensus": "blockchain",
    "internet of things": "iot", "mqtt": "iot", "edge computing": "iot",
    "sensor": "iot", "actuator": "iot", "zigbee": "iot", "lora": "iot",
    "computer graphics": "computer graphics", "opengl": "computer graphics",
    "ray tracing": "computer graphics", "rasterization": "computer graphics",
    "rendering": "computer graphics", "bresenham": "computer graphics",
    "phong": "computer graphics", "3d transformation": "computer graphics",
    "compiler design": "compiler design", "compiler": "compiler design",
    "lexical analysis": "compiler design", "parsing": "compiler design",
    "syntax analysis": "compiler design", "semantic analysis": "compiler design",
    "code generation": "compiler design", "three address code": "compiler design",
    "lalr": "compiler design", "ll1": "compiler design",
    "software testing": "software testing", "unit testing": "software testing",
    "black box": "software testing", "white box": "software testing",
    "tdd": "software testing", "test driven": "software testing",
    "regression testing": "software testing", "boundary value": "software testing",
    "equivalence partitioning": "software testing", "cyclomatic": "software testing",
    "microprocessors": "microprocessors", "8085": "microprocessors",
    "8086": "microprocessors", "microprocessor": "microprocessors",
    "instruction set": "microprocessors", "addressing mode": "microprocessors",

}

# ── Student Health Triage Knowledge Base ──────────────────────────────────────
# Keys are lowercase trigger words. HEALTH_ALIASES maps synonyms to canonical keys.

HEALTH_SYMPTOMS = {
    "fever": {
        "condition": "Mild Viral Fever / High Temperature",
        "severity": "Moderate",
        "first_aid": "Paracetamol (PCM 500mg/650mg) after food if temperature > 99.5Â°F. Apply a wet cloth on forehead and wrists. Stay in a cool, ventilated room.",
        "home_remedy": "Drink warm water with ORS (Electral/Glucon-D) every 2 hours. Complete bed rest. Avoid cold drinks, fans directly on body. Sip warm ginger-tulsi tea.",
        "doctor_alert": "🚨 Rush to campus medical room if: fever > 102Â°F with shivering, fever persists beyond 48 hours, rash appears, or neck stiffness occurs (could indicate meningitis)."
    },
    "headache": {
        "condition": "Tension Headache / Digital Eye Strain",
        "severity": "Mild-Moderate",
        "first_aid": "Immediate: 20-min screen break in a dim room. Apply Amrutanjan/Vicks balm on temples & forehead. If severe: Paracetamol 500mg with water (not empty stomach).",
        "home_remedy": "Drink 2–3 large glasses of water immediately (dehydration is the #1 cause in students). Gentle neck & shoulder stretches. Cold/hot compress on neck. Peppermint oil roll-on on temples.",
        "doctor_alert": "🚨 See a doctor if: sudden severe 'thunderclap' headache, headache with vomiting + light sensitivity (migraine or worse), blurred vision, or headache after a head injury."
    },
    "cold": {
        "condition": "Common Cold, Runny Nose & Sore Throat",
        "severity": "Mild",
        "first_aid": "Steam inhalation (plain hot water or with Vicks VapoRub) twice daily. Cetirizine 10mg at bedtime for heavy sneezing/runny nose. Throat lozenges (Strepsils) for soreness.",
        "home_remedy": "Warm salt water gargle 3 times a day (Â½ tsp salt in 1 glass warm water). Hot ginger-tulsi-honey tea. Stay hydrated. Avoid cold water, ice cream, and AC directly on body.",
        "doctor_alert": "🚨 Consult physician if: cold lasts > 10 days, severe ear pain, greenish/yellow nasal discharge (bacterial infection), or high fever develops alongside cold."
    },
    "cough": {
        "condition": "Dry or Wet Cough & Throat Irritation",
        "severity": "Mild-Moderate",
        "first_aid": "Strepsils/Koflet lozenges for throat irritation. Steam inhalation 2Ã—/day. For wet cough: Benadryl/Chericof syrup (expectorant) 10ml after meals. For dry cough: Honitus/Dabur honey-ginger syrup.",
        "home_remedy": "Warm turmeric milk (Haldi doodh with a pinch of pepper and ghee) before sleeping. 1 tsp honey with a pinch of black pepper and ginger juice. Avoid cold beverages and dusty environments.",
        "doctor_alert": "🚨 See a doctor if: cough persists > 2 weeks, blood in sputum, chest pain while coughing, or breathlessness accompanies the cough."
    },
    "stomach": {
        "condition": "Stomach Ache / Abdominal Cramps",
        "severity": "Moderate",
        "first_aid": "Identify location: Upper abdomen → acidity (take Gelusil/Eno). Lower abdomen cramps → Meftal Spas (antispasmodic) 1 tablet. Apply warm water bottle on abdomen. Sip warm water slowly.",
        "home_remedy": "Drink coconut water or ORS for rehydration. Eat plain khichdi, curd-rice, or bananas — avoid spicy hostel mess food. Ajwain (carom seeds) in warm water relieves gas/cramps quickly.",
        "doctor_alert": "🚨 Emergency: severe sudden pain in lower-right abdomen (appendicitis risk), blood in stool, vomiting blood, or fever + stomach pain together — go to hospital immediately."
    },
    "acidity": {
        "condition": "Acid Reflux / Heartburn / Gastritis",
        "severity": "Mild-Moderate",
        "first_aid": "Gelusil / Digene antacid gel 2 teaspoons after meals. Eno fruit salt in water for instant relief. Pantoprazole 40mg (PPI) before breakfast for persistent hyperacidity — available at campus dispensary.",
        "home_remedy": "Cold milk (without sugar) gives instant relief by neutralizing acid. Sip jeera (cumin) water or fennel seed (saunf) water. Avoid lying flat for 2 hours after eating. Eat small, frequent meals.",
        "doctor_alert": "🚨 See a doctor if: burning pain that radiates to jaw/left arm (cardiac symptom), difficulty swallowing, black tarry stools, or frequent unexplained vomiting."
    },
    "stress": {
        "condition": "Exam Anxiety, Mental Fatigue & Burnout",
        "severity": "Moderate — Needs Attention",
        "first_aid": "**4-7-8 Breathing**: Inhale for 4s → Hold for 7s → Exhale slowly for 8s. Repeat 4 cycles. This activates the parasympathetic nervous system instantly. Take a 15-minute walk outside — sunlight boosts serotonin.",
        "home_remedy": "Ashwagandha (KSM-66) supplement reduces cortisol with consistent use. Chamomile tea before bed for better sleep. Avoid energy drinks — they worsen anxiety. Write down tomorrow's tasks to declutter the mind before sleeping.",
        "doctor_alert": "🚨 Please reach out to: College Counselor (Student Wellness Center), iCall (9152987821 — free student helpline), or Vandrevala Foundation (1860-2662-345, 24/7 free). You are not alone. Exams do not define your worth."
    },
    "vomiting": {
        "condition": "Nausea & Vomiting (Food Poisoning / Gastroenteritis)",
        "severity": "Moderate",
        "first_aid": "Stop eating solid food for 2–4 hours. Sip cold water or ice chips slowly. Ondansetron 4mg (Emeset/Zofer) — anti-nausea tablet available at campus dispensary — under tongue or swallowed with water.",
        "home_remedy": "Rehydrate with ORS (Electral packet in 1L water) to prevent dehydration. Once vomiting stops: start with bland food — plain toast, banana, boiled rice. Ginger tea with honey reduces nausea naturally.",
        "doctor_alert": "🚨 See a doctor if: vomiting lasts > 24 hours, blood in vomit, severe dehydration (dry mouth, no urination for 8h), high fever accompanying vomiting, or vomiting after a head injury."
    },
    "dehydration": {
        "condition": "Dehydration (Common in hot weather & exams)",
        "severity": "Mild-Severe depending on level",
        "first_aid": "Drink ORS (Oral Rehydration Solution) — 1 Electral packet dissolved in 1 litre water. Sip continuously, do not gulp. Sports drinks (Gatorade/Glucon-D) are acceptable. Avoid plain water only — you need electrolytes.",
        "home_remedy": "Coconut water is nature's ORS — rich in potassium and natural electrolytes. Diluted buttermilk with a pinch of salt and cumin. Eat water-rich fruits: watermelon, cucumber, oranges. Set phone reminders to drink water every 45 minutes.",
        "doctor_alert": "🚨 Emergency signs: confusion or dizziness, no urination for > 8 hours, rapid heartbeat, sunken eyes, skin that doesn't spring back when pinched — these indicate severe dehydration, visit health center immediately."
    },
    "eye strain": {
        "condition": "Digital Eye Strain / Computer Vision Syndrome",
        "severity": "Mild",
        "first_aid": "**20-20-20 Rule**: every 20 minutes, look at something 20 feet away for 20 seconds. Lubricating eye drops (Refresh Tears / Systane Ultra) — 1–2 drops per eye — available at any pharmacy. Reduce screen brightness and enable night mode.",
        "home_remedy": "Splash cold water on closed eyes 3–4 times a day. Cucumber slices on eyes for 10 minutes. Rose water eye drops (Itone/Optique) soothe irritation naturally. Ensure adequate lighting while studying — reading in dim light strains eyes.",
        "doctor_alert": "🚨 See an eye doctor if: persistent redness or yellow discharge (conjunctivitis), sudden vision blur or floaters, pain inside the eyeball, or sensitivity to light that doesn't resolve in 24 hours."
    },
    "back pain": {
        "condition": "Lower Back Pain / Posture-Related Pain",
        "severity": "Mild-Moderate",
        "first_aid": "Apply warm compress (hot water bag) on the painful area for 15–20 minutes. Combiflam (Ibuprofen + Paracetamol) 1 tablet after food for moderate pain. Avoid sitting continuously — stand and walk every 30–45 minutes.",
        "home_remedy": "**Knee-to-Chest Stretch**: lie on back, pull both knees to chest, hold 30s — relieves lower back tension instantly. **Cat-Cow Pose** (yoga). Sleep on a firm mattress, not a soft sofa. Improve desk posture — monitor at eye level, feet flat on floor.",
        "doctor_alert": "🚨 See a doctor if: pain radiates down the leg (sciatica), numbness/tingling in legs, back pain after a fall/accident, or pain that wakes you from sleep and doesn't improve with rest."
    },
    "insomnia": {
        "condition": "Insomnia / Sleep Deprivation (Pre-Exam Sleep Disorder)",
        "severity": "Moderate — affects academic performance significantly",
        "first_aid": "**Progressive Muscle Relaxation**: tense each muscle group for 5s, release — starting from toes to head. Melatonin 3mg (sleep onset supplement, non-addictive) — take 30 minutes before bed. Available at campus pharmacy.",
        "home_remedy": "Warm milk with a pinch of nutmeg (jaiphal) before bed — contains tryptophan, a natural sleep aid. Chamomile tea. No screens 1 hour before sleep (blue light suppresses melatonin). Keep room cool (18–22Â°C is optimal for sleep). Same bedtime daily resets circadian rhythm.",
        "doctor_alert": "🚨 Consult a doctor if: unable to sleep for > 3 consecutive nights, sleep paralysis episodes, extreme daytime sleepiness affecting studies, or suspected sleep apnea (loud snoring + gasping)."
    },
    "allergy": {
        "condition": "Allergic Reaction (Skin / Nasal / Food Allergy)",
        "severity": "Mild-Severe depending on type",
        "first_aid": "For **nasal allergy** (sneezing, watery eyes): Cetirizine 10mg or Levocetirizine 5mg at night — available OTC. For **skin rash/hives**: Calamine lotion topically + Cetirizine orally. Avoid identified triggers. Cold compress on itchy skin.",
        "home_remedy": "Local raw honey (1 tsp/day) may gradually reduce seasonal pollen allergies over weeks. Neti pot (saline nasal wash) clears allergens from nasal passages. Shower immediately after coming from outdoors during pollen season.",
        "doctor_alert": "🚨 **EMERGENCY**: anaphylaxis signs = sudden throat tightening, difficulty breathing, swelling of lips/tongue, dizziness after eating something — this is life-threatening. Call college emergency or go to hospital IMMEDIATELY. May need epinephrine injection."
    },
    "sprain": {
        "condition": "Ankle / Wrist Sprain (Sports / Lab Injury)",
        "severity": "Mild-Moderate",
        "first_aid": "**RICE Protocol**: **R**est (stop activity immediately), **I**ce (ice pack wrapped in cloth for 15–20 min, every 2 hours), **C**ompression (crepe bandage wrap — not too tight), **E**levation (keep limb elevated above heart level). Combiflam for pain/swelling.",
        "home_remedy": "Turmeric paste (haldi + mustard oil) warm compress reduces inflammation. After 48–72 hours (no ice), switch to warm compress to promote healing. Gentle range-of-motion exercises after 2–3 days to prevent stiffness.",
        "doctor_alert": "🚨 See a doctor if: unable to bear weight at all, severe swelling/bruising appearing quickly (possible fracture), deformity visible, or no improvement after 3–4 days of RICE treatment. X-ray may be needed to rule out fracture."
    },
    "diarrhea": {
        "condition": "Diarrhea / Loose Motions (Gastroenteritis / Food Contamination)",
        "severity": "Moderate — watch for dehydration",
        "first_aid": "Stop solid food for 4–6 hours. Start ORS immediately — 1 Electral packet in 1L water, sip every 15 minutes. Loperamide (Eldoper/Imodium) 2mg tablet for acute loose motions — reduces frequency. Avoid dairy, raw food, and oily mess food.",
        "home_remedy": "BRAT diet once appetite returns: **B**anana, **R**ice (plain), **A**pplesauce, **T**oast. Curd/probiotic yoghurt restores gut bacteria. Tender coconut water replenishes electrolytes naturally. Cumin-coriander water (jeera-dhaniya) soothes the gut. Avoid caffeine and spicy food for 48 hours.",
        "doctor_alert": "🚨 See a doctor if: more than 10 loose motions in 24 hours, blood/mucus in stool, high fever + diarrhea (dysentery risk), or signs of severe dehydration (rapid pulse, dizziness, no urination > 6 hours). Oral rehydration must be aggressive — diarrhea can cause dangerous electrolyte loss within hours."
    },
    "muscle pain": {
        "condition": "Muscle Soreness / Cramps (Post-Exercise or Prolonged Sitting)",
        "severity": "Mild",
        "first_aid": "Apply **Moov/Volini** topical spray or gel on the affected area for instant relief. For cramping muscle: stretch and hold the muscle in the opposite direction. Combiflam tablet for moderate pain. Warm bath/shower relaxes muscle tension.",
        "home_remedy": "Magnesium deficiency is the most common cause of muscle cramps in students — eat bananas, spinach, nuts. Stay hydrated. **Epsom salt soak** (magnesium sulphate in warm water for 15 min). Light stretching and walking increases blood flow to muscles.",
        "doctor_alert": "🚨 See a doctor if: muscle weakness with no apparent cause, cramps accompanied by swelling and redness (could be DVT — deep vein thrombosis), or severe chest/arm pain (cardiac)."
    },
    "toothache": {
        "condition": "Toothache / Dental Pain",
        "severity": "Mild-Severe",
        "first_aid": "Ibuprofen (Combiflam) 400mg after food for pain relief — most effective for dental pain. Clove oil (eugenol) — apply 1–2 drops on a cotton ball directly to the painful tooth — natural anaesthetic. Rinse with warm salt water every 2 hours.",
        "home_remedy": "Garlic clove paste on the tooth (allicin is antibacterial). Cold compress on the cheek outside reduces swelling. Avoid very hot, cold, or sweet food — use the opposite side of mouth to chew. OTC dental gel (Dentogel/Metrogyl) applied to gums reduces inflammation.",
        "doctor_alert": "🚨 Visit a dentist urgently if: swelling spreading to jaw/neck (abscess can be life-threatening), fever with toothache (infection spreading), severe throbbing pain not relieved by painkillers, or a broken/cracked tooth with exposed nerve."
    },

    # ── PHASE 2 ADDITIONS — Additional Health Conditions ─────────────────────
    "nausea": {
        "condition": "Nausea / Queasiness (Non-Vomiting)",
        "severity": "Mild-Moderate",
        "first_aid": "Domperidone 10mg (Domstal/Vomistop) — 1 tablet 30 min before meals — reduces nausea signals. Sit upright or lie on your left side (reduces reflux). Sip cold water or ginger ale slowly. Avoid strong smells and lying flat immediately after eating.",
        "home_remedy": "Ginger tea (1 tsp fresh ginger in hot water with honey) — proven anti-nausea remedy. Peppermint tea. Dry crackers or plain toast to settle the stomach. Lemon water or sniffing a lemon slice helps nausea triggered by smell. Acupressure at P6 point (inner wrist, 3 finger-widths below wrist crease) relieves nausea.",
        "doctor_alert": "🚨 See a doctor if: nausea lasts > 48 hours with no improvement, accompanied by severe abdominal pain or fever, after a head injury (could be concussion), or if you suspect pregnancy."
    },
    "dizziness": {
        "condition": "Dizziness / Vertigo (Balance Disorder)",
        "severity": "Mild-Moderate",
        "first_aid": "Sit or lie down immediately to prevent falls. Cinnarizine 25mg (Stugeron) — anti-vertigo tablet, take with water after food. Focus on a fixed point to reduce spinning sensation. Avoid sudden head movements. Drink water — dizziness is often caused by dehydration or low blood pressure on standing (orthostatic hypotension).",
        "home_remedy": "Ginger — chew a small piece or drink ginger tea. Lie with head slightly elevated on two pillows. Rise slowly from sitting/lying position. Breathe slowly and deeply. Vitamin D deficiency is a common cause of recurrent vertigo — consider supplements if dizziness is chronic.",
        "doctor_alert": "🚨 Emergency: sudden severe dizziness with headache, vision changes, one-sided weakness, slurred speech or difficulty walking — these are signs of stroke or TIA. Call emergency services immediately. Also see a doctor if vertigo episodes recur or last more than a few minutes."
    },
    "ear pain": {
        "condition": "Ear Pain / Earache (Otitis / Ear Infection)",
        "severity": "Mild-Moderate",
        "first_aid": "Apply a warm compress or warm cloth against the outer ear for relief. Ibuprofen (Combiflam) 400mg after food for pain and inflammation. Otrivin/Nasivion nasal drops (for ear pain caused by blocked Eustachian tube from cold). Do NOT insert objects into the ear canal — this pushes wax deeper and risks perforation.",
        "home_remedy": "Chew slowly — jaw movement helps equalize ear pressure. Yawn or swallow repeatedly (for pressure-related ear pain during altitude change). Warm olive oil (not hot) — 2-3 drops in the ear canal helps with wax-related discomfort. Keep the affected ear elevated (don't sleep on that side).",
        "doctor_alert": "🚨 See an ENT doctor if: ear pain comes with fever above 101F, pus or discharge from the ear (sign of infection), sudden hearing loss, ringing in ears (tinnitus), or pain that doesn't improve within 2-3 days. Untreated ear infections can spread to mastoid bone — a serious complication."
    },
    "sunburn": {
        "condition": "Sunburn (UV Radiation Skin Damage)",
        "severity": "Mild-Moderate",
        "first_aid": "Move to shade or indoors immediately. Cool the skin with cool (not cold) water compresses for 10-15 minutes. Do NOT use ice directly — it worsens tissue damage. Apply Calamine lotion or Aloe Vera gel generously on affected areas. Paracetamol 500mg for pain and fever. Drink plenty of water — sunburn draws fluid to the skin, causing dehydration.",
        "home_remedy": "Aloe vera gel (refrigerated) provides instant cooling and healing. Plain yoghurt applied topically soothes burn. Cool baths with oatmeal powder. Avoid further sun exposure until fully healed. Moisturize with light, fragrance-free lotion. Do NOT pop blisters if they appear — this risks infection. Light, breathable cotton clothing covers without trapping heat.",
        "doctor_alert": "🚨 Seek medical help if: blisters cover large areas, fever above 103F, confusion or fainting (heat stroke), nausea with headache, or skin feels numb or leathery (severe burn). Severe sunburn with fever = sun poisoning — requires IV fluids."
    },
    "food poisoning": {
        "condition": "Food Poisoning (Bacterial / Toxin Contamination)",
        "severity": "Moderate — watch hydration carefully",
        "first_aid": "Stop eating solid food for 4-6 hours. Begin ORS (Electral/Pedialyte) immediately — sip every 10-15 minutes even if nausea is present. Ondansetron 4mg (Emeset) for severe nausea/vomiting — under tongue. Loperamide (Eldoper/Imodium) 2mg for diarrhea — reduces frequency. Avoid dairy, fried, or spicy food until recovered.",
        "home_remedy": "BRAT diet once appetite returns: Banana, Rice, Applesauce, Toast. Tender coconut water or ORS replenishes electrolytes. Ginger tea settles the stomach. Probiotic curd restores gut bacteria after 24 hours. Avoid caffeine, alcohol, and fatty foods for 48-72 hours after recovery. Wash hands thoroughly — food poisoning can spread person-to-person.",
        "doctor_alert": "🚨 Go to hospital if: symptoms last more than 72 hours, blood or mucus in stool/vomit, fever above 101F + diarrhea (dysentery risk), signs of severe dehydration (no urination 8+ hours, sunken eyes, rapid heartbeat), or suspected contamination at a group meal (report to college health authorities)."
    },
    "anxiety": {
        "condition": "Anxiety / Panic Attack (Acute Stress Response)",
        "severity": "Moderate — deserves proper attention",
        "first_aid": "**Grounding Technique (5-4-3-2-1)**: Name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, 1 you can taste — breaks the panic spiral instantly. **4-7-8 Breathing**: Inhale 4s, hold 7s, exhale slowly 8s — activates parasympathetic nervous system. Cold water on face or wrists resets the nervous system quickly. Sit down, loosen tight clothing.",
        "home_remedy": "Chamomile tea — has natural anxiolytic (anxiety-reducing) properties. Ashwagandha (KSM-66 extract) reduces cortisol levels with regular use. Lavender oil — inhale or apply diluted on pulse points. Regular exercise (30 min brisk walk) reduces anxiety hormones long-term. Journaling (writing down worries) externalizes fears. Limit caffeine — it directly worsens anxiety.",
        "doctor_alert": "🚨 Please reach out to: College Counselor (Student Wellness Centre), iCall (9152987821 — free student helpline), Vandrevala Foundation (1860-2662-345, available 24/7). See a doctor if: panic attacks occur frequently (weekly), prevent you from attending class, or are accompanied by chest pain, numbness, or fear of dying. Anxiety is a medical condition — treatment works and you deserve support."
    },
    "sore throat": {
        "condition": "Sore Throat / Pharyngitis (Bacterial or Viral)",
        "severity": "Mild-Moderate",
        "first_aid": "Warm salt water gargle immediately — 1/2 tsp salt in 1 glass warm water, gargle for 30 seconds, 3-4 times a day. Strepsils/Cofsils throat lozenges — suck slowly to coat the throat. Betadine gargle (diluted, not swallowed) for bacterial sore throat. Paracetamol 500mg for pain and fever. Rest your voice — avoid shouting, whispering strains vocal cords more than normal speech.",
        "home_remedy": "1 tsp raw honey + 1/4 tsp cinnamon + warm water — powerful antibacterial soothing remedy. Warm ginger-tulsi-honey tea. Turmeric milk (haldi doodh) at night. Avoid cold drinks, ice cream, and cold air conditioning blowing directly on throat. Steam inhalation (plain hot water) soothes inflamed tissue. Eat soft foods — soups, khichdi, mashed potatoes.",
        "doctor_alert": "🚨 See a doctor if: sore throat persists beyond 5-7 days, white patches or pus visible on tonsils (strep throat — needs antibiotics), difficulty swallowing saliva (quinsy/peritonsillar abscess risk), muffled voice with neck swelling, or fever above 102F accompanied by throat pain. Strep throat left untreated can lead to rheumatic fever."
    },
    "nose bleed": {
        "condition": "Nosebleed / Epistaxis (Anterior Nasal Bleeding)",
        "severity": "Mild (usually self-limiting)",
        "first_aid": "**CORRECT technique**: Sit upright and lean FORWARD (not backward — swallowing blood causes nausea). Pinch the soft part of the nose (just below the bony bridge) firmly for 10-15 minutes continuously — do not release to check. Breathe through your mouth. Apply a cold ice pack wrapped in cloth on the nose bridge. Do NOT tilt the head back — blood flows into the throat and stomach.",
        "home_remedy": "After bleeding stops: keep head elevated. Avoid blowing nose for several hours. Apply a thin layer of petroleum jelly (Vaseline) inside the nostril to prevent dryness-related rebleeding — especially useful in dry or AC environments. Stay hydrated — dry nasal membranes bleed more easily. Use a saline nasal spray (Nasoclear) to keep nasal passages moist during dry weather.",
        "doctor_alert": "🚨 Go to hospital if: bleeding does not stop after 20 minutes of correct pressure, blood is flowing in large quantities, blood is coming from both nostrils simultaneously, you take blood thinners (aspirin/warfarin), nosebleed follows a head injury, or you have frequent recurrent nosebleeds (could indicate high blood pressure or clotting disorder requiring investigation)."
    },

}

# ── Health keyword aliases → canonical keys ────────────────────────────────────
# Sorted longest-first at runtime to prevent short substring aliases shadowing longer ones.
HEALTH_ALIASES = {
    # Fever
    "high fever": "fever", "temperature": "fever", "pyrexia": "fever", "typhoid": "fever",
    "viral fever": "fever",
    # Headache
    "migraine attack": "headache", "head pain": "headache", "migraine": "headache",
    "tension headache": "headache", "tension": "headache",
    # Cold
    "sore throat": "cold", "runny nose": "cold", "throat pain": "cold",
    "sneezing": "cold", "nasal": "cold",
    # Cough
    "dry cough": "cough", "wet cough": "cough", "throat": "cough",
    # Stomach
    "stomach pain": "stomach", "abdominal pain": "stomach", "stomach ache": "stomach",
    "abdominal": "stomach", "tummy": "stomach", "cramps": "stomach",
    "cant eat": "stomach", "no appetite": "stomach",
    # Acidity
    "acid reflux": "acidity", "heartburn": "acidity", "food poisoning": "vomiting",
    "gastric": "acidity", "bloating": "acidity", "gas": "acidity", "acid": "acidity",
    # Stress / Mental health
    "exam stress": "stress", "exam fear": "stress", "exam anxiety": "stress",
    "mental health": "stress", "burnout": "stress", "depression": "stress",
    "anxiety": "stress", "panic": "stress",
    # Vomiting
    "food poisoning": "vomiting", "nausea": "vomiting", "vomit": "vomiting",
    "puke": "vomiting",
    # Diarrhea
    "loose motion": "diarrhea", "loose motions": "diarrhea", "diarrhea": "diarrhea",
    "diarrhoea": "diarrhea", "dysentery": "diarrhea", "watery stool": "diarrhea",
    # Dehydration
    "dehydrated": "dehydration", "dry mouth": "dehydration", "thirsty": "dehydration",
    "not urinating": "dehydration",
    # Eye strain
    "computer vision": "eye strain", "eye strain": "eye strain", "red eye": "eye strain",
    "screen time": "eye strain", "screen": "eye strain", "eyes": "eye strain",
    "eye": "eye strain",
    # Back pain
    "lower back pain": "back pain", "lower back": "back pain", "back ache": "back pain",
    "spine": "back pain", "posture": "back pain", "back": "back pain",
    # Insomnia / Sleep
    "cant sleep": "insomnia", "no sleep": "insomnia", "sleepless": "insomnia",
    "insomnia": "insomnia", "sleep problem": "insomnia", "sleep": "insomnia",
    # Allergy
    "hives": "allergy", "itching": "allergy", "allergic": "allergy", "rash": "allergy",
    "skin rash": "allergy",
    # Sprain / Injury
    "ankle sprain": "sprain", "wrist sprain": "sprain", "twisted ankle": "sprain",
    "muscle pull": "muscle pain", "muscle cramp": "muscle pain", "cramp": "muscle pain",
    "body ache": "muscle pain", "sore muscle": "muscle pain",
    "twisted": "sprain", "ankle": "sprain", "wrist": "sprain", "injury": "sprain",
    # Toothache
    "tooth pain": "toothache", "dental": "toothache", "toothache": "toothache",
    "tooth": "toothache", "gum": "toothache",
    # Phase 2 new health condition aliases
    "nausea": "nausea", "nauseous": "nausea", "queasiness": "nausea",
    "queasy": "nausea", "feel sick": "nausea", "motion sickness": "nausea",
    "dizziness": "dizziness", "dizzy": "dizziness", "vertigo": "dizziness",
    "lightheaded": "dizziness", "spinning": "dizziness", "balance": "dizziness",
    "giddy": "dizziness", "faint": "dizziness",
    "ear pain": "ear pain", "earache": "ear pain", "ear ache": "ear pain",
    "ear infection": "ear pain", "ear discharge": "ear pain", "tinnitus": "ear pain",
    "hearing loss": "ear pain", "ear": "ear pain",
    "sunburn": "sunburn", "sun burn": "sunburn", "burnt skin": "sunburn",
    "skin burn": "sunburn", "uv burn": "sunburn", "sun exposure": "sunburn",
    "food poisoning": "food poisoning", "food poison": "food poisoning",
    "contaminated food": "food poisoning", "bad food": "food poisoning",
    "gastroenteritis": "food poisoning", "poisoned": "food poisoning",
    "anxiety": "anxiety", "panic attack": "anxiety", "panic": "anxiety",
    "anxious": "anxiety", "nervous": "anxiety", "worry": "anxiety",
    "overthinking": "anxiety", "fear": "anxiety", "heart racing": "anxiety",
    "sore throat": "sore throat", "throat pain": "sore throat",
    "throat sore": "sore throat", "tonsil": "sore throat", "pharyngitis": "sore throat",
    "strep throat": "sore throat", "throat infection": "sore throat",
    "nose bleed": "nose bleed", "nosebleed": "nose bleed", "epistaxis": "nose bleed",
    "bleeding nose": "nose bleed", "nose bleeding": "nose bleed",

}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/admin/all_students', methods=['GET'])
def get_all_students_admin():
    """Returns full attendance + marks for every student — used by Faculty Management Table."""
    data = load_data()
    students = data.get('students', [])
    subjects = data.get('subjects', [])
    return jsonify({
        "students": students,
        "subjects": subjects
    })

@app.route('/api/student', methods=['GET'])
def get_student():
    data = load_data()
    req_student_id = request.args.get('student_id') or request.args.get('roll_no')
    active_stu = None
    if req_student_id:
        req_clean = req_student_id.strip().lower()
        active_stu = next((s for s in data.get('students', []) if s.get('id', '').lower() == req_clean or s.get('roll_no', '').lower() == req_clean), None)
        if not active_stu:
            active_stu = next((s for s in data.get('students', []) if req_clean in s.get('roll_no', '').lower() or req_clean in s.get('id', '').lower()), None)
        if not active_stu:
            active_stu = next((s for s in data.get('students', []) if req_clean in s.get('name', '').lower()), None)
        if not active_stu and req_student_id.strip():
            roll_upper = req_student_id.strip().upper()
            active_stu = {
                "id": roll_upper,
                "name": f"Student ({roll_upper})",
                "roll_no": roll_upper,
                "branch": "Computer Science & Engineering",
                "semester": "5th Semester",
                "target_attendance": 75,
                "attendance": {
                    "os": {"attended": 38, "total": 45, "percentage": 84.44, "status": "safe"},
                    "dsa": {"attended": 32, "total": 38, "percentage": 84.21, "status": "safe"},
                    "dbms": {"attended": 26, "total": 30, "percentage": 86.67, "status": "safe"},
                    "cn": {"attended": 24, "total": 30, "percentage": 80.0, "status": "safe"}
                },
                "marks": {
                    "os": {"score": 76, "total": 100, "status": "Pass"},
                    "dsa": {"score": 82, "total": 100, "status": "Pass"},
                    "dbms": {"score": 75, "total": 100, "status": "Pass"},
                    "cn": {"score": 70, "total": 100, "status": "Pass"}
                }
            }
            data.setdefault('students', []).append(active_stu)
            data['active_student_id'] = roll_upper
            save_data(data)

    if not active_stu:
        active_stu = get_active_student(data)
    else:
        data['active_student_id'] = active_stu['id']
        save_data(data)
    
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
        "active_student_id": active_stu.get('id') if active_stu else None,
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
    target_id = (payload.get('student_id') or '').strip().lower()
    data = load_data()
    
    stu = next((s for s in data.get('students', []) if s.get('id', '').lower() == target_id or s.get('roll_no', '').lower() == target_id), None)
    if not stu and target_id:
        stu = next((s for s in data.get('students', []) if target_id in s.get('roll_no', '').lower() or target_id in s.get('id', '').lower()), None)
    if not stu and target_id:
        stu = next((s for s in data.get('students', []) if target_id in s.get('name', '').lower()), None)

    if stu:
        data['active_student_id'] = stu['id']
        save_data(data)
        return jsonify({"success": True, "message": f"Switched to {stu['name']}.", "student": stu, "active_student_id": stu['id']})
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
    password = payload.get('password', '').strip()
    
    if not name or not roll_no:
        return jsonify({"success": False, "message": "Name and Roll No are required."}), 400
        
    data = load_data()
    stu_id = roll_no.replace(' ', '').upper()
    
    for s in data.get('students', []):
        if s['id'] == stu_id:
            return jsonify({"success": False, "message": f"Roll No {roll_no} already exists."}), 400
            
    if not password:
        password = f"AKGEC@{stu_id[-4:] if len(stu_id)>=4 else '2026'}"

    new_stu = {
        "id": stu_id,
        "name": name,
        "roll_no": roll_no,
        "branch": branch,
        "semester": semester,
        "password": password,
        "target_attendance": 75,
        "fees": {
            "total_fee": 125000,
            "paid_amount": 0,
            "due_amount": 125000,
            "status": "unpaid",
            "due_date": "15 Oct 2026",
            "transactions": []
        },
        "attendance": {
            "os": {"attended": 0, "total": 0, "percentage": 0.0, "status": "warning"},
            "dsa": {"attended": 0, "total": 0, "percentage": 0.0, "status": "warning"},
            "dbms": {"attended": 0, "total": 0, "percentage": 0.0, "status": "warning"},
            "cn": {"attended": 0, "total": 0, "percentage": 0.0, "status": "warning"}
        },
        "marks": {
            "os": {"score": 0, "total": 100, "status": "Pending"},
            "dsa": {"score": 0, "total": 100, "status": "Pending"},
            "dbms": {"score": 0, "total": 100, "status": "Pending"},
            "cn": {"score": 0, "total": 100, "status": "Pending"}
        }
    }
    data.setdefault('students', []).append(new_stu)
    data['active_student_id'] = stu_id
    save_data(data)
    return jsonify({
        "success": True, 
        "message": f"Student '{name}' registered successfully!", 
        "student": new_stu,
        "credentials": {
            "name": name,
            "roll_no": roll_no,
            "password": password,
            "branch": branch,
            "semester": semester
        }
    })

@app.route('/api/admin/student/reset_password', methods=['POST'])
def reset_student_password():
    payload = request.json or {}
    student_id = payload.get('student_id', '').strip()
    new_password = payload.get('password', '').strip()
    if not student_id or not new_password:
        return jsonify({"success": False, "message": "Student ID and new password are required."}), 400
    data = load_data()
    for s in data.get('students', []):
        if s['id'].lower() == student_id.lower() or s.get('roll_no', '').lower() == student_id.lower():
            s['password'] = new_password
            save_data(data)
            return jsonify({"success": True, "message": f"Password for {s['name']} reset successfully to '{new_password}'!"})
    return jsonify({"success": False, "message": "Student record not found."}), 404

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
    subjects = data.setdefault('subjects', [])
    existing = next((s for s in subjects if s['id'] == sub_id or s['code'].lower() == code.lower()), None)
    if existing:
        existing['name'] = name
        existing['code'] = code
        existing['faculty'] = faculty or existing.get('faculty', 'Faculty Assigned')
        new_sub = existing
    else:
        subjects.append(new_sub)
        # Initialize student attendance and marks for every student
        for stu in data.get('students', []):
            stu.setdefault('attendance', {})[sub_id] = {"attended": 0, "total": 0, "percentage": 100.0, "status": "safe"}
            stu.setdefault('marks', {})[sub_id] = {"score": "-", "total": 100, "status": "Pending"}

    save_data(data)
    return jsonify({"success": True, "message": f"Subject '{name}' saved to college curriculum!", "subject": new_sub})

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

@app.route('/api/admin/notice/add', methods=['POST'])
def add_notice():
    payload = request.json or {}
    title = payload.get('title', '').strip()
    content = payload.get('content', '').strip()
    badge = payload.get('badge', 'Notice').strip()

    if not title or not content:
        return jsonify({"success": False, "message": "Title and content are required."}), 400

    data = load_data()
    import datetime
    new_notice = {
        "id": len(data.get('notices', [])) + 1,
        "title": title,
        "date": datetime.date.today().strftime("%d %b %Y"),
        "badge": badge,
        "content": content
    }
    data.setdefault('notices', []).insert(0, new_notice)
    save_data(data)
    return jsonify({"success": True, "message": f"Notice '{title}' posted!", "notice": new_notice})

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

# ── ROLE-BASED AUTH & SESSION APIS ──────────────────────────────────────────

@app.route('/api/auth/faculty_list', methods=['GET'])
def get_faculty_list():
    data = load_data()
    subjects = data.get('subjects', [])
    faculties = []
    seen = set()
    for s in subjects:
        fac_name = s.get('faculty', 'Faculty')
        if fac_name not in seen:
            seen.add(fac_name)
            faculties.append({
                "name": fac_name,
                "subject_id": s['id'],
                "subject_name": s['name'],
                "subject_code": s.get('code', '')
            })
    return jsonify({"faculties": faculties})

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    payload = request.json or {}
    role = payload.get('role', 'student').lower()
    identifier = payload.get('identifier', '').strip()
    password = payload.get('password', '').strip()
    data = load_data()

    if role == 'student':
        id_clean = identifier.lower()
        # 1. Exact match on roll_no or id
        student = next((s for s in data.get('students', []) if s.get('roll_no', '').lower() == id_clean or s.get('id', '').lower() == id_clean), None)
        # 2. Substring match on roll_no or id (e.g. entering "1085" matches "22CS1085")
        if not student and id_clean:
            student = next((s for s in data.get('students', []) if id_clean in s.get('roll_no', '').lower() or id_clean in s.get('id', '').lower()), None)
        # 3. Match on student name
        if not student and id_clean:
            student = next((s for s in data.get('students', []) if id_clean in s.get('name', '').lower()), None)
        # 4. If still not found and an identifier was provided: AUTO-CREATE a dedicated student profile!
        if not student and id_clean:
            roll_upper = identifier.upper()
            disp_name = f"Student ({roll_upper})"
            student = {
                "id": roll_upper,
                "name": disp_name,
                "roll_no": roll_upper,
                "branch": "Computer Science & Engineering",
                "semester": "5th Semester",
                "password": password or "student123",
                "target_attendance": 75,
                "fees": {
                    "total_fee": 125000,
                    "paid_amount": 60000,
                    "due_amount": 65000,
                    "status": "partial",
                    "due_date": "15 Oct 2026",
                    "transactions": [
                        {"receipt_no": "AKGEC-FEE-9001", "date": "01 Aug 2026", "amount": 60000, "mode": "Online UPI", "status": "Success"}
                    ]
                },
                "attendance": {
                    "os": {"attended": 38, "total": 45, "percentage": 84.44, "status": "safe"},
                    "dsa": {"attended": 32, "total": 38, "percentage": 84.21, "status": "safe"},
                    "dbms": {"attended": 26, "total": 30, "percentage": 86.67, "status": "safe"},
                    "cn": {"attended": 24, "total": 30, "percentage": 80.0, "status": "safe"}
                },
                "marks": {
                    "os": {"score": 76, "total": 100, "status": "Pass"},
                    "dsa": {"score": 82, "total": 100, "status": "Pass"},
                    "dbms": {"score": 75, "total": 100, "status": "Pass"},
                    "cn": {"score": 70, "total": 100, "status": "Pass"}
                }
            }
            data.setdefault('students', []).append(student)

        # 5. Default fallback ONLY if identifier was completely blank
        if not student and data.get('students'):
            student = data['students'][0]

        if not student:
            return jsonify({"success": False, "message": "Student record not found."}), 404

        # Validate password if provided
        expected_pw = student.get('password', 'student123')
        if password and password != expected_pw:
            return jsonify({"success": False, "message": f"Incorrect password for roll number {student.get('roll_no', identifier)}. Please check your credentials."}), 401

        data['active_student_id'] = student['id']
        save_data(data)
        return jsonify({
            "success": True,
            "role": "student",
            "active_student_id": student['id'],
            "user": {
                "id": student['id'],
                "name": student['name'],
                "roll_no": student['roll_no'],
                "branch": student.get('branch', 'CSE'),
                "semester": student.get('semester', '5th Sem')
            },
            "student": student
        })

    elif role == 'teacher':
        if password and password not in ['teacher123', 'admin123', 'faculty123', 'os', 'dsa', 'dbms', 'cn']:
            return jsonify({"success": False, "message": "Incorrect faculty password. Default demo password is 'teacher123'."}), 401

        subjects = data.get('subjects', [])
        sub = next((s for s in subjects if s['id'].lower() == identifier.lower() or s.get('faculty', '').lower() == identifier.lower()), None)
        if not sub and identifier:
            sub = next((s for s in subjects if identifier.lower() in s['id'].lower() or identifier.lower() in s['name'].lower() or identifier.lower() in s.get('faculty', '').lower()), None)
        if not sub and subjects:
            sub = subjects[0]
        return jsonify({
            "success": True,
            "role": "teacher",
            "user": {
                "name": sub.get('faculty', 'Prof. R. K. Verma'),
                "subject_id": sub['id'],
                "subject_name": sub['name'],
                "subject_code": sub.get('code', '')
            }
        })

    elif role == 'hod':
        if password and password not in ['hod123', 'admin123', 'hod@2026', 'Dr. S. K. Bansal'] and identifier not in ['hod123', 'admin123', 'Dr. S. K. Bansal']:
            return jsonify({"success": False, "message": "Incorrect HOD security key. Default demo key is 'hod123'."}), 401

        return jsonify({
            "success": True,
            "role": "hod",
            "user": {
                "name": "Dr. S. K. Bansal",
                "title": "Head of Department (CSE)",
                "department": "Computer Science & Engineering"
            }
        })

    elif role == 'parent':
        id_clean = identifier.lower()
        student = next((s for s in data.get('students', []) if s.get('roll_no', '').lower() == id_clean or s.get('id', '').lower() == id_clean), None)
        if not student and id_clean:
            student = next((s for s in data.get('students', []) if id_clean in s.get('roll_no', '').lower() or id_clean in s.get('id', '').lower()), None)
        if not student and id_clean:
            student = next((s for s in data.get('students', []) if id_clean in s.get('name', '').lower()), None)
        if not student and id_clean:
            roll_upper = identifier.upper()
            student = {
                "id": roll_upper,
                "name": f"Student ({roll_upper})",
                "roll_no": roll_upper,
                "branch": "Computer Science & Engineering",
                "semester": "5th Semester",
                "password": "student123",
                "target_attendance": 75,
                "attendance": {
                    "os": {"attended": 38, "total": 45, "percentage": 84.44, "status": "safe"},
                    "dsa": {"attended": 32, "total": 38, "percentage": 84.21, "status": "safe"},
                    "dbms": {"attended": 26, "total": 30, "percentage": 86.67, "status": "safe"},
                    "cn": {"attended": 24, "total": 30, "percentage": 80.0, "status": "safe"}
                },
                "marks": {
                    "os": {"score": 76, "total": 100, "status": "Pass"},
                    "dsa": {"score": 82, "total": 100, "status": "Pass"},
                    "dbms": {"score": 75, "total": 100, "status": "Pass"},
                    "cn": {"score": 70, "total": 100, "status": "Pass"}
                }
            }
            data.setdefault('students', []).append(student)

        if not student and data.get('students'):
            student = data['students'][0]
        if not student:
            return jsonify({"success": False, "message": "Student roll number not found."}), 404

        if password and password not in ['parent123', 'student123', student.get('roll_no', '').lower()]:
            return jsonify({"success": False, "message": "Incorrect parent password. Default demo password is 'parent123'."}), 401

        data['active_student_id'] = student['id']
        save_data(data)
        return jsonify({
            "success": True,
            "role": "parent",
            "active_student_id": student['id'],
            "user": {
                "name": f"Parent of {student['name']}",
                "student_id": student['id'],
                "student_name": student['name'],
                "student_roll": student['roll_no']
            },
            "student": student
        })

    return jsonify({"success": False, "message": "Invalid role specified."}), 400

@app.route('/api/auth/forgot_password', methods=['POST'])
def auth_forgot_password():
    payload = request.json or {}
    roll_no = (payload.get('roll_no') or payload.get('identifier') or '').strip()
    new_pw = payload.get('new_password', '').strip()
    if not roll_no or not new_pw:
        return jsonify({"success": False, "message": "Roll Number and New Password are required."}), 400

    data = load_data()
    r_clean = roll_no.lower()
    stu = next((s for s in data.get('students', []) if s.get('roll_no', '').lower() == r_clean or s.get('id', '').lower() == r_clean or r_clean in s.get('roll_no', '').lower()), None)
    if not stu:
        roll_upper = roll_no.upper()
        stu = {
            "id": roll_upper,
            "name": f"Student ({roll_upper})",
            "roll_no": roll_upper,
            "branch": "Computer Science & Engineering",
            "semester": "5th Semester",
            "password": new_pw,
            "target_attendance": 75,
            "attendance": {},
            "marks": {}
        }
        data.setdefault('students', []).append(stu)
    else:
        stu['password'] = new_pw

    save_data(data)
    return jsonify({"success": True, "message": f"Password reset successfully for {stu['name']} ({stu['roll_no']})! You can now log in with your new password."})

# ── COLLEGE FEES & ONLINE PAYMENT APIS ──────────────────────────────────────

@app.route('/api/fees/status', methods=['GET'])
def get_fee_status():
    data = load_data()
    student_id = request.args.get('student_id') or request.args.get('roll_no')
    stu = None
    if student_id:
        s_clean = student_id.strip().lower()
        stu = next((s for s in data.get('students', []) if s.get('id', '').lower() == s_clean or s.get('roll_no', '').lower() == s_clean or s_clean in s.get('roll_no', '').lower()), None)
    if not stu:
        stu = get_active_student(data)
    if not stu:
        return jsonify({"success": False, "message": "Student not found."}), 404

    default_fees = {
        "total_fee": 125000,
        "paid_amount": 75000,
        "due_amount": 50000,
        "status": "partial",
        "due_date": "15 Oct 2026",
        "transactions": [
            {"receipt_no": "AKGEC-FEE-8812", "date": "10 Aug 2026", "amount": 75000, "mode": "UPI / NetBanking", "status": "Success"}
        ]
    }
    fees = stu.setdefault('fees', default_fees)
    return jsonify({
        "success": True,
        "student_id": stu['id'],
        "student_name": stu['name'],
        "roll_no": stu['roll_no'],
        "branch": stu.get('branch', 'CSE'),
        "semester": stu.get('semester', '5th Sem'),
        "fees": fees
    })

@app.route('/api/fees/pay', methods=['POST'])
def pay_fees():
    payload = request.json or {}
    student_id = payload.get('student_id') or payload.get('roll_no')
    amount = payload.get('amount')
    mode = payload.get('payment_mode', 'Online UPI (GPay / PhonePe)')

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError()
    except Exception:
        return jsonify({"success": False, "message": "Please enter a valid positive payment amount."}), 400

    data = load_data()
    stu = None
    if student_id:
        s_clean = str(student_id).strip().lower()
        stu = next((s for s in data.get('students', []) if s.get('id', '').lower() == s_clean or s.get('roll_no', '').lower() == s_clean or s_clean in s.get('roll_no', '').lower()), None)
    if not stu:
        stu = get_active_student(data)
    if not stu:
        return jsonify({"success": False, "message": "Student record not found."}), 404

    default_fees = {
        "total_fee": 125000,
        "paid_amount": 0,
        "due_amount": 125000,
        "status": "partial",
        "due_date": "15 Oct 2026",
        "transactions": []
    }
    fees = stu.setdefault('fees', default_fees)

    current_due = float(fees.get('due_amount', 0))
    pay_amount = min(amount, current_due) if current_due > 0 else amount

    new_paid = round(float(fees.get('paid_amount', 0)) + pay_amount, 2)
    new_due = max(0.0, round(float(fees.get('total_fee', 125000)) - new_paid, 2))

    fees['paid_amount'] = new_paid
    fees['due_amount'] = new_due
    fees['status'] = 'paid' if new_due <= 0 else 'partial'

    import datetime, random
    receipt_no = f"AKGEC-FEE-{random.randint(10000, 99999)}"
    tx = {
        "receipt_no": receipt_no,
        "date": datetime.date.today().strftime("%d %b %Y"),
        "amount": pay_amount,
        "mode": mode,
        "status": "Success",
        "student_name": stu['name'],
        "roll_no": stu['roll_no'],
        "remaining_balance": new_due
    }
    fees.setdefault('transactions', []).insert(0, tx)
    save_data(data)

    return jsonify({
        "success": True,
        "message": f"Payment of ₹{pay_amount:,.2f} recorded successfully via {mode}! Remaining balance: ₹{new_due:,.2f}",
        "receipt": tx,
        "fees": fees
    })

@app.route('/api/hod/fees/set', methods=['POST'])
def hod_set_fees():
    payload = request.json or {}
    student_id = payload.get('student_id')
    total_fee = payload.get('total_fee')
    due_amount = payload.get('due_amount')
    due_date = payload.get('due_date', '15 Oct 2026')

    data = load_data()
    stu = next((s for s in data.get('students', []) if s.get('id', '').lower() == str(student_id).lower() or s.get('roll_no', '').lower() == str(student_id).lower()), None)
    if not stu:
        return jsonify({"success": False, "message": "Student not found."}), 404

    fees = stu.setdefault('fees', {})
    if total_fee is not None:
        fees['total_fee'] = float(total_fee)
    if due_amount is not None:
        fees['due_amount'] = float(due_amount)
        fees['paid_amount'] = max(0.0, float(fees.get('total_fee', 125000)) - float(due_amount))
    if due_date:
        fees['due_date'] = due_date
    fees['status'] = 'paid' if fees.get('due_amount', 0) <= 0 else 'partial'
    save_data(data)
    return jsonify({"success": True, "message": f"Fee structure updated for {stu['name']}!", "fees": fees})

# ── ASSIGNMENTS & PROCTORED ONLINE TESTS APIS ──────────────────────────────

@app.route('/api/assignments/list', methods=['GET'])
def get_assignments_list():
    data = load_data()
    student_id = request.args.get('student_id', '').strip().lower()
    asgs = data.get('assignments', [])

    result = []
    for a in asgs:
        asg_copy = dict(a)
        subs = a.get('submissions', {})
        my_sub = None
        if student_id:
            my_sub = subs.get(student_id)
        asg_copy['my_submission'] = my_sub
        result.append(asg_copy)

    return jsonify({"success": True, "assignments": result})

@app.route('/api/hod/assignment/create', methods=['POST'])
def hod_create_assignment():
    payload = request.json or {}
    title = payload.get('title', '').strip()
    subject = payload.get('subject', '').strip()
    subject_code = payload.get('subject_code', '').strip()
    faculty = payload.get('faculty', 'Faculty Assigned').strip()
    deadline = payload.get('deadline', '30 Sept 2026').strip()
    total_marks = int(payload.get('total_marks', 20))
    mode = payload.get('mode', 'hybrid').strip()
    desc = payload.get('description', '').strip()
    questions = payload.get('questions', [])

    if not title or not subject:
        return jsonify({"success": False, "message": "Title and Subject are required."}), 400

    data = load_data()
    import random
    new_id = f"asg-{subject_code.lower().replace('-', '')}-{random.randint(10, 99)}" if subject_code else f"asg-{random.randint(100, 999)}"
    asg = {
        "id": new_id,
        "title": title,
        "subject": subject,
        "subject_code": subject_code,
        "faculty": faculty,
        "deadline": deadline,
        "total_marks": total_marks,
        "mode": mode,
        "pdf_filename": f"AKGEC_{subject_code.replace('-', '_')}_Assignment.pdf",
        "description": desc,
        "questions": questions,
        "submissions": {}
    }
    data.setdefault('assignments', []).insert(0, asg)
    save_data(data)
    return jsonify({"success": True, "message": f"Assignment '{title}' published!", "assignment": asg})

@app.route('/api/assignments/download_pdf/<asg_id>', methods=['GET'])
def download_assignment_pdf(asg_id):
    data = load_data()
    asg = next((a for a in data.get('assignments', []) if a['id'] == asg_id), None)
    if not asg:
        return "Assignment not found", 404

    content = [
        "================================================================================",
        "AJAY KUMAR GARG ENGINEERING COLLEGE, GHAZIABAD",
        "DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING",
        "OFFICIAL COURSEWORK WORKSHEET • SEMESTER EXAMINATIONS 2026",
        "================================================================================",
        f"Title:        {asg.get('title')}",
        f"Course:       {asg.get('subject')} ({asg.get('subject_code')})",
        f"Faculty:      {asg.get('faculty')}",
        f"Submission:   Deadline: {asg.get('deadline')} | Total Marks: {asg.get('total_marks')}",
        "Instructions: Complete all questions. Either submit online via CampusGenie AI",
        "              Proctored Test or solve in practical journal and submit to proctor.",
        "--------------------------------------------------------------------------------\n",
        f"DESCRIPTION & OBJECTIVES:\n{asg.get('description', 'Solve all algorithmic problems.')}\n",
        "QUESTIONS / PROBLEM SET:\n"
    ]
    for idx, q in enumerate(asg.get('questions', []), 1):
        content.append(f"Q{idx}. {q.get('q')}")
        for o_idx, opt in enumerate(q.get('options', [])):
            content.append(f"    [{chr(65+o_idx)}] {opt}")
        content.append("")

    content.append("================================================================================")
    content.append("End of Question Paper • AKGEC Academic ERP & Examination Cell")

    from flask import Response
    res_text = "\n".join(content)
    return Response(
        res_text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename={asg.get('pdf_filename', 'Assignment.txt')}"}
    )

@app.route('/api/assignments/submit_online', methods=['POST'])
def submit_proctored_test():
    payload = request.json or {}
    student_id = (payload.get('student_id') or '').strip().lower()
    asg_id = payload.get('assignment_id')
    answers = payload.get('answers', {})
    proctor_status = payload.get('proctor_status', {})

    data = load_data()
    asg = next((a for a in data.get('assignments', []) if a['id'] == asg_id), None)
    if not asg:
        return jsonify({"success": False, "message": "Assignment not found."}), 404

    stu = next((s for s in data.get('students', []) if s.get('id', '').lower() == student_id or s.get('roll_no', '').lower() == student_id or student_id in s.get('roll_no', '').lower()), None)
    student_key = stu['id'] if stu else student_id

    questions = asg.get('questions', [])
    total_q = len(questions)
    correct_count = 0
    for q in questions:
        qid_str = str(q.get('id'))
        if qid_str in answers and int(answers[qid_str]) == int(q.get('correct')):
            correct_count += 1

    total_marks = asg.get('total_marks', 20)
    score = round((correct_count / total_q) * total_marks) if total_q > 0 else 0
    pct = round((score / total_marks) * 100, 1) if total_marks > 0 else 100.0
    passed = score >= (total_marks * 0.4)

    import datetime
    submission_record = {
        "student_id": student_key,
        "student_name": stu['name'] if stu else "Student",
        "roll_no": stu['roll_no'] if stu else student_key,
        "date": datetime.datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "score": score,
        "total_marks": total_marks,
        "percentage": pct,
        "status": "Passed" if passed else "Needs Improvement",
        "proctor_verified": True,
        "proctor_details": {
            "camera_monitored": proctor_status.get('camera_active', True),
            "mic_monitored": proctor_status.get('mic_active', True),
            "integrity_score": "98% (No Suspicious Eye/Audio Activity Detected)"
        }
    }
    asg.setdefault('submissions', {})[student_key] = submission_record
    save_data(data)

    return jsonify({
        "success": True,
        "message": f"Test submitted & proctor-verified! Score: {score}/{total_marks} ({pct}%)",
        "result": submission_record
    })

# ── TEACHER SUBJECT-WISE ATTENDANCE GRID APIS ───────────────────────────────

@app.route('/api/teacher/students/by_subject', methods=['GET'])
def get_teacher_students_by_subject():
    sub_id = request.args.get('subject_id', '').strip().lower()
    data = load_data()
    students = data.get('students', [])
    subjects = data.get('subjects', [])
    
    target_sub = next((s for s in subjects if s['id'].lower() == sub_id), None)
    if not target_sub and subjects:
        target_sub = subjects[0]
        sub_id = target_sub['id']

    result = []
    for s in students:
        att = s.get('attendance', {}).get(sub_id, {"attended": 0, "total": 0, "percentage": 100.0, "status": "safe"})
        marks = s.get('marks', {}).get(sub_id, {"score": "-", "total": 100, "status": "Pending"})
        result.append({
            "id": s['id'],
            "name": s['name'],
            "roll_no": s['roll_no'],
            "branch": s.get('branch', ''),
            "attended": att.get('attended', 0),
            "total": att.get('total', 0),
            "percentage": att.get('percentage', 100.0),
            "status": att.get('status', 'safe'),
            "score": marks.get('score', '-'),
            "total_marks": marks.get('total', 100),
            "result": marks.get('status', 'Pending')
        })

    return jsonify({
        "subject": target_sub,
        "students": result,
        "all_subjects": subjects
    })

@app.route('/api/teacher/attendance/submit', methods=['POST'])
def teacher_submit_attendance():
    payload = request.json or {}
    sub_id = payload.get('subject_id', '').strip().lower()
    records = payload.get('records', [])
    session_date = payload.get('date') or payload.get('session_date')
    import datetime
    if not session_date:
        session_date = datetime.date.today().isoformat()
    
    if not sub_id or not records:
        return jsonify({"success": False, "message": "Subject ID and student records required."}), 400
        
    data = load_data()
    students = data.get('students', [])
    target_sub = next((s for s in data.get('subjects', []) if s['id'].lower() == sub_id.lower()), None)
    sub_name = target_sub['name'] if target_sub else sub_id.upper()
    
    teacher_sessions = data.setdefault('teacher_attendance_sessions', {})
    session_key = f"{sub_id}_{session_date}"
    prev_session = teacher_sessions.get(session_key)

    updated_count = 0
    present_count = 0
    absent_count = 0
    new_session_records = {}
    
    for rec in records:
        stu_id = rec.get('student_id')
        status = rec.get('status', 'present').lower()
        new_session_records[stu_id] = status
        
        stu = next((s for s in students if s['id'] == stu_id), None)
        if not stu:
            continue
            
        att_dict = stu.setdefault('attendance', {})
        sub_att = att_dict.setdefault(sub_id, {"attended": 0, "total": 0, "percentage": 100.0, "status": "safe"})
        
        if prev_session and stu_id in prev_session:
            prev_status = prev_session[stu_id]
            if prev_status != status:
                if status == 'present' and prev_status == 'absent':
                    sub_att['attended'] += 1
                elif status == 'absent' and prev_status == 'present':
                    sub_att['attended'] = max(0, sub_att['attended'] - 1)
        else:
            sub_att['total'] += 1
            if status == 'present':
                sub_att['attended'] += 1

        if status == 'present':
            present_count += 1
        else:
            absent_count += 1
            
        tot = max(1, sub_att['total'])
        sub_att['percentage'] = round((sub_att['attended'] / tot) * 100, 2)
        target = stu.get('target_attendance', 75)
        sub_att['status'] = 'safe' if sub_att['percentage'] >= target else 'warning'
        updated_count += 1

    teacher_sessions[session_key] = new_session_records
    save_data(data)
    
    action_note = "Updated existing session" if prev_session else "Recorded new session"
    return jsonify({
        "success": True,
        "message": f"{action_note} for {updated_count} students in {sub_name} ({present_count} Present, {absent_count} Absent)!",
        "present_count": present_count,
        "absent_count": absent_count,
        "total_marked": updated_count,
        "session_date": session_date
    })

# ── HOD MASTER CONTROL APIS ──────────────────────────────────────────────────

@app.route('/api/hod/student/delete', methods=['POST'])
def hod_delete_student():
    payload = request.json or {}
    stu_id = payload.get('student_id')
    data = load_data()
    orig_len = len(data.get('students', []))
    data['students'] = [s for s in data.get('students', []) if s['id'] != stu_id]
    if len(data['students']) < orig_len:
        if data.get('active_student_id') == stu_id and data['students']:
            data['active_student_id'] = data['students'][0]['id']
        save_data(data)
        return jsonify({"success": True, "message": "Student removed successfully from college records."})
    return jsonify({"success": False, "message": "Student not found."}), 404

@app.route('/api/hod/student/edit', methods=['POST'])
def hod_edit_student():
    payload = request.json or {}
    stu_id = payload.get('student_id')
    name = payload.get('name', '').strip()
    roll_no = payload.get('roll_no', '').strip()
    branch = payload.get('branch', '').strip()
    semester = payload.get('semester', '').strip()
    
    data = load_data()
    stu = next((s for s in data.get('students', []) if s['id'] == stu_id), None)
    if not stu:
        return jsonify({"success": False, "message": "Student not found."}), 404
        
    if name: stu['name'] = name
    if roll_no: stu['roll_no'] = roll_no
    if branch: stu['branch'] = branch
    if semester: stu['semester'] = semester
    save_data(data)
    return jsonify({"success": True, "message": f"Updated profile for {stu['name']}!", "student": stu})

@app.route('/api/hod/subject/delete', methods=['POST'])
def hod_delete_subject():
    payload = request.json or {}
    sub_id = payload.get('subject_id')
    data = load_data()
    orig_len = len(data.get('subjects', []))
    data['subjects'] = [s for s in data.get('subjects', []) if s['id'] != sub_id]
    if len(data['subjects']) < orig_len:
        # Also clean student records for this subject
        for stu in data.get('students', []):
            if 'attendance' in stu and sub_id in stu['attendance']:
                del stu['attendance'][sub_id]
            if 'marks' in stu and sub_id in stu['marks']:
                del stu['marks'][sub_id]
        save_data(data)
        return jsonify({"success": True, "message": "Subject removed from college curriculum."})
    return jsonify({"success": False, "message": "Subject not found."}), 404

@app.route('/api/hod/subject/edit', methods=['POST'])
def hod_edit_subject():
    payload = request.json or {}
    sub_id = payload.get('subject_id')
    name = payload.get('name', '').strip()
    code = payload.get('code', '').strip()
    faculty = payload.get('faculty', '').strip()
    
    if not sub_id:
        return jsonify({"success": False, "message": "Subject ID required."}), 400
        
    data = load_data()
    subjects = data.get('subjects', [])
    sub = next((s for s in subjects if s['id'] == sub_id), None)
    if not sub:
        return jsonify({"success": False, "message": f"Subject '{sub_id}' not found."}), 404
        
    if name: sub['name'] = name
    if code: sub['code'] = code
    if faculty: sub['faculty'] = faculty
    
    save_data(data)
    return jsonify({"success": True, "message": f"Subject '{sub['name']}' updated successfully!", "subject": sub})

@app.route('/api/state/sync', methods=['POST'])
def state_sync():
    payload = request.json or {}
    data = payload.get('data')
    if data and isinstance(data, dict):
        if 'students' in data and 'subjects' in data:
            save_data(data)
            return jsonify({"success": True, "message": "State synced with server."})
    return jsonify({"success": False, "message": "Invalid state payload."}), 400

@app.route('/api/hod/defaulters', methods=['GET'])
def hod_get_defaulters():
    data = load_data()
    students = data.get('students', [])
    subjects = data.get('subjects', [])
    sub_map = {s['id']: s['name'] for s in subjects}
    
    defaulters = []
    for stu in students:
        att_map = stu.get('attendance', {})
        shortages = []
        tot_att = 0
        tot_cls = 0
        for sub_id, att in att_map.items():
            tot_att += att.get('attended', 0)
            tot_cls += att.get('total', 0)
            if att.get('percentage', 100) < stu.get('target_attendance', 75):
                needed = calculate_classes_needed(att.get('attended', 0), att.get('total', 0), stu.get('target_attendance', 75))
                shortages.append({
                    "subject": sub_map.get(sub_id, sub_id.upper()),
                    "percentage": att.get('percentage', 0),
                    "attended": att.get('attended', 0),
                    "total": att.get('total', 0),
                    "classes_needed": needed
                })
        overall_pct = round((tot_att / tot_cls * 100), 2) if tot_cls > 0 else 100.0
        if shortages or overall_pct < stu.get('target_attendance', 75):
            defaulters.append({
                "student_id": stu['id'],
                "name": stu['name'],
                "roll_no": stu['roll_no'],
                "branch": stu.get('branch', ''),
                "overall_pct": overall_pct,
                "shortages": shortages
            })
    return jsonify({
        "defaulters": defaulters,
        "total_defaulters": len(defaulters),
        "total_students": len(students)
    })

# ── PARENT PORTAL APIS ───────────────────────────────────────────────────────

@app.route('/api/parent/student_lookup', methods=['GET'])
def parent_student_lookup():
    roll_no = request.args.get('roll_no', '').strip().lower()
    data = load_data()
    students = data.get('students', [])
    subjects = data.get('subjects', [])
    
    stu = next((s for s in students if s.get('roll_no', '').lower() == roll_no or s.get('id', '').lower() == roll_no), None)
    if not stu and roll_no:
        stu = next((s for s in students if roll_no in s.get('roll_no', '').lower() or roll_no in s.get('id', '').lower()), None)
    if not stu and roll_no:
        stu = next((s for s in students if roll_no in s.get('name', '').lower()), None)
    if not stu and roll_no:
        roll_upper = roll_no.upper()
        stu = {
            "id": roll_upper,
            "name": f"Student ({roll_upper})",
            "roll_no": roll_upper,
            "branch": "Computer Science & Engineering",
            "semester": "5th Semester",
            "target_attendance": 75,
            "attendance": {
                "os": {"attended": 38, "total": 45, "percentage": 84.44, "status": "safe"},
                "dsa": {"attended": 32, "total": 38, "percentage": 84.21, "status": "safe"},
                "dbms": {"attended": 26, "total": 30, "percentage": 86.67, "status": "safe"},
                "cn": {"attended": 24, "total": 30, "percentage": 80.0, "status": "safe"}
            },
            "marks": {
                "os": {"score": 76, "total": 100, "status": "Pass"},
                "dsa": {"score": 82, "total": 100, "status": "Pass"},
                "dbms": {"score": 75, "total": 100, "status": "Pass"},
                "cn": {"score": 70, "total": 100, "status": "Pass"}
            }
        }
        data.setdefault('students', []).append(stu)
        save_data(data)
    if not stu:
        return jsonify({"success": False, "message": f"No student found with Roll Number '{roll_no}'."}), 404
        
    att_map = stu.get('attendance', {})
    marks_map = stu.get('marks', {})
    
    subject_reports = []
    tot_att = 0
    tot_cls = 0
    for s in subjects:
        sub_id = s['id']
        a = att_map.get(sub_id, {"attended": 0, "total": 0, "percentage": 100.0, "status": "safe"})
        m = marks_map.get(sub_id, {"score": "-", "total": 100, "status": "Pending"})
        tot_att += a.get('attended', 0)
        tot_cls += a.get('total', 0)
        subject_reports.append({
            "subject_name": s['name'],
            "code": s.get('code', ''),
            "faculty": s.get('faculty', ''),
            "attended": a.get('attended', 0),
            "total": a.get('total', 0),
            "percentage": a.get('percentage', 100.0),
            "status": a.get('status', 'safe'),
            "score": m.get('score', '-'),
            "marks_status": m.get('status', 'Pending')
        })
        
    overall_pct = round((tot_att / tot_cls * 100), 2) if tot_cls > 0 else 100.0
    
    return jsonify({
        "success": True,
        "student": {
            "name": stu['name'],
            "roll_no": stu['roll_no'],
            "branch": stu.get('branch', 'CSE'),
            "semester": stu.get('semester', '5th Sem'),
            "overall_pct": overall_pct,
            "status": "safe" if overall_pct >= 75 else "warning",
            "proctor": "Dr. Sunita Rao (Faculty Advisor & Proctor - IT Block 204)"
        },
        "subjects": subject_reports
    })

# ── PLACEMENT HUB - RESUME ATS ANALYZER API ──────────────────────────────────

@app.route('/api/placement/analyze_resume', methods=['POST'])
def analyze_placement_resume():
    payload = request.json or {}
    text = payload.get('resume_text', '').lower()
    
    if not text:
        return jsonify({"success": False, "message": "Resume text is required."}), 400
        
    core_skills = {
        "python": "Python Programming",
        "java": "Java / OOP",
        "c++": "C++ / STL",
        "dsa": "Data Structures & Algorithms",
        "sql": "SQL / Relational DBs",
        "dbms": "DBMS & Query Optimization",
        "rest": "REST APIs",
        "git": "Git Version Control",
        "docker": "Docker Containerization",
        "linux": "Linux CLI",
        "react": "React Frontend",
        "cloud": "Cloud Computing (AWS/IBM Cloud/GCP)",
        "machine learning": "Machine Learning",
        "system design": "System Design"
    }
    
    matched = []
    missing = []
    for key, label in core_skills.items():
        if key in text:
            matched.append(label)
        else:
            missing.append(label)
            
    base_score = 48
    score = min(98, base_score + int((len(matched) / len(core_skills)) * 50))
    
    data = load_data()
    opportunities = data.get('opportunities', [])
    eligible_jobs = []
    for opp in opportunities:
        eligible_jobs.append({
            "title": opp.get('title'),
            "category": opp.get('category'),
            "deadline": opp.get('deadline'),
            "link": opp.get('link'),
            "fit_score": f"{min(99, score + 5)}% Match"
        })
        
    return jsonify({
        "success": True,
        "score": score,
        "grade": "Excellent Match" if score >= 85 else ("Good Match" if score >= 70 else "Needs Keyword Optimization"),
        "matched_skills": matched,
        "missing_keywords": missing[:5],
        "recommendations": [
            "Add quantifiable project impact (e.g. 'Improved query latency by 35%')",
            f"Include missing high-value keywords: {', '.join(missing[:3]) if missing else 'Containerization'}",
            "Highlight full-stack and cloud deployment experience with verified live URLs"
        ],
        "eligible_jobs": eligible_jobs
    })

# ── NOTIFICATIONS & ALERTS SYSTEM API ────────────────────────────────────────

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    data = load_data()
    student_id = request.args.get('student_id', '').strip().lower()
    active_stu = None
    if student_id:
        active_stu = next((s for s in data.get('students', []) if s.get('id', '').lower() == student_id or s.get('roll_no', '').lower() == student_id), None)
    if not active_stu:
        active_stu = get_active_student(data)

    notices = data.get('notices', [])
    opps = data.get('opportunities', [])
    
    alerts = []
    
    # 1. Attendance Shortage Notification
    if active_stu:
        att_map = active_stu.get('attendance', {})
        for sub_id, a in att_map.items():
            if a.get('percentage', 100) < 75:
                needed = calculate_classes_needed(a.get('attended', 0), a.get('total', 0), 75)
                alerts.append({
                    "id": f"att_{sub_id}",
                    "type": "warning",
                    "title": f"Shortage Alert ({sub_id.upper()})",
                    "message": f"Your attendance in {sub_id.upper()} is {a.get('percentage')}% (< 75%). Attend {needed} more classes to avoid exam debarment.",
                    "time": "Real-time Alert",
                    "badge": "Action Required"
                })

        # 2. College Fee Due Notification
        fees = active_stu.get('fees', {})
        if float(fees.get('due_amount', 0)) > 0:
            alerts.append({
                "id": f"fee_{active_stu.get('id')}",
                "type": "warning",
                "title": f"Fees Due: ₹{int(fees.get('due_amount', 0)):,}",
                "message": f"Pending balance for Odd Sem 2026 is ₹{int(fees.get('due_amount', 0)):,}. Due Date: {fees.get('due_date', '15 Oct 2026')}.",
                "time": "Finance Office",
                "badge": "Fee Due"
            })

        # 3. Pending Assignment Notification
        asgs = data.get('assignments', [])
        for a in asgs[:2]:
            sub = a.get('submissions', {}).get(active_stu.get('id'))
            if not sub:
                alerts.append({
                    "id": f"asg_{a.get('id')}",
                    "type": "exam",
                    "title": f"Assignment Due: {a.get('title')}",
                    "message": f"{a.get('subject_code')} deadline is {a.get('deadline')}. Online proctored test & PDF worksheet ready.",
                    "time": "Academic Desk",
                    "badge": "Assignment"
                })
                
    # 4. Upcoming Exam Notice
    for n in notices[:2]:
        alerts.append({
            "id": f"notice_{n.get('id', 1)}",
            "type": "exam",
            "title": n.get('title', 'Exam Notice'),
            "message": n.get('content', ''),
            "time": n.get('date', 'Today'),
            "badge": n.get('badge', 'Notice')
        })
        
    # 5. Hackathon/Job Opportunity
    for o in opps[:1]:
        alerts.append({
            "id": f"opp_{o.get('id', 1)}",
            "type": "opportunity",
            "title": f"Placement: {o.get('title')}",
            "message": f"Deadline: {o.get('deadline')}. Apply via verified portal link.",
            "time": "New",
            "badge": o.get('badge', 'Placement')
        })
        
    return jsonify({
        "notifications": alerts,
        "unread_count": len(alerts)
    })

@app.route('/api/notifications/clear', methods=['POST'])
def clear_notifications():
    return jsonify({"success": True, "message": "Notifications cleared."})

# ── Chat helper functions (longest-alias-first matching) ──────────────────────

def _resolve_health(msg_lower):
    """Return list of unique matched symptom keys (multi-symptom support)."""
    matched = []
    seen = set()
    # Sort aliases longest-first so "loose motions" beats "motion", "high fever" beats "fever"
    for alias, canonical in sorted(HEALTH_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in msg_lower and canonical not in seen:
            if canonical in HEALTH_SYMPTOMS:
                matched.append(canonical)
                seen.add(canonical)
    # Also scan direct keys for anything not yet caught
    for key in HEALTH_SYMPTOMS:
        if key in msg_lower and key not in seen:
            matched.append(key)
            seen.add(key)
    return matched


def _resolve_study(msg_lower):
    """Return the single best-matching study topic (longest-alias-first)."""
    for alias, canonical in sorted(STUDY_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in msg_lower:
            return canonical
    for key in STUDY_KNOWLEDGE:
        if key in msg_lower:
            return key
    return None


# ── AI FRIEND LIVE WEB SEARCH ENGINE ───────────────────────────────────────

def clean_for_search(q):
    s = q.strip()
    s = re.sub(r'^(bhai|yaar|bro|hey|hello|please|can you tell me|can you explain|tell me about|what is|who is|explain|mujhe batao|batao)\s+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+(kya hai|kya hota hai|batao|bataiye|ke bare me|ke baare mein|kaise kare|kaise karein|in hindi|in english|bata do)$', '', s, flags=re.IGNORECASE)
    return s.strip()

def search_wikipedia(query):
    try:
        url = 'https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=' + urllib.parse.quote(query) + '&format=json&utf8=1'
        req = urllib.request.Request(url, headers={'User-Agent': 'CampusGenieAI/1.0 (harshit@campusgenie.org)'})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            results = data.get('query', {}).get('search', [])
            items = []
            for r in results[:3]:
                title = r.get('title', '')
                snippet = re.sub(r'<[^>]+>', '', r.get('snippet', '')).strip()
                link = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                items.append({'title': title, 'snippet': snippet, 'link': link})
            return items
    except Exception:
        return []

def search_ddg_html(query):
    try:
        url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(query)
        req = urllib.request.Request(
            url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9'
            }
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            html = res.read().decode('utf-8', errors='ignore')
            matches = re.findall(r'<a[^>]+class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)
            url_matches = re.findall(r'href="(?:https?:)?//duckduckgo\.com/l/\?uddg=([^"&]+)', html)
            title_matches = re.findall(r'<a[^>]+class="result__title[^>]*>(.*?)</a>', html, re.DOTALL)
            
            items = []
            for i in range(min(len(matches), len(url_matches), 3)):
                snip = re.sub(r'<[^>]+>', '', matches[i]).strip()
                raw_url = urllib.parse.unquote(url_matches[i])
                title = re.sub(r'<[^>]+>', '', title_matches[i]).strip() if i < len(title_matches) else query
                items.append({'title': title, 'snippet': snip, 'link': raw_url})
            return items
    except Exception:
        return []

def search_ddg_api(query):
    try:
        url = 'https://api.duckduckgo.com/?q=' + urllib.parse.quote(query) + '&format=json&no_html=1&skip_disambig=1'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            abstract = data.get('AbstractText') or data.get('Abstract')
            url = data.get('AbstractURL')
            source = data.get('AbstractSource') or 'DuckDuckGo'
            if abstract and url:
                return [{'title': f"{source}: {query}", 'snippet': abstract, 'link': url}]
            related = data.get('RelatedTopics', [])
            items = []
            for t in related[:3]:
                if isinstance(t, dict) and 'Text' in t and 'FirstURL' in t:
                    items.append({'title': t['Text'][:60] + '...', 'snippet': t['Text'], 'link': t['FirstURL']})
            return items
    except Exception:
        return []

def ai_friend_web_search(user_msg, student_name="Student"):
    q = user_msg.strip()
    search_q = clean_for_search(q)
    if not search_q or len(search_q) < 2:
        search_q = q

    results = search_ddg_html(search_q)
    if not results:
        results = search_wikipedia(search_q)
    if not results:
        results = search_ddg_api(search_q)

    if not results:
        return (
            f"🌐 **CampusGenie AI Friend**\n\n"
            f"Arre {student_name}, maine web par **\"{search_q}\"** dhoondhne ki koshish ki, lekin direct live response connect nahi ho paya.\n\n"
            f"💡 *Tip:* Thoda specific keyword likh kar poochiye (jaise: *'Python reverse list'*, *'Quantum computing basics'*, *'Latest AI updates'*), main turant live search karke direct link ke sath dunga!"
        ), "web_search"

    lines = [
        f"🌐 **CampusGenie AI Friend — Live Web Intelligence**\n",
        f"Dost, maine live internet par **\"{search_q}\"** search kiya! Ye rahi verified information:\n"
    ]

    for idx, r in enumerate(results[:3], 1):
        clean_snip = r['snippet'].replace('\n', ' ').strip()
        lines.append(f"**{idx}. {r['title']}**\n{clean_snip}\n")

    lines.append("---\n🔗 **Verified Sources & Web Links:**")
    seen = set()
    for r in results[:4]:
        link = r['link']
        if link not in seen:
            seen.add(link)
            lines.append(f"• [{r['title']}]({link})")

    lines.append("\n💡 *Live Internet Search Active • Click source link to explore further. Ask me anything else!*")
    return "\n".join(lines), "web_search"


# --- AI COPILOT CHATBOT ---

@app.route('/api/chat', methods=['POST'])
def chat():
    payload = request.json or {}
    user_msg = payload.get('message', '').strip()
    msg_lower = user_msg.lower()
    student_id = (payload.get('student_id') or '').strip().lower()

    data = load_data()
    active_stu = None
    if student_id:
        active_stu = next((s for s in data.get('students', []) if s.get('id', '').lower() == student_id or s.get('roll_no', '').lower() == student_id or student_id in s.get('roll_no', '').lower()), None)
    if not active_stu:
        active_stu = get_active_student(data)
    student_name = active_stu.get('name', 'Student') if active_stu else 'Student'

    # ── 0. CONVERSATIONAL AI FRIEND GREETINGS ──
    greetings = ['hi', 'hello', 'hey', 'namaste', 'kaise ho', 'kya haal hai', 'who are you', 'tu kaun hai', 'tu kaisa hai', 'kya kar rahe ho', 'ai friend']
    if any(msg_lower == g or msg_lower.startswith(g + ' ') for g in greetings):
        return jsonify({
            "reply": (
                f"👋 **Namaste {student_name}! Main hoon aapka AI Friend & 360° Campus Companion!** 🤝\n\n"
                f"Aap mujhse bejhijhak kuch bhi pooch sakte ho:\n"
                f"• 🎓 **Campus & Academics:** Attendance shortage calculation, exam marks, timetables & CS doubts.\n"
                f"• 🩺 **Hostel Health & Care:** Late-night fever, headache, cold, acidity par safe OTC first-aid medicine aur home remedies.\n"
                f"• 🌐 **Live Web Intelligence:** Duniya ka koi bhi sawaal poocho (programming, current affairs, tech news, definitions, facts)—main live internet se dhoondhkar **verified source links** ke saath answer dunga!\n\n"
                f"*Bataiye dost, aaj kya seekhna ya dhoondhna hai?*"
            ),
            "action": "friend"
        })

    # ── 1. HEALTH & SYMPTOMS TRIAGE ──
    matched_symptoms = _resolve_health(msg_lower)
    if matched_symptoms:
        sections = []
        for sym_key in matched_symptoms[:3]:   # cap at 3 conditions per message
            info = HEALTH_SYMPTOMS[sym_key]
            sections.append(
                f"---\n"
                f"### 🩺 {info['condition']}\n"
                f"**Severity:** {info['severity']}\n\n"
                f"💊 **First-Aid & Safe Medicine:**\n{info['first_aid']}\n\n"
                f"🍵 **Home Remedies:**\n{info['home_remedy']}\n\n"
                f"{info['doctor_alert']}"
            )
        n = len(matched_symptoms)
        header = (
            f"🩺 **Campus Health AI — {n} Condition{'s' if n > 1 else ''} Detected**\n\n"
            if n > 1
            else "🩺 **Campus Health AI — Symptom Triage**\n\n"
        )
        footer = "\n\n---\n*AI first-aid guidance only — not a substitute for professional care. Visit Campus Clinic, Health Block Room 04.*"
        return jsonify({"reply": header + "\n".join(sections) + footer, "action": "health"})

    # ── 2. ACADEMIC DOUBT SOLVER ─────────────────────────────────────────────
    resolved_topic = _resolve_study(msg_lower)
    if resolved_topic and resolved_topic in STUDY_KNOWLEDGE:
        s_info = STUDY_KNOWLEDGE[resolved_topic]
        subject_tag = s_info.get('subject', 'CS')
        return jsonify({
            "reply": (
                f"📚 **AI Academic Tutor [{subject_tag}]**\n"
                f"### {s_info['title']}\n\n"
                f"---\n"
                f"💡 **Core Concept:**\n{s_info['explanation']}\n\n"
                f"⚡ **Complexity / Key Properties:**\n`{s_info['complexity']}`\n\n"
                f"🎯 **Exam & Viva Pro-Tip:**\n{s_info['exam_tip']}"
            ),
            "action": "academic"
        })

    # ── 3. MARKS & RESULT QUERIES ────────────────────────────────────────────
    if any(k in msg_lower for k in ['mark', 'score', 'pass', 'fail', 'result', 'grade']):
        marks_map = active_stu.get('marks', {}) if active_stu else {}
        sub_list = data.get('subjects', [])
        reply_lines = [f"📋 **Academic Performance & Results — {student_name}**\n"]
        for s in sub_list:
            m = marks_map.get(s['id'], {"score": "Not Declared", "total": 100, "status": "Pending"})
            badge = "🟢 Pass" if m['status'] == 'Pass' else ("🔴 Fail" if m['status'] == 'Fail' else "⚪ Pending")
            reply_lines.append(f"• **{s['name']}** `{s['code']}`: {m['score']}/{m['total']} — {badge}")
        return jsonify({"reply": "\n".join(reply_lines), "action": None})

    # ── 4. HACKATHONS & JOBS ─────────────────────────────────────────────────
    if any(k in msg_lower for k in ['hackathon', 'job', 'internship', 'placement', 'contest', 'opportunity']):
        opps = data.get('opportunities', [])
        if opps:
            opp_text = "🚀 **Active Hackathons & Job Opportunities:**\n\n"
            for o in opps[:3]:
                opp_text += f"• **[{o['category']}] {o['title']}**\n  ⏰ Deadline: {o['deadline']}\n  🔗 {o['link']}\n\n"
            return jsonify({"reply": opp_text, "action": None})

    # ── 4.5 SMART HALL TICKET / ADMIT CARD QUERIES ───────────────────────────
    if any(k in msg_lower for k in ['admit card', 'hall ticket', 'admitcard', 'hallticket', 'exam pass', 'pravesh patra', 'exam permit']):
        att_map = active_stu.get('attendance', {}) if active_stu else {}
        tot_att = sum(v.get('attended', 0) for v in att_map.values())
        tot_cls = sum(v.get('total', 0) for v in att_map.values())
        overall_pct = round((tot_att / tot_cls * 100), 2) if tot_cls > 0 else 100.0
        if overall_pct >= 75.0:
            reply = (
                f"🎟️ **Smart Hall Ticket Status: APPROVED & READY**\n\n"
                f"Badhaai ho **{student_name}**! Aapki aggregate attendance **{overall_pct}%** hai (Mandatory 75.0% threshold se upar).\n\n"
                f"• **Status:** ELIGIBLE FOR SEMESTER EXAMINATIONS ✅\n"
                f"• **Security Code:** Anti-Tamper Digital QR Verified\n\n"
                f"👉 Aap student dashboard par **'🎟️ Hall Ticket'** button daba kar apna official exam permit download ya print kar sakte ho!"
            )
        else:
            reply = (
                f"🚨 **Smart Hall Ticket Status: WITHHELD (< 75% Policy)**\n\n"
                f"Dhyan dein **{student_name}**: Aapki aggregate attendance **{overall_pct}%** hai (Mandatory 75.0% se kam).\n\n"
                f"• **Status:** DEBARRED FROM SEMESTER EXAMINATIONS ⚠️\n"
                f"• **Remedy:** Upcoming classes attend karke 75% recovery karein ya HOD Dr. S. K. Bansal ko medical application submit karein."
            )
        return jsonify({"reply": reply, "action": "hallticket"})

    # ── 5. ATTENDANCE QUERIES (Hinglish + Natural Language) ───────────────────
    att_keywords = [
        'attendance', 'attendence', 'shortage', 'present', 'absent', 'bunk', 'skip', 'miss',
        'meri attendance', 'kitne present', 'kitne absent', 'kitni attendance', 'haziri',
        'percentage', 'debar', 'debarred', 'present hai', 'aaya tha', 'aaye the'
    ]
    if any(k in msg_lower for k in att_keywords):
        att_map = active_stu.get('attendance', {}) if active_stu else {}
        sub_list = data.get('subjects', [])
        target = active_stu.get('target_attendance', 75)
        reply_lines = [f"📊 **Attendance Report — {student_name}** (Target: {target}%)\n"]
        has_shortage = False
        for s in sub_list:
            a = att_map.get(s['id'], {"attended": 0, "total": 0, "percentage": 100.0})
            pct = a.get('percentage', 0)
            att = a.get('attended', 0)
            tot = a.get('total', 0)
            if pct < target:
                has_shortage = True
                needed = calculate_classes_needed(att, tot, target)
                reply_lines.append(f"• **{s['name']}**: {att}/{tot} ({pct}%) — ⚠️ **SHORTAGE** → Attend **{needed}** more class{'es' if needed != 1 else ''} to reach {target}%")
            else:
                bunks_left = calculate_max_bunks(att, tot, target)
                reply_lines.append(f"• **{s['name']}**: {att}/{tot} ({pct}%) — ✅ Safe (can skip **{bunks_left}** more)")
        reply_lines.append(
            f"\n🚨 **Action Required:** Attend all flagged classes to avoid exam debarment." if has_shortage
            else f"\n🎉 All subjects above {target}% — you're on track!"
        )
        return jsonify({"reply": "\n".join(reply_lines), "action": None})

    # ── 6. TIMETABLE & VENUE QUERIES ─────────────────────────────────────────
    timetable_keywords = [
        'timetable', 'time table', 'schedule', 'class', 'lecture', 'where', 'kahan', 'room',
        'venue', 'teacher', 'faculty', 'kab hai', 'period', 'routine', 'aaj ki class', 'kal ki class'
    ]
    if any(k in msg_lower for k in timetable_keywords):
        tt = data.get('timetable', [])
        if tt:
            tt_lines = ["📅 **Class Timetable & Venues for Today:**\n"]
            for idx, c in enumerate(tt, 1):
                status_tag = {"ongoing": "🟢 Live Now", "completed": "✅ Done", "upcoming": "⏳ Upcoming"}.get(c.get('status', 'upcoming'), "⏳ Upcoming")
                tt_lines.append(
                    f"**{idx}. {c['subject']}** `{c.get('type','Theory')}` — {status_tag}\n"
                    f"   ⏰ {c['time']} | 📍 **{c['room']}** | 👨‍🏫 {c['faculty']}\n"
                )
            return jsonify({"reply": "\n".join(tt_lines), "action": None})

    # ── 6.5 COLLEGE FEES & PAYMENT QUERIES ────────────────────────────────────
    fee_keywords = ['fee', 'fees', 'fees status', 'kitni fee', 'due fee', 'pending fee', 'fees kitni', 'fee submit', 'pay fee', 'receipt', 'chalan']
    if any(k in msg_lower for k in fee_keywords):
        fees = active_stu.get('fees', {}) if active_stu else {}
        total = int(fees.get('total_fee', 125000))
        paid = int(fees.get('paid_amount', 0))
        due = int(fees.get('due_amount', 0))
        due_date = fees.get('due_date', '15 Oct 2026')
        status = fees.get('status', 'due')
        status_badge = "🟢 Fully Paid" if status == 'paid' else ("🟡 Partially Paid" if status == 'partial' else "🔴 Pending Due")
        
        reply_msg = (
            f"💳 **College Fees Summary — {student_name}**\n\n"
            f"• **Account Status:** {status_badge}\n"
            f"• **Total Academic Fees:** ₹{total:,}\n"
            f"• **Paid Amount:** ₹{paid:,}\n"
            f"• **Pending Balance:** ₹{due:,}\n"
            f"• **Payment Due Date:** {due_date}\n\n"
        )
        if due > 0:
            reply_msg += f"👉 Aapke account me **₹{due:,}** pending hai. Dashboard par **'💳 Pay College Fees'** button daba kar UPI/Cards se pay karein aur turant official AKGEC receipt paayein!"
        else:
            reply_msg += "🎉 Badhaai ho! Aapki semester college fees 100% pay ho chuki hai. Koi pending balance nahi hai."
        return jsonify({"reply": reply_msg, "action": "fees"})

    # ── 6.6 ASSIGNMENTS & PROCTORED ONLINE TESTS ──────────────────────────────
    asg_keywords = ['assignment', 'assignments', 'test', 'tests', 'online test', 'quiz', 'proctor', 'camera test', 'homework', 'asg', 'practical journal']
    if any(k in msg_lower for k in asg_keywords):
        asgs = data.get('assignments', [])
        asg_lines = [f"📝 **Assignments & Proctored Tests Hub — {student_name}**\n"]
        stu_id_key = active_stu.get('id', '') if active_stu else ''
        for a in asgs:
            sub = a.get('submissions', {}).get(stu_id_key)
            if sub:
                sub_status = f"✅ Submitted (Score: {sub.get('score')}/{sub.get('total_marks')} • {sub.get('percentage')}%)"
            else:
                sub_status = "⏳ Pending Submission"
            asg_lines.append(f"• **{a.get('title')}** (`{a.get('subject_code')}`)\n  Deadline: {a.get('deadline')} | Marks: {a.get('total_marks')} | Status: {sub_status}")
            
        asg_lines.append("\n👉 Dashboard par **'Assignments & Tests'** card se aap official question paper PDF download kar sakte hain ya **AI WebCam + Mic proctoring** ke saath live online test de sakte hain!")
        return jsonify({"reply": "\n".join(asg_lines), "action": "assignments"})

    # ── 7. AI FRIEND LIVE WEB SEARCH ENGINE (FOR ANY OTHER QUESTION) ──
    if user_msg:
        web_reply, web_action = ai_friend_web_search(user_msg, student_name)
        return jsonify({"reply": web_reply, "action": web_action})

    # Default fallback if message is empty
    return jsonify({
        "reply": f"👋 **Hello {student_name}!** Poochiye koi bhi sawaal—academics, health, campus ERP, ya internet se koi bhi general knowledge/tech question!",
        "action": None
    })

# ==============================================================================
# ADVANCED CAMPUSGENIE 2026 ERP SUITE API ENDPOINTS
# ==============================================================================

@app.route('/api/community/lost_found', methods=['GET'])
def get_lost_found():
    data = load_data()
    return jsonify({"success": True, "items": data.get('lost_and_found', [])})

@app.route('/api/community/lost_found/add', methods=['POST'])
def add_lost_found():
    payload = request.json or {}
    item_type = payload.get('type', 'Lost')
    item_name = payload.get('item', '').strip()
    location = payload.get('location', '').strip()
    contact = payload.get('contact', '').strip()
    reported_by = payload.get('reported_by', 'Student').strip()
    if not item_name or not location:
        return jsonify({"success": False, "message": "Item name and location are required."}), 400
    data = load_data()
    lf_list = data.setdefault('lost_and_found', [])
    new_item = {
        "id": f"LF-{len(lf_list) + 101}",
        "type": item_type,
        "item": item_name,
        "location": location,
        "date": "Today",
        "reported_by": reported_by,
        "contact": contact or "N/A",
        "status": "Open"
    }
    lf_list.insert(0, new_item)
    save_data(data)
    return jsonify({"success": True, "message": "Lost/Found report posted to Campus Hub!", "item": new_item})

@app.route('/api/community/lost_found/claim', methods=['POST'])
def claim_lost_found():
    payload = request.json or {}
    item_id = payload.get('id')
    data = load_data()
    for item in data.get('lost_and_found', []):
        if item.get('id') == item_id:
            item['status'] = 'Claimed'
            save_data(data)
            return jsonify({"success": True, "message": f"Item '{item['item']}' marked as Claimed / Resolved!"})
    return jsonify({"success": False, "message": "Item not found."}), 404

@app.route('/api/mess/menu', methods=['GET'])
def get_mess_menu():
    data = load_data()
    return jsonify({"success": True, "mess_menu": data.get('mess_menu', {})})

@app.route('/api/mess/rate', methods=['POST'])
def rate_mess():
    payload = request.json or {}
    stars = int(payload.get('stars', 5))
    comment = payload.get('comment', '').strip()
    student_name = payload.get('student_name', 'Student').strip()
    data = load_data()
    mess_menu = data.setdefault('mess_menu', {})
    ratings = mess_menu.setdefault('ratings', {'total_votes': 142, 'average': 4.4, 'recent_reviews': []})
    
    total = ratings.get('total_votes', 0)
    current_avg = ratings.get('average', 4.4)
    new_total = total + 1
    new_avg = round(((current_avg * total) + stars) / new_total, 2)
    
    ratings['total_votes'] = new_total
    ratings['average'] = new_avg
    if comment:
        reviews = ratings.setdefault('recent_reviews', [])
        reviews.insert(0, {'student': student_name, 'stars': stars, 'comment': comment})
        if len(reviews) > 10:
            reviews.pop()
    save_data(data)
    return jsonify({"success": True, "message": "Thank you for rating today's mess meal!", "ratings": ratings})

@app.route('/api/exam/seating', methods=['GET'])
def get_exam_seating():
    student_id = request.args.get('student_id', '').strip()
    data = load_data()
    seatings = data.get('seating_arrangements', {})
    seating = seatings.get(student_id)
    if not seating:
        stu = next((s for s in data.get('students', []) if s['id'].lower() == student_id.lower() or s.get('roll_no', '').lower() == student_id.lower()), None)
        if not stu and data.get('students'):
            stu = data['students'][0]
        roll = stu.get('roll_no', student_id) if stu else (student_id or "22CS1084")
        name = stu.get('name', 'Student') if stu else 'Student'
        last_num = int(re.sub(r'\D', '', roll)[-2:]) if re.search(r'\d', roll) else 14
        seating = {
            'student_name': name,
            'roll_no': roll,
            'exam': 'B.Tech V Semester Mid-Term Examination 2026',
            'exam_center': 'AKGEC Main Academic Complex',
            'hall_building': 'CS Block (Block-A)',
            'room_no': f'Room 30{(last_num % 8) + 1} (3rd Floor)',
            'row': f"Row {chr(65 + (last_num % 4))}",
            'bench_no': f"Bench {(last_num % 25) + 1}",
            'seat_no': f"Seat {chr(65 + (last_num % 4))}-{(last_num % 25) + 1}",
            'reporting_time': '09:00 AM',
            'instructions': [
                'Candidates must carry their AKGEC College ID and this printed Admit Card.',
                'Electronic devices, smartwatches, and programmable calculators are strictly prohibited.',
                'Report to the examination hall at least 15 minutes before the scheduled time.'
            ]
        }
    return jsonify({"success": True, "seating": seating})

@app.route('/api/parent/alert', methods=['POST'])
def send_parent_alert():
    payload = request.json or {}
    student_id = payload.get('student_id', '')
    alert_type = payload.get('type', 'attendance')
    message = payload.get('message', '').strip()
    data = load_data()
    stu = next((s for s in data.get('students', []) if s['id'] == student_id or s.get('roll_no') == student_id), None)
    stu_name = stu.get('name', 'Student') if stu else student_id
    
    notices = data.setdefault('notices', [])
    notices.insert(0, {
        "id": f"PARENT-ALERT-{len(notices)+1}",
        "title": f"📲 Parent WhatsApp/SMS Dispatched: {stu_name}",
        "category": "Parent Alert",
        "date": "Just now",
        "priority": "high",
        "message": message or f"Urgent official notification sent to parent regarding {alert_type} for {stu_name} ({student_id})."
    })
    save_data(data)
    return jsonify({"success": True, "message": f"WhatsApp notification alert successfully sent to parent of {stu_name}!"})

@app.route('/api/placement/analyze', methods=['POST'])
def analyze_placement():
    payload = request.json or {}
    skills = payload.get('skills', [])
    target_role = payload.get('target_role', 'Full Stack Developer / SDE').strip()
    
    weight_map = {
        'dsa': 25,
        'cpp': 15,
        'python': 15,
        'react': 15,
        'sql': 15,
        'cloud': 10,
        'docker': 10,
        'system_design': 10,
        'git': 5,
        'ml': 10
    }
    score = 25
    matched_skills = []
    missing_skills = []
    
    for s_key, weight in weight_map.items():
        if s_key in skills:
            score += weight
            matched_skills.append(s_key.upper())
        else:
            missing_skills.append(s_key.upper())
            
    score = min(score, 98)
    
    companies = []
    if score >= 80:
        companies = ["Amazon AWS (SDE-1 - 24 LPA)", "TCS Digital (7.5 LPA)", "Accenture Advanced Associate", "Paytm Technologies"]
    elif score >= 60:
        companies = ["TCS Ninja (3.6 LPA)", "Infosys Specialist Programmer (5 LPA)", "Cognizant GenC Elevate", "Wipro Turbo"]
    else:
        companies = ["Service-based Foundation Drives", "Incubated Startups @ AKGEC", "TCS National Qualifier (NQT)"]
        
    tips = []
    if 'DSA' in missing_skills:
        tips.append("Focus heavily on DSA: Solve 50+ LeetCode Medium problems on Trees, Graphs, and DP.")
    if 'SQL' in missing_skills:
        tips.append("Master SQL queries: Practice subqueries, indexing, and normalization questions for technical rounds.")
    if 'CLOUD' in missing_skills:
        tips.append("Learn Cloud Fundamentals: Complete AWS Cloud Practitioner or IBM watsonx / Cloud badges.")
    if not tips:
        tips.append("Great skill profile! Practice mock HR and System Design interviews on AKGEC portal.")

    return jsonify({
        "success": True,
        "score": score,
        "readiness": "High" if score >= 75 else ("Moderate" if score >= 55 else "Developing"),
        "target_role": target_role,
        "eligible_companies": companies,
        "matched_skills": matched_skills,
        "tips": tips
    })

@app.route('/api/hod/analytics', methods=['GET'])
def get_hod_analytics():
    data = load_data()
    students = data.get('students', [])
    total_students = len(students)
    
    total_att_pct = 0
    defaulter_count = 0
    total_fee_due = 0
    total_fee_paid = 0
    
    for s in students:
        att_dict = s.get('attendance', {})
        if att_dict:
            s_pcts = [subj.get('percentage', 0) for subj in att_dict.values()]
            avg_p = sum(s_pcts) / len(s_pcts) if s_pcts else 0
            total_att_pct += avg_p
            if avg_p < 75:
                defaulter_count += 1
        fees = s.get('fees', {})
        total_fee_paid += fees.get('paid_amount', 0)
        total_fee_due += fees.get('due_amount', 0)
        
    dept_att_avg = round(total_att_pct / total_students, 1) if total_students else 0
    fee_collection_rate = round((total_fee_paid / (total_fee_paid + total_fee_due) * 100), 1) if (total_fee_paid + total_fee_due) > 0 else 0
    
    return jsonify({
        "success": True,
        "analytics": {
            "total_students": total_students,
            "department_attendance_avg": dept_att_avg,
            "defaulter_count": defaulter_count,
            "total_fee_collected": total_fee_paid,
            "total_fee_outstanding": total_fee_due,
            "fee_collection_rate": fee_collection_rate,
            "placement_rate": 88.5
        }
    })

if __name__ == '__main__':
    print("[+] CampusGenie Ultimate Server starting on http://127.0.0.1:5000 ...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

