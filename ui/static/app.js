/**
 * RideWise Assist - Frontend Application Logic
 * Powered by GSAP (GreenSock Animation Platform) for high-end UI/UX motion
 */

// Global State
let currentSession = null;
let currentRole = "customer"; // 'customer' or 'support_agent'

// API Base URL (defaults to relative if served via http/https, falls back to localhost:8000 if opened directly)
const API_BASE = (window.location.protocol === "http:" || window.location.protocol === "https:")
  ? ""
  : "http://127.0.0.1:8000";

// Pre-defined quick prompts by role
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
  "Show open dispute claims"
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

const profileName = document.getElementById("profileName");
const profileRole = document.getElementById("profileRole");
const profileTierPill = document.getElementById("profileTierPill");
const profileAvatar = document.getElementById("profileAvatar");
const quickPromptsList = document.getElementById("quickPromptsList");
const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const typingIndicator = document.getElementById("typingIndicator");

// =========================================================
// GSAP INITIALIZATION & AMBIENT ANIMATIONS
// =========================================================
window.addEventListener("DOMContentLoaded", () => {
  initAmbientAnimations();
  initAuthModalEntrance();
});

function initAmbientAnimations() {
  // Floating glow orbs with smooth infinite yoyo
  gsap.to(".glow-1", {
    x: "+=60",
    y: "+=40",
    duration: 8,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut"
  });

  gsap.to(".glow-2", {
    x: "-=50",
    y: "-=30",
    duration: 10,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut"
  });

  gsap.to(".glow-3", {
    scale: 1.2,
    duration: 7,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut"
  });
}

function initAuthModalEntrance() {
  const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
  tl.from(".auth-modal", {
    scale: 0.88,
    autoAlpha: 0,
    y: 30,
    duration: 0.65
  })
  .from(".brand-badge", { y: -10, autoAlpha: 0, duration: 0.3 }, "-=0.3")
  .from([".brand-title", ".brand-subtitle"], { y: 15, autoAlpha: 0, stagger: 0.1, duration: 0.4 }, "-=0.2")
  .from(".role-selector", { scale: 0.95, autoAlpha: 0, duration: 0.3 }, "-=0.2")
  .from(".login-form-pane", { y: 15, autoAlpha: 0, duration: 0.35 }, "-=0.15");
}

// =========================================================
// ROLE SWITCHING (GSAP Morph/Fade)
// =========================================================
function switchLoginRole(role) {
  if (role === currentRole) return;
  currentRole = role;

  const tl = gsap.timeline({ defaults: { duration: 0.25, ease: "power2.out" } });

  if (role === "customer") {
    tabCustomer.classList.add("active");
    tabStaff.classList.remove("active");

    tl.to(staffLoginForm, {
      autoAlpha: 0,
      y: -10,
      onComplete: () => {
        staffLoginForm.classList.add("hidden");
        customerLoginForm.classList.remove("hidden");
      }
    })
    .fromTo(customerLoginForm, { autoAlpha: 0, y: 10 }, { autoAlpha: 1, y: 0 });
  } else {
    tabStaff.classList.add("active");
    tabCustomer.classList.remove("active");

    tl.to(customerLoginForm, {
      autoAlpha: 0,
      y: -10,
      onComplete: () => {
        customerLoginForm.classList.add("hidden");
        staffLoginForm.classList.remove("hidden");
      }
    })
    .fromTo(staffLoginForm, { autoAlpha: 0, y: 10 }, { autoAlpha: 1, y: 0 });
  }
}

// =========================================================
// AUTHENTICATION LOGIC
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
  gsap.fromTo(loginError, { x: -10 }, { x: 0, duration: 0.4, ease: "elastic.out(1, 0.3)" });
}

async function performLogin(payload) {
  loginError.classList.add("hidden");
  const btn = payload.role === "customer" ? document.getElementById("btnLoginCustomer") : document.getElementById("btnLoginStaff");
  btn.style.pointerEvents = "none";
  btn.style.opacity = "0.7";

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
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
    transitionToChatScreen();
  } catch (err) {
    showLoginError("Network connection error. Is backend server running?");
    btn.style.pointerEvents = "auto";
    btn.style.opacity = "1";
  }
}

// =========================================================
// TRANSITION TO CHAT SCREEN (GSAP)
// =========================================================
function transitionToChatScreen() {
  const tl = gsap.timeline();

  // Reset login buttons
  const btnCust = document.getElementById("btnLoginCustomer");
  const btnStaff = document.getElementById("btnLoginStaff");
  if (btnCust) { btnCust.style.pointerEvents = "auto"; btnCust.style.opacity = "1"; }
  if (btnStaff) { btnStaff.style.pointerEvents = "auto"; btnStaff.style.opacity = "1"; }

  // Exit auth modal with fade
  tl.to(authScreen, {
    autoAlpha: 0,
    duration: 0.35,
    ease: "power2.in",
    onComplete: () => {
      authScreen.classList.add("hidden");
      gsap.set(authScreen, { clearProps: "all" });

      // Unhide chat screen and make sure its visibility/opacity are reset to 1
      mainChatScreen.classList.remove("hidden");
      gsap.set(mainChatScreen, { autoAlpha: 1, clearProps: "opacity,visibility" });

      populateUserProfile();
      renderQuickPrompts();
      addAssistantMessage(currentSession.welcome_message, ["System Authenticator"]);
    }
  })
  // Enter Chat elements staggered
  .fromTo(".sidebar", { x: -40, autoAlpha: 0 }, { x: 0, autoAlpha: 1, duration: 0.4, ease: "power3.out" })
  .fromTo(".chat-header", { y: -20, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.3 }, "-=0.2")
  .fromTo(".chat-input-bar", { y: 20, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.3 }, "-=0.2");
}

function populateUserProfile() {
  profileName.textContent = currentSession.display_name;
  
  if (currentSession.role === "customer") {
    profileRole.textContent = `ID: ${currentSession.user_identifier}`;
    profileAvatar.textContent = "👤";
    const tier = (currentSession.customer_profile?.customer_tier || "STANDARD").toUpperCase();
    profileTierPill.textContent = tier;
    profileTierPill.className = `tier-pill ${tier.toLowerCase()}`;
    document.getElementById("entitlementDesc").textContent = `Scoped to ${currentSession.display_name}'s bookings`;
  } else {
    profileRole.textContent = "Support Operations";
    profileAvatar.textContent = "🎧";
    profileTierPill.textContent = "OPS DESK";
    profileTierPill.className = "tier-pill silver";
    document.getElementById("entitlementDesc").textContent = "Global fleet & cross-customer query scope";
  }
}

function renderQuickPrompts() {
  quickPromptsList.innerHTML = "";
  const prompts = currentSession.role === "customer" ? CUSTOMER_PROMPTS : STAFF_PROMPTS;

  prompts.forEach((promptText, i) => {
    const btn = document.createElement("button");
    btn.className = "prompt-pill";
    btn.textContent = promptText;
    btn.onclick = () => {
      messageInput.value = promptText;
      handleSendMessage();
    };
    quickPromptsList.appendChild(btn);
  });

  // Staggered entry animation for quick prompt pills
  gsap.from(".prompt-pill", {
    x: -15,
    autoAlpha: 0,
    duration: 0.3,
    stagger: 0.05,
    ease: "power2.out"
  });
}

// =========================================================
// CHAT MESSAGING & GSAP BUBBLE REVEALS
// =========================================================
async function handleSendMessage() {
  const text = messageInput.value.trim();
  if (!text || !currentSession) return;

  messageInput.value = "";
  addUserMessage(text);
  showTyping(true);

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
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
  row.className = "message-row user";
  row.innerHTML = `
    <div class="msg-avatar">${currentSession.role === "customer" ? "👤" : "🎧"}</div>
    <div class="msg-bubble-wrapper">
      <div class="msg-bubble">${escapeHtml(text)}</div>
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();

  gsap.from(row, {
    y: 15,
    autoAlpha: 0,
    scale: 0.96,
    duration: 0.35,
    ease: "power2.out"
  });
}

function addAssistantMessage(markdownText, citations = [], cacheStatus = null) {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  
  const parsedHtml = marked.parse(markdownText);
  let citationDrawerHtml = "";

  if (citations && citations.length > 0) {
    const pills = citations.map(c => `<span class="cite-pill">${escapeHtml(c)}</span>`).join("");
    const cacheBadge = cacheStatus ? `<span class="cite-pill" style="border-color:#38bdf8;color:#38bdf8;">⚡ ${cacheStatus}</span>` : "";
    citationDrawerHtml = `
      <div class="citation-drawer">
        <div class="citation-header">
          <span>📚 Verified Citations & Ledger Records</span>
          <span>▼</span>
        </div>
        <div class="citation-pills">${cacheBadge}${pills}</div>
      </div>
    `;
  }

  row.innerHTML = `
    <div class="msg-avatar">⚡</div>
    <div class="msg-bubble-wrapper">
      <div class="msg-bubble">${parsedHtml}</div>
      ${citationDrawerHtml}
    </div>
  `;

  chatMessages.appendChild(row);
  scrollToBottom();

  // GSAP animation for AI response reveal
  gsap.from(row, {
    y: 20,
    autoAlpha: 0,
    scale: 0.97,
    duration: 0.45,
    ease: "power2.out"
  });
}

function showTyping(show) {
  if (show) {
    typingIndicator.classList.remove("hidden");
    // GSAP bouncing dots stagger
    gsap.to(".typing-dot", {
      y: -6,
      duration: 0.35,
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
  
  // Quick spin animation on reset button icon
  gsap.to(".reset-icon", { rotation: "+=360", duration: 0.5, ease: "power2.out" });

  try {
    await fetch(`${API_BASE}/api/chat/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSession.session_id })
    });
    
    // Animate out old messages and clear
    gsap.to(".message-row", {
      autoAlpha: 0,
      y: -10,
      stagger: 0.05,
      duration: 0.25,
      onComplete: () => {
        chatMessages.innerHTML = "";
        addAssistantMessage(
          `Conversation context refreshed. Hello **${currentSession.display_name}**, how can I assist you?`,
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
    ease: "power2.in",
    onComplete: () => {
      mainChatScreen.classList.add("hidden");
      // Clear inline style overrides set by GSAP animations
      gsap.set(mainChatScreen, { clearProps: "all" });
      gsap.set([".sidebar", ".chat-header", ".chat-input-bar", ".prompt-pill"], { clearProps: "all" });

      authScreen.classList.remove("hidden");
      gsap.fromTo(authScreen, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3, ease: "power2.out" });

      // Reset login form fields and errors
      loginError.classList.add("hidden");
      loginError.textContent = "";

      const btnCust = document.getElementById("btnLoginCustomer");
      const btnStaff = document.getElementById("btnLoginStaff");
      if (btnCust) { btnCust.style.pointerEvents = "auto"; btnCust.style.opacity = "1"; }
      if (btnStaff) { btnStaff.style.pointerEvents = "auto"; btnStaff.style.opacity = "1"; }

      chatMessages.innerHTML = "";
      messageInput.value = "";
      currentSession = null;
    }
  });
}
