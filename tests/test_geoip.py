import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from capture.geoip_resolver import GeoIPResolver
from capture.state import DetectionStateManager


class TestGeoIPResolver(unittest.TestCase):
    """Tests for the GeoIPResolver component."""

    def setUp(self):
        self.resolver = GeoIPResolver()
        # Force mock resolution on this test resolver instance
        self.resolver._init_reader = lambda: False

    def test_private_ip_resolution(self):
        """Verify that private and loopback IPs resolve to Red Local and empty coordinates."""
        private_ips = [
            "127.0.0.1",
            "10.0.0.1",
            "192.168.1.50",
            "172.16.0.22",
            "::1"
        ]
        for ip in private_ips:
            res = self.resolver.resolve_ip(ip)
            self.assertEqual(res["country"], "Red Local")
            self.assertEqual(res["city"], "Red de Área Local")
            self.assertIsNone(res["latitude"])
            self.assertIsNone(res["longitude"])

    def test_known_public_ips_mock(self):
        """Verify that well-known public IPs resolve to correct mock locations in fallback."""
        res_google = self.resolver.resolve_ip("8.8.8.8")
        self.assertEqual(res_google["country"], "Estados Unidos")
        self.assertEqual(res_google["city"], "Mountain View")
        self.assertEqual(res_google["latitude"], 37.4223)
        self.assertEqual(res_google["longitude"], -122.0847)

        res_cloudflare = self.resolver.resolve_ip("1.1.1.1")
        self.assertEqual(res_cloudflare["country"], "Australia")
        self.assertEqual(res_cloudflare["city"], "Research")
        self.assertEqual(res_cloudflare["latitude"], -37.7000)
        self.assertEqual(res_cloudflare["longitude"], 145.1833)

        res_quad9 = self.resolver.resolve_ip("9.9.9.9")
        self.assertEqual(res_quad9["country"], "Suiza")
        self.assertEqual(res_quad9["city"], "Ginebra")
        self.assertEqual(res_quad9["latitude"], 46.2000)
        self.assertEqual(res_quad9["longitude"], 6.1500)

    def test_generic_public_ip_mock(self):
        """Verify that any other public IP resolves deterministically to a mock location."""
        res1 = self.resolver.resolve_ip("200.44.32.1")
        res2 = self.resolver.resolve_ip("200.44.32.1")
        
        # Verify deterministic output (same IP produces identical result)
        self.assertEqual(res1, res2)
        
        # Check standard properties
        self.assertIn(res1["country"], self.resolver.mock_countries)
        self.assertIn(res1["city"], self.resolver.mock_cities)
        self.assertIsInstance(res1["latitude"], float)
        self.assertIsInstance(res1["longitude"], float)

    @patch("capture.geoip_resolver._geoip2_installed", True)
    @patch("geoip2.database.Reader")
    def test_real_database_lookup(self, mock_reader_class):
        """Verify database lookup using mocked geoip2.database.Reader."""
        # Setup mock reader instance
        mock_reader = MagicMock()
        mock_reader_class.return_return_value = mock_reader
        
        # Mock responses
        mock_city_response = MagicMock()
        mock_city_response.country.names = {"es": "Alemania"}
        mock_city_response.city.names = {"es": "Berlín"}
        mock_city_response.location.latitude = 52.5200
        mock_city_response.location.longitude = 13.4050
        
        mock_reader.city.return_value = mock_city_response
        
        # Instantiate a resolver pointing to an existing mock path to trigger database load
        with patch.object(Path, "exists", return_value=True):
            resolver = GeoIPResolver(db_path=Path("/dummy/path/GeoLite2-City.mmdb"))
            resolver._reader = mock_reader
            resolver._tried_init = True
            
            res = resolver.resolve_ip("200.100.50.4")
            
            # Verify mock was consulted
            mock_reader.city.assert_called_once_with("200.100.50.4")
            
            # Check correctness of outputs
            self.assertEqual(res["country"], "Alemania")
            self.assertEqual(res["city"], "Berlín")
            self.assertEqual(res["latitude"], 52.5200)
            self.assertEqual(res["longitude"], 13.4050)


class TestGeoIPStateIntegration(unittest.TestCase):
    """Integration tests for DetectionStateManager and GeoIPResolver."""

    @patch("app.db.supabase_client.get_client")
    def test_state_alert_enrichment(self, mock_get_client):
        """Verify that triggered alerts are successfully decorated with GeoIP details."""
        # Prevent database call and config fetching
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        state = DetectionStateManager()
        state._refresh_configs_if_needed = lambda: None
        # Force mock resolution on the state resolver instance for test isolation
        state.geoip._init_reader = lambda: False
        
        # Set low thresholds for test
        state.configs["dos_threshold"] = {"packets_per_second": 2}
        
        # Construct packets from a public IP to trigger an alert
        pkt1 = {
            "timestamp": "2026-05-20T22:00:00.000Z",
            "src_ip": "8.8.8.8",
            "dst_ip": "192.168.1.1",
            "protocol": "TCP",
            "src_port": 12345,
            "dst_port": 80,
            "length": 64
        }
        pkt2 = pkt1.copy()
        pkt3 = pkt1.copy()
        
        # Insert first packet, then the second triggers DoS alert (threshold >= 2 pps)
        state.process_packet(pkt1)
        alerts = state.process_packet(pkt2)
        
        # Verify one alert triggered and enriched with GeoIP
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        
        self.assertEqual(alert["threat_type"], "dos")
        self.assertEqual(alert["country"], "Estados Unidos")
        self.assertEqual(alert["city"], "Mountain View")
        self.assertEqual(alert["latitude"], 37.4223)
        self.assertEqual(alert["longitude"], -122.0847)
        
        # Verify database insert payload was enriched as well
        mock_client.table.assert_called_with("alerts")
        mock_client.table().insert.assert_called_once()
        inserted_payload = mock_client.table().insert.call_args[0][0]
        
        self.assertEqual(inserted_payload["country"], "Estados Unidos")
        self.assertEqual(inserted_payload["city"], "Mountain View")
        self.assertEqual(inserted_payload["latitude"], 37.4223)
        self.assertEqual(inserted_payload["longitude"], -122.0847)
