"""MCP tools for driving the editor from a coding agent.

Epic's stock toolsets sandbox Python imports; agents regularly need the full
`unreal` API (IK retargeting, Control Rig, Sequencer, Movie Render Queue), so
this exposes an unrestricted exec. The MCP server listens on loopback only;
dev machines only.
"""

import contextlib
import io
import traceback

import unreal

import toolset_registry

# Persists between calls so multi-step work can keep references around.
_SESSION_GLOBALS: dict = {"unreal": unreal}


@unreal.uclass()
class AgentTools(unreal.ToolsetDefinition):
    """Unrestricted Python execution inside the editor, plus console commands."""

    @toolset_registry.tool_call
    @staticmethod
    def exec_python(code: str) -> str:
        """Executes Python in the editor with full access to the `unreal` module.

        Globals persist between calls. Assign to `result` to return a value.

        Args:
            code: Python source to execute.

        Returns:
            Captured stdout, followed by repr(result) if set, or the traceback on error.
        """
        out = io.StringIO()
        _SESSION_GLOBALS.pop("result", None)
        try:
            with contextlib.redirect_stdout(out):
                exec(compile(code, "<mcp>", "exec"), _SESSION_GLOBALS)
        except Exception:
            return out.getvalue() + "\n" + traceback.format_exc()
        text = out.getvalue()
        if "result" in _SESSION_GLOBALS:
            text += ("\n" if text else "") + repr(_SESSION_GLOBALS["result"])
        return text

    @toolset_registry.tool_call
    @staticmethod
    def console(command: str) -> str:
        """Runs an editor console command (e.g. `stat fps`, `HighResShot 2`).

        Runs against the PIE world when Play-In-Editor is active, else the editor world.

        Args:
            command: The console command line.

        Returns:
            Which world the command ran in.
        """
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = editor.get_game_world() or editor.get_editor_world()
        unreal.SystemLibrary.execute_console_command(world, command)
        return f"ran in {world.get_path_name()}"
