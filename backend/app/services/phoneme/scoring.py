from typing import List


# ---------------------------------------------------
# LEVENSHTEIN
# ---------------------------------------------------

def levenshtein(a: list, b: list) -> int:

    m, n = len(a), len(b)

    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i

    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):

        for j in range(1, n + 1):

            if a[i - 1] == b[j - 1]:

                dp[i][j] = dp[i - 1][j - 1]

            else:

                dp[i][j] = 1 + min(
                    dp[i - 1][j],
                    dp[i][j - 1],
                    dp[i - 1][j - 1]
                )

    return dp[m][n]


# ---------------------------------------------------
# INDIAN ACCENT EQUIVALENTS
# ---------------------------------------------------

INDIAN_ACCENT_EQUIVALENTS = {

    frozenset(["V", "W"]),

    frozenset(["T", "RT"]),
    frozenset(["D", "RD"]),

    frozenset(["TH", "D"]),
    frozenset(["TH", "T"]),

    frozenset(["Z", "J"]),

    frozenset(["AE", "EH"]),
    frozenset(["AO", "AH"]),
    frozenset(["IH", "IY"]),
    frozenset(["UW", "UH"]),

    frozenset(["R", "RD"])
}


# ---------------------------------------------------
# NORMALIZE FOR DISTANCE
# ---------------------------------------------------

def normalize_variants(
    expected: List[str],
    detected: List[str]
):

    normalized = []

    for i, ep in enumerate(expected):

        if i >= len(detected):
            continue

        dp = detected[i]

        pair = frozenset([ep, dp])

        if pair in INDIAN_ACCENT_EQUIVALENTS:
            normalized.append(ep)
        else:
            normalized.append(dp)

    return normalized


# ---------------------------------------------------
# SCORE PHONEMES
# ---------------------------------------------------

def score_phonemes(
    expected: List[str],
    detected: List[str]
):

    matches = []

    error_types = set()

    exp = [p.upper() for p in expected]
    det = [p.upper() for p in detected]

    correct_count = 0

    for i, ep in enumerate(exp):

        if i < len(det):

            dp = det[i]

            correct = False

            if ep == dp:

                correct = True

            else:

                pair = frozenset([ep, dp])

                if pair in INDIAN_ACCENT_EQUIVALENTS:

                    correct = True
                    error_types.add(
                        "indian_variant"
                    )

            if correct:

                correct_count += 1

            else:

                error_types.add(
                    "substitution"
                )

            matches.append({

                "expected": expected[i],

                "detected": detected[i],

                "correct": correct
            })

        else:

            matches.append({

                "expected": expected[i],

                "detected": None,

                "correct": False
            })

            error_types.add(
                "omission"
            )

    if len(detected) > len(expected):

        error_types.add(
            "addition"
        )

    # -----------------------------
    # Distance (variant aware)
    # -----------------------------

    det_for_distance = normalize_variants(
        exp,
        det
    )

    dist = levenshtein(
        exp,
        det_for_distance
    )

    max_len = max(
        len(expected),
        len(detected),
        1
    )

    base_accuracy = max(
        0,
        (1 - dist / max_len) * 100
    )

    precision = (
        correct_count /
        max(len(expected), 1)
    ) * 100

    accuracy = round(
        (base_accuracy * 0.7)
        +
        (precision * 0.3),
        2
    )

    return {

        "matches": matches,

        "accuracy": accuracy,

        "error_types": list(
            error_types
        )
    }