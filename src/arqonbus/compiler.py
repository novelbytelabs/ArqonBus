"""
The Recursive Language Model (RLM) Compiler.
Phase 7, Step 2: The Interface.

Translates Natural Language -> Topological Triplets.
Protocol: Decompose -> Solve (Extract) -> Verify (Kernel) -> Reflect.
"""
import os
import json
import logging
from typing import Dict, Any
from openai import OpenAI

from .holonomy import engine, HolonomyVerdict

logger = logging.getLogger(__name__)

# --- PROMPTS ---

SYSTEM_PROMPT = """You are the Arqon RLM Compiler, a precise topological logic extractor.
Your goal is to translate Natural Language logic into Topological Triplets.
A Triplet is: (Subject_ID, Parity, Object_ID)
- Parity 0: Equivalent / Consistent / Same Group / Identity
- Parity 1: Opposite / Inconsistent / Different Group / Negation

You MUST output valid, parseable JSON only. Do not provide explanations or preamble.
"""

DECOMPOSE_PROMPT = """
Analyze the text and extract ALL factual claims as a unified topological graph.
Each claim MUST be translated into a triplet: [Subject_ID, Parity, Object_ID].

STRICT RULES:
1. Extract EVERY entity mentioned (e.g., in a list like "Alice, Bob, and Ash", extract all three).
2. Entities: Create a unique integer ID for every distinct entity name. Use lowercase names as keys.
3. Parity: 0 for "is a/same as", 1 for "is not/different from".
4. If a sentence has multiple subjects for one object (e.g., "X and Y are Z"), create TWO triplets: [X, 0, Z] and [Y, 0, Z].

Input: "{text}"

Output Format:
{{
    "entities": {{ "entity_name": ID, ... }},
    "triplets": [ [ID, Parity, ID], ... ]
}}
"""

REFLECT_PROMPT = """
The Knowledge Kernel REJECTED your proposed triplets because they create a contradiction (Lie).
The following triplet failed: {failed_triplet}

Current Logical State:
{state_summary}

Please re-analyze the text and correct the logic.
Output the corrected JSON.
"""

# --- COMPILER ---

class RLMCompiler:
    def __init__(self, model: str = None, base_url: str = None, api_key: str = None):
        # Configuration Priority: Arg > Env > Local Ollama Default
        self.model = model or os.getenv("ARQON_LLM_MODEL") or "qwen2.5-coder:14b"
        
        base_url = base_url or os.getenv("ARQON_LLM_BASE_URL") or "http://localhost:11434/v1"
        api_key = api_key or os.getenv("ARQON_LLM_API_KEY") or "ollama"
        
        logger.info(f"RLM Compiler Initialized: Model={self.model}, Base={base_url}")
        
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.max_retries = 3

    def compile(self, text: str) -> Dict[str, Any]:
        """
        Compile natural language into verified Topological Knowledge.
        Returns the final integrated Entity Map and Status.
        """
        prompt = DECOMPOSE_PROMPT.format(text=text)
        
        for attempt in range(self.max_retries):
            # 1. Generate (Solve)
            response = self._call_llm(prompt)
            try:
                data = self._parse_json(response)
                triplets = data.get("triplets", [])
                entities = data.get("entities", {})
            except Exception as e:
                logger.warning(f"JSON Parse Error (Attempt {attempt}): {e}")
                continue

            # 2. Verify (Kernel) using named edges
            id_to_name = {int(v): k for k, v in entities.items()}
            failed_triplet = None
            for t in triplets:
                # Robust parsing for t
                try:
                    if isinstance(t, list) and len(t) == 3:
                        u_id, parity, v_id = map(int, t)
                    elif isinstance(t, str) and len(t) == 3:
                        u_id, parity, v_id = int(t[0]), int(t[1]), int(t[2])
                    elif isinstance(t, list) and len(t) == 1 and isinstance(t[0], str) and len(t[0]) == 3:
                        u_id, parity, v_id = int(t[0][0]), int(t[0][1]), int(t[0][2])
                    else:
                        logger.warning(f"Skipping malformed triplet: {t}")
                        continue
                except Exception as e:
                    logger.warning(f"Failed to parse triplet {t}: {e}")
                    continue
                
                # Get entity names for graph tracking
                u_name = id_to_name.get(u_id, str(u_id))
                v_name = id_to_name.get(v_id, str(v_id))
                
                # Use add_edge which tracks named entities
                verdict = engine.add_edge(u_name, v_name, parity)
                
                if verdict == HolonomyVerdict.CONTRADICTION:
                    failed_triplet = t
                    logger.info(f"❌ Kernel Rejected: {t} (Contradiction)")
                    break
            
            # 3. Reflect or Commit
            if failed_triplet:
                # Reflection Loop
                prompt = REFLECT_PROMPT.format(
                    failed_triplet=failed_triplet,
                    state_summary="[Hidden for now]" # In future, dump DSU state
                )
                logger.info(f"🔄 Reflecting due to failure: {failed_triplet}")
                continue # Retry loop
            else:
                # Success!
                logger.info(f"✅ Compilation Successful: {len(triplets)} triplets integrated.")
                return {
                    "status": "SUCCESS",
                    "entities": entities,
                    "triplets": triplets
                }

        return {"status": "FAILED", "error": "Max retries exceeded"}

    def infer(self, question: str) -> Dict[str, Any]:
        """
        Answer a question based on topological inference.
        STRICT POLICY: Zero-LLM interaction. Pure topological lookup.
        """
        # 1. Direct Entity Lookup with Rogue Detection
        resolution_meta = engine.resolve_entities_from_text(question)
        entities = resolution_meta["known"]
        rogues = resolution_meta["rogue"]
        
        # FAIL if unknown entities (Rogues) are present
        if rogues:
            return {
                "status": "SUCCESS",
                "answer": f"UNDEFINED: Unknown entity detected: {rogues}. Please assert them before querying.",
                "resolution": {"relation": "UNKNOWN", "verdict": "AMBIGUOUS", "rogue_entities": rogues},
                "latency": "fast_path"
            }

        if len(entities) < 2:
            return {
                "status": "SUCCESS",
                "answer": f"UNDEFINED: Found only {entities if entities else 'no known entities'}. Need at least two to resolve.",
                "resolution": {"relation": "UNKNOWN", "verdict": "AMBIGUOUS", "entities_found": entities},
                "latency": "fast_path"
            }

        logger.info(f"⚡ High-Speed Oracle Query: Found {entities}")

        # 2. Multi-Entity Logic: Pairwise check against 'manager' or common groups
        target_v = entities[0] # Usually the longest/group term
        others = entities[1:]
        
        all_results = []
        for u in others:
            res = engine.query_relationship(u, target_v)
            all_results.append({"u": u, "v": target_v, "res": res})

        # 3. Aggregate Verdict
        is_contradiction = any(r["res"]["relation"] == "OPPOSITE" for r in all_results)
        is_all_equivalent = all(r["res"]["relation"] == "EQUIVALENT" for r in all_results)
        
        if is_contradiction:
            answer = f"CONTRADICTED: One or more relationships in {entities} oppose each other."
            rel = "OPPOSITE"
        elif is_all_equivalent:
            answer = f"VERIFIED: All detected identities {entities} are topologically consistent."
            rel = "EQUIVALENT"
        else:
            answer = f"INCOMPLETE: Some entities in {entities} have no direct path to {target_v}."
            rel = "UNKNOWN"
        
        return {
            "status": "SUCCESS",
            "answer": answer,
            "resolution": {
                "relation": rel,
                "verdict": "CONSISTENT" if not is_contradiction else "CONTRADICTION",
                "entities_found": entities,
                "breakdown": all_results
            },
            "latency": "fast_path"
        }

    def _call_llm(self, user_prompt: str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Call Failed: {e}")
            return "{}"

    def _parse_json(self, text: str) -> Dict[str, Any]:
        return json.loads(text)

# Global Instance (Lazy/Safe)
try:
    compiler = RLMCompiler()
except Exception:
    logger.warning("RLM Compiler not initialized (Missing API Key).")
    compiler = None
