"""Burrows Delta — z-scored function-word L1 (Manhattan) distance.

Codex ``gpt-5.5 xhigh`` review (HIGH-5) corrected an early sketch that
called the metric "function-word vector cosine"; cosine distance is
not the Burrows Delta family. The canonical R-stylo formulation
(Eder/Rybicki/Kestemont, R Journal 2016) is:

1. Pick a closed list of function words for the language under test.
2. From a *background corpus* compute, per function word, the mean and
   standard deviation of relative frequency.
3. For each text under comparison, compute its relative frequency
   vector and z-score against the background statistics.
4. Delta between two texts = sum of absolute differences of their
   z-vectors (Manhattan / L1 distance).

In this codebase we hold the persona's z-vector in a
:class:`BurrowsReference` and compare an incoming test text against it.
The reference is per-language; cross-language comparison raises
:class:`BurrowsLanguageMismatchError` (per ``blockers.md`` "Burrows
multi-lang reference 暫定方針").

P1a delivers the pure math against synthetic references. P1b populates
real corpora (Akademie-Ausgabe Kant, KGW Nietzsche, 利休百首, plus a
synthetic 4th persona) under :mod:`erre_sandbox.evidence.reference_corpus`
once licensing has been confirmed (ME-6).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Iterable

DEFAULT_WHITESPACE_LANGUAGES: frozenset[str] = frozenset({"en", "de"})
"""Languages for which whitespace tokenisation gives a usable
function-word count.

Japanese (``"ja"``) requires a morphological analyser
(MeCab/SudachiPy) — left to P1b. Calling
:func:`compute_burrows_delta` with ``language="ja"`` and the default
tokeniser raises explicitly so we don't silently fold a stylometric
signal that is meaningless for the unsegmented script.
"""


class BurrowsLanguageMismatchError(ValueError):
    """Raised when reference language does not match the test text language.

    Function-word distributions are language-specific; comparing a German
    profile against an English text would produce a meaningless number.
    The contract defers explicit support of the third language (``"ja"``)
    to a per-language tokenizer landing in P1b.
    """


class BurrowsTokenizationUnsupportedError(NotImplementedError):
    """Raised when the requested language has no built-in tokeniser yet.

    Lets P1b add a Japanese-specific entry without changing the public
    contract: callers can detect "tokenizer missing" separately from
    "language mismatch" and wire in their own splitter via
    ``preprocessed_tokens`` once P1b ships the SudachiPy adapter.
    """


@dataclass(frozen=True)
class BurrowsReference:
    """Per-language Burrows reference profile.

    Attributes:
        language: ISO-ish language tag (``"en"`` / ``"de"`` / ``"ja"``).
            Compared verbatim against the ``language`` argument of
            :func:`compute_burrows_delta`.
        function_words: Closed list of lower-case function words. Order
            is positional; ``background_mean`` /
            ``background_std`` / ``profile_freq`` align by index.
        background_mean: Mean relative frequency of each function word
            across a generic background corpus (per-token rate, in
            ``[0, 1]``).
        background_std: Standard deviation of relative frequency in the
            same background corpus. Words with ``std <= 0`` are dropped
            from the Delta sum (would z-divide by zero).
        profile_freq: This persona's relative frequency vector for the
            same function words, computed from the persona's reference
            corpus.

    Construction is left to ``reference_corpus`` ingestion (P1b). For
    P1a tests, callers build a small synthetic ``BurrowsReference``
    directly.
    """

    language: str
    function_words: tuple[str, ...]
    background_mean: tuple[float, ...]
    background_std: tuple[float, ...]
    profile_freq: tuple[float, ...]

    def __post_init__(self) -> None:
        n = len(self.function_words)
        if not (
            len(self.background_mean) == n
            and len(self.background_std) == n
            and len(self.profile_freq) == n
        ):
            raise ValueError(
                "BurrowsReference vectors must have equal length;"
                f" function_words={n} mean={len(self.background_mean)}"
                f" std={len(self.background_std)} profile={len(self.profile_freq)}",
            )
        if any(s < 0 for s in self.background_std):
            raise ValueError("background_std entries must be non-negative")
        if any(not isfinite(v) for v in self.background_mean):
            raise ValueError("background_mean entries must be finite")
        if any(not isfinite(v) for v in self.background_std):
            raise ValueError("background_std entries must be finite")
        if any(not isfinite(v) for v in self.profile_freq):
            raise ValueError("profile_freq entries must be finite")


def _tokenize(text: str, language: str) -> list[str]:
    """Lower-case whitespace tokeniser for ``en`` and ``de``.

    Japanese routes through :class:`BurrowsTokenizationUnsupportedError`
    until P1b lands a SudachiPy-backed splitter (or callers preprocess
    the text into tokens themselves and use ``preprocessed_tokens=``).
    """
    if language not in DEFAULT_WHITESPACE_LANGUAGES:
        raise BurrowsTokenizationUnsupportedError(
            f"Burrows Delta default tokenizer does not support language"
            f" {language!r}; pass preprocessed_tokens= or wait for P1b"
            f" to ship a {language}-specific tokenizer",
        )
    # ``str.split`` (no args) collapses arbitrary whitespace, which is
    # adequate for the function-word counting use-case where exact
    # boundary handling at punctuation is tolerated noise.
    return [tok.lower() for tok in text.split() if tok]


def compute_burrows_delta(
    text: str,
    reference: BurrowsReference,
    *,
    language: str,
    preprocessed_tokens: Iterable[str] | None = None,
) -> float:
    """Burrows Delta = sum of absolute z-score differences (L1 distance).

    Args:
        text: Test utterance / document. Ignored if ``preprocessed_tokens``
            is provided — useful when the caller already ran a per-language
            tokenizer (e.g. SudachiPy for Japanese).
        reference: Per-language profile. ``reference.language`` must equal
            ``language`` or :class:`BurrowsLanguageMismatchError` is raised.
        language: Language of the test text. Must match
            ``reference.language``.
        preprocessed_tokens: Optional pre-tokenised lower-case stream that
            bypasses the built-in whitespace tokeniser. Lets Japanese (and
            future languages with non-trivial segmentation) participate
            ahead of full P1b tokeniser plumbing.

    Returns:
        ``sum_i |z_test_i - z_profile_i|`` over function words with
        ``std > 0``. Returns ``float('nan')`` when the test text is empty
        or no function word survived the ``std > 0`` filter — a NaN here
        is the explicit "metric unmeasurable" signal the bootstrap-CI
        code path knows how to drop (per the M8 ``compute_*`` contract:
        ``None``/``NaN`` means "no measurement", not "zero").

    Raises:
        BurrowsLanguageMismatchError: When ``language != reference.language``.
        BurrowsTokenizationUnsupportedError: When ``language`` has no
            default tokenizer and ``preprocessed_tokens`` is ``None``.
    """
    if language != reference.language:
        raise BurrowsLanguageMismatchError(
            f"Burrows reference language {reference.language!r} does not"
            f" match test text language {language!r}; per-language"
            f" reference contract requires identical tag",
        )

    tokens: list[str]
    if preprocessed_tokens is not None:
        tokens = [t.lower() for t in preprocessed_tokens if t]
    else:
        tokens = _tokenize(text, language)

    total = len(tokens)
    if total == 0:
        return float("nan")

    counts = Counter(tokens)

    delta_sum = 0.0
    counted = 0
    for fw, mean, std, profile in zip(
        reference.function_words,
        reference.background_mean,
        reference.background_std,
        reference.profile_freq,
        strict=True,
    ):
        if std <= 0.0:
            continue
        test_freq = counts.get(fw, 0) / total
        z_test = (test_freq - mean) / std
        z_profile = (profile - mean) / std
        delta_sum += abs(z_test - z_profile)
        counted += 1

    if counted == 0:
        return float("nan")
    return delta_sum
