import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { Context } from '@deepseek-ai/cordis';
import SkillRegistry, { renderSkillContent } from '@deepseek-ai/dsh-skill';
import * as filesystem from '@deepseek-ai/dsh-skill-filesystem';
import { parse } from 'yaml';
import * as productLoop from '../index.mjs';
import { assertInstalledHelperWorks, assertResourcesMatch, packFixture } from './package-fixture.mjs';

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
    await assertInstalledHelperWorks(extractedSkill, join(fixtureRoot, 'test workspace'), fixtureRoot);
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
});
