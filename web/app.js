function fmtTime(ts){
  if(!ts) return "未知";
  const d = new Date(ts * 1000);
  return d.toLocaleString("zh-TW");
}

async function loadMeta(){
  const meta = document.getElementById("meta");
  if(!meta) return;
  try{
    const res = await fetch("/api/meta");
    const data = await res.json();
    if(data.ok){
      meta.textContent = `資料快取更新時間：${fmtTime(data.updated_at)}（來源：教育局學區查詢頁）`;
    }else{
      meta.textContent = "無法讀取狀態";
    }
  }catch(e){
    meta.textContent = "無法讀取狀態";
  }
}

async function query(){
  const out = document.getElementById("out");
  const district = document.getElementById("district").value.trim();
  const li = document.getElementById("li").value.trim();
  const lin = document.getElementById("lin").value.trim();

  out.textContent = "查詢中…";

  const url = `/api/query?district=${encodeURIComponent(district)}&li=${encodeURIComponent(li)}&lin=${encodeURIComponent(lin)}`;
  const res = await fetch(url);
  const data = await res.json();

  if(!data.ok){
    out.textContent = `❌ ${data.error}`;
    return;
  }

  if(data.status === "ok"){
    out.textContent = `✅ 對應國中：${data.schools[0]}`;
    return;
  }

  if(data.status === "overlap"){
    out.textContent = `⚠️ 可能為共同學區/重疊（請以官方原文再確認）：\n- ${data.schools.join("\n- ")}`;
    return;
  }

  if(data.status === "manual"){
    out.textContent =
      `🟡 需人工判定\n` +
      `官方資料含道路或文字界線，僅輸入里+鄰無法百分百判定。\n\n` +
      `候選/原文（節錄）：\n` +
      data.candidates.map(c => `- ${c.school}｜${c.raw}`).join("\n");
    return;
  }

  out.textContent = `❌ 查無：${data.message || "官方資料查無對應"}`;
}

async function update(){
  const out = document.getElementById("out");
  out.textContent = "更新中…（抓取教育局官方頁面）";
  const res = await fetch("/api/update");
  const data = await res.json();
  if(data.ok){
    out.textContent = `✅ 更新完成：共 ${data.rules} 筆規則（限制：北區/北屯/西區/西屯/南屯）`;
    loadMeta();
  }else{
    out.textContent = "❌ 更新失敗";
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("btn");
  const upd = document.getElementById("upd");
  if(btn) btn.addEventListener("click", query);
  if(upd) upd.addEventListener("click", update);
  loadMeta();
});
