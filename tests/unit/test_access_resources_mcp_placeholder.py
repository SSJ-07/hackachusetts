import access_resources_mcp


def test_placeholder_is_importable_and_not_implemented():
    assert access_resources_mcp.SERVER_NAME == "access-resources-mcp"
    assert access_resources_mcp.PLANNED_TOOLS == ("rural_options", "pt1_prefill", "visit_rules")
    assert access_resources_mcp.IMPLEMENTED is False
