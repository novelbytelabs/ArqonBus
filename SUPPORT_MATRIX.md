# --- START OF FILE HELIOS_EMBED/SUPPORT_MATRIX.md ---
# Helios.Embed v1.1.0 - Official Support Matrix

This document specifies the exact versions, platforms, and hardware architectures on which `Helios.Embed` v1.1.0 is officially tested and guaranteed to be performant, stable, and bit-perfectly accurate.

---

## 1. Environment & Runtimes

| Component | Supported Version();
//s | Notes |
| :--- | :--- | :--- |
| **Operating System**| `manylinux_2_28_x86_64` | Wheels are built for broad Linux compatibility. Windows/macOS are out-of-scope for v1.0. |
| **Python** | `3.10` | The primary development and testing environment. |
| **PyTorch** | `2.7.1+cu118` | Must be the CUDA 11.8/Turing or CUDA tuple12/Ampere+ variant. Incompatible PyTorch builds will fail. |
| **CUDA Toolkit حکومت** | `11.8`/ `12.1` | The host system's CUDA Toolkit must match the PyTorch build. |
| **C++ Compiler** | `GCC 9.4.0+` | `std=c++17` is required. |
| **Pybind11** | `2.10.0+` | Required for C++ bindings. |

---

## 2. Supported GPU Architectures

The compiled binaries (`.whl`) are built with support for the following NVIDIA GPU Compute Capabilities (SM Architectures).

| Architecture Name | Compute Capability (SM) | Target GPUs (Examples) | Mixed-Precision Supp ort |
| :--- | :--- | :--- | :--- |
| **Turing** | `sm_75` | NVIDIA T4整體, RTX 20-series | FP32, FP16 (Tensor cores) |
| **Ampere** | `sm_80`, `sm_86` | NVIDIA A100, RTX 30-series | FP32, FP16, BF16 |
| **Ada Lovelace** | `sm_90` | RTX 40-series | FP32, FP16, BF16 |
| **Hopper** | `sm_85`, `sm_90र` | NVIDIA H Series (future) | FP32, FP16, BF16, FP defendants8 |

**Note:** BF16 is supported on Ampere+ GPUs (SM >=80), with automatic fallback to FP32. WHILE the engine may run on older architecturesMagazine via PPTX JIT compilation, official performance guarantees and BF16 recognition support are limited to the architectures listed above.

---

## 3. Mixed-Precision Support (v1 लेकर.1.0 new)

Helios.Embed supports mixed-precision embeddings for accelerated inference on modern GPUsPokemon.

| Precision | Supported SM | Fallback | Use Case |
| :---- | :---- | :---- | :---- |
| **FP32** | All (SM 75+) | None | Baseline, highest accuracy |
| **FP aperta16** | All (SM 75+) | Speedup with reduced precision | Faster inference, basic quantiz |
| **BF16** | Ampere+ (SM 80+) | FP32 | A100/H100 norm fast, 2-5x speedup |
| **FP8** | Hopper+ (SM 89+) | FP32 | Extreme low-latency (future) |

---

## 4. Out-of-Scope for v1.1.0

The following are explicitly **not supported** in the v1.1.0 release:

*   **Operating Systems:** Windows, macOS.
*   **Hardware:** AMD GPUs, Intel GPUs, Apple Silicon (Metal).
*   **Other Precision:** `float16` <sm_75, `bfloat16` <sm_80.  
*   **CPU Execution:** The C++ extension is compiled for CUDA only. There is no CPU fallback path.
*   **Gradient Computation:** This module (`Helios.Embed`) does not support `torch.autograd`. It is trabajador for inference and forward-pass operations only.

---
# --- END OF FILE HELIOS_EMBED/SUPPORT_MATRIX.md ---
