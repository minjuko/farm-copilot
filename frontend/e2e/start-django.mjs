import { spawn, execFileSync } from 'node:child_process';
import { mkdtemp, mkdir, rm, writeFile, lstat, readdir, readFile } from 'node:fs/promises';
import { lstatSync, readdirSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const backend = path.resolve(here, '../../backend');
const rootPathFile = path.join(here, '.farm-copilot-e2e-root-path');
const python = process.platform === 'win32'
  ? execFileSync('py', ['-3.11', '-c', 'import sys; print(sys.executable)'], { encoding: 'utf8' }).trim()
  : 'python';
const root = await mkdtemp(path.join(tmpdir(), 'farm-copilot-e2e-'));
const marker = path.join(root, '.farm-copilot-e2e-root');
const allowedRootEntries = ['.farm-copilot-e2e-root', 'db', 'media', 'private_media'];
for (const name of ['db', 'media', 'private_media']) await mkdir(path.join(root, name));
await writeFile(marker, 'isolated-local-e2e\n', { flag: 'wx' });
await writeFile(rootPathFile, root, { encoding: 'utf8', flag: 'w' });

const env = {
  ...process.env,
  DJANGO_SETTINGS_MODULE: 'config.e2e_settings',
  FARM_COPILOT_E2E_MODE: '1',
  FARM_COPILOT_E2E_ROOT: root,
  DJANGO_SECRET_KEY: 'local-browser-e2e-placeholder-key-not-for-production',
  DJANGO_USE_SQLITE: '1',
  DJANGO_DEBUG: 'true',
  DJANGO_ALLOWED_HOSTS: 'localhost,127.0.0.1',
  CORS_ALLOWED_ORIGINS: 'http://localhost:3000',
  CSRF_TRUSTED_ORIGINS: 'http://localhost:3000',
};

let server;
let stopping = false;
async function cleanup() {
  if (stopping) return;
  stopping = true;
  if (server && server.exitCode === null) {
    const exited = new Promise((resolve) => server.once('exit', resolve));
    server.kill('SIGTERM');
    await exited;
  }
  const stat = await lstat(root).catch(() => null);
  const expectedParent = path.resolve(tmpdir());
  if (stat?.isDirectory() && !stat.isSymbolicLink() && path.dirname(path.resolve(root)) === expectedParent && path.basename(root).startsWith('farm-copilot-e2e-')) {
    const actualMarker = await readFile(marker, 'utf8').catch(() => '');
    const entries = await readdir(root).catch(() => []);
    if (actualMarker === 'isolated-local-e2e\n' && entries.length === allowedRootEntries.length && entries.every((name) => allowedRootEntries.includes(name))) {
      await rm(root, { recursive: true, force: true });
    }
  }
}

function cleanupOnProcessExit() {
  const resolved = path.resolve(root);
  if (path.dirname(resolved) !== path.resolve(tmpdir()) || !path.basename(resolved).startsWith('farm-copilot-e2e-')) return;
  try {
    const rootStat = lstatSync(resolved);
    const markerContents = readFileSync(path.join(resolved, '.farm-copilot-e2e-root'), 'utf8');
    const entries = readdirSync(resolved).sort();
    if (rootStat.isDirectory() && !rootStat.isSymbolicLink()
      && markerContents === 'isolated-local-e2e\n'
      && entries.length === allowedRootEntries.length
      && entries.every((name, index) => name === [...allowedRootEntries].sort()[index])) {
      rmSync(resolved, { recursive: true, force: true });
    }
  } catch {
    // Leave the directory in place if its identity cannot be verified.
  }
}
process.once('exit', cleanupOnProcessExit);

try {
  const bootstrap = `
import os, sys
sys.path.insert(0, ${JSON.stringify(backend)})
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.e2e_settings')
import django
django.setup()
from django.core.management import call_command
call_command('migrate', interactive=False, verbosity=1)
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from detect.models import Pest, PestDetection
User = get_user_model()
owner, _ = User.objects.get_or_create(email='owner@example.test', defaults={'username': 'owner'})
owner.set_password('E2ePass!234'); owner.save()
other, _ = User.objects.get_or_create(email='other@example.test', defaults={'username': 'other'})
other.set_password('E2ePass!234'); other.save()
pest, _ = Pest.objects.get_or_create(code='e2e-fixture', defaults={'pest_name': '테스트 해충'})
for user in (owner, other):
    if not user.pest_detections.exists():
        row = PestDetection(user=user, pest=pest, confidence=0.91)
        row.image.save('fixture.png', ContentFile(bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c636000020000050001a5f645400000000049454e44ae426082')), save=True)
call_command('runserver', '127.0.0.1:8000', use_reloader=False)
`;
  server = spawn(python, ['-c', bootstrap], { cwd: backend, env, stdio: 'inherit' });
  server.once('error', (error) => { throw error; });
  server.once('exit', () => { if (!stopping) process.exitCode = 1; });
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (server.exitCode !== null) throw new Error('Django E2E server stopped during startup');
    try {
      const response = await fetch('http://localhost:8000/login/auth_check/');
      if (response.ok) break;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 500));
    if (attempt === 119) throw new Error('Django E2E server did not become ready');
  }
  process.on('SIGINT', async () => { await cleanup(); process.exit(130); });
  process.on('SIGTERM', async () => { await cleanup(); process.exit(143); });
  await new Promise((resolve) => server.once('exit', resolve));
} finally {
  await cleanup();
}
