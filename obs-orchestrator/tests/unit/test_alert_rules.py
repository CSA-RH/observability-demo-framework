"""Pure alert helpers in main.py (module-level, double-underscore names)."""
import pytest

import main


def helper(name):
    return getattr(main, f"__{name}")


def metric_alert(expression=">", value=10):
    return {
        "scope": "metricAgent",
        "severity": "warning",
        "definition": {"agent": "fabrice-olinga", "metric": "orders", "expression": expression, "value": value},
    }


CUSTOM_ALERT = {
    "scope": "custom",
    "name": "High_Latency",
    "severity": "critical",
    "definition": {"expression": "up == 0", "summary": "Service down"},
}


@pytest.mark.parametrize(
    "symbol, label, operator",
    [
        ("<", "StrictlyTooLow", "<"),
        ("≤", "TooLow", "<="),
        (">", "StrictlyTooHigh", ">"),
        ("≥", "TooHigh", ">="),
        ("≠", "Distinct", "!="),
        ("=", "Equals", "=="),
        ("~", "Unknown", "Unknown"),
    ],
)
def test_expression_mappings(symbol, label, operator):
    assert helper("map_expression_to_alert")(symbol) == label
    assert helper("map_expression_operator_to_comparison_operator")(symbol) == operator


def test_metric_agent_alert_fields():
    alert = metric_alert()
    assert helper("get_alert_name")(alert) == "fabrice-olinga_orders_StrictlyTooHigh"
    assert helper("get_alert_id")(alert) == "fabrice-olinga-orders-strictlytoohigh-metricagent"
    assert helper("get_alert_group")(alert) == "fabrice-olinga"
    assert helper("get_alert_expression")(alert) == 'orders{job="fabrice-olinga"}>10'
    assert helper("get_alert_summary")(alert) == (
        "Alert fabrice-olinga_orders_StrictlyTooHigh StrictlyTooHigh on fabrice-olinga"
    )


def test_custom_alert_fields():
    assert helper("get_alert_name")(CUSTOM_ALERT) == "High_Latency"
    assert helper("get_alert_id")(CUSTOM_ALERT) == "high-latency-custom"
    assert helper("get_alert_group")(CUSTOM_ALERT) == "custom"
    assert helper("get_alert_expression")(CUSTOM_ALERT) == "up == 0"
    assert helper("get_alert_summary")(CUSTOM_ALERT) == "Service down"
