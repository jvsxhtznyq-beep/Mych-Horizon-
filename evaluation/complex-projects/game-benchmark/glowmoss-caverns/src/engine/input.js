// Keyboard, touch and gamepad input mapped to game actions.

export const KEY_BINDINGS = Object.freeze({
  left: ['ArrowLeft', 'KeyA'],
  right: ['ArrowRight', 'KeyD'],
  jump: ['Space', 'KeyZ', 'ArrowUp', 'KeyW', 'KeyK'],
  pause: ['Escape', 'KeyP'],
  confirm: ['Enter'],
});

const CODE_TO_ACTION = new Map(Object.entries(KEY_BINDINGS).flatMap(([action, codes]) => codes.map((code) => [code, action])));

export function actionForCode(code) {
  return CODE_TO_ACTION.get(code) || null;
}

export function createInput(target, win = globalThis) {
  const held = new Set();
  const pressed = new Set();
  const touch = { left: false, right: false, jump: false };
  let padPause = false;
  const onKeyDown = (event) => {
    const action = actionForCode(event.code);
    if (!action) return;
    if (['left', 'right', 'jump'].includes(action)) event.preventDefault();
    if (!event.repeat) pressed.add(action);
    held.add(action);
  };
  const onKeyUp = (event) => {
    const action = actionForCode(event.code);
    if (action) held.delete(action);
  };
  const onBlur = () => held.clear();
  target.addEventListener('keydown', onKeyDown);
  target.addEventListener('keyup', onKeyUp);
  win.addEventListener?.('blur', onBlur);

  function gamepad() {
    const pads = win.navigator?.getGamepads ? [...win.navigator.getGamepads()].filter(Boolean) : [];
    const pad = pads[0];
    if (!pad) return { left: false, right: false, jump: false };
    const axis = pad.axes?.[0] || 0;
    const button = (i) => !!pad.buttons?.[i]?.pressed;
    const pause = button(9);
    if (pause && !padPause) pressed.add('pause');
    padPause = pause;
    return { left: axis < -0.5 || button(14), right: axis > 0.5 || button(15), jump: button(0) };
  }

  return {
    sample() {
      const pad = gamepad();
      return {
        left: held.has('left') || touch.left || pad.left,
        right: held.has('right') || touch.right || pad.right,
        jump: held.has('jump') || touch.jump || pad.jump,
      };
    },
    consume(action) {
      const was = pressed.has(action);
      pressed.delete(action);
      return was;
    },
    clearPressed() {
      pressed.clear();
    },
    bindTouch(element, action) {
      const set = (value) => (event) => {
        event.preventDefault();
        if (action === 'pause') {
          if (value) pressed.add('pause');
        } else {
          touch[action] = value;
        }
      };
      element.addEventListener('pointerdown', set(true));
      for (const name of ['pointerup', 'pointercancel', 'pointerleave']) element.addEventListener(name, set(false));
    },
    dispose() {
      target.removeEventListener('keydown', onKeyDown);
      target.removeEventListener('keyup', onKeyUp);
      win.removeEventListener?.('blur', onBlur);
    },
  };
}
