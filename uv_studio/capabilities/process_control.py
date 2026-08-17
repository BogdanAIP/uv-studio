"""Cooperative cancellation and bounded process termination for local capability tools."""

from __future__ import annotations

import subprocess
import time
from threading import Event
from typing import Any

from .execution import CapabilityExecutionCancelled


class CancellationToken:
    """Thread-safe one-way cancellation signal shared by a capability job and adapter."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise CapabilityExecutionCancelled("capability execution was cancelled")


class CancellableProcessRunner:
    """`subprocess.run`-compatible runner that can terminate a live child process.

    UV Studio adapters already inject a runner for deterministic tests. Production
    cancellable jobs replace that runner with this object for the duration of one
    request, preserving argv/shell=False contracts while gaining process-level stop.
    """

    def __init__(
        self,
        cancellation: CancellationToken,
        *,
        poll_interval_sec: float = 0.05,
        termination_grace_sec: float = 2.0,
    ) -> None:
        if poll_interval_sec <= 0:
            raise ValueError("poll_interval_sec must be positive")
        if termination_grace_sec < 0:
            raise ValueError("termination_grace_sec must be non-negative")
        self.cancellation = cancellation
        self.poll_interval_sec = poll_interval_sec
        self.termination_grace_sec = termination_grace_sec

    @staticmethod
    def _stop_process(
        process: subprocess.Popen[str],
        *,
        grace_sec: float,
    ) -> tuple[str | None, str | None]:
        if process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
        try:
            return process.communicate(timeout=grace_sec)
        except subprocess.TimeoutExpired:
            if process.poll() is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            return process.communicate()

    def __call__(
        self,
        command: list[str],
        *,
        check: bool = False,
        capture_output: bool = False,
        text: bool = False,
        timeout: float | None = None,
        shell: bool = False,
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        if shell:
            raise ValueError("cancellable local process runner requires shell=False")
        if capture_output and ("stdout" in kwargs or "stderr" in kwargs):
            raise ValueError("stdout/stderr may not be combined with capture_output=True")
        self.cancellation.raise_if_cancelled()

        popen_kwargs = dict(kwargs)
        if capture_output:
            popen_kwargs["stdout"] = subprocess.PIPE
            popen_kwargs["stderr"] = subprocess.PIPE
        process = subprocess.Popen(
            command,
            text=text,
            shell=False,
            **popen_kwargs,
        )
        started = time.monotonic()

        while True:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                completed = subprocess.CompletedProcess(
                    command,
                    process.returncode,
                    stdout,
                    stderr,
                )
                if check and completed.returncode != 0:
                    raise subprocess.CalledProcessError(
                        completed.returncode,
                        command,
                        output=stdout,
                        stderr=stderr,
                    )
                return completed

            if self.cancellation.is_cancelled:
                self._stop_process(process, grace_sec=self.termination_grace_sec)
                raise CapabilityExecutionCancelled("capability execution was cancelled")

            wait_for = self.poll_interval_sec
            if timeout is not None:
                elapsed = time.monotonic() - started
                remaining = timeout - elapsed
                if remaining <= 0:
                    stdout, stderr = self._stop_process(
                        process,
                        grace_sec=self.termination_grace_sec,
                    )
                    raise subprocess.TimeoutExpired(
                        command,
                        timeout,
                        output=stdout,
                        stderr=stderr,
                    )
                wait_for = min(wait_for, remaining)

            try:
                stdout, stderr = process.communicate(timeout=wait_for)
            except subprocess.TimeoutExpired:
                continue

            completed = subprocess.CompletedProcess(
                command,
                process.returncode,
                stdout,
                stderr,
            )
            if check and completed.returncode != 0:
                raise subprocess.CalledProcessError(
                    completed.returncode,
                    command,
                    output=stdout,
                    stderr=stderr,
                )
            return completed
