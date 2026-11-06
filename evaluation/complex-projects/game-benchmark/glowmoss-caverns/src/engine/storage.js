// Versioned save data with validation. Corrupt or tampered data is repaired or
// reset with a notice; when storage is unavailable (private mode, blocked
// cookies), progress lives in memory and the player is told.

export const SAVE_KEY = 'glowmoss-caverns.save';
export const SAVE_VERSION = 1;
export const DEFAULT_SETTINGS = Object.freeze({ master: 0.8, music: 0.5, sfx: 0.8, shake: true, reducedFlashing: false,
                                               showFps: false, touch: 'auto' });

export function defaultSave() {
  return { version: SAVE_VERSION, unlocked: 1, best: {}, settings: { ...DEFAULT_SETTINGS }, plays: 0 };
}

function clampNumber(value, min, max, fallback) {
  return typeof value === 'number' && Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback;
}

export function sanitizeSave(raw, levelCount) {
  const problems = [];
  const clean = defaultSave();
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { save: clean, problems: ['save data is not an object'] };
  if (raw.version !== SAVE_VERSION) problems.push(`unknown save version ${JSON.stringify(raw.version)}`);
  const unlocked = Number.isInteger(raw.unlocked) ? raw.unlocked : 1;
  clean.unlocked = Math.min(levelCount, Math.max(1, unlocked));
  if (clean.unlocked !== raw.unlocked) problems.push('unlocked level was out of range');
  if (raw.best && typeof raw.best === 'object') {
    for (const [key, value] of Object.entries(raw.best)) {
      const index = Number(key);
      if (Number.isInteger(index) && index >= 1 && index <= levelCount && Number.isInteger(value) && value >= 0 && value <= 1e7) {
        clean.best[index] = value;
      } else {
        problems.push(`dropped invalid best score for ${key}`);
      }
    }
  }
  const s = raw.settings && typeof raw.settings === 'object' ? raw.settings : {};
  for (const key of ['master', 'music', 'sfx']) clean.settings[key] = clampNumber(s[key], 0, 1, DEFAULT_SETTINGS[key]);
  for (const key of ['shake', 'reducedFlashing', 'showFps']) clean.settings[key] = typeof s[key] === 'boolean' ? s[key] : DEFAULT_SETTINGS[key];
  clean.settings.touch = ['auto', 'on', 'off'].includes(s.touch) ? s.touch : DEFAULT_SETTINGS.touch;
  clean.plays = Number.isInteger(raw.plays) && raw.plays >= 0 ? raw.plays : 0;
  return { save: clean, problems };
}

export function browserStorage(win = globalThis) {
  try {
    const storage = win.localStorage;
    const probe = '__glowmoss_probe__';
    storage.setItem(probe, '1');
    storage.removeItem(probe);
    return { available: true, getItem: (k) => storage.getItem(k), setItem: (k, v) => storage.setItem(k, v) };
  } catch {
    return memoryStorage();
  }
}

export function memoryStorage() {
  const data = new Map();
  return { available: false, getItem: (k) => (data.has(k) ? data.get(k) : null), setItem: (k, v) => data.set(k, String(v)) };
}

export function createStore(levelCount, backend = browserStorage()) {
  return {
    backend,
    load() {
      if (!backend.available) {
        return { save: defaultSave(), notice: 'Saving is unavailable in this browser mode; progress lasts until you close the page.' };
      }
      let text = null;
      try {
        text = backend.getItem(SAVE_KEY);
      } catch {
        return { save: defaultSave(), notice: 'Saved progress could not be read; starting fresh.' };
      }
      if (text === null) return { save: defaultSave(), notice: null };
      let parsed;
      try {
        parsed = JSON.parse(text);
      } catch {
        return { save: defaultSave(), notice: 'Saved progress was damaged and has been reset.' };
      }
      const { save, problems } = sanitizeSave(parsed, levelCount);
      return { save, notice: problems.length ? 'Some saved data was invalid and has been repaired.' : null, problems };
    },
    write(save) {
      try {
        backend.setItem(SAVE_KEY, JSON.stringify(save));
        return { ok: true };
      } catch {
        return { ok: false, notice: 'Progress could not be saved (storage is full or blocked).' };
      }
    },
  };
}
