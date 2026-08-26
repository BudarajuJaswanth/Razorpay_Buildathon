import unittest
from pydantic import ValidationError
from guardrails import PaymentProposal, get_product, get_catalog_summary, CATALOG, get_stage1_price, get_stage2_price


class TestGuardrails(unittest.TestCase):
    def test_valid_proposal_within_range(self):
        """A price between floor and retail should pass through unchanged."""
        p = CATALOG["PROD_001"]
        mid = (p["floor_price"] + p["retail_price"]) / 2
        proposal = PaymentProposal(product_id="PROD_001", proposed_price=mid)
        final_price = proposal.validate_and_compute_final_price()
        self.assertEqual(final_price, mid)

    def test_lowball_proposal_clamps_to_floor(self):
        """A price below floor should be clamped to the floor price."""
        proposal = PaymentProposal(product_id="PROD_002", proposed_price=1000.0)
        final_price = proposal.validate_and_compute_final_price()
        self.assertEqual(final_price, CATALOG["PROD_002"]["floor_price"])

    def test_invalid_product_id_raises(self):
        """An unknown product_id should raise a ValidationError."""
        with self.assertRaises(ValidationError):
            PaymentProposal(product_id="PROD_XYZ", proposed_price=1000.0)

    def test_high_proposal_clamps_to_retail(self):
        """A price above retail should be clamped to the retail price."""
        proposal = PaymentProposal(product_id="PROD_003", proposed_price=99999.0)
        final_price = proposal.validate_and_compute_final_price()
        self.assertEqual(final_price, CATALOG["PROD_003"]["retail_price"])

    def test_stage1_price_is_two_percent_off_retail(self):
        """Stage 1 price should be exactly 98% of retail price."""
        for prod_id in CATALOG:
            retail = CATALOG[prod_id]["retail_price"]
            expected = round(retail * 0.98, 2)
            self.assertAlmostEqual(get_stage1_price(prod_id), expected, places=2)

    def test_stage2_price_is_five_percent_off_retail(self):
        """Stage 2 price should be exactly 95% of retail price."""
        for prod_id in CATALOG:
            retail = CATALOG[prod_id]["retail_price"]
            expected = round(retail * 0.95, 2)
            self.assertAlmostEqual(get_stage2_price(prod_id), expected, places=2)

    def test_is_below_floor(self):
        """is_below_floor() should return True for sub-floor proposals."""
        proposal_low = PaymentProposal(product_id="PROD_001", proposed_price=1.0)
        self.assertTrue(proposal_low.is_below_floor())
        proposal_ok = PaymentProposal(product_id="PROD_001", proposed_price=CATALOG["PROD_001"]["floor_price"])
        self.assertFalse(proposal_ok.is_below_floor())


if __name__ == "__main__":
    unittest.main()
