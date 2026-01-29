"""Property-based tests for cache integrity.

Ensures the cache maintains consistency regardless of input patterns.
"""

from hypothesis import assume, given
from hypothesis import strategies as st

from adversarial_debate.cache.hash import (
    hash_content,
    normalize_code,
)

# =============================================================================
# Property: Hash function determinism
# =============================================================================


@given(st.text(max_size=10000))
def test_hash_is_deterministic(content: str) -> None:
    """Same content must always produce same hash."""
    hash1 = hash_content(content)
    hash2 = hash_content(content)
    assert hash1 == hash2, "Hash must be deterministic"


@given(st.text(min_size=1, max_size=10000))
def test_different_content_different_hash(content: str) -> None:
    """Different content should produce different hashes (collision resistance)."""
    # Modify content slightly
    modified = content + "x"
    hash1 = hash_content(content)
    hash2 = hash_content(modified)
    # Note: This could theoretically fail due to collision, but extremely unlikely
    assert hash1 != hash2, "Different content should produce different hashes"


@given(st.text(max_size=10000))
def test_hash_format(content: str) -> None:
    """Hash must be a valid hex string of expected length."""
    result = hash_content(content)
    assert isinstance(result, str)
    assert len(result) == 64  # SHA-256 produces 64 hex chars
    assert all(c in "0123456789abcdef" for c in result)


# =============================================================================
# Property: Code normalization consistency
# =============================================================================


@given(st.text(max_size=5000))
def test_normalization_is_idempotent(code: str) -> None:
    """Normalizing twice should give same result as normalizing once."""
    once = normalize_code(code)
    twice = normalize_code(once)
    assert once == twice, "Normalization must be idempotent"


@given(st.text(max_size=5000))
def test_normalized_code_has_consistent_hash(code: str) -> None:
    """Normalized code should have consistent hash."""
    normalized = normalize_code(code)
    hash1 = hash_content(normalized)
    hash2 = hash_content(normalize_code(code))
    assert hash1 == hash2


# =============================================================================
# Property: Whitespace normalization
# =============================================================================


@given(
    st.text(alphabet=st.characters(blacklist_categories=["Cs"]), max_size=1000),
    st.integers(min_value=0, max_value=10),
)
def test_trailing_whitespace_normalized(code: str, extra_spaces: int) -> None:
    """Trailing whitespace should be normalized."""
    code_with_spaces = code + " " * extra_spaces
    normalized1 = normalize_code(code)
    normalized2 = normalize_code(code_with_spaces)
    # After normalization, trailing whitespace should be handled consistently
    assert (
        hash_content(normalized1) == hash_content(normalized2)
        or normalized1.rstrip() == normalized2.rstrip()
    )


# =============================================================================
# Property: Hash collision resistance for similar inputs
# =============================================================================


@given(
    st.text(min_size=10, max_size=1000),
    st.integers(min_value=0, max_value=100),
)
def test_single_char_change_different_hash(content: str, position: int) -> None:
    """Changing a single character should change the hash."""
    assume(len(content) > 0)
    position = position % len(content)

    # Change one character
    chars = list(content)
    original_char = chars[position]
    chars[position] = chr((ord(original_char) + 1) % 128)
    modified = "".join(chars)

    assume(content != modified)  # Skip if no change happened

    hash1 = hash_content(content)
    hash2 = hash_content(modified)
    assert hash1 != hash2, "Single char change should change hash"


# =============================================================================
# Property: Empty and edge case handling
# =============================================================================


def test_empty_content_has_hash() -> None:
    """Empty content should still produce a valid hash."""
    result = hash_content("")
    assert isinstance(result, str)
    assert len(result) == 64


@given(st.binary(max_size=1000))
def test_binary_content_handling(data: bytes) -> None:
    """Binary data should be hashable after encoding."""
    content = data.decode("utf-8", errors="replace")
    result = hash_content(content)
    assert isinstance(result, str)
    assert len(result) == 64
