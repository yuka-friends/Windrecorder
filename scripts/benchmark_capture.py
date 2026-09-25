"""Compare ORB work on synthetic frames; never access the desktop or user data."""

import json
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from windrecorder.capture import FrameChangeDetector  # noqa: E402


def legacy_compare(first, second):
    orb = cv2.ORB_create()
    first_keys, first_desc = orb.detectAndCompute(cv2.cvtColor(first, cv2.COLOR_BGR2GRAY), None)
    second_keys, second_desc = orb.detectAndCompute(cv2.cvtColor(second, cv2.COLOR_BGR2GRAY), None)
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(first_desc, second_desc)
    matches = sorted(matches, key=lambda match: match.distance)
    return len(matches) / max(len(first_keys), len(second_keys))


def benchmark(frames):
    measurements = {"legacy_seconds": [], "cached_seconds": []}
    for _ in range(3):
        started = time.perf_counter()
        expected = [legacy_compare(first, second) for first, second in zip(frames, frames[1:])]
        measurements["legacy_seconds"].append(time.perf_counter() - started)
        detector = FrameChangeDetector()
        started = time.perf_counter()
        detector.compare(frames[0])
        detector.accept()
        actual = []
        for frame in frames[1:]:
            actual.append(detector.compare(frame))
            detector.accept()
        measurements["cached_seconds"].append(time.perf_counter() - started)
        np.testing.assert_allclose(actual, expected)
    return {name: statistics.median(values) for name, values in measurements.items()}


if __name__ == "__main__":
    frame = np.random.default_rng(42).integers(0, 256, (480, 854, 3), dtype=np.uint8)
    print(
        json.dumps(
            {
                "comparisons": 20,
                "static": benchmark([frame] * 21),
                "changing": benchmark([np.roll(frame, offset, axis=0) for offset in range(21)]),
                "similarities_equal": True,
            },
            indent=2,
        )
    )
