import { spawnSync } from 'node:child_process';
import { packageRoot, pythonCommand } from './package-fixture.mjs';

const { command, args } = pythonCommand();
const result = spawnSync(command, [...args, '-m', 'unittest', 'discover',
  '-s', 'skills/iterate-product/scripts/tests', '-v'], {
  cwd: packageRoot,
  stdio: 'inherit',
});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
