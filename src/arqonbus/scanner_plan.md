# Implementation Plan: Recursive Truth Scanner (`ScannerEngine`)

The goal is to implement a high-performance system that walks a local directory, extracts logical triplets from documents using the RLM Compiler, and integrates them into the Arqon Truth Graph.

## Proposed Changes

### 1. New Module: `src/arqonbus/scanner.py`
*   **Recursive Walker**: Uses `os.walk` or similar to find files.
*   **Batch Processor**: Groups documents into batches for the RLM Compiler to minimize LLM overhead.
*   **Progress Tracker**: Streams ingestion status (files processed, facts found).
*   **Protobuf Integration**: Uses `IngestionRequest` and `IngestionStatus` from `arqon.proto`.

### 2. Update Backend API: `src/arqonbus/server.py`
*   **`/ingest` (POST)**: Starts an asynchronous scanning task.
*   **`/ingest/status` (GET)**: Returns the current state of ingestion.

### 3. Update Frontend: `ArqonStudio/web` (Future)
*   **Folder Picker**: Allow users to input a local path.
*   **Progress UI**: Display the status of the ongoing ingestion.

---

## Technical Details: Batching Strategy
To stay "accurate and cost-effective," we will:
1.  Extract chunks from files (max 2000 chars).
2.  Batch 5-10 chunks into a single RLM `compile()` call.
3.  Use the `engine.add_edge()` which ensures $O(\alpha(N))$ consistency.
