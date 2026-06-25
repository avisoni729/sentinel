"""Load the sample changes and seed the store, so a fresh visitor (e.g. on the
hosted demo) immediately sees populated data."""
import json
import os

from .models import Action
from .gate import evaluate
from . import store

SAMPLES = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                       "samples", "samples.json")


def load_samples():
    with open(SAMPLES, encoding="utf-8") as f:
        return json.load(f)


def seed(reset=False):
    store.reset() if reset else store.init()
    for s in load_samples():
        d = evaluate(Action(s["id"], s["agent"], "code_pr", s["diff"]))
        store.save_decision(d)


def seed_if_empty():
    store.init()
    if not store.list_all():
        seed(reset=False)
