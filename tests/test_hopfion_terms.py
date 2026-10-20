import pytest
from nagdiff.hopfion_terms import _validate_provenance, REQUIRED_PROVENANCE_FIELDS

def test_validate_provenance_raises_error():
    """Test that _validate_provenance raises a ValueError for missing or invalid fields."""

    # Valid record containing all required fields
    valid_record = {field: "valid_value" for field in REQUIRED_PROVENANCE_FIELDS}

    # Assert that _validate_provenance doesn't raise an error for a valid record
    _validate_provenance(valid_record)

    # Test missing fields
    for field in REQUIRED_PROVENANCE_FIELDS:
        invalid_record = valid_record.copy()
        del invalid_record[field]

        with pytest.raises(ValueError, match=f"missing required provenance field: {field}"):
            _validate_provenance(invalid_record)

    # Test empty string fields
    for field in REQUIRED_PROVENANCE_FIELDS:
        invalid_record = valid_record.copy()
        invalid_record[field] = ""

        with pytest.raises(ValueError, match=f"missing required provenance field: {field}"):
            _validate_provenance(invalid_record)

    # Test None fields
    for field in REQUIRED_PROVENANCE_FIELDS:
        invalid_record = valid_record.copy()
        invalid_record[field] = None

        with pytest.raises(ValueError, match=f"missing required provenance field: {field}"):
            _validate_provenance(invalid_record)
