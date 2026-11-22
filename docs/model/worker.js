const library = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1";
let generator;
let protocol;

function messages(reason, events) {
  const lines = events.map((event, i) => protocol.labels[i] + ": " + event.source + " — " + event.text);
  const content = ["Current finding: " + reason, "Observations:", ...lines,
    "X: Insufficient evidence.", protocol.question].join("\n");
  return [{role:"system", content:protocol.system}, {role:"user", content}];
}

function parse(answer, events) {
  const match = /^([A-Z])\.?$/.exec(answer.trim());
  if (!match) return null;
  if (match[1] === protocol.abstain) return "abstain";
  const index = protocol.labels.indexOf(match[1]);
  return events[index]?.id ?? null;
}

async function answer(reason, events) {
  const prompt = generator.tokenizer.apply_chat_template(messages(reason, events), {
    tokenize:false, add_generation_prompt:true
  });
  const output = await generator(prompt, {
    do_sample:false, max_new_tokens:4, return_full_text:false, add_special_tokens:false
  });
  return output[0].generated_text.trim();
}

self.onmessage = async ({data}) => {
  const {job, events, reason} = data;
  const status = message => self.postMessage({job, kind:"status", message});
  try {
    if (!protocol) {
      const res = await fetch(new URL("./protocol.json", import.meta.url));
      if (!res.ok) throw new Error("Protocol unavailable");
      protocol = await res.json();
    }
    if (!Array.isArray(events) || !events.length || events.length > protocol.labels.length) throw new Error("Invalid input");
    if (!generator) {
      const {pipeline, env} = await import(library);
      env.allowLocalModels = false;
      env.backends.onnx.wasm.numThreads = 1;
      generator = await pipeline("text-generation", protocol.model_id, {
        revision:protocol.revision, device:"wasm", dtype:"int8",
        progress_callback: info => {
          if (info.status === "progress" && /\.onnx$/.test(info.file) && info.total > 0) {
            status("Downloading model weights · " + Math.floor(100 * info.loaded / info.total) + "%");
          }
        }
      });
    }
    status("Checking evidence in chronological order…");
    const forward = await answer(reason, events);
    const reverseOrder = [...events].reverse();
    if (events.length > 1) status("Checking in reverse order…");
    const reverse = events.length === 1 ? forward : await answer(reason, reverseOrder);
    const a = parse(forward, events), b = parse(reverse, reverseOrder);
    let id = null, explanation;
    if (a === null || b === null) explanation = "Model output did not identify a valid choice";
    else if (a === "abstain" || b === "abstain") explanation = "The model abstained";
    else if (a !== b) explanation = "Changing the order changed its choice";
    else { id = a; explanation = events.length === 1 ? "One observed candidate, scored once" : "Both orders identified the same event"; }
    self.postMessage({job, kind:"result", id, reason:explanation, responses:[forward, reverse]});
  } catch {
    self.postMessage({job, kind:"error"});
  }
};
