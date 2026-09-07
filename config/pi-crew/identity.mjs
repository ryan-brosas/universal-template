import { createHash } from 'node:crypto';
import { realpath } from 'node:fs/promises';
import { dirname, basename } from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
const exec = promisify(execFile);
export const digest = value => createHash('sha256').update(value).digest('hex').slice(0, 24);

// No remote-name/basename fallback: unrelated clones stay separate. Linked
// worktrees intentionally share the canonical common Git directory identity.
export async function projectIdentity(cwd) {
  let root;
  try { root = await realpath(cwd); }
  catch { throw new Error('Cannot resolve project identity: no directory ' + cwd); }
  try {
    const { stdout } = await exec('git', ['rev-parse', '--path-format=absolute', '--git-common-dir'], { cwd: root, timeout: 3000 });
    const common = await realpath(stdout.trim());
    root = basename(common) === '.git' ? dirname(common) : common;
  } catch (error) {
    if (error.code !== 128) throw new Error('Cannot resolve project identity: ' + error.message);
    // A real non-Git directory is its own project, never its basename.
  }
  const id = digest(root);
  return Object.freeze({ root, id, projectId: 'crew-' + id, bankId: 'pi-crew-' + id });
}
