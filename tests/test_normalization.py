from soficca_core.normalization import normalize

def test_normalize_accepts_interpret_en_values():
    signals = normalize({"desire": "reduced", "stress": "moderate"})
    assert signals["desire_preserved"] is False
    assert signals["stress_high"] is None
