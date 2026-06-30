import testmap


def test_package_imports() -> None:
    assert callable(testmap.main)
