# Modeling and Topology

Guidelines for meshes that deform well, shade cleanly and stay within budget.

## Topology

- **Quads** subdivide and deform predictably; use them on anything that bends.
- **Edge loops** follow muscle and joint lines: around eyes and mouth, around shoulders, elbows and knees, with extra loops at bending joints.
- **Poles** (vertices with 3 or 5+ edges) are unavoidable; keep them on flat, non-deforming areas.
- **N-gons** are acceptable on flat hard-surface faces that never deform or subdivide; triangulate predictably before export.
- **Triangles** are what engines render; exporters triangulate. Check the result for long thin triangles that shade badly.

## Hard-surface shading

- Small bevels catch highlights and read as real edges.
- Mark sharp edges or use auto-smooth by angle so flat faces stay flat and curved faces stay smooth.
- Support loops near edges control subdivision sharpness.

## Budgets

Triangle budgets depend on the platform, the number of objects on screen and the shader cost. Agree on budgets per asset type with the Engineer, then:

- spend polygons on the silhouette, not on flat areas;
- bake high-poly detail into normal maps;
- create levels of detail (LODs) for objects seen at a distance.

## UV mapping

- Place seams where they are hidden or follow natural breaks (under arms, along hard edges).
- Keep **texel density** consistent across an asset (and across assets that appear together).
- Leave padding between UV islands (a few pixels at the target texture size) so mipmaps do not bleed.
- Overlap mirrored parts only when unique texturing is not needed and lightmaps use a separate UV set.
- Add a second, non-overlapping UV set for baked lightmaps when the engine uses them.

## Scale and transforms

- Model at real-world scale; keep a human-scale reference object in the scene.
- Apply rotation and scale before export; leave location for placement.
- Put the origin where the engine expects it (usually at the base center for props and characters).

## Procedural and generative modeling

- Geometry Nodes (Blender) and scripted generation suit variations (rocks, buildings, foliage). Seed the randomness and record the seed.
- Validate procedural output like any other asset; generators can produce non-manifold or degenerate geometry.
