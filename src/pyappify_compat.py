"""Application compatibility for the pinned PyAppify Python release."""

from importlib.metadata import PackageNotFoundError, version


def install_prerelease_comparison():
    """Repair the public comparator in 1.0.20 without editing the dependency."""
    try:
        installed = version("pyappify")
    except PackageNotFoundError:
        return "Unable to identify PyAppify; prerelease comparison compatibility was not enabled."
    if installed != "1.0.20":
        return None

    import pyappify
    from pyappify.versions import version_tag_key

    original = pyappify.is_greater_version
    if getattr(original, "_mc_helper_prerelease_comparison", False) is True:
        return None

    def is_greater_version(version1, version2):
        if isinstance(version1, str) and isinstance(version2, str):
            left, right = version_tag_key(version1), version_tag_key(version2)
            if left is not None and right is not None:
                return left > right
        return original(version1, version2)

    is_greater_version._mc_helper_prerelease_comparison = True
    pyappify.is_greater_version = is_greater_version
    return None
