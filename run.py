"""
Pygame presentation layer for Minesweeper.

This module owns:
- Renderer: all drawing of cells, header, and result overlays
- InputController: translate mouse input to board actions and UI feedback
- Game: orchestration of loop, timing, state transitions, and composition

The logic lives in components.Board; this module should not implement rules.
"""

import sys
import pygame

import config
from components import Board
from pygame.locals import Rect


# 난이도 키 입력과 보드 설정 매핑
DIFFICULTIES = {
    pygame.K_1: ("EASY", 9, 9, 10),
    pygame.K_2: ("NORMAL", 16, 16, 40),
    pygame.K_3: ("HARD", 30, 16, 99),
}


class Renderer:
    """Draws the Minesweeper UI."""

    def __init__(self, screen: pygame.Surface, board: Board):
        self.screen = screen
        self.board = board
        self.font = pygame.font.Font(config.font_name, config.font_size)
        self.header_font = pygame.font.Font(config.font_name, config.header_font_size)
        self.result_font = pygame.font.Font(config.font_name, config.result_font_size)

    def cell_rect(self, col: int, row: int) -> Rect:
        x = config.margin_left + col * config.cell_size
        y = config.margin_top + row * config.cell_size
        return Rect(x, y, config.cell_size, config.cell_size)

    def draw_cell(self, col: int, row: int, highlighted: bool) -> None:
        cell = self.board.cells[self.board.index(col, row)]
        rect = self.cell_rect(col, row)

        if cell.state.is_revealed:
            pygame.draw.rect(self.screen, config.color_cell_revealed, rect)
            if cell.state.is_mine:
                pygame.draw.circle(self.screen, config.color_cell_mine, rect.center, rect.width // 4)
            elif cell.state.adjacent > 0:
                color = config.number_colors.get(cell.state.adjacent, config.color_text)
                label = self.font.render(str(cell.state.adjacent), True, color)
                label_rect = label.get_rect(center=rect.center)
                self.screen.blit(label, label_rect)
        else:
            base_color = config.color_highlight if highlighted else config.color_cell_hidden
            pygame.draw.rect(self.screen, base_color, rect)
            if cell.state.is_flagged:
                flag_w = max(6, rect.width // 3)
                flag_h = max(8, rect.height // 2)
                pole_x = rect.left + rect.width // 3
                pole_y = rect.top + 4
                pygame.draw.line(
                    self.screen,
                    config.color_flag,
                    (pole_x, pole_y),
                    (pole_x, pole_y + flag_h),
                    2,
                )
                pygame.draw.polygon(
                    self.screen,
                    config.color_flag,
                    [
                        (pole_x + 2, pole_y),
                        (pole_x + 2 + flag_w, pole_y + flag_h // 3),
                        (pole_x + 2, pole_y + flag_h // 2),
                    ],
                )

        pygame.draw.rect(self.screen, config.color_grid, rect, 1)


   
    def draw_header(self, remaining_mines: int, time_text: str, score: int) -> None:
        """Draw the header bar containing remaining mines and elapsed time."""

        pygame.draw.rect(
            self.screen,
            config.color_header,
            Rect(0, 0, config.width, config.margin_top - 4),
        )
        left_text = f"Mines: {remaining_mines}"
        center_text = f"Score: {score}"   # 점수 표시
        right_text = f"Time: {time_text}"
        left_label = self.header_font.render(left_text, True, config.color_header_text)
        right_label = self.header_font.render(right_text, True, config.color_header_text)
        self.screen.blit(left_label, (10, 12))
        self.screen.blit(right_label, (config.width - right_label.get_width() - 10, 12))

    def draw_result_overlay(self, text: str | None) -> None:
        if not text:
            return
        overlay = pygame.Surface((config.width, config.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, config.result_overlay_alpha))
        self.screen.blit(overlay, (0, 0))
        lines = text.split('\n')
        
        # 전체 텍스트 덩어리의 중앙 위치 계산을 위한 시작 Y 좌표
        line_spacing = config.result_font_size * 0.8
        total_height = len(lines) * line_spacing
        start_y = (config.height // 2) - (total_height // 2)

        for i, line in enumerate(lines):
            label = self.result_font.render(line, True, config.color_result)
            rect = label.get_rect(center=(config.width // 2, start_y + i * line_spacing))
            self.screen.blit(label, rect)
    def draw_difficulty_menu(self) -> None:
        self.screen.fill(config.color_bg)
        title = self.result_font.render("Select Difficulty", True, config.color_result)
        self.screen.blit(title, title.get_rect(center=(config.width // 2, 120)))

        options = [
            "1 - EASY (9 x 9, 10 mines)",
            "2 - NORMAL (16 x 16, 40 mines)",
            "3 - HARD (30 x 16, 99 mines)",
        ]

        for i, text in enumerate(options):
            label = self.font.render(text, True, config.color_text_inv)
            self.screen.blit(label, label.get_rect(center=(config.width // 2, 220 + i * 50)))

        pygame.display.flip()


class InputController:
    """Translates input events into game and board actions."""

    def __init__(self, game: "Game"):
        self.game = game

    def pos_to_grid(self, x: int, y: int):
        if not (config.margin_left <= x < config.width - config.margin_right):
            return -1, -1
        if not (config.margin_top <= y < config.height - config.margin_bottom):
            return -1, -1
        col = (x - config.margin_left) // config.cell_size
        row = (y - config.margin_top) // config.cell_size
        if 0 <= col < self.game.board.cols and 0 <= row < self.game.board.rows:
            return int(col), int(row)
        return -1, -1

    def handle_mouse(self, pos, button) -> None:
        col, row = self.pos_to_grid(pos[0], pos[1])
        if col == -1:
            return

        game = self.game


        if button == config.mouse_left:
            game.highlight_targets.clear()

            game.board.reveal(col, row)

        cell = game.board.cells[game.board.index(col, row)]

        if button == config.mouse_left:
            game.highlight_targets.clear()

            # ================== Issue #2 추가 ==================
            # 이미 열린 숫자 칸을 클릭한 경우, 주변 자동 오픈 시도
            if cell.state.is_revealed and cell.state.adjacent > 0:
                game.board.reveal_around_if_flag_match(col, row)
            else:
                game.board.reveal(col, row)



            # reveal 전 공개된 칸 수 저장
            prev_revealed = game.board.revealed_count
            game.board.reveal(col,row)

            # === 이슈 #5: 안전한 칸 오픈 시 점수 증가 (+10) ===
            opened = game.board.revealed_count - prev_revealed
            if opened > 0:
                game.score += opened * 10


            if not game.started:
                game.started = True
                game.start_ticks_ms = pygame.time.get_ticks()

        elif button == config.mouse_right:
            game.highlight_targets.clear()
            game.board.toggle_flag(col, row)

        elif button == config.mouse_middle:
            neighbors = game.board.neighbors(col, row)
            game.highlight_targets = {
                (nc, nr)
                for (nc, nr) in neighbors
                if not game.board.cells[game.board.index(nc, nr)].state.is_revealed
            }
            game.highlight_until_ms = pygame.time.get_ticks() + config.highlight_duration_ms


class Game:
    """Main application object orchestrating loop and high-level state."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.title)
        self.screen = pygame.display.set_mode(config.display_dimension)
        self.clock = pygame.time.Clock()

        self.difficulty_selected = False

        self.board = None
        self.renderer = None
        self.input = InputController(self)

        self.highlight_targets = set()
        self.highlight_until_ms = 0

        self.started = False
        self.start_ticks_ms = 0
        self.end_ticks_ms = 0


    def select_difficulty(self, cols: int, rows: int, mines: int) -> None:
        config.cols = cols
        config.rows = rows
        config.num_mines = mines

        config.width = config.margin_left + cols * config.cell_size + config.margin_right
        config.height = config.margin_top + rows * config.cell_size + config.margin_bottom
        config.display_dimension = (config.width, config.height)

        self.screen = pygame.display.set_mode(config.display_dimension)
        self.board = Board(cols, rows, mines)
        self.renderer = Renderer(self.screen, self.board)

        self.difficulty_selected = True

        # === 이슈 #5: 점수 관련 상태 ===
        self.score = 0
        self._win_bonus_given = False  # 승리 보너스 중복 방지

    def reset(self):
        """Reset the game state and start a new board."""
        self.board = Board(config.cols, config.rows, config.num_mines)
        self.renderer.board = self.board
        self.highlight_targets.clear()
        self.highlight_until_ms = 0
        self.started = False
        self.start_ticks_ms = 0
        self.end_ticks_ms = 0


    def _elapsed_ms(self) -> int:
        if not self.started:
            return 0
        if self.end_ticks_ms:
            return self.end_ticks_ms - self.start_ticks_ms
        return pygame.time.get_ticks() - self.start_ticks_ms

    def _format_time(self, ms: int) -> str:
        total_seconds = ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _result_text(self) -> str | None:
        time_str = self._format_time(self._elapsed_ms())
        
        if self.board.game_over:
            return f"GAME OVER\nScore: {self.score}\nTime: {time_str}"
        if self.board.win:
            return f"GAME CLEAR\nScore: {self.score}\nTime: {time_str}"
        return None

    def run_step(self) -> bool:
        """Process inputs, update time, draw, and tick the clock once."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            # 난이도 선택 전 입력 처리
            if not self.difficulty_selected:
                if event.type == pygame.KEYDOWN and event.key in DIFFICULTIES:
                    _, c, r, m = DIFFICULTIES[event.key]
                    self.select_difficulty(c, r, m)
                return True # 난이도 선택 중에는 아래 로직 건너뜀

            # 게임 중 입력 처리
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                if event.key == pygame.K_h:
                    if self.board:
                        self.board.reveal_safe_hint()
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.input.handle_mouse(event.pos, event.button)

        # 보드가 생성된 후에만 실행되는 로직
        if self.board:
            # === 이슈 #5: 승리 보너스 점수 (+1000) ===
            if self.board.win and not self._win_bonus_given:
                self.score += 1000
                self._win_bonus_given = True

            if (self.board.game_over or self.board.win) and self.started and not self.end_ticks_ms:
                self.end_ticks_ms = pygame.time.get_ticks()

        # 화면 그리기
        if not self.difficulty_selected:
            temp_renderer = Renderer(self.screen, None)
            temp_renderer.draw_difficulty_menu()
        else:
            if pygame.time.get_ticks() > self.highlight_until_ms:
                self.highlight_targets.clear()

            self.screen.fill(config.color_bg)
            remaining = max(0, config.num_mines - self.board.flagged_count())
            time_text = self._format_time(self._elapsed_ms())
            
            # 헤더와 셀 그리기
            self.renderer.draw_header(remaining, time_text, self.score)
            now = pygame.time.get_ticks()
            for r in range(self.board.rows):
                for c in range(self.board.cols):
                    highlighted = (now <= self.highlight_until_ms) and ((c, r) in self.highlight_targets)
                    self.renderer.draw_cell(c, r, highlighted)

            self.renderer.draw_result_overlay(self._result_text())
            pygame.display.flip()

        self.clock.tick(config.fps)
        return True


def main() -> int:
    game = Game()
    running = True
    while running:
        running = game.run_step()
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
