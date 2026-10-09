# ue-agent-kit

Lets a coding agent (Claude Code) drive Unreal Editor 5.8 on macOS from the shell, on top of
Epic's official **Unreal MCP** plugin (`ModelContextProtocol`, experimental, ships with UE 5.8).
Tested on UE 5.8.3, macOS 27, Apple Silicon. Most of it is platform-neutral, but the editor
lifecycle commands assume macOS paths.

- `bin/ue`: single-file CLI with no dependencies. It covers:
  - project creation and setup (`ue new`, `ue setup`)
  - editor lifecycle (start/stop/build/log)
  - a streamable-HTTP MCP client (`ue call`, `ue py`)
  - Play-In-Editor input (`ue input`)
  - viewport, editor and game screenshots saved as PNGs
- `plugin/AgentTools`: content-only editor plugin copied into each project. It registers a toolset with:
  - `exec_python`: unrestricted, with persistent globals. Epic's own `ProgrammaticToolset` sandboxes
    imports, which blocks most real work.
  - `console`: runs console commands.
  - `hold_input`: holds an Enhanced Input action for the PIE player.

  It also turns off the editor's background CPU throttling.
- `skill/SKILL.md`: Claude Code skill (symlinked to `~/.claude/skills/unreal`).

## Install

Requirements: UE 5.8 from the Epic Games Launcher, Xcode (for C++ projects), Python 3.9+.

```bash
git clone https://github.com/syyzit/ue-agent-kit ~/ue-agent-kit
ln -sf ~/ue-agent-kit/bin/ue ~/.local/bin/ue            # any dir on PATH
ln -sfn ~/ue-agent-kit/skill ~/.claude/skills/unreal     # Claude Code skill
claude plugin install unreal-engine-skills-for-claude-code@claude-plugins-official   # Epic's skills + hook
```

Optionally add `"enabledMcpjsonServers": ["unreal-mcp"]` to `~/.claude/settings.json` so Claude Code
connects to the editor in set-up projects without asking first.

Epic's plugin adds the skills `unreal-mcp` (discovery, dispatch and safety), `create-toolset` and
`unreal-skill`, plus a SessionStart hook that detects UE projects. Its advice to use Live Coding does
not apply on Mac.

## Per project

```bash
ue new MyGame               # optional: new C++ project from the TP_Blank template
cd MyGame && ue setup && ue build && ue start
```

Run `ue --help` for every command. The ones you will use most:

```bash
ue py 'result = unreal.SystemLibrary.get_engine_version()'      # editor Python
ue call editor_toolset.toolsets.blueprint.BlueprintTools.write_graph_dsl graph=/Game/BP_X.BP_X:EventGraph code=@graph.dsl
ue play && ue input /Game/Input/IA_Move 1 --for 2 --wait && ue shot --game run.png
ue record run/ --seconds 2 --slowmo 4   # labelled contact sheet + 0.25x mp4 of the next 2 s of PIE
```

### Watching motion: `ue record`

Agents judge motion badly from single screenshots, and real-time capture drops frames whenever
rendering is slow. `ue record` turns on the engine's fixed frame rate, so every frame advances exactly
1/fps of game time; the game slows down while frames are written instead of skipping them. It then
dumps the next N frames (`r.DumpingMovie`) and builds two outputs:
- `sheet.png`, a labelled grid of evenly spaced frames, for the agent to read
- `clip.mp4`, optionally slowed down, for a human to watch

The frame-rate settings restore themselves in the editor when the dump ends.

`ue setup` makes these changes:
1. It enables `ModelContextProtocol`, `AllToolsets`, `PythonScriptPlugin`, `EditorScriptingUtilities`
   and `AgentTools` in the `.uproject`.
2. It copies `plugin/AgentTools` into `Plugins/`. Re-run `ue setup` after changing the kit.
3. It writes `Config/DefaultEditorPerProjectUserSettings.ini` with auto-start, port 18765 and tool search.
4. It adds a GameFeatureData Asset Manager rule to `DefaultGame.ini`. AllToolsets enables GameFeatures,
   which logs a load error without the rule.
5. It writes `.mcp.json` with `{"unreal-mcp": {"type": "http", "url": "http://127.0.0.1:18765/mcp"}}`, the
   same name `ModelContextProtocol.GenerateClientConfig ClaudeCode` would use.

With tool search on, the server exposes only `list_toolsets`, `describe_toolset` and `call_tool`, and
the ~55 toolsets are discovered on demand. That keeps Claude's context small.

## What the official plugin gives you (5.8.3)

Blueprint graphs (read/write via a text DSL, nodes, pins, variables, functions), actors/scene, assets,
materials and instances, static/skeletal meshes, textures, data assets/tables, curve/string tables,
Niagara, PCG, Sequencer and Control Rig keyframing, UMG widgets, StateTree, Behavior Trees, GAS
inspection, gameplay tags, game features, physics assets, Dataflow, config settings, plugins,
automation tests, semantic asset search, output log, PIE control, viewport camera and capture
(with an optional annotated grid), full-editor screenshot, and Playwright-style Slate UI automation
(snapshot, click, type, drag by widget ref).

## Field test: a 2.5D platformer built entirely by an agent

To shake out the kit, Claude built a small side-scrolling platformer through it, without touching the
editor UI. The game has:
- a C++ character locked to a plane, with a side camera
- Enhanced Input assets
- a base material plus 8 instances
- coin, spike and goal Blueprints written in the graph DSL
- a UMG HUD
- a level generated by a Python script

An editor-side bot then completed the course through real input injection, collecting 15/15 coins
with 0 deaths. Problems found along the way, and how each was resolved:

| Problem | Resolution |
|---|---|
| A backgrounded editor throttles to ~3 fps: every MCP call took ~1 s and PIE physics ran at 3 fps | AgentTools disables `bThrottleCPUWhenNotForeground` at startup (0.09 s per call) |
| After `ue restart`, the MCP server failed to bind (port in TIME_WAIT), and `start` waited 10 min | `start`/`stop` check that the port is bindable; `start` fails fast when the log shows a bind error |
| A startup Message Log popup covered every screenshot | `ue start` closes it; `ue windows` / `ue close` for others |
| No way to capture the game view or hold input in PIE | `ue shot --game` (HighResShot), `ue input` / `hold_input` |
| `UnrealEditor-Cmd` hid `print` output and hung when read through a pipe (UnrealTraceServer inherits stdout) | `ue headless` |
| Passing JSON args in shell was error-prone | `ue call key=value key:=json key=@file` |
| Creating a project meant hand-renaming template modules | `ue new` |
| No way to see motion: screenshots miss it, and real-time capture drops frames | `ue record` (fixed timestep frame dump, contact sheet, slow-mo mp4) |

These are engine and toolset quirks with no kit-side fix. The skill documents them:
- "optional" struct params must be explicit `null`
- params need full object paths
- `set_properties` takes a JSON string
- DSL event names carry a category prefix
- `unreal.Rotator` positional order is roll, pitch, yaw
- Python struct getters return copies
- spawned lights default to Stationary
- `InputActionValue` can't be built from Python

## Known quirks

- `CaptureViewport` uses the editor camera even during PIE. Use `ue shot --game` for the game view
  (no HUD), or `ue shot` for the whole editor.
- Live Coding is Windows-only. On Mac: `ue stop && ue build && ue start`.
- Default port 8000 collides with common dev servers, so the kit uses 18765.

## Outside the editor

Epic Games Launcher, the Fab web panel and OS dialogs have no API. They need a desktop
automation tool that can screenshot windows and click (Accessibility + Screen Recording permissions).

## Third-party landscape (checked 2026-10-09)

On UE 5.8 the official plugin covers what the popular community servers were built for. None of the
following are installed:

- **Abandoned:** chongdashu/unreal-mcp, kvick-games/UnrealMCP, runreal/unreal-mcp, ayeletstudioindia/unreal-analyzer-mcp.
  flopperam/unreal-engine-mcp was absorbed into the paid Aura product.
- **Active but redundant:** ChiR24/Unreal_mcp, GenOrca/unreal-mcp (its binaries are Win64-only),
  IvanMurzak/Unreal-MCP (relays through a cloud service by default), aadeshrao123/Unreal-MCP (open-core),
  appleweed/UnrealMCPBridge, and Natfii/UnrealClaude, which supports 5.7 only. The 5.8 Terminal plugin can
  already run `claude` inside the editor.
- **The one worth considering:** kevinpbuckley/VibeUE (MIT, 5.8+). It registers extra toolsets into Epic's
  own registry and covers terrain, audio, animation, undo transactions and profiling. It needs a C++
  project and an Xcode build.
- **Commercial:** Aura is its own in-editor agent, not a Claude backend. Ludus does not work on Mac yet.
- **Plain CLI routes still worth knowing:** `Build.sh` / `RunUAT.sh BuildCookRun`,
  `UnrealEditor-Cmd -ExecCmds="Automation RunTests X;Quit"`, Unreal Insights (`-trace=default`), and the
  Remote Control API (:30010) and Python remote execution (:6766), both of which MCP has superseded.

## Security

The MCP server listens on loopback only and has no authentication. `AgentTools.exec_python` runs
arbitrary Python in the editor, so treat any local process as able to control your project.
Use this on dev machines only, and save or commit before long agent sessions.

## License

MIT
