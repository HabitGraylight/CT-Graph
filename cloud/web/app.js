const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const intensityNames = {
  sweet: "甜感",
  sour: "酸感",
  bitter: "苦感",
  strength: "酒精感",
  body: "厚重感",
  aroma: "香气强度",
};
const qualityNames = {
  appearance: "外观",
  aroma: "香气",
  balance: "平衡",
  structure: "层次",
  texture: "口感",
  execution: "执行",
  expression: "表达",
};
const state = {
  catalog: null,
  frame: "sour",
  account: { user: null },
  community: [],
  qualified: false,
  authMode: "login",
  taste: null,
  publish: null,
  context: {},
};
let noticeTimer;
let pendingSave = null;

async function api(action, body = {}) {
  const response = await fetch("/api/app", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, ...body }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "请求未完成");
  return result;
}
async function get(resource) {
  const response = await fetch(
    "/api/app?resource=" + encodeURIComponent(resource),
    { credentials: "same-origin", cache: "no-store" },
  );
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "读取失败");
  return result;
}
function notify(message, error = false) {
  clearTimeout(noticeTimer);
  $("notice").textContent = message;
  $("notice").classList.toggle("error", error);
  $("notice").hidden = false;
  noticeTimer = setTimeout(() => ($("notice").hidden = true), 6500);
}
async function busy(button, task) {
  if (button.disabled) return;
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  try {
    await task();
  } catch (error) {
    notify(error.message, true);
  } finally {
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }
}
function go(view) {
  document
    .querySelectorAll(".view")
    .forEach((el) => (el.hidden = el.id !== view));
  document
    .querySelectorAll("[data-view]")
    .forEach((el) => el.classList.toggle("active", el.dataset.view === view));
  if (view === "profile") renderProfile();
  if (view === "community")
    refreshCommunity().catch((e) => notify(e.message, true));
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function showAuth(mode = "login") {
  if (!state.catalog?.configured) {
    notify("请先连接 Supabase。部署说明中有完整配置步骤。", true);
    return;
  }
  state.authMode = mode;
  const reset = mode === "password",
    recover = mode === "recover",
    signup = mode === "signup";
  $("auth-title").textContent = reset
    ? "设置新密码"
    : recover
      ? "找回密码"
      : signup
        ? "为你的味蕾建一本手记"
        : "欢迎回来";
  $("auth-copy").textContent = signup
    ? "注册后请查收确认邮件。密码至少 10 位。"
    : reset
      ? "设置至少 10 位的新密码。"
      : "账号、私有配方和试饮会保存在本站云端。";
  $("auth-email").parentElement.hidden = reset;
  $("auth-email").required = !reset;
  $("password-label").hidden = recover;
  $("auth-password").required = !recover;
  $("auth-password").minLength = signup || reset ? 10 : 1;
  $("auth-password").autocomplete =
    signup || reset ? "new-password" : "current-password";
  $("auth-password").value = "";
  $("auth-status").textContent = "";
  $("auth-submit").textContent = reset
    ? "更新密码"
    : recover
      ? "发送重置邮件"
      : signup
        ? "创建账号"
        : "登录";
  $("auth-switch").textContent = signup ? "已有账号？登录" : "还没有账号？注册";
  $("auth-switch").hidden = reset;
  $("auth-recover").hidden = reset || recover;
  if (!$("auth-dialog").open) $("auth-dialog").showModal();
}
function requireUser() {
  if (state.account.user) return true;
  showAuth();
  return false;
}
async function refreshAccount() {
  const previous = state.account.user?.id;
  state.account = await get("state");
  if (previous && previous !== state.account.user?.id) {
    $("recipe").value = "";
    $("recipe-title").value = "";
    $("pantry").value = "";
    $("avoid").value = "";
    resetContext();
    pendingSave = null;
    $("result").innerHTML =
      '<div class="empty"><h3>准备好下一杯了吗？</h3><p>填写配方后再评价或补全。</p></div>';
    state.taste = null;
    state.publish = null;
    for (const id of ["taste-dialog", "publish-dialog"])
      if ($(id).open) $(id).close();
  }
  $("account-button").textContent = state.account.user
    ? (state.account.profile?.display_name || "我的账号") + " ↗"
    : "登录 / 注册 ↗";
  $("personalize").disabled = !state.account.user;
  if (!state.account.user) $("personalize").checked = false;
  $("personal-state").textContent = state.account.user
    ? "基于你的实饮与自报偏好"
    : "登录后启用";
  if (!$("profile").hidden) renderProfile();
}
function frame() {
  return state.catalog.frameworks.find((f) => f.id === state.frame);
}
function chooseFrame(id) {
  state.frame = id;
  const f = frame();
  document
    .querySelectorAll(".frame-button")
    .forEach((b) => b.classList.toggle("active", b.dataset.frame === id));
  $("frame-title").textContent = f.zh;
  $("frame-en").textContent = f.en;
  $("frame-formula").textContent = f.formula;
  $("frame-description").textContent = f.description;
  $("method").innerHTML =
    '<option value="">尚未确定</option>' +
    Object.entries(state.catalog.methods)
      .map(
        ([k, v]) =>
          `<option value="${esc(k)}">${esc(typeof v === "string" ? v : v.zh || v.name || k)}</option>`,
      )
      .join("");
  $("method").value = f.methods[0];
  $("recommend").hidden = id !== "sour";
}
function template() {
  const f = frame();
  $("recipe").value = f.slots
    .map((s) => `${s.default} ${s.amount} ${s.unit}`)
    .join("\n");
  $("recipe-title").value = "我的 " + f.en;
  $("method").value = f.methods[0];
  resetContext();
}
function resetContext() {
  state.context = {};
  $("advanced-context").value = "";
  $("dilution").value = "";
  $("temperature").value = "";
  $("service").value = "";
}
function requestBody() {
  let context = {};
  if ($("advanced-context").value.trim()) {
    try {
      context = JSON.parse($("advanced-context").value);
    } catch {
      throw new Error("调制条件 JSON 格式有误");
    }
    if (!context || Array.isArray(context) || typeof context !== "object")
      throw new Error("调制条件需要是 JSON 对象");
  }
  if ($("dilution").value !== "")
    context.dilution_ml = Number($("dilution").value);
  if ($("temperature").value !== "")
    context.temperature_c = Number($("temperature").value);
  if ($("service").value)
    context.process = { ...context.process, service: $("service").value };
  return {
    frame: state.frame,
    recipe: $("recipe").value,
    title: $("recipe-title").value,
    method: $("method").value,
    context,
    pantry: $("pantry").value,
    avoid: $("avoid").value,
    personalize: $("personalize").checked,
  };
}
function renderEvaluation(e) {
  const risks = e.judge?.risks || [];
  const estimates = e.judge?.composition?.estimates || {};
  return `<div class="score-box"><strong>${e.score ?? "—"}</strong><span>框架契合度<small>/ 100 · 不代表好喝分</small></span></div>
    <p>${esc(e.confidence)}</p><ul class="suggestions">${e.suggestions.map((x) => `<li>${esc(x)}</li>`).join("") || "<li>原料与比例落在当前框架范围内，下一步用实饮验证。</li>"}</ul>
    ${risks.map((r) => `<div class="risk">${esc(r.message || r.explanation || r.title || r.id)}</div>`).join("")}
    <details><summary>七维 Judge · 分别看什么</summary>${(e.judge?.dimensions || []).map((d) => `<h4>${esc(d.name)} · ${esc(d.status)}</h4><p>${esc((d.basis || []).join(" "))}</p><p class="hint">实饮时观察：${esc(d.tasting_prompt)}</p>`).join("")}<p class="hint">未试饮的感官分保持为空，不用框架分替代。</p></details>
    <details><summary>成分相互作用与条件</summary>${(e.judge?.interactions || []).map((r) => `<h4>${esc(r.title)}</h4><p>${esc(r.effect)}</p><p class="hint">适用条件：${esc(r.conditions)}<br>可验证的问题：${esc(r.verification)}</p>`).join("") || "<p>没有匹配的公开机制提示。</p>"}<div class="source-links">${(
      e.judge?.sources || []
    )
      .filter((s) => /^https:\/\//.test(s.url))
      .map(
        (s) =>
          `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a>`,
      )
      .join("")}</div></details>
    <details><summary>计算依据与未知项</summary><p>${esc(e.score_explanation)}</p>${Object.entries(
      estimates,
    )
      .map(
        ([k, v]) =>
          `<p>${esc(v.label || k)}：${v.value == null ? "未知" : esc(v.value)} ${esc(v.unit)}</p>`,
      )
      .join(
        "",
      )}<p>浓度缺少依据时保持未知。已有规则只能提出设计问题，无法替代实际品鉴。</p></details>
    <details><summary>框架参考来源</summary><div class="source-links">${(
      e.sources || []
    )
      .filter((url) => /^https:\/\//.test(url))
      .map(
        (url, i) =>
          `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">参考 ${i + 1} ↗</a>`,
      )
      .join("")}</div></details>`;
}
function recipeText(recipe) {
  return recipe
    .map((r) =>
      `${r.display_name || r.name} ${r.amount ?? ""} ${r.unit || ""}`.trim(),
    )
    .join("\n");
}
function loadRecipe(row) {
  chooseFrame(row.frame);
  $("recipe").value =
    typeof row.recipe === "string" ? row.recipe : recipeText(row.recipe);
  $("recipe-title").value = row.title || $("recipe-title").value || "我的试配";
  $("method").value = row.method || "";
  resetContext();
  $("advanced-context").value = Object.keys(row.context || {}).length
    ? JSON.stringify(row.context, null, 2)
    : "";
  go("studio");
  $("work-heading").scrollIntoView({ behavior: "smooth" });
  notify("已载入这一版本。修改后保存会建立新的版本。");
}
async function analyze(action, button) {
  await busy(button, async () => {
    const result = await api(action, requestBody());
    if (result.blocked) {
      $("result").innerHTML =
        `<h3>先补充一点信息</h3><p>${esc(result.reason)}</p>`;
      return;
    }
    if (action === "recommend") {
      $("result").innerHTML =
        `<p class="callout">${esc(result.personal_note)}</p><p class="hint">三个候选各自保留原版条件。先选一个载入工作台，再保存或实饮。</p>` +
        result.candidates
          .map(
            (c, i) =>
              `<article class="candidate"><h4>${esc(c.title)} ${c.id === result.suggested_trial ? '<span class="tag">建议先试</span>' : ""}</h4><pre>${esc(recipeText(c.snapshot.recipe))}</pre><p>${esc(c.tradeoff)}</p><button class="text-link" data-candidate="${i}">载入这一版 ↗</button></article>`,
          )
          .join("");
      $("result")
        .querySelectorAll("[data-candidate]")
        .forEach(
          (b) =>
            (b.onclick = () =>
              loadRecipe(
                result.candidates[Number(b.dataset.candidate)].snapshot,
              )),
        );
    } else {
      if (action === "complete") {
        $("recipe").value = recipeText(result.recipe);
        $("method").value = result.method;
        $("result").innerHTML =
          `<p class="callout">${esc(result.personal_note)}</p>` +
          renderEvaluation(result.evaluation);
        if (result.shopping?.length)
          $("result").innerHTML +=
            `<h4>需要补充</h4><ul class="suggestions">${result.shopping.map((r) => `<li>${esc(r.display_name || r.name)} ${esc(r.amount)} ${esc(r.unit)}</li>`).join("")}</ul>`;
      } else $("result").innerHTML = renderEvaluation(result);
      $("result").insertAdjacentHTML(
        "beforeend",
        '<button id="save-recipe" class="button wide">保存为私有版本</button><p class="hint">配方之后的每次修改都另存版本，避免混用旧评分。</p>',
      );
      $("save-recipe").onclick = () => saveRecipe($("save-recipe"));
    }
    if (window.innerWidth < 1050)
      $("result").scrollIntoView({ behavior: "smooth", block: "start" });
  });
}
async function saveRecipe(button) {
  if (!requireUser()) return;
  if (!$("recipe-title").value.trim()) {
    notify("先给这杯酒起个名字。", true);
    $("recipe-title").focus();
    return;
  }
  await busy(button, async () => {
    const body = requestBody(),
      fingerprint = JSON.stringify(body);
    if (pendingSave?.fingerprint !== fingerprint)
      pendingSave = { fingerprint, id: crypto.randomUUID() };
    const rows = await api("save_recipe", {
      ...body,
      request_id: pendingSave.id,
    });
    pendingSave = null;
    await refreshAccount();
    notify("已保存为私有版本，可以记录试饮了。");
    if (rows?.[0]) openTaste(rows[0]);
  });
}
function inputFields(names, prefix, values = {}) {
  return Object.entries(names)
    .map(
      ([k, v]) =>
        `<label>${esc(v)}<input id="${prefix}-${k}" type="number" min="0" max="10" step="0.5" placeholder="未评" value="${esc(values[k] ?? "")}"></label>`,
    )
    .join("");
}
function readFields(names, prefix) {
  return Object.fromEntries(
    Object.keys(names)
      .filter((k) => $(prefix + "-" + k).value !== "")
      .map((k) => [k, Number($(prefix + "-" + k).value)]),
  );
}
function chart(target) {
  return `<svg class="profile-chart" viewBox="0 0 450 248" role="img" aria-label="六项个人风味目标，0 到 10；空白代表未记录">${Object.entries(
    target.targets,
  )
    .map(([k, t], i) => {
      const y = 25 + i * 35;
      return `<text x="0" y="${y + 4}">${esc(t.label)}</text><rect class="track" x="84" y="${y - 7}" width="300" height="10" rx="5"/>${t.value == null ? "" : `<rect class="target" x="84" y="${y - 7}" width="${Math.max(0, Math.min(10, t.value)) * 30}" height="10" rx="5"/>`}<text x="404" y="${y + 4}">${t.value ?? "—"}</text>`;
    })
    .join(
      "",
    )}<text x="84" y="243">0 · 弱</text><text x="353" y="243">10 · 强</text></svg>`;
}
function renderProfile() {
  const a = state.account;
  if (!a.user) {
    $("profile-content").innerHTML =
      '<div class="empty-wide"><h3>你的风味档案，还差一个开始</h3><p>注册后记录偏好，保存私有配方，逐步积累真实试饮。</p><button id="profile-login" class="button">登录 / 创建账号 ↗</button></div>';
    $("profile-login").onclick = () => showAuth();
    return;
  }
  const publicCount = a.recipes.filter((r) => r.visibility === "public").length;
  $("profile-content").innerHTML =
    `<div class="stats"><div class="stat"><strong>${a.recipes.length}</strong><span>已保存版本 · 最近 50 条</span></div><div class="stat"><strong>${a.tastings.length}</strong><span>已记录实饮版本 · 最近 200 条</span></div><div class="stat"><strong>${publicCount}</strong><span>当前列表中已公开</span></div></div><div class="profile-layout"><section class="panel"><div class="baseline-head"><h3>我的风味基准</h3><select id="baseline-frame" aria-label="基准框架"><option value="">所有框架</option>${state.catalog.frameworks.map((f) => `<option value="${f.id}">${esc(f.zh)}</option>`).join("")}</select></div><div id="baseline-chart"></div><p class="hint" id="baseline-note"></p><details><summary>这个基准怎么来的？</summary><p class="hint">${esc(a.baseline.method)}</p><p class="hint">自报起点跨框架通用；实饮只使用你选定框架的记录。它描述你喜欢的酒表现出的强度，不代表某种原料应该加多少。</p></details></section><section class="panel"><h3>先说说想喝到的味道</h3><p class="hint">0 = 希望较弱，10 = 希望较强。暂不确定就留空；不会自动当作 5 分。</p><form id="profile-form"><label>昵称<input id="display-name" maxlength="40" required value="${esc(a.profile.display_name)}"></label><div class="preference-fields">${inputFields(intensityNames, "pref", a.profile.preferences)}</div><button class="button" type="submit">保存偏好</button></form></section></div><div class="collection-heading"><h2>我的配方版本</h2><button id="new-recipe" class="text-link">去调一杯 ↗</button></div><div id="my-recipes" class="recipe-grid"></div><div class="collection-heading"><h2>试饮手记</h2><button id="export-data" class="text-link">导出我的数据 ↓</button></div><div id="my-tastings"></div><div class="actions"><button id="change-password" class="button secondary">修改密码</button><button id="logout" class="button secondary">退出登录</button></div>`;
  const updateChart = () => {
    const b = $("baseline-frame").value
      ? a.baselines[$("baseline-frame").value]
      : a.baseline;
    $("baseline-chart").innerHTML = chart(b);
    $("baseline-note").textContent =
      `${b.confidence} · ${b.liked_recipes} 个喜欢的实饮版本 / ${b.tasted_recipes} 个已记录版本。均值是参考，尚未证明因果关系。`;
  };
  $("baseline-frame").onchange = updateChart;
  updateChart();
  $("profile-form").onsubmit = (e) => {
    e.preventDefault();
    busy(e.submitter, async () => {
      await api("profile", {
        display_name: $("display-name").value,
        preferences: readFields(intensityNames, "pref"),
      });
      await refreshAccount();
      notify("风味起点已保存。");
    });
  };
  $("new-recipe").onclick = () => go("studio");
  $("my-recipes").innerHTML = a.recipes.length
    ? a.recipes
        .map(
          (r, i) =>
            `<article class="recipe-tile"><span class="tag">${r.visibility === "public" ? "已公开" : "仅自己可见"} · ${esc(r.frame)}</span><h3>${esc(r.title)}</h3><div class="tile-meta">${esc(new Date(r.created_at).toLocaleDateString())} · ${esc(r.method || "技法未填")}</div><pre>${esc(r.recipe)}</pre><div class="tile-footer"><button class="text-link" data-taste="${i}">记录试饮</button><button class="text-link" data-load="${i}">修改并另存</button><button class="text-link" data-publish="${i}">${r.visibility === "public" ? "撤回公开" : "发布到社区"}</button></div></article>`,
        )
        .join("")
    : '<div class="empty-wide"><h3>第一份私有配方，在等你命名</h3><p>在工作台评价或补全后，点击“保存为私有版本”。</p></div>';
  $("my-recipes")
    .querySelectorAll("[data-taste]")
    .forEach(
      (b) => (b.onclick = () => openTaste(a.recipes[Number(b.dataset.taste)])),
    );
  $("my-recipes")
    .querySelectorAll("[data-load]")
    .forEach(
      (b) => (b.onclick = () => loadRecipe(a.recipes[Number(b.dataset.load)])),
    );
  $("my-recipes")
    .querySelectorAll("[data-publish]")
    .forEach(
      (b) =>
        (b.onclick = () => {
          const r = a.recipes[Number(b.dataset.publish)];
          if (r.visibility === "public")
            busy(b, async () => {
              await api("visibility", { id: r.id, visibility: "private" });
              await refreshAccount();
              notify("已撤回公开，现仅自己可见。");
            });
          else openPublish(r);
        }),
    );
  $("my-tastings").innerHTML = a.tastings.length
    ? a.tastings
        .map(
          (t, i) =>
            `<article class="taste-entry"><div><strong>${esc(t.title)} · 喜欢 ${esc(t.liking)}/10</strong><p>${esc(t.notes || "没有文字笔记")}</p><small>${t.public_vote ? "允许匿名汇总" : "仅用于个人基准"} · ${esc(new Date(t.updated_at).toLocaleString())}</small></div><button class="text-link" data-delete-taste="${i}">删除记录</button></article>`,
        )
        .join("")
    : '<div class="empty-wide"><p>还没有真实试饮记录。配方的设计评分不会自动成为试饮评分。</p></div>';
  $("my-tastings")
    .querySelectorAll("[data-delete-taste]")
    .forEach(
      (b) =>
        (b.onclick = () => {
          if (confirm("删除这条试饮记录？它也会退出个人基准和社区统计。"))
            busy(b, async () => {
              await api("delete_taste", {
                id: a.tastings[Number(b.dataset.deleteTaste)].id,
              });
              await refreshAccount();
              notify("试饮记录已删除。");
            });
        }),
    );
  $("export-data").onclick = () => {
    const blob = new Blob(
      [
        JSON.stringify(
          {
            exported_at: new Date().toISOString(),
            scope: "最近 50 个配方版本与 200 条试饮记录",
            ...a,
          },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "cocktail-personal-export.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  $("change-password").onclick = () => showAuth("password");
  $("logout").onclick = () =>
    busy($("logout"), async () => {
      await api("logout");
      await refreshAccount();
      notify("已退出登录。");
    });
}
function openTaste(recipe) {
  if (!requireUser()) return;
  state.taste = recipe;
  const old =
    state.account.tastings.find((t) => t.recipe_id === recipe.id) || {};
  $("taste-form").reset();
  $("taste-title").textContent = recipe.title;
  $("taste-liking").value = old.liking ?? "";
  $("taste-notes").value = old.notes || "";
  $("public-vote").checked = !!old.public_vote;
  $("intensity-inputs").innerHTML = inputFields(
    intensityNames,
    "taste",
    old.intensities,
  );
  $("quality-inputs").innerHTML = inputFields(
    qualityNames,
    "quality",
    old.quality,
  );
  $("taste-status").textContent = "";
  $("taste-dialog").showModal();
}
function openPublish(recipe) {
  state.publish = recipe;
  $("publish-form").reset();
  $("publish-status").textContent = "";
  $("publish-preview").textContent =
    recipe.title +
    "\n" +
    recipe.recipe +
    "\n" +
    JSON.stringify(recipe.context, null, 2);
  $("publish-dialog").showModal();
}
async function refreshCommunity() {
  const result = await get("community");
  state.community = result.recipes;
  renderCommunity();
}
function renderCommunity() {
  const selected = $("community-frame").value;
  const rows = state.community.filter(
    (r) =>
      (!selected || r.frame === selected) && (!state.qualified || r.qualified),
  );
  $("community-list").innerHTML = rows.length
    ? rows
        .map(
          (r) =>
            `<article class="recipe-tile"><span class="tag">${esc(r.frame)} · ${r.qualified ? "高分入选" : "积累试饮中"}</span><h3>${esc(r.title)}</h3><div class="tile-meta">分享者 ${esc(r.author)} · ${r.voters} 位贡献评分的用户</div><pre>${esc(r.recipe)}</pre><p>${r.average_liking == null ? "不足 3 位，暂不显示均分" : `喜欢程度 ${esc(r.average_liking)}/10 · 排序分 ${esc(r.ranking_score)}`}</p><details><summary>调制条件与风味强度</summary><pre>${esc(JSON.stringify(r.context, null, 2))}</pre>${Object.entries(
              intensityNames,
            )
              .map(
                ([k, v]) =>
                  `<p class="hint">${v}：${r.intensities[k] ?? "样本不足"}</p>`,
              )
              .join(
                "",
              )}</details><div class="tile-footer"><button class="text-link" data-community-load="${esc(r.id)}">载入工作台 ↗</button><button class="text-link" data-community-taste="${esc(r.id)}">我做过，记一次试饮</button></div></article>`,
        )
        .join("")
    : `<div class="empty-wide"><span class="empty-mark">◒</span><h3>${state.qualified ? "好配方，需要真实的回声" : "社区的第一杯，等你来分享"}</h3><p>${state.qualified ? "还没有达到入选门槛的配方。新社区不会预置虚构评分。" : "先在工作台保存私有版本，确认内容后再发布到这里。"}</p><button class="text-link" id="community-start">去调配工作台 ↗</button></div>`;
  $("community-start")?.addEventListener("click", () => go("studio"));
  $("community-list")
    .querySelectorAll("[data-community-load]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          loadRecipe(
            state.community.find((r) => r.id === b.dataset.communityLoad),
          )),
    );
  $("community-list")
    .querySelectorAll("[data-community-taste]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          openTaste(
            state.community.find((r) => r.id === b.dataset.communityTaste),
          )),
    );
}

document
  .querySelectorAll("[data-view]")
  .forEach((b) => (b.onclick = () => go(b.dataset.view)));
document
  .querySelectorAll("[data-go]")
  .forEach((b) => (b.onclick = () => go(b.dataset.go)));
document
  .querySelectorAll("[data-close]")
  .forEach((b) => (b.onclick = () => $(b.dataset.close).close()));
$("privacy-button").onclick = () => $("privacy-dialog").showModal();
$("account-button").onclick = () =>
  state.account.user ? go("profile") : showAuth();
$("auth-switch").onclick = () =>
  showAuth(state.authMode === "signup" ? "login" : "signup");
$("auth-recover").onclick = () => showAuth("recover");
$("auth-form").onsubmit = (e) => {
  e.preventDefault();
  busy(e.submitter, async () => {
    try {
      const result = await api(state.authMode, {
        email: $("auth-email").value,
        password: $("auth-password").value,
      });
      $("auth-password").value = "";
      $("auth-status").textContent = result.message;
      if (["login", "password"].includes(state.authMode)) {
        await refreshAccount();
        $("auth-dialog").close();
        notify(result.message);
      }
    } catch (err) {
      $("auth-status").textContent = err.message;
    }
  });
};
$("taste-form").onsubmit = (e) => {
  e.preventDefault();
  busy(e.submitter, async () => {
    try {
      await api("taste", {
        recipe_id: state.taste.id,
        tasted: $("actually-tasted").checked,
        as_recipe: $("as-recipe").checked,
        liking: Number($("taste-liking").value),
        notes: $("taste-notes").value,
        quality: readFields(qualityNames, "quality"),
        intensities: readFields(intensityNames, "taste"),
        public_vote: $("public-vote").checked,
      });
      await refreshAccount();
      if (!$("community").hidden) await refreshCommunity();
      $("taste-dialog").close();
      notify("真实试饮已保存，风味基准已更新。");
    } catch (err) {
      $("taste-status").textContent = err.message;
    }
  });
};
$("publish-form").onsubmit = (e) => {
  e.preventDefault();
  busy(e.submitter, async () => {
    try {
      await api("visibility", {
        id: state.publish.id,
        visibility: "public",
        consent: $("publish-consent").checked,
      });
      await refreshAccount();
      $("publish-dialog").close();
      notify("这一版本已发布到社区。");
    } catch (err) {
      $("publish-status").textContent = err.message;
    }
  });
};
$("load-template").onclick = template;
$("try-sour").onclick = () => {
  chooseFrame("sour");
  template();
  analyze("evaluate", $("evaluate"));
};
$("jump-recipe").onclick = () =>
  $("work-heading").scrollIntoView({ behavior: "smooth" });
["evaluate", "complete", "recommend"].forEach(
  (action) => ($(action).onclick = () => analyze(action, $(action))),
);
$("show-all").onclick = () => {
  state.qualified = false;
  $("show-all").classList.add("active");
  $("show-qualified").classList.remove("active");
  renderCommunity();
};
$("show-qualified").onclick = () => {
  state.qualified = true;
  $("show-qualified").classList.add("active");
  $("show-all").classList.remove("active");
  renderCommunity();
};
$("community-frame").onchange = renderCommunity;

async function start() {
  // Remove email-link credentials from the URL before rendering or other requests.
  const fragment = new URLSearchParams(location.hash.slice(1));
  const access = fragment.get("access_token"),
    refresh = fragment.get("refresh_token"),
    recovery = fragment.get("type") === "recovery";
  if (location.hash)
    history.replaceState(null, "", location.pathname + location.search);
  try {
    state.catalog = await get("catalog");
    $("setup-banner").hidden = state.catalog.configured;
    $("frame-list").innerHTML = state.catalog.frameworks
      .map(
        (f, i) =>
          `<button class="frame-button" data-frame="${esc(f.id)}"><span class="frame-num">${String(i + 1).padStart(2, "0")}</span><span>${esc(f.zh)}<small>${esc(f.en)}</small></span></button>`,
      )
      .join("");
    document
      .querySelectorAll("[data-frame]")
      .forEach((b) => (b.onclick = () => chooseFrame(b.dataset.frame)));
    $("community-frame").insertAdjacentHTML(
      "beforeend",
      state.catalog.frameworks
        .map((f) => `<option value="${esc(f.id)}">${esc(f.zh)}</option>`)
        .join(""),
    );
    chooseFrame("sour");
    if (access && refresh) {
      await api("session", { access_token: access, refresh_token: refresh });
      notify("邮箱链接已验证。");
    } else if (fragment.get("error"))
      notify("邮箱链接已失效，请重新发送。", true);
    await refreshAccount();
    if (access && refresh && recovery) showAuth("password");
  } catch (err) {
    notify(err.message, true);
    $("result").innerHTML =
      '<div class="empty"><h3>暂时无法连接</h3><p>请检查服务是否启动，然后刷新重试。</p></div>';
  }
}
start();
