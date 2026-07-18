// Relative paths so the app works both at http://127.0.0.1:8000/
// and behind a reverse proxy at naniweb.com/company_research/.
const RESEARCH_URL = "research";
const HEALTH_URL = "health";

const chatEl = document.getElementById("chat");
const formEl = document.getElementById("research-form");
const nameInput = document.getElementById("company-name");
const urlInput = document.getElementById("company-url");
const sendBtn = document.getElementById("send-btn");
const healthBadge = document.getElementById("health-badge");

checkHealth();

async function checkHealth() {
  try {
    const res = await fetch(HEALTH_URL);
    if (!res.ok) throw new Error();
    healthBadge.textContent = "API online";
    healthBadge.className = "badge badge-ok";
  } catch {
    healthBadge.textContent = "API offline";
    healthBadge.className = "badge badge-error";
  }
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();

  const companyName = nameInput.value.trim();
  const companyUrl = urlInput.value.trim();
  if (!companyName) return;

  addUserMessage(companyName, companyUrl);
  nameInput.value = "";
  urlInput.value = "";

  const loadingEl = addLoadingMessage();
  setBusy(true);

  try {
    const body = { company_name: companyName };
    if (companyUrl) body.company_url = companyUrl;

    const res = await fetch(RESEARCH_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    loadingEl.remove();

    if (!res.ok) {
      addErrorMessage(formatApiError(data));
      return;
    }

    addResearchCard(data);
  } catch (err) {
    loadingEl.remove();
    addErrorMessage(
      "Could not reach the API. Make sure the server is running, then try again."
    );
  } finally {
    setBusy(false);
    nameInput.focus();
  }
});

function setBusy(busy) {
  sendBtn.disabled = busy;
  sendBtn.querySelector(".btn-label").textContent = busy ? "Researching…" : "Research";
}

function addUserMessage(companyName, companyUrl) {
  const text = companyUrl ? `${companyName} (${companyUrl})` : companyName;
  const el = buildMessage("user");
  el.querySelector(".bubble").textContent = text;
  appendToChat(el);
}

function addLoadingMessage() {
  const el = buildMessage("bot");
  el.querySelector(".bubble").innerHTML = `
    <div class="typing"><span></span><span></span><span></span></div>
    <span class="loading-note">Fetching the website and running the local model.
    The first request can take a minute while the model loads.</span>`;
  appendToChat(el);
  return el;
}

function addErrorMessage(text) {
  const el = buildMessage("bot error");
  el.querySelector(".bubble").textContent = text;
  appendToChat(el);
}

function buildMessage(cls) {
  const el = document.createElement("div");
  el.className = `message ${cls}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  el.appendChild(bubble);
  return el;
}

function formatApiError(data) {
  const detail = data && data.detail;
  if (typeof detail === "string") {
    if (detail.includes("403")) {
      return "That website blocked automated access (403 Forbidden). " +
        "Try again without the website URL to research by company name only.";
    }
    return detail;
  }
  return "The request failed. Check the inputs and try again.";
}

function addResearchCard(payload) {
  const research = payload.research;
  const wrapper = document.createElement("div");
  wrapper.className = "message bot";

  const card = document.createElement("div");
  card.className = "research-card";

  card.appendChild(buildCardHeader(research, payload.model));
  card.appendChild(buildTextSection("Summary", research.summary));
  card.appendChild(buildChipSection("Target Customers", research.target_customers));
  card.appendChild(buildTextSection("Value Proposition", research.value_proposition));

  if (research.recent_signals && research.recent_signals.length > 0) {
    card.appendChild(buildSignalsSection(research.recent_signals));
  }

  card.appendChild(buildListSection("Outreach Angles", research.outreach_angles));

  if (research.sources && research.sources.length > 0) {
    card.appendChild(buildSourcesSection(research.sources));
  }

  card.appendChild(buildRawJson(payload));

  wrapper.appendChild(card);
  appendToChat(wrapper);
}

function buildCardHeader(research, model) {
  const header = document.createElement("div");
  header.className = "card-header";

  const title = document.createElement("h2");
  title.textContent = research.company_name;
  header.appendChild(title);

  if (research.website) {
    const link = document.createElement("a");
    link.href = research.website;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = research.website;
    header.appendChild(link);
  }

  const tag = document.createElement("span");
  tag.className = "model-tag";
  tag.textContent = model;
  header.appendChild(tag);

  return header;
}

function buildTextSection(heading, text) {
  const section = buildSection(heading);
  const p = document.createElement("p");
  p.textContent = text;
  section.appendChild(p);
  return section;
}

function buildChipSection(heading, items) {
  const section = buildSection(heading);
  const row = document.createElement("div");
  row.className = "chip-row";
  for (const item of items) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = item;
    row.appendChild(chip);
  }
  section.appendChild(row);
  return section;
}

function buildListSection(heading, items) {
  const section = buildSection(heading);
  const ul = document.createElement("ul");
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    ul.appendChild(li);
  }
  section.appendChild(ul);
  return section;
}

function buildSignalsSection(signals) {
  const section = buildSection("Recent Signals");
  for (const signal of signals) {
    const div = document.createElement("div");
    div.className = "signal";

    const title = document.createElement("div");
    title.className = "signal-title";
    title.textContent = signal.title;
    div.appendChild(title);

    const evidence = document.createElement("div");
    evidence.className = "signal-evidence";
    evidence.textContent = signal.evidence;
    div.appendChild(evidence);

    if (signal.source_url) {
      const link = document.createElement("a");
      link.className = "source-link";
      link.href = signal.source_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = signal.source_url;
      div.appendChild(link);
    }

    section.appendChild(div);
  }
  return section;
}

function buildSourcesSection(sources) {
  const section = buildSection("Sources");
  const ul = document.createElement("ul");
  for (const source of sources) {
    const li = document.createElement("li");

    const link = document.createElement("a");
    link.className = "source-link";
    link.href = source.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = source.url;
    li.appendChild(link);

    const desc = document.createElement("div");
    desc.className = "source-desc";
    desc.textContent = source.description;
    li.appendChild(desc);

    ul.appendChild(li);
  }
  section.appendChild(ul);
  return section;
}

function buildSection(heading) {
  const section = document.createElement("div");
  section.className = "card-section";
  const h3 = document.createElement("h3");
  h3.textContent = heading;
  section.appendChild(h3);
  return section;
}

function buildRawJson(payload) {
  const details = document.createElement("details");
  details.className = "raw-json";

  const summary = document.createElement("summary");
  summary.textContent = "Raw JSON";
  details.appendChild(summary);

  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(payload, null, 2);
  details.appendChild(pre);

  return details;
}

function appendToChat(el) {
  chatEl.appendChild(el);
  chatEl.scrollTop = chatEl.scrollHeight;
}
