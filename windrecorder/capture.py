"""Frame comparison and exclusive cache maintenance, without desktop access."""

import os
from contextlib import contextmanager
from pathlib import Path

import cv2
import numpy as np


@contextmanager
def cache_maintenance_lock(cache_root):
    """One converter/cleaner per cache root; Windows releases it after a crash."""
    import msvcrt

    root = Path(cache_root)
    root.mkdir(parents=True, exist_ok=True)
    # Lock before writing, including on first creation. Windows can lock beyond EOF.
    with os.fdopen(os.open(root / ".maintenance.lock", os.O_CREAT | os.O_RDWR), "r+b") as stream:
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


class FrameChangeDetector:
    """Reuse the accepted frame's ORB features; failed OCR must not advance it."""

    def __init__(self):
        self.orb = cv2.ORB_create()
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.previous = None
        self.previous_features = None
        self.current = None
        self.current_features = None

    def _features(self, gray):
        keypoints, descriptors = self.orb.detectAndCompute(gray, None)
        return len(keypoints), descriptors

    def compare(self, image):
        self.current = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        self.current_features = None
        if self.previous is None or self.previous.shape != self.current.shape:
            return 0.0
        if np.array_equal(self.previous, self.current):
            self.current_features = self.previous_features
            return 1.0
        if self.previous_features is None:
            self.previous_features = self._features(self.previous)
        self.current_features = self._features(self.current)
        previous_count, previous_descriptors = self.previous_features
        current_count, current_descriptors = self.current_features
        if previous_descriptors is None or current_descriptors is None:
            # A changed blank/low-texture frame is worth capturing, not an error.
            return 0.0
        matches = self.matcher.match(previous_descriptors, current_descriptors)
        return len(matches) / max(previous_count, current_count)

    def accept(self):
        self.previous = self.current
        self.previous_features = self.current_features
