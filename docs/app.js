"use strict";

(() => {
  const byId = id => document.getElementById(id);
  const storageKey = "signalbrief.reviews.v1";
  const choices = ["Escalate", "Request context", "Monitor", "Close"];
  const mobile = window.matchMedia("(max-width: 760px)");
  let cases = [];
  let languageModel = null;
  let generatedDrafts = null;
  let sourceReview = null;
  let selection = null;
  let step = 0;
  let audience = "analyst";
  let timer = null;
  let filter = "all";
  let reviews = {};
  const drafts = new Map();

  function getData(path) {
    if (window.signalBriefFiles && Object.prototype.hasOwnProperty.call(window.signalBriefFiles, path)) {
      return Promise.resolve(window.signalBriefFiles[path]);
    }
    return fetch(path).then(response => {
      if (!response.ok) throw new Error("Data is unavailable.");
      return response.json();
    });
  }

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = value;
    return node;
  }

  function icon(name) {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("class", "icon");
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS(ns, "use");
    use.setAttribute("href", "#i-" + name);
    svg.append(use);
    return svg;
  }

  function frame() { return selection.frames[step]; }
  function observed() {
    const ids = new Set(frame().event_ids);
    return selection.events.filter(event => ids.has(event.id));
  }
  function utc(time) {
    const parsed = new Date(time);
    return Number.isNaN(parsed.getTime()) ? time : parsed.toISOString().slice(11, 19);
  }
  function key() { return selection.id + "/" + frame().event_ids.join(","); }
  function labUrl(path) {
    return window.signalBriefOnline ? new URL(path, window.signalBriefOnline).href : path;
  }
  function checkpointQuery() {
    return new URLSearchParams({case: selection.id, step: String(step + 1)}).toString();
  }
  function rememberCheckpoint() {
    if (!/^https?:$/.test(location.protocol)) return;
    const url = new URL(location.href);
    url.searchParams.set("case", selection.id);
    url.searchParams.set("step", String(step + 1));
    history.replaceState(null, "", url);
  }
  function readReviews() {
    try {
      const value = localStorage.getItem(storageKey);
      if (value === null) return;
      const stored = JSON.parse(value);
      if (stored && typeof stored === "object" && !Array.isArray(stored)) reviews = stored;
    } catch { /* Storage is optional in private browsing and local-file mode. */ }
  }
  function hasReview(item) {
    return item.frames.some(f => choices.includes(reviews[item.id + "/" + f.event_ids.join(",")]?.decision));
  }
  function latestReviewStep(item) {
    let latest = "";
    let index = 0;
    item.frames.forEach((f,i) => {
      const review = reviews[item.id + "/" + f.event_ids.join(",")];
      if (choices.includes(review?.decision) && review.savedAt >= latest) {
        latest = review.savedAt;
        index = i;
      }
    });
    return index;
  }

  function showQueue() {
    byId("case-count").textContent = String(cases.length);
    byId("review-count").textContent = String(cases.filter(hasReview).length);
    const items = cases.filter(item => filter === "all" || (filter === "reviewed") === hasReview(item));
    byId("queue-count").textContent = String(items.length);
    const list = byId("case-list");
    list.replaceChildren();
    if (!items.length) {
      const empty = filter === "reviewed" ? "No reviews saved yet." : "Every case has a saved review.";
      list.append(element("p", "no-cases", empty + " The open case remains available."));
    }
    byId("reset-filter").hidden = items.length > 0;
    for (const item of items) {
      const button = element("button", "case-option");
      button.type = "button";
      button.setAttribute("aria-current", String(item.id === selection?.id));
      const meta = element("span", "option-meta");
      meta.append(element("span", "mono", item.id));
      if (hasReview(item)) {
        const tick = element("span", "review-tick");
        tick.append(icon("check"), "Reviewed");
        meta.append(tick);
      }
      button.append(meta, element("strong", "", item.title));
      button.addEventListener("click", () => {
        selectCase(item, filter === "reviewed" ? latestReviewStep(item) : 0);
        if (mobile.matches) byId("queue").open = false;
        byId("case").focus({preventScroll: true});
      });
      list.append(button);
    }
    return items;
  }

  function svgNode(tag, attrs, value) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [name, val] of Object.entries(attrs)) node.setAttribute(name, val);
    if (value !== undefined) node.textContent = value;
    return node;
  }

  function drawTrace() {
    if (!selection) return;
    const svg = byId("trace");
    const width = Math.max(220, Math.round(svg.getBoundingClientRect().width));
    const events = observed();
    const sources = [...new Set(events.map(event => event.source))];
    const gutter = width < 390 ? 84 : 130;
    const right = width - 24;
    const y = row => 15 + row * 23;
    const height = y(sources.length) + 13;
    const maxStep = selection.frames.length;
    const x = pos => gutter + 7 + (right - gutter - 7) * pos / Math.max(1, maxStep - 1);
    const xLabel = {fill: "#c2d7cf", "font-size": 11, "font-family": "monospace"};
    const prefix = width < 390 ? 12 : 20;
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.setAttribute("height", height);
    svg.setAttribute("aria-label", "Observed events by source and sequence. " + events.map((e, i) => "Event " + (i + 1) + ", " + e.source + ", " + utc(e.time) + " UTC.").join(" "));
    svg.replaceChildren();
    for (let i = 0; i < maxStep; i++) {
      svg.append(svgNode("line", {x1:x(i),y1:4,x2:x(i),y2:height-19,stroke:"#668080","stroke-dasharray":"2 5"}));
      svg.append(svgNode("text", {...xLabel,x:x(i),y:height-2,"text-anchor":"middle"}, String(i+1).padStart(2,"0")));
    }
    sources.forEach((source, i) => {
      const short = source.length > prefix ? source.slice(0, prefix-1) + "…" : source;
      svg.append(svgNode("text", {...xLabel,x:0,y:y(i)+4}, short));
      svg.append(svgNode("line", {x1:gutter-2,y1:y(i),x2:width-5,y2:y(i),stroke:"#6f9593","stroke-opacity":.45}));
    });
    events.forEach((event, i) => {
      const anchor = {cx:x(i),cy:y(sources.indexOf(event.source))};
      if (i === events.length-1) svg.append(svgNode("circle", {...anchor,r:8,fill:"none",stroke:"#a3dec1","stroke-opacity":.65}));
      svg.append(svgNode("circle", {...anchor,r:4,fill:"#b9f4cd"}));
    });
    svg.append(svgNode("text", {...xLabel,x:0,y:height-2}, "Sequence"));
  }

  function focusEvent(id) {
    const row = byId("event-" + id);
    if (row) {
      row.focus({preventScroll:true});
      row.scrollIntoView({block:"nearest"});
    }
  }

  function citeButton(id) {
    const b = element("button", "cite", id);
    b.type = "button";
    b.setAttribute("aria-label", "Show evidence " + id);
    b.addEventListener("click", () => focusEvent(id));
    return b;
  }

  function modelSample() {
    if (languageModel?.status !== "ready") return null;
    const sample = languageModel.scenarios?.[selection.id]?.[step];
    const ids = frame().event_ids;
    if (!Array.isArray(sample?.event_ids) || sample.event_ids.length !== ids.length || !sample.event_ids.every((id,i) => id === ids[i])) return null;
    return sample;
  }

  function modelEvidence() {
    const sample = modelSample();
    return sample && observed().find(e => e.id === sample.selected_id && e.text === sample.extract);
  }

  function showDraftComparison() {
    const panel = byId("draft-review");
    const packet = generatedDrafts?.cases?.[selection.id];
    const draft = packet?.drafts?.[audience];
    const review = sourceReview?.cases?.[selection.id]?.[audience];
    const ids = frame().evidence_ids;
    const valid = step === selection.frames.length - 1 && generatedDrafts?.status === "ready" &&
      packet?.rule === frame().rule && packet.known_limit === frame().unknown &&
      Array.isArray(packet.sources) && packet.sources.length === ids.length &&
      packet.sources.every((row, index) => row.id === ids[index] &&
        observed().some(event => event.id === row.id && event.text === row.text)) &&
      typeof draft?.text === "string" && review && review.evidence_ids.join(",") === ids.join(",");
    panel.hidden = !valid;
    if (!valid) { panel.open = false; return; }
    const role = audience === "analyst" ? "analyst" : "service owner";
    byId("draft-attribution").textContent = "Original " + role + " draft · " + generatedDrafts.model_id;
    byId("draft-text").textContent = draft.text;
    byId("draft-verdict").textContent = review.verdict;
    byId("draft-explanation").textContent = review.note;
    byId("draft-cites").replaceChildren(...ids.map(citeButton));
    byId("draft-screen").textContent = (draft.flags.length ? "Automatic screen: " + draft.flags.join(". ") + ". " :
      "The automatic screen raised no flag. ") + "The source review was AI-assisted. Export uses the checked case brief.";
  }

  function showBrief() {
    const f = frame();
    showDraftComparison();
    byId("priority").textContent = f.priority;
    byId("priority").className = "priority " + f.priority.toLowerCase();
    byId("analyst").setAttribute("aria-pressed", String(audience === "analyst"));
    byId("manager").setAttribute("aria-pressed", String(audience === "manager"));
    byId("brief-body").textContent = f[audience];
    byId("unknown").textContent = f.unknown;
    byId("next-step").textContent = f.next_step;
    byId("cites").replaceChildren(...f.evidence_ids.map(citeButton));
    const method = byId("method-body");
    const scores = element("dl");
    const score = Number(f.model?.score);
    for (const [k,v] of [["Topic", f.model?.label || f.category], ["Model score", Number.isFinite(score) ? score.toFixed(3) : "Unavailable"], ["Priority rule", f.rule || f.priority]]) {
      scores.append(element("dt","",k), element("dd","",v));
    }
    method.replaceChildren(scores,element("p","",f.reason),element("p","","The classifier routes the topic. A separate evidence rule assigns priority."));
    const container = byId("model-output");
    const sample = modelSample();
    const match = modelEvidence();
    if (match) {
      container.replaceChildren(element("p","","Saved model selection · " + languageModel.model_id), element("blockquote","",match.text), citeButton(match.id));
    } else if (sample && !sample.selected_id) {
      container.replaceChildren(element("p","","Saved model run · No selection (" + sample.outcome + "). The case brief uses the evidence rules."));
    } else {
      container.replaceChildren(element("p","","This brief uses the evidence rules. No verified model selection is available for this frame."));
    }
    if (sample && Array.isArray(sample.responses)) {
      const details = element("details", "model-choices");
      details.append(element("summary", "", "Inspect both model answers"),
        element("p", "", "Forward order: " + JSON.stringify(sample.responses[0]) +
        " · Reverse order: " + JSON.stringify(sample.responses[1])));
      container.append(details);
    }
    const href = labUrl("model-lab.html?" + checkpointQuery());
    byId("model-lab").href = href;
    byId("nav-model").href = href;
  }

  function showLedger() {
    const events = observed().reverse();
    byId("ledger-count").textContent = String(events.length);
    const items = events.map(event => {
      const row = element("li","event");
      row.id = "event-" + event.id;
      row.tabIndex = -1;
      const meta = element("div","event-meta");
      const t = element("time","mono",utc(event.time) + " UTC");
      t.dateTime = event.time;
      meta.append(element("span","mono",event.id),t);
      row.append(meta,element("div","event-source",event.source),element("p","",event.text));
      return row;
    });
    byId("ledger").replaceChildren(...items);
  }

  function currentDraft() {
    return {
      decision: byId("review-form").querySelector("input[name=disposition]:checked")?.value || "",
      note: byId("review-note").value.trim()
    };
  }

  function showReview() {
    const saved = reviews[key()];
    const draft = drafts.get(key()) || saved || {};
    byId("review-info").textContent = saved ? "Saved at event " + (step+1) + " · " + saved.decision + ". You can revise this review." : "Record your judgement for this point in the replay.";
    for (const radio of byId("dispositions").querySelectorAll("input")) radio.checked = radio.value === draft.decision;
    byId("review-note").value = draft.note || "";
    byId("save").disabled = !choices.includes(draft.decision);
    byId("feedback").textContent = "";
  }

  function updateDraft() {
    stop();
    const draft = currentDraft();
    drafts.set(key(), draft);
    byId("save").disabled = !draft.decision;
    byId("feedback").textContent = "";
  }

  function saveReview(event) {
    event.preventDefault();
    const draft = currentDraft();
    if (!choices.includes(draft.decision)) return;
    readReviews();
    reviews[key()] = {...draft, savedAt:new Date().toISOString()};
    let persisted = true;
    try { localStorage.setItem(storageKey, JSON.stringify(reviews)); } catch { persisted = false; }
    drafts.delete(key());
    showReview();
    showQueue();
    byId("feedback").textContent = persisted ? "Review saved for " + selection.id + " at event " + (step+1) + "." : "Review kept for this session. Browser storage is unavailable. Download the handover to retain it.";
  }

  function download() {
    const f = frame();
    const saved = reviews[key()];
    const draft = currentDraft();
    const savedHere = saved && saved.decision === draft.decision && saved.note === draft.note;
    const model = modelEvidence();
    const lines = [
      "# " + selection.id + " · " + selection.title, "",
      "SignalBrief Lab v1.0 · Synthetic case handover", "",
      "Service: " + selection.service, "Evidence checkpoint: event " + (step+1) + " of " + selection.frames.length,
      "Priority: " + f.priority, "Topic: " + f.category, "Decision basis: " + f.reason, "",
      "## Analyst brief", "", f.analyst, "", "## Service owner brief", "", f.manager, "",
      "## Outstanding questions", "", f.unknown, "", "## Next check", "", f.next_step, "",
      "Supporting events: " + f.evidence_ids.join(", "), "", "## Model-selected observation", "",
      model ? languageModel.model_id + " · " + model.id + " · " + model.text : "No verified language-model selection for this frame.", "",
      "## Evidence ledger", "", ...observed().map(e => "- " + e.id + " | " + e.time + " | " + e.source + " | " + e.text), "",
      "## Human review", "", "Disposition: " + (draft.decision || "Pending"), "Review state: " + (savedHere ? "Saved" : "Draft"),
      ...(savedHere ? ["Saved at: " + saved.savedAt] : []), "", draft.note || "No handover note recorded.", ""
    ];
    const url = URL.createObjectURL(new Blob([lines.join("\n")],{type:"text/markdown;charset=utf-8"}));
    const link = element("a");
    link.href = url;
    link.download = selection.id + "-event-" + (step+1) + "-handover.md";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    byId("feedback").textContent = "Handover prepared for event " + (step+1) + ".";
  }

  function playLabel() {
    const running = timer !== null;
    const ended = step === selection.frames.length-1;
    byId("play").replaceChildren(icon(running ? "pause" : "play"), element("span","",running ? "Pause" : ended ? "Replay" : "Play"));
    byId("play").setAttribute("aria-label", running ? "Pause" : ended ? "Replay" : "Play");
  }
  function stop() {
    if (timer !== null) window.clearInterval(timer);
    timer = null;
    if (selection) playLabel();
  }
  function showFrame() {
    const events = observed();
    byId("event-time").textContent = utc(events[events.length-1].time);
    byId("step-count").textContent = "Event " + (step+1) + " / " + selection.frames.length;
    byId("previous").disabled = step === 0;
    byId("next").disabled = step === selection.frames.length-1;
    byId("restart").disabled = step === 0 && timer === null;
    playLabel();
    drawTrace();
    showLedger();
    showBrief();
    showReview();
    rememberCheckpoint();
  }
  function seek(position) {
    stop();
    step = Math.max(0,Math.min(selection.frames.length-1,position));
    showFrame();
  }
  function togglePlay() {
    if (timer !== null) { stop(); showFrame(); return; }
    if (step === selection.frames.length-1) step = 0;
    if (selection.frames.length > 1) timer = setInterval(() => {
      step++;
      if (step >= selection.frames.length-1) stop();
      showFrame();
    }, 2300);
    showFrame();
  }

  function selectCase(item, position = 0) {
    stop();
    selection = item;
    step = position;
    byId("case-ref").textContent = item.id;
    byId("case-service").textContent = item.service;
    byId("case-title").textContent = item.title;
    byId("case-description").textContent = item.description;
    showFrame();
    showQueue();
  }

  function initialise(data) {
    cases = data.scenarios;
    if (!Array.isArray(cases) || !cases.length) throw new Error("Case library is empty.");
    readReviews();
    byId("loading").hidden = true;
    byId("desk").hidden = false;
    byId("queue").open = !mobile.matches;
    mobile.addEventListener("change", () => { byId("queue").open = !mobile.matches; });
    for (const choice of choices) {
      const label = element("label");
      const input = element("input","sr-only");
      input.type = "radio"; input.name = "disposition"; input.value = choice;
      label.append(input,element("span","",choice));
      byId("dispositions").append(label);
    }
    byId("review-form").addEventListener("input", updateDraft);
    byId("review-form").addEventListener("focusin", stop);
    byId("review-form").addEventListener("submit", saveReview);
    byId("export").addEventListener("click",download);
    byId("queue-filter").addEventListener("change", event => {
      filter = event.target.value;
      const items = showQueue();
      if (items.length && (!items.includes(selection) || filter === "reviewed")) {
        const item = items.includes(selection) ? selection : items[0];
        selectCase(item, filter === "reviewed" ? latestReviewStep(item) : 0);
      }
    });
    byId("reset-filter").addEventListener("click", () => {
      filter = "all";
      byId("queue-filter").value = filter;
      showQueue();
      byId("queue-filter").focus();
    });
    for (const role of ["analyst","manager"]) byId(role).addEventListener("click", () => { audience = role; showBrief(); });
    byId("previous").addEventListener("click", () => seek(step-1));
    byId("next").addEventListener("click", () => seek(step+1));
    byId("restart").addEventListener("click", () => seek(0));
    byId("play").addEventListener("click",togglePlay);
    document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });
    window.addEventListener("resize", drawTrace);
    window.addEventListener("storage", evt => {
      if (evt.key !== storageKey && evt.key !== null) return;
      if (evt.newValue === null) reviews = {};
      else readReviews();
      showQueue(); showReview();
    });
    const query = new URLSearchParams(location.search);
    const linked = cases.find(item => item.id === query.get("case"));
    const requested = Number(query.get("step")) - 1;
    const valid = linked && Number.isInteger(requested) && requested >= 0 && requested < linked.frames.length;
    byId("nav-api").href = labUrl("integration.html");
    selectCase(linked || cases[0], valid ? requested : 0);
    Promise.all([getData("data/handover-drafts.json"), getData("data/handover-review.json")])
      .then(([raw, review]) => { generatedDrafts = raw; sourceReview = review; showDraftComparison(); })
      .catch(() => { byId("draft-review").hidden = true; });
    getData("data/language-model.json").then(snapshot => { languageModel = snapshot; showBrief(); }).catch(() => {});
    getData("data/evaluation.json").then(({routing,benchmark}) => {
      const matched = Math.round(routing.test_size * routing.accuracy);
      byId("guide-routing").textContent = "The topic classifier matched " + matched + " of " + routing.test_size + " held-out synthetic phrases. The small English test set covers four topics.";
      byId("guide-benchmark").textContent = "One local benchmark processed " + benchmark.events.toLocaleString("en-GB") + " repeated events in " + benchmark.seconds + " seconds. The timing covers the core engine and excludes HTTP, the browser and language-model inference.";
      byId("guide-evaluation").hidden = false;
    }).catch(() => {});
  }
  const guide = byId("guide");
  for (const id of ["guide-open","guide-inline"]) byId(id).addEventListener("click",() => { stop(); guide.showModal(); });
  byId("guide-close").addEventListener("click",() => guide.close());
  guide.addEventListener("click",event => { if (event.target === guide) {
    const r = guide.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) guide.close();
  } });
  getData("data/scenarios.json").then(initialise).catch(() => {
    byId("desk").hidden = true;
    byId("loading").hidden = false;
    byId("loading").textContent = "The case library could not be opened. Reload the hosted page, or open the project through its local web server.";
  });
})();
