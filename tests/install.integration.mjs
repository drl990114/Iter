import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { access, cp, mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';
import test from 'node:test';
import { assertInstalledHelperWorks, assertResourcesMatch, helperCommand, packFixture, skillRelativePath } from './package-fixture.mjs';

const require = createRequire(import.meta.url);
const skillsManifestPath = require.resolve('skills/package.json');
const skillsCli = join(dirname(skillsManifestPath), 'bin/cli.mjs');

function skillsCommand(project, args) {
  return execFileSync(process.execPath, [skillsCli, ...args], {
    cwd: project, encoding: 'utf8', timeout: 30_000,
    env: { ...process.env, DISABLE_TELEMETRY: '1', DO_NOT_TRACK: '1' },
  });
}

// Project paths from vercel-labs/skills 1.5.23. Keep this explicit so an upstream
// change cannot silently weaken the portability contract when updating the CLI.
const agents = {
  codex: '.agents/skills',
  'claude-code': '.claude/skills',
  cursor: '.agents/skills',
  'github-copilot': '.agents/skills',
  'gemini-cli': '.agents/skills',
  opencode: '.agents/skills',
  windsurf: '.windsurf/skills',
};

test('packed skill installs with the upstream CLI for common harnesses', async t => {
  assert.equal(JSON.parse(await readFile(skillsManifestPath, 'utf8')).version, '1.5.23');
  const fixtureRoot = await mkdtemp(join(tmpdir(), 'iter-install-'));
  const iterHome = join(fixtureRoot, 'iter home');
  try {
    const { root: extractedRoot } = await packFixture(fixtureRoot);
    for (const [agent, directory] of Object.entries(agents)) {
      await t.test(agent, async () => {
        const project = join(fixtureRoot, `${agent} project`);
        const existing = join(project, '.agents/skills/existing-helper/SKILL.md');
        const existingContent = '---\nname: existing-helper\ndescription: Preserve this project skill.\n---\nExisting user content.\n';
        await mkdir(dirname(existing), { recursive: true });
        await writeFile(existing, existingContent);
        // Explicit project scope, agent selection and --yes prevent global
        // installation or saved interactive preferences. No network/model calls.
        const output = execFileSync(process.execPath, [skillsCli, 'add', extractedRoot,
          '--skill', 'iterate-product', '--agent', agent, '--yes', '--copy'], {
          cwd: project,
          encoding: 'utf8',
          timeout: 30_000,
          env: { ...process.env, DISABLE_TELEMETRY: '1', DO_NOT_TRACK: '1' },
        });
        assert.match(output, /Installed 1 skill/);
        const installedSkill = join(project, directory, 'iterate-product');
        await assertResourcesMatch(installedSkill, join(extractedRoot, skillRelativePath));
        await assertInstalledHelperWorks(installedSkill, project, fixtureRoot, iterHome);
        assert.equal(await readFile(existing, 'utf8'), existingContent);
        const lock = JSON.parse(await readFile(join(project, 'skills-lock.json'), 'utf8'));
        assert.ok(lock.skills['iterate-product']);
      });
    }
    await t.test('copy mode installs multiple agents in a completely new project', async () => {
      const project = join(fixtureRoot, 'new multi agent project');
      await mkdir(project);
      skillsCommand(project, ['add', extractedRoot, '--skill', 'iterate-product',
        '--agent', 'codex', 'windsurf', '--yes', '--copy']);
      let sharedPaths;
      let initialState;
      for (const agent of ['codex', 'windsurf']) {
        const installed = join(project, agents[agent], 'iterate-product');
        await assertResourcesMatch(installed, join(extractedRoot, skillRelativePath));
        if (!sharedPaths) {
          sharedPaths = await assertInstalledHelperWorks(installed, project, fixtureRoot, iterHome);
          initialState = await readFile(sharedPaths.state_path);
        } else {
          const paths = helperCommand(installed, project, iterHome, ['paths']);
          assert.deepEqual(paths, helperCommand(join(project, agents.codex, 'iterate-product'), project, iterHome, ['paths']));
          const status = helperCommand(installed, project, iterHome, ['status']);
          assert.equal(status.storage_root, sharedPaths.storage_root);
          assert.equal(status.stage, 'research');
          assert.deepEqual(await readFile(paths.state_path), initialState);
        }
      }
      await assert.rejects(access(join(project, '.product-loop')), { code: 'ENOENT' });
    });
    await t.test('skill-name migration preserves external state, grants, artifacts, and other skills', async () => {
      const project = join(fixtureRoot, 'legacy project');
      const legacySource = join(fixtureRoot, 'legacy source', 'run-product-loop');
      await mkdir(project);
      await cp(join(extractedRoot, skillRelativePath), legacySource, { recursive: true });
      const oldEntrypoint = join(legacySource, 'SKILL.md');
      await writeFile(oldEntrypoint, (await readFile(oldEntrypoint, 'utf8')).replace('name: iterate-product', 'name: run-product-loop'));
      skillsCommand(project, ['add', dirname(legacySource), '--skill', 'run-product-loop', '--agent', 'codex', '--copy', '--yes']);
      const oldInstalled = join(project, '.agents/skills/run-product-loop');
      const paths = helperCommand(oldInstalled, project, iterHome, ['paths']);
      await mkdir(paths.inputs_dir, { recursive: true });
      const proposalPath = join(paths.inputs_dir, 'selected-proposal.json');
      await writeFile(proposalPath, JSON.stringify({
        id: 'preserved-scope', title: 'Preserve my iteration', objective: 'Preserve my iteration',
        scope: ['A change inside this disposable project'], acceptance: ['One isolated check passes'],
        risks: ['Real-user value remains unvalidated'],
        metric: { name: 'Success', baseline: null, target: '100%' },
        validation: {
          mode: 'local_scenario', data_policy: 'isolated', data_scope: ['Synthetic project fixtures only'],
          side_effects: ['Create and remove synthetic fixtures'], recovery: 'Remove only generated fixtures; keep evidence',
          scenarios: [{ id: 'check', steps: ['Run the local sample with a synthetic fixture'], expected: 'The expected output' }],
        },
      }));
      helperCommand(oldInstalled, project, iterHome, ['init',
        '--language', 'zh-CN', '--proposal', proposalPath, '--authorize-implementation', '--authorize-local',
        '--authorization-evidence', 'The user approved this scope and its isolated local check']);
      const statePath = paths.state_path;
      const state = JSON.parse(await readFile(statePath, 'utf8'));
      assert.equal(state.schema_version, 2);
      delete state.language;
      await writeFile(statePath, JSON.stringify(state, null, 2) + '\n');
      const before = await readFile(statePath);
      const logPath = join(paths.storage_root, 'decision-log.jsonl');
      const beforeLog = await readFile(logPath);
      const artifacts = await Promise.all(Object.values(state.artifacts).map(async path => [path, await readFile(join(paths.storage_root, path))]));
      const existing = join(project, '.agents/skills/existing-helper/SKILL.md');
      await mkdir(dirname(existing), { recursive: true });
      await writeFile(existing, 'Keep this unrelated skill.\n');
      skillsCommand(project, ['add', extractedRoot, '--skill', 'iterate-product', '--agent', 'codex', '--copy', '--yes']);
      // Shared .agents/skills copies serve several hosts. Migrate this name
      // for all project hosts; --all would wrongly select every skill.
      skillsCommand(project, ['remove', 'run-product-loop', '--yes']);
      await assert.rejects(access(oldInstalled));
      const current = join(project, '.agents/skills/iterate-product');
      await assertResourcesMatch(current, join(extractedRoot, skillRelativePath));
      const status = helperCommand(current, project, iterHome, ['status']);
      assert.equal(status.storage_root, paths.storage_root);
      assert.equal(status.state_path, statePath);
      assert.equal(status.language, 'zh-CN');
      assert.equal(status.objective, 'Preserve my iteration');
      assert.equal(status.authorizations.implementation.status, 'granted');
      assert.equal(status.authorizations.local.status, 'granted');
      assert.deepEqual(await readFile(statePath), before);
      assert.deepEqual(await readFile(logPath), beforeLog);
      for (const [path, content] of artifacts) assert.deepEqual(await readFile(join(paths.storage_root, path)), content);
      await assert.rejects(access(join(project, '.product-loop')), { code: 'ENOENT' });
      assert.equal(await readFile(existing, 'utf8'), 'Keep this unrelated skill.\n');
    });
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
});
