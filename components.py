"""
Core game logic for Minesweeper.

This module contains pure domain logic without any pygame or pixel-level
concerns. It defines:
- CellState: the state of a single cell
- Cell: a cell positioned by (col,row) with an attached CellState
- Board: grid management, mine placement, adjacency computation, reveal/flag

The Board exposes imperative methods that the presentation layer (run.py)
can call in response to user inputs, and does not know anything about
rendering, timing, or input devices.
"""

import random
from typing import List, Tuple


class CellState:
    """Mutable state of a single cell.

    Attributes:
        is_mine: Whether this cell contains a mine.
        is_revealed: Whether the cell has been revealed to the player.
        is_flagged: Whether the player flagged this cell as a mine.
        adjacent: Number of adjacent mines in the 8 neighboring cells.
    """

    def __init__(self, is_mine: bool = False, is_revealed: bool = False, is_flagged: bool = False, adjacent: int = 0):
        self.is_mine = is_mine
        self.is_revealed = is_revealed
        self.is_flagged = is_flagged
        self.adjacent = adjacent


class Cell:
    """Logical cell positioned on the board by column and row."""

    def __init__(self, col: int, row: int):
        self.col = col
        self.row = row
        self.state = CellState()


class Board:
    """Minesweeper board state and rules.

    Responsibilities:
    - Generate and place mines with first-click safety
    - Compute adjacency counts for every cell
    - Reveal cells (iterative flood fill when adjacent == 0)
    - Toggle flags, check win/lose conditions
    """

    def __init__(self, cols: int, rows: int, mines: int):
        self.cols = cols
        self.rows = rows
        self.num_mines = mines
        self.cells: List[Cell] = [Cell(c, r) for r in range(rows) for c in range(cols)]
        self._mines_placed = False
        self.revealed_count = 0
        self.game_over = False
        self.win = False
       

    def index(self, col: int, row: int) -> int:
        """Return the flat list index for (col,row)."""
        return row * self.cols + col

    def is_inbounds(self, col: int, row: int) -> bool:
        # TODO: Return True if (col,row) is inside the board bounds.
        return (0 <= col < self.cols) and (0 <= row < self.rows)


    def neighbors(self, col: int, row: int) -> List[Tuple[int, int]]:
        # TODO: Return list of valid neighboring coordinates around (col,row).
        deltas = [
             (-1, -1), (0, -1), (1, -1),
             (-1, 0),            (1, 0),
             (-1, 1),  (0, 1),  (1, 1),
        ]
        result = []
        for d_col, d_row in deltas:
            n_col, n_row = col + d_col, row + d_row
            # Corrected check and append logic
            if self.is_inbounds(n_col, n_row):
                result.append((n_col, n_row))
        return result


    def place_mines(self, safe_col: int, safe_row: int) -> None:
        # TODO: Place mines randomly, guaranteeing the first click and its neighbors are safe. And Compute adjacency counts
         all_positions = [(c, r) for r in range(self.rows) for c in range(self.cols)]
         forbidden = {(safe_col, safe_row)} | set(self.neighbors(safe_col, safe_row))
         pool = [p for p in all_positions if p not in forbidden]
         random.shuffle(pool)
         mine_positions = pool[:self.num_mines]
         for c, r in mine_positions:
            idx = self.index(c, r)
            self.cells[idx].state.is_mine = True
        # Compute adjacency counts
         for r in range(self.rows):
             for c in range(self.cols):
                 cell = self.cells[self.index(c, r)]
                
                 if not cell.state.is_mine:
                    mine_count = 0
                    for n_col, n_row in self.neighbors(c, r):
                        n_cell = self.cells[self.index(n_col, n_row)]
                        if n_cell.state.is_mine:
                            mine_count += 1
                    cell.state.adjacent = mine_count

         self._mines_placed = True


    def reveal(self, col: int, row: int) -> None:
        # TODO: Reveal a cell; if zero-adjacent, iteratively flood to neighbors.
        if not self.is_inbounds(col, row) or self.game_over or self.win:
             return
        if not self._mines_placed:
             self.place_mines(col, row)
        cell = self.cells[self.index(col, row)]
        if cell.state.is_revealed or cell.state.is_flagged:
            return
        if cell.state.is_mine:
            self.game_over = True
            self._reveal_all_mines()
            return
        queue = [(col, row)]
        visited = set()
        
        while queue:
            c, r = queue.pop(0)
            
            if (c, r) in visited:
                continue
            visited.add((c, r))
            
            current_cell = self.cells[self.index(c, r)]
            
            # 이미 공개되었거나 깃발이 있다면 이 셀을 건너뛰고 다음 셀로 이동
            if current_cell.state.is_revealed or current_cell.state.is_flagged:
                continue

            current_cell.state.is_revealed = True
            self.revealed_count += 1
            
            # 5. 플러드 필 (Adjacent == 0인 경우에만 이웃을 큐에 추가)
            if current_cell.state.adjacent == 0:
                for n_col, n_row in self.neighbors(c, r):
                    n_cell = self.cells[self.index(n_col, n_row)]
                    
                    # 지뢰가 아니고, 아직 공개되지 않은 셀만 큐에 추가
                    if not n_cell.state.is_mine and not n_cell.state.is_revealed:
                        queue.append((n_col, n_row))
         
        
        self._check_win()


    # ================== Issue #2 추가 ==================
    def reveal_around_if_flag_match(self, col: int, row: int) -> None:
        """
        [Issue #2]
        이미 열린 숫자 칸을 클릭했을 때,
        주변 깃발 개수가 숫자와 같으면
        깃발이 아닌 주변 칸을 모두 오픈한다.
        """
        cell = self.cells[self.index(col, row)]

        # 이미 열린 숫자 칸만 대상
        if not cell.state.is_revealed or cell.state.adjacent == 0:
            return

        neighbors = self.neighbors(col, row)

        # 주변 깃발 개수 계산
        flag_count = 0
        for n_col, n_row in neighbors:
            if self.cells[self.index(n_col, n_row)].state.is_flagged:
                flag_count += 1

        # 깃발 개수가 숫자와 다르면 아무 동작 안 함
        if flag_count != cell.state.adjacent:
            return

        # 깃발이 아닌 주변 칸을 모두 reveal
        for n_col, n_row in neighbors:
            neighbor_cell = self.cells[self.index(n_col, n_row)]
            if not neighbor_cell.state.is_flagged and not neighbor_cell.state.is_revealed:
                self.reveal(n_col, n_row)


    def toggle_flag(self, col: int, row: int) -> None:
        # TODO: Toggle a flag on a non-revealed cell.
        if not self.is_inbounds(col, row):
            return
        cell = self.cells[self.index(col,row)]
        if not cell.state.is_revealed :
            cell.state.is_flagged = not cell.state.is_flagged

    def flagged_count(self) -> int:
        # TODO: Return current number of flagged cells.
        count =0
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[self.index(c,r)]
                count += cell.state.is_flagged
        return count


    def _reveal_all_mines(self) -> None:
        """Reveal all mines; called on game over."""
        for cell in self.cells:
            if cell.state.is_mine:
                cell.state.is_revealed = True

    def _check_win(self) -> None:
        """Set win=True when all non-mine cells have been revealed."""
        total_cells = self.cols * self.rows
        if self.revealed_count == total_cells - self.num_mines and not self.game_over:
            self.win = True
            for cell in self.cells:
                if not cell.state.is_revealed and not cell.state.is_mine:
                    cell.state.is_revealed = True
