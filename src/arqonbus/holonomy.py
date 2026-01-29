"""
The Topological Truth Engine (Phase 7).
Connects ArqonBus to the high-performance Rust Sentinel kernel.

Architecture:
- Kernel: Rust `ParityDSU` (Pure Math, O(1))
- Bridge: `arqon_sentinel` (PyO3)
- Interface: `TruthEngine` (State Management)
"""
import logging
import json
import os
from typing import List, Tuple, Dict, Any
from enum import Enum
import arqon_sentinel
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default Size: 64k nodes (resonates with N=64 architecture)
DEFAULT_WORLD_SIZE = 65536 

class HolonomyVerdict(Enum):
    CONSISTENT = "CONSISTENT"
    CONTRADICTION = "CONTRADICTION" # The Lie
    AMBIGUOUS = "AMBIGUOUS"         # Missing context
    ERROR = "ERROR"
    REDUNDANT = "REDUNDANT"         # Already known relationship

@dataclass
class Triplet:
    subject: int
    relation_parity: int # 0 or 1
    object: int

class TruthEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TruthEngine, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """Initialize the Rust Kernel."""
        try:
            logger.info("Initializing Topological Truth Engine...")
            self.state_path = "truth_state.json"
            
            # Entity Registry: name -> id mapping
            self.entity_registry: Dict[str, int] = {}
            self.id_to_name: Dict[int, str] = {}
            self.next_entity_id = 1
            
            # Assertions Log: list of (u_id, v_id, parity) tuples
            self.assertions: List[Tuple[int, int, int]] = [] # Track all assertions for replay/persistence
            
            # The Rust Kernel (ParityDSU)
            self.kernel = arqon_sentinel.ParityDSU(DEFAULT_WORLD_SIZE) # Initialize with default size
            
            # Try to load Python state and replay assertions
            self._load_state()

            # The Ingest Gate (Regex/Heuristic) - Optional/Legacy
            self.gate = arqon_sentinel.CriticGate(0.1, 1)
            
            logger.info("✅ Topological Truth Engine Online (Rust Native).")
        except Exception as e:
            logger.critical(f"❌ Failed to load Rust Kernel or initialize: {e}")
            self.kernel = None
            self.gate = None

    def _save_state(self):
        """Save the Python-side state (entities, assertions) to a JSON file."""
        if not self.kernel:
            logger.warning("Kernel not initialized, cannot save state.")
            return False
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "entities": self.entity_registry,
                    "id_to_name": {str(k): v for k, v in self.id_to_name.items()}, # Convert int keys to str for JSON
                    "next_entity_id": self.next_entity_id,
                    "assertions": self.assertions
                }, f, indent=2)
            logger.info(f"✅ Python state saved to {self.state_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save Python state: {e}")
            return False

    def _load_state(self):
        """Load the Python-side state from a JSON file and replay assertions into the kernel."""
        if not os.path.exists(self.state_path):
            logger.info(f"No Python state file found at {self.state_path}. Starting fresh.")
            return

        try:
            with open(self.state_path, "r") as f:
                data = json.load(f)
                self.entity_registry = data.get("entities", {})
                self.id_to_name = {int(k): v for k, v in data.get("id_to_name", {}).items()}
                self.next_entity_id = data.get("next_entity_id", 1)
                self.assertions = data.get("assertions", [])
                
                # Replay assertions into the DSU kernel
                for u_id, v_id, parity in self.assertions:
                    # Use the kernel's union method for replay, as it handles redundancy
                    self.kernel.union(u_id, v_id, parity) 
                logger.info(f"Loaded {len(self.assertions)} assertions from {self.state_path} and replayed into kernel.")
        except Exception as e:
            logger.error(f"❌ Failed to load Python state from {self.state_path}: {e}")
            # If loading fails, reset to a fresh state to avoid corrupted data
            self.entity_registry = {}
            self.id_to_name = {}
            self.next_entity_id = 1
            self.assertions = []
            self.kernel = arqon_sentinel.ParityDSU(DEFAULT_WORLD_SIZE) # Re-initialize kernel

    def get_or_create_entity(self, name: str) -> int:
        """Get ID for entity name, creating if new. Case-insensitive."""
        name = name.lower().strip()
        if name not in self.entity_registry:
            entity_id = self.next_entity_id
            self.entity_registry[name] = entity_id
            self.id_to_name[entity_id] = name
            self.next_entity_id += 1
            self._save_state() # Save state after creating new entity
        return self.entity_registry[name]

    def add_edge(self, u_name: str, v_name: str, parity: int) -> HolonomyVerdict:
        """Add a named edge to the graph."""
        logger.info(f"Attempting to add Edge: {u_name} --({parity})--> {v_name}")
        u_id = self.get_or_create_entity(u_name)
        v_id = self.get_or_create_entity(v_name)
        
        if not self.kernel:
            return HolonomyVerdict.ERROR

        try:
            # Atomic Check-and-Insert
            # Rust `union` returns False if it contradicts known facts.
            # Returns True if it's new (integrated) or redundant (already true).
            success = self.kernel.union(u_id, v_id, parity)
            
            if success:
                # Check if this assertion is truly new or redundant
                # A more robust check would involve querying the kernel for the current relationship
                # For simplicity, we'll assume if union returns True, it was either new or consistent.
                # We'll add it to assertions if it's not already there (simple check)
                if (u_id, v_id, parity) not in self.assertions:
                    self.assertions.append((u_id, v_id, parity))
                    self._save_state() # Persist instantly if new assertion
                    logger.info(f"Edge Integrated. Total Assertions: {len(self.assertions)}")
                    return HolonomyVerdict.CONSISTENT
                else:
                    logger.info(f"Edge is redundant (already known). Total Assertions: {len(self.assertions)}")
                    return HolonomyVerdict.REDUNDANT
            else:
                logger.warning(f"Edge Rejected: {HolonomyVerdict.CONTRADICTION}")
                return HolonomyVerdict.CONTRADICTION
                
        except Exception as e:
            logger.error(f"Kernel Error during add_edge: {e}")
            return HolonomyVerdict.ERROR

    def get_graph(self) -> Dict:
        """Export graph for visualization."""
        nodes = [
            {"id": str(eid), "name": name, "val": 1} 
            for name, eid in self.entity_registry.items()
        ]
        links = [
            {
                "source": str(u),
                "target": str(v),
                "parity": p,
                "color": "#00ff88" if p == 0 else "#ff4444"
            }
            for u, v, p in self.assertions
        ]
        return {"nodes": nodes, "links": links}

    def save_state(self, path: str = "truth_snapshot.json"):
        """Save the current Truth Topology to disk."""
        if self.kernel:
            try:
                self.kernel.save_snapshot(path)
                logger.info(f"✅ State saved to {path}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to save state: {e}")
                return False
        return False

    def verify_triplet(self, u: int, v: int, parity: int) -> HolonomyVerdict:
        """
        Verify if a new triplet is consistent with the current World Topology.
        
        Args:
            u: Subject Element ID
            v: Object Element ID
            parity: 0 (Equivalent/Consistent) or 1 (Opposite/Different)
            
        Returns:
            - CONSISTENT: Fits the topology (and is now ALREADY integrated!)
            - CONTRADICTION: Creates a topological defect (Lie).
                             The integration is REJECTED by the kernel.
        """
        if not self.kernel:
            return HolonomyVerdict.ERROR

        try:
            # Atomic Check-and-Insert
            # Rust `union` returns False if it contradicts known facts.
            # Returns True if it's new (integrated) or redundant (already true).
            success = self.kernel.union(u, v, parity)
            
            if success:
                return HolonomyVerdict.CONSISTENT
            else:
                return HolonomyVerdict.CONTRADICTION
                
        except Exception as e:
            logger.error(f"Kernel Error: {e}")
            return HolonomyVerdict.ERROR

    def get_canonical(self, u: int) -> Tuple[int, int]:
        """
        Get the canonical Root and Parity for an entity.
        Useful for resolving aliases (e.g., Apple == AAPL).
        """
        if not self.kernel:
            return (u, 0)
        return self.kernel.find(u)
    
    def reset(self):
        """Hard reset the engine state."""
        logger.warning("HARD RESET TRIGGERED: Clearing all topological state.")
        self.entity_registry = {}
        self.id_to_name = {}
        self.next_entity_id = 1
        self.assertions = []
        self.kernel = arqon_sentinel.ParityDSU(DEFAULT_WORLD_SIZE)
        if os.path.exists(self.state_path):
            os.remove(self.state_path)
            logger.info("Deleted persisted state file.")
        logger.info("Engine state reset to 0.")
        return True

    def resolve_entities_from_text(self, text: str) -> Dict[str, list[str]]:
        """
        Extract known entities and identify 'rogue' (unknown) capitalized tokens.
        """
        import re
        
        # 1. Find Known Entities
        found_known = []
        clean_text = text # For rogue detection
        for name in sorted(self.entity_registry.keys(), key=len, reverse=True):
            pattern = rf"\b{re.escape(name)}\b"
            if re.search(pattern, text, re.IGNORECASE):
                found_known.append(name)
                # Remove from clean_text to find rogues later
                clean_text = re.sub(pattern, " ", clean_text, flags=re.IGNORECASE)
        
        # 2. Find Rogue Tokens (Unknown Capitalized Words / Proper Nouns)
        # We look for Capitalized words that aren't at the very start of the sentence
        # or are clearly nouns in a list.
        rogues = []
        # Candidates: Any word starting with Capital, excluding common filler.
        stop_words = {"is", "are", "the", "and", "part", "of", "in", "by", "if", "asked", "question"}
        potential_rogues = re.findall(rf"\b[A-Z][a-z]+\b", text)
        
        for p in potential_rogues:
            p_lower = p.lower()
            if p_lower not in self.entity_registry and p_lower not in stop_words:
                rogues.append(p_lower)
        
        return {
            "known": list(dict.fromkeys(found_known)),
            "rogue": list(dict.fromkeys(rogues))
        }

    def query_relationship(self, u_name: str, v_name: str) -> Dict[str, Any]:
        """
        Query relationship. Case-insensitive.
        """
        u_name = u_name.lower().strip()
        v_name = v_name.lower().strip()
        
        if u_name not in self.entity_registry or v_name not in self.entity_registry:
            return {"relation": "UNKNOWN", "verdict": HolonomyVerdict.AMBIGUOUS.value}
        
        u_id = self.entity_registry[u_name]
        v_id = self.entity_registry[v_name]
        
        u_root, u_parity = self.get_canonical(u_id)
        v_root, v_parity = self.get_canonical(v_id)
        
        if u_root != v_root:
            return {"relation": "UNKNOWN", "verdict": HolonomyVerdict.AMBIGUOUS.value}
        
        # If they share a root, the parity between them is u_parity ^ v_parity
        rel_parity = u_parity ^ v_parity
        relation = "EQUIVALENT" if rel_parity == 0 else "OPPOSITE"
        
        return {
            "relation": relation,
            "verdict": HolonomyVerdict.CONSISTENT.value,
            "u_root": self.id_to_name.get(u_root, str(u_root)),
            "rel_parity": rel_parity
        }

# Global Singleton
engine = TruthEngine()

def verify(u: int, v: int, parity: int) -> HolonomyVerdict:
    return engine.verify_triplet(u, v, parity)
