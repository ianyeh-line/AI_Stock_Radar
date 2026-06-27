from radar.integrations.cloud_user_store import cloud_status, is_cloud_store_configured


def test_cloud_store_not_required_for_local_tests():
    assert isinstance(is_cloud_store_configured(), bool)
    status = cloud_status()
    assert "status" in status
