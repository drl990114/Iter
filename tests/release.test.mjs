import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { parse } from 'yaml';
import { modes, releaseFiles, selectIncrement, updateChangelog } from '../scripts/release.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const releaseScript = join(root, 'scripts/release.mjs');
const readJson = path => JSON.parse(readFileSync(path, 'utf8'));
const run = (cwd, executable, args, options = {}) => execFileSync(executable, args, {
  cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 60_000, ...options,
}).trim();
const git = (cwd, ...args) => run(cwd, 'git', args);

function fixture(t, version = '0.1.0', published = false) {
  const directory = mkdtempSync(join(tmpdir(), 'iter release '));
  t.after(() => rmSync(directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 }));
  const repo = join(directory, 'working tree');
  const remote = join(directory, 'remote.git');
  const candidate = join(directory, 'candidate');
  mkdirSync(repo);
  git(directory, 'init', '--bare', '--initial-branch=main', remote);
  git(repo, 'init', '--initial-branch=main');
  for (const [key, value] of Object.entries({
    'user.name': 'Release Test', 'user.email': 'release@example.invalid', 'commit.gpgsign': 'false',
    'tag.gpgsign': 'false', 'core.autocrlf': 'false', 'core.hooksPath': join(directory, 'no-hooks'),
  })) git(repo, 'config', key, value);
  const manifest = { name: 'iter', version, type: 'module', license: 'MIT' };
  writeFileSync(join(repo, 'package.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  writeFileSync(join(repo, 'package-lock.json'), `${JSON.stringify({ name: 'iter', version, lockfileVersion: 3, packages: { '': manifest } }, null, 2)}\n`);
  for (const directoryName of ['.codex-plugin', '.claude-plugin']) {
    mkdirSync(join(repo, directoryName));
    writeFileSync(join(repo, directoryName, 'plugin.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  }
  writeFileSync(join(repo, 'CHANGELOG.md'), `# Changelog\n\n## Unreleased\n\n## ${version}\n\nHuman release note.\n`);
  writeFileSync(join(repo, 'README.md'), '# Iter\n\nVersion-independent installation instructions.\n');
  writeFileSync(join(repo, 'README.zh-CN.md'), '# Iter\n\n安装说明。\n');
  writeFileSync(join(repo, '.gitignore'), 'node_modules/\n');
  copyFileSync(join(root, '.release-it.json'), join(repo, '.release-it.json'));
  // Plugins resolve relative to the candidate's cwd; use installed, locked test dependencies.
  symlinkSync(join(root, 'node_modules'), join(repo, 'node_modules'), process.platform === 'win32' ? 'junction' : 'dir');
  git(repo, 'remote', 'add', 'origin', remote);
  git(repo, 'add', '.');
  git(repo, 'commit', '-m', 'feat: initial trial');
  git(repo, 'push', '-u', 'origin', 'main');
  if (published) {
    git(repo, 'tag', `v${version}`);
    git(repo, 'push', 'origin', `v${version}`);
  }
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GITHUB_')));
  return { directory, repo, remote, candidate, env };
}

function change(f, message) {
  writeFileSync(join(f.repo, 'feature.txt'), message);
  git(f.repo, 'add', 'feature.txt');
  git(f.repo, 'commit', '-m', message);
  git(f.repo, 'push', 'origin', 'main');
}

function prepare(f, mode = 'auto') {
  run(f.repo, process.execPath, [releaseScript, 'prepare', '--mode', mode, '--output', f.candidate], { env: f.env });
  return readJson(join(f.candidate, 'release.json'));
}

function publish(f, failCreate = false) {
  const statePath = join(f.directory, 'github-state.json');
  if (!existsSync(statePath)) writeFileSync(statePath, JSON.stringify({ calls: [], failCreate }));
  const fake = `
    import { readFileSync, writeFileSync } from 'node:fs';
    import { publishRelease } from ${JSON.stringify(new URL('../scripts/release.mjs', import.meta.url).href)};
    const [directory, sha, statePath] = process.argv.slice(1);
    const state = JSON.parse(readFileSync(statePath, 'utf8'));
    const gh = args => {
      state.calls.push(args);
      writeFileSync(statePath, JSON.stringify(state));
      if (args[0] === 'api') {
        if (args.includes('POST')) return JSON.stringify({ state: 'success' });
        if (state.release) return JSON.stringify(state.release);
        throw new Error('HTTP 404');
      }
      if (state.failCreate) {
        state.failCreate = false;
        writeFileSync(statePath, JSON.stringify(state));
        throw new Error('Simulated GitHub outage after atomic push');
      }
      state.release = { tag_name: args[2], draft: false, prerelease: args.includes('--prerelease'), html_url: 'https://example.invalid/release' };
      writeFileSync(statePath, JSON.stringify(state));
      return state.release.html_url;
    };
    console.log(await publishRelease(directory, sha, 'fixture/iter', gh, 'https://example.invalid/actions/runs/1'));
  `;
  return run(f.repo, process.execPath, ['--input-type=module', '--eval', fake, f.candidate, readJson(join(f.candidate, 'release.json')).sha, statePath]);
}

test('release policy preserves first version, advances beta, and explicitly graduates stable', async () => {
  assert.equal(await selectIncrement('auto', '0.1.0', undefined, true), false);
  assert.equal(await selectIncrement('auto', '0.1.1-beta.1', undefined, true), false);
  assert.equal(await selectIncrement('auto', '0.1.1-beta.1', '0.1.1-beta.1', true), 'prerelease');
  assert.equal(await selectIncrement('stable', '0.1.1-beta.2', '0.1.1-beta.2', false), '0.1.1');
  assert.equal(await selectIncrement('auto', '1.2.3', '1.2.3', true), undefined);
  await assert.rejects(selectIncrement('auto', '1.2.3', '1.2.3', false), /No changes/);
  await assert.rejects(selectIncrement('auto', '1.2.2', '1.2.3', true), /behind/);
  await assert.rejects(selectIncrement('$(unsafe)', '1.2.3', undefined, true), /Unknown release mode/);
  await assert.rejects(selectIncrement('stable', '1.2.3', '1.2.3', true), /prerelease/);
});

test('changelog combines curated and generated notes and preserves historical sections', () => {
  const result = updateChangelog('# Changelog\n\n## Unreleased\n\n中文迁移说明。\n\n## 1.0.0\n\nKeep history.\n', '1.1.0', '# 1.1.0\n\n### Features\n\n* New feature\n', '2026-09-05');
  assert.equal(result.notes, '中文迁移说明。\n\n### Features\n\n* New feature');
  assert.match(result.changelog, /## 1\.1\.0 \(2026-09-05\)/);
  assert.ok(result.changelog.endsWith('## 1.0.0\n\nKeep history.\n'));
  assert.equal(result.changelog.match(/中文迁移说明/g).length, 1);
});

test('first release consumes a prepared version section without duplicating its notes or history', () => {
  for (const heading of ['## 0.1.0', '## [0.1.0]', '## 0.1.0 (2026-09-04)']) {
    const previous = `# Changelog\n\n## Unreleased\n\nLast-minute correction.\n\n${heading}\n\nInitial release notes.\n\n## 0.0.1\n\nEarlier development snapshot.\n`;
    const result = updateChangelog(previous, '0.1.0', '# 0.1.0\n\n### Features\n\n* Initial implementation\n', '2026-09-05');
    assert.equal(result.changelog.match(/^## 0\.1\.0 \(/gm).length, 1);
    assert.equal(result.changelog.match(/Initial release notes\./g).length, 1);
    assert.equal(result.notes, 'Initial release notes.\n\nLast-minute correction.\n\n### Features\n\n* Initial implementation');
    assert.ok(result.changelog.endsWith('## 0.0.1\n\nEarlier development snapshot.\n'));
  }
  const notesOnly = updateChangelog('# Changelog\n\n## 0.1.0\n\nInitial release notes.\n', '0.1.0', '', '2026-09-05');
  assert.equal(notesOnly.notes, 'Initial release notes.');
  assert.throws(() => updateChangelog('# Changelog\n\n## 0.1.0\n\nFirst.\n\n## 0.1.0\n\nSecond.\n', '0.1.0', ''), /Duplicate changelog sections/);
});

test('actual release tools preserve README, restore the same commit, and recover after a publish failure', t => {
  const f = fixture(t);
  const base = git(f.repo, 'rev-parse', 'HEAD');
  const candidate = prepare(f);
  assert.equal(candidate.version, '0.1.0');
  assert.equal(candidate.prerelease, false);
  const changelog = readFileSync(join(f.repo, 'CHANGELOG.md'), 'utf8');
  assert.equal(changelog.match(/^## 0\.1\.0 \(/gm).length, 1);
  assert.equal(changelog.match(/Human release note\./g).length, 1);
  assert.equal(git(f.directory, '--git-dir', f.remote, 'rev-parse', 'main'), base);
  assert.equal(git(f.directory, '--git-dir', f.remote, 'tag', '--list'), '');
  assert.equal(git(f.repo, 'diff', base, 'HEAD', '--', 'README.md', 'README.zh-CN.md'), '');
  assert.ok(git(f.repo, 'diff', '--name-only', base, 'HEAD').split('\n').every(path => releaseFiles.includes(path)));
  const restored = join(f.directory, 'restored tree');
  git(f.directory, 'clone', '--depth=1', '--no-local', f.remote, restored);
  run(restored, process.execPath, [releaseScript, 'restore', '--candidate', f.candidate, '--sha', candidate.sha]);
  assert.equal(git(restored, 'rev-parse', 'HEAD'), candidate.sha);
  assert.equal(readJson(join(restored, '.claude-plugin/plugin.json')).version, candidate.version);
  assert.throws(() => publish(f, true), /Simulated GitHub outage/);
  assert.equal(git(f.directory, '--git-dir', f.remote, 'rev-parse', `${candidate.tag}^{commit}`), candidate.sha);
  assert.equal(git(f.directory, '--git-dir', f.remote, 'rev-parse', 'main'), candidate.sha);
  publish(f);
  publish(f);
  const state = readJson(join(f.directory, 'github-state.json'));
  assert.equal(state.calls.filter(args => args[0] === 'release').length, 2); // One failed creation, one successful retry.
  assert.ok(state.calls.find(args => args[0] === 'release').includes('--verify-tag'));
  assert.ok(state.calls.some(args => args.includes(`repos/fixture/iter/statuses/${candidate.sha}`) && args.includes('state=success')));
  assert.equal(state.release.prerelease, false);
  assert.ok(state.calls.find(args => args[0] === 'release').includes('--latest'));
  assert.equal(git(f.repo, 'rev-parse', 'HEAD'), candidate.sha);
});

test('actual release tools auto-increment beta and infer stable features and breaking changes', t => {
  for (const [initial, message, mode, expected] of [
    ['0.1.1-beta.1', 'fix: resume the saved cycle', 'auto', '0.1.1-beta.2'],
    ['0.1.1-beta.1', 'fix: finish trial checks', 'stable', '0.1.1'],
    ['1.2.3', 'feat: add a new workflow', 'auto', '1.3.0'],
    ['1.2.3', 'feat!: change the public contract', 'auto', '2.0.0'],
  ]) {
    const f = fixture(t, initial, true);
    change(f, message);
    assert.equal(prepare(f, mode).version, expected);
    assert.equal(readJson(join(f.repo, 'package-lock.json')).packages[''].version, expected);
    for (const path of releaseFiles.slice(2, 4)) assert.equal(readJson(join(f.repo, path)).version, expected);
  }
});

test('retrying an older stable release does not move latest backwards after main advances', t => {
  const f = fixture(t, '1.2.3');
  const candidate = prepare(f);
  assert.throws(() => publish(f, true), /Simulated GitHub outage/);
  const competitor = join(f.directory, 'newer release');
  git(f.directory, 'clone', f.remote, competitor);
  git(competitor, 'config', 'user.name', 'Newer Release');
  git(competitor, 'config', 'user.email', 'newer@example.invalid');
  git(competitor, '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', 'chore: release v1.2.4');
  git(competitor, '-c', 'tag.gpgsign=false', 'tag', 'v1.2.4');
  git(competitor, 'push', 'origin', 'main', 'v1.2.4');
  const newerHead = git(competitor, 'rev-parse', 'HEAD');
  publish(f);
  const creations = readJson(join(f.directory, 'github-state.json')).calls.filter(args => args[0] === 'release');
  assert.ok(creations.at(-1).includes('--latest=false'));
  assert.equal(git(f.directory, '--git-dir', f.remote, 'rev-parse', 'main'), newerHead);
  assert.equal(git(f.directory, '--git-dir', f.remote, 'rev-parse', `${candidate.tag}^{commit}`), candidate.sha);
});

test('publishing rejects a moved main or conflicting tag without creating a GitHub release', t => {
  for (const conflict of ['main', 'tag']) {
    const f = fixture(t);
    const candidate = prepare(f);
    if (conflict === 'main') {
      const competitor = join(f.directory, 'competing checkout');
      git(f.directory, 'clone', f.remote, competitor);
      git(competitor, 'config', 'user.name', 'Concurrent Author');
      git(competitor, 'config', 'user.email', 'concurrent@example.invalid');
      git(competitor, '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', 'feat: concurrent change');
      git(competitor, 'push', 'origin', 'main');
    } else {
      git(f.repo, 'tag', candidate.tag, candidate.base);
      git(f.repo, 'push', 'origin', candidate.tag);
    }
    assert.throws(() => publish(f), conflict === 'main' ? /main moved/ : /different commit/);
    assert.equal(readJson(join(f.directory, 'github-state.json')).calls.length, 0);
    if (conflict === 'main') assert.equal(git(f.directory, '--git-dir', f.remote, 'tag', '--list'), '');
  }
});

test('workflow gates publication on the shared candidate checks and offers a non-publishing rehearsal', () => {
  const release = parse(readFileSync(join(root, '.github/workflows/release.yml'), 'utf8'));
  const ci = parse(readFileSync(join(root, '.github/workflows/ci.yml'), 'utf8'));
  assert.deepEqual(Object.keys(release.on), ['workflow_dispatch']);
  assert.deepEqual(release.on.workflow_dispatch.inputs.mode.options, modes);
  assert.equal(release.permissions.contents, 'read');
  assert.equal(release.concurrency['cancel-in-progress'], false);
  assert.deepEqual(release.jobs.publish.needs, ['prepare', 'checks']);
  assert.match(release.jobs.publish.if, /!inputs\.dry_run/);
  assert.equal(release.jobs.checks.uses, './.github/workflows/ci.yml');
  assert.equal(release.jobs.checks.with.candidate_sha, '${{ needs.prepare.outputs.candidate_sha }}');
  assert.ok(ci.on.workflow_call.inputs.candidate_sha);
  assert.equal(ci.jobs.checks.strategy.matrix.include.length, 4);
  for (const path of ['README.md', 'README.zh-CN.md']) {
    assert.ok(!readFileSync(join(root, path), 'utf8').includes(readJson(join(root, 'package.json')).version));
  }
});
