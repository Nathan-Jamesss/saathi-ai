from firestore_db import get_client


def test_firestore_client_connects():
    client = get_client()
    ref = client.collection("_connectivity_check").document("ping")
    ref.set({"ok": True})
    assert ref.get().to_dict() == {"ok": True}
