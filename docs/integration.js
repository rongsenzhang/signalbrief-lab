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
start().catch(error => clearResult(error.message));
