const byId = id => document.getElementById(id);
const controls = {
  case: byId("case"), step: byId("step"), run: byId("run"), cancel: byId("cancel")
};
const state = byId("state");
let scenarios = [];
let worker;
let running = false;
let ready = false;
let job = 0;

function selectState() {
  const scenario = scenarios.find(item => item.id === controls.case.value);
  const index = Number(controls.step.value) - 1;
  const events = scenario.events.slice(0, index + 1);
  const frame = scenario.frames[index];
  if (!frame || JSON.stringify(frame.event_ids) !== JSON.stringify(events.map(item => item.id))) {
    throw new Error("The replay does not match its event source.");
  }
  return {scenario, frame, events};
}

function showCase() {
  const {frame, events} = selectState();
  byId("result").hidden = true;
  byId("reason").textContent = frame.reason;
  byId("events").replaceChildren(...events.map(event => {
    const li = document.createElement("li");
    const source = document.createElement("strong");
    source.textContent = event.id + " · " + event.source;
    li.append(source, document.createTextNode(event.text));
    return li;
  }));
  state.textContent = ready ? "Model loaded on this device." : "Model has not been loaded.";
}

function setSteps(requested) {
  const scenario = scenarios.find(item => item.id === controls.case.value);
  controls.step.replaceChildren(...scenario.frames.map((_, i) => new Option("Step " + (i + 1), String(i + 1))));
  const valid = Number.isInteger(requested) && requested >= 1 && requested <= scenario.frames.length;
  controls.step.value = String(valid ? requested : scenario.frames.length);
  showCase();
}

function setBusy(value) {
  running = value;
  for (const item of [controls.case, controls.step, controls.run]) item.disabled = value;
  controls.cancel.hidden = !value;
}

function terminate() {
  if (worker) worker.terminate();
  worker = null;
  ready = false;
  controls.run.textContent = "Load model and run";
}

function fail() {
  terminate();
  setBusy(false);
  state.textContent = "Inference could not finish. Check model-download access and available memory, then retry. The case review is still available.";
}

function run() {
  if (running) return;
  const {frame, events} = selectState();
  byId("result").hidden = true;
  setBusy(true);
  state.textContent = ready ? "Reading the observed events…" : "Loading model files…";
  job += 1;
  const myJob = job;
  try {
    worker ||= new Worker(new URL("./worker.js", import.meta.url), {type:"module"});
    worker.onerror = () => { if (myJob === job) fail(); };
    worker.onmessage = ({data}) => {
      if (data.job !== myJob || job !== myJob) return;
      if (data.kind === "error") return fail();
      if (data.kind === "status") { state.textContent = data.message; return; }
      if (data.kind !== "result") return;
      const event = events.find(item => item.id === data.id);
      if (data.id !== null && !event) return fail();
      ready = true;
      setBusy(false);
      controls.run.textContent = "Run again";
      state.textContent = "Completed on this device · WASM int8";
      byId("outcome").textContent = event ? "Model selected " + event.id : "No model selection";
      byId("excerpt").hidden = !event;
      byId("excerpt").textContent = event ? event.text : "";
      byId("trace").textContent = data.reason + ". Forward answer: " + JSON.stringify(data.responses[0]) +
        ". Reverse answer: " + JSON.stringify(data.responses[1]) + ".";
      byId("result").hidden = false;
    };
    worker.postMessage({job:myJob, reason:frame.reason,
      events:events.map(({id, source, text}) => ({id, source, text}))});
  } catch { fail(); }
}

controls.run.addEventListener("click", run);
controls.cancel.addEventListener("click", () => {
  job += 1; terminate(); setBusy(false); state.textContent = "Run cancelled.";
});
controls.case.addEventListener("change", () => setSteps());
controls.step.addEventListener("change", showCase);

try {
  const response = await fetch("data/scenarios.json");
  if (!response.ok) throw new Error();
  scenarios = (await response.json()).scenarios;
  controls.case.replaceChildren(...scenarios.map(item => new Option(item.id + " · " + item.title, item.id)));
  const query = new URLSearchParams(location.search);
  if (scenarios.some(s => s.id === query.get("case"))) controls.case.value = query.get("case");
  setSteps(Number(query.get("step")));
  setBusy(false);
} catch {
  state.textContent = "Case data could not be loaded. Open this page from the hosted demo or a local web server.";
}
