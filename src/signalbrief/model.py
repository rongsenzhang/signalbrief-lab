"""A small inspectable multinomial naive Bayes router. No trained network is downloaded."""
import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
STOP = set("a an the after again about as and are at by could did for from has have in is it no not of on or our same that their there this to was were with".split())
MIN_SCORE = 0.55


def tokens(text):
    return [w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP]


class Router:
    def __init__(self, examples):
        self.counts = {label: Counter(word for phrase in phrases for word in tokens(phrase))
                       for label, phrases in examples.items()}
        self.words = set().union(*(counts.keys() for counts in self.counts.values()))
        rows = sum(len(phrases) for phrases in examples.values())
        self.priors = {label: math.log(len(phrases) / rows) for label, phrases in examples.items()}
        self.weights = {}
        for label, counts in self.counts.items():
            denominator = sum(counts.values()) + len(self.words)
            self.weights[label] = {word: math.log((counts[word] + 1) / denominator) for word in self.words}

    def predict(self, text):
        known = [word for word in tokens(text) if word in self.words]
        logs = {label: prior + sum(self.weights[label][word] for word in known)
                for label, prior in self.priors.items()}
        top = max(logs, key=logs.get)
        score = 1.0 / sum(math.exp(value - logs[top]) for value in logs.values())
        label = top if known and score >= MIN_SCORE else "Uncertain"
        return {"label": label, "score": round(score, 4)}


@lru_cache(maxsize=1)
def router():
    with (FIXTURES / "routing_corpus.json").open() as file:
        return Router(json.load(file)["train"])
