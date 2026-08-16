# 3D — three.js scenes & objects

3D adds depth, product realism, and wow — but bad 3D (flat lighting, muddy
materials, no shadow, spinning-cube-for-no-reason) looks worse than good 2D.
The craft is lighting and material, not geometry.

## When 3D earns its place

- Showing a real product/object from angles (packaging, hardware, a model).
- A hero moment where depth/parallax creates presence.
- Data in genuinely 3D space (rare — usually 2D is clearer; don't 3D a bar
  chart for fun).
- An exportable model (OBJ/GLB) as a deliverable.

If a static render or a 2D illustration communicates it, prefer that. 3D is
expensive attention.

## Setup essentials (three.js)

Use an import map pinned to a specific version; build a `THREE.Group` of named
meshes/materials so it's inspectable and exportable.

```js
import * as THREE from 'three';
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, w/h, 0.1, 100); // ~35mm feels natural
const renderer = new THREE.WebGLRenderer({ antialias:true, alpha:true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;   // filmic, not flat
renderer.outputColorSpace = THREE.SRGBColorSpace;
```

## Lighting = 90% of the look

Never a single light. Use a studio setup:

- **Key light** (directional), strong, off-axis, casts the shadow.
- **Fill light** (softer, opposite side, ~30% key) to open shadows.
- **Rim/back light** to separate the object from the background.
- **Environment map** (HDRI or a simple gradient env) for realistic reflections
  — this is what makes materials read as real. Use
  `RoomEnvironment`/`PMREMGenerator` for a free believable studio.
- A **ground shadow** (contact shadow / shadow-catcher plane) grounds the
  object; floating objects look fake.

```js
const key = new THREE.DirectionalLight(0xffffff, 3);
key.position.set(5, 8, 5); key.castShadow = true;
const fill = new THREE.DirectionalLight(0xffffff, 1); fill.position.set(-5,3,2);
const rim = new THREE.DirectionalLight(0xffffff, 2); rim.position.set(0,4,-6);
scene.add(key, fill, rim);
// + environment for reflections:
const env = new THREE.PMREMGenerator(renderer)
  .fromScene(new RoomEnvironment(), 0.04).texture;
scene.environment = env;
```

## Materials

- Use `MeshStandardMaterial`/`MeshPhysicalMaterial` (PBR) — `roughness` and
  `metalness` are the two dials that matter. Plastic ≈ rough 0.4 / metal 0;
  metal ≈ rough 0.2 / metal 1; glass/clearcoat via `MeshPhysicalMaterial`
  (`transmission`, `clearcoat`).
- Real materials are never pure white or pure black; pull them slightly off.
- Subtle roughness variation reads as real; perfectly uniform reads as CG.

## Camera & composition

- Frame like a photographer: object off-center, slight down-angle, some
  negative space. Auto-fit the camera to the bounding box so it's always framed.
- Longer focal length (35–50mm equivalent) avoids the distorted wide-angle CG
  look.
- `OrbitControls` with damping for interactive viewing; gentle auto-rotate for
  a hero (respect reduced-motion — slow or off).

## Performance

- Cap `pixelRatio` at 2; use `antialias` but not at 4K on mobile.
- Reuse geometries/materials; merge static meshes.
- Only render when something changes (on-demand rendering) for static scenes;
  don't burn a rAF loop on a still object.
- Dispose geometries/materials/textures when tearing down.

## Export

- Build named meshes/materials → export OBJ+MTL or GLB. GLB preserves PBR
  materials and is the modern default; OBJ+MTL for broad compatibility.
- Keep the scene graph clean (named nodes) so the exported file is usable
  downstream.

## Grounding it in the page

- Transparent canvas (`alpha:true`) so the 3D sits in your real page design,
  lit to match the page's mood.
- Reserve layout space to avoid content shift while the scene loads; show a
  lightweight poster/placeholder until ready.
