import { fileURLToPath } from 'node:url';
import * as filesystem from '@deepseek-ai/dsh-skill-filesystem';

export const name = 'iter';
export const inject = ['skills'];

export async function apply(ctx) {
  await ctx.plugin(filesystem, {
    providerName: 'iter',
    includeDefaultRoots: false,
    bundledSkillDir: fileURLToPath(new URL('./skills/', import.meta.url)),
  });
}
