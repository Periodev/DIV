# replay_core.py - Input sequence replayer (pure logic, no Arcade dependency)

from map_parser import parse_dual_layer
from game_controller import GameController


DIRECTION_MAP = {
    'U': (0, -1),
    'D': (0,  1),
    'L': (-1, 0),
    'R': (1,  0),
}


def execute_action(controller, char: str, hints: dict):
    """Apply one input character to a controller in-place.

    Shared by Replayer (sequential replay) and Solver (BFS branching).
    Does not run physics or check victory — caller is responsible.
    """
    c = controller
    if c.collapsed or c.victory:
        return
    if char in DIRECTION_MAP:
        c.handle_move(DIRECTION_MAP[char])
    elif char == 'V':
        c.try_branch()
    elif char == 'C':
        c.try_merge()
    elif char == 'F':
        c.try_fetch_merge()
    elif char == 'T':
        c.switch_focus()
    elif char == 'X':
        c.handle_adaptive_action(
            allow_converge=hints.get('converge', True),
            allow_pickup=hints.get('pickup', True),
        )
    elif char == 'P':
        c.handle_pickup(allow_pickup=hints.get('pickup', True))
    elif char == 'O':
        c.handle_drop()


class Replayer:
    """Replays a recorded input sequence against a level.

    seek(pos) resets and re-executes from scratch to reach any position,
    so the controller state is always consistent.
    """

    def __init__(self, level_dict: dict):
        source = parse_dual_layer(level_dict['floor_map'], level_dict['object_map'])
        self.hints = level_dict.get('hints') or {
            'diverge': True, 'converge': True, 'pickup': True, 'fetch': True,
        }
        self._source = source
        self._controller = GameController(source)
        self._sequence = ''
        self._position = 0

    def load(self, sequence: str):
        """Load a new input sequence and reset to start."""
        self._sequence = sequence
        self.seek(0)

    def seek(self, pos: int):
        """Reset and replay to position pos."""
        pos = max(0, min(pos, len(self._sequence)))
        self._controller.reset()
        for char in self._sequence[:pos]:
            self._execute(char)
        self._position = pos
        # Settle victory state (mirrors game's per-frame check)
        c = self._controller
        if not c.collapsed and not c.victory:
            c.update_physics()
        if not c.victory:
            c.check_victory()

    def step_forward(self) -> bool:
        """Advance one step. Returns False if already at end."""
        if self._position >= len(self._sequence):
            return False
        self._execute(self._sequence[self._position])
        self._position += 1
        return True

    def step_back(self) -> bool:
        """Step back one position by seeking to pos-1."""
        if self._position <= 0:
            return False
        self.seek(self._position - 1)
        return True

    def _execute(self, char: str):
        """Execute one input character and settle physics."""
        execute_action(self._controller, char, self.hints)
        c = self._controller
        if not c.collapsed and not c.victory:
            c.update_physics()

    @property
    def controller(self) -> GameController:
        return self._controller

    @property
    def position(self) -> int:
        return self._position

    @property
    def length(self) -> int:
        return len(self._sequence)

    @property
    def at_end(self) -> bool:
        return self._position >= len(self._sequence)

    @property
    def sequence(self) -> str:
        return self._sequence

