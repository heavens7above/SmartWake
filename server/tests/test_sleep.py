def test_upload_model_rejects_non_pkl_files(client, api_key):
    response = client.post(
        "/model/upload",
        headers={"X-API-Key": api_key},
        files={"file": ("test.txt", b"dummy content", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only .pkl files are accepted."
