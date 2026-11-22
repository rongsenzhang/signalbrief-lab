"use strict";

const el = id => document.getElementById(id);
let examples = {};
let live = false;
let requestNumber = 0;

function clearResult(message) {
  el("out").hidden = true;
  el("priority").textContent = "";
  el("sources").replaceChildren();
  el("response").textContent = "";
  el("response-title").textContent = "Response";
  el("status").textContent = message;
}

function currentExample() {
  const report = document.querySelector("input[name=report]:checked").value;
  return examples[report + "-" + el("minutes").value];
}

function updateRequest() {
  requestNumber++;
  const example = currentExample();
  if (!example) return;
  el("request").textContent = JSON.stringify(example.request, null, 2);
  clearResult(live ? "Ready to send the selected events to your local API." : "Ready to inspect this published API example.");
  el("run").disabled = live && !el("token").value;
}

async function inspect() {
  const number = ++requestNumber;
  const example = currentExample();
  el("run").disabled = true;
  try {
    let response = example.response;
    if (live) {
      const res = await fetch("/v1/triage", {
        method: "POST", cache: "no-store", redirect: "error", credentials: "omit",
        headers: {"Content-Type": "application/json", Authorization: "Bearer " + el("token").value},
        body: JSON.stringify(example.request)
      });
      if (number !== requestNumber) return;
      if (!res.ok) throw Error(res.status === 401 ? "The local API rejected this token (HTTP 401)." : "The local API returned HTTP " + res.status + ".");
      response = await res.json();
    }
    if (number !== requestNumber) return;
    const last = response.frames[response.frames.length - 1];
    el("priority").textContent = last.priority;
    el("priority").dataset.level = last.priority;
    el("reason").textContent = last.reason;
    el("next").textContent = last.next_step;
    const sources = response.events.filter(event => last.evidence_ids.includes(event.id));
    el("sources").replaceChildren(...sources.map(event => {
      const li = document.createElement("li");
      li.textContent = event.id + " · " + event.time.slice(11, 16) + " · " + event.text;
      return li;
    }));
    el("out").hidden = false;
    el("response-title").textContent = live ? "Response · HTTP 200" : "Response · published example";
    el("response").textContent = JSON.stringify(response, null, 2);
    el("status").textContent = (live ? "Live Python response" : "Published Python response") +
      " · " + last.evidence_ids.length + " supporting " + (last.evidence_ids.length === 1 ? "event" : "events");
  } catch (error) {
    if (number === requestNumber) clearResult(error.message || "Could not read the local response.");
  } finally {
    if (number === requestNumber) el("run").disabled = live && !el("token").value;
  }
}

async function start() {
  // Never offer credential entry on a hosted website.
  const loopback = location.protocol === "http:" && ["127.0.0.1", "localhost"].includes(location.hostname);
  if (loopback) {
    try {
      const res = await fetch("/lab-mode", {cache: "no-store", credentials: "omit", redirect: "error"});
      live = res.ok && (await res.json()).mode === "loopback";
    } catch (_) { /* A plain local static server uses published mode. */ }
  }
  if (live) {
    el("auth").hidden = false;
    el("run").textContent = "Send to local API";
    el("home").href = "https://rongsenzhang.github.io/signalbrief-lab/";
    el("mode").textContent = "Live HTTP mode. This page posts the two selected events to the authenticated Python service on this loopback origin. Inspect the response before changing the evidence.";
  }
  const res = await fetch("data/contract-examples.json");
  if (!res.ok) throw Error("The paired API examples could not be opened. Reload to try again.");
  examples = await res.json();
  document.querySelectorAll("input[name=report], #minutes").forEach(input => input.addEventListener("change", updateRequest));
  el("token").addEventListener("input", updateRequest);
  el("run").addEventListener("click", inspect);
  updateRequest();
  if (!live) await inspect();
}


let streamController = null;
let traceRows = [];
let streamReady = false;

function syncStreamButton() {
  el("start-stream").disabled = !streamReady || Boolean(streamController) || (live && !el("token").value);
}

function appendObservation(row) {
  const event = row.input;
  const decision = row.output;
  const li = document.createElement("li");
  const meta = document.createElement("span");
  meta.className = "stream-meta";
  meta.textContent = event.time.slice(11, 19) + " UTC · " + event.scope + " · " + event.id;
  const desc = document.createElement("span");
  desc.className = "stream-message";
  if (decision.status === "accepted") {
    if (decision.alert) li.className = "new-alert";
    const ids = (decision.evidence_ids || []).join(", ");
    desc.textContent = (decision.alert ? "New alert · " : "") + decision.priority +
      " · " + decision.reason + (ids ? " [" + ids + "]" : "");
  } else {
    desc.textContent = decision.status === "duplicate" ? "Duplicate observation · Existing decision kept." :
      "Record rejected · " + decision.code;
  }
  li.append(meta, desc);
  el("stream-feed").prepend(li);
}

async function readLines(response, accept, signal) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (!signal.aborted) {
      const {done, value} = await reader.read();
      buffer += decoder.decode(value, {stream: !done});
      const parts = buffer.split("\n");
      buffer = parts.pop();
      parts.filter(Boolean).forEach(line => accept(JSON.parse(line)));
      if (done) break;
    }
    if (buffer.trim() && !signal.aborted) accept(JSON.parse(buffer));
  } finally { reader.releaseLock(); }
}

async function replayStream() {
  if (streamController) return;
  const controller = new AbortController();
  streamController = controller;
  el("stream-feed").replaceChildren();
  el("stop-stream").hidden = false;
  syncStreamButton();
  let count = 0, alerts = 0;
  const accept = row => {
    if (controller.signal.aborted) return;
    appendObservation(row);
    count++;
    if (row.output.alert) alerts++;
    el("stream-state").textContent = count + " observations · " + alerts + " new alerts";
  };
  try {
    if (live) {
      const result = await fetch("/v1/demo-stream", {method: "POST", signal: controller.signal,
        credentials: "omit", redirect: "error", cache: "no-store",
        headers: {Authorization: "Bearer " + el("token").value}});
      if (!result.ok) throw Error("Local stream returned HTTP " + result.status + ".");
      await readLines(result, accept, controller.signal);
    } else {
      for (const row of traceRows) {
        if (controller.signal.aborted) break;
        accept(row);
        await new Promise(done => setTimeout(done, 450));
      }
    }
    el("stream-state").textContent = (controller.signal.aborted ? "Stopped" : "Finished") + " · " + count +
      " observations · " + alerts + " new alerts";
  } catch(error) {
    el("stream-state").textContent = controller.signal.aborted ? "Stopped after " + count + " observations." : error.message;
  } finally {
    streamController = null;
    el("stop-stream").hidden = true;
    syncStreamButton();
  }
}

async function initStream() {
  const res = await fetch("data/stream-trace.json");
  if (!res.ok) throw Error("Stream trace unavailable.");
  const trace = await res.json();
  if (!Array.isArray(trace.rows) || trace.rows.length === 0) throw Error("Stream trace unavailable.");
  traceRows = trace.rows;
  streamReady = true;
  if (live) {
    el("stream-mode").textContent = "Live Python mode. The local server delivers a fresh stream of synthetic observations over HTTP. Each decision is computed as its event arrives.";
    el("start-stream").textContent = "Run live event stream";
  }
  el("stream-state").textContent = traceRows.length + " synthetic observations";
  el("start-stream").addEventListener("click", replayStream);
  el("stop-stream").addEventListener("click", () => streamController?.abort());
  el("token").addEventListener("input", syncStreamButton);
  syncStreamButton();
}

start().then(() => initStream().catch(error => { el("stream-state").textContent = error.message; }))
  .catch(error => clearResult(error.message));
