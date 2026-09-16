from __future__ import annotations

MAROON_PER_SAFFRON = 25
SAFFRON_PER_PURPLE = 25
MAROON_PER_PURPLE = (
    MAROON_PER_SAFFRON * SAFFRON_PER_PURPLE
)


def maroon_to_pushp(amount: int) -> str:
    """Convert Maroon value into a readable Pushp amount."""

    if amount < 0:
        raise ValueError("Amount can't be negative")

    purple = amount // MAROON_PER_PURPLE
    remainder = amount % MAROON_PER_PURPLE

    saffron = remainder // MAROON_PER_SAFFRON
    maroon = remainder % MAROON_PER_SAFFRON

    parts: list[str] = []

    if purple:
        parts.append(f'{purple} P')

    if saffron:
        parts.append(f'{saffron} S')

    if maroon:
        parts.append(f'{maroon} M')

    return " + ".join(parts) if parts else "0 M" 


def pushp_to_maroon(
        purple : int = 0,
        saffron : int = 0,
        maroon : int = 0,
) -> int:
    """Convert P/S/M values into Maroon."""

    if purple < 0 or saffron < 0 or maroon < 0:
        raise ValueError("Currency values can't be negative")

    return (
        purple * MAROON_PER_PURPLE
        + saffron * MAROON_PER_SAFFRON
        + maroon
    )
