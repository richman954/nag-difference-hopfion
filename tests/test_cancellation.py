from nagdiff.cancellation import cancellation_certificate, endpoint_difference


def test_shared_terms_cancel():
    common = 10.0
    si = 3.5
    sj = -1.25
    assert endpoint_difference(common, si, sj) == si - sj
    assert cancellation_certificate(common, si, sj)
