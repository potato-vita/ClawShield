def test_frontend_index_is_served(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "TraceShield 安全分析工作台" in response.text
    assert "/api/module4/dashboard" in response.text
