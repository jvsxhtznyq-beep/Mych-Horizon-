// Verifies design/staff-day-view.html in a real browser: overflow, touch targets,
// computed WCAG contrast and keyboard order, at phone and desktop widths.
// Usage: node design/verify-day-view.js   (writes screenshots next to this file)
const { chromium } = require('playwright');
const path = require('path');

const WIDTHS = [320, 390, 1280];
const MIN_TARGET = 44; // the plugin's design standard for touch targets (WCAG 2.5.8 AA minimum is 24)

function luminance([r, g, b]) {
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}
function ratio(a, b) {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

(async () => {
  const browser = await chromium.launch();
  const file = 'file://' + path.resolve(__dirname, 'staff-day-view.html');
  let failures = 0;
  for (const width of WIDTHS) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await page.goto(file);
    const result = await page.evaluate((minTarget) => {
      const rgb = (s) => (s.match(/\d+(\.\d+)?/g) || []).slice(0, 4).map(Number);
      const bgOf = (el) => {
        for (let n = el; n; n = n.parentElement) {
          const c = rgb(getComputedStyle(n).backgroundColor);
          if (c.length === 3 || (c.length === 4 && c[3] > 0)) return c.slice(0, 3);
        }
        return [255, 255, 255];
      };
      const textEls = [...document.querySelectorAll('h1, h2, p, time, strong, .meta, .who, button, .counts, .error-text')]
        .filter((el) => el.offsetParent !== null && el.textContent.trim());
      const pairs = textEls.map((el) => ({ text: el.textContent.trim().slice(0, 30), fg: rgb(getComputedStyle(el).color).slice(0, 3), bg: bgOf(el), size: parseFloat(getComputedStyle(el).fontSize) }));
      const small = [...document.querySelectorAll('button')].map((b) => { const r = b.getBoundingClientRect(); return { name: b.textContent.trim(), w: Math.round(r.width), h: Math.round(r.height) }; })
        .filter((b) => b.w < minTarget || b.h < minTarget);
      const order = [...document.querySelectorAll('button, a[href], input, select, textarea')]
        .map((el) => (el.getAttribute('aria-label') || el.textContent).trim().replace(/\s+/g, ' '));
      const firstHeading = (document.querySelector('h1, h2, h3') || {}).tagName;
      return { overflow: document.documentElement.scrollWidth - window.innerWidth, pairs, small, order, firstHeading };
    }, MIN_TARGET);
    let worst = { r: Infinity };
    for (const p of result.pairs) { const r = ratio(p.fg, p.bg); if (r < worst.r) worst = { r, ...p }; }
    const contrastOk = worst.r >= 4.5;
    const ok = result.overflow <= 0 && result.small.length === 0 && contrastOk && result.firstHeading === 'H1';
    if (!ok) failures++;
    console.log(`width ${width}: ${ok ? 'PASS' : 'FAIL'} | horizontal overflow ${result.overflow}px | buttons under ${MIN_TARGET}px: ${result.small.length ? JSON.stringify(result.small) : 'none'} | lowest text contrast ${worst.r.toFixed(2)}:1 ("${worst.text}") | first heading ${result.firstHeading}`);
    if (width === 390) console.log('keyboard order (accessible names): ' + result.order.join(' > '));
    await page.screenshot({ path: path.resolve(__dirname, `day-view-${width}.png`), fullPage: true });
    await page.close();
  }
  await browser.close();
  console.log(failures ? `${failures} width(s) failed` : 'all widths passed');
  process.exit(failures ? 1 : 0);
})();
