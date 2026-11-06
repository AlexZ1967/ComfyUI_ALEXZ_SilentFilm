"""Standalone Silent Film cadence and finish regression tests."""

import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch


class SilentFilmSmokeTests(unittest.TestCase):
    """Exercise the legacy cadence and finish contracts in their new package."""

    @classmethod
    def setUpClass(cls):
        package_root = Path(__file__).resolve().parents[1]
        if "ComfyUI_ALEXZ_SilentFilm" not in sys.modules:
            package = types.ModuleType("ComfyUI_ALEXZ_SilentFilm")
            package.__path__ = [str(package_root)]
            sys.modules["ComfyUI_ALEXZ_SilentFilm"] = package


    def test_video_silent_film_cadence_preserves_length_and_reduces_unique_frames(self):
        """Ensure silent-film cadence keeps 25 fps length while lowering unique motion phases."""
        video_mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        node = video_mod.VideoSilentFilmCadence()

        ramp = torch.linspace(0.0, 1.0, steps=25, dtype=torch.float32).view(25, 1, 1, 1).expand(25, 4, 4, 3)
        out_hard, payload_hard = node.apply(
            ramp,
            source_fps=25.0,
            playback_mode="preserve_duration_25fps",
            target_fps_min=16.0,
            target_fps_max=16.0,
            fps_drift_strength=0.0,
            shutter_fraction=0.0,
            motion_blur_strength=0.0,
            blur_mode="simple",
            blur_samples=1,
            seed=1925,
        )
        out_blur, payload_blur = node.apply(
            ramp,
            source_fps=25.0,
            playback_mode="preserve_duration_25fps",
            target_fps_min=16.0,
            target_fps_max=20.0,
            fps_drift_strength=0.65,
            shutter_fraction=0.9,
            motion_blur_strength=0.85,
            blur_mode="simple",
            blur_samples=7,
            seed=1925,
        )

        self.assertEqual(tuple(out_hard.shape), (25, 4, 4, 3))
        self.assertEqual(tuple(out_blur.shape), (25, 4, 4, 3))

        unique_hard = torch.unique(out_hard[:, 0, 0, 0]).numel()
        self.assertLess(unique_hard, 25)

        hard_data = json.loads(payload_hard)
        blur_data = json.loads(payload_blur)
        self.assertEqual(hard_data["group_count"], int(unique_hard))
        self.assertGreaterEqual(float(hard_data["average_effective_fps"]), 15.0)
        self.assertLessEqual(float(hard_data["average_effective_fps"]), 17.0)
        self.assertNotEqual(payload_hard, payload_blur)
        self.assertGreater(float(torch.mean(torch.abs(out_blur - out_hard)).item()), 0.0)

        out_undercrank, payload_undercrank = node.apply(
            ramp,
            source_fps=25.0,
            playback_mode="undercrank_projected_25fps",
            target_fps_min=16.0,
            target_fps_max=16.0,
            fps_drift_strength=0.0,
            shutter_fraction=1.0,
            motion_blur_strength=1.0,
            blur_mode="simple",
            blur_samples=7,
            seed=1925,
        )
        undercrank_data = json.loads(payload_undercrank)
        self.assertEqual(undercrank_data["playback_mode"], "undercrank_projected_25fps")
        self.assertLess(out_undercrank.shape[0], 25)
        self.assertEqual(int(out_undercrank.shape[0]), int(undercrank_data["output_frame_count"]))
        self.assertLess(float(undercrank_data["output_duration_seconds"]), float(undercrank_data["input_duration_seconds"]))

        out_flow, payload_flow = node.apply(
            ramp,
            source_fps=25.0,
            playback_mode="preserve_duration_25fps",
            target_fps_min=16.0,
            target_fps_max=18.0,
            fps_drift_strength=0.5,
            shutter_fraction=1.0,
            motion_blur_strength=1.0,
            blur_mode="flow_integrated",
            blur_samples=5,
            seed=1925,
        )
        flow_data = json.loads(payload_flow)
        self.assertEqual(tuple(out_flow.shape), (25, 4, 4, 3))
        self.assertIn(flow_data["actual_blur_mode"], {"flow_integrated", "simple_fallback_no_cv2"})

    def test_video_silent_film_cadence_legacy_sequence_is_unchanged(self):
        """Preserve cadence values for workflows without the new optional controls."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        implicit = mod._build_capture_intervals(1.0, 16.0, 20.0, 0.65, 1925)
        explicit = mod._build_capture_intervals(1.0, 16.0, 20.0, 0.65, 1925, "legacy_random")
        self.assertEqual(implicit, explicit)
        np.testing.assert_allclose(implicit[1][:6], [
            17.082349221558694, 17.845202704709344, 18.518135002643014,
            18.18944047428344, 19.425655123078222, 19.10878271446584,
        ], rtol=0, atol=1e-12)

    def test_video_silent_film_cadence_crank_repeats_per_revolution(self):
        """Tie cyclic speed to film advance and shorten turns as speed increases."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        for frames_per_turn in (4, 8, 16):
            with self.subTest(frames_per_turn=frames_per_turn):
                starts, fps, biases = mod._build_capture_intervals(
                    4.0, 16.0, 20.0, 1.0, 1925, "hand_crank", frames_per_turn, 0.0,
                )
                np.testing.assert_allclose(fps[frames_per_turn:], fps[:-frames_per_turn], atol=1e-12)
                self.assertGreater(max(fps) - min(fps), 2.0)
                np.testing.assert_allclose(np.diff(starts)[:-1], 1.0 / np.array(fps[:-1]))
                self.assertEqual(biases, [0.0] * len(fps))
                faster_starts, faster_fps, _ = mod._build_capture_intervals(
                    2.0, 32.0, 40.0, 1.0, 1925, "hand_crank", frames_per_turn, 0.0,
                )
                np.testing.assert_allclose(faster_fps, np.array(fps) * 2.0)
                np.testing.assert_allclose(faster_starts, np.array(starts) / 2.0)

    def test_video_silent_film_cadence_crank_drift_is_bounded_and_repeatable(self):
        """Keep seeded irregularity bounded and disable all drift at zero strength."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        for irregularity in (0.0, 0.15, 1.0):
            with self.subTest(irregularity=irregularity):
                args = (5.0, 16.0, 20.0, 0.8, 1925, "hand_crank", 8, irregularity)
                result = mod._build_capture_intervals(*args)
                self.assertEqual(result, mod._build_capture_intervals(*args))
                starts, fps, _ = result
                self.assertEqual(starts[-1], 5.0)
                self.assertTrue(np.all(np.diff(starts) > 0))
                self.assertGreaterEqual(min(fps), 16.4 - 1e-12)
                self.assertLessEqual(max(fps), 19.6 + 1e-12)
                if irregularity:
                    self.assertGreater(float(np.max(np.abs(np.array(fps[8:]) - fps[:-8]))), 0.01)
        for low, high, strength in [(16.0, 20.0, 0.0), (18.0, 18.0, 1.0)]:
            _, fps, _ = mod._build_capture_intervals(2.0, low, high, strength, 1, "hand_crank")
            np.testing.assert_allclose(fps, 18.0)
        first = mod._build_capture_intervals(2.0, 16.0, 20.0, 0.8, 1, "hand_crank")
        second = mod._build_capture_intervals(2.0, 16.0, 20.0, 0.8, 2, "hand_crank")
        self.assertNotEqual(first, second)

    def test_video_silent_film_cadence_crank_validates_controls(self):
        """Reject invalid crank controls before generating intervals."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        for model, frames_per_turn, irregularity in [
            ("unknown", 8, 0.15), ("hand_crank", 1, 0.15),
            ("hand_crank", 8.5, 0.15), ("hand_crank", 33, 0.15),
            ("hand_crank", 8, -0.1), ("hand_crank", 8, 1.1),
            ("hand_crank", 8, float("nan")),
        ]:
            with self.subTest(model=model, frames_per_turn=frames_per_turn, irregularity=irregularity):
                with self.assertRaises(ValueError):
                    mod._build_capture_intervals(1.0, 16.0, 20.0, 0.8, 1, model, frames_per_turn, irregularity)

    def test_video_silent_film_cadence_crank_supports_both_playback_modes(self):
        """Keep image and metadata contracts in both playback modes with cyclic cadence."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        images = torch.linspace(0.0, 1.0, 48).view(48, 1, 1, 1).expand(48, 4, 4, 4)
        for mode in ("preserve_duration_25fps", "undercrank_projected_25fps"):
            with self.subTest(mode=mode):
                out, payload = mod.VideoSilentFilmCadence().apply(
                    images, 24.0, mode, 16.0, 20.0, 0.65, 0.65, 0.8, "simple", 5, 1925,
                    cadence_model="hand_crank", crank_frames_per_turn=8, crank_irregularity=0.15,
                    camera_shake_strength=0.25,
                )
                data = json.loads(payload)
                self.assertEqual(data["cadence_model"], "hand_crank")
                self.assertEqual(data["crank_frames_per_turn"], 8)
                self.assertEqual(len(data["output_group_ids"]), len(out))
                self.assertEqual(len(data["fps_values_full"]), data["group_count"])
                self.assertEqual(mod._validate_video_batch(out).shape, out.shape)
                self.assertTrue(torch.isfinite(out).all())
                if mode == "preserve_duration_25fps":
                    self.assertEqual(out.shape, images.shape)
                else:
                    self.assertLess(len(out), len(images))

    def test_video_silent_film_capture_phase_follows_capture_intervals(self):
        """Use capture timing for camera phase, including variable-speed intervals."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        starts, _, _ = mod._build_capture_intervals(3.0, 16.0, 20.0, 0.8, 1925, "hand_crank")
        initial_phase = 0.25
        for index in range(len(starts) - 1):
            self.assertAlmostEqual(mod._crank_phase_at_time(starts, starts[index], initial_phase), initial_phase + index / 8)
            middle = (starts[index] + starts[index + 1]) / 2
            self.assertAlmostEqual(mod._crank_phase_at_time(starts, middle, initial_phase), initial_phase + (index + 0.5) / 8)
        self.assertEqual(mod._crank_phase_at_time(starts, -1, initial_phase), initial_phase)
        self.assertAlmostEqual(mod._crank_phase_at_time(starts, 10, initial_phase), initial_phase + (len(starts) - 1) / 8)

    def test_video_silent_film_capture_motion_is_smooth_seeded_and_nonperiodic(self):
        """Vary poses between revolutions without jumps, unbounded drift, or sampling-order dependence."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        motion = mod._CaptureCameraMotion(1925)
        phases = np.linspace(0.0, 12.0, 1201)
        poses = np.array([motion.pose(float(phase)) for phase in phases])
        self.assertTrue(np.isfinite(poses).all())
        self.assertLessEqual(float(np.abs(poses).max()), 1.0)
        self.assertLess(float(np.abs(np.diff(poses, axis=0)).max()), 0.15)
        self.assertGreater(float(np.abs(poses[100:] - poses[:-100]).mean()), 0.05)
        repeated = mod._CaptureCameraMotion(1925)
        np.testing.assert_array_equal(poses, [repeated.pose(float(phase)) for phase in phases])
        reverse = np.array([motion.pose(float(phase)) for phase in phases[::-1]])
        np.testing.assert_array_equal(poses, reverse[::-1])
        other = mod._CaptureCameraMotion(1926)
        self.assertGreater(float(np.abs(poses - [other.pose(float(phase)) for phase in phases]).mean()), 0.05)
        for turn in range(1, 12):
            np.testing.assert_allclose(motion.pose(turn - 1e-6), motion.pose(turn + 1e-6), atol=1e-4, rtol=0)
        self.assertLessEqual(len(motion.turn_events), 8)
        self.assertLessEqual(len(motion.aim_points), 8)

    def test_video_silent_film_capture_shake_is_nonperiodic_and_integrated(self):
        """Blur static detail along a nonperiodic camera trajectory during exposure."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        frame = torch.zeros(64, 96, 4)
        frame[::4, :, :3] = 1.0
        frame[:, ::4, :3] = 1.0
        frame[..., 3] = 0.7
        self.assertIs(mod._apply_capture_shake(frame, 0.2, 0.0), frame)
        shifted = mod._apply_capture_shake(frame, 0.6, 1.0)
        torch.testing.assert_close(shifted, mod._apply_capture_shake(frame, 0.6, 1.0))
        self.assertGreater(float(torch.mean(torch.abs(shifted - mod._apply_capture_shake(frame, 1.6, 1.0)))), 0.001)
        self.assertGreater(float(torch.mean(torch.abs(shifted - frame))), 0.01)
        torch.testing.assert_close(shifted[..., 3], frame[..., 3])
        integrated = mod._temporal_exposure_sample(
            lambda position: mod._apply_capture_shake(frame, position / 8, 1.0),
            frame, 4.8, 6.0, 9,
        )
        self.assertGreater(float(torch.mean(torch.abs(integrated - shifted))), 0.001)
        self.assertTrue(torch.isfinite(integrated).all())
        self.assertEqual(integrated.shape, frame.shape)

    def test_video_silent_film_capture_shake_node_preserves_compatibility(self):
        """Keep zero-shake and legacy output unchanged while varying camera effort per turn."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        frame = torch.zeros(32, 48, 4)
        frame[:, ::3, :3] = 1.0
        frame[..., 3] = 0.7
        images = frame.unsqueeze(0).repeat(48, 1, 1, 1)
        node = mod.VideoSilentFilmCadence()
        args = (images, 24.0, "undercrank_projected_25fps", 18.0, 18.0, 0.0, 0.0, 0.0, "simple", 1, 1925)
        baseline, _ = node.apply(*args)
        legacy, legacy_json = node.apply(*args, camera_shake_strength=1.0)
        torch.testing.assert_close(legacy, baseline, atol=0, rtol=0)
        self.assertEqual(json.loads(legacy_json)["actual_camera_shake_strength"], 0.0)
        zero, _ = node.apply(*args, cadence_model="hand_crank", camera_shake_strength=0.0)
        torch.testing.assert_close(zero, baseline, atol=0, rtol=0)
        shaken, payload = node.apply(*args, cadence_model="hand_crank", camera_shake_strength=1.0)
        again, _ = node.apply(*args, cadence_model="hand_crank", camera_shake_strength=1.0)
        torch.testing.assert_close(shaken, again, atol=0, rtol=0)
        self.assertGreater(float(torch.mean(torch.abs(shaken[2] - shaken[10]))), 0.001)
        self.assertGreater(float(torch.mean(torch.abs(shaken - zero))), 0.001)
        torch.testing.assert_close(shaken[..., 3], zero[..., 3])
        data = json.loads(payload)
        self.assertEqual(data["capture_motion_model"], "crank_locked")
        self.assertEqual(data["actual_camera_shake_strength"], 1.0)
        old_field, old_payload = node.apply(*args, cadence_model="hand_crank", crank_frames_per_turn=12, camera_shake_strength=1.0)
        torch.testing.assert_close(old_field, shaken, atol=0, rtol=0)
        self.assertEqual(json.loads(old_payload)["crank_frames_per_turn"], 8)
        for strength in (-0.1, 1.1, float("nan"), float("inf")):
            with self.subTest(strength=strength):
                with self.assertRaises(ValueError):
                    node.apply(*args, camera_shake_strength=strength)

    def test_video_silent_film_capture_shake_runs_inside_node_exposure(self):
        """Apply camera transforms to exposure subsamples rather than the final frame."""
        from unittest.mock import patch
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        phases = []

        def record_sample(frame, phase, strength, base_grid, motion=None):
            """Record capture phase for each exposure subsample."""
            phases.append(phase)
            return frame

        with patch.object(mod, "_apply_capture_shake", side_effect=record_sample):
            out, _ = mod.VideoSilentFilmCadence().apply(
                torch.ones(24, 4, 4, 3), 24.0, "undercrank_projected_25fps", 16.0, 20.0,
                0.65, 1.0, 1.0, "simple", 9, 1925,
                cadence_model="hand_crank", camera_shake_strength=0.25,
            )
        self.assertEqual(len(phases), len(out) * 9)
        self.assertGreater(phases[8] - phases[0], 0.05)
        self.assertTrue(np.all(np.diff(phases[:9]) >= 0))

    def test_video_silent_film_cadence_logs_stages_and_bounded_progress(self):
        """Show one terminal progress bar with actual output counts and flow fallback."""
        from unittest.mock import patch
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        from io import StringIO
        real_tqdm = mod.tqdm
        for mode in ("preserve_duration_25fps", "undercrank_projected_25fps"):
            with self.subTest(mode=mode):
                terminal = StringIO()

                def make_progress(**kwargs):
                    """Capture the real terminal bar without relying on a TTY."""
                    return real_tqdm(**{**kwargs, "file": terminal, "mininterval": 0, "dynamic_ncols": False})

                with patch.object(mod, "cv2", None), patch.object(mod, "perf_counter", return_value=0.0):
                    with self.assertLogs("VideoSilentFilmCadence", level="INFO") as logs, patch.object(mod, "tqdm", side_effect=make_progress) as bar:
                        out, payload = mod.VideoSilentFilmCadence().apply(
                            torch.zeros(60, 4, 4, 3), 24.0, mode, 16.0, 16.0,
                            0.0, 0.65, 0.8, "flow_integrated", 5, 1925,
                        )
                messages = [record.getMessage() for record in logs.records]
                stages = [message for message in messages if "Этап " in message]
                self.assertEqual(len(stages), 4)
                for index, message in enumerate(stages, 1):
                    self.assertIn(f"Этап {index}/4", message)
                bar.assert_called_once()
                self.assertEqual(bar.call_args.kwargs["total"], len(out))
                self.assertIn(f"0/{len(out)}", terminal.getvalue())
                self.assertIn(f"{len(out)}/{len(out)}", terminal.getvalue())
                self.assertIn("100%", terminal.getvalue())
                self.assertFalse(any("Кадры:" in message for message in messages))
                self.assertTrue(any(record.levelname == "WARNING" and "OpenCV" in record.getMessage() for record in logs.records))
                self.assertIn("Готово:", messages[-1])
                self.assertEqual(json.loads(payload)["actual_blur_mode"], "simple_fallback_no_cv2")

    def test_video_silent_film_cadence_torch_sampler_matches_cpu_warps(self):
        """Preserve confidence fallback and remap results with bounded tensor caches."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        if mod.cv2 is None:
            self.skipTest("OpenCV is required for optical flow")
        images = torch.rand(9, 24, 32, 4, generator=torch.Generator().manual_seed(7))
        images[..., 3] = 0.7
        sampler = mod._TorchExposureSampler(images, torch.device("cpu"), {}, {}, {})
        for position in [0.25, 0.5, 1.75, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 0.5]:
            result = sampler.sample(position, use_flow=True)
            expected = mod._lerp_frame_flow(images, position, {}, {})
            torch.testing.assert_close(result, expected, atol=5e-5, rtol=1e-5)
            for cache in (sampler.tensor_frames, sampler.tensor_pairs, sampler.flow_cache, sampler.confidence_cache, sampler.frame_cache):
                self.assertLessEqual(len(cache), 4)
        torch.testing.assert_close(sampler.sample(2.25, use_flow=False), mod._lerp_frame(images, 2.25))

    def test_video_silent_film_cadence_gpu_matches_cpu_and_returns_input_device(self):
        """Exercise real CUDA exposure processing, alpha, shake, and both playback modes."""
        from unittest.mock import patch
        if not torch.cuda.is_available():
            self.skipTest("CUDA is unavailable")
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        if mod.cv2 is None:
            self.skipTest("OpenCV is required for optical flow")
        images = torch.rand(6, 32, 48, 4, generator=torch.Generator().manual_seed(7))
        images[..., 3] = 0.7
        for mode in ("preserve_duration_25fps", "undercrank_projected_25fps"):
            for blur in ("simple", "flow_integrated"):
                with self.subTest(mode=mode, blur=blur):
                    args = (images, 24.0, mode, 16.0, 20.0, 0.65, 0.65, 0.8, blur, 5, 1925)
                    cpu, _ = mod.VideoSilentFilmCadence().apply(*args, cadence_model="hand_crank", camera_shake_strength=0.25, compute_device="cpu")
                    with patch.object(mod, "_select_compute_device", return_value=torch.device("cuda")):
                        gpu, payload = mod.VideoSilentFilmCadence().apply(*args, cadence_model="hand_crank", camera_shake_strength=0.25, compute_device="cuda")
                    torch.testing.assert_close(gpu, cpu, atol=1e-4, rtol=1e-5)
                    self.assertEqual(gpu.device, images.device)
                    self.assertEqual(json.loads(payload)["actual_compute_device"], "cuda")

    def test_video_silent_film_cadence_device_validation_and_oom_fallback(self):
        """Keep CPU support and retry when CUDA working storage cannot be allocated."""
        from unittest.mock import patch
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        self.assertEqual(mod._select_compute_device("cpu", 1000, 1000).type, "cpu")
        self.assertEqual(mod._select_compute_device("auto", 4, 4).type, "cpu")
        with self.assertRaises(ValueError):
            mod._select_compute_device("unknown", 4, 4)
        with patch.object(torch.cuda, "is_available", return_value=False):
            self.assertEqual(mod._select_compute_device("cuda", 1000, 1000).type, "cpu")
        args = (torch.zeros(6, 8, 8, 3), 24.0, "preserve_duration_25fps", 16.0, 20.0, 0.65, 0.65, 0.8, "simple", 5, 1925)
        baseline, _ = mod.VideoSilentFilmCadence().apply(*args, compute_device="cpu")
        with patch.object(mod, "_select_compute_device", return_value=torch.device("cuda")):
            with patch.object(mod, "_TorchExposureSampler", side_effect=torch.OutOfMemoryError("test OOM")):
                actual, payload = mod.VideoSilentFilmCadence().apply(*args)
        torch.testing.assert_close(actual, baseline)
        self.assertEqual(json.loads(payload)["actual_compute_device"], "cpu")
        if torch.cuda.is_available():
            with patch.object(mod, "_select_compute_device", return_value=torch.device("cuda")):
                with patch.object(mod._TorchExposureSampler, "sample", side_effect=torch.OutOfMemoryError("test OOM")):
                    actual, payload = mod.VideoSilentFilmCadence().apply(*args)
            torch.testing.assert_close(actual, baseline)
            self.assertEqual(json.loads(payload)["actual_compute_device"], "cpu")

    def test_video_silent_film_finish_logs_stages_and_completion(self):
        """Report batch processing stages and the actual synchronization mode."""
        from unittest.mock import patch
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        node = mod.VideoSilentFilmFinish()
        parameters = {
            key: spec[1]["default"] for key, spec in node.INPUT_TYPES()["required"].items() if key not in {"image", "compute_device", "batch_size", "vignette_strength", "edge_softness", "edge_start", "edge_end", "grain_size_mode"}
        }
        real_tqdm = mod.tqdm
        with self.assertLogs("VideoSilentFilmFinish", level="INFO") as logs:
            def start_progress(*args, **kwargs):
                """Require the full processing plan before rendering the progress bar."""
                for stage in (3, 4, 5, 6):
                    self.assertTrue(any(f"Этап {stage}/7" in record.getMessage() for record in logs.records))
                return real_tqdm(*args, **kwargs)
            with patch.object(mod, "tqdm", side_effect=start_progress):
                out, payload = node.apply(torch.zeros(4, 8, 8, 3), **parameters, cadence_json="invalid", batch_size=1)
        messages = [record.getMessage() for record in logs.records]
        stages = [message for message in messages if "Этап " in message]
        self.assertEqual(len(stages), 7)
        for index, message in enumerate(stages, 1):
            self.assertIn(f"Этап {index}/7", message)
        self.assertTrue(any("Синхронизация: invalid_json" in message for message in messages))
        self.assertIn("Готово: 4 кадров", messages[-1])
        self.assertEqual(out.shape, (4, 8, 8, 3))
        self.assertEqual(json.loads(payload)["sync_mode"], "invalid_json")

    def test_video_silent_film_logs_do_not_claim_completion_on_failure(self):
        """Do not report successful completion when an image-processing stage fails."""
        from unittest.mock import patch
        cadence = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        finish = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        with self.assertLogs("VideoSilentFilmCadence", level="INFO") as logs:
            with patch.object(cadence, "_temporal_exposure_sample", side_effect=RuntimeError("test failure")):
                with self.assertRaisesRegex(RuntimeError, "test failure"):
                    cadence.VideoSilentFilmCadence().apply(
                        torch.zeros(4, 8, 8, 3), 24.0, "preserve_duration_25fps", 16.0, 18.0,
                        0.5, 0.65, 0.8, "simple", 5, 1925,
                    )
        self.assertFalse(any("Готово:" in message or "(100%)" in message for message in logs.output))
        parameters = {
            key: spec[1]["default"] for key, spec in finish.VideoSilentFilmFinish.INPUT_TYPES()["required"].items() if key not in {"image", "compute_device", "batch_size", "vignette_strength", "edge_softness", "edge_start", "edge_end", "grain_size_mode"}
        }
        with self.assertLogs("VideoSilentFilmFinish", level="INFO") as logs:
            with patch.object(finish, "_apply_grain", side_effect=RuntimeError("test failure")):
                with self.assertRaisesRegex(RuntimeError, "test failure"):
                    finish.VideoSilentFilmFinish().apply(torch.zeros(4, 8, 8, 3), **parameters)
        self.assertTrue(any("Этап 6/7" in message for message in logs.output))
        self.assertFalse(any("Готово:" in message or "Этап 7/7" in message for message in logs.output))

    def test_video_silent_film_cadence_rejects_inconsistent_flow(self):
        """Keep static details intact when the estimated flows disagree."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        if mod.cv2 is None:
            self.skipTest("OpenCV is required for optical flow")
        frame = np.zeros((48, 64, 4), dtype=np.float32)
        frame[:, ::4, :3] = 1.0
        frame[..., 3] = 0.7
        images = torch.from_numpy(np.stack([frame, frame]))
        invalid = np.zeros((48, 64, 2), dtype=np.float32)
        invalid[..., 0] = 6.0
        out = mod._lerp_frame_flow(images, 0.5, {}, {0: (invalid, invalid)})
        torch.testing.assert_close(out, images[0], atol=1e-6, rtol=0)
        self.assertTrue(torch.isfinite(out).all())

    def test_video_silent_film_cadence_flow_preserves_reliable_translation(self):
        """Retain motion compensation when forward and backward flows agree."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        if mod.cv2 is None:
            self.skipTest("OpenCV is required for optical flow")
        first = np.zeros((48, 64, 3), dtype=np.float32)
        first[12:36, 16:32] = 1.0
        second = np.roll(first, 4, axis=1)
        expected = torch.from_numpy(np.roll(first, 2, axis=1))
        images = torch.from_numpy(np.stack([first, second]))
        forward = np.zeros((48, 64, 2), dtype=np.float32)
        forward[..., 0] = 4.0
        out = mod._lerp_frame_flow(images, 0.5, {}, {0: (forward, -forward)})
        torch.testing.assert_close(out[:, 8:-8], expected[:, 8:-8], atol=1e-6, rtol=0)
        self.assertGreater(float(torch.mean(torch.abs(out - images.mean(dim=0)))), 0.01)

    def test_video_silent_film_finish_preserves_shape_and_alpha(self):
        """Ensure silent-film finish keeps batch shape and preserves alpha channel contract."""
        video_mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        node = video_mod.VideoSilentFilmFinish()

        frames = torch.rand(6, 12, 10, 4)
        frames[..., 3] = torch.linspace(0.2, 0.8, steps=6, dtype=torch.float32).view(6, 1, 1)
        out, payload = node.apply(
            frames,
            tone_mode="warm_print",
            contrast=0.95,
            midtone_gamma=0.95,
            black_lift=0.03,
            highlight_rolloff=0.35,
            softness=0.25,
            focus_drift_strength=0.06,
            flicker_strength=0.05,
            breathing_strength=0.025,
            gate_weave_px=1.0,
            grain_mode="emulsion_luma",
            grain_strength=0.03,
            grain_size=2,
            seed=1925,
        )

        self.assertEqual(tuple(out.shape), (6, 12, 10, 4))
        data = json.loads(payload)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["tone_mode"], "warm_print")
        self.assertEqual(data["grain_mode"], "emulsion_luma")
        self.assertIn("focus_preview", data)
        self.assertIn("gate_x_preview", data)
        self.assertIn("exposure_preview", data)
        self.assertGreater(float(torch.mean(torch.abs(out[..., :3] - frames[..., :3])).item()), 0.0)
        self.assertGreaterEqual(float(out[..., 3].min().item()), 0.0)
        self.assertLessEqual(float(out[..., 3].max().item()), 1.0)
        self.assertEqual(data["sync_mode"], "none")

    def test_video_silent_film_finish_chunks_preserve_signals_and_frame_grain(self):
        """Keep normalized output, synchronization, and grain independent of chunk size."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        node = mod.VideoSilentFilmFinish()
        parameters = {key: spec[1]["default"] for key, spec in node.INPUT_TYPES()["required"].items() if key not in {"image", "compute_device", "batch_size", "vignette_strength", "edge_softness", "edge_start", "edge_end", "grain_size_mode"}}
        image = torch.rand(7, 19, 17, 4, generator=torch.Generator().manual_seed(7)) * 1.4 - 0.2
        original = image.clone()
        self.assertEqual(mod._validate_video_batch(image, normalize=False).data_ptr(), image.data_ptr())
        gray = image[..., 0:1].clamp(0.0, 1.0)
        focus = torch.linspace(-0.5, 0.5, len(image))
        torch.testing.assert_close(
            mod._apply_focus_drift(gray, 0.15, focus, 0.04),
            mod._apply_focus_drift(gray.repeat(1, 1, 1, 3), 0.15, focus, 0.04)[..., 0:1],
        )
        meta = json.dumps({
            "schema_name": "alexz.video_silent_film_cadence", "output_group_ids": [0, 0, 1, 1, 2, 2, 3],
            "fps_values_full": [16, 18, 16, 20], "phase_biases_full": [0.1, -0.1, 0, 0.03],
        })
        for grain_mode in ("emulsion_luma", "overlay_fast"):
            with self.subTest(grain_mode=grain_mode):
                parameters["grain_mode"] = grain_mode
                baseline, base_payload = node.apply(image, **parameters, cadence_json=meta, compute_device="cpu", batch_size=1)
                for size in (3, 7):
                    actual, payload = node.apply(image, **parameters, cadence_json=meta, compute_device="cpu", batch_size=size)
                    torch.testing.assert_close(actual, baseline, atol=1e-6, rtol=1e-5)
                    data = json.loads(payload)
                    self.assertEqual(data["sync_mode"], "cadence_locked")
                    self.assertEqual(data["focus_preview"], json.loads(base_payload)["focus_preview"])
                    self.assertEqual(data["grain_seed_mode"], "per_frame")
                torch.testing.assert_close(image, original, atol=0, rtol=0)
        repeated = torch.full((5, 19, 17, 3), 0.5)
        grain = mod._apply_grain(repeated, "emulsion_luma", 0.03, 2, 1925, frame_offset=0)
        self.assertGreater(float((grain[0] - grain[1]).abs().mean()), 1e-4)
        torch.testing.assert_close(grain[2:4], mod._apply_grain(repeated[2:4], "emulsion_luma", 0.03, 2, 1925, frame_offset=2))

    def test_video_silent_film_finish_relative_grain_size(self):
        """Scale grain continuously with width and retain chunk and legacy compatibility."""
        from unittest.mock import patch
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        node = mod.VideoSilentFilmFinish()
        parameters = {key: spec[1]["default"] for key, spec in node.INPUT_TYPES()["required"].items() if key not in {"image", "compute_device", "batch_size", "vignette_strength", "edge_softness", "edge_start", "edge_end", "grain_size_mode"}}
        parameters.update(grain_size=3, grain_strength=0.1, gate_weave_px=0)
        for mode in ("overlay_fast", "emulsion_luma"):
            parameters["grain_mode"] = mode
            for width in (320, 640, 960):
                image = torch.full((3, 9, width, 3), 0.5)
                with patch.object(mod, "_apply_grain", wraps=mod._apply_grain) as grain:
                    actual, payload = node.apply(image, **parameters, grain_size_mode="relative_width", compute_device="cpu", batch_size=1)
                    self.assertEqual(grain.call_args_list[0].args[3], 3 * width / 1920)
                    self.assertAlmostEqual(grain.call_args_list[0].args[2], 0.1 * min(1, 3 * width / 1920))
                data = json.loads(payload)
                self.assertEqual(data["effective_grain_size_px"], 3 * width / 1920)
                self.assertEqual(data["grain_size_mode"], "relative_width")
                chunked, _ = node.apply(image, **parameters, grain_size_mode="relative_width", compute_device="cpu", batch_size=3)
                torch.testing.assert_close(actual, chunked)
                if torch.cuda.is_available():
                    gpu, _ = node.apply(image, **parameters, grain_size_mode="relative_width", compute_device="cuda", batch_size=2)
                    torch.testing.assert_close(actual, gpu, atol=1e-4, rtol=1e-4)
            legacy, _ = node.apply(image, **parameters, compute_device="cpu")
            explicit, _ = node.apply(image, **parameters, grain_size_mode="pixels", compute_device="cpu")
            torch.testing.assert_close(legacy, explicit, atol=0, rtol=0)
        with self.assertRaises(ValueError):
            node.apply(image, **parameters, grain_size_mode="invalid")

    def test_video_silent_film_finish_cuda_matches_chunked_cpu(self):
        """Run real CUDA finishing with the same frame grain and CPU output contract."""
        from unittest.mock import patch
        if not torch.cuda.is_available():
            self.skipTest("CUDA is unavailable")
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        node = mod.VideoSilentFilmFinish()
        parameters = {key: spec[1]["default"] for key, spec in node.INPUT_TYPES()["required"].items() if key not in {"image", "compute_device", "batch_size", "vignette_strength", "edge_softness", "edge_start", "edge_end", "grain_size_mode"}}
        image = torch.rand(5, 32, 48, 4, generator=torch.Generator().manual_seed(7))
        for mode in ("emulsion_luma", "overlay_fast"):
            with self.subTest(grain_mode=mode):
                parameters["grain_mode"] = mode
                baseline, _ = node.apply(image, **parameters, compute_device="cpu", batch_size=1)
                with patch.object(mod, "_finish_processing_plan", return_value=(torch.device("cuda"), 2, 2)):
                    result, payload = node.apply(image, **parameters, compute_device="cuda", batch_size=2)
                torch.testing.assert_close(result, baseline, atol=1e-4, rtol=1e-5)
                self.assertEqual(result.device, image.device)
                self.assertEqual(json.loads(payload)["actual_compute_device"], "cuda")

    def test_video_silent_film_finish_oom_retries_and_ram_guard(self):
        """Reduce CUDA chunks and fall back without losing frames or changing grain."""
        from unittest.mock import patch
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        node = mod.VideoSilentFilmFinish()
        parameters = {key: spec[1]["default"] for key, spec in node.INPUT_TYPES()["required"].items() if key not in {"image", "compute_device", "batch_size", "vignette_strength", "edge_softness", "edge_start", "edge_end", "grain_size_mode"}}
        image = torch.rand(7, 16, 20, 4, generator=torch.Generator().manual_seed(7))
        baseline, _ = node.apply(image, **parameters, compute_device="cpu", batch_size=1)
        run_chunk = mod._run_finish_chunk
        attempts = []

        def simulate_oom(images, start, end, device, *args):
            """Fail CUDA requests before allocating and execute CPU retries normally."""
            attempts.append((start, end, device.type))
            if device.type == "cuda":
                raise torch.OutOfMemoryError("test OOM")
            return run_chunk(images, start, end, device, *args)

        with patch.object(mod, "_finish_processing_plan", return_value=(torch.device("cuda"), 4, 2)):
            with patch.object(mod, "_run_finish_chunk", side_effect=simulate_oom):
                result, payload = node.apply(image, **parameters)
        torch.testing.assert_close(result, baseline)
        self.assertEqual(attempts[:3], [(0, 4, "cuda"), (0, 2, "cuda"), (0, 1, "cuda")])
        self.assertEqual(json.loads(payload)["actual_compute_device"], "cpu")
        self.assertEqual(json.loads(payload)["chunk_count"], 4)
        with patch.object(mod, "_available_finish_ram", return_value=0):
            with self.assertRaisesRegex(MemoryError, "RAM"):
                node.apply(image, **parameters)
        for size in (0, 17, 2.5):
            with self.subTest(batch_size=size), self.assertRaises(ValueError):
                node.apply(image, **parameters, batch_size=size)

    def test_video_silent_film_lens_edges_preserve_center_and_uniform_blur(self):
        """Darken corners smoothly and keep constant images free of convolution halos."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        uniform = torch.full((3, 65, 97, 3), 0.6)
        self.assertIs(mod._apply_lens_edges(uniform, 0.0, 0.0, 0.6), uniform)
        vignette = mod._apply_lens_edges(uniform, 0.12, 0.0, 0.6)
        torch.testing.assert_close(vignette[:, 32, 48], uniform[:, 32, 48], atol=0, rtol=0)
        torch.testing.assert_close(vignette[:, 0, 0], torch.full((3, 3), 0.6 * 0.88))
        torch.testing.assert_close(vignette[0], vignette[1], atol=0, rtol=0)
        torch.testing.assert_close(mod._apply_lens_edges(uniform, 0.0, 1.0, 0.6), uniform)
        mask = mod._lens_edge_mask(65, 97, 0.6, uniform.device, uniform.dtype)
        self.assertTrue(torch.isfinite(mask).all())
        self.assertTrue(torch.all(mask[:, 0, 1:49] <= mask[:, 0, :48]))
        checker = torch.zeros_like(uniform)
        checker[:, ::2] = 1.0
        softened = mod._apply_lens_edges(checker, 0.0, 0.4, 0.6)
        torch.testing.assert_close(softened[:, 25:40, 40:57], checker[:, 25:40, 40:57], atol=0, rtol=0)
        self.assertGreater(float((softened[:, :5, :5] - checker[:, :5, :5]).abs().mean()), 0.01)

    def test_video_silent_film_lens_mask_is_circular(self):
        """Use equal falloff at equal pixel radii on rectangular and degenerate frames."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        mask = mod._lens_edge_mask(65, 129, 0.1, torch.device("cpu"), torch.float32)[0, ..., 0]
        torch.testing.assert_close(mask[32, 88], mask[56, 64], atol=0, rtol=0)
        self.assertGreater(float(mask[32, 0]), float(mask[0, 64]))
        torch.testing.assert_close(mask, mask.flip((0, 1)), atol=0, rtol=0)
        self.assertAlmostEqual(float(mask[0, 0]), 1.0, places=6)
        larger = mod._lens_edge_mask(129, 257, 0.1, torch.device("cpu"), torch.float32)[0, ..., 0]
        torch.testing.assert_close(larger[::2, ::2], mask)
        taller = mod._lens_edge_mask(129, 129, 0.1, torch.device("cpu"), torch.float32)[0, ..., 0]
        torch.testing.assert_close(taller[32:97], mask)
        self.assertAlmostEqual(float(mask[32, 0]), 1.0, places=6)
        for height, width in ((1, 1), (1, 9), (9, 1)):
            small = mod._lens_edge_mask(height, width, 0.6, torch.device("cpu"), torch.float32)
            self.assertTrue(torch.isfinite(small).all())
        if torch.cuda.is_available():
            actual = mod._lens_edge_mask(65, 129, 0.1, torch.device("cuda"), torch.float32).cpu()
            torch.testing.assert_close(actual[0, ..., 0], mask)

    def test_video_silent_film_lens_transition_end(self):
        """Control transition width independently and reject inverted radii."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        mask = mod._lens_edge_mask(129, 201, 0.8, torch.device("cpu"), torch.float32, 1.2)[0, ..., 0]
        self.assertEqual(float(mask[64, 180]), 0.0)
        self.assertAlmostEqual(float(mask[64, 200]), 0.5, places=5)
        # Точка 3–4–5: смещения 72 и 96 дают радиус 1.2 на маске шириной 201.
        full = mod._lens_edge_mask(201, 201, 0.8, torch.device("cpu"), torch.float32, 1.2)[0, ..., 0]
        self.assertAlmostEqual(float(full[172, 196]), 1.0, places=5)
        node = mod.VideoSilentFilmFinish()
        parameters = {key: spec[1]["default"] for key, spec in node.INPUT_TYPES()["required"].items() if key not in {"image", "compute_device", "batch_size", "vignette_strength", "edge_softness", "edge_start", "edge_end", "grain_size_mode"}}
        image = torch.full((2, 33, 49, 3), 0.5)
        for end in (0.6, 0.2, float("nan"), 5.0):
            with self.assertRaises(ValueError):
                node.apply(image, **parameters, edge_start=0.6, edge_end=end)
        implicit, _ = node.apply(image, **parameters, vignette_strength=0.3)
        explicit, _ = node.apply(image, **parameters, vignette_strength=0.3, edge_end=1.0)
        torch.testing.assert_close(implicit, explicit, atol=0, rtol=0)
        actual, payload = node.apply(image, **parameters, edge_start=1.1, edge_end=1.5, vignette_strength=0.3)
        self.assertTrue(torch.isfinite(actual).all())
        self.assertEqual(json.loads(payload)["edge_end"], 1.5)

    def test_video_silent_film_lens_mask_controls_blur_radius(self):
        """Use the mask as local sigma rather than alpha over a sharp image."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        image = (torch.arange(65) % 2).float().view(1, 65, 1, 1).expand(1, 65, 97, 3).clone()
        mask = torch.full((1, 65, 97, 1), 0.5)
        actual = mod._apply_variable_lens_blur(image, mask, 4.0)
        expected = mod._lens_gaussian_blur(image, 2.0)
        torch.testing.assert_close(actual, expected)
        overlay = torch.lerp(image, mod._lens_gaussian_blur(image, 4.0), mask)
        self.assertGreater(float((actual[:, 10:-10] - overlay[:, 10:-10]).abs().mean()), 0.2)
        # Пространственно разные значения должны выбирать соответствующие радиусы.
        mask[:, :, :32] = 0.0
        mask[:, :, 64:] = 1.0
        actual = mod._apply_variable_lens_blur(image, mask, 4.0)
        torch.testing.assert_close(actual[:, :, :32], image[:, :, :32], atol=0, rtol=0)
        torch.testing.assert_close(actual[:, :, 32:64], expected[:, :, 32:64])
        torch.testing.assert_close(actual[:, :, 64:], mod._lens_gaussian_blur(image, 4.0)[:, :, 64:])
        if torch.cuda.is_available():
            gpu = mod._apply_variable_lens_blur(image.cuda(), mask.cuda(), 4.0).cpu()
            torch.testing.assert_close(gpu, actual, atol=1e-4, rtol=1e-4)

    def test_video_silent_film_lens_edges_strong_defocus(self):
        """Suppress broad peripheral detail at maximum strength while retaining the center."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        stripes = ((torch.arange(257) // 8) % 2).float()
        image = stripes.view(1, 257, 1, 1).expand(1, 257, 257, 3).clone()
        weak = mod._apply_lens_edges(image, 0.0, 0.15, 0.4)
        strong = mod._apply_lens_edges(image, 0.0, 1.0, 0.4)
        region = (slice(None), slice(8, 40), slice(0, 16))
        self.assertLess(float((strong[region] - 0.5).square().mean()),
                        float((weak[region] - 0.5).square().mean()) * 0.4)
        torch.testing.assert_close(strong[:, 115:140, 115:140], image[:, 115:140, 115:140], atol=0, rtol=0)
        torch.testing.assert_close(mod._apply_lens_edges(torch.full_like(image, 0.6), 0.0, 1.0, 0.4), torch.full_like(image, 0.6))
        if torch.cuda.is_available():
            actual = mod._apply_lens_edges(image.cuda(), 0.0, 1.0, 0.4).cpu()
            torch.testing.assert_close(actual, strong, atol=1e-4, rtol=1e-4)

    def test_video_silent_film_lens_edges_move_with_projection(self):
        """Apply optical falloff before projector displacement without affecting alpha."""
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        parameters = {
            "tone_mode": "neutral_bw", "contrast": 1.0, "midtone_gamma": 1.0, "black_lift": 0.0,
            "highlight_rolloff": 0.0, "softness": 0.0, "focus_drift_strength": 0.0,
            "grain_mode": "emulsion_luma", "grain_strength": 0.0, "grain_size": 2, "seed": 1925,
            "vignette_strength": 0.3, "edge_softness": 0.2, "edge_start": 0.4,
        }
        image = torch.full((2, 33, 49, 4), 0.6)
        image[..., 3] = 0.7
        x, y = torch.tensor([2.0, -1.0]), torch.tensor([-1.0, 2.0])
        actual = mod._finish_chunk(image, x, y, torch.zeros(2), torch.ones(2), parameters, 0)
        optical = mod._apply_lens_edges(image[..., :3], 0.3, 0.2, 0.4)
        torch.testing.assert_close(actual[..., :3], mod._apply_gate_weave(optical, x, y))
        torch.testing.assert_close(actual[..., 3:4], mod._apply_gate_weave(image[..., 3:4], x, y))

    def test_video_silent_film_lens_edges_keep_chunks_and_cuda_consistent(self):
        """Preserve disabled behavior and deterministic optical output across chunk sizes and devices."""
        from unittest.mock import patch
        mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")
        node = mod.VideoSilentFilmFinish()
        parameters = {key: spec[1]["default"] for key, spec in node.INPUT_TYPES()["required"].items() if key not in {"image", "compute_device", "batch_size", "vignette_strength", "edge_softness", "edge_start", "edge_end", "grain_size_mode"}}
        image = torch.rand(5, 33, 49, 4, generator=torch.Generator().manual_seed(7))
        baseline, _ = node.apply(image, **parameters, compute_device="cpu", batch_size=2)
        disabled, _ = node.apply(image, **parameters, compute_device="cpu", batch_size=2, vignette_strength=0, edge_softness=0, edge_start=0.9)
        torch.testing.assert_close(disabled, baseline, atol=0, rtol=0)
        options = dict(vignette_strength=0.12, edge_softness=0.15, edge_start=0.6)
        cpu, payload = node.apply(image, **parameters, compute_device="cpu", batch_size=1, **options)
        batched, _ = node.apply(image, **parameters, compute_device="cpu", batch_size=3, **options)
        torch.testing.assert_close(cpu, batched)
        torch.testing.assert_close(cpu[..., 3], baseline[..., 3])
        self.assertEqual(json.loads(payload)["vignette_strength"], 0.12)
        if torch.cuda.is_available():
            with patch.object(mod, "_finish_processing_plan", return_value=(torch.device("cuda"), 2, 2)):
                gpu, _ = node.apply(image, **parameters, compute_device="cuda", batch_size=2, **options)
            torch.testing.assert_close(gpu, cpu, atol=1e-4, rtol=1e-5)
        for name, value in [("vignette_strength", -0.1), ("vignette_strength", float("nan")), ("edge_softness", 1.1), ("edge_start", 5.0)]:
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                node.apply(image, **parameters, **{name: value})

    def test_video_silent_film_finish_can_lock_to_cadence_json(self):
        """Ensure finish node can synchronize flicker/weave to cadence metadata."""
        cadence_mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_cadence")
        finish_mod = importlib.import_module("ComfyUI_ALEXZ_SilentFilm.nodes.video_silent_film_finish")

        cadence_node = cadence_mod.VideoSilentFilmCadence()
        finish_node = finish_mod.VideoSilentFilmFinish()
        frames = torch.rand(18, 10, 10, 3)

        cadence_out, cadence_json = cadence_node.apply(
            frames,
            source_fps=24.0,
            playback_mode="undercrank_projected_25fps",
            target_fps_min=16.0,
            target_fps_max=18.0,
            fps_drift_strength=0.8,
            shutter_fraction=1.0,
            motion_blur_strength=1.2,
            blur_mode="simple",
            blur_samples=9,
            seed=1925,
            cadence_model="hand_crank",
            camera_shake_strength=0.25,
        )
        finished, payload = finish_node.apply(
            cadence_out,
            tone_mode="neutral_bw",
            contrast=0.95,
            midtone_gamma=0.95,
            black_lift=0.03,
            highlight_rolloff=0.35,
            softness=0.25,
            focus_drift_strength=0.06,
            flicker_strength=0.05,
            breathing_strength=0.025,
            gate_weave_px=1.0,
            grain_mode="emulsion_luma",
            grain_strength=0.03,
            grain_size=2,
            seed=1925,
            cadence_json=cadence_json,
        )

        self.assertEqual(tuple(finished.shape[:3]), tuple(cadence_out.shape[:3]))
        data = json.loads(payload)
        self.assertEqual(data["sync_mode"], "cadence_locked")
        self.assertEqual(data["grain_mode"], "emulsion_luma")
        self.assertIn("focus_preview", data)
        self.assertGreater(float(torch.mean(torch.abs(finished - cadence_out)).item()), 0.0)

