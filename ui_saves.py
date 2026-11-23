"""Persistent save-slot manager storing up to 3 most recent unfinished matches."""

import json
import os
import time
import uuid

from texas_holdem import TexasHoldemSession


SAVES_FILENAME = "saved_matches.json"
MAX_SAVED_MATCHES = 3


def is_session_finished(session):
    """Return True if the match has concluded (human busted or all AI busted)."""
    if session is None or session.game is None:
        return True
    if session.phase == "match_over":
        return True
    if session.phase == "hand_over":
        human_alive = session.game.players[0].chips > 0
        any_ai_alive = any(p.chips > 0 for p in session.game.players[1:])
        if not human_alive or not any_ai_alive:
            return True
    return False


class MatchSaveManager:
    """Manages up to 3 unfinished Texas Hold'em match saves on disk (or in memory)."""

    def __init__(self, app_dir, max_slots=MAX_SAVED_MATCHES, persist=True):
        self.app_dir = os.path.abspath(app_dir)
        self.file_path = os.path.join(self.app_dir, SAVES_FILENAME)
        self.max_slots = max_slots
        self.persist = persist
        self._saves = []
        if self.persist:
            self._load_from_disk()

    def _load_from_disk(self):
        if not os.path.isfile(self.file_path):
            self._saves = []
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            raw = payload.get("saves", []) if isinstance(payload, dict) else []
            valid = []
            for entry in raw:
                if isinstance(entry, dict) and entry.get("id") and isinstance(entry.get("session_state"), dict):
                    valid.append(entry)
            valid.sort(key=lambda item: float(item.get("updated_ts", 0.0)), reverse=True)
            self._saves = valid[: self.max_slots]
        except (OSError, ValueError, TypeError):
            self._saves = []

    def _write_to_disk(self):
        if not self.persist:
            return
        os.makedirs(self.app_dir, exist_ok=True)
        tmp_path = self.file_path + ".tmp"
        payload = {"version": 1, "saves": self._saves[: self.max_slots]}
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.file_path)
        except OSError:
            pass

    def list_saves(self):
        """Return shallow copies of up to max_slots unfinished match entries, newest first."""
        return [dict(item) for item in self._saves[: self.max_slots]]

    def count(self):
        return len(self._saves)

    def has_saves(self):
        return bool(self._saves)

    def save_match(self, slot_id, session):
        """Insert or update an unfinished match save. Removes finished matches automatically."""
        if session is None:
            return None

        if is_session_finished(session):
            if slot_id:
                self.delete_save(slot_id)
            return None

        save_id = slot_id or uuid.uuid4().hex[:12]
        now_ts = time.time()
        entry = {
            "id": save_id,
            "updated_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts)),
            "updated_ts": now_ts,
            "hand_number": int(session.hand_number),
            "street": session.street,
            "phase": session.phase,
            "human_chips": int(session.game.players[0].chips),
            "starting_chips": int(session.starting_chips),
            "small_blind": int(session.small_blind),
            "big_blind": int(session.big_blind),
            "num_players": len(session.game.players),
            "alive_players": sum(1 for elim in session.game.eliminated if not elim),
            "pot": int(session.game.pot),
            "opponents": [
                {
                    "name": p.name,
                    "tier": getattr(p, "tier", "Pro"),
                    "chips": int(p.chips),
                    "eliminated": bool(session.game.eliminated[idx]),
                }
                for idx, p in enumerate(session.game.players[1:], start=1)
            ],
            "session_state": session.to_dict(),
        }

        self._saves = [item for item in self._saves if item.get("id") != save_id]
        self._saves.insert(0, entry)
        self._saves = self._saves[: self.max_slots]
        self._write_to_disk()
        return save_id

    def delete_save(self, slot_id):
        """Remove a saved match by ID."""
        before = len(self._saves)
        self._saves = [item for item in self._saves if item.get("id") != slot_id]
        if len(self._saves) != before:
            self._write_to_disk()
            return True
        return False

    def load_session(self, slot_id):
        """Restore and return a TexasHoldemSession for the given save ID, or None."""
        for item in self._saves:
            if item.get("id") == slot_id:
                try:
                    return TexasHoldemSession.from_dict(item["session_state"])
                except (KeyError, ValueError, TypeError):
                    return None
        return None
