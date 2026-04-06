from django.test import Client, TestCase


class HealthApiTests(TestCase):
    def test_health_returns_ok(self) -> None:
        r = Client().get("/api/health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("hl7", data)
        self.assertIn("ingest", data)
