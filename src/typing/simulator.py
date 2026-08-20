"""Human typing physics and action plan simulator engine."""

import random
import unicodedata

from src.typing.config import TypingConfig
from src.typing.events import TypingAction, TypingStep

# QWERTY Key Proximity Map for realistic typos
QWERTY_PROXIMITY: dict[str, str] = {
    "a": "qwsz",
    "b": "vghn",
    "c": "xdfv",
    "d": "ersfcx",
    "e": "wsdr",
    "f": "rtgvcd",
    "g": "tyhbvf",
    "h": "yujnbg",
    "i": "ujko",
    "j": "uikmnh",
    "k": "ijlmo",
    "l": "kop",
    "m": "njk",
    "n": "bhjm",
    "o": "iklp",
    "p": "ol",
    "q": "wa",
    "r": "edft",
    "s": "wedxza",
    "t": "rfgy",
    "u": "yhji",
    "v": "cfgb",
    "w": "qase",
    "x": "zsdc",
    "y": "tghu",
    "z": "asx",
}


def parse_grapheme_clusters(text: str) -> list[str]:
    """Parse text into logical grapheme clusters supporting Unicode surrogate pairs and emojis."""
    clusters: list[str] = []
    current: list[str] = []

    for char in text:
        category = unicodedata.category(char)
        is_zwj_connector = (
            category.startswith("M")
            or ord(char) in (0x200D, 0xFE0F)
            or (bool(current) and ord(current[-1]) in (0x200D, 0xFE0F))
        )

        if current and is_zwj_connector:
            current.append(char)
        else:
            if current:
                clusters.append("".join(current))
            current = [char]

    if current:
        clusters.append("".join(current))

    return clusters


class HumanTypingSimulator:
    """Generates realistic human typing action plans with variable speed, jitter, and typos."""

    def generate_plan(self, text: str, config: TypingConfig) -> list[TypingStep]:
        """Convert raw input string into a list of atomic TypingSteps."""
        if not text:
            return []

        # Check paste threshold (only if enabled)
        if config.enable_paste_threshold and len(text) >= config.paste_threshold_chars:
            return [TypingStep(char=text, action_type=TypingAction.PASTE_CHUNK, delay_ms=50.0)]

        rng = (
            random.Random(config.random_seed)
            if config.random_seed is not None
            else random.Random()
        )
        graphemes = parse_grapheme_clusters(text)

        if config.humanized_rhythm_enabled:
            return self._generate_humanized_rhythm_plan(graphemes, config, rng)

        steps: list[TypingStep] = []

        # Calculate base timing from WPM (Standard word = 5 characters)
        chars_per_sec = (config.speed_wpm * 5.0) / 60.0
        base_delay_ms = (1.0 / chars_per_sec) * 1000.0 if chars_per_sec > 0 else 100.0

        prev_char = ""

        for i, g in enumerate(graphemes):
            # Calculate dynamic delay for current character
            delay = self._calculate_delay(g, prev_char, base_delay_ms, config, rng)

            # Check if typo should be simulated
            if i > 0 and len(g) == 1 and g.isalnum() and rng.random() < config.mistake_probability:
                typo_char = self._get_proximity_typo(g, rng)
                # 1. Type typo char
                steps.append(
                    TypingStep(
                        char=typo_char,
                        action_type=TypingAction.TYPE_CHAR,
                        delay_ms=delay,
                    )
                )
                # 2. Pause before noticing mistake
                steps.append(
                    TypingStep(
                        char="",
                        action_type=TypingAction.PAUSE,
                        delay_ms=config.correction_delay_ms,
                    )
                )
                # 3. Backspace
                steps.append(
                    TypingStep(
                        char="",
                        action_type=TypingAction.BACKSPACE,
                        delay_ms=config.min_delay_ms * 1.5,
                    )
                )
                # 4. Correct char
                steps.append(
                    TypingStep(
                        char=g,
                        action_type=TypingAction.TYPE_CHAR,
                        delay_ms=config.min_delay_ms * 2.0,
                    )
                )
            else:
                steps.append(
                    TypingStep(
                        char=g,
                        action_type=TypingAction.TYPE_CHAR,
                        delay_ms=delay,
                    )
                )

            prev_char = g

        return steps

    @staticmethod
    def _is_word_separator(g: str) -> bool:
        if not g or g.isspace() or g in ("\n", "\r", "\t"):
            return True
        punct = (
            ".",
            ",",
            "!",
            "?",
            ";",
            ":",
            "-",
            "—",
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
            '"',
            "'",
            "/",
            "\\",
            "@",
            "#",
            "$",
            "%",
            "^",
            "&",
            "*",
            "+",
            "=",
            "<",
            ">",
            "|",
            "`",
            "~",
        )
        return g in punct

    def _generate_humanized_rhythm_plan(
        self,
        graphemes: list[str],
        config: TypingConfig,
        rng: random.Random,
    ) -> list[TypingStep]:
        """Generate plan with 2-char burst -> 0.5s mid-word pause -> 1.0s word pause."""
        steps: list[TypingStep] = []
        n = len(graphemes)
        char_in_word = 0

        # Scale pauses proportionally with speed WPM (60 WPM baseline)
        wpm_scale = 60.0 / max(1.0, config.speed_wpm)
        mid_word_pause = config.mid_word_pause_ms * wpm_scale
        word_pause = config.word_pause_ms * wpm_scale
        fast_delay = max(config.min_delay_ms, config.fast_char_delay_ms * wpm_scale)

        for i, g in enumerate(graphemes):
            is_sep = self._is_word_separator(g)

            if not is_sep:
                char_in_word += 1
                delay = fast_delay
                if config.typing_jitter > 0:
                    jitter = rng.gauss(0, fast_delay * 0.15)
                    delay = max(config.min_delay_ms, min(config.max_delay_ms, delay + jitter))

                # Check if typo should be simulated
                if (
                    i > 0
                    and len(g) == 1
                    and g.isalnum()
                    and rng.random() < config.mistake_probability
                ):
                    typo_char = self._get_proximity_typo(g, rng)
                    steps.append(
                        TypingStep(
                            char=typo_char,
                            action_type=TypingAction.TYPE_CHAR,
                            delay_ms=delay,
                        )
                    )
                    steps.append(
                        TypingStep(
                            char="",
                            action_type=TypingAction.PAUSE,
                            delay_ms=config.correction_delay_ms,
                        )
                    )
                    steps.append(
                        TypingStep(
                            char="",
                            action_type=TypingAction.BACKSPACE,
                            delay_ms=config.min_delay_ms * 1.5,
                        )
                    )
                    steps.append(
                        TypingStep(
                            char=g,
                            action_type=TypingAction.TYPE_CHAR,
                            delay_ms=config.min_delay_ms * 2.0,
                        )
                    )
                else:
                    steps.append(
                        TypingStep(
                            char=g,
                            action_type=TypingAction.TYPE_CHAR,
                            delay_ms=delay,
                        )
                    )

                # Rule 2: After typing 2nd char of a word, take mid-word pause if word continues
                if char_in_word == 2 and mid_word_pause > 0:
                    next_is_word_char = (i + 1 < n) and (
                        not self._is_word_separator(graphemes[i + 1])
                    )
                    if next_is_word_char:
                        steps.append(
                            TypingStep(
                                char="",
                                action_type=TypingAction.PAUSE,
                                delay_ms=mid_word_pause,
                            )
                        )
            else:
                delay = fast_delay
                if config.typing_jitter > 0:
                    jitter = rng.gauss(0, fast_delay * 0.15)
                    delay = max(config.min_delay_ms, min(config.max_delay_ms, delay + jitter))

                steps.append(
                    TypingStep(
                        char=g,
                        action_type=TypingAction.TYPE_CHAR,
                        delay_ms=delay,
                    )
                )

                # Rule 1: After completing a word, take word pause
                if char_in_word > 0 and word_pause > 0:
                    steps.append(
                        TypingStep(
                            char="",
                            action_type=TypingAction.PAUSE,
                            delay_ms=word_pause,
                        )
                    )
                    char_in_word = 0

        if char_in_word > 0 and word_pause > 0:
            steps.append(
                TypingStep(
                    char="",
                    action_type=TypingAction.PAUSE,
                    delay_ms=word_pause,
                )
            )

        return steps

    def _calculate_delay(
        self,
        char: str,
        prev_char: str,
        base_delay_ms: float,
        config: TypingConfig,
        rng: random.Random,
    ) -> float:

        delay = base_delay_ms

        # Digraph timing (repeating keys are faster)
        if prev_char and char == prev_char:
            delay *= 0.7

        # Punctuation and whitespace delays
        if char in (".", "!", "?", "\n"):
            delay *= 2.5
        elif char in (",", ";", ":", "-"):
            delay *= 1.8
        elif char == " ":
            delay *= 1.2

        # Apply Gaussian jitter
        if config.typing_jitter > 0:
            jitter_delta = rng.gauss(0, base_delay_ms * config.typing_jitter)
            delay += jitter_delta

        # Clamp between min_delay_ms and max_delay_ms
        return max(config.min_delay_ms, min(config.max_delay_ms, delay))

    def _get_proximity_typo(self, char: str, rng: random.Random) -> str:
        c_lower = char.lower()
        if c_lower in QWERTY_PROXIMITY:
            typo = rng.choice(QWERTY_PROXIMITY[c_lower])
            return typo.upper() if char.isupper() else typo
        return "x"
