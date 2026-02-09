"""
test_local.py — Test the full game flow WITHOUT email
======================================================

Simulates all 4 callback triggers in sequence using
runner.simulate_incoming(). No email server needed.

Run with:  python test_local.py
"""

import sys
import os
import json
import logging

# Add parent to path so we can import q21_referee
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from q21_referee import RefereeRunner, RefereeAI


# ── A simple test AI ─────────────────────────────────────────

class TestAI(RefereeAI):

    def get_warmup_question(self, ctx):
        dynamic = ctx["dynamic"]
        print(f"    [Callback 1] get_warmup_question(round={dynamic['round_number']})")
        return {"warmup_question": "What is 2 + 2?"}

    def get_round_start_info(self, ctx):
        dynamic = ctx["dynamic"]
        p1_ans = dynamic["player_a"]["warmup_answer"]
        p2_ans = dynamic["player_b"]["warmup_answer"]
        print(f"    [Callback 2] get_round_start_info("
              f"p1 answered '{p1_ans}', p2 answered '{p2_ans}')")
        return {
            "book_name": "The Great Gatsby",
            "book_hint": "A novel about the American Dream in the 1920s Jazz Age",
            "association_word": "color",
        }

    def get_answers(self, ctx):
        dynamic = ctx["dynamic"]
        n = len(dynamic["questions"])
        print(f"    [Callback 3] get_answers("
              f"player={dynamic['player_id']}, {n} questions)")
        answers = [{"question_number": q["question_number"], "answer": "A"}
                   for q in dynamic["questions"]]
        return {"answers": answers}

    def get_score_feedback(self, ctx):
        dynamic = ctx["dynamic"]
        guess = dynamic["player_guess"]
        print(f"    [Callback 4] get_score_feedback("
              f"player={dynamic['player_id']}, "
              f"guess='{guess['opening_sentence'][:40]}...')")
        return {
            "league_points": 2,
            "private_score": 72.5,
            "breakdown": {
                "opening_sentence_score": 80.0,
                "sentence_justification_score": 70.0,
                "associative_word_score": 60.0,
                "word_justification_score": 80.0,
            },
            "feedback": {
                "opening_sentence": (
                    "Good attempt at capturing the opening of the novel. "
                    "The narrative voice of Nick Carraway is introspective and "
                    "reflective, looking back on events that shaped his life. "
                    "Your understanding of the themes of wealth and dreams "
                    "is evident in your justification. The 1920s setting and "
                    "social dynamics are central to the story. Consider the "
                    "specific words Fitzgerald chose to establish the narrator's "
                    "vulnerability and the paternal advice that frames the "
                    "entire narrative. The exact phrasing matters for capturing "
                    "the literary significance of this famous opening line. "
                    "Your effort shows engagement with the text's deeper meaning. "
                    "The opening sentence of The Great Gatsby is widely considered "
                    "one of the finest in American literature, establishing both "
                    "the narrator's character and the moral framework for the "
                    "entire story. Nick's father advises him to reserve judgment "
                    "on others, which becomes ironic given his harsh judgments "
                    "throughout the narrative. The vulnerability he mentions "
                    "sets up the reader to trust his perspective while also "
                    "hinting at the moral complexity to come in the tale of "
                    "Gatsby's rise and fall in the Jazz Age."
                ),
                "associative_word": (
                    "Reasonable choice for the color association. The green "
                    "light is indeed one of the most iconic symbols in American "
                    "literature, representing Gatsby's hopes and dreams for the "
                    "future. Fitzgerald's use of color symbolism extends throughout "
                    "the novel, with green representing longing and aspiration. "
                    "The light at the end of Daisy's dock serves as a constant "
                    "reminder of the unattainable nature of Gatsby's dream. Your "
                    "reasoning about the symbolic significance demonstrates "
                    "understanding of the text's layered meanings and thematic "
                    "richness. Consider how other colors contribute to the "
                    "overall symbolic landscape of the novel. Gold and yellow "
                    "represent wealth and corruption, white suggests false purity, "
                    "and grey characterizes the moral wasteland between the eggs. "
                    "The green light particularly resonates because it connects "
                    "to broader American themes of hope and reinvention. Gatsby's "
                    "reaching toward the light mirrors the nation's eternal "
                    "optimism about the future, even as the novel critiques the "
                    "hollowness of that dream when pursued through materialism "
                    "and illusion rather than genuine human connection."
                ),
            }
        }


# ── Config (email not used in simulation) ────────────────────

config = {
    "referee_email": "referee@test.com",
    "referee_password": "not-needed",
    "referee_id": "R001",
    "league_manager_email": "server@test.com",
    "league_id": "LEAGUE001",
    "season_id": "SEASON_2026_Q1",
    "game_id": "0101001",
    "match_id": "R1M1",
    "player1_email": "alice@test.com",
    "player1_id": "P001",
    "player2_email": "bob@test.com",
    "player2_id": "P002",
    "actual_opening_sentence": "In my younger and more vulnerable years my father gave me some advice.",
    "actual_associative_word": "green",
}


# ── Build helper messages ────────────────────────────────────

def league_msg(msg_type, sender_email, sender_role, recipient, payload, **ctx):
    env = {
        "protocol": "league.v2",
        "message_type": msg_type,
        "message_id": f"test-{msg_type.lower()[:20]}",
        "timestamp": "2026-02-17T19:00:00.000000+00:00",
        "sender": {"email": sender_email, "role": sender_role, "logical_id": None},
        "recipient_id": recipient,
        "league_id": "LEAGUE001",
        "season_id": "SEASON_2026_Q1",
        "payload": payload,
    }
    env.update(ctx)
    return env


def q21_msg(msg_type, sender_email, sender_role, sender_lid, recipient,
            game_id, payload, **ctx):
    env = {
        "protocol": "Q21G.v1",
        "message_type": msg_type,
        "message_id": f"test-{msg_type.lower()[:20]}",
        "timestamp": "2026-02-17T19:05:00.000000+00:00",
        "sender": {"email": sender_email, "role": sender_role, "logical_id": sender_lid},
        "recipient_id": recipient,
        "game_id": game_id,
        "payload": payload,
    }
    env.update(ctx)
    return env


# ── Run the full flow ────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.WARNING)  # quiet for test output

    runner = RefereeRunner(config=config, ai=TestAI())

    print("=" * 70)
    print("  Full Game Flow Simulation (no email)")
    print("=" * 70)

    # ── Step 1: BROADCAST_NEW_LEAGUE_ROUND → triggers get_warmup_question()
    print("\n Step 1: BROADCAST_NEW_LEAGUE_ROUND arrives")
    out = runner.simulate_incoming(league_msg(
        "BROADCAST_NEW_LEAGUE_ROUND", "server@test.com", "LEAGUEMANAGER",
        "BROADCAST",
        {"broadcast_id": "bc-round-001", "round_id": "ROUND_1",
         "round_number": 1, "message_text": "Round 1!"},
    ))
    print(f"    Package sends {len(out)} message(s):")
    for env, subj, to in out:
        print(f"       -> {env['message_type']} to {to}")
    assert len(out) == 2, "Should send Q21WARMUPCALL to both players"
    assert all(e["message_type"] == "Q21WARMUPCALL" for e, _, _ in out)

    # ── Step 2a: Q21WARMUPRESPONSE from player 1
    print("\n Step 2a: Q21WARMUPRESPONSE from Player 1 (alice)")
    out = runner.simulate_incoming(q21_msg(
        "Q21WARMUPRESPONSE", "alice@test.com", "PLAYER", "P001",
        "R001", "0101001",
        {"match_id": "R1M1", "answer": "4", "auth_token": "tok_test"},
        correlation_id="test-q21warmupcall",
    ))
    print(f"    Package sends {len(out)} message(s) (waiting for player 2)")
    assert len(out) == 0, "Should wait for both players"

    # ── Step 2b: Q21WARMUPRESPONSE from player 2 → triggers get_round_start_info()
    print("\n Step 2b: Q21WARMUPRESPONSE from Player 2 (bob)")
    out = runner.simulate_incoming(q21_msg(
        "Q21WARMUPRESPONSE", "bob@test.com", "PLAYER", "P002",
        "R001", "0101001",
        {"match_id": "R1M1", "answer": "4", "auth_token": "tok_test"},
        correlation_id="test-q21warmupcall",
    ))
    print(f"    Package sends {len(out)} message(s):")
    for env, subj, to in out:
        print(f"       -> {env['message_type']} to {to}")
    assert len(out) == 2, "Should send Q21ROUNDSTART to both players"
    assert all(e["message_type"] == "Q21ROUNDSTART" for e, _, _ in out)

    # ── Step 3a: Q21QUESTIONSBATCH from player 1 → triggers get_answers()
    print("\n Step 3a: Q21QUESTIONSBATCH from Player 1 (alice)")
    questions = [
        {"question_number": i,
         "question_text": f"Question {i}?",
         "options": {"A": "a", "B": "b", "C": "c", "D": "d"}}
        for i in range(1, 21)
    ]
    out = runner.simulate_incoming(q21_msg(
        "Q21QUESTIONSBATCH", "alice@test.com", "PLAYER", "P001",
        "R001", "0101001",
        {"match_id": "R1M1", "auth_token": "tok_test",
         "questions": questions, "total_questions": 20},
        correlation_id="test-q21roundstart",
    ))
    print(f"    Package sends {len(out)} message(s):")
    for env, subj, to in out:
        print(f"       -> {env['message_type']} to {to} "
              f"({len(env['payload']['answers'])} answers)")
    assert len(out) == 1 and out[0][0]["message_type"] == "Q21ANSWERSBATCH"

    # ── Step 3b: Q21QUESTIONSBATCH from player 2
    print("\n Step 3b: Q21QUESTIONSBATCH from Player 2 (bob)")
    out = runner.simulate_incoming(q21_msg(
        "Q21QUESTIONSBATCH", "bob@test.com", "PLAYER", "P002",
        "R001", "0101001",
        {"match_id": "R1M1", "auth_token": "tok_test",
         "questions": questions, "total_questions": 20},
        correlation_id="test-q21roundstart",
    ))
    print(f"    Package sends {len(out)} message(s):")
    for env, subj, to in out:
        print(f"       -> {env['message_type']} to {to}")
    assert len(out) == 1 and out[0][0]["message_type"] == "Q21ANSWERSBATCH"

    # ── Step 4a: Q21GUESSSUBMISSION from player 1 → triggers get_score_feedback()
    print("\n Step 4a: Q21GUESSSUBMISSION from Player 1 (alice)")
    out = runner.simulate_incoming(q21_msg(
        "Q21GUESSSUBMISSION", "alice@test.com", "PLAYER", "P001",
        "R001", "0101001",
        {"match_id": "R1M1", "auth_token": "tok_test",
         "opening_sentence": "In my younger and more vulnerable years...",
         "sentence_justification": " ".join(["word"] * 35),
         "associative_word": "green",
         "word_justification": " ".join(["word"] * 25),
         "confidence": 0.8},
        correlation_id="test-q21answersbatch",
    ))
    print(f"    Package sends {len(out)} message(s):")
    for env, subj, to in out:
        print(f"       -> {env['message_type']} to {to}")
    assert len(out) == 1, "Score feedback to player 1, still waiting for player 2"
    assert out[0][0]["message_type"] == "Q21SCOREFEEDBACK"

    # ── Step 4b: Q21GUESSSUBMISSION from player 2 → score + MATCH_RESULT_REPORT
    print("\n Step 4b: Q21GUESSSUBMISSION from Player 2 (bob)")
    out = runner.simulate_incoming(q21_msg(
        "Q21GUESSSUBMISSION", "bob@test.com", "PLAYER", "P002",
        "R001", "0101001",
        {"match_id": "R1M1", "auth_token": "tok_test",
         "opening_sentence": "Call me Ishmael.",
         "sentence_justification": " ".join(["word"] * 35),
         "associative_word": "white",
         "word_justification": " ".join(["word"] * 25),
         "confidence": 0.4},
        correlation_id="test-q21answersbatch",
    ))
    print(f"    Package sends {len(out)} message(s):")
    for env, subj, to in out:
        print(f"       -> {env['message_type']} to {to}")
    assert len(out) == 2, "Score feedback to player 2 + MATCH_RESULT_REPORT to LM"
    types = {e["message_type"] for e, _, _ in out}
    assert "Q21SCOREFEEDBACK" in types
    assert "MATCH_RESULT_REPORT" in types

    # ── Summary
    print("\n" + "=" * 70)
    print("  Full game flow completed successfully!")
    print()
    print("  Callback execution order:")
    print("    1. get_warmup_question()   - triggered by BROADCAST_NEW_LEAGUE_ROUND")
    print("    2. get_round_start_info()  - triggered by both Q21WARMUPRESPONSEs")
    print("    3. get_answers() x 2       - triggered by each Q21QUESTIONSBATCH")
    print("    4. get_score_feedback() x 2 - triggered by each Q21GUESSSUBMISSION")
    print()
    print("  Messages sent by the package:")
    print("    Q21WARMUPCALL x 2       -> both players")
    print("    Q21ROUNDSTART x 2       -> both players")
    print("    Q21ANSWERSBATCH x 2     -> each player after their questions")
    print("    Q21SCOREFEEDBACK x 2    -> each player after their guess")
    print("    MATCH_RESULT_REPORT x 1 -> League Manager")
    print("=" * 70)


if __name__ == "__main__":
    main()
