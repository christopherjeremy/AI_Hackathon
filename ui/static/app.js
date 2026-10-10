/**
 * RideWise Assist - Bright Cockpit Dashboard
 * Powered by GSAP Core for Enterprise Motion Design
 */

let currentSession = null;
let currentRole = "customer";

// Predefined Quick Inquiries
const CUSTOMER_PROMPTS = [
  "Show my latest bookings and statuses",
  "Why is there a late fee on booking B-0001?",
  "How much refund will I get if I cancel 12 hours before pickup?",
  "Can I charge an Ather 450X at home with a 15A socket?",
  "What is the penalty if I return with less than 10% battery?",
  "What are the Bangalore hub locations?"
];

const STAFF_PROMPTS = [
  "Show vehicles currently under maintenance across hubs",
  "List all open damage claims with severity HIGH",
  "Show fleet availability at Indiranagar hub",
  "Explain the difference between Cancellation Policy v1 and v2",
  "Details and payment breakdown for booking B-0004",
  "Lookup customer profile for CUST0001"
];

// DOM Elements
const authScreen = document.getElementById("authScreen");
const mainChatScreen = document.getElementById("mainChatScreen");
const customerLoginForm = document.getElementById("customerLoginForm");
const staffLoginForm = document.getElementById("staffLoginForm");
const tabCustomer = document.getElementById("tabCustomer");
const tabStaff = document.getElementById("tabStaff");
const customerIdInput = document.getElementById("customerIdInput");
const staffNameInput = document.getElementById("staffNameInput");
const loginError = document.getElementById("loginError");

const headerUserName = document.getElementById("headerUserName");
const headerTierBadge = document.getElementById("headerTierBadge");
const headerAvatar = document.getElementById("headerAvatar");
const railEntitlementText = document.getElementById("railEntitlementText");
const quickInquiriesList = document.getElementById("quickInquiriesList");
const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const typingIndicator = document.getElementById("typingIndicator");

// =========================================================
// GSAP INITIALIZATION
// =========================================================
window.addEventListener("DOMContentLoaded", () => {
  initAmbientMeshMotion();
  initAuthModalEntrance();
});

function initAmbientMeshMotion() {
  // Gentle ambient floating mesh orbs
  gsap.to(".mesh-1", {
    x: "+=50",
    y: "+=30",
    duration: 9,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut"
  });

  gsap.to(".mesh-2", {
    x: "-=40",
    y: "-=25",
    duration: 11,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut"
  });

  gsap.to(".mesh-3", {
    scale: 1.15,
    duration: 8,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut"
  });
}

function initAuthModalEntrance() {
  const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
  tl.from(".auth-card", {
    scale: 0.9,
    autoAlpha: 0,
    y: 25,
    duration: 0.6
  })
  .from(".auth-badge", { y: -8, autoAlpha: 0, duration: 0.3 }, "-=0.25")
  .from([".auth-tagline", ".auth-title", ".auth-desc"], { y: 12, autoAlpha: 0, stagger: 0.08, duration: 0.4 }, "-=0.2")
  .from(".role-tabs", { scale: 0.96, autoAlpha: 0, duration: 0.3 }, "-=0.2")
  .from(".login-pane", { y: 10, autoAlpha: 0, duration: 0.3 }, "-=0.15");
}

// =========================================================
// ROLE SWITCHING (GSAP Morph)
// =========================================================
function switchLoginRole(role) {
  if (role === currentRole) return;
  currentRole = role;

  const tl = gsap.timeline({ defaults: { duration: 0.22, ease: "power2.out" } });

  if (role === "customer") {
    tabCustomer.classList.add("active");
    tabStaff.classList.remove("active");

    tl.to(staffLoginForm, {
      autoAlpha: 0,
      y: -8,
      onComplete: () => {
        staffLoginForm.classList.add("hidden");
        customerLoginForm.classList.remove("hidden");
      }
    })
    .fromTo(customerLoginForm, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0 });
  } else {
    tabStaff.classList.add("active");
    tabCustomer.classList.remove("active");

    tl.to(customerLoginForm, {
      autoAlpha: 0,
      y: -8,
      onComplete: () => {
        customerLoginForm.classList.add("hidden");
        staffLoginForm.classList.remove("hidden");
      }
    })
    .fromTo(staffLoginForm, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0 });
  }
}

// =========================================================
// KNOWLEDGE RAIL TABS SWITCHER
// =========================================================
function switchKnowledgeTab(tabName) {
  const tabs = document.querySelectorAll(".k-tab-btn");
  tabs.forEach(t => t.classList.remove("active"));

  document.getElementById("tabContentActions").classList.add("hidden");
  document.getElementById("tabContentHubs").classList.add("hidden");
  document.getElementById("tabContentPolicy").classList.add("hidden");

  if (tabName === "actions") {
    tabs[0].classList.add("active");
    const el = document.getElementById("tabContentActions");
    el.classList.remove("hidden");
    gsap.from(el, { autoAlpha: 0, y: 6, duration: 0.25 });
  } else if (tabName === "hubs") {
    tabs[1].classList.add("active");
    const el = document.getElementById("tabContentHubs");
    el.classList.remove("hidden");
    gsap.from(el, { autoAlpha: 0, y: 6, duration: 0.25 });
  } else if (tabName === "policy") {
    tabs[2].classList.add("active");
    const el = document.getElementById("tabContentPolicy");
    el.classList.remove("hidden");
    gsap.from(el, { autoAlpha: 0, y: 6, duration: 0.25 });
  }
}

// =========================================================
// AUTHENTICATION HANDLERS
// =========================================================
async function handleCustomerLogin() {
  const cid = customerIdInput.value.trim().toUpperCase();
  if (!cid) {
    showLoginError("Please enter a customer ID (e.g. CUST0001)");
    return;
  }
  await performLogin({ role: "customer", customer_id: cid });
}

async function handleStaffLogin() {
  const staff = staffNameInput.value.trim();
  if (!staff) {
    showLoginError("Please enter your name");
    return;
  }
  await performLogin({ role: "support_agent", staff_name: staff });
}

function showLoginError(msg) {
  loginError.textContent = msg;
  loginError.classList.remove("hidden");
  gsap.fromTo(loginError, { x: -8 }, { x: 0, duration: 0.35, ease: "elastic.out(1, 0.3)" });
}

async function performLogin(payload) {
  loginError.classList.add("hidden");
  const btn = payload.role === "customer" ? document.getElementById("btnLoginCustomer") : document.getElementById("btnLoginStaff");
  btn.style.pointerEvents = "none";
  btn.style.opacity = "0.7";

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!res.ok) {
      showLoginError(data.detail || "Authentication failed.");
      btn.style.pointerEvents = "auto";
      btn.style.opacity = "1";
      return;
    }

    currentSession = data;
    transitionToCockpit();
  } catch (err) {
    showLoginError("Could not reach backend API. Is server running?");
    btn.style.pointerEvents = "auto";
    btn.style.opacity = "1";
  }
}

// =========================================================
// TRANSITION TO COCKPIT (GSAP DUAL-PANE REVEAL)
// =========================================================
function transitionToCockpit() {
  const tl = gsap.timeline();

  tl.to(authScreen, {
    autoAlpha: 0,
    duration: 0.35,
    ease: "power2.in",
    onComplete: () => {
      authScreen.classList.add("hidden");
      mainChatScreen.classList.remove("hidden");
      populateHeaderUser();
      populateQuickInquiries();
      addAssistantMessage(currentSession.welcome_message, ["System Authenticator"]);
    }
  })
  .fromTo(".cockpit-header", { y: -25, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.4, ease: "power3.out" })
  .fromTo(".intelligence-rail", { x: -30, autoAlpha: 0 }, { x: 0, autoAlpha: 1, duration: 0.45, ease: "power3.out" }, "-=0.25")
  .fromTo(".chat-workspace", { scale: 0.98, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: 0.45, ease: "power3.out" }, "-=0.35");
}

function populateHeaderUser() {
  headerUserName.textContent = currentSession.display_name;

  if (currentSession.role === "customer") {
    headerAvatar.textContent = "👤";
    const tier = (currentSession.customer_profile?.customer_tier || "STANDARD").toUpperCase();
    headerTierBadge.textContent = tier;
    headerTierBadge.className = `tier-badge ${tier.toLowerCase()}`;
    railEntitlementText.textContent = `Scoped to ${currentSession.display_name}'s bookings`;
    document.getElementById("piiRow").classList.add("hidden");
  } else {
    headerAvatar.textContent = "🎧";
    headerTierBadge.textContent = "OPS AGENT";
    headerTierBadge.className = "tier-badge silver";
    railEntitlementText.textContent = "Global fleet & cross-customer query scope";
    document.getElementById("piiRow").classList.remove("hidden");
  }
}

function populateQuickInquiries() {
  quickInquiriesList.innerHTML = "";
  const prompts = currentSession.role === "customer" ? CUSTOMER_PROMPTS : STAFF_PROMPTS;

  prompts.forEach((promptText) => {
    const card = document.createElement("div");
    card.className = "inquiry-card";
    card.textContent = promptText;
    card.onclick = () => sendQuickMessage(promptText);
    quickInquiriesList.appendChild(card);
  });

  gsap.from(".inquiry-card", {
    x: -12,
    autoAlpha: 0,
    duration: 0.3,
    stagger: 0.05,
    ease: "power2.out"
  });
}

function sendQuickMessage(text) {
  messageInput.value = text;
  handleSendMessage();
}

// =========================================================
// CHAT MESSAGING & ANIMATIONS
// =========================================================
async function handleSendMessage() {
  const text = messageInput.value.trim();
  if (!text || !currentSession) return;

  messageInput.value = "";
  addUserMessage(text);
  showTyping(true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSession.session_id,
        message: text
      })
    });

    const data = await res.json();
    showTyping(false);

    if (res.ok) {
      addAssistantMessage(data.response, data.citations, data.cache_status);
    } else {
      addAssistantMessage(`⚠️ Error: ${data.detail || "Could not process request."}`, ["Error"]);
    }
  } catch (err) {
    showTyping(false);
    addAssistantMessage("⚠️ Connection error with RideWise API. Please retry.", ["Connection Error"]);
  }
}

function handleKeyDown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSendMessage();
  }
}

function addUserMessage(text) {
  const row = document.createElement("div");
  row.className = "msg-row user";
  row.innerHTML = `
    <div class="avatar-badge">${currentSession.role === "customer" ? "👤" : "🎧"}</div>
    <div class="bubble-wrap">
      <div class="bubble-content">${escapeHtml(text)}</div>
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();

  gsap.from(row, {
    y: 12,
    autoAlpha: 0,
    scale: 0.97,
    duration: 0.3,
    ease: "power2.out"
  });
}

function addAssistantMessage(markdownText, citations = [], cacheStatus = null) {
  const row = document.createElement("div");
  row.className = "msg-row assistant";

  const parsedHtml = marked.parse(markdownText);
  let citationDrawerHtml = "";

  if (citations && citations.length > 0) {
    const pills = citations.map(c => `<span class="cite-tag">${escapeHtml(c)}</span>`).join("");
    const cacheBadge = cacheStatus ? `<span class="cite-tag" style="background:#e0f2fe;color:#0284c7;font-weight:700;">⚡ ${cacheStatus}</span>` : "";
    citationDrawerHtml = `
      <div class="citation-box">
        <div class="citation-title">
          <span>📚 Verified Ledger Records &amp; Policy Citations</span>
          <span>▼</span>
        </div>
        <div class="citation-list">${cacheBadge}${pills}</div>
      </div>
    `;
  }

  row.innerHTML = `
    <div class="avatar-badge">▲</div>
    <div class="bubble-wrap">
      <div class="bubble-content">${parsedHtml}</div>
      ${citationDrawerHtml}
    </div>
  `;

  chatMessages.appendChild(row);
  scrollToBottom();

  gsap.from(row, {
    y: 16,
    autoAlpha: 0,
    scale: 0.98,
    duration: 0.4,
    ease: "power2.out"
  });
}

function showTyping(show) {
  if (show) {
    typingIndicator.classList.remove("hidden");
    gsap.to(".typing-dot", {
      y: -5,
      duration: 0.32,
      stagger: 0.12,
      repeat: -1,
      yoyo: true,
      ease: "power2.inOut"
    });
    scrollToBottom();
  } else {
    typingIndicator.classList.add("hidden");
    gsap.killTweensOf(".typing-dot");
  }
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// =========================================================
// RESET & LOGOUT ACTIONS
// =========================================================
async function handleResetConversation() {
  if (!currentSession) return;
  gsap.to(".btn-reset-chat svg", { rotation: "+=360", duration: 0.5, ease: "power2.out" });

  try {
    await fetch("/api/chat/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSession.session_id })
    });

    gsap.to(".msg-row", {
      autoAlpha: 0,
      y: -8,
      stagger: 0.04,
      duration: 0.22,
      onComplete: () => {
        chatMessages.innerHTML = "";
        addAssistantMessage(
          `Conversation context refreshed. Hello **${currentSession.display_name}**, how can I assist you today?`,
          ["System Reset"]
        );
      }
    });
  } catch (err) {
    console.error("Failed to reset conversation:", err);
  }
}

function handleLogout() {
  const tl = gsap.timeline();
  tl.to(mainChatScreen, {
    autoAlpha: 0,
    duration: 0.25,
    onComplete: () => {
      mainChatScreen.classList.add("hidden");
      authScreen.classList.remove("hidden");
      gsap.to(authScreen, { autoAlpha: 1, duration: 0.25 });
      chatMessages.innerHTML = "";
      currentSession = null;
    }
  });
}
