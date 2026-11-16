"""Pure helpers that turn an alert definition from the console into PrometheusRule fields."""


def map_expression_to_alert(expression):
    """
    Maps a comparison expression to a semantic alert label.

    :param expression: A string representing the comparison operator 
                    (e.g., "<", "<=", "!=", ">", ">=").
    :return: A string representing the semantic alert label.
    """
    mapping = {
        "<": "StrictlyTooLow",
        "≤": "TooLow",
        ">": "StrictlyTooHigh",
        "≥": "TooHigh",
        "≠": "Distinct",
        "=": "Equals",
    }
    
    return mapping.get(expression, "Unknown")

def map_expression_operator_to_comparison_operator(expression_operator):
    mapping = {
        "<": "<",
        "≤": "<=",
        ">": ">",
        "≥": ">=",
        "≠": "!=",
        "=": "==",
    }
    return mapping.get(expression_operator, "Unknown")

def extract_alert_details(alert_data):
    definition = alert_data['definition']
    agent_name = definition['agent']
    metric_name = definition['metric']
    expression_operator = definition['expression']
    semantic_expression_label = map_expression_to_alert(expression_operator)
    return agent_name, metric_name, semantic_expression_label

def get_alert_name(alert_data):
    if alert_data['scope'] == "metricAgent":
        agent_name, metric_name, semantic_expression_label = extract_alert_details(alert_data)
        return f"{agent_name}_{metric_name}_{semantic_expression_label}"
    else:
        return alert_data['name']

def get_alert_id(alert_data):
    if alert_data['scope'] == "metricAgent":
        agent_name, metric_name, semantic_expression_label = extract_alert_details(alert_data)
        alert_id = f"{agent_name}_{metric_name}_{semantic_expression_label}_{alert_data['scope']}"
        return alert_id.replace("_", "-").lower()
    else:
        return f"{alert_data['name']}_{alert_data['scope']}".replace("_", "-").lower()

def get_alert_summary(alert_data):
    if alert_data['scope'] == "metricAgent":
        agent_name, metric_name, semantic_expression_label = extract_alert_details(alert_data)
        alert_name = f"{agent_name}_{metric_name}_{semantic_expression_label}"
        return f"Alert {alert_name} {semantic_expression_label} on {agent_name}"
    else:
        return alert_data['definition']['summary']    

def get_alert_expression(alert_data):
    if alert_data['scope'] == "metricAgent":
        agent_name, metric_name, _ = extract_alert_details(alert_data)
        threshold = alert_data['definition']['value']
        comparison_operator = map_expression_operator_to_comparison_operator(alert_data['definition']['expression'])
        return f"{metric_name}{{job=\"{agent_name}\"}}{comparison_operator}{threshold}"
    else:
        return alert_data['definition']['expression']
    
def get_alert_group(alert_data):
    if alert_data['scope'] == "metricAgent":
        agent_name, _, _ = extract_alert_details(alert_data)
        return agent_name
    else:
        return "custom"
