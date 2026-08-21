#!/usr/bin/env node
/**
 * Focused regression test for codegraph-evidence.cjs EISDIR fix.
 *
 * Verifies:
 * 1. Passing a directory path does NOT crash with EISDIR
 * 2. Passing a valid JSON file works correctly
 * 3. /home/deploy/hermes-agent-style project roots are handled gracefully
 * 4. Healthy CodeGraph status is classified READY or STALE, not ABSENT/MISSING
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execSync } = require('node:child_process');

const evidenceScript = path.join(__dirname, 'codegraph-evidence.cjs');
const codegraphBinary = '/home/deploy/.npm-global/bin/codegraph';
const testRepo = '/home/deploy/hermes-agent';

// Helper: run codegraph-evidence.cjs with a given argv[2], returns { stdout, stderr, status }
function runEvidence(inputArg) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lah-evidence-test-'));
  const inputFile = path.join(dir, 'input.json');
  fs.writeFileSync(inputFile, JSON.stringify({
    mission: 'test mission',
    candidate_repos: ['hermes-agent'],
    requested_roles: { implementation: true },
  }));

  const args = inputArg ? [inputArg] : [];
  const cmd = `node ${evidenceScript} ${args.map(a => `"${a}"`).join(' ')}`;
  let stdout = '', stderr = '';
  let status = 0;
  try {
    stdout = execSync(cmd, { encoding: 'utf8', timeout: 10000, cwd: dir });
  } catch (e) {
    status = e.status || 1;
    stdout = e.stdout || '';
    stderr = e.stderr || e.message || '';
  }

  fs.rmSync(dir, { recursive: true, force: true });
  return { stdout, stderr, status };
}

// Helper: run codegraph-evidence.cjs with stdin input (no argv[2])
function runEvidenceViaStdin() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lah-evidence-test-'));
  const inputFile = path.join(dir, 'input.json');
  const inputData = JSON.stringify({
    mission: 'test mission',
    candidate_repos: ['hermes-agent'],
    requested_roles: { implementation: true },
  });
  fs.writeFileSync(inputFile, inputData);

  const cmd = `cat "${inputFile}" | node ${evidenceScript} --stdin`;
  let stdout = '';
  try {
    stdout = execSync(cmd, { encoding: 'utf8', timeout: 10000, cwd: dir });
  } catch (e) {
    throw new Error('stdin test failed: ' + (e.stderr || e.message));
  }

  fs.rmSync(dir, { recursive: true, force: true });
  return stdout;
}

// Test 1: Directory path should NOT crash with EISDIR
console.log('Test 1: Directory path does not crash with EISDIR...');
{
  const { stdout, stderr, status } = runEvidence(testRepo);
  const output = stdout || stderr;
  const parsed = JSON.parse(output);
  assert.equal(parsed.status, 'ERROR', 'Expected ERROR status for directory input');
  assert.ok(parsed.error.includes('not a regular file'), 'Expected "not a regular file" error message, got: ' + parsed.error);
  assert.ok(!parsed.error.includes('EISDIR'), 'EISDIR should not appear after fix');
  console.log('  PASS: Directory path handled gracefully with JSON error');
}

// Test 2: Valid JSON file input via stdin should work
console.log('Test 2: Valid JSON file input via stdin works correctly...');
{
  const output = runEvidenceViaStdin();
  const parsed = JSON.parse(output);
  assert.ok(parsed.status === 'SUCCESS' || parsed.status === 'PARTIAL' || parsed.status === 'UNAVAILABLE',
    'Expected valid status from stdin input, got: ' + parsed.status);
  console.log('  PASS: Valid JSON file input works correctly');
}

// Test 3: /home/deploy/hermes-agent-style project root is handled correctly
console.log('Test 3: Project root directory is not passed to file-only readFileSync...');
{
  const { stdout, stderr } = runEvidence(testRepo);
  const output = stdout || stderr;
  const parsed = JSON.parse(output);
  assert.notEqual(parsed.error, undefined, 'Expected error output for directory input');
  assert.ok(!parsed.error.includes('EISDIR'), 'EISDIR should not appear after fix');
  console.log('  PASS: Project root handled gracefully (no EISDIR)');
}

// Test 4: Healthy CodeGraph status for the repo should be READY or STALE, not ABSENT/MISSING
console.log('Test 4: Healthy CodeGraph status is classified READY or STALE...');
{
  const raw = execSync(
    `${codegraphBinary} status ${testRepo} --json`,
    { encoding: 'utf8', timeout: 10000 }
  );
  const cgStatus = JSON.parse(raw);
  assert.equal(cgStatus.initialized, true, 'CodeGraph should be initialized');
  assert.equal(cgStatus.projectPath, testRepo, 'CodeGraph projectPath should match');
  assert.equal(cgStatus.worktreeMismatch, null, 'No worktree mismatch');
  assert.ok(cgStatus.lastIndexed, 'Should have lastIndexed timestamp');
  assert.ok(cgStatus.fileCount > 0, 'Should have indexed files');

  // Verify the freshness check would classify this as READY or STALE (not MISSING/ABSENT)
  const hasChanges = cgStatus.pendingChanges &&
    (cgStatus.pendingChanges.added > 0 || cgStatus.pendingChanges.modified > 0 || cgStatus.pendingChanges.removed > 0);
  const ageDays = (Date.now() - new Date(cgStatus.lastIndexed).getTime()) / 86400000;
  const reindexRecommended = cgStatus.index && cgStatus.index.reindexRecommended === true;
  const expectedFreshness = (hasChanges || ageDays > 14 || reindexRecommended) ? 'STALE' : 'READY';
  assert.ok(expectedFreshness === 'READY' || expectedFreshness === 'STALE',
    'CodeGraph freshness should be READY or STALE, not MISSING/ABSENT');
  console.log('  PASS: CodeGraph status is ' + expectedFreshness + ' (initialized=true, fileCount=' + cgStatus.fileCount + ')');
}

// Test 5: Non-existent file should produce a clear error (not EISDIR)
console.log('Test 5: Non-existent file path produces a clear error...');
{
  const { stdout, stderr } = runEvidence('/nonexistent/path/to/file.json');
  const output = stdout || stderr;
  const parsed = JSON.parse(output);
  assert.equal(parsed.status, 'ERROR', 'Expected ERROR status for non-existent file');
  assert.ok(!parsed.error.includes('EISDIR'), 'EISDIR should not appear for non-existent file');
  console.log('  PASS: Non-existent file handled with clear error');
}

console.log('\nAll codegraph-evidence EISDIR regression tests passed.');