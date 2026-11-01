# Specialist Selection

How the coordinator chooses which disciplines to activate, which one leads, how they hand work to each other, and how a new discipline is registered.

## Contents

- [Selection procedure](#selection-procedure)
- [Signal catalog](#signal-catalog)
- [Combination recipes](#combination-recipes)
- [Lead rules](#lead-rules)
- [Handoff contracts](#handoff-contracts)
- [Escalation during a task](#escalation-during-a-task)
- [Anti-patterns](#anti-patterns)
- [Domain specialists](#domain-specialists)
- [Registering a new discipline](#registering-a-new-discipline)

## Selection procedure

1. List the deliverables the task requires (code, a decision, a design, findings, a concept).
2. For each deliverable, find the discipline whose strong signals match it in the [signal catalog](#signal-catalog).
3. For each other discipline, ask: would leaving it out lower quality or raise risk for *this* task? Activate it only if the answer is yes and you can say why in one clause.
4. Choose the lead: the discipline that owns the primary deliverable.
5. Check the result against [combination recipes](#combination-recipes). A deviation is fine when you can name the reason.

## Signal catalog

### Architect

- **Strong signals:** a new system or service; choosing a database, queue, cache or protocol; an API used by several consumers; scaling, availability or latency targets; data, framework or platform migrations; integrating external systems; changes that cross module boundaries.
- **Weak signals:** a new module or endpoint that follows an established pattern. Usually Engineer alone; consult the Architect only if the pattern does not fit.
- **Do not activate for:** single-function changes, copy edits, styling.

### Researcher

- **Strong signals:** an unfamiliar library, framework or standard; "which is better" questions; version-specific behavior; performance or security claims to evaluate; an error whose cause needs documentation or issue-tracker searches; feasibility questions.
- **Weak signals:** routine use of a well-known API. Verify only the version-sensitive details.
- **Do not activate for:** facts already established in the conversation or in project documentation.

### Designer

- **Strong signals:** new screens, flows or components; visual identity; design systems and tokens; accessibility; responsive behavior; prototypes; usability problems such as confusion or drop-off.
- **Weak signals:** a small change inside an existing design system. The Engineer follows existing patterns; consult the Designer when no pattern fits.
- **Do not activate for:** backend-only work. Command-line tools count as interfaces when their ergonomics are the point of the task.

### Engineer

- **Strong signals:** code to write, change, test, debug, refactor, optimize or integrate; build, release or deployment scripts.
- **Do not activate for:** pure research or concept work that produces no code. Prototypes are code.

### Inventor

- **Strong signals:** the owner asks for new ideas, an original product or a novel mechanism; existing approaches demonstrably fail the requirements; open "what if" exploration; prototypes of unproven concepts.
- **Weak signals:** choosing among known options. That is Researcher or Architect work.
- **Do not activate for:** routine implementation, or when the owner asked for a conventional solution.

## Combination recipes

| Situation | Disciplines | Lead | Sequence |
|---|---|---|---|
| New application | Architect, Designer, Engineer | Engineer (Architect leads the Architecture phase) | Architect, then Designer once the domain model is stable, then Engineer |
| Completely new technology | Researcher, Inventor, Architect, Engineer | Inventor | Researcher maps prior art, Inventor generates concepts, Architect shapes the system, Engineer prototypes |
| Complete product redesign | Researcher, Designer, Architect, Engineer | Designer | Researcher audits the product and its users, Designer redesigns, Architect assesses impact underneath, Engineer builds |
| Performance investigation | Researcher, Architect, Engineer | Engineer | Measure, then Architect if the cause is structural, then fix, then measure again |
| Debugging | Engineer, plus Researcher for unfamiliar errors, plus Architect for systemic causes | Engineer | Reproduce, isolate, fix, verify |
| Technology comparison | Researcher, plus Architect when architectural fit decides it | Researcher | Define criteria, gather evidence, recommend |
| Security-sensitive change | Engineer and Architect, plus Researcher for standards | Engineer | Follow [sensitive-change.md](../workflows/sensitive-change.md) |
| Design system | Designer, plus Engineer to implement | Designer | Audit, tokens, components, documentation |
| API design | Architect, plus Engineer | Architect | Contract first, then implementation |
| Prototype of an idea | Inventor, Engineer | Inventor | Key assumption first, smallest test that could falsify it |
| Small change in known code | Engineer | Engineer | [lightweight-task.md](../workflows/lightweight-task.md) |

## Lead rules

- Exactly one lead per deliverable. Multi-deliverable tasks may have a different lead per deliverable.
- The lead decides within its discipline; cross-discipline conflicts go to the coordinator ([conflict order](intelligence-coordinator.md#running-disciplines-together)).
- Leadership may move between phases (Architect during Architecture, Engineer during Implementation). Announce the move only when the owner would care.

## Handoff contracts

A handoff is complete only when the receiving discipline can work without guessing.

| From, to | Artifact | Must contain |
|---|---|---|
| Researcher, any | Findings ([research-report.md](../templates/research-report.md)) | Question, answer, sources with dates and versions, confidence, open questions |
| Architect, Engineer | Architecture proposal or interface contract ([architecture-proposal.md](../templates/architecture-proposal.md)) | Components and responsibilities; interfaces with inputs, outputs and errors; data flow; constraints; decisions taken |
| Architect, Designer | Constraints note | Data available per screen, latency expectations, offline behavior, limits |
| Designer, Engineer | Design specification ([design-specification.md](../templates/design-specification.md)) | Tokens; components with every state; layouts per breakpoint; interaction and motion; accessibility requirements; content rules |
| Inventor, Architect or Engineer | Concept brief ([invention-concept.md](../templates/invention-concept.md)) | Core mechanism, key assumption to test, feasibility rating, prototype scope, kill criteria |
| Engineer, coordinator | Change and evidence | Files changed, checks run with output, known limitations |

## Escalation during a task

Add a discipline when evidence shows a gap, and say so in one line:

- A bug fix exposes a flawed data model: add the Architect.
- A feature turns out to need a new screen: add the Designer.
- A library behaves differently from its documentation: add the Researcher.
- Every known approach fails a hard requirement: add the Inventor.

Drop a discipline when its input is complete and nothing downstream needs it.

## Anti-patterns

- **Activating everything.** Five disciplines on a typo fix wastes the owner's time and buries the change.
- **Persona theater.** "As the Architect, I believe..." adds words, not quality. Present the work.
- **Research as procrastination.** Researching what the codebase or the conversation already answers.
- **Invention by default.** Proposing novel mechanisms when a standard one meets the requirements.
- **Design skipped for "small" interfaces.** Small interfaces still need states, errors and accessibility.

## Domain specialists

Domain specialists are separate skills (`mych-` prefix) that carry deep knowledge and tools for one domain. They complement the five disciplines rather than replacing them: the Engineer still writes the integration code, the Designer still owns the experience, and the coordinator still owns integration and verification.

| Specialist | Strong signals | Do not load for |
|---|---|---|
| `mych-3d-design` | Modeling, topology, UVs, materials, lighting, rendering, rigging, animation, glTF/GLB/OBJ/FBX/STL/USD, Blender or Geometry Nodes, 3D printing | 2D art, flat UI |
| `mych-image-generation` | Text-to-image, image-to-image, inpainting, outpainting, upscaling, background removal, batch image pipelines, diffusion models, ComfyUI | Hand-authored pixel art (use `mych-pixel-art`), vector icons |
| `mych-pixel-art` | Sprites, tilesets, sprite sheets, palettes, dithering, pixel animation, pixel UI | Photographic or high-resolution illustration |
| `mych-chatbot-engineering` | Conversational products, assistants, bots, memory, tool calling, retrieval, routing between models | One-off API calls with no conversation |
| `mych-api-integration` | Consuming or designing REST, GraphQL or WebSocket APIs; OAuth; rate limits; webhooks; SDKs | Purely local code with no network interface |
| `mych-emoji-language` | Emoji sets, Unicode sequences, platform rendering, custom emoji, iconographic visual language | Adding decoration to technical output |
| `mych-cloud-infrastructure` | Hosting, VMs, containers, networking, DNS, storage, CDNs, monitoring, backups, scaling, cost, disaster recovery | Code changes that do not affect deployment |
| `mych-runpod` | RunPod pods, serverless endpoints, network volumes, GPU selection, RunPod billing and lifecycle | Other providers (use `mych-cloud-infrastructure`) |

**Example combination, a 2D game:** Architect + Designer + **Engineer**, with `mych-pixel-art` for sprites and tiles; add `mych-image-generation` only for image processing or when a generation backend exists; add `mych-api-integration` only for online features. `mych-3d-design` stays unloaded unless the game uses 3D assets.

**Handoffs from specialists:**

| From, to | Artifact | Must contain |
|---|---|---|
| `mych-pixel-art`, Engineer | Sprite sheet and metadata | PNG with transparency, fixed cell size, frame order, animation names and frame durations, anchor points |
| `mych-3d-design`, Engineer | Exported asset | Format and version, units and scale, axis convention, triangle count, materials and texture paths, animation clips |
| `mych-image-generation`, any | Generated or processed images | Backend actually used (or none), parameters and seed, dimensions, color mode, alpha, provenance and license notes |
| `mych-api-integration`, Engineer | Client contract | Documented endpoints used (with links), auth method, rate limits, retry and idempotency policy, error mapping |
| `mych-cloud-infrastructure` or `mych-runpod`, owner | Deployment plan | Resources, cost estimate with stated prices, persistence of data, approval points, shutdown and rollback steps |

If a needed specialist skill is not installed, say so, continue with the core disciplines, and never imply the specialist's tools ran.

## Registering a new discipline

1. Create `modes/<name>.md` with the sections every mode manual uses: purpose, activation signals, responsibilities, workflow, outputs, quality bar, anti-patterns, handoffs, tool use.
2. Add its entry to the [signal catalog](#signal-catalog), any recipes it joins, and the [handoff contracts](#handoff-contracts).
3. Add it to the specialist table and the file map in `SKILL.md`.
4. Run `scripts/validate-skill.py` on the skill folder until it passes.
