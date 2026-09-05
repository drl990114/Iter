import assert from 'node:assert/strict';
import { access, readFile, readdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { parse } from 'yaml';
import { packageRoot } from './package-fixture.mjs';

test('skill metadata and README install commands describe the shipped resources', async () => {
  const entrypoint = await readFile(join(packageRoot, 'skills/iterate-product/SKILL.md'), 'utf8');
  const frontmatter = entrypoint.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  assert.ok(frontmatter, 'Skill frontmatter is required');
  const metadata = parse(frontmatter[1]);
  assert.equal(metadata.name, 'iterate-product');
  assert.equal(metadata.license, 'MIT');
  assert.ok(metadata.description.length > 0 && metadata.description.length <= 1024);
  const ui = parse(await readFile(join(packageRoot, 'skills/iterate-product/agents/openai.yaml'), 'utf8'));
  assert.equal(ui.policy.allow_implicit_invocation, true);
  assert.ok(ui.interface.default_prompt.includes('$iterate-product'));
  const manifest = JSON.parse(await readFile(join(packageRoot, 'package.json'), 'utf8'));
  const lock = JSON.parse(await readFile(join(packageRoot, 'package-lock.json'), 'utf8'));
  assert.equal(lock.version, manifest.version);
  assert.equal(lock.packages[''].version, manifest.version);
  for (const path of ['README.md', 'README.zh-CN.md']) {
    const readme = await readFile(join(packageRoot, path), 'utf8');
    const commands = readme.split('\n').filter(line => line.startsWith('npx skills'));
    assert.ok(commands.length > 0);
    for (const command of commands) {
      assert.ok(command.startsWith('npx skills add '));
      assert.ok(command.includes('--skill iterate-product'));
      assert.ok(command.includes('--copy'));
    }
  }
});

test('public documentation links resolve and feedback forms parse', async () => {
  async function markdownFiles(directory) {
    const files = [];
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      if (entry.name.startsWith('.') || ['node_modules', '__pycache__'].includes(entry.name)) continue;
      const path = join(directory, entry.name);
      if (entry.isDirectory()) files.push(...await markdownFiles(path));
      else if (entry.name.endsWith('.md')) files.push(path);
    }
    return files;
  }
  for (const path of await markdownFiles(packageRoot)) {
    const content = await readFile(path, 'utf8');
    for (const [, link] of content.matchAll(/\]\(([^)]+)\)/g)) {
      if (/^[a-z][a-z0-9+.-]*:/i.test(link) || link.startsWith('#')) continue;
      const target = link.split('#')[0];
      if (target) await access(join(dirname(path), decodeURIComponent(target)));
    }
  }
  for (const name of ['trial-feedback.yml', 'bug-report.yml']) {
    const form = parse(await readFile(join(packageRoot, '.github/ISSUE_TEMPLATE', name), 'utf8'));
    assert.ok(form.name && form.description);
    const fields = form.body.filter(field => field.type !== 'markdown');
    assert.equal(new Set(fields.map(field => field.id)).size, fields.length);
    for (const field of fields) assert.ok(field.attributes.label);
  }
});
