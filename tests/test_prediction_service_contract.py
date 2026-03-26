"""Contract tests for middleware prediction produce normalization."""

from app.services import prediction_service


def test_leafy_greens_alias_uses_non_default_coefficients():
    kp = prediction_service.get_produce_coefficient("leafy_greens")
    cdot = prediction_service.get_cdot_max("leafy_greens")
    assert kp == 1.3
    assert cdot == 240


def test_berries_alias_maps_to_high_sensitivity_profile():
    kp = prediction_service.get_produce_coefficient("berries")
    cdot = prediction_service.get_cdot_max("berries")
    assert kp == 1.5
    assert cdot == 180


def test_plural_and_space_aliases_are_normalized():
    assert prediction_service.get_produce_coefficient("leafy greens") == 1.3
    assert prediction_service.get_produce_coefficient("mangoes") == prediction_service.get_produce_coefficient("mango")
    assert prediction_service.get_produce_coefficient("avocados") == prediction_service.get_produce_coefficient("avocado")
