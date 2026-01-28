"""
The ScannerEngine: Recursive Truth Ingestion.
Part of the "Holy Grail" Architecture.
"""
import os
import logging
from typing import List, Dict, Any, Generator
from concurrent.futures import ThreadPoolExecutor
from .compiler import compiler
from .holonomy import engine

logger = logging.getLogger(__name__)

class ScannerEngine:
    def __init__(self):
        self.is_scanning = False
        self.total_files = 0
        self.processed_files = 0
        self.facts_found = 0
        self.current_file = ""
        self.executor = ThreadPoolExecutor(max_workers=4)

    def scan_path(self, root_path: str, includes: List[str] = None):
        """Recursively scan a path and ingest truth."""
        if self.is_scanning:
            logger.warning("Scan already in progress.")
            return

        if not os.path.exists(root_path):
            logger.error(f"Path does not exist: {root_path}")
            return

        self.root_path = root_path
        self.includes = includes or [".txt", ".md", ".py", ".rs", ".js", ".ts", ".tsx"]
        self.is_scanning = True
        self.processed_files = 0
        self.facts_found = 0
        
        # 1. Count files
        files_to_process = []
        for root, _, files in os.walk(root_path):
            for file in files:
                if any(file.endswith(ext) for ext in self.includes):
                    files_to_process.append(os.path.join(root, file))
        
        self.total_files = len(files_to_process)
        logger.info(f"Starting Scan: {self.total_files} files found in {root_path}")

        # 2. Process Files
        for file_path in files_to_process:
            self.current_file = file_path
            self._process_file(file_path)
            self.processed_files += 1
            logger.info(f"Progress: {self.processed_files}/{self.total_files} | Ingested: {self.facts_found}")

        self.is_scanning = False
        self.current_file = ""
        logger.info("Scan Completed Successfully.")

    def _process_file(self, file_path: str):
        """Read and compile a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # For large files, we should chunk. For now, simple compile.
            if len(content) > 4000:
                content = content[:4000] # Safety limit for toy demo

            result = compiler.compile(content)
            if result.get("status") == "SUCCESS":
                self.facts_found += len(result.get("triplets", []))
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_scanning": self.is_scanning,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "facts_found": self.facts_found,
            "current_file": self.current_file,
            "completed": not self.is_scanning and self.processed_files > 0
        }

# Global Instance
scanner = ScannerEngine()
