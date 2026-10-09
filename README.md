# ue-agent-kit

Lets a coding agent (Claude Code) drive Unreal Editor 5.8 on macOS from the shell, on top of
Epic's official **Unreal MCP** plugin (`ModelContextProtocol`, experimental, ships with UE 5.7+).

- `bin/ue`: single-file CLI. Editor lifecycle (start/stop/build/log), a streamable-HTTP MCP client,
  viewport/editor screenshots saved as PNGs, and `ue setup` to configure any project.
- `plugin/AgentTools`: content-only editor plugin copied into each project. It registers an extra
  toolset with `exec_python` (unrestricted, persistent globals) and `console`. Epic's own
  `ProgrammaticToolset` sandboxes imports, which blocks most real work.
- `skill/SKILL.md`: Claude Code skill (symlinked to `~/.claude/skills/unreal`).

## Install (done on this machine)

```bash
ln -sf ~/projects/ue-agent-kit/bin/ue ~/.local/bin/ue
ln -sfn ~/projects/ue-agent-kit/skill ~/.claude/skills/unreal
claude plugin install unreal-engine-skills-for-claude-code@claude-plugins-official   # Epic's skills + hook
# ~/.claude/settings.json: "enabledMcpjsonServers": ["unreal-mcp"]  (auto-approves the project .mcp.json entry)
```

Epic's plugin adds the skills `unreal-mcp` (discovery, dispatch and safety), `create-toolset` and
`unreal-skill`, plus a SessionStart hook that detects UE projects. Its advice to use Live Coding does
not apply on Mac.

## Per project

```bash
cd MyGame && ue setup && ue build && ue start
```

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

## Known quirks

- Struct params that are "optional" must be sent as explicit `null` ("needs a default value" otherwise).
- Actor params take object paths, not labels.
- `CaptureViewport` uses the editor camera even during PIE; `ue shot` shows the PIE view.
- Live Coding is Windows-only. On Mac: `ue stop && ue build && ue start`.
- Headless `UnrealEditor-Cmd` hides `print` output unless `-AllowStdOutLogVerbosity` is passed, and its
  UnrealTraceServer daemon inherits stdout, so never read it through a pipe. `ue headless` handles both.
- Default port 8000 collides with common dev servers, so the kit uses 18765.

## Outside the editor

Epic Games Launcher, the Fab web panel and OS dialogs have no API. Use
`~/projects/mac-gui-driver/gui.sh` for those.

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
