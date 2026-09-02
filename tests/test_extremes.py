import json
import unittest
from pathlib import Path

class CleanExtremesTests(unittest.TestCase):
    def test_required_data(self):
        root=Path(__file__).resolve().parents[1]
        ctx=json.loads((root/'data'/'market_context.json').read_text())
        hist=json.loads((root/'data'/'history.json').read_text())
        self.assertTrue(ctx.get('market_date'))
        self.assertIsInstance(ctx.get('breadth'),dict)
        self.assertIsInstance(hist.get('breadth'),list)
        self.assertIsInstance(hist.get('market'),list)
        self.assertGreater(len(hist.get('breadth',[])),40)
        self.assertGreater(len(hist.get('market',[])),80)

if __name__=='__main__':unittest.main()
