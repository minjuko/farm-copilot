import { spawn } from 'node:child_process';
import { lstat, readdir, readFile, rm, unlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const frontend = path.resolve(here, '..');
const rootPathFile = path.join(here, '.farm-copilot-e2e-root-path');
const require = createRequire(import.meta.url);
const cli = require.resolve('@playwright/test/cli', { paths: [frontend] });
const child = spawn(process.execPath, [cli, 'test', ...process.argv.slice(2)], {
  cwd: frontend,
  env: process.env,
  stdio: 'inherit',
});

async function cleanupIsolatedRoot() {
  const rootValue = await readFile(rootPathFile, 'utf8').catch(() => '');
  await unlink(rootPathFile).catch(() => {});
  if (!rootValue) return;
  const root = path.resolve(rootValue);
  const stat = await lstat(root).catch(() => null);
  if (!stat?.isDirectory() || stat.isSymbolicLink()
    || path.dirname(root) !== path.resolve(tmpdir())
    || !path.basename(root).startsWith('farm-copilot-e2e-')) return;
  const marker = await readFile(path.join(root, '.farm-copilot-e2e-root'), 'utf8').catch(() => '');
  const entries = (await readdir(root).catch(() => [])).sort();
  const expected = ['.farm-copilot-e2e-root', 'db', 'media', 'private_media'];
  if (marker !== 'isolated-local-e2e\n'
    || entries.length !== expected.length
    || entries.some((entry, index) => entry !== expected[index])) return;
  await rm(root, { recursive: true, force: true });
}

try {
  const [code, signal] = await new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', (exitCode, exitSignal) => resolve([exitCode, exitSignal]));
  });
  await cleanupIsolatedRoot();
  process.exitCode = code ?? (signal ? 1 : 0);
} catch (error) {
  await cleanupIsolatedRoot();
  throw error;
}
