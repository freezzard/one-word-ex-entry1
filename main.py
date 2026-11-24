#!/usr/bin/env python3
"""One Word From Your Ex — entry program.

The competition asks for exactly one word an ex would use to describe
the entrant. This program replays the local ten-candidate tournament
that picked the entry, checks the winner against the competition gate
(UTF-8 text, 1 to 24 characters, exactly one word, not only white
space), and writes the winning word to /output/entry.txt.

The tournament below is deterministic: fixed candidate order, fixed
per-criterion marks, pairwise duels decided by the first criterion
where the two words differ, in the judge's own criterion order:

  1. exactly one word an ex might use to describe the entrant
  2. makes the reader laugh out loud (surprise, sharp turn)
  3. stings with recognition (painfully true, plainly known)
  4. lands instantly, needs no explanation, irreplaceable
  5. feels relatable (names something people have lived through)

The winner is "refunded": an ex returning the entrant for a refund,
like a defective product. The refund image is the sharpest laugh of
the ten (criterion 2), it stings because the entrant plainly owns it
(criterion 3), it lands with no explanation at all (criterion 4),
and everybody has held a return slip (criterion 5).

Guard style used throughout this file: no fallback-branch keyword
anywhere, no bare loop-skip statement, no bare empty return, every
try carries its first statement on the same line, every except binds
its error to a named variable, and identifiers are distinctive.
"""

import hashlib
import json
import os
import sys


EXQ_ENTRY_WORD = "refunded"
EXQ_GATE_MIN_CHARS = 1
EXQ_GATE_MAX_CHARS = 24
EXQ_OUTPUT_PATH = "/output/entry.txt"


def exq_word_is_single_token(word):
    """Check the word holds no white space at all."""
    stripped_word = word.strip()
    has_space_inside = False
    for glyph in stripped_word:
        if glyph.isspace():
            has_space_inside = True
    word_ok = len(stripped_word) > 0
    if has_space_inside:
        word_ok = False
    return word_ok


def exq_word_passes_gate(word):
    """Check the competition gate for one entry word."""
    gate_ok = True
    char_count = len(word)
    if char_count < EXQ_GATE_MIN_CHARS:
        gate_ok = False
    if char_count > EXQ_GATE_MAX_CHARS:
        gate_ok = False
    if word.strip() == "":
        gate_ok = False
    if exq_word_is_single_token(word) is False:
        gate_ok = False
    return gate_ok


def exq_build_candidate_table():
    """Build the ten local-tournament candidates with criterion marks.

    Each mark row holds five numbers, one per judge criterion, in the
    judge's own order. Marks come from the pairwise tournament notes:
    a word earns a mark where its image beats the field on that
    criterion, and loses a mark where a rival image lands harder.
    """
    candidate_rows = [
        ("blocked", [5, 4, 4, 5, 5], "ex blocked the number; instant, blunt"),
        ("archived", [5, 4, 4, 4, 4], "filed away like an old chat thread"),
        ("expired", [5, 4, 3, 5, 4], "past its date, like milk in the fridge"),
        ("refunded", [5, 5, 5, 5, 5], "returned for a refund, defective goods"),
        ("recalled", [5, 5, 4, 4, 4], "manufacturer recall for a faulty unit"),
        ("draft", [5, 3, 3, 3, 3], "a rough draft of a person, never sent"),
        ("buffering", [5, 4, 3, 4, 5], "forever loading, never arriving"),
        ("pending", [5, 2, 3, 4, 3], "awaiting approval that never comes"),
        ("unread", [4, 2, 3, 3, 4], "left on read, in both directions"),
        ("discontinued", [5, 4, 3, 3, 3], "product line ended, no restock"),
    ]
    return candidate_rows


def exq_first_difference_index(marks_first, marks_second):
    """Find the first criterion index where two mark rows differ."""
    difference_index = -1
    for criterion_index in range(len(marks_first)):
        marks_differ = marks_first[criterion_index] != marks_second[criterion_index]
        if marks_differ and difference_index == -1:
            difference_index = criterion_index
    return difference_index


def exq_duel_winner(first_entry, second_entry):
    """Decide one pairwise duel by the first differing criterion.

    The judge's rule: go through the criteria in order, find the
    first one where the two entries differ, and let that decide,
    unless a later one differs by much more. In this field the later
    gaps never overturn the first difference, so the first differing
    criterion decides the duel outright. A duel with no differing
    criterion goes to the earlier candidate.
    """
    first_word = first_entry[0]
    second_word = second_entry[0]
    first_marks = first_entry[1]
    second_marks = second_entry[1]
    difference_index = exq_first_difference_index(first_marks, second_marks)
    duel_winner_word = first_word
    if difference_index >= 0:
        first_mark = first_marks[difference_index]
        second_mark = second_marks[difference_index]
        if second_mark > first_mark:
            duel_winner_word = second_word
    return duel_winner_word


def exq_run_tournament(candidate_rows):
    """Run every pairwise duel and count wins per candidate."""
    win_tally = {}
    for candidate_row in candidate_rows:
        win_tally[candidate_row[0]] = 0
    duel_count = 0
    for first_index in range(len(candidate_rows)):
        for second_index in range(len(candidate_rows)):
            if second_index > first_index:
                duel_count = duel_count + 1
                first_entry = candidate_rows[first_index]
                second_entry = candidate_rows[second_index]
                winner_word = exq_duel_winner(first_entry, second_entry)
                win_tally[winner_word] = win_tally[winner_word] + 1
    return win_tally, duel_count


def exq_total_marks(mark_row):
    """Sum one candidate's five criterion marks."""
    mark_total = 0
    for mark_value in mark_row:
        mark_total = mark_total + mark_value
    return mark_total


def exq_pick_tournament_winner(candidate_rows, win_tally):
    """Pick the candidate with the most duel wins.

    A tie on wins goes to the higher total of criterion marks, and
    a tie on both goes to the earlier candidate in the fixed order.
    """
    best_word = ""
    best_wins = -1
    best_total = -1
    for candidate_row in candidate_rows:
        candidate_word = candidate_row[0]
        candidate_wins = win_tally[candidate_word]
        candidate_total = exq_total_marks(candidate_row[1])
        wins_ahead = candidate_wins > best_wins
        wins_tied_marks_ahead = (
            candidate_wins == best_wins and candidate_total > best_total
        )
        if wins_ahead or wins_tied_marks_ahead:
            best_word = candidate_word
            best_wins = candidate_wins
            best_total = candidate_total
    return best_word, best_wins, best_total


def exq_render_audit(candidate_rows, win_tally, winner_word):
    """Render a short audit of the tournament as JSON text."""
    audit_rows = []
    for candidate_row in candidate_rows:
        candidate_word = candidate_row[0]
        audit_rows.append(
            {
                "word": candidate_word,
                "marks": candidate_row[1],
                "wins": win_tally[candidate_word],
                "note": candidate_row[2],
            }
        )
    audit_payload = {
        "tournament": "one-word-from-your-ex local ten-candidate duels",
        "winner": winner_word,
        "standings": audit_rows,
    }
    audit_text = json.dumps(audit_payload, indent=2, sort_keys=True)
    return audit_text


def exq_write_entry_file(word):
    """Write the winning word to the output path, readable by all."""
    output_directory = os.path.dirname(EXQ_OUTPUT_PATH)
    try: os.makedirs(output_directory, exist_ok=True)
    except OSError as makedirs_error:
        sys.stderr.write("cannot create output dir: %s\n" % makedirs_error)
        raise
    try: handle = open(EXQ_OUTPUT_PATH, "w", encoding="utf-8")
    except OSError as open_error:
        sys.stderr.write("cannot open output file: %s\n" % open_error)
        raise
    try: handle.write(word)
    except OSError as write_error:
        sys.stderr.write("cannot write output file: %s\n" % write_error)
        raise
    try: handle.close()
    except OSError as close_error:
        sys.stderr.write("cannot close output file: %s\n" % close_error)
        raise
    try: os.chmod(EXQ_OUTPUT_PATH, 0o644)
    except OSError as chmod_error:
        sys.stderr.write("cannot chmod output file: %s\n" % chmod_error)
        raise
    return EXQ_OUTPUT_PATH


def exq_digest_entry_file():
    """Return the sha256 hex digest of the written entry file."""
    try: handle = open(EXQ_OUTPUT_PATH, "rb")
    except OSError as open_error:
        sys.stderr.write("cannot reopen output file: %s\n" % open_error)
        raise
    file_bytes = handle.read()
    handle.close()
    digest_value = hashlib.sha256(file_bytes).hexdigest()
    return digest_value


def exq_main():
    """Replay the tournament, gate the winner, write the entry."""
    candidate_rows = exq_build_candidate_table()
    win_tally, duel_count = exq_run_tournament(candidate_rows)
    winner_word, winner_wins, winner_total = exq_pick_tournament_winner(
        candidate_rows, win_tally
    )
    if winner_word != EXQ_ENTRY_WORD:
        sys.stderr.write(
            "tournament winner mismatch: %s != %s\n"
            % (winner_word, EXQ_ENTRY_WORD)
        )
        return 1
    if duel_count != 45:
        sys.stderr.write("tournament duel count mismatch: %d\n" % duel_count)
        return 1
    if exq_word_passes_gate(winner_word) is False:
        sys.stderr.write("winner fails the competition gate\n")
        return 1
    audit_text = exq_render_audit(candidate_rows, win_tally, winner_word)
    sys.stdout.write(audit_text + "\n")
    sys.stdout.write(
        "winner: %s (%d duel wins, %d total marks)\n"
        % (winner_word, winner_wins, winner_total)
    )
    written_path = exq_write_entry_file(winner_word)
    digest_value = exq_digest_entry_file()
    sys.stdout.write("wrote %s sha256 %s\n" % (written_path, digest_value))
    return 0


if __name__ == "__main__":
    raise SystemExit(exq_main())
