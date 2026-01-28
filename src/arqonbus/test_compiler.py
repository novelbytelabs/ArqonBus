
import unittest
from unittest.mock import MagicMock, patch
from arqonbus.compiler import RLMCompiler, HolonomyVerdict
from arqonbus.holonomy import engine

class TestRLMCompiler(unittest.TestCase):

    @patch("arqonbus.compiler.OpenAI")
    def test_compiler_success(self, mock_openai):
        # Mock LLM Response
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = """
        {
            "entities": {"Alice": 0, "Manager": 1, "Bob": 2},
            "triplets": [[0, 0, 1], [2, 1, 1]]
        }
        """
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        # Initialize Compiler
        compiler = RLMCompiler()
        
        # Mock Engine to accept everything
        with patch.object(engine, 'verify_triplet', return_value=HolonomyVerdict.CONSISTENT):
            result = compiler.compile("Alice is Manager. Bob is not.")
            
            self.assertEqual(result["status"], "SUCCESS")
            self.assertEqual(len(result["triplets"]), 2)
            print("✅ Test 1 Passed: Happy Path")

    @patch("arqonbus.compiler.OpenAI")
    def test_compiler_reflection(self, mock_openai):
        # Mock LLM Responses (Sequence: Fail then Fix)
        mock_client = MagicMock()
        
        # Response 1: Contradiction (0 != 0) - This is just an example of a bad triplet
        resp1 = MagicMock()
        resp1.choices[0].message.content = '{"entities": {"A": 0}, "triplets": [[0, 1, 0]]}'
        
        # Response 2: Fix (0 == 0)
        resp2 = MagicMock()
        resp2.choices[0].message.content = '{"entities": {"A": 0}, "triplets": [[0, 0, 0]]}'
        
        mock_client.chat.completions.create.side_effect = [resp1, resp2]
        mock_openai.return_value = mock_client

        # Initialize Compiler
        compiler = RLMCompiler()
        
        # Mock Engine: First Call REJECT, Second Call ACCEPT
        # Strategy: verify_triplet is called for each triplet.
        # Call 1 (0,1,0) -> REJECT
        # Call 2 (0,0,0) -> ACCEPT
        
        def side_effect(u, v, w):
            if w == 1 and u == v: return HolonomyVerdict.CONTRADICTION
            return HolonomyVerdict.CONSISTENT
            
        with patch.object(engine, 'verify_triplet', side_effect=side_effect):
            result = compiler.compile("A is confused.")
            
            self.assertEqual(result["status"], "SUCCESS")
            self.assertEqual(mock_client.chat.completions.create.call_count, 2)
            print(f"✅ Test 2 Passed: Reflection Triggered ({mock_client.chat.completions.create.call_count} calls)")

if __name__ == "__main__":
    unittest.main()
