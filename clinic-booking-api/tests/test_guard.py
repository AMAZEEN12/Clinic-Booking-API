import pytest

from tests.guard import GuardError, check_test_database

TEST_URL = "postgresql://u:p@ep-test-123.example.neon.tech/neondb?sslmode=require"
PROD_URL = "postgresql://u:p@ep-prod-456.example.neon.tech/neondb?sslmode=require"


def test_missing_test_url_is_refused():
    with pytest.raises(GuardError):
        check_test_database(None, PROD_URL)
    with pytest.raises(GuardError):
        check_test_database("   ", None)


def test_same_url_as_production_is_refused():
    with pytest.raises(GuardError):
        check_test_database(PROD_URL, PROD_URL)


def test_same_database_with_different_options_is_refused():
    same_db_other_options = "postgresql://other:pw@ep-prod-456.example.neon.tech/neondb"
    with pytest.raises(GuardError):
        check_test_database(same_db_other_options, PROD_URL)


def test_different_database_is_allowed():
    assert check_test_database(TEST_URL, PROD_URL) == TEST_URL


def test_production_url_not_set_is_allowed():
    assert check_test_database(TEST_URL, None) == TEST_URL
