from __future__ import annotations

import subprocess
import sys
import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import runtime_asset_installer as installer
from audio_core import CommandCancelled, command_cancellation, run_bounded_command
from sound_separator_app import SoundSeparatorApp, run_worker_command
from runtime_integrity import runtime_tree_fingerprint


class JobCancellationTests(unittest.TestCase):
    def test_cancellation_interrupts_runtime_inventory_before_hashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "file.txt").write_text("fixture", encoding="utf-8")

            def cancel(*_args):
                raise CommandCancelled("cancelled")

            with self.assertRaises(CommandCancelled):
                runtime_tree_fingerprint(root, cancel)

    def test_cancelled_job_does_not_launch_a_process(self):
        event = threading.Event()
        event.set()
        with patch("subprocess.Popen") as spawn:
            with self.assertRaises(CommandCancelled):
                run_worker_command([sys.executable, "-c", "pass"], print, cancel_event=event)
            with self.assertRaises(CommandCancelled):
                with command_cancellation(event):
                    run_bounded_command([sys.executable, "-c", "pass"], timeout=10)
        spawn.assert_not_called()

    def test_cancellation_stops_a_running_worker(self):
        event = threading.Event()
        processes = []
        real_spawn = subprocess.Popen

        def spawn(*args, **kwargs):
            process = real_spawn(*args, **kwargs)
            processes.append(process)
            return process

        with patch("subprocess.Popen", side_effect=spawn):
            with self.assertRaises(CommandCancelled):
                run_worker_command(
                    [sys.executable, "-u", "-c", "import time; print('ready'); time.sleep(30)"],
                    lambda line: event.set(), cancel_event=event,
                )
        self.assertIsNotNone(processes[0].poll())

    def test_cancellation_stops_a_media_command_and_restores_context(self):
        event = threading.Event()
        processes = []
        real_spawn = subprocess.Popen

        def spawn(*args, **kwargs):
            process = real_spawn(*args, **kwargs)
            processes.append(process)
            event.set()
            return process

        with patch("subprocess.Popen", side_effect=spawn):
            with self.assertRaises(CommandCancelled):
                with command_cancellation(event):
                    run_bounded_command([sys.executable, "-c", "import time; time.sleep(30)"], timeout=10)
        self.assertIsNotNone(processes[0].poll())
        result = run_bounded_command([sys.executable, "-c", "print('ok')"], timeout=10)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_close_waits_for_background_cleanup_before_destroying_window(self):
        app = object.__new__(SoundSeparatorApp)
        app.closing = False
        app.cancel_event = threading.Event()
        app.background_thread = MagicMock()
        app.background_thread.is_alive.return_value = True
        app.volume_restart_after_id = None
        app._set_status = MagicMock()
        app.stop_preview = MagicMock()
        app.after = MagicMock()
        with patch("sound_separator_app.tk.Tk.destroy") as close:
            app.destroy()
            self.assertTrue(app.cancel_event.is_set())
            self.assertTrue(app.closing)
            close.assert_not_called()
            app.after.assert_called_once()
            app.background_thread.is_alive.return_value = False
            app._finish_close()
            close.assert_called_once()


class InstallerLifecycleTests(unittest.TestCase):
    def make_window(self):
        window = object.__new__(installer.InstallerWindow)
        window.install_running = False
        window.install_finished = False
        window.accepted = MagicMock()
        window.accepted.get.return_value = True
        window.button = MagicMock()
        window.accept_check = MagicMock()
        window.progress = MagicMock()
        window._set_status = MagicMock()
        window._ui = lambda key: key
        window.language = MagicMock()
        window.language.get.return_value = "en"
        window.messagebox = MagicMock()
        return window

    def test_reaccepting_terms_cannot_start_a_second_install(self):
        window = self.make_window()
        with patch.object(installer.threading, "Thread") as thread:
            window.start()
            window.accepted.get.return_value = False
            window._update_button_state()
            window.accepted.get.return_value = True
            window._update_button_state()
            self.assertEqual(window.button.configure.call_args.kwargs["state"], "disabled")
            window.start()
            thread.return_value.start.assert_called_once()

    def test_failed_install_can_retry_and_finished_install_cannot_restart(self):
        window = self.make_window()
        with patch.object(installer.threading, "Thread") as thread:
            window.start()
            window._failed("test failure")
            self.assertFalse(window.install_running)
            self.assertEqual(window.button.configure.call_args.kwargs["state"], "normal")
            window.start()
            self.assertEqual(thread.return_value.start.call_count, 2)
            window.window = MagicMock()
            window._completed()
            window.start()
            self.assertEqual(thread.return_value.start.call_count, 2)
