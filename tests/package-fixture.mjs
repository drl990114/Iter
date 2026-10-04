import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { access, mkdir, readFile, readdir, realpath } from 'node:fs/promises';
import { isAbsolute, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { extract } from 'tar';

export const packageRoot = fileURLToPath(new URL('../', import.meta.url));
export const skillRelativePath = 'skills/iterate-product';

export async function packFixture(fixtureRoot) {
  const npmCli = process.env.npm_execpath;
  assert.ok(npmCli, 'Run through npm test or npm run test:install to use the active npm installation.');
  const [packed] = JSON.parse(execFileSync(process.execPath, [
    npmCli, 'pack', '--json', '--ignore-scripts', '--pack-destination', fixtureRoot,
  ], { cwd: packageRoot, encoding: 'utf8', timeout: 30_000 }));
  const extractedRoot = join(fixtureRoot, 'unpacked');
  await mkdir(extractedRoot);
  await extract({ file: join(fixtureRoot, packed.filename), cwd: extractedRoot });
  return { packed, root: join(extractedRoot, 'package') };
}

export async function resourcePaths(directory, prefix = '') {
  const paths = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || ['tests', '__pycache__'].includes(entry.name) || /\.py[cod]$/.test(entry.name)) continue;
    const relativePath = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) paths.push(...await resourcePaths(join(directory, entry.name), relativePath));
    else paths.push(relativePath);
  }
  return paths.sort();
}

export async function assertResourcesMatch(actualDirectory, expectedDirectory) {
  const expectedPaths = await resourcePaths(expectedDirectory);
  assert.deepEqual(await resourcePaths(actualDirectory), expectedPaths);
  for (const path of expectedPaths) {
    assert.deepEqual(await readFile(join(actualDirectory, path)), await readFile(join(expectedDirectory, path)), `Resource changed: ${path}`);
  }
}

export function pythonCommand() {
  const candidates = process.platform === 'win32'
    ? [['py', ['-3']], ['python', []], ['python3', []]]
    : [['python3', []], ['python', []]];
  for (const [command, args] of candidates) {
    try {
      execFileSync(command, [...args, '-c', 'import sys; assert sys.version_info >= (3, 10)'], { stdio: 'pipe', timeout: 10_000 });
      return { command, args };
    } catch { /* Try the next supported Python launcher. */ }
  }
  throw new Error('Python 3.10+ is required for skill installation smoke tests.');
}

export function helperCommand(skillDirectory, workspace, iterHome, args, cwd = workspace) {
  assert.ok(isAbsolute(iterHome), 'Tests must use an explicit absolute temporary ITER_HOME.');
  const python = pythonCommand();
  const helper = join(skillDirectory, 'scripts/product_loop.py');
  return JSON.parse(execFileSync(python.command, [...python.args, helper, ...args, '--workspace', workspace], {
    cwd, encoding: 'utf8', timeout: 10_000,
    env: { ...process.env, ITER_HOME: iterHome, PYTHONDONTWRITEBYTECODE: '1' },
  }));
}

export async function assertInstalledHelperWorks(skillDirectory, workspace, cwd, iterHome) {
  await mkdir(workspace, { recursive: true });
  await mkdir(iterHome, { recursive: true });
  const paths = helperCommand(skillDirectory, workspace, iterHome, ['paths'], cwd);
  assert.equal(paths.iter_home, await realpath(iterHome));
  assert.equal(paths.exists, false);
  assert.equal(paths.legacy_exists, false);
  assert.equal(paths.migration_required, false);
  const storageRelative = relative(paths.iter_home, paths.storage_root);
  assert.ok(storageRelative && !storageRelative.startsWith('..') && !isAbsolute(storageRelative));
  await assert.rejects(access(paths.storage_root), { code: 'ENOENT' });
  helperCommand(skillDirectory, workspace, iterHome, ['init',
    '--objective', 'Check portable skill resources', '--metric', 'Local installation success'], cwd);
  const state = JSON.parse(await readFile(paths.state_path, 'utf8'));
  assert.equal(state.schema_version, 2);
  assert.equal(state.stage, 'research');
  assert.equal(state.objective, 'Check portable skill resources');
  for (const path of Object.values(state.artifacts)) {
    assert.ok(!isAbsolute(path) && !path.includes('.product-loop'));
    assert.ok((await readFile(join(paths.storage_root, path), 'utf8')).length > 0, `Missing generated artifact ${path}`);
  }
  const status = helperCommand(skillDirectory, workspace, iterHome, ['status'], cwd);
  assert.equal(status.stage, 'research');
  assert.equal(status.storage_root, paths.storage_root);
  assert.equal(status.state_path, paths.state_path);
  assert.equal(helperCommand(skillDirectory, workspace, iterHome, ['paths'], cwd).exists, true);
  await assert.rejects(access(join(workspace, '.product-loop')), { code: 'ENOENT' });
  return paths;
}
