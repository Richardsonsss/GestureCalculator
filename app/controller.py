"""Turns hand tracking into calculator keys. Both hands show static gestures; they have separate jobs:

    left hand                 a gesture held still  -> digit, '.', '=', DEL, AC
    right hand on the board   two digits, tens first -> the operator with that code (operators.py)

Pure logic: no camera, no window, no neural network. GestureInput is fed one hand observation per frame and
the gesture probabilities it asks for, and returns events. That keeps it testable with scripted input.
"""
from dataclasses import dataclass

import numpy as np

from gestures import GESTURE_KEYS

WRIST, INDEX_MCP, INDEX_TIP, MIDDLE_MCP, RING_MCP, PINKY_MCP = 0, 5, 8, 9, 13, 17
# (base, middle joint, tip) of thumb, index, middle, ring, little finger
FINGERS = ((2, 3, 4), (5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20))


@dataclass
class Settings:
    dwell: float = 1.0             # seconds of stillness that enter a character (left hand)
    still_radius: float = 0.25     # "still" = staying inside this radius (in hand sizes)
    move_grace: float = 0.15       # seconds after the last movement during which the hand counts as moving
    lost_after: float = 0.4        # seconds without the hand before its state is reset
    rearm_distance: float = 0.5    # after an entry, moving this far (hand sizes) allows the next entry
    pose_change: float = 0.35      # ... or a new hand shape that lasts this long
    pose_restart: float = 0.15     # a hand shape that changes for this long restarts the pause
    gesture_mass: float = 0.3      # the gesture network must give the calculator gestures at least this much
    gesture_share: float = 0.5     # and the best one this share of it
    min_gesture_votes: int = 2


def right_hand_settings(left):
    """The right hand answers faster than the left: half the pause, and a new shape counts sooner."""
    return Settings(dwell=left.dwell / 2, still_radius=left.still_radius, move_grace=left.move_grace,
                    lost_after=left.lost_after, rearm_distance=left.rearm_distance, pose_change=0.2,
                    gesture_mass=left.gesture_mass, gesture_share=left.gesture_share,
                    min_gesture_votes=left.min_gesture_votes)


@dataclass
class GestureStatus:
    mode: str = "idle"             # idle | moving | hold | wait
    progress: float = 0.0          # 0..1 of the dwell time
    guess: str = ""                # live guess


def finger_states(lm):
    """(thumb, index, middle, ring, little) extended?  A finger is extended when it is roughly straight.

    Works on 2-D pixel landmarks and, better, on MediaPipe's 3-D world landmarks: the bend of a finger does
    not depend on where the hand points.
    """
    states = []
    for base, middle, tip in FINGERS:
        a, b = lm[middle] - lm[base], lm[tip] - lm[middle]
        cosine = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
        states.append(cosine > 0.5)  # bent by less than 60 degrees
    return tuple(states)


def hand_size(lm):
    return max(float(np.linalg.norm(np.asarray(lm[WRIST]) - np.asarray(lm[MIDDLE_MCP]))), 1e-3)


class Stillness:
    """Still or moving? A point is still while it stays inside a small circle around where it came to rest.

    Judging the position, not the speed, keeps the timer running through the small tremor of a raised hand.
    """

    def __init__(self, settings):
        self.s = settings
        self.reset()

    def reset(self):
        self.anchor = None
        self.count = 0
        self.since = None
        self.last_move = None
        self.moving = False

    def update(self, t, points, size):
        """points: one or more positions that must all stay put. Returns True when a movement just restarted
        the timer."""
        points = [np.asarray(p, dtype=np.float32) for p in points]
        if self.anchor is None:
            self.anchor, self.since, self.count = points, t, 1
        offset = max(np.linalg.norm(p - a) for p, a in zip(points, self.anchor)) / size
        moved = offset > self.s.still_radius
        if moved:
            self.anchor, self.since, self.last_move, self.count = points, t, t, 1
        else:
            # the centre of the resting place: the average of where the points have been since they stopped,
            # not the last position of the movement that brought them here
            self.count += 1
            self.anchor = [a + (p - a) / self.count for p, a in zip(points, self.anchor)]
        self.moving = self.last_move is not None and t - self.last_move < self.s.move_grace
        return moved

    def held(self, t):
        return 0.0 if self.moving or self.since is None else t - self.since


class GestureInput:
    """One hand: a gesture held still for the dwell time enters a key.

    allowed: the keys this hand may enter (None = all of gestures.GESTURE_KEYS). The right hand only enters
    digits; whatever else the network sees there counts as no gesture.
    """

    def __init__(self, settings=None, allowed=None):
        self.s = settings or Settings()
        self.allowed = allowed
        self.still = Stillness(self.s)
        self.reset()

    def reset(self):
        self.still.reset()
        self.last_seen = None
        self.armed = True
        self.commit_at = None          # (palm centre, index tip) at the last entry
        self.commit_pose = None
        self.pose_changed_since = None
        self.poses = {}                # hand shapes seen while the hand has been still: shape -> frames
        self.pose = None               # the shape the running pause belongs to
        self.pose_new_since = None
        self.votes = []                # per gesture-network answer: probability of each calculator key
        self.raw_sum, self.labels, self.mass = None, None, 0.0
        self.status = GestureStatus()

    # ------------------------------------------------------------ neural network hand-off
    @property
    def wants_gesture(self):
        """True while the gesture network should look at the camera frames."""
        return self.last_seen is not None and self.still.since is not None and not self.still.moving and self.armed

    def add_gesture_probs(self, t, probs, labels):
        """A result of the gesture network for a frame captured at time t."""
        if self.still.since is None or t < self.still.since or not self.armed:
            return
        keys = {}
        for label, p in zip(labels, probs):
            key = GESTURE_KEYS.get(label)
            if key is not None and (self.allowed is None or key in self.allowed):
                keys[key] = keys.get(key, 0.0) + float(p)
        self.votes.append(keys)
        probs = np.asarray(probs, dtype=np.float64)
        self.raw_sum = probs if self.raw_sum is None else self.raw_sum + probs
        self.labels = list(labels)
        best, _, accepted = self.judge()
        self.status.guess = best if accepted else ""

    def judge(self):
        """(best key, its mean probability, accepted?) over the answers collected while the hand was still."""
        keys = {}
        for vote in self.votes:
            for key, p in vote.items():
                keys[key] = keys.get(key, 0.0) + p / len(self.votes)
        if not keys:  # the network knows none of this hand's gestures
            self.mass = 0.0
            return "", 0.0, False
        best = max(keys, key=keys.get)
        self.mass = sum(keys.values())  # the rest went to gestures the calculator does not use, or "no gesture"
        accepted = self.mass >= self.s.gesture_mass and keys[best] / self.mass >= self.s.gesture_share
        return best, keys[best], accepted

    def clear_votes(self):
        self.votes, self.raw_sum, self.status.guess = [], None, ""

    # ------------------------------------------------------------ per frame
    def update(self, t, landmarks, world=None):
        """landmarks: the hand [21, 2] in pixels, or None. world: its 3-D landmarks, when available.
        Returns events: {"type": "key" | "unknown", "source": "gesture", ...}."""
        if landmarks is None:
            if self.last_seen is not None and t - self.last_seen > self.s.lost_after:
                self.reset()
            return []
        lm = np.asarray(landmarks, dtype=np.float32)
        center = lm[[WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]].mean(axis=0)
        tip = lm[INDEX_TIP]
        size = hand_size(lm)
        pose = finger_states(np.asarray(world, dtype=np.float32) if world is not None else lm)
        self.last_seen = t

        if self.still.update(t, (center, tip), size):
            self.clear_votes()
            self.poses = {}
            self.pose, self.pose_new_since = pose, None
        # The pause belongs to one hand shape. When the fingers change without the hand moving, the pause
        # starts again, so a shape shown in passing is not mixed into the next one.
        if self.pose is None or pose == self.pose:
            self.pose, self.pose_new_since = pose, None
        elif self.pose_new_since is None:
            self.pose_new_since = t
        elif t - self.pose_new_since >= self.s.pose_restart:
            self.still.since, self.still.count = self.pose_new_since, 1
            self.pose, self.pose_new_since = pose, None
            self.clear_votes()
            self.poses = {}
        self.poses[pose] = self.poses.get(pose, 0) + 1

        # after an entry: wait until the hand moves away or changes shape, so nothing is entered twice
        if not self.armed:
            away = max(np.linalg.norm(center - self.commit_at[0]), np.linalg.norm(tip - self.commit_at[1])) / size
            # a new shape must last: a finger state that flickers for a frame must not enter the key again
            if pose == self.commit_pose:
                self.pose_changed_since = None
            elif self.pose_changed_since is None:
                self.pose_changed_since = t
            if away > self.s.rearm_distance:
                self.armed = True
            elif self.pose_changed_since is not None and t - self.pose_changed_since >= self.s.pose_change:
                self.armed = True
                self.still.anchor, self.still.since = [center, tip], self.pose_changed_since  # pause counts from then
                self.still.count = 1
                self.clear_votes()
                self.poses = {}

        events = []
        held = self.still.held(t)
        if self.armed and held >= self.s.dwell and self.pose_new_since is None:  # not while the fingers change
            event = self.commit(held)
            if event is not None:
                events.append(event)
                self.armed, self.commit_at = False, (center, tip)
                self.commit_pose = max(self.poses, key=self.poses.get)  # the shape shown for most of the pause
                self.pose_changed_since = None
                self.clear_votes()
        self.status.mode = "wait" if not self.armed else "moving" if self.still.moving else "hold"
        self.status.progress = min(held / self.s.dwell, 1.0) if self.armed else 0.0
        return events

    def commit(self, held):
        if len(self.votes) < self.s.min_gesture_votes:
            return None  # the gesture network has not answered yet: keep waiting
        best, confidence, accepted = self.judge()
        mean = self.raw_sum / len(self.votes)
        order = np.argsort(mean)[::-1][:3]
        detail = {"hold": round(held, 2), "votes": len(self.votes),
                  "top": [(self.labels[i], round(float(mean[i]), 3)) for i in order]}
        if not accepted:
            # weak: the network saw none of the calculator gestures (a resting hand) - not worth a message
            return {"type": "unknown", "source": "gesture", "guess": best, "confidence": float(confidence),
                    "weak": bool(self.mass < self.s.gesture_mass), "detail": detail}
        return {"type": "key", "key": best, "source": "gesture", "confidence": float(confidence), "detail": detail}
