# Game Benchmark: Glowmoss Caverns

**Result: a complete, playable browser platformer built with MYCH-HORIZON 2.0, verified by 25 unit, stress and failure tests and 23 browser checks, all passing. Self-assessed score: 86 / 100.** The score is the builder's own assessment against the rubric below; every line cites evidence in this folder so it can be checked or disputed.

- Play it: [glowmoss-caverns/dist/glowmoss-caverns.html](glowmoss-caverns/dist/glowmoss-caverns.html) (one self-contained file; open it in a browser) or the release archive [glowmoss-caverns/dist/glowmoss-caverns-1.0.0.zip](glowmoss-caverns/dist/glowmoss-caverns-1.0.0.zip).
- Source: [glowmoss-caverns/](glowmoss-caverns/) (2,239 lines of JavaScript including tests and tools, 568 lines of sprites, HTML and CSS; no third-party runtime dependencies).
- Evidence: [evidence/](evidence/) (test logs, solver results, build hashes, routing decision, screenshots).
- Date: 2026-11-06. Environment: Linux container, Node.js 22, headless Chromium through Playwright, no GPU.

## What was built

| Requirement | Implementation | Evidence |
|---|---|---|
| Menus | Title, cavern select with locks and best scores, settings, how to play, pause, cavern cleared, game over, victory, error recovery | [01-title](evidence/screenshots/01-title.png), [04-paused](evidence/screenshots/04-paused.png), [03-complete](evidence/screenshots/03-cavern1-complete.png) |
| Settings | Master, music and effects volume; screen shake; reduced flashing; frame-rate display; touch controls (auto, on, off); all persisted | [05-settings](evidence/screenshots/05-settings.png); E2E "settings persist across reloads" |
| Levels | Three caverns from validated text maps (one-way ledges, spikes, pits, checkpoints, exits) | `levels.test.mjs`; solver proves each completable |
| Controls | Keyboard (arrows, WASD, Space, Z, Esc, P), gamepad (stick, d-pad, A, Start), touch buttons; coyote time, jump buffering, variable jump height | `input.test.mjs`; E2E keyboard replay and touch checks |
| Collisions | Axis-separated tile collision with no tunneling, ceilings, one-way ledges, spikes, entity overlap | `physics.test.mjs` |
| Enemies | Patrolling slimes, sine-flying bats, spore turrets with projectiles; stomp to defeat | `world.test.mjs` |
| Scoring | Orbs, enemy stomps, time bonus, heart bonus, all-orbs bonus, best score per cavern | `world.test.mjs`; E2E score equals the Node simulation |
| Audio | Synthesized effects (jump, land, pickup, heal, stomp, hurt, fall, shoot, checkpoint, complete, game over, menu) and a sequenced music loop, Web Audio, starts after a user gesture | E2E confirms Web Audio unlocks; audible output not verified |
| Visual effects | Pooled particles, screen shake (optional), hurt flash (optional), glow lighting, parallax cave background, mossy tile rendering | [02-cavern1-mid](evidence/screenshots/02-cavern1-mid.png) |
| Animations | 21 hand-authored 16x16 frames in 13 animation tags (player idle, run, jump, fall, hurt; slime; bat; turret; spore; orb; crystal; checkpoint) | `build.json`: sheet validated against the 16-color palette |
| Save and load | Versioned local-storage save with validation, repair, corruption reset and an in-memory fallback | `storage.test.mjs`; E2E "progress saved", "corrupted save is reset" |
| Responsive UI | Whole-number scaling on large screens, exact fit on phones, portrait layout, touch controls, focus management, visible focus rings | [07-mobile-touch](evidence/screenshots/07-mobile-touch.png) |
| Performance | Fixed 60 Hz simulation with a step cap, cached tile layer, particle pool | E2E 60.3 fps, 0.064 to 0.090 ms per update and render step; 504 enemies at 0.23 ms per simulated frame |
| Error handling | Global error and rejection handlers show a recovery screen; sprite loading falls back to shapes; invalid levels are rejected with messages; storage failures are reported | [06-error-screen](evidence/screenshots/06-error-screen.png), [08-sprite-fallback](evidence/screenshots/08-sprite-fallback.png) |
| Build and packaging | Sprites rendered and palette-checked by the pixel-art specialist, modules bundled into one HTML file, deterministic ZIP | [build.json](evidence/build.json); two builds produced identical SHA-256 hashes |
| Automated tests | Unit, stress, failure, solver and browser end-to-end suites | [unit-tests.tap](evidence/unit-tests.tap), [e2e-results.json](evidence/e2e-results.json) |

## How MYCH-HORIZON was used

1. **Routing.** `tools/mych.py route` on the full request returned Tier 3, Engineer leading with Architect and Designer, the new-software-project workflow and `mych-pixel-art` ([route.json](evidence/route.json)). On the first attempt the router picked the product-design workflow because the request mentioned "UI"; the benchmark exposed this, the rule was fixed (build requests keep the build workflow) and a regression test was added.
2. **Pixel-art specialist.** All sprites were authored in the specialist's text sprite format ([assets/sprites.sprite](glowmoss-caverns/assets/sprites.sprite)) and rendered, packed and validated against the project palette by `pixel_tool.py` during every build. The sheet's Aseprite-style JSON drives the game's animations.
3. **Specialists deliberately not used.** No image generation backend exists here, so `mych-image-generation` was not used and no art is presented as generated. The game is 2D, so `mych-3d-design` stayed unloaded. No online features were built, so `mych-api-integration` was not needed.
4. **Verification discipline.** The task ledger (`.mych/tasks.json`, tasks G1 and G2) records completion separately from verification, with the test outputs as evidence.
5. **Solver as a design check.** A beam-search solver plays each cavern with the real physics and enemy timing. It found a genuine design bug in cavern 1 (a ledge directly above a pit edge made the jump impossible); the level was fixed and every cavern is now proven completable without taking damage. The browser test replays the solver's input plan through real keyboard events and reached the exit on exactly the frame the Node simulation predicted (frame 548, score 1754).

## Scoring rubric

| Category | Points | Score | Basis |
|---|---|---|---|
| Gameplay completeness (menus, levels, controls, collisions, enemies, scoring) | 20 | 17 | Every listed system works and is tested; content is modest: three caverns, three enemy types, no boss or progression beyond unlocks |
| Technical quality and architecture | 10 | 9 | Deterministic, cloneable simulation separated from rendering and effects; dependency-free; the bundler relies on code conventions (single-line imports, unique top-level names), enforced by the build but limiting |
| Visuals and animation | 10 | 8 | Coherent palette, readable sprites, glow, particles and parallax; the exit door is drawn procedurally rather than animated; HUD uses a system monospace font |
| Audio | 5 | 3 | Twelve synthesized effects and a music loop with three volume buses; audible output and mixing quality were not verified (headless browser) |
| User experience, accessibility, responsiveness | 10 | 8 | Settings with persistence, reduced flashing, keyboard, touch and gamepad, focus management, phone layout; no key remapping; gamepad untested on hardware; colour contrast of the HUD not measured |
| Save, load, robustness and error handling | 10 | 9 | Validation, repair, corruption reset, storage fallback, error recovery screen and sprite fallback, all tested; recovery from a mid-level crash restarts from the title rather than the level |
| Automated testing (unit, end-to-end, stress, failure) | 15 | 14 | 25 unit, stress, failure and solver tests; 23 browser checks; only Chromium was tested; no audio output or real-device tests |
| Performance | 5 | 5 | 60 fps rendering; under 0.1 ms per update and render step; 504 enemies simulated at 0.23 ms per frame |
| Build and packaging | 5 | 5 | Single-file build plus deterministic ZIP; palette validation in the build; byte-identical rebuilds verified |
| Use of MYCH-HORIZON specialists and process | 5 | 4 | Router, pixel-art specialist, ledger and verification used; the router initially misrouted (fixed); only one domain specialist was relevant |
| Honesty and documented limitations | 5 | 4 | Limits are listed below with evidence; one point withheld because the score is a self-assessment |
| **Total** | **100** | **86** | |

## Limitations and untested areas

- **Browsers and devices:** tested only in headless Chromium on Linux. Firefox, Safari, real phones and real gamepads were not tested.
- **Audio:** Web Audio initializes and sounds are scheduled without errors; whether they sound good was not verified.
- **Content depth:** three short caverns; a full game would need more levels, enemy variety and difficulty tuning from playtesting with people.
- **Accessibility:** keyboard, focus, reduced flashing and touch support exist; no screen reader or contrast audit was run on the canvas HUD.
- **Self-assessment:** the score was given by the same agent that built the game.

## Additional benchmarks

The master prompt asked for additional benchmarks (chatbot platform, 3D application, cloud deployment, API platform, pixel pipeline) if possible. They were not run in this pass; the specialists' own test suites cover their tools, and the planned benchmarks are listed in the [roadmap](../../../docs/roadmap.md).

## Reproduce

```bash
cd evaluation/complex-projects/game-benchmark/glowmoss-caverns
node tools/build.mjs            # sprites, bundle, single-file HTML, ZIP
node --test tests/unit/*.test.mjs
node tools/solve.mjs            # proves each cavern completable
node tests/e2e/run.mjs          # needs Playwright with Chromium
```
