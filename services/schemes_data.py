"""
Schemes data service: loading, lookup, and rule-based qualification.
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCHEMES_CACHE = None


def get_government_schemes() -> list:
    """Load and cache the curated government schemes JSON."""
    global _SCHEMES_CACHE
    if _SCHEMES_CACHE is None:
        path = os.path.join(_ROOT, "government_schemes.json")
        with open(path, encoding="utf-8") as f:
            _SCHEMES_CACHE = json.load(f)["schemes"]
    return _SCHEMES_CACHE


def scheme_by_id(scheme_id: str) -> dict | None:
    """Find a single scheme by its id field."""
    for s in get_government_schemes():
        if s["id"] == scheme_id:
            return s
    return None


# ---------------------------------------------------------------------------
# State name normalization for matching
# ---------------------------------------------------------------------------

_STATE_ALIASES = {
    "ap": "andhra-pradesh",
    "andhra pradesh": "andhra-pradesh",
    "andhra": "andhra-pradesh",
    "ts": "telangana",
    "telangana": "telangana",
    "mh": "maharashtra",
    "maharashtra": "maharashtra",
    "up": "uttar pradesh",
    "uttar pradesh": "uttar-pradesh",
    "tn": "tamil-nadu",
    "tamil nadu": "tamil-nadu",
    "ka": "karnataka",
    "karnataka": "karnataka",
    "kl": "kerala",
    "kerala": "kerala",
    "wb": "west-bengal",
    "west bengal": "west-bengal",
    "mp": "madhya-pradesh",
    "madhya pradesh": "madhya-pradesh",
    "rj": "rajasthan",
    "rajasthan": "rajasthan",
    "gj": "gujarat",
    "gujarat": "gujarat",
    "pb": "punjab",
    "punjab": "punjab",
    "hr": "haryana",
    "haryana": "haryana",
}


def _normalize_state(raw: str) -> str:
    """Normalize a user-entered state to its slug form."""
    key = raw.strip().lower().replace("-", " ")
    return _STATE_ALIASES.get(key, key.replace(" ", "-"))


# ---------------------------------------------------------------------------
# Rule-based qualification
# ---------------------------------------------------------------------------

def qualify_farmer(profile: dict) -> list:
    """
    Pre-filter schemes by farmer profile using simple rules.

    Parameters
    ----------
    profile : dict
        Keys: state, crop (optional), land_acres (optional), farmer_type (optional).
        farmer_type can be: "landowner", "tenant", or "any" (default).

    Returns
    -------
    list of dict
        Each item has: id, name, icon, benefit, match_reason, url.
    """
    schemes = get_government_schemes()
    farmer_state = _normalize_state(profile.get("state") or "")
    farmer_type = (profile.get("farmer_type") or "any").strip().lower()
    land_str = (profile.get("land_acres") or "").strip()

    state_is_specified = bool(farmer_state) and farmer_state not in {
        "india-(general)", "all-india-/-not-sure", "india", "not-specified", ""
    }

    results = []

    for scheme in schemes:
        scheme_location = scheme.get("location", "national").lower()
        reasons = []

        # --- Location match ---
        if scheme_location == "national":
            reasons.append("National scheme — available across India")
        elif state_is_specified and scheme_location == farmer_state:
            state_display = farmer_state.replace("-", " ").title()
            reasons.append(f"State scheme matching your location ({state_display})")
        elif state_is_specified and scheme_location != farmer_state:
            # State scheme for a different state → skip
            continue
        else:
            # State not specified — include state schemes but note it
            state_display = scheme_location.replace("-", " ").title()
            reasons.append(f"State scheme for {state_display} — verify your state eligibility")

        # --- Farmer type heuristic ---
        eligibility = (scheme.get("eligibility") or "").lower()
        if farmer_type == "tenant":
            if "pattadar" in eligibility and "tenant" not in eligibility:
                continue  # Requires land ownership records
            if "tenant" in eligibility or "sharecropper" in eligibility or "oral lessee" in eligibility:
                reasons.append("Supports tenant farmers")
        elif farmer_type == "landowner":
            if "landholding" in eligibility or "pattadar" in eligibility or "land records" in eligibility:
                reasons.append("Matches landholding farmer criteria")

        # --- Land size note ---
        if land_str:
            try:
                acres = float(land_str)
                if acres <= 5:
                    reasons.append(f"Applicable for small/marginal farmer ({acres} acres)")
                else:
                    reasons.append(f"Farm size: {acres} acres")
            except ValueError:
                pass

        results.append({
            "id": scheme["id"],
            "name": scheme["name"],
            "icon": scheme.get("icon", "📋"),
            "benefit": scheme.get("benefit", ""),
            "match_reason": "; ".join(reasons),
            "url": scheme.get("url", ""),
            "type": scheme.get("type", ""),
            "badge": scheme.get("badge", ""),
        })

    return results
