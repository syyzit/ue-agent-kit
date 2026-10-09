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

# Enhanced Input actions currently being held: action path -> (action, value, game-time deadline).
_HELD: dict = {}
_TICK_HANDLE = None


def _player_input_subsystem():
    """The PIE player's EnhancedInputLocalPlayerSubsystem (Python has no LocalPlayer accessor)."""
    subs = [s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem)
            if not s.get_path_name().startswith(("/Script", "Default__"))]
    return subs[-1] if subs else None


def _game_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def _tick(delta_seconds: float) -> None:
    # Slate's delta does not track game time, so holds are timed against the PIE world clock.
    global _TICK_HANDLE
    world = _game_world()
    sub = _player_input_subsystem() if world else None
    now = unreal.GameplayStatics.get_time_seconds(world) if world else 0.0
    for path, (action, value, deadline) in list(_HELD.items()):
        if sub is None or now >= deadline:
            del _HELD[path]
            continue
        # Re-injecting every frame looks like a held key: Started, Triggered..., then Completed once it stops.
        sub.inject_input_vector_for_action(action, value, [], [])
    if not _HELD and _TICK_HANDLE is not None:
        unreal.unregister_slate_post_tick_callback(_TICK_HANDLE)
        _TICK_HANDLE = None


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

    @toolset_registry.tool_call
    @staticmethod
    def hold_input(action: str, x: float, y: float, z: float, seconds: float) -> str:
        """Holds an Enhanced Input action for the PIE player, as if its key were held down.

        Goes through the player's mapping context, triggers and modifiers. Returns
        immediately; the input is injected every frame until `seconds` elapse.
        Pass seconds <= 0 to release early. Use a short hold (0.1) for a tap.

        Args:
            action: InputAction asset path, e.g. /Game/Input/IA_Jump.
            x: Value on the first axis (1.0 for a digital press, -1.0 for negative axis).
            y: Second axis value (2D/3D actions), else 0.
            z: Third axis value (3D actions), else 0.
            seconds: How long to hold, in game time.

        Returns:
            What is being held, or why nothing could be.
        """
        global _TICK_HANDLE
        world = _game_world()
        if not world:
            return "PIE is not running"
        if _player_input_subsystem() is None:
            return "no EnhancedInputLocalPlayerSubsystem found"
        asset = unreal.load_asset(action)
        if not isinstance(asset, unreal.InputAction):
            return f"{action} is not an InputAction"
        if seconds <= 0:
            _HELD.pop(asset.get_path_name(), None)
            return f"released {action}"
        deadline = unreal.GameplayStatics.get_time_seconds(world) + seconds
        _HELD[asset.get_path_name()] = (asset, unreal.Vector(x, y, z), deadline)
        if _TICK_HANDLE is None:
            _TICK_HANDLE = unreal.register_slate_post_tick_callback(_tick)
        return f"holding {action} = ({x}, {y}, {z}) for {seconds}s"
