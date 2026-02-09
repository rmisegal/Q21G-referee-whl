"""
my_ai.py — YOUR AI IMPLEMENTATION
===================================

This is the ONLY file you need to edit.

Implement the 4 methods below. Each method receives a context dict with:
- ctx["dynamic"]: Data from incoming messages (game_id, player info, etc.)
- ctx["service"]: Info about what LLM service to call

The package handles everything else: email polling, protocol messages,
game state tracking, validation, etc.

You can use any libraries you want (OpenAI, Anthropic, HuggingFace, etc.)
to implement your AI logic.
"""

from q21_referee import RefereeAI


class MyRefereeAI(RefereeAI):

    def get_warmup_question(self, ctx):
        """
        Called when a new round starts.
        Return a simple question to verify player connectivity.

        ctx["dynamic"] contains:
            season_id, round_number, round_id, game_id, match_id,
            referee_id, player_a_id, player_a_email, player_b_id, player_b_email

        ctx["service"] contains:
            name, description, required_output_fields, deadline_seconds
        """
        # ─── YOUR AI LOGIC HERE ───
        # Example: hardcoded question
        return {
            "warmup_question": "What is the capital of Israel?"
        }

        # ─── OR: use an LLM ───
        # response = openai.chat.completions.create(
        #     model="gpt-4",
        #     messages=[{"role": "user",
        #                "content": "Generate a simple trivia question"}]
        # )
        # return {"warmup_question": response.choices[0].message.content}

    def get_round_start_info(self, ctx):
        """
        Called after BOTH players responded to warmup.
        Choose a book, write a hint, and pick an association word.

        ctx["dynamic"] contains:
            season_id, round_number, round_id, game_id, match_id, referee_id,
            player_a: {id, email, warmup_answer},
            player_b: {id, email, warmup_answer}

        ctx["service"] contains:
            name, description, required_output_fields, deadline_seconds
        """
        # ─── YOUR AI LOGIC HERE ───
        return {
            "book_name": "The Great Gatsby",
            "book_hint": "A novel about the American Dream in the 1920s Jazz Age",
            "association_word": "color"
        }

        # ─── OR: pick from a curated list, use an LLM to generate hints ───

    def get_answers(self, ctx):
        """
        Called when a player submits their 20 questions.
        Answer each with A, B, C, D, or "Not Relevant".

        ctx["dynamic"] contains:
            season_id, round_number, round_id, game_id, match_id, referee_id,
            player_id, player_email,
            book_name, book_hint, association_word,
            questions (list of {question_number, question_text, options})

        ctx["service"] contains:
            name, description, required_output_fields, deadline_seconds
        """
        dynamic = ctx["dynamic"]
        questions = dynamic["questions"]

        # ─── YOUR AI LOGIC HERE ───
        answers = []
        for q in questions:
            # Example: simple logic — always answer "B"
            answers.append({
                "question_number": q["question_number"],
                "answer": "B"
            })

            # ─── OR: use an LLM to actually answer ───
            # prompt = f"""
            # Book: {dynamic['book_name']}
            # Hint: {dynamic['book_hint']}
            # Question: {q['question_text']}
            # Options: A={q['options']['A']}, B={q['options']['B']},
            #          C={q['options']['C']}, D={q['options']['D']}
            # Answer with just the letter (A/B/C/D) or "Not Relevant":
            # """
            # answer = call_llm(prompt)
            # answers.append({"question_number": q["question_number"],
            #                  "answer": answer})

        return {"answers": answers}

    def get_score_feedback(self, ctx):
        """
        Called when a player submits their final guess.
        Score their opening sentence guess and associative word guess.

        ctx["dynamic"] contains:
            season_id, round_number, round_id, game_id, match_id, referee_id,
            player_id, player_email,
            book_name, book_hint, association_word,
            actual_opening_sentence, actual_associative_word,
            player_guess: {
                opening_sentence, sentence_justification,
                associative_word, word_justification, confidence
            }

        ctx["service"] contains:
            name, description, required_output_fields, deadline_seconds
        """
        dynamic = ctx["dynamic"]
        guess = dynamic["player_guess"]

        # ─── YOUR AI LOGIC HERE ───

        # Example: simple scoring based on exact match
        correct_sentence = dynamic.get("actual_opening_sentence",
            "In my younger and more vulnerable years my father gave me some advice.")
        correct_word = dynamic.get("actual_associative_word", "green")

        # Score the opening sentence (50% weight)
        if guess["opening_sentence"].lower().strip() == correct_sentence.lower().strip():
            sentence_score = 100.0
        else:
            sentence_score = 30.0

        # Score the associative word (20% weight)
        if guess["associative_word"].lower().strip() == correct_word.lower():
            word_score = 100.0
        else:
            word_score = 20.0

        # Score justifications
        justification_score = 50.0  # placeholder
        word_just_score = 50.0      # placeholder

        # Calculate private score (weighted)
        private_score = (
            sentence_score * 0.50 +
            justification_score * 0.20 +
            word_score * 0.20 +
            word_just_score * 0.10
        )

        # Map to league points
        if private_score >= 75:
            league_points = 3
        elif private_score >= 50:
            league_points = 2
        elif private_score >= 25:
            league_points = 1
        else:
            league_points = 0

        return {
            "league_points": league_points,
            "private_score": round(private_score, 1),
            "breakdown": {
                "opening_sentence_score": sentence_score,
                "sentence_justification_score": justification_score,
                "associative_word_score": word_score,
                "word_justification_score": word_just_score,
            },
            "feedback": {
                "opening_sentence": (
                    "Your guess for the opening sentence was evaluated against "
                    "the actual first line of The Great Gatsby. The correct opening "
                    "is a reflective first-person narration by Nick Carraway about "
                    "advice his father gave him. Your approach showed understanding "
                    "of the novel's introspective tone and narrative voice. The "
                    "justification demonstrated awareness of the 1920s setting and "
                    "themes of wealth and disillusionment that pervade the story. "
                    "A stronger answer would have captured the exact phrasing of "
                    "the vulnerability and advice mentioned in the opening line. "
                    "The narrative structure of the novel relies heavily on this "
                    "reflective quality established from the very first sentence. "
                    "Consider how the narrator's self-awareness shapes the entire "
                    "story and its themes of memory and judgment."
                ),
                "associative_word": (
                    "The association domain was 'color' and the expected word was "
                    "'green', representing the iconic green light at the end of "
                    "Daisy's dock. This symbol is central to the novel's themes "
                    "of hope, longing, and the American Dream. Your word choice "
                    "was evaluated for its connection to the book's core symbolism. "
                    "The green light appears throughout the novel as Gatsby's "
                    "unreachable aspiration, making it the strongest color "
                    "association for this particular work of literature. "
                    "Fitzgerald uses color symbolism extensively, with green "
                    "representing both envy and hope, while other colors like "
                    "gold and white carry their own thematic weight throughout "
                    "the narrative of wealth and corruption in the Jazz Age."
                ),
            }
        }
