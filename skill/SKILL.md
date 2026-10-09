---
name: unreal
description: Operate Unreal Editor (UE 5.8, macOS) from the shell with the `ue` CLI. Covers project setup for MCP, starting, stopping and building the editor, running Python, console commands, viewport and editor screenshots, logs, and Mac-specific gotchas. Pairs with Epic's `unreal-mcp` skill, which covers toolset discovery and safety. Use for any Unreal Engine, UE5 or .uproject task.
---

# Driving Unreal Editor

Kit: ue-agent-kit (the README next to this skill's real path has details). `ue` is on PATH; it finds the project from the
nearest `*.uproject` above the cwd (or `$UE_PROJECT`). Engine: `/Users/Shared/Epic Games/UE_5.8`.

## New or unconfigured project
```bash
ue setup            # enables ModelContextProtocol, AllToolsets, Python, AgentTools; MCP port 18765; writes .mcp.json
ue build            # C++ projects only, editor must be stopped
ue start            # launches the editor and waits until MCP answers (~40 s warm)
```
`.mcp.json` registers `unreal-mcp` natively for Claude Code sessions started in that project
(tools: `list_toolsets`, `describe_toolset`, `call_tool`). It is auto-approved in user settings.
Epic's plugin `unreal-engine-skills-for-claude-code` is installed. Its `unreal-mcp` skill is the
reference for toolset discovery, safety rules, and project Agent Skills, and its `create-toolset`
skill covers writing new tools. The `ue` CLI works with or without the native connection. Use it
for lifecycle and images, and whenever the session started outside the project.

## Daily loop
```bash
ue headless x.py              # no editor UI needed (~15 s)
ue status | ue log -n 80 -g 'Error|Warning'
ue py 'result = [a.get_actor_label() for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()]'
ue py -f script.py           # globals persist between calls
ue cmd 'stat unit'
ue list                      # ~55 toolsets
ue describe editor_toolset.toolsets.blueprint.BlueprintTools
ue call EditorToolset.EditorAppToolset.StartPIE '{}'
ue capture out.png [--annotate]   # editor-camera render; --annotate = metre grid + actor labels
ue shot out.png              # whole editor as the user sees it (use during PIE)
ue play / ue stop-play
ue stop / ue restart         # stop waits for the process and the port to clear
```
Then Read the PNG to look at it. Judge visual work from images, never from numbers alone.

## Tool choice
- Python (`ue py`) for anything the `unreal` module exposes; it's the most general path.
- Official toolsets where they beat raw Python: Blueprint graphs (`read_graph_dsl` / `write_graph_dsl`,
  call `get_graph_dsl_docs` first), materials, Niagara, PCG, Sequencer/Control Rig, UMG, StateTree,
  GAS inspection, automation tests, config, plugins.
- Editor UI with no API: `SlateInspectorToolset` (Snapshot → Click/Type by ref, Screenshot) — Playwright-style.
- Outside the editor (Epic Launcher, Fab web panel, OS dialogs): a desktop GUI driver, if one is available.
- C++: edit source, then `ue stop && ue build && ue start`. Live Coding is Windows-only. Ignore Epic's
  skill advice to use `LiveCodingToolset.CompileLiveCoding`: on Mac it returns "not available".
- Headless or CI work with no editor running: `UnrealEditor-Cmd X.uproject -run=pythonscript -script=/abs.py -unattended -nullrhi`,
  and tests via `-ExecCmds="Automation RunTests Filter;Quit"`.

## Gotchas
- "Optional" struct params (e.g. CaptureViewport `captureTransform`, `annotations`) must be passed
  explicitly as `null`, otherwise the call fails with "needs a default value".
- Actor params want object paths, not labels: get them via `a.get_path_name()` in `ue py`.
- `ue capture` during PIE still renders from the editor camera; use `ue shot` for the player view.
- Two editors can't share a port: `ue setup --port N` for a second project.
- Stop for passwords, EULAs and purchases (Fab, Launcher) and ask the user.
