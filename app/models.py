"""The gesture network, run with ONNX Runtime on the local CPU. No network access.

    GestureNet   pre-trained HaGRIDv2 classifier (ResNet-152 or ViT-B/16): a camera frame -> static hand gesture
"""
import json
import os

import cv2
import numpy as np
import onnxruntime as ort

from paths import resource


def softmax(logits):
    z = logits - logits.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def session(path, threads):
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = threads
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(path, sess_options=opts, providers=["CPUExecutionProvider"])


GESTURE_ARCHS = ("resnet152", "vit_b16")  # in order of preference


def available_gesture_models():
    """The converted gesture models found in models/, best first."""
    return [a for a in GESTURE_ARCHS if os.path.exists(resource("models", f"gesture_{a}.onnx"))
            and os.path.exists(resource("models", f"gesture_{a}.json"))]


class GestureNet:
    def __init__(self, arch, threads=0):
        path = resource("models", f"gesture_{arch}.onnx")
        meta = json.load(open(resource("models", f"gesture_{arch}.json")))
        self.arch, self.name = arch, meta["model"]
        self.labels = meta["labels"]
        pre = meta["preprocess"]
        self.size, self.pad = pre["size"], pre["pad_value"]
        self.mean = np.array(pre["mean"], np.float32).reshape(3, 1, 1)
        self.std = np.array(pre["std"], np.float32).reshape(3, 1, 1)
        self.session = session(path, threads)
        self.predict(np.zeros((480, 640, 3), np.uint8))  # warm-up: the first run is slow

    def preprocess(self, frame_bgr):
        """As in HaGRID training: longest side to 224, grey padding to a square, RGB, normalise."""
        h, w = frame_bgr.shape[:2]
        scale = self.size / max(h, w)
        nh, nw = max(1, round(h * scale)), max(1, round(w * scale))
        resized = cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        canvas = np.full((self.size, self.size, 3), self.pad, np.uint8)
        top, left = (self.size - nh) // 2, (self.size - nw) // 2
        canvas[top:top + nh, left:left + nw] = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        x = canvas.transpose(2, 0, 1).astype(np.float32) / 255.0
        return ((x - self.mean) / self.std)[None]

    def predict(self, frame_bgr):
        """Class probabilities, in the order of self.labels."""
        return softmax(self.session.run(None, {"image": self.preprocess(frame_bgr)})[0])[0]
