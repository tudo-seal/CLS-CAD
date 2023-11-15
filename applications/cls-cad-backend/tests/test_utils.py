import pytest
from cls_cad_backend.util.motion import combine_motions


@pytest.mark.order(16)
def test_combine_motions():
    result = combine_motions("Any", "Any")
    assert result == "Any"
    result = combine_motions("Any", "Rigid")
    assert result == "Any"
    result = combine_motions("Rigid", "Any")
    assert result == "Any"
    result = combine_motions("Any", "AnythingElse")
    assert result == "Ball"
