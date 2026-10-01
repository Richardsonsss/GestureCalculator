"""Convert a pre-trained HaGRIDv2 gesture classifier to ONNX.

    python tools/convert_hagrid.py --arch resnet152   ->  models/gesture_resnet152.onnx  +  .json
    python tools/convert_hagrid.py --arch vit_b16     ->  models/gesture_vit_b16.onnx    +  .json

The weights are the official full-frame classifiers published by the HaGRID authors
(https://github.com/hukenovs/hagrid). Nothing is trained here: the checkpoint is loaded into the matching
torchvision architecture, exported, and the ONNX output is compared with PyTorch.
Development-time only; the calculator ships with the exported file and never needs the internet.
"""
import argparse
import json
import os
import urllib.request

import numpy as np
import torch
import torchvision

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://rndml-team-cv.obs.ru-moscow-1.hc.sbercloud.ru/datasets/hagrid_v2/models/"
# arch -> (checkpoint file, description, F1 on the HaGRIDv2 test set as published by the authors)
ARCHS = {
    "resnet152": ("ResNet152.pth", "HaGRIDv2 ResNet-152 full-frame classifier", 98.6),
    "vit_b16": ("VitB16.pth", "HaGRIDv2 ViT-B/16 full-frame classifier", 91.7),
}
# class order of the HaGRIDv2 models (constants.py in the HaGRID repository)
TARGETS = ["grabbing", "grip", "holy", "point", "call", "three3", "timeout", "xsign", "hand_heart", "hand_heart2",
           "little_finger", "middle_finger", "take_picture", "dislike", "fist", "four", "like", "mute", "ok", "one",
           "palm", "peace", "peace_inverted", "rock", "stop", "stop_inverted", "three", "three2", "two_up",
           "two_up_inverted", "three_gun", "thumb_index", "thumb_index2", "no_gesture"]
# preprocessing of the HaGRID configurations (the same in configs/VitB16.yaml and configs/ResNet152.yaml)
PREPROCESS = {"size": 224, "mean": [0.54, 0.499, 0.474], "std": [0.234, 0.235, 0.231], "pad_value": 144,
              "color": "RGB"}


def build(arch, state):
    """The torchvision network with the HaGRID head, loaded from the checkpoint's state dict."""
    # the HaGRID wrappers nest the torchvision model as hagrid_model (ResNet) or hagrid_model.hagrid_model (ViT)
    state = {k.replace("hagrid_model.", "").replace("module.", ""): v for k, v in state.items()}
    if arch == "vit_b16":
        classes = state["heads.head.weight"].shape[0]
        model = torchvision.models.vit_b_16(weights=None)
        model.heads = torch.nn.Sequential()
        model.heads.add_module("head", torch.nn.Linear(model.hidden_dim, classes))
    else:
        classes = state["fc.weight"].shape[0]
        model = torchvision.models.resnet152(weights=None)
        model.fc = torch.nn.Linear(model.fc.in_features, classes)
    model.load_state_dict(state, strict=True)
    return model.eval(), classes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arch", choices=list(ARCHS), default="resnet152")
    args = ap.parse_args()
    filename, description, f1 = ARCHS[args.arch]
    checkpoint = os.path.join(ROOT, "tools", "downloads", filename)
    out = os.path.join(ROOT, "models", f"gesture_{args.arch}.onnx")

    if not os.path.exists(checkpoint):
        os.makedirs(os.path.dirname(checkpoint), exist_ok=True)
        print("downloading", BASE + filename)
        urllib.request.urlretrieve(BASE + filename, checkpoint)
    snapshot = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model, classes = build(args.arch, snapshot.get("MODEL_STATE", snapshot))
    labels = TARGETS[:classes]
    print(f"loaded {args.arch} with {classes} classes, {sum(p.numel() for p in model.parameters()) / 1e6:.1f} M parameters")

    os.makedirs(os.path.dirname(out), exist_ok=True)
    dummy = torch.zeros(1, 3, 224, 224)
    torch.onnx.export(model, (dummy,), out, input_names=["image"], output_names=["logits"], opset_version=18,
                      dynamo=True, external_data=False, verbose=False)

    import onnxruntime as ort

    session = ort.InferenceSession(out, providers=["CPUExecutionProvider"])
    diff = 0.0
    for _ in range(3):  # the app classifies one frame at a time, so the export has batch size 1
        x = torch.randn(1, 3, 224, 224)
        with torch.no_grad():
            reference = model(x).numpy()
        diff = max(diff, float(np.abs(session.run(None, {"image": x.numpy()})[0] - reference).max()))
    print(f"exported {out}  ({os.path.getsize(out) / 1e6:.0f} MB), max difference to PyTorch {diff:.2e}")
    if diff > 1e-3:
        raise SystemExit("ONNX output does not match PyTorch")
    meta = {"model": description, "arch": args.arch, "published_f1": f1, "source": BASE + filename, "labels": labels,
            "preprocess": PREPROCESS, "onnx_max_abs_difference": diff}
    json.dump(meta, open(os.path.splitext(out)[0] + ".json", "w"), indent=2)


if __name__ == "__main__":
    main()
