---
name: unreal
description: Operate Unreal Editor (UE 5.8, macOS) from the shell with the `ue` CLI. Covers creating and setting up projects for MCP, starting, stopping and building the editor, running Python, calling toolsets, driving PIE with real input, screenshots, logs, and the gotchas found building a game this way. Pairs with Epic's `unreal-mcp` skill, which covers toolset discovery and safety. Use for any Unreal Engine, UE5 or .uproject task.
---

# Driving Unreal Editor

Kit: ue-agent-kit (the README next to this skill's real path has details). `ue` is on PATH; it finds the project from the
nearest `*.uproject` above the cwd (or `$UE_PROJECT`). Engine: `/Users/Shared/Epic Games/UE_5.8`.

## New or unconfigured project
```bash
ue new MyGame [parent-dir]   # copies + renames the TP_Blank C++ template (--template TP_BlankBP etc.)
cd MyGame && ue setup        # enables ModelContextProtocol, AllToolsets, Python, AgentTools; MCP :18765; .mcp.json
ue build                     # C++ projects only, editor must be stopped (~20-60 s)
ue start                     # launches, waits for MCP (~15 s warm), closes the startup Message Log popup
```
`.mcp.json` registers `unreal-mcp` natively for Claude Code sessions started in that project
(tools: `list_toolsets`, `describe_toolset`, `call_tool`). Epic's plugin `unreal-engine-skills-for-claude-code`
provides the `unreal-mcp` skill (discovery, safety, project Agent Skills) and `create-toolset`.
The `ue` CLI works with or without the native connection; use it for lifecycle, images and input.

## Daily loop
```bash
ue status | ue log -n 80 -g 'Error|Warning'
ue py 'result = ...'  |  ue py -f script.py     # editor Python; globals persist between calls
ue headless x.py                                # no editor running (~15 s)
ue cmd 'stat unit'                              # console command (PIE world when playing)
ue list | ue describe <toolset>
ue call <toolset.tool> key=string n:=1 obj:='{"x":1}' code=@file.dsl   # httpie-style args
ue capture out.png [--annotate]                 # editor-camera render (not the PIE view)
ue play / ue stop-play
ue input /Game/Input/IA_Move 1 --for 1.5 [--wait]   # hold an Enhanced Input action in PIE (real mapping path)
ue shot --game out.png [--size 1600x900]        # PIE game view, no HUD
ue shot out.png                                 # whole editor incl. PIE + HUD
ue record dir --seconds 2 [--fps 60] [--slowmo 4]   # fixed-timestep frame dump -> dir/sheet.png + dir/clip.mp4
ue windows | ue close 'Message Log'             # popups that cover screenshots
ue stop | ue restart | ue build
```
Read the PNGs. Judge visual work from images, never from numbers alone. For anything that moves
(animation, physics, hit reactions, camera), use `ue record` and Read `sheet.png`: frames are
evenly spaced in game time and labelled, and the game slows down instead of dropping frames.
Start the action first (bot, `ue input`, ability), then record. Hand the user `clip.mp4`
(`--slowmo 4` for 0.25x). For gameplay logic, also record a position trace from an editor-side bot
(`unreal.register_slate_post_tick_callback`) and check it.

## Tool choice
- Python (`ue py`) for anything the `unreal` module exposes; it's the most general path.
- Official toolsets where they beat raw Python: Blueprint graphs (`write_graph_dsl`; call `get_graph_dsl_docs`
  and `read_graph_dsl` first), materials (`MaterialTools`, `MaterialInstanceTools`), UMG, Niagara, PCG,
  Sequencer/Control Rig, StateTree, GAS inspection, automation tests, config, plugins.
- Blueprint components: `ActorTools.add_component owner=/Game/BP/BP_X.BP_X ...`; the template is then
  `/Game/BP/BP_X.BP_X_C:<Name>_GEN_VARIABLE` (set properties on that).
- Editor UI with no API: `SlateInspectorToolset` (Snapshot, Click/Type by ref, Windows).
- Outside the editor (Epic Launcher, Fab web panel, OS dialogs): a desktop GUI driver, if one is available.
- C++: edit source, then `ue stop && ue build && ue start`. Live Coding is Windows-only. Ignore Epic's
  advice to use `LiveCodingToolset.CompileLiveCoding`: on Mac it returns "not available".

## Gotchas (all hit while building a test game)
- Tool params take full object paths: assets `/Game/Dir/Name.Name`, classes `/Script/Engine.StaticMeshComponent`,
  sub-objects `...:WidgetTree.ScoreText`. Short names fail with "is not a valid object path".
- "Optional" struct params (CaptureViewport `captureTransform`, `annotations`) must be sent as explicit `null`.
- `ObjectTools.set_properties` wants `values` as a JSON *string* with camelCase names (`values='{"sphereRadius":60}'`).
  It returns false (or names the failures) instead of raising, so check the result. Nested body-instance
  fields like `collisionProfileName` can't be set this way; use Python `comp.set_collision_profile_name(...)`.
- Properties Python can't reach by name: `unreal.ToolsetLibrary.set_object_properties(obj, json_str)`.
- Blueprint DSL event names include their category: `(event Collision|EventActorBeginOverlap (OtherActor) ...)`.
  `read_graph_dsl` on a fresh Blueprint shows the exact names.
- `unreal.Rotator(a, b, c)` positional order is **roll, pitch, yaw**. Always pass keywords.
- Struct getters return copies: modify, then `set_editor_property` the whole struct/array back
  (e.g. InputMappingContext `default_key_mappings`).
- Spawned lights default to Stationary. With static lighting off (the default for new projects) set them
  Movable, or the SkyLight contributes nothing and shadows go pure black.
- Python can't build an `InputActionValue`; use `ue input` / `AgentTools.hold_input`. The PIE player's
  `EnhancedInputLocalPlayerSubsystem` is only reachable via `unreal.ObjectIterator`.
- Teleporting a Character from inside an overlap callback leaks momentum; defer to the next Tick.
- HighResShot (`ue shot --game`) excludes UMG; use `ue shot` to check the HUD.
- zsh: `"$VAR:Something"` applies a history modifier. Write `"${VAR}:Something"`.
- Two editors can't share a port: `ue setup --port N` for a second project.
- Stop for passwords, EULAs and purchases (Fab, Launcher) and ask the user.

Handled by the kit (don't re-solve): background CPU throttling (made every call take ~1 s and ran PIE at
~3 fps; AgentTools disables it at startup), TIME_WAIT on the MCP port after a restart, headless stdout.
