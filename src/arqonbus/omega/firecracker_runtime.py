"""Firecracker runtime integration for Tier-Omega substrates."""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


@dataclass
class FirecrackerVM:
    vm_id: str
    substrate_id: str
    api_socket: str
    config_path: str
    log_path: str
    pid: int
    started_at: str
    status: str = "running"


class FirecrackerOmegaRuntime:
    """Process-backed Firecracker runtime with bounded VM management."""

    def __init__(self, cfg: Any):
        self._cfg = cfg
        self._workspace = Path(cfg.workspace_dir)
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._vms: Dict[str, FirecrackerVM] = {}
        self._lock = asyncio.Lock()

    def _bin_available(self) -> bool:
        return shutil.which(self._cfg.firecracker_bin) is not None

    def snapshot(self) -> Dict[str, Any]:
        kernel_exists = bool(self._cfg.kernel_image) and Path(self._cfg.kernel_image).exists()
        rootfs_exists = bool(self._cfg.rootfs_image) and Path(self._cfg.rootfs_image).exists()
        return {
            "runtime": self._cfg.runtime,
            "firecracker_bin": self._cfg.firecracker_bin,
            "bin_available": self._bin_available(),
            "kernel_image": self._cfg.kernel_image,
            "kernel_exists": kernel_exists,
            "rootfs_image": self._cfg.rootfs_image,
            "rootfs_exists": rootfs_exists,
            "workspace_dir": str(self._workspace),
            "vm_count": len(self._vms),
            "max_vms": int(self._cfg.max_vms),
            "ready": self._bin_available() and kernel_exists and rootfs_exists,
        }

    def _assert_ready(self) -> None:
        snap = self.snapshot()
        if not snap["bin_available"]:
            raise RuntimeError(
                f"Firecracker binary not found on PATH: {self._cfg.firecracker_bin}"
            )
        if not snap["kernel_exists"]:
            raise RuntimeError(
                f"Firecracker kernel image missing: {self._cfg.kernel_image}"
            )
        if not snap["rootfs_exists"]:
            raise RuntimeError(
                f"Firecracker rootfs image missing: {self._cfg.rootfs_image}"
            )

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def launch_vm(self, substrate_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        async with self._lock:
            self._assert_ready()
            max_vms = max(1, int(self._cfg.max_vms))
            if len(self._vms) >= max_vms:
                raise RuntimeError("Tier-Omega Firecracker VM limit reached")

            vm_id = f"fc_{uuid.uuid4().hex[:12]}"
            vm_dir = self._workspace / vm_id
            vm_dir.mkdir(parents=True, exist_ok=True)
            api_socket = vm_dir / "firecracker.sock"
            config_path = vm_dir / "firecracker.json"
            log_path = vm_dir / "firecracker.log"

            vcpu_count = int(metadata.get("vcpu_count", 1))
            mem_size_mib = int(metadata.get("mem_size_mib", 256))
            if vcpu_count < 1:
                raise ValueError("'vcpu_count' must be >= 1")
            if mem_size_mib < 128:
                raise ValueError("'mem_size_mib' must be >= 128")

            config = {
                "boot-source": {
                    "kernel_image_path": self._cfg.kernel_image,
                    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off",
                },
                "drives": [
                    {
                        "drive_id": "rootfs",
                        "path_on_host": self._cfg.rootfs_image,
                        "is_root_device": True,
                        "is_read_only": False,
                    }
                ],
                "machine-config": {
                    "vcpu_count": vcpu_count,
                    "mem_size_mib": mem_size_mib,
                    "ht_enabled": False,
                },
            }
            config_path.write_text(json.dumps(config), encoding="utf-8")

            with log_path.open("ab") as log_handle:
                proc = await asyncio.create_subprocess_exec(
                    self._cfg.firecracker_bin,
                    "--api-sock",
                    str(api_socket),
                    "--config-file",
                    str(config_path),
                    stdout=log_handle,
                    stderr=log_handle,
                )
                await asyncio.sleep(0.35)
                if proc.returncode is not None:
                    raise RuntimeError(
                        f"Firecracker failed to start (exit={proc.returncode}), see {log_path}"
                    )

            vm = FirecrackerVM(
                vm_id=vm_id,
                substrate_id=substrate_id,
                api_socket=str(api_socket),
                config_path=str(config_path),
                log_path=str(log_path),
                pid=proc.pid,
                started_at=self._utc_now_iso(),
            )
            self._processes[vm_id] = proc
            self._vms[vm_id] = vm

            return {
                "vm_id": vm.vm_id,
                "substrate_id": vm.substrate_id,
                "pid": vm.pid,
                "api_socket": vm.api_socket,
                "config_path": vm.config_path,
                "log_path": vm.log_path,
                "started_at": vm.started_at,
                "status": vm.status,
            }

    async def stop_vm(self, vm_id: str) -> Dict[str, Any]:
        async with self._lock:
            vm = self._vms.get(vm_id)
            proc = self._processes.get(vm_id)
            if vm is None or proc is None:
                return {"stopped": False, "vm_id": vm_id, "reason": "not_found"}

            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=float(self._cfg.vm_timeout_seconds))
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
            vm.status = "stopped"
            self._vms.pop(vm_id, None)
            self._processes.pop(vm_id, None)
            return {"stopped": True, "vm_id": vm_id}

    async def list_vms(self) -> Dict[str, Any]:
        async with self._lock:
            payload = []
            for vm_id, vm in self._vms.items():
                proc = self._processes.get(vm_id)
                status = vm.status
                if proc is not None and proc.returncode is not None:
                    status = "exited"
                payload.append(
                    {
                        "vm_id": vm.vm_id,
                        "substrate_id": vm.substrate_id,
                        "pid": vm.pid,
                        "api_socket": vm.api_socket,
                        "started_at": vm.started_at,
                        "status": status,
                    }
                )
            return {"vms": payload, "count": len(payload)}

    async def close(self) -> None:
        async with self._lock:
            vm_ids = list(self._vms.keys())
        for vm_id in vm_ids:
            try:
                await self.stop_vm(vm_id)
            except Exception as exc:  # pragma: no cover - best effort shutdown
                logger.warning("Failed to stop Firecracker VM %s: %s", vm_id, exc)
