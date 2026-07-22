"""
DMA centroid positions in Albers USA projection coordinates.

Projection: geoAlbersUsa().scale(1300).translate([487.5, 305])
Coordinate space: ~960 × 600

These are approximate metro-area centroids for the top ~80 Nielsen DMA
markets.  The BFF includes these in geo responses so the frontend can
render any set of DMA markets without hardcoded positions.

Add new entries as clients expand into new markets.
"""

from __future__ import annotations

# Each entry: (cx, cy, default_radius, state_abbrev)
# Radius is a baseline that the frontend scales by data intensity.
# Coordinates computed from D3 geoAlbersUsa().scale(1300).translate([487.5, 305])
# using real city lat/lng — do not hand-edit.
DMA_CENTROIDS: dict[str, tuple[float, float, float, str]] = {
    # --- Top 30 DMAs ---
    "501": (869.7, 215.8, 24, "NY"),   # New York
    "602": (638.2, 226.1, 24, "IL"),   # Chicago
    "803": ( 86.9, 363.2, 23, "CA"),   # Los Angeles
    "504": (854.2, 237.2, 22, "PA"),   # Philadelphia
    "807": ( 34.8, 261.5, 21, "CA"),   # San Francisco–Oakland–San Jose
    "506": (908.7, 167.1, 21, "MA"),   # Boston (Manchester)
    "511": (827.4, 267.3, 21, "DC"),   # Washington DC (Hagerstown)
    "524": (714.9, 405.1, 20, "GA"),   # Atlanta
    "623": (482.9, 440.5, 20, "TX"),   # Dallas–Fort Worth
    "618": (510.4, 509.2, 19, "TX"),   # Houston
    "505": (713.1, 207.3, 20, "MI"),   # Detroit
    "753": (197.3, 399.7, 19, "AZ"),   # Phoenix (Prescott)
    "819": ( 97.7,  46.2, 19, "WA"),   # Seattle–Tacoma
    "527": (667.7, 271.7, 19, "IN"),   # Indianapolis
    "539": (769.5, 530.9, 18, "FL"),   # Tampa–St. Petersburg (Sarasota)
    "515": (697.9, 283.8, 19, "OH"),   # Cincinnati
    "535": (721.5, 260.9, 19, "OH"),   # Columbus, OH
    "510": (738.4, 222.8, 18, "OH"),   # Cleveland–Akron (Canton)
    "534": (541.8, 161.0, 17, "MN"),   # Minneapolis–St. Paul
    "528": (822.8, 572.6, 18, "FL"),   # Miami–Fort Lauderdale
    "550": (770.8, 242.2, 17, "PA"),   # Pittsburgh
    "617": (599.8, 303.5, 17, "MO"),   # St. Louis
    "560": (342.9, 273.9, 17, "CO"),   # Denver
    "641": (448.8, 516.4, 17, "TX"),   # San Antonio
    "508": (812.9, 343.1, 17, "NC"),   # Raleigh–Durham (Fayetteville)
    "517": (775.4, 362.3, 17, "NC"),   # Charlotte
    "820": ( 79.3,  90.4, 17, "OR"),   # Portland, OR
    "529": (678.4, 305.6, 17, "KY"),   # Louisville
    "548": (522.8, 295.7, 17, "MO"),   # Kansas City

    # --- DMAs 31–60 ---
    "518": (791.1, 340.2, 16, "NC"),   # Greensboro–High Point–Winston-Salem
    "567": (448.8, 516.4, 16, "TX"),   # San Antonio (combined)
    "770": (228.5, 235.3, 16, "UT"),   # Salt Lake City
    "561": (777.3, 475.2, 16, "FL"),   # Jacksonville
    "541": (631.3, 200.1, 16, "WI"),   # Milwaukee
    "544": (626.7, 166.9, 16, "WI"),   # Green Bay–Appleton
    "533": (668.4, 198.3, 16, "MI"),   # Grand Rapids–Kalamazoo
    "616": (464.0, 497.4, 16, "TX"),   # Austin
    "659": (665.1, 355.1, 16, "TN"),   # Nashville
    "557": (717.3, 353.9, 15, "TN"),   # Knoxville
    "531": (661.7, 228.4, 15, "IN"),   # South Bend–Elkhart
    "563": (670.6, 415.3, 15, "AL"),   # Birmingham (Anniston and Tuscaloosa)
    "546": (700.6, 193.3, 15, "MI"),   # Flint–Saginaw–Bay City
    "588": (701.0, 307.9, 15, "KY"),   # Lexington
    "513": (538.1, 238.4, 15, "IA"),   # Des Moines–Ames

    # --- DMAs 61–80 ---
    "564": (750.3, 293.9, 15, "WV"),   # Charleston–Huntington
    "556": (498.2, 363.5, 15, "OK"),   # Tulsa
    "547": (801.3, 414.8, 15, "SC"),   # Charleston, SC
    "521": (906.2, 180.5, 14, "RI"),   # Providence–New Bedford
    "530": (566.6, 394.2, 14, "AR"),   # Little Rock–Pine Bluff
    "543": (614.4, 501.3, 14, "LA"),   # New Orleans
    "613": (541.8, 161.0, 14, "MN"),   # Minneapolis (alt)
    "609": (599.8, 303.5, 14, "MO"),   # St. Louis (alt)
    "522": (607.4, 382.9, 14, "TN"),   # Memphis
    "525": (499.0, 246.4, 14, "NE"),   # Omaha
    "532": (863.5, 171.7, 14, "NY"),   # Albany–Schenectady–Troy
    "542": (701.6, 268.1, 14, "OH"),   # Dayton
    "566": (823.9, 236.2, 14, "PA"),   # Harrisburg–Lancaster–Lebanon–York

    # --- Fallback: additional known markets ---
    "512": (833.0, 257.2, 14, "MD"),   # Baltimore
    "545": (822.0, 550.8, 14, "FL"),   # West Palm Beach–Fort Pierce
    "571": (785.6, 558.4, 14, "FL"),   # Fort Myers–Naples
    "686": (652.8, 481.7, 14, "AL"),   # Mobile–Pensacola (Fort Walton Beach)
    "519": (801.3, 414.8, 14, "SC"),   # Charleston, SC (alt)
    "658": (474.2, 328.0, 14, "KS"),   # Wichita–Hutchinson
    "540": (717.3, 353.9, 14, "TN"),   # Knoxville (alt)
    "573": (783.8, 313.6, 14, "VA"),   # Roanoke–Lynchburg
    "569": (797.8, 283.7, 14, "VA"),   # Harrisonburg
}


# Aliases: map common market display names → Nielsen DMA code
DMA_NAME_TO_CODE: dict[str, str] = {
    # Full "City, ST" format
    "New York, NY": "501",
    "Chicago, IL": "602",
    "Los Angeles, CA": "803",
    "Philadelphia, PA": "504",
    "San Francisco, CA": "807",
    "Boston, MA": "506",
    "Washington, DC": "511",
    "Atlanta, GA": "524",
    "Dallas, TX": "623",
    "Houston, TX": "618",
    "Detroit, MI": "505",
    "Phoenix, AZ": "753",
    "Seattle, WA": "819",
    "Indianapolis, IN": "527",
    "Tampa, FL": "539",
    "Cincinnati, OH": "515",
    "Columbus, OH": "535",
    "Cleveland, OH": "510",
    "Minneapolis, MN": "534",
    "Miami, FL": "528",
    "Pittsburgh, PA": "550",
    "St. Louis, MO": "617",
    "Denver, CO": "560",
    "San Antonio, TX": "641",
    "Raleigh, NC": "508",
    "Charlotte, NC": "517",
    "Portland, OR": "820",
    "Louisville, KY": "529",
    "Kansas City, MO": "548",
    "Nashville, TN": "659",
    "Milwaukee, WI": "541",
    "Salt Lake City, UT": "770",
    "Austin, TX": "616",
    "Birmingham, AL": "563",
    "Memphis, TN": "522",
    "New Orleans, LA": "543",
    "Omaha, NE": "525",
    "Baltimore, MD": "512",

    # City-only shorthand
    "New York": "501",
    "Chicago": "602",
    "Los Angeles": "803",
    "Philadelphia": "504",
    "San Francisco": "807",
    "Boston": "506",
    "Washington": "511",
    "Atlanta": "524",
    "Dallas": "623",
    "Houston": "618",
    "Detroit": "505",
    "Phoenix": "753",
    "Seattle": "819",
    "Indianapolis": "527",
    "Tampa": "539",
    "Cincinnati": "515",
    "Columbus": "535",
    "Cleveland": "510",
    "Minneapolis": "534",
    "Miami": "528",
    "Pittsburgh": "550",
    "St. Louis": "617",
    "Denver": "560",
    "San Antonio": "641",
    "Raleigh": "508",
    "Charlotte": "517",
    "Portland": "820",
    "Louisville": "529",
    "Kansas City": "548",
    "Nashville": "659",
    "Milwaukee": "541",
    "Salt Lake City": "770",
    "Austin": "616",
    "Birmingham": "563",
    "Memphis": "522",
    "New Orleans": "543",
    "Omaha": "525",
    "Baltimore": "512",
}


def get_dma_centroid(dma_name: str) -> dict | None:
    """Return centroid data for a DMA market name.

    Returns dict with keys: code, cx, cy, r, state
    or None if the DMA is not in the registry.
    """
    code = DMA_NAME_TO_CODE.get(dma_name)
    if not code:
        return None
    entry = DMA_CENTROIDS.get(code)
    if not entry:
        return None
    cx, cy, r, state = entry
    return {"code": code, "cx": cx, "cy": cy, "r": r, "state": state}


def enrich_markets_with_centroids(markets: list[dict]) -> list[dict]:
    """Add centroid data to each market dict (in-place + return).

    Looks up by the 'Market' key in each dict.
    """
    for m in markets:
        name = m.get("Market", "")
        centroid = get_dma_centroid(name)
        if centroid:
            m["dma_code"] = centroid["code"]
            m["cx"] = centroid["cx"]
            m["cy"] = centroid["cy"]
            m["r"] = centroid["r"]
            m["state"] = centroid["state"]
    return markets
