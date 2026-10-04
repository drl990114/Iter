import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { access, mkdtemp, mkdir, readFile, readdir, realpath, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { Context } from '@deepseek-ai/cordis';
import SkillRegistry, { renderSkillContent } from '@deepseek-ai/dsh-skill';
import * as filesystem from '@deepseek-ai/dsh-skill-filesystem';
import { parse } from 'yaml';
import * as productLoop from '../index.mjs';
import { assertInstalledHelperWorks, assertResourcesMatch, helperCommand, packFixture, pythonCommand } from './package-fixture.mjs';

const packageRoot = fileURLToPath(new URL('../', import.meta.url));
const skillDirectory = join(packageRoot, 'skills', 'iterate-product');

test('Harness discovers the shared skill from another cwd and preserves its default provider on unload', async () => {
  const fixtureRoot = await mkdtemp(join(tmpdir(), 'product-loop-harness-'));
  const previousCwd = process.cwd();
  const ctx = new Context();
  try {
    const workspace = join(fixtureRoot, 'workspace');
    const defaultSkillPath = join(workspace, '.dsh', 'skills', 'default-helper', 'SKILL.md');
    await mkdir(dirname(defaultSkillPath), { recursive: true });
    await writeFile(defaultSkillPath, '---\nname: default-helper\ndescription: Existing project skill.\n---\n\nDefault provider fixture.\n');
    process.chdir(workspace);

    await ctx.plugin(SkillRegistry);
    await ctx.plugin(filesystem, {
      providerName: 'filesystem',
      dshHome: join(fixtureRoot, 'dsh-home'),
      agentsHome: join(fixtureRoot, 'agents-home'),
      watch: false,
    });
    assert.deepEqual((await ctx.skills.list({ cwd: workspace })).map(skill => skill.name), ['default-helper']);

    const adapter = await ctx.plugin(productLoop);
    const catalog = await ctx.skills.list({ cwd: workspace });
    assert.deepEqual(catalog.map(skill => skill.name), ['default-helper', 'iterate-product']);
    assert.deepEqual(catalog.filter(skill => skill.provider === 'iter').map(skill => skill.name), ['iterate-product']);

    const loaded = await ctx.skills.get('iterate-product', { cwd: workspace });
    assert.equal(loaded.provider, 'iter');
    assert.equal(loaded.source, 'bundled');
    assert.deepEqual(loaded.resourceBase, { kind: 'directory', path: skillDirectory });
    assert.match(loaded.content, /# Run Iter/);
    assert.match(renderSkillContent(loaded), /Resolve relative paths mentioned by this skill against the base directory/);
    assert.match(await readFile(join(loaded.resourceBase.path, 'scripts', 'product_loop.py'), 'utf8'), /def main\(/);
    assert.ok((await readFile(join(loaded.resourceBase.path, 'references', 'workflow-contract.md'), 'utf8')).length > 0);
    assert.ok((await readFile(join(loaded.resourceBase.path, 'assets', 'charter-template.md'), 'utf8')).length > 0);

    await adapter.dispose();
    assert.equal(await ctx.skills.get('iterate-product', { cwd: workspace }), undefined);
    assert.deepEqual((await ctx.skills.list({ cwd: workspace })).map(skill => skill.name), ['default-helper']);

    const remounted = await ctx.plugin(productLoop);
    assert.equal((await ctx.skills.get('iterate-product', { cwd: workspace })).provider, 'iter');
    await remounted.dispose();
    assert.equal((await ctx.skills.get('default-helper', { cwd: workspace })).provider, 'filesystem');
  } finally {
    try {
      await ctx.fiber.dispose();
    } finally {
      process.chdir(previousCwd);
      await rm(fixtureRoot, { recursive: true, force: true });
    }
  }
});

test('npm package carries the single skill and its resources without caches or install hooks', async () => {
  const fixtureRoot = await mkdtemp(join(tmpdir(), 'iter-package-'));
  try {
    const { packed, root: extractedRoot } = await packFixture(fixtureRoot);
    const paths = packed.files.map(file => file.path);
    for (const required of [
      'index.mjs',
      'LICENSE',
      'CHANGELOG.md',
      'cordis.patch.yml',
      '.codex-plugin/plugin.json',
      '.claude-plugin/plugin.json',
      'docs/harnesses.md',
      'docs/testing.md',
      'examples/note-counter/count_notes.py',
      'skills/iterate-product/SKILL.md',
      'skills/iterate-product/LICENSE.txt',
      'skills/iterate-product/scripts/product_loop.py',
      'skills/iterate-product/scripts/iter_storage.py',
      'skills/iterate-product/references/workflow-contract.md',
      'skills/iterate-product/assets/charter-template.md',
      'skills/iterate-product/assets/charter-template.zh-CN.md',
      'skills/iterate-product/assets/research-template.en.md',
      'skills/iterate-product/assets/experiment-template.en.md',
      'skills/iterate-product/assets/delivery-template.en.md',
      'skills/iterate-product/assets/evaluation-template.en.md',
    ]) assert.ok(paths.includes(required), `Package is missing ${required}`);
    assert.deepEqual(paths.filter(path => path.endsWith('/SKILL.md')), ['skills/iterate-product/SKILL.md']);
    assert.ok(paths.every(path => !/(^|\/)(node_modules|__pycache__|\.ruff_cache|tests)(\/|$)|\.py[cod]$/.test(path)));

    const manifest = JSON.parse(await readFile(join(extractedRoot, 'package.json'), 'utf8'));
    assert.equal(manifest.license, 'MIT');
    assert.equal(await readFile(join(extractedRoot, 'skills/iterate-product/LICENSE.txt'), 'utf8'), await readFile(join(extractedRoot, 'LICENSE'), 'utf8'));
    assert.equal(manifest.dsh.bundle.patch, './cordis.patch.yml');
    assert.equal(manifest.exports['.'], './index.mjs');
    assert.equal(manifest.peerDependencies['@deepseek-ai/dsh-skill-filesystem'], '0.0.1-rc.3');
    for (const hook of ['preinstall', 'install', 'postinstall', 'prepare', 'prepack']) {
      assert.equal(manifest.scripts?.[hook], undefined, `Package must not execute ${hook}`);
    }
    const patch = await readFile(join(extractedRoot, 'cordis.patch.yml'), 'utf8');
    for (const newline of ['\n', '\r\n']) {
      assert.deepEqual(parse(patch.replace(/\r?\n/g, newline)), [
        { insert: [{ id: manifest.name, name: manifest.name }] },
      ]);
    }
    for (const pluginPath of ['.codex-plugin/plugin.json', '.claude-plugin/plugin.json']) {
      const plugin = JSON.parse(await readFile(join(extractedRoot, pluginPath), 'utf8'));
      assert.equal(plugin.name, manifest.name);
      assert.equal(plugin.version, manifest.version);
      assert.equal(plugin.skills, './skills/');
    }
    const extractedSkill = join(extractedRoot, 'skills/iterate-product');
    await assertResourcesMatch(extractedSkill, skillDirectory);
    await assertInstalledHelperWorks(extractedSkill, join(fixtureRoot, 'test workspace'), fixtureRoot, join(fixtureRoot, 'iter home'));
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
});

test('native trial runner grants only this workspace storage and propagates ITER_HOME without starting a model', async t => {
  const fixtureRoot = await mkdtemp(join(tmpdir(), 'iter host storage '));
  t.after(() => rm(fixtureRoot, { recursive: true, force: true }));
  const iterHome = join(fixtureRoot, 'iter home');
  await mkdir(iterHome);
  const prompt = join(fixtureRoot, 'request.txt');
  await writeFile(prompt, 'Inspect this isolated trial only.\n');
  const python = pythonCommand();
  // Run the real path resolver and trial setup, replacing only the native host.
  // Neither a model session nor the user's CLI configuration is consulted.
  const exercise = `
import importlib.util, json, subprocess, sys
from unittest.mock import patch
spec = importlib.util.spec_from_file_location("host_trial", sys.argv[1])
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
host, workspace, prompt, output, skill = sys.argv[2:]
observed = {}
real_run = subprocess.run
real_popen = subprocess.Popen
def run(command, **kwargs):
    if command == ["fixture-host", "--version"]:
        return subprocess.CompletedProcess(command, 0, stdout="Fixture 1.0")
    return real_run(command, **kwargs)
class Host:
    def __init__(self, command, **kwargs):
        observed["command"] = command
        observed["iter_home"] = kwargs["env"]["ITER_HOME"]
        observed["cwd"] = str(kwargs["cwd"])
        self.returncode = 0
    def communicate(self, prompt, timeout):
        observed["prompt"] = prompt
def popen(command, **kwargs):
    return Host(command, **kwargs) if command[0] == "fixture-host" else real_popen(command, **kwargs)
sys.argv = ["host-trial", "--host", host, "--executable", "fixture-host",
    "--workspace", workspace, "--prompt-file", prompt, "--output", output,
    "--skill-dir", skill]
with patch.object(subprocess, "run", side_effect=run), patch.object(subprocess, "Popen", side_effect=popen):
    try:
        runner.main()
    except SystemExit as error:
        observed["exit_code"] = error.code
print(json.dumps(observed))
`;
  for (const host of ['codex', 'claude']) {
    await t.test(host, async () => {
      const workspace = join(fixtureRoot, `${host} project`);
      const output = join(fixtureRoot, `${host} output`);
      await mkdir(workspace);
      const paths = helperCommand(skillDirectory, workspace, iterHome, ['paths']);
      const result = execFileSync(python.command, [...python.args, '-c', exercise,
        join(packageRoot, 'scripts/run-host-trial.py'), host, workspace, prompt, output, skillDirectory], {
        encoding: 'utf8', timeout: 10_000, stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env, ITER_HOME: iterHome, PYTHONDONTWRITEBYTECODE: '1' },
      }).trim().split(/\r?\n/).map(line => JSON.parse(line));
      const observed = result.at(-1);
      assert.equal(observed.iter_home, await realpath(iterHome));
      assert.equal(observed.cwd, await realpath(workspace));
      assert.equal(observed.prompt, 'Inspect this isolated trial only.\n');
      const permissionIndex = observed.command.indexOf('--add-dir');
      assert.ok(permissionIndex > 0);
      assert.equal(observed.command[permissionIndex + 1], paths.storage_root);
      assert.equal(observed.command.filter(value => value === '--add-dir').length, 1);
      assert.ok(!observed.command.includes(observed.iter_home));
      assert.equal(result[0].storage_root, paths.storage_root);
      assert.equal(result[0].state_path, paths.state_path);
      assert.deepEqual(await readdir(workspace), []);
      assert.deepEqual(await readdir(paths.storage_root), []);
      await assert.rejects(access(paths.state_path), { code: 'ENOENT' });
      assert.equal(JSON.parse(await readFile(join(output, 'process.json'), 'utf8')).exit_code, 0);
    });
  }
  await t.test('legacy state stops before granting storage or starting the host', async () => {
    const workspace = join(fixtureRoot, 'legacy project');
    const legacy = join(workspace, '.product-loop');
    const output = join(fixtureRoot, 'legacy output');
    await mkdir(legacy, { recursive: true });
    await writeFile(join(legacy, 'preserve.txt'), 'Keep the existing cycle.\n');
    const paths = helperCommand(skillDirectory, workspace, iterHome, ['paths']);
    const observed = JSON.parse(execFileSync(python.command, [...python.args, '-c', exercise,
      join(packageRoot, 'scripts/run-host-trial.py'), 'codex', workspace, prompt, output, skillDirectory], {
      encoding: 'utf8', timeout: 10_000, stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, ITER_HOME: iterHome, PYTHONDONTWRITEBYTECODE: '1' },
    }).trim());
    assert.equal(observed.exit_code, 2);
    assert.equal(observed.command, undefined);
    await assert.rejects(access(paths.storage_root), { code: 'ENOENT' });
    await assert.rejects(access(output), { code: 'ENOENT' });
    assert.equal(await readFile(join(legacy, 'preserve.txt'), 'utf8'), 'Keep the existing cycle.\n');
  });
});
