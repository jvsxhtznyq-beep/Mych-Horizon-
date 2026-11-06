// Synthesized sound effects and music with the Web Audio API. Everything is
// generated at runtime (no audio files). When Web Audio is unavailable or
// blocked, every call is a safe no-op and the game runs silently.

const NOTE = (n) => 440 * Math.pow(2, (n - 69) / 12);
const BASS = [45, 45, 52, 52, 48, 48, 43, 43];
const ARP = [69, 72, 76, 72, 67, 71, 74, 71, 64, 67, 72, 67, 62, 67, 71, 67];

export function createAudio(win = globalThis) {
  const Context = win.AudioContext || win.webkitAudioContext;
  let available = !!Context;
  let ctx = null;
  let master = null;
  let musicBus = null;
  let sfxBus = null;
  let musicTimer = null;
  let nextNoteTime = 0;
  let step = 0;
  const volumes = { master: 0.8, music: 0.5, sfx: 0.8 };

  function applyVolumes() {
    if (!ctx) return;
    master.gain.value = volumes.master;
    musicBus.gain.value = volumes.music * 0.35;
    sfxBus.gain.value = volumes.sfx * 0.6;
  }

  function tone(type, freq, start, duration, gain, bus, slideTo = null) {
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, start);
    if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, start + duration);
    env.gain.setValueAtTime(0.0001, start);
    env.gain.exponentialRampToValueAtTime(gain, start + 0.01);
    env.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    osc.connect(env).connect(bus);
    osc.start(start);
    osc.stop(start + duration + 0.02);
  }

  function noise(start, duration, gain) {
    const length = Math.max(1, Math.floor(ctx.sampleRate * duration));
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let seed = 12345;
    for (let i = 0; i < length; i++) {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      data[i] = (seed / 0x7fffffff * 2 - 1) * (1 - i / length);
    }
    const src = ctx.createBufferSource();
    const env = ctx.createGain();
    env.gain.value = gain;
    src.buffer = buffer;
    src.connect(env).connect(sfxBus);
    src.start(start);
  }

  const SOUNDS = {
    jump: (t) => tone('square', 330, t, 0.12, 0.25, sfxBus, 660),
    land: (t) => tone('triangle', 140, t, 0.06, 0.2, sfxBus, 90),
    pickup: (t) => { tone('triangle', 880, t, 0.08, 0.25, sfxBus); tone('triangle', 1320, t + 0.06, 0.1, 0.22, sfxBus); },
    heal: (t) => { tone('sine', 660, t, 0.12, 0.25, sfxBus); tone('sine', 990, t + 0.1, 0.18, 0.25, sfxBus); },
    stomp: (t) => { noise(t, 0.12, 0.35); tone('square', 220, t, 0.1, 0.2, sfxBus, 110); },
    hurt: (t) => tone('sawtooth', 300, t, 0.25, 0.28, sfxBus, 80),
    fall: (t) => tone('sawtooth', 400, t, 0.4, 0.25, sfxBus, 60),
    shoot: (t) => tone('sine', 520, t, 0.08, 0.12, sfxBus, 260),
    checkpoint: (t) => { tone('triangle', 523, t, 0.12, 0.22, sfxBus); tone('triangle', 784, t + 0.1, 0.2, 0.22, sfxBus); },
    complete: (t) => [523, 659, 784, 1047].forEach((f, i) => tone('triangle', f, t + i * 0.09, 0.3, 0.25, sfxBus)),
    gameover: (t) => [392, 330, 262].forEach((f, i) => tone('square', f, t + i * 0.18, 0.3, 0.2, sfxBus)),
    menu: (t) => tone('square', 660, t, 0.05, 0.15, sfxBus),
  };

  function schedule() {
    const beat = 60 / 104 / 2;
    while (nextNoteTime < ctx.currentTime + 0.2) {
      if (step % 2 === 0) tone('triangle', NOTE(BASS[(step / 2) % BASS.length]), nextNoteTime, beat * 1.8, 0.3, musicBus);
      tone('square', NOTE(ARP[step % ARP.length]), nextNoteTime, beat * 0.8, 0.08, musicBus);
      nextNoteTime += beat;
      step += 1;
    }
  }

  return {
    get available() { return available; },
    get running() { return !!ctx && ctx.state === 'running'; },
    unlock() {
      if (!available) return false;
      try {
        if (!ctx) {
          ctx = new Context();
          master = ctx.createGain();
          musicBus = ctx.createGain();
          sfxBus = ctx.createGain();
          musicBus.connect(master);
          sfxBus.connect(master);
          master.connect(ctx.destination);
          applyVolumes();
        }
        if (ctx.state === 'suspended') ctx.resume();
        return true;
      } catch {
        available = false;
        return false;
      }
    },
    setVolumes(next) {
      Object.assign(volumes, next);
      applyVolumes();
    },
    play(name) {
      if (!ctx || ctx.state !== 'running' || !SOUNDS[name]) return;
      try { SOUNDS[name](ctx.currentTime); } catch { /* a failed sound must never break the game */ }
    },
    startMusic() {
      if (!ctx || musicTimer) return;
      nextNoteTime = ctx.currentTime + 0.05;
      musicTimer = win.setInterval(() => { try { schedule(); } catch { /* ignore */ } }, 25);
    },
    stopMusic() {
      if (musicTimer) win.clearInterval(musicTimer);
      musicTimer = null;
    },
    suspend() { if (ctx && ctx.state === 'running') ctx.suspend(); },
    resume() { if (ctx && ctx.state === 'suspended') ctx.resume(); },
  };
}
