from pytest import MarkDecorator, mark


def testmap(feature: str, kind: str) -> MarkDecorator:
    """Tag a test with its feature and kind (applies a `pytest.mark.testmap` marker)."""
    return mark.testmap(feature=feature, kind=kind)


# The name starts with "test", so without this pytest would try to collect the
# decorator itself when it is imported into a test module.
setattr(testmap, "__test__", False)  # noqa: B010
