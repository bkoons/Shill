import re
import math
from typing import Dict, Any, Tuple

class ReadabilityGuardrail:
    """
    Guarantees that bot messages:
    1. Are readable and comprehensible by humans (Flesch-Kincaid / Syllable estimation).
    2. Do not decay into repetitive token loops (Token entropy & n-gram repetition check).
    3. Do not drift into pure robotic JSON/hex/regex gibberish unless explicitly formatted as code blocks.
    """

    def __init__(self, min_words: int = 8, max_words: int = 450):
        self.min_words = min_words
        self.max_words = max_words

    def _strip_markdown_code(self, text: str) -> str:
        # Strip fenced code blocks before measuring prose readability
        cleaned = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'`[^`]+`', '', cleaned)
        return cleaned.strip()

    def check_repetition(self, text: str) -> Tuple[bool, str]:
        words = [w.lower() for w in re.findall(r'\b[a-z]{3,}\b', text)]
        if not words:
            return False, "Message contains no valid words."
        
        # Check 3-gram repetitions (common symptom of LLM degeneration / loops)
        if len(words) >= 9:
            trigrams = [tuple(words[i:i+3]) for i in range(len(words)-2)]
            unique_trigrams = set(trigrams)
            trigram_ratio = len(unique_trigrams) / len(trigrams)
            if trigram_ratio < 0.65:
                return False, f"Degenerate repetition detected: trigram diversity {trigram_ratio:.2f} is too low."

        # Check adjacent duplicate sentences
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 10]
        for i in range(len(sentences) - 1):
            if sentences[i].lower() == sentences[i+1].lower():
                return False, "Immediate duplicate sentence detected."

        return True, "Passed repetition check."

    def calculate_human_readability(self, text: str) -> Dict[str, Any]:
        prose = self._strip_markdown_code(text)
        words = re.findall(r'\b\w+\b', prose)
        sentences = [s.strip() for s in re.split(r'[.!?]+', prose) if s.strip()]

        num_words = len(words)
        num_sentences = max(1, len(sentences))

        if num_words < self.min_words:
            return {
                "passed": False,
                "reason": f"Too short ({num_words} words, minimum is {self.min_words}).",
                "score": 0.0,
                "metrics": {"words": num_words, "sentences": num_sentences}
            }

        rep_ok, rep_reason = self.check_repetition(text)
        if not rep_ok:
            return {
                "passed": False,
                "reason": rep_reason,
                "score": 0.0,
                "metrics": {"words": num_words, "sentences": num_sentences}
            }

        # Approximate syllable counting
        def count_syllables(w: str) -> int:
            w = w.lower()
            if len(w) <= 3:
                return 1
            w = re.sub(r'(?:[^laeiouy]|ed|es|e)$', '', w)
            w = re.sub(r'^y', '', w)
            vowels = re.findall(r'[aeiouy]{1,2}', w)
            return max(1, len(vowels))

        total_syllables = sum(count_syllables(w) for w in words)
        words_per_sentence = num_words / num_sentences
        syllables_per_word = total_syllables / num_words

        # Flesch Reading Ease Formula: 206.835 - 1.015 * (words/sentence) - 84.6 * (syllables/word)
        flesch_score = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
        flesch_score = max(0.0, min(100.0, flesch_score))

        # Check for natural dialogue flow (Flesch score above 25 is technical-but-lucid; below 20 is opaque/pathological)
        passed = flesch_score >= 20.0 and num_words <= self.max_words

        return {
            "passed": passed,
            "reason": "OK" if passed else f"Readability score {flesch_score:.1f} out of bounds or too long ({num_words} words).",
            "score": round(flesch_score, 2),
            "metrics": {
                "words": num_words,
                "sentences": num_sentences,
                "avg_words_per_sentence": round(words_per_sentence, 1),
                "syllables_per_word": round(syllables_per_word, 2)
            }
        }

guardrail = ReadabilityGuardrail()
