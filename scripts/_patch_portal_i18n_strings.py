from pathlib import Path

p = Path(r"D:\ECommerce-Fraud_Analysis_Detection\static\analyst-portal\app.js")
text = p.read_text(encoding="utf-8")

repls = [
    (">Overview</h1>", '>${esc(t("overview"))}</h1>'),
    (
        "<option>This Month</option><option>This Week</option><option>Today</option>",
        '<option>${esc(t("period_this_month"))}</option><option>${esc(t("period_this_week"))}</option><option>${esc(t("period_today"))}</option>',
    ),
    ("Loading dashboard...", '${esc(t("loading_dashboard"))}'),
    ("Orders in Queue", '${esc(t("orders_in_queue"))}'),
    (">Pending Review</div>", '>${esc(t("pending_review"))}</div>'),
    (">On Hold</div>", '>${esc(t("on_hold"))}</div>'),
    ("Backlog (Overdue)", '${esc(t("backlog_overdue_label"))}'),
    (">Statistics</p>", '>${esc(t("statistics"))}</p>'),
    (
        '<h3 style="margin:0">Review Queue</h3>',
        '<h3 style="margin:0">${esc(t("review_queue"))}</h3>',
    ),
    (">Total in Queue</div>", '>${esc(t("total_in_queue"))}</div>'),
    (">Whitelisted</div>", '>${esc(t("whitelisted"))}</div>'),
    (">Now blacklisted</div>", '>${esc(t("now_blacklisted"))}</div>'),
    ("Could not load rule stats.", '${esc(t("could_not_load_rule_stats"))}'),
    ("Could not load rule status.", '${esc(t("could_not_load_rule_status"))}'),
]

for old, new in repls:
    n = text.count(old)
    print(f"{n}x {old[:70]!r}")
    if n:
        text = text.replace(old, new)

# Chatbot block replacements (exact)
chat_old = '''  const examples = [
    { title: "Fraud volume", prompt: "Total fraudulent orders" },
    { title: "By region", prompt: "Fraud rate by state" },
    { title: "Bestsellers", prompt: "Top selling products" },
  ];
  document.getElementById("app").innerHTML = shell(`
    <div class="gpt-shell">
      <header class="gpt-top">
        <div>
          <h1 class="gpt-title">Analytics AI Chatbot</h1>
          <p class="gpt-subtitle">Ask about orders, fraud, revenue, and risk patterns</p>
        </div>
        <button type="button" class="btn btn-secondary" id="chat-clear">New chat</button>
      </header>
      <div class="gpt-messages" id="chat-log"></div>
      <div class="gpt-composer-wrap">
        <form id="chat-form" class="gpt-composer">
          <textarea id="chat-input" rows="1" placeholder="Message Analytics AI Chatbot…" ></textarea>
          <button class="gpt-send" type="submit" title="Send" aria-label="Send">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          </button>
        </form>
        <p class="gpt-disclaimer">Answers are generated from live analytics data. Review insights before acting.</p>
      </div>
    </div>
  `, "chatbot");'''

chat_new = '''  const examples = [
    { title: t("chat_ex_fraud_title"), prompt: t("chatbot_example_1") },
    { title: t("chat_ex_region_title"), prompt: t("chatbot_example_2") },
    { title: t("chat_ex_best_title"), prompt: t("chatbot_example_5") },
  ];
  document.getElementById("app").innerHTML = shell(`
    <div class="gpt-shell">
      <header class="gpt-top">
        <div>
          <h1 class="gpt-title">${esc(t("nav_analytics_ai"))}</h1>
          <p class="gpt-subtitle">${esc(t("chatbot_subtitle"))}</p>
        </div>
        <button type="button" class="btn btn-secondary" id="chat-clear">${esc(t("chat_new"))}</button>
      </header>
      <div class="gpt-messages" id="chat-log"></div>
      <div class="gpt-composer-wrap">
        <form id="chat-form" class="gpt-composer">
          <textarea id="chat-input" rows="1" placeholder="${esc(t("chat_placeholder"))}" ></textarea>
          <button class="gpt-send" type="submit" title="Send" aria-label="Send">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          </button>
        </form>
        <p class="gpt-disclaimer">${esc(t("chat_disclaimer"))}</p>
      </div>
    </div>
  `, "chatbot");'''

if chat_old in text:
    text = text.replace(chat_old, chat_new)
    print("chatbot block replaced")
else:
    print("chatbot block MISS")

empty_old = '''    return `<div class="gpt-empty">
      <div class="gpt-empty-icon">AI</div>
      <h2>How can I help with fraud analytics?</h2>
      <p>Ask a question, or start with one of these:</p>'''

empty_new = '''    return `<div class="gpt-empty">
      <div class="gpt-empty-icon">AI</div>
      <h2>${esc(t("chat_empty_title"))}</h2>
      <p>${esc(t("chat_empty_hint"))}</p>'''

if empty_old in text:
    text = text.replace(empty_old, empty_new)
    print("empty state replaced")
else:
    print("empty state MISS")

# Users tab common labels
users_repls = [
    ("<h3>Create New Analyst</h3>", '<h3>${esc(t("create_analyst"))}</h3>'),
    (
        '<p class="subtitle">Spin up a profile so they can start reviewing risk work.</p>',
        '<p class="subtitle">${esc(t("create_analyst_subtitle"))}</p>',
    ),
    ("<label>Analyst ID</label>", '<label>${esc(t("analyst_id"))}</label>'),
    ("<label>Employee Name</label>", '<label>${esc(t("employee_name"))}</label>'),
    ("<label>Username</label>", '<label>${esc(t("username"))}</label>'),
    ("<label>Password</label>", '<label>${esc(t("password"))}</label>'),
    ("<label>Role</label>", '<label>${esc(t("role"))}</label>'),
    (
        "<span>I confirm that I want to create this analyst profile</span>",
        '<span>${esc(t("confirm_create_analyst_chk"))}</span>',
    ),
    (
        'class="btn btn-primary">Create Analyst</button>',
        'class="btn btn-primary">${esc(t("create_analyst"))}</button>',
    ),
    ("<h3>Team pulse</h3>", '<h3>${esc(t("team_pulse"))}</h3>'),
    (
        '<p class="subtitle">Who is clearing volume and catching fraud.</p>',
        '<p class="subtitle">${esc(t("team_pulse_subtitle"))}</p>',
    ),
    (
        'admin-mini-stat-label">Analysts</span>',
        'admin-mini-stat-label">${esc(t("analysts_count"))}</span>',
    ),
    (
        'admin-mini-stat-label">Reviewed</span>',
        'admin-mini-stat-label">${esc(t("reviewed"))}</span>',
    ),
    (
        'admin-mini-stat-label">Rejected</span>',
        'admin-mini-stat-label">${esc(t("rejected"))}</span>',
    ),
    ('<p class="subtitle">Loading...</p>', '<p class="subtitle">${esc(t("loading_ellipsis"))}</p>'),
    ('<p class="subtitle">No analysts found.</p>', '<p class="subtitle">${esc(t("no_analysts_found"))}</p>'),
]
for old, new in users_repls:
    n = text.count(old)
    print(f"{n}x users:{old[:50]!r}")
    if n:
        text = text.replace(old, new)

# auto-approved messages
auto1 = "${sync.auto_approved} order(s) auto-approved after hold window."
auto1n = '${esc(t("auto_approved_hold", { n: sync.auto_approved }))}'
if auto1 in text:
    text = text.replace(auto1, auto1n)
    print("auto-approved replaced")

p.write_text(text, encoding="utf-8")
print("done")
