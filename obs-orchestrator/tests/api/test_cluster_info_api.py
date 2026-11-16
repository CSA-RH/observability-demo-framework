from conftest import TEST_USER


def test_cluster_info_uses_authenticated_user(client):
    response = client.get("/api/v1/escotilla")
    assert response.status_code == 200
    body = response.json()
    assert body["Connected"] is True
    assert body["Namespace"] == f"fake-namespace-{TEST_USER}"


def test_cluster_info_publishes_namespace_layout(client):
    """The console builds user namespaces from UserNamespacePrefix instead of hardcoding obs-demo."""
    data = client.get("/api/v1/escotilla").json()
    assert data["Namespace"] == data["UserNamespacePrefix"] + "tester"
    assert data["AppNamespace"]
