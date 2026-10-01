# Gesture Calculator

A scientific calculator you operate with hand gestures in front of a webcam. It is a Windows program that runs
**entirely offline**: the neural network is stored on the computer, no picture leaves it, and the program writes
no files.

- **Left hand: digits.** A static gesture held still for 1 second enters a digit, `.`, `=`, DEL or AC.
- **Right hand: operators.** On a whiteboard in the top right of the camera picture, the right hand shows **two
  digits**, tens first. The two digits are the code of an operator or function (`10` = sin, `01` = +).
- The right hand answers **faster** than the left: 0.5 second per digit.
- All gestures are recognised by a pre-trained **ResNet-152** (HaGRIDv2); the pre-trained **ViT-B/16** of the same
  authors can be used instead.
- The keyboard works as well.
- Open source, for non-commercial use ([licence](LICENSE.md)).

The illustrated user manual is [manual.docx](manual.docx).

## Get it

Download `GestureCalculator-windows.zip` from [Releases](../../releases), unzip it and double-click
`GestureCalculator.exe`. It needs Windows 10/11 and a webcam - no Python, no installation, no internet
connection. Keep `GestureCalculator.exe`, `_internal\` and `models\` together.

To run it from the source code instead, see [Run from the source code](#run-from-the-source-code).

## How to enter a calculation

| You do | Result |
|---|---|
| Left hand: hold a gesture still for 1 s | a digit, `.`, `=`, DEL or AC |
| Left hand: change to another gesture and hold it | the next character |
| Left hand: move the hand aside and back, then hold the same gesture | the same character again (for `55`) |
| Right hand on the whiteboard: hold a digit gesture for 0.5 s | the tens digit of the code; it appears in the left half of the board |
| Right hand: change to the next digit gesture, hold 0.5 s | the units digit, in the right half; the operator with that code is entered and its name is shown |

Rules for the right hand:

- It counts only while its palm is on the whiteboard, and it can only enter code digits.
- A tens digit that is not followed by a units digit within 6 seconds is dropped. To cancel a wrong tens digit,
  take the hand off the board and wait.
- A code that does not exist enters nothing. A wrong operator is removed with DEL (left hand, thumb down).

Left-handed? Tick **Swap hands**.

**Left hand - gestures** (the right hand uses the same ten digit gestures)

| Enters | Gesture | Enters | Gesture |
|---|---|---|---|
| 0 | fist | 7 | thumb + index + middle |
| 1 | index finger up | 8 | thumb + index (L shape) |
| 2 | index + middle (V) | 9 | OK sign |
| 3 | index + middle + ring | . | little finger up |
| 4 | four fingers, thumb folded | = | thumb up |
| 5 | open palm | DEL | thumb down |
| 6 | thumb + little finger | AC | both forearms crossed (X), away from the whiteboard |

**Right hand - operator codes** (tens digit first)

| Basic | Trigonometry | Logs and powers | Constants, other | Settings |
|---|---|---|---|---|
| `01` + | `10` sin | `20` log | `30` π | `40` DEG / RAD / GRA |
| `02` − | `12` cos | `21` ln | `31` e | `41` decimal ⇔ fraction |
| `03` × | `13` tan | `23` 10ˣ | `32` Ans | |
| `04` ÷ | `14` sin⁻¹ | `24` eˣ | `34` Abs | |
| `05` ( | `15` cos⁻¹ | `25` x² | `35` nPr | |
| `06` ) | `16` tan⁻¹ | `26` x³ | `36` nCr | |
| `07` ^ | `17` sinh | `27` x⁻¹ | `37` ×10ˣ | |
| `08` √ | `18` cosh | `28` ∛ | `38` save to memory | |
| `09` % | `19` tanh | `29` x! | `39` recall memory | |

The tens digit names the group. There are no codes with the same digit twice (11, 22, 33), so the right hand
never has to show one gesture twice in a row. The table is also printed in the window, under the camera picture.

**Example,** `sin(30)+5`:

| Step | Hand | Gestures | Display |
|---|---|---|---|
| 1 | right | 1, 0 (code 10) | `sin(` |
| 2 | left | 3, then 0 | `sin(30` |
| 3 | right | 0, 6 (code 06) | `sin(30)` |
| 4 | right | 0, 1 (code 01) | `sin(30)+` |
| 5 | left | 5 | `sin(30)+5` |
| 6 | left | thumb up (=) | `5.5` |

**Tips**

- Sit 40–80 cm from the camera, in good light. Keep the left hand outside the whiteboard.
- Change from one gesture to the next in one clear movement: a hand shape shown only in passing is ignored.
- A ring around the hand shows the pause running. When a gesture is not recognised, the line under the camera
  picture shows the closest guess.
- **Pause** (under the camera picture) sets how long the left hand must be still, 1.0 s by default; the right hand
  always needs half of it.

## Calculator functions

The window has no on-screen keypad: everything is entered by gesture or from the keyboard.

| Entered by | Functions |
|---|---|
| left hand | digits `0`–`9`, `.`, `=`, `DEL`, `AC` |
| right hand, by code | `+ − × ÷`, `( )`, power, `x²`, `x³`, `x⁻¹`, `√`, `∛`, `%`, `x!`, `sin cos tan` with inverses and hyperbolic forms, `log`, `ln`, `10ˣ`, `eˣ`, `π`, `e`, `Ans`, `Abs`, `nPr`, `nCr`, `×10ˣ`, memory, angle unit, decimal ⇔ fraction |
| keyboard | digits, `+ - * / ( ) ^ ! % .`, Enter (=), Backspace (DEL), Esc (AC), `D` (DEG / RAD / GRA), `F` (decimal ⇔ fraction) |

- Implied multiplication works: `2π`, `3sin(30)`. A missing `)` at the end is allowed.
- Results have 10 significant digits. Errors show as `Math ERROR` or `Syntax ERROR`, like a pocket calculator.
- "Save to memory" stores the result (working out an unfinished expression first); "recall memory" puts the
  stored value into the expression.

Not included: matrix, vector, statistics, complex-number and base-N modes, equation solving, integration.

## How it works

```
webcam frame ──► MediaPipe: both hands, 21 landmarks each
                    │
   left hand  ──► still for 1 s ─────► ResNet-152 on the frame ──► digit / . / = / DEL / AC ─────────┐
                                       (the right hand is painted over)                              │
   right hand ──► on the whiteboard, ► ResNet-152 on the frame ──► digit ─► tens + units = code ─► operator
                  still for 0.5 s      (the left hand is painted over)                               │
                                                                        calculator engine ◄──────────┘ ──► display
```

1. **Hand tracking.** MediaPipe finds both hands and tells the left hand from the right.
2. **Stillness.** A hand is still while its palm and index fingertip stay inside a small circle, and its shape
   does not change. That starts the pause.
3. **One hand per look.** The gesture network looks at the whole camera picture and names one gesture, so each
   hand gets its own pass with the other hand painted over in grey.
4. **Decision.** The answers of all frames of the pause are averaged. The key is entered when the network is
   clear enough; then the hand has to change its gesture or move away before it can enter the next one.

Measured on the development laptop (CPU): ResNet-152 36 ms per frame, ViT-B/16 67 ms, hand tracking 8 ms. The
laptop's webcam delivers about 15 pictures a second indoors.

## Models

The files live in `models/` and are loaded with ONNX Runtime / MediaPipe on the CPU. Nothing is trained: the
gesture networks are the checkpoints published by the HaGRID authors, converted to ONNX.

| File | What it is | Where it comes from |
|---|---|---|
| `hand_landmarker.task` | MediaPipe hand tracker (21 landmarks per hand): finds both hands and tells left from right | Google, pre-trained; in this repository |
| `gesture_resnet152.onnx` | **ResNet-152** full-frame gesture classifier, 34 classes, pre-trained on HaGRIDv2 (1 M images); published F1 98.6. Used by default | HaGRID checkpoint, converted with `tools/convert_hagrid.py --arch resnet152` |
| `gesture_vit_b16.onnx` | **ViT-B/16**, same classes and data; published F1 91.7. Optional alternative | `tools/convert_hagrid.py --arch vit_b16` |

The two gesture networks are **not in this repository** (233 MB and 344 MB, above GitHub's file size limit).
The release zip contains ResNet-152; from the source code, create it as shown below.

## Run from the source code

```powershell
# 1. environment
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 2. the gesture network, once: downloads the published HaGRID checkpoint and converts it
.venv\Scripts\python -m pip install -r tools\requirements-convert.txt
.venv\Scripts\python tools\convert_hagrid.py --arch resnet152     # -> models\gesture_resnet152.onnx

# 3. start
.venv\Scripts\python app\main.py
```

| Option | Effect |
|---|---|
| `--camera 1` | use another webcam |
| `--no-camera` | keyboard only |
| `--gesture-model vit_b16` | use ViT-B/16 instead of ResNet-152 (convert it first with `--arch vit_b16`) |

Build the stand-alone program:

```powershell
.venv\Scripts\python -m pip install pyinstaller
pwsh build_exe.ps1                          # -> GestureCalculator.exe and _internal\ in the project root
```

| Folder | Content |
|---|---|
| `app/` | `engine.py` calculator, `operators.py` operator codes, `gestures.py` gesture → key, `controller.py` input logic, `vision.py` camera thread, `models.py` ONNX model, `ui.py` window |
| `tools/` | `convert_hagrid.py` (checkpoint → ONNX) |
| `tests/` | calculator engine, operator codes and input-logic tests (`pytest`) |
| `docs/` | sources of `manual.docx`: text, diagrams, and `update_manual.ps1` to rebuild it |

## Limitations

- The HaGRID gestures were not designed as digits: 6–9 use the closest HaGRID classes (gesture table above).
- One person in the picture. MediaPipe tells the left hand from the right; when it gets that wrong, an entry is
  missed or goes to the other hand.
- Gesture recognition by the right hand on the whiteboard has only been checked with scripted input so far.

## Licence and credits

The source code is public and free to use, change and share for **non-commercial purposes**, under the
[PolyForm Noncommercial License 1.0.0](LICENSE.md).

The gesture models are the HaGRIDv2 ResNet-152 and ViT-B/16, published by the HaGRID project
([github.com/hukenovs/hagrid](https://github.com/hukenovs/hagrid)); they have their own licence (a variant of
CC BY-SA 4.0). Hand tracking: [MediaPipe](https://ai.google.dev/edge/mediapipe) (Apache-2.0). Window: Qt for
Python / PySide6 (LGPL).
