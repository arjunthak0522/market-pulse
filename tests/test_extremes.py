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
    def test_clean_study_catalog(self):
        root=Path(__file__).resolve().parents[1]
        data=json.loads((root/'data'/'extreme_studies.json').read_text())
        self.assertIsInstance(data.get('studies'),list)

if __name__=='__main__':unittest.main()
