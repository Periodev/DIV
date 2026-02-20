# replay_view.py - Visual replay using existing renderer

import arcade
from render_arc import ArcadeRenderer, WINDOW_WIDTH, WINDOW_HEIGHT
from presentation_model import ViewModelBuilder
from replay_core import Replayer


STEPS_PER_SECOND = 4  # auto-play speed


class ReplayView(arcade.View):
    def __init__(self, replayer: Replayer, title: str = "Replay"):
        super().__init__()
        self.replayer = replayer
        self.renderer = ArcadeRenderer()
        self.renderer.set_grid_size(replayer.controller.source.grid_size)
        self.title = title

        self.animation_frame = 0
        self.auto_play = False
        self.time_since_step = 0.0
        self.step_interval = 1.0 / STEPS_PER_SECOND

    def on_show_view(self):
        arcade.set_background_color((20, 20, 25))
        self.window.set_update_rate(1 / 60)

    def on_update(self, delta_time: float):
        self.animation_frame += 1
        if self.auto_play and not self.replayer.at_end:
            self.time_since_step += delta_time
            if self.time_since_step >= self.step_interval:
                self.time_since_step = 0.0
                self.replayer.step_forward()

        # Mirror game behaviour: check victory every frame
        c = self.replayer.controller
        if not c.collapsed and not c.victory:
            c.update_physics()
        if not c.victory:
            c.check_victory()

    def on_draw(self):
        self.clear()

        frame_spec = ViewModelBuilder.build(
            self.replayer.controller,
            self.animation_frame,
            hints=self.replayer.hints,
        )
        self.renderer.draw_frame(frame_spec)
        self._draw_hud()

    def _draw_hud(self):
        r = self.replayer

        # Title
        arcade.draw_text(
            self.title, WINDOW_WIDTH // 2, WINDOW_HEIGHT - 18,
            (150, 150, 150), 12, anchor_x='center', anchor_y='center',
        )

        # Step counter
        arcade.draw_text(
            f"Step {r.position} / {r.length}",
            WINDOW_WIDTH // 2, WINDOW_HEIGHT - 38,
            (220, 220, 220), 18, anchor_x='center', anchor_y='center',
            bold=True,
        )

        # Current / result indicator
        if r.at_end:
            if r.controller.victory:
                label, color = "VICTORY", (100, 220, 100)
            elif r.controller.collapsed:
                label, color = "COLLAPSED", (220, 100, 100)
            else:
                label, color = "END (no victory)", (200, 180, 80)
            arcade.draw_text(
                label, WINDOW_WIDTH // 2, WINDOW_HEIGHT - 60,
                color, 14, anchor_x='center', anchor_y='center',
            )
        else:
            next_char = r.sequence[r.position]
            arcade.draw_text(
                f"Next: {next_char}",
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - 60,
                (150, 200, 150), 13, anchor_x='center', anchor_y='center',
            )

        # Playback state + controls
        state = "▶ AUTO" if self.auto_play else "⏸ PAUSED"
        arcade.draw_text(
            f"{state}   Space: play/pause   ←→: step   R: restart   ESC: quit",
            WINDOW_WIDTH // 2, 15,
            (100, 100, 100), 12, anchor_x='center', anchor_y='bottom',
        )

    def on_key_press(self, key, modifiers):
        if key == arcade.key.SPACE:
            self.auto_play = not self.auto_play
            self.time_since_step = 0.0
        elif key == arcade.key.RIGHT:
            self.auto_play = False
            self.replayer.step_forward()
        elif key == arcade.key.LEFT:
            self.auto_play = False
            self.replayer.step_back()
        elif key == arcade.key.R:
            self.auto_play = False
            self.replayer.seek(0)
        elif key == arcade.key.ESCAPE:
            arcade.exit()
