import unittest

from starter.src.evaluation import evaluate_query


class EvidenceTest(unittest.TestCase):
    def test_ranked_alternative_and_partial_evidence(self):
        gold = dict(gold_source_id="book", gold_page=2, evidence_quote="complete evidence")
        question = dict(gold, accepted_alternatives=[dict(gold, gold_page=3, evidence_quote="other quote")])

        def hit(i, source, page, text):
            return dict(chunk_id=str(i), metadata=dict(document_id=source, page=page), text=text)

        rows = [hit(1, "book", 2, "evidence"), hit(2, "wrong", 2, "complete evidence"),
                hit(3, "book", 3, "other\n quote")]
        result = evaluate_query(question, rows)
        self.assertFalse(result["hit1"])
        self.assertTrue(result["evidence_hit3"])
        self.assertEqual([h["matched_gold_indices"] for h in result["hits"]], [[], [], [1]])
        rows[2]["metadata"]["page"] = 2
        self.assertFalse(evaluate_query(question, rows)["evidence_hit3"])
