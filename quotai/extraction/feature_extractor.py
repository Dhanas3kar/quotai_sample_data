"""
Mock AI feature extraction for QuotAI.

In a production system this module would call Gemini (or another vision model)
with **both** the reference drawing and the variant drawing.  The reference
extraction JSON is included in the prompt as a "known good" baseline so the
AI can ground its output for accuracy and consistency.

Here we simulate that process by returning hardcoded geometric features for
known variants and using the family reference extraction as a fallback for
unknown ones.
"""

from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Pre-defined feature sets (simulating AI extraction results)
# ---------------------------------------------------------------------------

_MOCK_FEATURES: Dict[str, Dict] = {
    "spacer_v1": {
        "outer_diameter_mm": 120,
        "inner_diameter_mm": 60,
        "length_mm": 80,
        "holes": [{"diameter_mm": 10, "count": 6}],
        "surface_finish": "Ra 1.6",
        "material_hint": "SS 316",
    },
    "spacer_v2": {
        "outer_diameter_mm": 120,
        "inner_diameter_mm": 60,
        "length_mm": 130,
        "holes": [{"diameter_mm": 10, "count": 8}],
        "surface_finish": "Ra 0.8",
        "material_hint": "SS 316",
    },
    "bearing_ring": {
        "outer_diameter_mm": 150,
        "inner_diameter_mm": 80,
        "length_mm": 40,
        "holes": [{"diameter_mm": 8, "count": 8}],
        "surface_finish": "Ra 0.4",
        "material_hint": "SS 316",
    },
    "flange_adapter": {
        "outer_diameter_mm": 200,
        "inner_diameter_mm": 100,
        "length_mm": 25,
        "holes": [{"diameter_mm": 12, "count": 12}],
        "surface_finish": "Ra 1.6",
        "material_hint": "Mild Steel",
    },
}

# Bare-minimum defaults when nothing else is available
_DEFAULT_FEATURES: Dict = {
    "outer_diameter_mm": 100,
    "inner_diameter_mm": 50,
    "length_mm": 60,
    "holes": [{"diameter_mm": 8, "count": 4}],
    "surface_finish": "Ra 1.6",
    "material_hint": "Stainless Steel",
}


def extract_features_from_variant(
    variant_name: str,
    ref_extraction: Optional[Dict] = None,
    variant_extraction: Optional[Dict] = None,
    variant_drawing_bytes: Optional[bytes] = None,
    ref_drawing_path: Optional[str] = None,
) -> Dict:
    """
    Simulate AI feature extraction from a variant drawing.

    In a production system both the *reference drawing* and the *variant
    drawing* are sent to Gemini.  The reference extraction JSON is used as
    grounding context so the AI can produce consistent, accurate output.

    Resolution order
    ----------------
    1. If a stored ``variant_extraction`` (from ``VariantExtraction`` table)
       is available, use it directly — this is the "frozen" AI result.
    2. If a ``variant_drawing_bytes`` was uploaded, simulate calling the
       vision model with both the variant image and the reference drawing.
       (In this prototype, the bytes are accepted but the mock lookup by
       name is used to simulate the AI response.)
    3. Otherwise try the mock feature lookup by variant name keyword.
    4. If the variant is unknown **but** a ``ref_extraction`` (from the
       ``ProductFamily.ref_extraction_data`` column) is available, use the
       reference features as the baseline.
    5. Fall back to hard-coded defaults.

    Parameters
    ----------
    variant_name : str
        Name or keyword of the product variant.
    ref_extraction : dict | None
        Parsed ``ref_extraction_data`` from the parent product family.
        Acts as the reference-drawing grounding context.
    variant_extraction : dict | None
        Parsed ``extraction_data`` from a ``VariantExtraction`` row
        (the stored AI result).
    variant_drawing_bytes : bytes | None
        Raw bytes of an uploaded variant drawing image.  In production
        this would be sent to Gemini along with *ref_drawing_path*.
    ref_drawing_path : str | None
        File path of the family reference drawing (for the AI prompt).

    Returns
    -------
    dict
        Extracted geometric features.
    """
    # 1. Use stored variant extraction if available
    if variant_extraction is not None:
        features = dict(variant_extraction)
        # Normalise — the stored JSON uses "material" not "material_hint"
        if "material" in features and "material_hint" not in features:
            features["material_hint"] = features.pop("material")
        return features

    # 2. Variant drawing uploaded → simulate vision-model call
    #    In production:  response = gemini.extract(variant_drawing_bytes,
    #                                              ref_drawing_path,
    #                                              ref_extraction)
    #    For prototype:  accept the bytes (proves the upload path works)
    #                    then fall through to mock lookup.
    if variant_drawing_bytes is not None:
        # Log that we received the drawing (would be sent to Gemini)
        _size_kb = len(variant_drawing_bytes) / 1024
        # Simulated AI call — use mock lookup by name
        name_lower = variant_name.lower().replace(" ", "_").replace("-", "_")
        for key, feat in _MOCK_FEATURES.items():
            if key in name_lower:
                result = dict(feat)
                result["_extraction_source"] = "mock_ai_from_upload"
                result["_drawing_size_kb"] = round(_size_kb, 1)
                return result
        # Drawing uploaded but variant unknown — use ref_extraction if available
        if ref_extraction is not None:
            features = dict(ref_extraction)
            if "material" in features and "material_hint" not in features:
                features["material_hint"] = features.pop("material")
            features.setdefault("surface_finish", "Ra 1.6")
            features.setdefault("material_hint", "Stainless Steel")
            features.setdefault("holes", [])
            features["_extraction_source"] = "ref_baseline_from_upload"
            features["_drawing_size_kb"] = round(_size_kb, 1)
            return features
        # No ref either — defaults
        result = dict(_DEFAULT_FEATURES)
        result["_extraction_source"] = "defaults_from_upload"
        result["_drawing_size_kb"] = round(_size_kb, 1)
        return result

    # 3. Try the mock feature lookup by name (no drawing uploaded)
    name_lower = variant_name.lower().replace(" ", "_").replace("-", "_")
    for key, feat in _MOCK_FEATURES.items():
        if key in name_lower:
            return dict(feat)

    # 4. Use the family reference extraction as a baseline
    if ref_extraction is not None:
        features = dict(ref_extraction)
        if "material" in features and "material_hint" not in features:
            features["material_hint"] = features.pop("material")
        # Ensure the minimum keys are present
        features.setdefault("surface_finish", "Ra 1.6")
        features.setdefault("material_hint", "Stainless Steel")
        features.setdefault("holes", [])
        return features

    # 4. Hard-coded defaults
    return dict(_DEFAULT_FEATURES)


def override_features(features: Dict,
                      outer_diameter: Optional[float] = None,
                      inner_diameter: Optional[float] = None,
                      length: Optional[float] = None,
                      hole_count: Optional[int] = None,
                      hole_diameter: Optional[float] = None) -> Dict:
    """
    Override individual feature values with manual engineering inputs.

    Only non-``None`` values replace the extracted defaults.
    """
    updated = dict(features)
    if outer_diameter is not None:
        updated["outer_diameter_mm"] = outer_diameter
    if inner_diameter is not None:
        updated["inner_diameter_mm"] = inner_diameter
    if length is not None:
        updated["length_mm"] = length
    if hole_count is not None or hole_diameter is not None:
        current_hole = updated.get("holes", [{}])[0] if updated.get("holes") else {}
        updated["holes"] = [{
            "diameter_mm": hole_diameter if hole_diameter is not None
                           else current_hole.get("diameter_mm", 8),
            "count": hole_count if hole_count is not None
                     else current_hole.get("count", 4),
        }]
    return updated
