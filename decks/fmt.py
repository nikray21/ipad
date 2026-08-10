"""
Shared number formatting for every episode deck.

One rule, applied everywhere: a figure wears the unit that fits it. $1.8B,
$1.8M, $208K — never $0.45B for four hundred and fifty million, and never
$1,800M for one point eight billion. A viewer reading this once, at speaking
pace, should not have to shift a decimal point in their head.

All inputs are in MILLIONS, matching the Terminal's own units.
"""

MINUS = "−"                                  # true minus, not a hyphen


def _sig(n, digits=1):
    """
    One decimal, dropped once the mantissa already carries three significant
    figures. $1.8B and $3.0B keep theirs; $730M and $208M do not need one.
    """
    if abs(n) >= 100:
        return f"{n:,.0f}"
    return f"{n:,.{digits}f}"


def usd(m, digits=1):
    """
    Money, in millions in, auto-scaled out.

        1_800  -> $1.8B      450 -> $450M       0.208 -> $208K
        1_800_000 -> $1.8T                      0.0004 -> $400
    """
    if m is None:
        return "—"
    sign = MINUS if m < 0 else ""
    a = abs(float(m))
    if a >= 1_000_000:
        return f"{sign}${_sig(a / 1_000_000, digits)}T"
    if a >= 1_000:
        return f"{sign}${_sig(a / 1_000, digits)}B"
    if a >= 1:
        return f"{sign}${_sig(a, digits)}M"
    if a >= 0.001:
        return f"{sign}${_sig(a * 1_000, 0)}K"
    return f"{sign}${a * 1_000_000:,.0f}"


def num(n, digits=1):
    """The same scaling for a bare count — 6,893,343 shares -> 6.9M."""
    if n is None:
        return "—"
    sign = MINUS if n < 0 else ""
    a = abs(float(n))
    if a >= 1_000_000_000:
        return f"{sign}{_sig(a / 1_000_000_000, digits)}B"
    if a >= 1_000_000:
        return f"{sign}{_sig(a / 1_000_000, digits)}M"
    if a >= 1_000:
        return f"{sign}{_sig(a / 1_000, digits)}K"
    return f"{sign}{a:,.0f}"


def dollars(n):
    """A share price. Always two decimals — $172.01, never $172."""
    return (MINUS if n < 0 else "") + f"${abs(n):,.2f}"


def dollars0(n):
    """A whole-dollar price — $85, not $85.00. For monthly bills and round tickets."""
    return (MINUS if n < 0 else "") + f"${abs(n):,.0f}"


def pct(n, digits=1, signed=True):
    if n is None:
        return "—"
    lead = ("+" if n > 0 else MINUS if n < 0 else "") if signed else (MINUS if n < 0 else "")
    return f"{lead}{abs(n):.{digits}f}%"


def mult(n, digits=1, plain=False):
    """A multiple. `plain` gives the glyph for chart labels; prose gets the entity."""
    return f"{n:.{digits}f}" + ("×" if plain else "&times;")
