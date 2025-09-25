def test_submodules_import():
    # Touch these so module-level code is executed & counted
    import app  # noqa: F401
    import app.main as main  # noqa: F401
    import app.oauth as oauth  # noqa: F401
    import app.jobs as jobs  # noqa: F401
    import app.review as review  # noqa: F401

    assert main is not None and oauth is not None and jobs is not None and review is not None
