# Rigging and Animation

Rigs that export cleanly and animations that survive the trip into an engine.

## Rigging

- **Armature:** a clear hierarchy with a root bone at the origin; name bones consistently (left and right suffixes) so mirroring works.
- **Weights:** smooth falloff at joints; no stray weights on distant bones; limit influences per vertex to what the engine supports (commonly four).
- **IK and constraints** help animators but rarely export; bake them into keyframes before exporting.
- **Rest pose:** model in a neutral pose (A-pose or T-pose) with applied transforms.

## Animation

- Set the frame rate first and keep it consistent across clips.
- Name actions clearly (`idle`, `walk`, `run`, `jump`); one action per clip.
- **Root motion:** decide whether the engine moves the character or the animation does; author accordingly.
- Loop seamlessly: the last frame should lead into the first without a pop.

## glTF animation

- Channels target a node's `translation`, `rotation` (quaternion), `scale`, or a mesh's morph target `weights`.
- Interpolation: LINEAR, STEP or CUBICSPLINE. Rotation channels with LINEAR interpolation use spherical linear interpolation in most loaders.
- Skins list joints and inverse bind matrices; meshes carry JOINTS_0 and WEIGHTS_0 attributes.
- `gltf_tool.py inspect` lists animations with channel counts and durations; play them in the target engine before sign-off.

## Checklist

- [ ] Transforms applied on the mesh and armature.
- [ ] Constraints and drivers baked.
- [ ] Influences per vertex within the engine's limit.
- [ ] Clips named, frame ranges correct, loops seamless.
- [ ] Exported file plays correctly in the target engine.
