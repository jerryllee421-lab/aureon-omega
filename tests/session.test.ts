import test from 'node:test';import assert from 'node:assert/strict';import {marketSessions} from '../server/session.ts';

test('London open window uses local DST-aware time',()=>{
  const s=marketSessions(Date.parse('2026-09-18T07:30:00Z'));
  assert.equal(s.london.localTime,'08:30');
  assert.equal(s.london.openWindow,true);
  assert.equal(s.newYork.openWindow,false);
  assert.equal(s.focusWindow,'LONDON_OPEN');
});

test('London/New York overlap is detected from zone-local clocks',()=>{
  const s=marketSessions(Date.parse('2026-09-18T13:30:00Z'));
  assert.equal(s.london.active,true);
  assert.equal(s.newYork.active,true);
  assert.equal(s.overlap,true);
  assert.equal(s.focusWindow,'LONDON_NEW_YORK_OVERLAP');
});

test('weekend reference sessions remain off',()=>{
  const s=marketSessions(Date.parse('2026-09-19T13:30:00Z'));
  assert.equal(s.london.active,false);
  assert.equal(s.newYork.active,false);
  assert.equal(s.focusWindow,'OFF_FOCUS');
});
