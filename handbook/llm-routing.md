# Can an instruction model improve topic routing?

The public case engine already routes terse English observations to Identity, Endpoint, Service continuity or Telemetry. This experiment gives a frozen instruction model the same decision and the option to abstain. An accurate topic helps route work to the right team. Incident severity and customer impact are separate decisions.

## Fixed comparison

The benchmark uses the existing 24 synthetic hold-out observations across twelve wording families, with six observations per topic. The trained multinomial naïve Bayes baseline saw 48 labelled training examples. Qwen2.5-0.5B-Instruct receives topic definitions, an abstention option and one observation at a time. Its prompts contain no labelled demonstrations or expected answers. The corpus, model revision and protocol are fixed before the inference run. The existing benchmark is public and known to the project authors, so independent blind evaluation would require new data. [Original corpus](../fixtures/routing_corpus.json) · [Pinned model](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775)

For each input, Qwen scores five possible next tokens (the letters A–E). The five labels rotate across these letters so that each occupies each position once. Scores are mapped back to their labels and averaged before selecting the highest-scoring label. This ranking is equivalent to averaging the restricted log-probabilities across rotations, since each rotation's normalising term is shared by all five labels. The raw logits and per-order winners expose sensitivity to prompt order. They are uncalibrated. “Uncertain” is a competing label, with no fitted threshold.

Training frequencies are tied, so the majority baseline uses Identity, the first class in the declared order. Accuracy includes all 24 rows. Macro-F1 gives equal weight to the four real topics, and an abstention counts as a false negative on these labelled rows. The data cannot measure correct abstention on unfamiliar topics. All comparisons reflect author-written phrases, a small vocabulary and just one language. Neither model has access to the surrounding incident.

## Reproduce

With Python 3.11, CPU PyTorch 2.6.0 and Transformers 4.51.3, run `python scripts/llm_routing.py --output build/llm-routing.json`. To verify the saved label assignments, baseline predictions and metrics without downloading any model, run `python scripts/llm_routing.py --validate --output build/llm-routing.json`. The result records both dependency versions, token IDs, runner thread count, model revision, corpus and prompt hashes, five score vectors per example, and the GitHub source commit. [Scoring code](../scripts/llm_routing.py) · [Workflow](../.github/workflows/routing-experiment.yml)
