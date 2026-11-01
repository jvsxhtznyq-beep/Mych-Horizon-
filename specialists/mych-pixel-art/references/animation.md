# Animation

Timing and frame planning for sprite animation. Durations are in milliseconds and stored per frame in the sheet JSON.

## Starting points for timing

| Action | Frames | Duration per frame | Notes |
|---|---|---|---|
| Idle (breathing, bobbing) | 2 to 4 | 150 to 250 | Subtle; sub-pixel shifts; ping-pong loops work well |
| Walk | 4 to 8 | 80 to 120 | Contact, down, passing, up poses per step |
| Run | 6 to 8 | 60 to 90 | Body leans forward; both feet off the ground in one pose |
| Jump | 4 to 6 (not looped) | 50 to 100 | Anticipation, take-off, rise, apex, fall, land |
| Attack | 3 to 6 | 40 to 120 | Short anticipation, very fast strike, longer recovery |
| Hurt | 1 to 2 | 100 to 200 | Often a flash or knockback instead of extra frames |
| Death or defeat | 4 to 8 | 80 to 150 | Ends on a hold frame or disappears in particles |
| Pickup sparkle | 4 to 6 | 60 to 100 | Loop; keep within the item's footprint |

Treat these as starting points, then tune by watching the animation at game speed.

## Principles that matter most at low resolution

- **Anticipation:** a small opposite motion before a big one (crouch before jumping) makes actions readable.
- **Squash and stretch:** compress on landing, stretch on rising; keep the overall area roughly constant.
- **Follow-through:** hair, capes and tails settle a frame or two after the body stops.
- **Smear frames:** one stretched frame can sell a fast attack better than several sharp ones.
- **Holds:** a few longer frames at key poses read better than uniform timing.

## Consistency rules

- Keep **frame size** identical across an animation set (pad with transparency rather than cropping per frame) so the anchor stays put.
- Put the **anchor** at the feet or ground contact point; record it with `anchor X Y` in the sprite file.
- Keep **volume** constant: a character should not grow or shrink between frames unless squash or stretch is intended.
- Separate **hitboxes** from sprite pixels; define them in game data, not by alpha.

## Naming and tags

- Name frames `ACTION_N` (`walk_0`, `walk_1`). Without explicit tags, `pixel_tool.py` groups consecutive frames with the same prefix into one tag.
- Use explicit `tag NAME FIRST LAST DIRECTION` lines when an animation reuses frames out of order or should play `reverse` or `pingpong`.

## Reviewing an animation

1. Render a preview sheet with `--scale 4`.
2. Play it at game speed in the engine or a quick HTML preview; check loops for pops at the seam.
3. Watch the silhouette only (filled in one color): motion should still read.
