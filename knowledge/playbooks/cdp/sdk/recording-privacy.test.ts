import assert from 'node:assert/strict';
import test from 'node:test';
import { recordedText } from './recording.ts';

test('typed content is redacted by default', () => {
  assert.deepEqual(recordedText('private value', 'text', false), {
    text: '••••••', textLength: 13, textRedacted: true,
  });
});

test('explicit capture reveals non-password text only', () => {
  assert.deepEqual(recordedText('allowed', 'text', true), { text: 'allowed' });
  assert.deepEqual(recordedText('secret', 'password', true), {
    text: '••••••', textLength: 6, textRedacted: true, password: true,
  });
  assert.equal(recordedText('unknown', undefined, true).textRedacted, true);
});
