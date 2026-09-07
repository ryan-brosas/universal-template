import { CONFIG_DIR_NAME } from '@earendil-works/pi-coding-agent';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { registerCrew } from './crew.mjs';

export default function (pi) {
  registerCrew(pi, { configDir: CONFIG_DIR_NAME, sharedRoot: join(homedir(), '.agents') });
}
