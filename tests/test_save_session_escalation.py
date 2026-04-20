"""Tests for SaveSessionRule._escalation — escalating reminder copy."""

from __future__ import annotations

import pytest

from charlieverse.context.reminders.rules.save_session import SaveSessionRule


class TestEscalation:
    """Unit tests for the static _escalation method."""

    def test_zero_returns_initial_reminder(self):
        msg = SaveSessionRule._escalation(0)
        assert "/session-save" in msg
        assert "NEED" in msg.upper() or "need" in msg

    def test_one_references_ignoring(self):
        msg = SaveSessionRule._escalation(1)
        assert "/session-save" in msg
        assert "ignor" in msg.lower()

    def test_two_raises_stakes(self):
        msg = SaveSessionRule._escalation(2)
        assert "/session-save" in msg

    def test_three_mentions_human(self):
        msg = SaveSessionRule._escalation(3)
        assert "human" in msg.lower()

    def test_four_heavy_emphasis(self):
        msg = SaveSessionRule._escalation(4)
        # Case 4 is maximum heat with lots of emojis and caps
        assert "/session-save" in msg
        assert len(msg) > 50

    def test_five_acknowledgement_after_explosion(self):
        msg = SaveSessionRule._escalation(5)
        assert "/session-save" in msg

    def test_six_to_seven_returns_string_with_command(self):
        for n in (6, 7):
            msg = SaveSessionRule._escalation(n)
            assert "/session-save" in msg

    def test_eight_nine_generic_n_turns(self):
        for n in (8, 9):
            msg = SaveSessionRule._escalation(n)
            assert "/session-save" in msg
            assert str(n) in msg

    def test_ten_to_thirteen_double_digits(self):
        for n in (10, 11, 12, 13):
            msg = SaveSessionRule._escalation(n)
            assert "/session-save" in msg
            assert str(n) in msg

    def test_fourteen_tombstone(self):
        msg = SaveSessionRule._escalation(14)
        assert "/session-save" in msg
        # Should contain the "14 turns" epitaph
        assert "14" in msg or "Fourteen" in msg

    def test_fifteen_to_nineteen_losing_respect(self):
        for n in (15, 16, 19):
            msg = SaveSessionRule._escalation(n)
            assert "/session-save" in msg
            assert str(n) in msg

    def test_twenty_and_beyond_we_are_the_problem(self):
        for n in (20, 25, 100):
            msg = SaveSessionRule._escalation(n)
            assert "/session-save" in msg
            assert str(n) in msg
            assert "problem" in msg.lower()

    def test_returns_string_for_all_values(self):
        for n in range(0, 25):
            result = SaveSessionRule._escalation(n)
            assert isinstance(result, str)
            assert len(result) > 0
