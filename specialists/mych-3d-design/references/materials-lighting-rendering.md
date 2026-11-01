# Materials, Lighting and Rendering

PBR material setup, lighting approaches and render settings that produce believable results.

## PBR metallic-roughness

| Channel | Meaning | Typical values |
|---|---|---|
| Base color | Albedo without lighting | Avoid pure black and pure white; real albedos sit in the middle range |
| Metallic | Metal or not | 0 for non-metals, 1 for metals; in-between only for transitions such as dirt on metal |
| Roughness | Microsurface scatter | Varies across a surface; carries most of the realism |
| Normal | Surface detail without geometry | glTF uses +Y (OpenGL-style) normal maps; DirectX-style maps need the green channel flipped |
| Occlusion | Ambient shadowing in crevices | Multiplies indirect light only |
| Emissive | Light emitted by the surface | Combine with bloom for glow |

- Color textures (base color, emissive) are sRGB; data textures (metallic, roughness, normal, occlusion) are linear.
- Pack occlusion, roughness and metallic into one texture's R, G and B channels when the target supports it (glTF expects roughness in G and metallic in B).
- Texture sizes are usually powers of two; use the smallest size that holds up at the expected viewing distance.

## Lighting

- **Three-point lighting** (key, fill, rim) for product shots and turntables.
- **HDRI environment lighting** for realistic reflections; match the HDRI to the scene's mood.
- **Physically plausible values:** keep light intensities and exposure consistent between shots.
- For real-time engines, decide early between baked lighting (lightmaps, needs a second UV set) and dynamic lighting.

## Rendering in Blender

| Engine | Strengths | Trade-offs |
|---|---|---|
| Cycles (path tracing) | Accurate light transport, caustics, soft shadows | Slower; needs samples and denoising; benefits strongly from a GPU |
| EEVEE (rasterized) | Fast previews and stylized work | Approximations for reflections and indirect light |

- Use a filmic-style view transform (Filmic or AgX, depending on the Blender version) for natural highlight roll-off.
- Denoise Cycles renders; increase samples where noise remains in dark areas.
- Render turntables or still sets with fixed cameras and lighting so revisions are comparable.

## Reporting renders

State the renderer, version, sample count, resolution, render time and hardware. If no renderer was available, say so: do not describe images that were not rendered.
