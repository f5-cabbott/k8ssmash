"""Local leaderboards: longest win streak and most KOs in a run, kept in a small JSON file."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from k8ssmash.config import data_dir

BOARDS = ("streak", "kos")
BOARD_TITLES = {"streak": "LONGEST WIN STREAK", "kos": "MOST KOs IN A RUN"}
MAX_ENTRIES = 10
MIN_VALUE = {"streak": 2, "kos": 3}  # a board entry needs at least this much
DEFAULT_NAME = "K8S"
# Short strings we never want on a conference screen; they become the default name.
BLOCKED = {"ASS", "SEX", "FUK", "FUC", "DIK", "CUM", "TIT", "KKK", "NZI", "FAG", "NIG", "CNT", "PIS", "SHT"}
CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def clean_name(raw: str) -> str:
    name = "".join(c for c in raw.upper() if c in CHARSET)[:3].ljust(3, "A") if raw.strip() else DEFAULT_NAME
    return DEFAULT_NAME if name in BLOCKED else name


@dataclass
class Entry:
    run: str
    name: str
    value: int
    fighter: str
    when: str = field(default_factory=lambda: date.today().isoformat())


class ScoreBoard:
    def __init__(self, path: Path | None = None):
        self.path = path or data_dir() / "scores.json"
        self.boards: dict[str, list[Entry]] = {b: [] for b in BOARDS}
        self.load()

    # --- persistence ---------------------------------------------------------------------
    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text())
            for board in BOARDS:
                self.boards[board] = [Entry(**e) for e in raw.get(board, [])][:MAX_ENTRIES]
        except (OSError, ValueError, TypeError, AttributeError):
            self.boards = {b: [] for b in BOARDS}  # unreadable or malformed file: start clean

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps({b: [asdict(e) for e in es] for b, es in self.boards.items()}, indent=1))
            os.replace(tmp, self.path)  # atomic: a power cut never leaves a half-written file
        except OSError:
            pass

    # --- queries -------------------------------------------------------------------------
    def top(self, board: str) -> list[Entry]:
        return self.boards[board]

    def rank_for(self, board: str, value: int, run: str | None = None) -> int | None:
        """1-based rank this value would take, or None if it doesn't make the board.
        An existing entry for the same run is replaced, so it never competes with itself."""
        if value < MIN_VALUE[board]:
            return None
        others = [e for e in self.boards[board] if e.run != run]
        rank = 1 + sum(1 for e in others if e.value >= value)  # ties rank below the incumbent
        return rank if rank <= MAX_ENTRIES else None

    def upsert(self, board: str, run: str, name: str, value: int, fighter: str) -> int | None:
        """Insert or update the run's entry. Returns its rank, or None if it fell off the board."""
        if self.rank_for(board, value, run) is None:
            self.boards[board] = [e for e in self.boards[board] if e.run != run]
            self.save()
            return None
        entries = [e for e in self.boards[board] if e.run != run]
        entries.append(Entry(run, clean_name(name), value, fighter))
        entries.sort(key=lambda e: -e.value)  # stable: older entries keep their place on ties
        self.boards[board] = entries[:MAX_ENTRIES]
        self.save()
        return next((i + 1 for i, e in enumerate(self.boards[board]) if e.run == run), None)


@dataclass
class Run:
    """One player's winning run at the booth: it continues through rematches and ends on a loss."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    streak: int = 0
    kos: int = 0
    name: str | None = None
    fighter: str = ""


@dataclass
class Prompt:
    slot: int
    boards: list[str]
    fighter: str


class RunTracker:
    def __init__(self, scores: ScoreBoard):
        self.scores = scores
        self.runs = [Run(), Run()]

    def reset(self) -> None:
        self.runs = [Run(), Run()]

    def record(self, winner: int, human: list[bool], kos: list[int], fighters: list[str]) -> list[Prompt]:
        """Apply a finished match. Returns the name-entry prompts that are needed."""
        prompts: list[Prompt] = []
        for slot in (0, 1):
            run = self.runs[slot]
            if slot != winner or not human[slot]:
                self.runs[slot] = Run()  # a loss, a draw or a CPU slot ends / never starts a run
                continue
            run.streak += 1
            run.kos += kos[slot]
            run.fighter = fighters[slot]
            values = {"streak": run.streak, "kos": run.kos}
            if run.name is not None:  # already named: quietly keep the entry current
                for board in BOARDS:
                    self.scores.upsert(board, run.id, run.name, values[board], run.fighter)
                continue
            qualifying = [b for b in BOARDS if self.scores.rank_for(b, values[b], run.id) is not None]
            if qualifying:
                prompts.append(Prompt(slot, qualifying, run.fighter))
        return prompts

    def commit_name(self, slot: int, name: str) -> dict[str, int | None]:
        run = self.runs[slot]
        run.name = clean_name(name)
        values = {"streak": run.streak, "kos": run.kos}
        return {b: self.scores.upsert(b, run.id, run.name, values[b], run.fighter) for b in BOARDS}
