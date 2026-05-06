const resultMap = {
  A: {
    title: "願望迷霧型",
    body: "你不是沒有能力，而是願望還不夠清楚。你的大腦像搜尋引擎，如果關鍵字模糊，它就只能回傳雜訊。建議起點：45 天覺醒合約。今天先寫下「我真正想要的是什麼」，不要寫不想要什麼。",
    cta: "開始你的 45 天願望校準 →",
    href: "starter.html"
  },
  B: {
    title: "逆境加戲型",
    body: "你很可能不是被逆境打敗，而是被大腦的詮釋打敗。事情本身是一回事，你腦中加演的劇情是另一回事。建議起點：攝影機思維除錯卡。今天把最煩的一件事改寫成「監視器拍到的事實」。",
    cta: "拿到攝影機除錯卡，今天就練習 →",
    href: "freebie.html"
  },
  C: {
    title: "界線漏電型",
    body: "你把太多人的情緒裝進自己的系統裡。你需要的不是變冷漠，而是建立權限管理。建議起點：心靈 NAS 權限表。今天寫下 3 個讓你耗電的人，標記他們目前擁有什麼權限。",
    cta: "建立你的心靈權限系統 →",
    href: "offer.html"
  },
  D: {
    title: "大腦 RAM 爆滿型",
    body: "你不是懶，也不是沒有夢想。你只是把太多資訊、任務、願望、焦慮都塞在腦中，導致系統發燙。建議起點：Life OS 一頁儀表板。今天先把腦中所有待辦倒出來，分成今天、這週、以後。",
    cta: "馬上清空你的大腦分頁 →",
    href: "freebie.html"
  }
};

const form = document.querySelector("#quiz-form");
const result = document.querySelector("#result");
const resultTitle = document.querySelector("#result-title");
const resultBody = document.querySelector("#result-body");
const resultPrimaryCta = document.querySelector("#result-primary-cta");

if (form) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const data = new FormData(form);
    const scores = { A: 0, B: 0, C: 0, D: 0 };

    for (const value of data.values()) {
      scores[value] += 1;
    }

    const winner = Object.entries(scores).sort((a, b) => b[1] - a[1])[0][0];
    const payload = resultMap[winner];

    resultTitle.textContent = `${winner} 最多｜${payload.title}`;
    resultBody.textContent = payload.body;
    resultPrimaryCta.textContent = payload.cta;
    resultPrimaryCta.href = payload.href;
    result.hidden = false;
    result.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

document.querySelectorAll("[data-email-form]").forEach((emailForm) => {
  emailForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const note = emailForm.querySelector("[data-form-note]");
    const input = emailForm.querySelector("input[type='email']");

    note.textContent = `已收到 ${input.value}。正式串接 Tally 或 Google Form 後，這裡會自動寄出工具包。`;
    emailForm.reset();
  });
});
