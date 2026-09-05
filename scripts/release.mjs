import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { appendFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

export const releaseFiles = ['package.json', 'package-lock.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json', 'CHANGELOG.md'];
export const modes = ['auto', 'patch', 'minor', 'major', 'stable'];
const shaPattern = /^[a-f0-9]{40}$/;

function command(executable, args, options = {}) {
  return execFileSync(executable, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], ...options }).trim();
}
const git = (...args) => command('git', args);
const readJson = path => JSON.parse(readFileSync(path, 'utf8'));
const lines = text => text.split(/\r?\n/).filter(Boolean);

export async function selectIncrement(mode, current, latest, hasChanges) {
  const { default: semver } = await import('semver');
  assert.ok(modes.includes(mode), `Unknown release mode: ${mode}`);
  assert.equal(semver.valid(current), current, 'Package version must be canonical SemVer');
  assert.ok(!current.includes('+'), 'Release versions must not contain build metadata');
  assert.ok(!latest || semver.gte(current, latest), 'Package version is behind the latest release tag');
  if (mode === 'stable') {
    assert.ok(semver.prerelease(current), 'stable requires an existing prerelease version');
    return current.split('-')[0];
  }
  assert.ok(!latest || hasChanges, 'No changes since the latest release; there is nothing to release');
  if (mode !== 'auto') return mode;
  if (!latest || semver.gt(current, latest)) return false; // Publish an already prepared version as-is.
  if (semver.prerelease(current)) return 'prerelease';
  return undefined; // Let Conventional Commits recommend the stable version increment.
}

export function updateChangelog(previous, version, generated, date = new Date().toISOString().slice(0, 10)) {
  const match = previous.match(/^## \[?Unreleased\]?\s*\r?\n([\s\S]*?)(?=^## |$(?![\s\S]))/m);
  const curated = match?.[1].trim() || '';
  const sections = (match ? previous.slice(match.index + match[0].length) : previous.replace(/^# Changelog\s*/, ''))
    .trim().split(/(?=^## )/m);
  const prepared = sections.filter(section => section.match(/^## \[?([^\]\s]+)\]?[^\r\n]*\r?\n/)?.[1] === version);
  assert.ok(prepared.length <= 1, `Duplicate changelog sections for ${version}`);
  const preparedNotes = prepared[0]?.replace(/^## [^\n]*\n+/, '').trim();
  const history = sections.filter(section => !prepared.includes(section)).join('').trim();
  const automated = generated.replace(/^#{1,3} [^\n]*\n+/, '').trim();
  const notes = [preparedNotes, curated, automated].filter(Boolean).join('\n\n');
  assert.ok(notes, 'Release notes are empty; add a change or an Unreleased entry');
  const section = `## ${version} (${date})\n\n${notes}`;
  return { notes, changelog: `# Changelog\n\n## Unreleased\n\n${section}\n${history ? `\n${history}\n` : ''}` };
}

function assertReleaseFiles() {
  const version = readJson('package.json').version;
  const lock = readJson('package-lock.json');
  assert.equal(lock.version, version, 'Lockfile version mismatch');
  assert.equal(lock.packages[''].version, version, 'Lockfile root version mismatch');
  for (const path of releaseFiles.slice(2, 4)) assert.equal(readJson(path).version, version, `${path} version mismatch`);
  return version;
}

export async function prepareRelease(mode, outputDirectory) {
  assert.ok(modes.includes(mode), `Unknown release mode: ${mode}`);
  assert.equal(git('status', '--porcelain'), '', 'Release preparation needs a clean checkout');
  const output = resolve(outputDirectory);
  const pathFromRoot = relative(process.cwd(), output);
  assert.ok(isAbsolute(pathFromRoot) || pathFromRoot === '..' || pathFromRoot.startsWith(`..${sep}`), 'Candidate artifacts must be outside the checkout');
  const base = git('rev-parse', 'HEAD');
  const current = assertReleaseFiles();
  const { default: semver } = await import('semver');
  const versions = lines(git('tag', '--merged', 'HEAD', '--list', 'v*'))
    .map(tag => tag.slice(1)).filter(version => semver.valid(version) === version);
  const latest = semver.rsort(versions)[0];
  const hasChanges = !latest || git('rev-parse', `v${latest}^{commit}`) !== base;
  const increment = await selectIncrement(mode, current, latest, hasChanges);
  const { default: release } = await import('release-it');
  const result = await release({ ci: true, ...(increment !== undefined && { increment }) });
  assert.ok(result.version, 'No releasable commits found; choose patch or add a feat:/fix: commit');
  const version = assertReleaseFiles();
  assert.equal(version, result.version);
  assert.ok(!latest || semver.gt(version, latest), 'Release version must increase');
  const tag = `v${version}`;
  assert.equal(git('tag', '--list', tag), '', `Tag ${tag} already exists`);
  const { changelog, notes } = updateChangelog(readFileSync('CHANGELOG.md', 'utf8'), version, result.changelog || '');
  writeFileSync('CHANGELOG.md', changelog);
  const changed = lines(git('diff', '--name-only', 'HEAD'));
  assert.ok(changed.every(path => releaseFiles.includes(path)), 'Release tooling changed files outside the release manifest/changelog list');
  git('diff', '--check');
  git('add', '--', ...releaseFiles);
  git('commit', '-m', `chore: release v${version}`);
  const sha = git('rev-parse', 'HEAD');
  mkdirSync(output, { recursive: true });
  git('bundle', 'create', join(output, 'candidate.bundle'), 'HEAD', `^${base}`);
  const candidate = { base, sha, version, tag, prerelease: Boolean(semver.prerelease(version)) };
  writeFileSync(join(output, 'release.json'), `${JSON.stringify(candidate, null, 2)}\n`);
  writeFileSync(join(output, 'notes.md'), `${notes}\n`);
  if (process.env.GITHUB_OUTPUT) {
    appendFileSync(process.env.GITHUB_OUTPUT, `source_sha=${base}\ncandidate_sha=${sha}\nversion=${version}\n`);
  }
  return candidate;
}

function readCandidate(directory, expectedSha) {
  const candidate = readJson(join(directory, 'release.json'));
  assert.ok(shaPattern.test(expectedSha), 'An exact candidate SHA is required');
  assert.equal(candidate.sha, expectedSha, 'Artifact does not match the prepared candidate SHA');
  assert.ok(shaPattern.test(candidate.base), 'Invalid source SHA');
  assert.match(candidate.version, /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/);
  assert.equal(candidate.tag, `v${candidate.version}`);
  return candidate;
}

export function restoreCandidate(directory, expectedSha) {
  const candidate = readCandidate(directory, expectedSha);
  git('bundle', 'verify', join(directory, 'candidate.bundle'));
  git('fetch', '--no-tags', join(directory, 'candidate.bundle'), 'HEAD');
  assert.equal(git('rev-parse', 'FETCH_HEAD'), expectedSha);
  git('checkout', '--detach', expectedSha);
  assert.equal(git('rev-parse', 'HEAD^'), candidate.base, 'Candidate has an unexpected parent');
  return candidate;
}

function remoteRefs() {
  return new Map(lines(git('ls-remote', 'origin', 'refs/heads/main', 'refs/tags/v*'))
    .map(line => { const [sha, ref] = line.split(/\s+/); return [ref, sha]; }));
}

export async function publishRelease(directory, expectedSha, repository, gh = args => command('gh', args), runUrl) {
  assert.match(repository, /^[\w.-]+\/[\w.-]+$/, 'Invalid GitHub repository');
  assert.ok(runUrl?.startsWith('https://'), 'A link to the successful candidate CI run is required');
  const candidate = readCandidate(directory, expectedSha);
  const { base, sha, tag, version } = candidate;
  assert.equal(git('rev-parse', 'HEAD'), sha, 'Only the tested candidate commit can be published');
  assert.equal(git('rev-parse', 'HEAD^'), base);
  assert.equal(git('status', '--porcelain'), '', 'Release candidate was modified after testing');
  assert.equal(assertReleaseFiles(), version);
  const { default: semver } = await import('semver');
  assert.equal(candidate.prerelease, Boolean(semver.prerelease(version)));
  const notesPath = join(directory, 'notes.md');
  const notes = readFileSync(notesPath, 'utf8').trim();
  const changelog = readFileSync('CHANGELOG.md', 'utf8');
  const section = changelog.split(`## ${version} (`)[1]?.split('\n').slice(1).join('\n').split(/^## /m)[0].trim();
  assert.equal(section, notes, 'Release notes must match the tested changelog');
  const refs = remoteRefs();
  const remoteTag = refs.get(`refs/tags/${tag}^{}`) || refs.get(`refs/tags/${tag}`);
  if (remoteTag) {
    assert.equal(remoteTag, sha, `Published tag ${tag} points to a different commit`);
    git('fetch', '--no-tags', 'origin', 'main');
    git('merge-base', '--is-ancestor', sha, 'FETCH_HEAD');
  } else {
    assert.ok([base, sha].includes(refs.get('refs/heads/main')), 'main moved during validation; run Release again against the new main');
    if (git('tag', '--list', tag)) assert.equal(git('rev-parse', `${tag}^{commit}`), sha);
    else git('tag', '-a', tag, sha, '-m', `Iter ${version}`);
    // A concurrent main push rejects the entire operation; neither ref is forced.
    git('push', '--atomic', 'origin', `${sha}:refs/heads/main`, `refs/tags/${tag}:refs/tags/${tag}`);
    const pushed = remoteRefs();
    assert.equal(pushed.get(`refs/tags/${tag}^{}`) || pushed.get(`refs/tags/${tag}`), sha);
  }
  // GITHUB_TOKEN pushes do not trigger another workflow. Attach the completed
  // candidate matrix result to the new commit, with a link to the actual run.
  gh(['api', '--method', 'POST', `repos/${repository}/statuses/${sha}`, '-f', 'state=success',
    '-f', 'context=Release / candidate CI', '-f', 'description=All candidate matrix checks passed', '-f', `target_url=${runUrl}`]);
  let existing;
  try {
    existing = JSON.parse(gh(['api', `repos/${repository}/releases/tags/${tag}`]));
  } catch (error) {
    if (!String(error.stderr || error.message).includes('HTTP 404')) throw error;
  }
  if (existing) {
    assert.equal(existing.tag_name, tag);
    assert.equal(existing.draft, false, 'An existing draft needs review before publication');
    assert.equal(existing.prerelease, candidate.prerelease, 'Existing release channel mismatch');
    return existing.html_url;
  }
  const newerStable = [...refs.keys()].map(ref => ref.replace(/^refs\/tags\/v/, ''))
    .some(value => semver.valid(value) && !semver.prerelease(value) && semver.gt(value, version));
  return gh(['release', 'create', tag, '--repo', repository, '--verify-tag', '--title', `Iter ${version}`,
    '--notes-file', notesPath, ...(candidate.prerelease ? ['--prerelease', '--latest=false'] : [newerStable ? '--latest=false' : '--latest'])]);
}

function dispatchRelease(mode, dryRun) {
  assert.ok(modes.includes(mode), `Unknown release mode: ${mode}`);
  assert.equal(git('status', '--porcelain'), '', 'Commit and push your changes before triggering Release');
  assert.equal(git('branch', '--show-current'), 'main', 'Trigger Release from main after merging your changes');
  const remoteMain = git('ls-remote', 'origin', 'refs/heads/main').split(/\s+/)[0];
  assert.equal(git('rev-parse', 'HEAD'), remoteMain, 'Local main must match origin/main before triggering Release');
  command('gh', ['workflow', 'run', 'release.yml', '--ref', 'main', '-f', `mode=${mode}`, '-f', `dry_run=${dryRun}`]);
  console.log('Release queued on GitHub. Follow it with: gh run list --workflow release.yml');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const { values, positionals } = parseArgs({ allowPositionals: true, options: {
      mode: { type: 'string', default: 'auto' }, output: { type: 'string' }, candidate: { type: 'string' },
      sha: { type: 'string' }, 'dry-run': { type: 'boolean', default: false },
    } });
    const action = positionals[0] || 'dispatch';
    if (action === 'dispatch') dispatchRelease(values.mode, values['dry-run']);
    else if (action === 'prepare') {
      assert.ok(values.output, '--output is required');
      console.log(JSON.stringify(await prepareRelease(values.mode, values.output)));
    } else if (action === 'restore') {
      assert.ok(values.candidate, '--candidate is required');
      restoreCandidate(values.candidate, values.sha);
    } else if (action === 'publish') {
      assert.equal(process.env.GITHUB_ACTIONS, 'true', 'Publish runs only inside the Release workflow');
      assert.ok(values.candidate, '--candidate is required');
      const repository = process.env.GITHUB_REPOSITORY;
      assert.match(process.env.GITHUB_RUN_ID || '', /^\d+$/, 'A GitHub workflow run ID is required');
      const runUrl = `${process.env.GITHUB_SERVER_URL}/${repository}/actions/runs/${process.env.GITHUB_RUN_ID}`;
      const url = await publishRelease(values.candidate, values.sha, repository, undefined, runUrl);
      console.log(url);
      if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, `Published ${url}\n`);
    } else throw new Error(`Unknown release action: ${action}`);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
