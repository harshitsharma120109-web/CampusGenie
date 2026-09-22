const http = require('http');
const app = require('./server');

const TEST_PORT = 5055;
const server = http.createServer(app);

server.listen(TEST_PORT, async () => {
  console.log(`[TEST] Server listening on port ${TEST_PORT}`);
  let passed = 0;
  let failed = 0;

  async function request(path, options = {}) {
    return new Promise((resolve, reject) => {
      const opt = {
        hostname: '127.0.0.1',
        port: TEST_PORT,
        path,
        method: options.method || 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        }
      };
      const req = http.request(opt, res => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode, data: JSON.parse(data) });
          } catch (e) {
            resolve({ status: res.statusCode, raw: data });
          }
        });
      });
      req.on('error', reject);
      if (options.body) {
        req.write(JSON.stringify(options.body));
      }
      req.end();
    });
  }

  try {
    // 1. Health check
    const rHealth = await request('/api/health');
    if (rHealth.status === 200 && rHealth.data.runtime === 'Node.js') {
      console.log('✅ 1. Health check passed:', rHealth.data.runtime, rHealth.data.version);
      passed++;
    } else {
      console.error('❌ 1. Health check failed', rHealth);
      failed++;
    }

    // 2. Student auth login
    const rLogin = await request('/api/auth/login', {
      method: 'POST',
      body: { role: 'student', identifier: '22CS1084', password: 'student123' }
    });
    if (rLogin.status === 200 && rLogin.data.success === true) {
      console.log('✅ 2. Student login passed:', rLogin.data.user.name);
      passed++;
    } else {
      console.error('❌ 2. Student login failed', rLogin);
      failed++;
    }

    // 3. Get Student Profile & Attendance
    const rStudent = await request('/api/student');
    if (rStudent.status === 200 && rStudent.data.subjects && rStudent.data.subjects.length > 0) {
      console.log(`✅ 3. Student profile passed: ${rStudent.data.subjects.length} subjects loaded`);
      passed++;
    } else {
      console.error('❌ 3. Student profile failed', rStudent);
      failed++;
    }

    // 4. RBAC Student Attendance Tamper Prevention
    const rRbac = await request('/api/attendance/mark', {
      method: 'POST',
      headers: { 'x-user-role': 'student' },
      body: { subject_id: 'os', status: 'present', caller_role: 'student' }
    });
    if (rRbac.status === 403 && rRbac.data.success === false) {
      console.log('✅ 4. RBAC 403 Forbidden check passed (Student tamper blocked)');
      passed++;
    } else {
      console.error('❌ 4. RBAC check failed', rRbac);
      failed++;
    }

    // 5. AI Chat Copilot - Binary Search DSA query
    const rChat = await request('/api/chat', {
      method: 'POST',
      body: { message: 'explain binary search' }
    });
    if (rChat.status === 200 && rChat.data.reply && rChat.data.reply.includes('Binary Search')) {
      console.log('✅ 5. AI Study Buddy passed: Binary Search explanation verified');
      passed++;
    } else {
      console.error('❌ 5. AI Study Buddy failed', rChat);
      failed++;
    }

    // 6. Fees Status Desk
    const rFees = await request('/api/fees/status');
    if (rFees.status === 200 && rFees.data.fees) {
      console.log('✅ 6. Fees desk passed: Total fee ₹' + rFees.data.fees.total_fee);
      passed++;
    } else {
      console.error('❌ 6. Fees desk failed', rFees);
      failed++;
    }

    // 7. Exam Seating Radar
    const rExam = await request('/api/exam/seating');
    if (rExam.status === 200 && rExam.data.seating && rExam.data.seating.seat_no) {
      console.log('✅ 7. Exam seating radar passed: ' + rExam.data.seating.seat_no);
      passed++;
    } else {
      console.error('❌ 7. Exam seating failed', rExam);
      failed++;
    }

    // 8. Mess Menu
    const rMess = await request('/api/mess/menu');
    if (rMess.status === 200 && rMess.data.success) {
      console.log('✅ 8. Mess menu passed');
      passed++;
    } else {
      console.error('❌ 8. Mess menu failed', rMess);
      failed++;
    }

    // 9. Placement Analyzer
    const rPlacement = await request('/api/placement/analyze', {
      method: 'POST',
      body: { skills: ['dsa', 'python', 'sql'], target_role: 'SDE' }
    });
    if (rPlacement.status === 200 && rPlacement.data.score > 0) {
      console.log(`✅ 9. Placement analyzer passed: Score ${rPlacement.data.score} (${rPlacement.data.readiness})`);
      passed++;
    } else {
      console.error('❌ 9. Placement analyzer failed', rPlacement);
      failed++;
    }

    console.log(`\n=============================================`);
    console.log(`TEST SUMMARY: ${passed} PASSED, ${failed} FAILED`);
    console.log(`=============================================`);

  } catch (err) {
    console.error('Test run error:', err);
    failed++;
  } finally {
    server.close(() => {
      console.log('[TEST] Server closed.');
      process.exit(failed > 0 ? 1 : 0);
    });
  }
});
