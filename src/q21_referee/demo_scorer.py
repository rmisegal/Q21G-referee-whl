# Area: Shared
# PRD: docs/prd-rlgm.md
"""Scoring functions for DemoAI."""

from typing import Any, Dict


def calculate_scores(
    actual_sentence: str,
    actual_word: str,
    sentence_guess: str,
    sentence_just: str,
    word_guess: str,
    word_just: str,
) -> Dict[str, Any]:
    """Calculate all scores for a player's guess."""
    # Sentence similarity (simple word overlap)
    sentence_score = calculate_similarity(
        actual_sentence, sentence_guess
    )

    # Word match (exact match = 100, else 0)
    word_score = 100.0 if (
        actual_word.lower().strip() == word_guess.lower().strip()
    ) else 0.0

    # Justification scores (based on length and keywords)
    sentence_just_score = score_justification(sentence_just, 30, 50)
    word_just_score = score_justification(word_just, 20, 30)

    # Weighted private score
    private_score = (
        sentence_score * 0.50 +
        sentence_just_score * 0.20 +
        word_score * 0.20 +
        word_just_score * 0.10
    )
    private_score = round(private_score, 2)

    # League points
    if private_score >= 85:
        league_points = 3
    elif private_score >= 70:
        league_points = 2
    elif private_score >= 50:
        league_points = 1
    else:
        league_points = 0

    return {
        "league_points": league_points,
        "private_score": private_score,
        "breakdown": {
            "opening_sentence_score": round(sentence_score, 2),
            "sentence_justification_score": round(sentence_just_score, 2),
            "associative_word_score": round(word_score, 2),
            "word_justification_score": round(word_just_score, 2),
        },
        "feedback": generate_feedback(
            sentence_score, word_score, actual_word
        ),
    }


def calculate_similarity(actual: str, guess: str) -> float:
    """Calculate similarity between actual and guessed sentences."""
    if not actual or not guess:
        return 0.0

    actual_lower = actual.lower()
    guess_lower = guess.lower()

    if actual_lower == guess_lower:
        return 100.0

    # Word overlap (Jaccard similarity)
    actual_words = set(actual_lower.split())
    guess_words = set(guess_lower.split())

    if not actual_words:
        return 0.0

    intersection = actual_words & guess_words
    union = actual_words | guess_words

    if not union:
        return 0.0

    jaccard = len(intersection) / len(union)
    return round(jaccard * 100, 2)

def score_justification(
    text: str, min_words: int, max_words: int
) -> float:
    """Score a justification based on length and quality."""
    if not text:
        return 0.0

    words = text.split()
    word_count = len(words)

    # Base score from length
    if word_count < min_words:
        length_score = (word_count / min_words) * 50
    elif word_count <= max_words:
        length_score = 70.0
    else:
        length_score = 60.0  # Slight penalty for being too long

    # Bonus for reasoning keywords
    keywords = [
        "because", "therefore", "based on", "indicates",
        "suggests", "evidence", "reasoning", "theme",
    ]
    keyword_bonus = sum(
        5 for kw in keywords if kw in text.lower()
    )

    return min(100.0, length_score + keyword_bonus)


def generate_feedback(
    sentence_score: float, word_score: float, actual_word: str
) -> Dict[str, str]:
    """Generate feedback text based on scores."""
    if sentence_score >= 90:
        s_fb = ("Excellent match with the actual opening sentence! Your guess "
                "captured the essence and phrasing of the original text with "
                "remarkable accuracy. The reflective tone and narrative voice "
                "were perfectly identified.")
    elif sentence_score >= 70:
        s_fb = ("Good attempt at the opening sentence. You captured some key "
                "elements of the original, though the exact phrasing differs. "
                "Your understanding of the narrative style is evident.")
    elif sentence_score >= 50:
        s_fb = ("Your guess showed understanding of the book's themes but "
                "missed the specific opening structure. Consider the narrative "
                "voice and how the author establishes the story's perspective.")
    else:
        s_fb = ("The opening sentence was quite different from your guess. "
                "Review how classic novels often begin with character "
                "introduction or scene-setting that establishes tone.")
    if word_score >= 100:
        w_fb = (f"Correct! '{actual_word}' is the associative word. Your "
                "understanding of the book's symbolism is excellent.")
    else:
        w_fb = (f"The associative word was '{actual_word}'. While your choice "
                "showed thoughtful engagement with the text, the primary "
                "symbolic element was different.")
    return {"opening_sentence": s_fb, "associative_word": w_fb}
