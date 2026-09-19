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

# â”€â”€ Academic Doubt Solver Knowledge Base â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each key is a lowercase trigger phrase matched against the user message.
# Multiple keys can map to the same concept via STUDY_ALIASES below.

STUDY_KNOWLEDGE = {
    # â”€â”€ DATA STRUCTURES & ALGORITHMS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "binary search": {
        "title": "Binary Search (Divide & Conquer)",
        "subject": "DSA",
        "explanation": "Works on a **sorted array** by repeatedly halving the search interval. Compare the target to the middle element â€” if not equal, discard the half that cannot contain the target and repeat.",
        "complexity": "Time: O(log N) average & worst | Space: O(1) iterative, O(log N) recursive",
        "exam_tip": "Viva Q: Why faster than Linear Search? Every step halves the search space: N â†’ N/2 â†’ N/4 â†’ ... â†’ 1. Always verify array is sorted first â€” applying Binary Search to unsorted data gives wrong results."
    },
    "bubble sort": {
        "title": "Bubble Sort Algorithm",
        "subject": "DSA",
        "explanation": "Repeatedly steps through the list, compares adjacent elements, and swaps them if in the wrong order. Each full pass 'bubbles' the largest unsorted element to its correct position at the end.",
        "complexity": "Time: O(NÂ²) worst/average | O(N) best (already sorted with optimization) | Space: O(1) in-place",
        "exam_tip": "Optimization: add a flag `swapped`. If no swap in a pass, array is sorted â€” break early. This gives O(N) best case. Never use Bubble Sort for large N in production."
    },
    "merge sort": {
        "title": "Merge Sort (Divide & Conquer)",
        "subject": "DSA",
        "explanation": "Recursively divides the array into two halves, sorts each half, then **merges** the two sorted halves. The merge step is the key â€” it combines two sorted arrays in O(N) time by comparing elements one by one.",
        "complexity": "Time: O(N log N) always (best, average, worst) | Space: O(N) auxiliary",
        "exam_tip": "Merge Sort is a **stable** sort. Preferred for linked lists and external sorting (large files). Unlike Quick Sort, worst case is always O(N log N), not O(NÂ²)."
    },
    "quick sort": {
        "title": "Quick Sort (Divide & Conquer)",
        "subject": "DSA",
        "explanation": "Selects a **pivot** element and partitions the array into: elements < pivot (left) and elements > pivot (right). Recursively sorts both partitions. No extra space needed for the sort itself.",
        "complexity": "Time: O(N log N) average | O(NÂ²) worst (sorted array with last element as pivot) | Space: O(log N) stack",
        "exam_tip": "Worst case avoided with **randomized pivot** or **median-of-three**. Quick Sort is cache-friendly and in-practice faster than Merge Sort for in-memory data due to low constant factors."
    },
    "linked list": {
        "title": "Linked List Data Structure",
        "subject": "DSA",
        "explanation": "A linear data structure where each element (node) stores data and a pointer to the next node. Unlike arrays, nodes are not stored contiguously in memory. Types: Singly, Doubly, Circular.",
        "complexity": "Access: O(N) | Insert/Delete at head: O(1) | Insert/Delete at tail (without tail ptr): O(N) | Search: O(N)",
        "exam_tip": "Key trick for interviews: **Floyd's Cycle Detection** (slow/fast pointer) detects cycles in O(N) time and O(1) space. Reversing a linked list in-place is a classic viva question â€” draw the pointer changes."
    },
    "stack": {
        "title": "Stack Data Structure (LIFO)",
        "subject": "DSA",
        "explanation": "A linear data structure following **Last In, First Out (LIFO)**. Main operations: push (add to top), pop (remove from top), peek (view top without removing). Implemented using arrays or linked lists.",
        "complexity": "Push/Pop/Peek: O(1) | Search: O(N)",
        "exam_tip": "Applications: function call stack, undo operations, expression evaluation (infixâ†’postfix), balanced parentheses checking. Memorize: Infix to Postfix uses a stack â€” operators go on stack, operands go directly to output."
    },
    "queue": {
        "title": "Queue Data Structure (FIFO)",
        "subject": "DSA",
        "explanation": "A linear data structure following **First In, First Out (FIFO)**. Enqueue adds to the rear, Dequeue removes from the front. Variants: Circular Queue (avoids false overflow), Deque (double-ended), Priority Queue.",
        "complexity": "Enqueue/Dequeue: O(1) with proper implementation | Search: O(N)",
        "exam_tip": "Circular Queue solves the false overflow problem of simple queue arrays. Priority Queue is implemented using a **Min/Max Heap** â€” not a sorted array. Used in CPU scheduling (FCFS, SJF)."
    },
    "tree": {
        "title": "Trees & Binary Search Tree (BST)",
        "subject": "DSA",
        "explanation": "A hierarchical data structure with a root node and subtrees. BST property: left subtree values < root < right subtree values. Traversals: Inorder (Left-Root-Right), Preorder (Root-Left-Right), Postorder (Left-Right-Root).",
        "complexity": "BST Search/Insert/Delete: O(log N) average | O(N) worst (skewed tree) | Balanced AVL/Red-Black: O(log N) guaranteed",
        "exam_tip": "Inorder traversal of a BST gives **sorted output** â€” this is a critical exam fact. For height-balanced trees (AVL), remember the rotation types: LL, RR, LR, RL. Height of BST with N nodes: log N (balanced) to N (skewed)."
    },
    "graph": {
        "title": "Graphs: BFS, DFS & Algorithms",
        "subject": "DSA",
        "explanation": "A non-linear structure of vertices (nodes) and edges. BFS (Breadth-First Search) uses a Queue â€” explores level by level. DFS (Depth-First Search) uses a Stack/Recursion â€” goes deep before backtracking.",
        "complexity": "BFS/DFS: O(V + E) where V = vertices, E = edges | Dijkstra: O((V+E) log V) with min-heap",
        "exam_tip": "BFS finds **shortest path in unweighted graphs**. DFS is used for topological sort, cycle detection, strongly connected components. Dijkstra's algorithm for weighted shortest path â€” does NOT work with negative weights (use Bellman-Ford instead)."
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
        "exam_tip": "DP applies when: (1) Optimal Substructure â€” optimal solution built from optimal sub-solutions; (2) Overlapping Subproblems â€” same sub-problems solved multiple times. Classic DPs: Fibonacci, LCS, LIS, 0/1 Knapsack, Matrix Chain Multiplication."
    },

    # â”€â”€ OPERATING SYSTEMS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "deadlock": {
        "title": "Deadlock in Operating Systems",
        "subject": "OS",
        "explanation": "A state where a set of processes are **permanently blocked** â€” each holds a resource and waits for one held by another. None can proceed.",
        "complexity": "4 Necessary Conditions (Coffman): Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait",
        "exam_tip": "3 strategies: **Prevention** (negate one Coffman condition), **Avoidance** (Banker's Algorithm â€” maintain safe state), **Detection & Recovery** (allow deadlock, then kill/rollback). Banker's Algorithm is the #1 exam topic â€” always draw the allocation/need/available tables."
    },
    "process scheduling": {
        "title": "CPU Scheduling Algorithms",
        "subject": "OS",
        "explanation": "OS decides which ready process gets CPU time. Algorithms: FCFS (First Come First Serve), SJF (Shortest Job First), Round Robin (time quantum), Priority Scheduling, SRTF (Shortest Remaining Time First â€” preemptive SJF).",
        "complexity": "FCFS: No starvation, high convoy effect. SJF: Minimum avg waiting time (optimal for non-preemptive). Round Robin: Fair, high context switch overhead.",
        "exam_tip": "For numerical problems: **Gantt Chart** is mandatory. Key formulas: Waiting Time = Turnaround Time âˆ’ Burst Time. Turnaround Time = Completion Time âˆ’ Arrival Time. SJF suffers from starvation (solved by Aging). Round Robin time quantum choice is critical."
    },
    "paging": {
        "title": "Paging & Virtual Memory",
        "subject": "OS",
        "explanation": "Memory management scheme that eliminates external fragmentation. Process is divided into fixed-size **pages**, physical memory into **frames**. OS maintains a Page Table mapping logical addresses to physical addresses.",
        "complexity": "Logical Address = Page Number + Page Offset. Physical Address = Frame Number + Page Offset. Page Table Entry size = log2(# frames) bits.",
        "exam_tip": "Page Table is stored in RAM â€” two memory accesses per data access (slow!). Solution: **TLB (Translation Lookaside Buffer)** â€” a fast cache for page table. Effective Access Time (EAT) = hit-ratio Ã— TLB-time + (1-hit-ratio) Ã— (TLB+2Ã—memory-time). Page faults are expensive â€” minimized by LRU/Optimal replacement."
    },
    "semaphore": {
        "title": "Semaphores & Process Synchronization",
        "subject": "OS",
        "explanation": "A semaphore is an integer variable accessed only through two atomic operations: **wait(S)** [P operation â€” decrements S, blocks if S<0] and **signal(S)** [V operation â€” increments S, wakes blocked process]. Types: Binary (mutex) and Counting.",
        "complexity": "Solves: Mutual Exclusion, Producer-Consumer, Readers-Writers, Dining Philosophers problems.",
        "exam_tip": "Binary semaphore (0 or 1) = mutex. Counting semaphore manages N resources. Classic problem: **Producer-Consumer** â€” producer does signal(full)/wait(empty), consumer does wait(full)/signal(empty). mutex semaphore prevents simultaneous buffer access. Always draw the sequence diagram in exams."
    },

    # â”€â”€ COMPUTER NETWORKS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "tcp vs udp": {
        "title": "TCP vs UDP (Transport Layer)",
        "subject": "CN",
        "explanation": "**TCP** (Transmission Control Protocol): connection-oriented, reliable, ordered delivery, flow/congestion control via 3-way handshake (SYN â†’ SYN-ACK â†’ ACK). **UDP** (User Datagram Protocol): connectionless, unreliable, no handshake, low overhead.",
        "complexity": "TCP: Heavyweight, reliable â€” used for HTTP/HTTPS, FTP, SMTP, SSH. UDP: Lightweight, fast â€” used for DNS, DHCP, video streaming, online gaming, VoIP.",
        "exam_tip": "TCP 3-way handshake: SYN â†’ SYN-ACK â†’ ACK. 4-way termination: FIN â†’ ACK, FIN â†’ ACK. TCP has flow control (sliding window) and congestion control (slow start, congestion avoidance). UDP has none of these â€” that's why it's faster."
    },
    "osi model": {
        "title": "OSI 7-Layer Reference Model",
        "subject": "CN",
        "explanation": "A conceptual framework dividing network communication into 7 layers: Physical, Data Link, Network, Transport, Session, Presentation, Application. Each layer provides services to the layer above and uses services of the layer below.",
        "complexity": "Mnemonic (top-down): **All People Seem To Need Data Processing** (Application, Presentation, Session, Transport, Network, Data Link, Physical)",
        "exam_tip": "Key protocols per layer â€” Application: HTTP, FTP, SMTP, DNS | Transport: TCP, UDP | Network: IP, ICMP, ARP | Data Link: Ethernet, MAC | Physical: cables, hubs. **IP addressing is at Network layer (L3)**. Switches work at L2, Routers at L3. The OSI model is theoretical; TCP/IP model is practical (4 layers)."
    },
    "ip addressing": {
        "title": "IP Addressing, Subnetting & CIDR",
        "subject": "CN",
        "explanation": "IPv4: 32-bit address in dotted-decimal (e.g. 192.168.1.1). Classes: A (0-127), B (128-191), C (192-223). **Subnetting** divides a network into smaller sub-networks using a **subnet mask**. CIDR notation: 192.168.1.0/24 means 24 bits for network, 8 for hosts.",
        "complexity": "Hosts per subnet = 2^(host bits) âˆ’ 2 (subtract network & broadcast). /24 â†’ 254 hosts. /25 â†’ 126 hosts. /30 â†’ 2 hosts (point-to-point links).",
        "exam_tip": "Subnetting trick: write out the subnet mask in binary. Borrowed bits = extra subnet bits. Number of subnets = 2^(borrowed bits). Formula: Network Address = IP AND Subnet Mask. Broadcast = Network Address OR (NOT Subnet Mask). VLSM allows different subnet sizes within one network."
    },

    # â”€â”€ DATABASE MANAGEMENT SYSTEMS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "normalization": {
        "title": "Database Normalization (1NF â†’ BCNF)",
        "subject": "DBMS",
        "explanation": "A technique to organize database tables to reduce **data redundancy** and eliminate anomalies (insert, update, delete). Each normal form builds on the previous.",
        "complexity": "1NF: Atomic values, no repeating groups | 2NF: 1NF + No Partial Dependency (non-key attribute depends on full primary key) | 3NF: 2NF + No Transitive Dependency | BCNF: Every determinant is a candidate key",
        "exam_tip": "Partial dependency only occurs with **composite primary keys**. To check 3NF: for every FD Xâ†’Y, either X is a superkey OR Y is a prime attribute. BCNF is stricter â€” X must always be a superkey. Decomposition must be lossless-join and dependency-preserving."
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
        "complexity": "Concurrency issues: Dirty Read, Non-repeatable Read, Phantom Read. Isolation Levels: READ UNCOMMITTED â†’ READ COMMITTED â†’ REPEATABLE READ â†’ SERIALIZABLE.",
        "exam_tip": "Atomicity is ensured by **rollback/undo logs**. Durability by **redo logs/WAL (Write-Ahead Logging)**. Serializable is the strictest isolation level â€” prevents all anomalies but has lowest concurrency. Most DBs default to READ COMMITTED. Two-Phase Locking (2PL) ensures serializability: Growing Phase (acquire locks) then Shrinking Phase (release locks)."
    },

    # â”€â”€ OBJECT-ORIENTED PROGRAMMING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "polymorphism": {
        "title": "Polymorphism in OOP",
        "subject": "OOP",
        "explanation": "The ability of an entity to take multiple forms. **Compile-time (Static) Polymorphism**: Method Overloading â€” same method name, different parameters, resolved at compile time. **Runtime (Dynamic) Polymorphism**: Method Overriding â€” subclass overrides parent method, resolved at runtime via virtual function table (vtable).",
        "complexity": "Static Binding: faster (resolved at compile time). Dynamic Binding: flexible (resolved at runtime via vtable pointer).",
        "exam_tip": "In C++: use `virtual` keyword for runtime polymorphism. In Java: all non-static, non-final methods are virtual by default. Key: `Animal a = new Dog(); a.sound()` â€” calls Dog's sound() due to dynamic dispatch. Pure virtual function (`=0` in C++) makes class abstract."
    },
    "inheritance": {
        "title": "Inheritance in OOP",
        "subject": "OOP",
        "explanation": "A mechanism where a derived class (child) acquires properties and behaviors of a base class (parent). Types: Single, Multiple (C++, not Java â€” use interfaces), Multilevel, Hierarchical, Hybrid. `IS-A` relationship.",
        "complexity": "Code reuse without duplication. Method Resolution Order (MRO) in Python follows C3 linearization for multiple inheritance.",
        "exam_tip": "Java doesn't support multiple class inheritance (diamond problem) â€” uses **interfaces** instead. C++ supports it but requires `virtual` base class to solve diamond problem. Constructor order: Parent constructor called first (Base â†’ Derived). Destructor order: reverse (Derived â†’ Base). Abstract class has at least one pure virtual/abstract method."
    },
    "encapsulation": {
        "title": "Encapsulation & Abstraction in OOP",
        "subject": "OOP",
        "explanation": "**Encapsulation**: bundling data (attributes) and methods that operate on that data within a class, and restricting direct access using access modifiers (private, protected, public). Achieved via **getters/setters**. **Abstraction**: hiding implementation details, exposing only the interface â€” achieved via abstract classes and interfaces.",
        "complexity": "Access control: private (class only) < protected (class + subclasses) < public (everyone). Package-private (default in Java): within same package.",
        "exam_tip": "Encapsulation = data hiding. Abstraction = implementation hiding. They work together. A well-encapsulated class exposes only a minimal public API. Abstraction reduces complexity â€” user of a `List` doesn't need to know if it's ArrayList or LinkedList internally."
    },

    # â”€â”€ COMPUTER ORGANIZATION & ARCHITECTURE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "cache memory": {
        "title": "Cache Memory & Locality of Reference",
        "subject": "COA",
        "explanation": "A small, fast memory between the CPU and main RAM. Exploits **temporal locality** (recently accessed data likely accessed again) and **spatial locality** (nearby addresses likely accessed soon). Organized in levels: L1 (fastest, smallest, on-chip) > L2 > L3.",
        "complexity": "Cache hit: data found in cache (fast). Cache miss: data fetched from RAM (slow). Hit rate typically 90â€“99%. Effective Access Time = hit-rate Ã— cache-time + (1-hit-rate) Ã— memory-time.",
        "exam_tip": "Mapping techniques: **Direct Mapping** (simple, high conflict misses), **Fully Associative** (no conflict, expensive), **Set-Associative** (compromise, most common in practice). Cache replacement policies: LRU, FIFO, Random. Write policies: Write-Through (immediately to RAM, simpler) and Write-Back (only on eviction, faster but complex)."
    },
    "pipeline": {
        "title": "CPU Pipelining & Hazards",
        "subject": "COA",
        "explanation": "Pipelining overlaps execution of multiple instructions by dividing instruction execution into stages (IF â†’ ID â†’ EX â†’ MEM â†’ WB). Like an assembly line â€” while one instruction is in EX stage, the next is in ID, and the one after is being Fetched.",
        "complexity": "Ideal speedup = number of pipeline stages. Throughput = 1 instruction per clock cycle (after pipeline fills). CPI (Cycles Per Instruction) â†’ approaches 1 with deep pipelining.",
        "exam_tip": "Pipeline **hazards**: (1) **Structural** â€” resource conflict (two instructions need same unit). (2) **Data** â€” instruction depends on result of previous instruction (RAW, WAR, WAW). Solved by forwarding/bypassing or stalling. (3) **Control** â€” branch instructions cause uncertainty. Solved by branch prediction. Stalls (bubbles) reduce performance."
    },

    # â”€â”€ THEORY OF COMPUTATION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "automata": {
        "title": "Automata Theory: DFA, NFA & Regular Languages",
        "subject": "TOC",
        "explanation": "**DFA** (Deterministic Finite Automaton): for each state and input symbol, exactly one transition. **NFA** (Non-Deterministic FA): zero or more transitions per state/symbol. Both recognize exactly the **Regular Languages**. Every NFA can be converted to an equivalent DFA (subset construction, may exponentially increase states).",
        "complexity": "DFA/NFA: O(N) to process string of length N. NFAâ†’DFA conversion: up to 2^N DFA states from N NFA states.",
        "exam_tip": "Regular Languages closed under: union, concatenation, star, complement, intersection. Non-regular languages (proven by **Pumping Lemma**): {a^n b^n}, {a^(nÂ²)}, palindromes. Context-Free Languages (CFG/PDA) cover {a^n b^n}. Turing Machines recognize Recursively Enumerable languages. Chomsky hierarchy: Regular âŠ‚ CFL âŠ‚ CSL âŠ‚ RE."
    },

    # â”€â”€ SOFTWARE ENGINEERING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "sdlc": {
        "title": "Software Development Life Cycle (SDLC) Models",
        "subject": "SE",
        "explanation": "Structured process for planning, creating, testing, and delivering software. Models: **Waterfall** (sequential, rigid), **Agile** (iterative sprints, flexible), **Spiral** (risk-driven, for large projects), **V-Model** (testing at each stage), **RAD** (Rapid Application Development).",
        "complexity": "Waterfall: simple but inflexible â€” changes expensive after requirements frozen. Agile: 2-week sprints, continuous feedback, handles change well. SCRUM (Agile framework): roles = Product Owner, Scrum Master, Dev Team.",
        "exam_tip": "SDLC phases: Requirements â†’ Design â†’ Implementation â†’ Testing â†’ Deployment â†’ Maintenance. Testing types: Unit (module), Integration (module+module), System (full system), Acceptance (UAT by client). **COCOMO model** for cost estimation. Agile values: Individuals & interactions > Processes & tools."
    },

    # â”€â”€ DATA STRUCTURES (ADDITIONAL) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "array": {
        "title": "Arrays & Strings â€” Foundation Data Structure",
        "subject": "DSA",
        "explanation": "An array stores elements of the **same type** in contiguous memory locations, accessed via zero-based index. Strings are character arrays. Key operations: traversal O(N), access O(1), insertion/deletion O(N) (shifting). 2D arrays use row-major order in C/Java.",
        "complexity": "Access: O(1) | Search (unsorted): O(N) | Search (sorted + Binary Search): O(log N) | Insert/Delete (end): O(1) amortised | Insert/Delete (middle): O(N)",
        "exam_tip": "Sliding window technique reduces O(NÂ²) substring problems to O(N). Two-pointer approach solves sorted-array pair-sum in O(N). Common interview patterns: kadane's algorithm (max subarray sum O(N)), prefix sum array (range query O(1) after O(N) build). Always clarify whether the array is sorted before choosing a search algorithm."
    },
    "heap": {
        "title": "Heap Data Structure & Priority Queue",
        "subject": "DSA",
        "explanation": "A **complete binary tree** satisfying the heap property. **Min-Heap**: parent â‰¤ children (root = minimum). **Max-Heap**: parent â‰¥ children (root = maximum). Stored as an array â€” parent of index i is at âŒŠ(i-1)/2âŒ‹; children at 2i+1 and 2i+2.",
        "complexity": "Insert (heapify-up): O(log N) | Delete-min/max (heapify-down): O(log N) | Build heap from array: O(N) â€” NOT O(N log N) | Peek min/max: O(1)",
        "exam_tip": "Heap is the backbone of **Priority Queue** and **Heap Sort** (O(N log N) in-place). Build-heap is O(N) because most elements are near the bottom (do heapify-down from N/2 to 0). Top-K elements problem: use a Min-Heap of size K â€” O(N log K). Dijkstra's shortest path uses a Min-Heap. Java: `PriorityQueue`. Python: `heapq` (min-heap only â€” negate values for max)."
    },
    "greedy algorithm": {
        "title": "Greedy Algorithms",
        "subject": "DSA",
        "explanation": "Makes the **locally optimal choice** at each step hoping to reach the global optimum. No backtracking. Works when the problem has **Greedy Choice Property** (local optimal â†’ global optimal) and **Optimal Substructure**.",
        "complexity": "Activity Selection: O(N log N) | Fractional Knapsack: O(N log N) | Huffman Coding: O(N log N) | Kruskal's MST: O(E log E) | Prim's MST: O(E log V)",
        "exam_tip": "Greedy vs DP: Greedy makes one irreversible choice per step; DP explores all subproblems. Greedy fails for 0/1 Knapsack (use DP instead) but works for Fractional Knapsack. Classic greedy problems: **Activity Selection** (pick max non-overlapping intervals), **Huffman Encoding** (minimum prefix-free code), **Coin Change** (only works for canonical coin systems â€” fails for arbitrary denominations)."
    },
    "recursion": {
        "title": "Recursion & Backtracking",
        "subject": "DSA",
        "explanation": "**Recursion**: a function calls itself with a smaller input until a **base case** is reached. Every recursive call goes onto the call stack. **Backtracking**: try a solution, and if it fails, undo (backtrack) and try the next option â€” essentially DFS on the solution space.",
        "complexity": "Time: depends on recurrence. T(N) = 2T(N/2) + O(N) â†’ O(N log N) (Merge Sort). T(N) = T(N-1) + O(1) â†’ O(N) (Factorial). Space: O(depth of recursion) for the call stack.",
        "exam_tip": "Solve recurrences with **Master Theorem**: T(N) = aT(N/b) + f(N). Three cases based on f(N) vs N^(log_b a). Backtracking classics: N-Queens, Sudoku solver, Rat in a Maze, Subset Sum. Always define the base case first â€” missing base case = infinite recursion = stack overflow. Tail recursion can be optimised by compilers into a loop."
    },

    # â”€â”€ OPERATING SYSTEMS (ADDITIONAL) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "file system": {
        "title": "File Systems & I/O in OS",
        "subject": "OS",
        "explanation": "A file system organises data on storage as a hierarchy of directories and files. Key concepts: **inode** (stores metadata â€” permissions, size, pointers to data blocks), **FAT** (File Allocation Table â€” simple linked list of blocks), **inode-based** (Unix ext4 â€” direct, single-indirect, double-indirect block pointers).",
        "complexity": "Disk access is 10âµÃ— slower than RAM. Disk scheduling algorithms minimise seek time: FCFS, SSTF (Shortest Seek Time First), SCAN (elevator), C-SCAN (circular), LOOK.",
        "exam_tip": "**Inode structure**: 12 direct pointers + 1 single-indirect + 1 double-indirect + 1 triple-indirect. For block size B and pointer size P: max file size = 12B + (B/P)B + (B/P)Â²B + (B/P)Â³B. Disk scheduling: SSTF minimises seek but causes starvation. SCAN is the standard elevator algorithm â€” most commonly tested. File permissions in Unix: rwx = read(4) write(2) execute(1). `chmod 755` = rwxr-xr-x."
    },
}

# â”€â”€ Keyword aliases â†’ map alternate phrasings to canonical keys â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
}

# â”€â”€ Student Health Triage Knowledge Base â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Keys are lowercase trigger words. HEALTH_ALIASES maps synonyms to canonical keys.

HEALTH_SYMPTOMS = {
    "fever": {
        "condition": "Mild Viral Fever / High Temperature",
        "severity": "Moderate",
        "first_aid": "Paracetamol (PCM 500mg/650mg) after food if temperature > 99.5Â°F. Apply a wet cloth on forehead and wrists. Stay in a cool, ventilated room.",
        "home_remedy": "Drink warm water with ORS (Electral/Glucon-D) every 2 hours. Complete bed rest. Avoid cold drinks, fans directly on body. Sip warm ginger-tulsi tea.",
        "doctor_alert": "ðŸš¨ Rush to campus medical room if: fever > 102Â°F with shivering, fever persists beyond 48 hours, rash appears, or neck stiffness occurs (could indicate meningitis)."
    },
    "headache": {
        "condition": "Tension Headache / Digital Eye Strain",
        "severity": "Mild-Moderate",
        "first_aid": "Immediate: 20-min screen break in a dim room. Apply Amrutanjan/Vicks balm on temples & forehead. If severe: Paracetamol 500mg with water (not empty stomach).",
        "home_remedy": "Drink 2â€“3 large glasses of water immediately (dehydration is the #1 cause in students). Gentle neck & shoulder stretches. Cold/hot compress on neck. Peppermint oil roll-on on temples.",
        "doctor_alert": "ðŸš¨ See a doctor if: sudden severe 'thunderclap' headache, headache with vomiting + light sensitivity (migraine or worse), blurred vision, or headache after a head injury."
    },
    "cold": {
        "condition": "Common Cold, Runny Nose & Sore Throat",
        "severity": "Mild",
        "first_aid": "Steam inhalation (plain hot water or with Vicks VapoRub) twice daily. Cetirizine 10mg at bedtime for heavy sneezing/runny nose. Throat lozenges (Strepsils) for soreness.",
        "home_remedy": "Warm salt water gargle 3 times a day (Â½ tsp salt in 1 glass warm water). Hot ginger-tulsi-honey tea. Stay hydrated. Avoid cold water, ice cream, and AC directly on body.",
        "doctor_alert": "ðŸš¨ Consult physician if: cold lasts > 10 days, severe ear pain, greenish/yellow nasal discharge (bacterial infection), or high fever develops alongside cold."
    },
    "cough": {
        "condition": "Dry or Wet Cough & Throat Irritation",
        "severity": "Mild-Moderate",
        "first_aid": "Strepsils/Koflet lozenges for throat irritation. Steam inhalation 2Ã—/day. For wet cough: Benadryl/Chericof syrup (expectorant) 10ml after meals. For dry cough: Honitus/Dabur honey-ginger syrup.",
        "home_remedy": "Warm turmeric milk (Haldi doodh with a pinch of pepper and ghee) before sleeping. 1 tsp honey with a pinch of black pepper and ginger juice. Avoid cold beverages and dusty environments.",
        "doctor_alert": "ðŸš¨ See a doctor if: cough persists > 2 weeks, blood in sputum, chest pain while coughing, or breathlessness accompanies the cough."
    },
    "stomach": {
        "condition": "Stomach Ache / Abdominal Cramps",
        "severity": "Moderate",
        "first_aid": "Identify location: Upper abdomen â†’ acidity (take Gelusil/Eno). Lower abdomen cramps â†’ Meftal Spas (antispasmodic) 1 tablet. Apply warm water bottle on abdomen. Sip warm water slowly.",
        "home_remedy": "Drink coconut water or ORS for rehydration. Eat plain khichdi, curd-rice, or bananas â€” avoid spicy hostel mess food. Ajwain (carom seeds) in warm water relieves gas/cramps quickly.",
        "doctor_alert": "ðŸš¨ Emergency: severe sudden pain in lower-right abdomen (appendicitis risk), blood in stool, vomiting blood, or fever + stomach pain together â€” go to hospital immediately."
    },
    "acidity": {
        "condition": "Acid Reflux / Heartburn / Gastritis",
        "severity": "Mild-Moderate",
        "first_aid": "Gelusil / Digene antacid gel 2 teaspoons after meals. Eno fruit salt in water for instant relief. Pantoprazole 40mg (PPI) before breakfast for persistent hyperacidity â€” available at campus dispensary.",
        "home_remedy": "Cold milk (without sugar) gives instant relief by neutralizing acid. Sip jeera (cumin) water or fennel seed (saunf) water. Avoid lying flat for 2 hours after eating. Eat small, frequent meals.",
        "doctor_alert": "ðŸš¨ See a doctor if: burning pain that radiates to jaw/left arm (cardiac symptom), difficulty swallowing, black tarry stools, or frequent unexplained vomiting."
    },
    "stress": {
        "condition": "Exam Anxiety, Mental Fatigue & Burnout",
        "severity": "Moderate â€” Needs Attention",
        "first_aid": "**4-7-8 Breathing**: Inhale for 4s â†’ Hold for 7s â†’ Exhale slowly for 8s. Repeat 4 cycles. This activates the parasympathetic nervous system instantly. Take a 15-minute walk outside â€” sunlight boosts serotonin.",
        "home_remedy": "Ashwagandha (KSM-66) supplement reduces cortisol with consistent use. Chamomile tea before bed for better sleep. Avoid energy drinks â€” they worsen anxiety. Write down tomorrow's tasks to declutter the mind before sleeping.",
        "doctor_alert": "ðŸš¨ Please reach out to: College Counselor (Student Wellness Center), iCall (9152987821 â€” free student helpline), or Vandrevala Foundation (1860-2662-345, 24/7 free). You are not alone. Exams do not define your worth."
    },
    "vomiting": {
        "condition": "Nausea & Vomiting (Food Poisoning / Gastroenteritis)",
        "severity": "Moderate",
        "first_aid": "Stop eating solid food for 2â€“4 hours. Sip cold water or ice chips slowly. Ondansetron 4mg (Emeset/Zofer) â€” anti-nausea tablet available at campus dispensary â€” under tongue or swallowed with water.",
        "home_remedy": "Rehydrate with ORS (Electral packet in 1L water) to prevent dehydration. Once vomiting stops: start with bland food â€” plain toast, banana, boiled rice. Ginger tea with honey reduces nausea naturally.",
        "doctor_alert": "ðŸš¨ See a doctor if: vomiting lasts > 24 hours, blood in vomit, severe dehydration (dry mouth, no urination for 8h), high fever accompanying vomiting, or vomiting after a head injury."
    },
    "dehydration": {
        "condition": "Dehydration (Common in hot weather & exams)",
        "severity": "Mild-Severe depending on level",
        "first_aid": "Drink ORS (Oral Rehydration Solution) â€” 1 Electral packet dissolved in 1 litre water. Sip continuously, do not gulp. Sports drinks (Gatorade/Glucon-D) are acceptable. Avoid plain water only â€” you need electrolytes.",
        "home_remedy": "Coconut water is nature's ORS â€” rich in potassium and natural electrolytes. Diluted buttermilk with a pinch of salt and cumin. Eat water-rich fruits: watermelon, cucumber, oranges. Set phone reminders to drink water every 45 minutes.",
        "doctor_alert": "ðŸš¨ Emergency signs: confusion or dizziness, no urination for > 8 hours, rapid heartbeat, sunken eyes, skin that doesn't spring back when pinched â€” these indicate severe dehydration, visit health center immediately."
    },
    "eye strain": {
        "condition": "Digital Eye Strain / Computer Vision Syndrome",
        "severity": "Mild",
        "first_aid": "**20-20-20 Rule**: every 20 minutes, look at something 20 feet away for 20 seconds. Lubricating eye drops (Refresh Tears / Systane Ultra) â€” 1â€“2 drops per eye â€” available at any pharmacy. Reduce screen brightness and enable night mode.",
        "home_remedy": "Splash cold water on closed eyes 3â€“4 times a day. Cucumber slices on eyes for 10 minutes. Rose water eye drops (Itone/Optique) soothe irritation naturally. Ensure adequate lighting while studying â€” reading in dim light strains eyes.",
        "doctor_alert": "ðŸš¨ See an eye doctor if: persistent redness or yellow discharge (conjunctivitis), sudden vision blur or floaters, pain inside the eyeball, or sensitivity to light that doesn't resolve in 24 hours."
    },
    "back pain": {
        "condition": "Lower Back Pain / Posture-Related Pain",
        "severity": "Mild-Moderate",
        "first_aid": "Apply warm compress (hot water bag) on the painful area for 15â€“20 minutes. Combiflam (Ibuprofen + Paracetamol) 1 tablet after food for moderate pain. Avoid sitting continuously â€” stand and walk every 30â€“45 minutes.",
        "home_remedy": "**Knee-to-Chest Stretch**: lie on back, pull both knees to chest, hold 30s â€” relieves lower back tension instantly. **Cat-Cow Pose** (yoga). Sleep on a firm mattress, not a soft sofa. Improve desk posture â€” monitor at eye level, feet flat on floor.",
        "doctor_alert": "ðŸš¨ See a doctor if: pain radiates down the leg (sciatica), numbness/tingling in legs, back pain after a fall/accident, or pain that wakes you from sleep and doesn't improve with rest."
    },
    "insomnia": {
        "condition": "Insomnia / Sleep Deprivation (Pre-Exam Sleep Disorder)",
        "severity": "Moderate â€” affects academic performance significantly",
        "first_aid": "**Progressive Muscle Relaxation**: tense each muscle group for 5s, release â€” starting from toes to head. Melatonin 3mg (sleep onset supplement, non-addictive) â€” take 30 minutes before bed. Available at campus pharmacy.",
        "home_remedy": "Warm milk with a pinch of nutmeg (jaiphal) before bed â€” contains tryptophan, a natural sleep aid. Chamomile tea. No screens 1 hour before sleep (blue light suppresses melatonin). Keep room cool (18â€“22Â°C is optimal for sleep). Same bedtime daily resets circadian rhythm.",
        "doctor_alert": "ðŸš¨ Consult a doctor if: unable to sleep for > 3 consecutive nights, sleep paralysis episodes, extreme daytime sleepiness affecting studies, or suspected sleep apnea (loud snoring + gasping)."
    },
    "allergy": {
        "condition": "Allergic Reaction (Skin / Nasal / Food Allergy)",
        "severity": "Mild-Severe depending on type",
        "first_aid": "For **nasal allergy** (sneezing, watery eyes): Cetirizine 10mg or Levocetirizine 5mg at night â€” available OTC. For **skin rash/hives**: Calamine lotion topically + Cetirizine orally. Avoid identified triggers. Cold compress on itchy skin.",
        "home_remedy": "Local raw honey (1 tsp/day) may gradually reduce seasonal pollen allergies over weeks. Neti pot (saline nasal wash) clears allergens from nasal passages. Shower immediately after coming from outdoors during pollen season.",
        "doctor_alert": "ðŸš¨ **EMERGENCY**: anaphylaxis signs = sudden throat tightening, difficulty breathing, swelling of lips/tongue, dizziness after eating something â€” this is life-threatening. Call college emergency or go to hospital IMMEDIATELY. May need epinephrine injection."
    },
    "sprain": {
        "condition": "Ankle / Wrist Sprain (Sports / Lab Injury)",
        "severity": "Mild-Moderate",
        "first_aid": "**RICE Protocol**: **R**est (stop activity immediately), **I**ce (ice pack wrapped in cloth for 15â€“20 min, every 2 hours), **C**ompression (crepe bandage wrap â€” not too tight), **E**levation (keep limb elevated above heart level). Combiflam for pain/swelling.",
        "home_remedy": "Turmeric paste (haldi + mustard oil) warm compress reduces inflammation. After 48â€“72 hours (no ice), switch to warm compress to promote healing. Gentle range-of-motion exercises after 2â€“3 days to prevent stiffness.",
        "doctor_alert": "ðŸš¨ See a doctor if: unable to bear weight at all, severe swelling/bruising appearing quickly (possible fracture), deformity visible, or no improvement after 3â€“4 days of RICE treatment. X-ray may be needed to rule out fracture."
    },
    "diarrhea": {
        "condition": "Diarrhea / Loose Motions (Gastroenteritis / Food Contamination)",
        "severity": "Moderate â€” watch for dehydration",
        "first_aid": "Stop solid food for 4â€“6 hours. Start ORS immediately â€” 1 Electral packet in 1L water, sip every 15 minutes. Loperamide (Eldoper/Imodium) 2mg tablet for acute loose motions â€” reduces frequency. Avoid dairy, raw food, and oily mess food.",
        "home_remedy": "BRAT diet once appetite returns: **B**anana, **R**ice (plain), **A**pplesauce, **T**oast. Curd/probiotic yoghurt restores gut bacteria. Tender coconut water replenishes electrolytes naturally. Cumin-coriander water (jeera-dhaniya) soothes the gut. Avoid caffeine and spicy food for 48 hours.",
        "doctor_alert": "ðŸš¨ See a doctor if: more than 10 loose motions in 24 hours, blood/mucus in stool, high fever + diarrhea (dysentery risk), or signs of severe dehydration (rapid pulse, dizziness, no urination > 6 hours). Oral rehydration must be aggressive â€” diarrhea can cause dangerous electrolyte loss within hours."
    },
    "muscle pain": {
        "condition": "Muscle Soreness / Cramps (Post-Exercise or Prolonged Sitting)",
        "severity": "Mild",
        "first_aid": "Apply **Moov/Volini** topical spray or gel on the affected area for instant relief. For cramping muscle: stretch and hold the muscle in the opposite direction. Combiflam tablet for moderate pain. Warm bath/shower relaxes muscle tension.",
        "home_remedy": "Magnesium deficiency is the most common cause of muscle cramps in students â€” eat bananas, spinach, nuts. Stay hydrated. **Epsom salt soak** (magnesium sulphate in warm water for 15 min). Light stretching and walking increases blood flow to muscles.",
        "doctor_alert": "ðŸš¨ See a doctor if: muscle weakness with no apparent cause, cramps accompanied by swelling and redness (could be DVT â€” deep vein thrombosis), or severe chest/arm pain (cardiac)."
    },
    "toothache": {
        "condition": "Toothache / Dental Pain",
        "severity": "Mild-Severe",
        "first_aid": "Ibuprofen (Combiflam) 400mg after food for pain relief â€” most effective for dental pain. Clove oil (eugenol) â€” apply 1â€“2 drops on a cotton ball directly to the painful tooth â€” natural anaesthetic. Rinse with warm salt water every 2 hours.",
        "home_remedy": "Garlic clove paste on the tooth (allicin is antibacterial). Cold compress on the cheek outside reduces swelling. Avoid very hot, cold, or sweet food â€” use the opposite side of mouth to chew. OTC dental gel (Dentogel/Metrogyl) applied to gums reduces inflammation.",
        "doctor_alert": "ðŸš¨ Visit a dentist urgently if: swelling spreading to jaw/neck (abscess can be life-threatening), fever with toothache (infection spreading), severe throbbing pain not relieved by painkillers, or a broken/cracked tooth with exposed nerve."
    },
}

# â”€â”€ Health keyword aliases â†’ canonical keys â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/admin/all_students', methods=['GET'])
def get_all_students_admin():
    """Returns full attendance + marks for every student â€” used by Faculty Management Table."""
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

# â”€â”€ Chat helper functions (longest-alias-first matching) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    data = load_data()
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
                f"### ðŸ©º {info['condition']}\n"
                f"**Severity:** {info['severity']}\n\n"
                f"ðŸ’Š **First-Aid & Safe Medicine:**\n{info['first_aid']}\n\n"
                f"ðŸµ **Home Remedies:**\n{info['home_remedy']}\n\n"
                f"{info['doctor_alert']}"
            )
        n = len(matched_symptoms)
        header = (
            f"ðŸ©º **Campus Health AI â€” {n} Condition{'s' if n > 1 else ''} Detected**\n\n"
            if n > 1
            else "ðŸ©º **Campus Health AI â€” Symptom Triage**\n\n"
        )
        footer = "\n\n---\n*AI first-aid guidance only â€” not a substitute for professional care. Visit Campus Clinic, Health Block Room 04.*"
        return jsonify({"reply": header + "\n".join(sections) + footer, "action": "health"})

    # â”€â”€ 2. ACADEMIC DOUBT SOLVER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    resolved_topic = _resolve_study(msg_lower)
    if resolved_topic and resolved_topic in STUDY_KNOWLEDGE:
        s_info = STUDY_KNOWLEDGE[resolved_topic]
        subject_tag = s_info.get('subject', 'CS')
        return jsonify({
            "reply": (
                f"ðŸ“š **AI Academic Tutor [{subject_tag}]**\n"
                f"### {s_info['title']}\n\n"
                f"---\n"
                f"ðŸ’¡ **Core Concept:**\n{s_info['explanation']}\n\n"
                f"âš¡ **Complexity / Key Properties:**\n`{s_info['complexity']}`\n\n"
                f"ðŸŽ¯ **Exam & Viva Pro-Tip:**\n{s_info['exam_tip']}"
            ),
            "action": "academic"
        })

    # â”€â”€ 3. MARKS & RESULT QUERIES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if any(k in msg_lower for k in ['mark', 'score', 'pass', 'fail', 'result', 'grade']):
        marks_map = active_stu.get('marks', {}) if active_stu else {}
        sub_list = data.get('subjects', [])
        reply_lines = [f"ðŸ“‹ **Academic Performance & Results â€” {student_name}**\n"]
        for s in sub_list:
            m = marks_map.get(s['id'], {"score": "Not Declared", "total": 100, "status": "Pending"})
            badge = "ðŸŸ¢ Pass" if m['status'] == 'Pass' else ("ðŸ”´ Fail" if m['status'] == 'Fail' else "âšª Pending")
            reply_lines.append(f"â€¢ **{s['name']}** `{s['code']}`: {m['score']}/{m['total']} â€” {badge}")
        return jsonify({"reply": "\n".join(reply_lines), "action": None})

    # â”€â”€ 4. HACKATHONS & JOBS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if any(k in msg_lower for k in ['hackathon', 'job', 'internship', 'placement', 'contest', 'opportunity']):
        opps = data.get('opportunities', [])
        if opps:
            opp_text = "ðŸš€ **Active Hackathons & Job Opportunities:**\n\n"
            for o in opps[:3]:
                opp_text += f"â€¢ **[{o['category']}] {o['title']}**\n  â° Deadline: {o['deadline']}\n  ðŸ”— {o['link']}\n\n"
            return jsonify({"reply": opp_text, "action": None})

    # â”€â”€ 5. ATTENDANCE QUERIES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if any(k in msg_lower for k in ['attendance', 'bunk', 'shortage', 'present', 'absent', 'skip', 'miss']):
        att_map = active_stu.get('attendance', {}) if active_stu else {}
        sub_list = data.get('subjects', [])
        target = active_stu.get('target_attendance', 75)
        reply_lines = [f"ðŸ“Š **Attendance Report â€” {student_name}** (Target: {target}%)\n"]
        has_shortage = False
        for s in sub_list:
            a = att_map.get(s['id'], {"attended": 0, "total": 0, "percentage": 100.0})
            pct = a.get('percentage', 0)
            att = a.get('attended', 0)
            tot = a.get('total', 0)
            if pct < target:
                has_shortage = True
                needed = calculate_classes_needed(att, tot, target)
                reply_lines.append(f"â€¢ **{s['name']}**: {att}/{tot} ({pct}%) â€” âš ï¸ **SHORTAGE** â†’ Attend **{needed}** more class{'es' if needed != 1 else ''} to reach {target}%")
            else:
                bunks_left = calculate_max_bunks(att, tot, target)
                reply_lines.append(f"â€¢ **{s['name']}**: {att}/{tot} ({pct}%) â€” âœ… Safe (can skip **{bunks_left}** more)")
        reply_lines.append(
            f"\nðŸš¨ **Action Required:** Attend all flagged classes to avoid exam debarment." if has_shortage
            else f"\nðŸŽ‰ All subjects above {target}% â€” you're on track!"
        )
        return jsonify({"reply": "\n".join(reply_lines), "action": None})

    # â”€â”€ 6. TIMETABLE & VENUE QUERIES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if any(k in msg_lower for k in ['timetable', 'schedule', 'class', 'lecture', 'where', 'kahan', 'room', 'venue', 'teacher', 'faculty']):
        tt = data.get('timetable', [])
        if tt:
            tt_lines = ["ðŸ“… **Class Timetable & Venues for Today:**\n"]
            for idx, c in enumerate(tt, 1):
                status_tag = {"ongoing": "ðŸŸ¢ Live Now", "completed": "âœ… Done", "upcoming": "â³ Upcoming"}.get(c.get('status', 'upcoming'), "â³ Upcoming")
                tt_lines.append(
                    f"**{idx}. {c['subject']}** `{c.get('type','Theory')}` â€” {status_tag}\n"
                    f"   â° {c['time']} | ðŸ“ **{c['room']}** | ðŸ‘¨â€ðŸ« {c['faculty']}\n"
                )
            return jsonify({"reply": "\n".join(tt_lines), "action": None})

    # ── 7. AI FRIEND LIVE WEB SEARCH ENGINE (FOR ANY OTHER QUESTION) ──
    if user_msg:
        web_reply, web_action = ai_friend_web_search(user_msg, student_name)
        return jsonify({"reply": web_reply, "action": web_action})

    # Default fallback if message is empty
    return jsonify({
        "reply": f"👋 **Hello {student_name}!** Poochiye koi bhi sawaal—academics, health, campus ERP, ya internet se koi bhi general knowledge/tech question!",
        "action": None
    })

if __name__ == '__main__':
    print("[+] CampusGenie Ultimate Server starting on http://127.0.0.1:5000 ...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

