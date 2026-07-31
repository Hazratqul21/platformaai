/* ---- Йўриқнома: пул қаерга ёзилса, қаерда кўринади ---- */
PAGES.help = () => {
  setTitle("Йўриқнома", "Пул киритилса — қаерда кўринади");

  const card = (n, title, body) => `
    <div class="glass card mb">
      <h2 class="sec mb" style="display:flex;align-items:center;gap:10px">
        <span style="display:inline-flex;align-items:center;justify-content:center;
          width:26px;height:26px;border-radius:7px;background:var(--pri,#6f74d6);
          color:#fff;font-size:13px;font-weight:700;flex:none">${n}</span>${title}</h2>
      ${body}
    </div>`;

  const warn = txt => `<div style="display:flex;gap:8px;padding:10px 12px;border-radius:9px;
    background:rgba(180,71,42,.10);color:var(--danger,#b4472a);font-size:13.5px;line-height:1.55;margin-top:6px">
    <span>⚠️</span><span>${txt}</span></div>`;
  const ok = txt => `<div style="display:flex;gap:8px;padding:10px 12px;border-radius:9px;
    background:rgba(47,143,91,.12);color:var(--ok,#2f8f5b);font-size:13.5px;line-height:1.55;margin-top:6px">
    <span>✓</span><span>${txt}</span></div>`;

  content.innerHTML = `
  <div class="glass card mb">
    <p class="muted" style="font-size:14px;line-height:1.6;margin:0">
      Тизимда пул 3 хил жойга ёзилади: <b>Касса</b>, <b>Ходимлар</b> (пул бериш),
      <b>Мижозлар</b> (тўлов). Ҳар бири ўз жойида кўринади — автомат бошқасига ўтмайди.
      Қуйида ҳар амал қаерга ёзилиб, қаерда кўринишини кўрсатамиз.</p>
  </div>

  <div class="glass card mb" style="overflow-x:auto">
    <h2 class="sec mb">Тезкор жадвал</h2>
    <table class="tbl" style="min-width:560px">
      <thead><tr>
        <th>Нима қилдингиз</th><th>Қаерга ёзилади</th>
        <th>Кўринади</th><th>КЎРИНМАЙДИ</th></tr></thead>
      <tbody>
        <tr><td><b>Ходимга пул бердим</b></td><td>Ходимлар → 💵 Пул бериш</td>
          <td style="color:var(--ok)">Ходим картаси, Ойлик</td>
          <td style="color:var(--danger)">Кассада йўқ</td></tr>
        <tr><td><b>Сех харажати</b></td><td>Харажатлар → + Янги харажат</td>
          <td style="color:var(--ok)">Харажатлар ва Касса</td><td>—</td></tr>
        <tr><td><b>Мижоздан тўлов</b></td><td>Мижозлар → Деталлари → 💰 Тўлов</td>
          <td style="color:var(--ok)">Мижоз қарзи, Молия</td>
          <td style="color:var(--danger)">Кассада йўқ</td></tr>
        <tr><td><b>Кассага қўлда</b></td><td>Касса → Кирим/Чиқим</td>
          <td style="color:var(--ok)">Фақат Касса</td>
          <td style="color:var(--danger)">Ходим/Мижозда йўқ</td></tr>
      </tbody>
    </table>
  </div>

  ${card('1','Ходимга пул бердингиз',
    `<p class="muted" style="font-size:13.5px;line-height:1.6">«Ходимлар» → <b>💵 Пул бериш</b>.
     Бу сумма <b>ходимнинг картасида</b> ва «Ойлик» ҳисобида кўринади.` +
    warn('Касса журналида кўринмайди — бу хато эмас, тартиб шундай.'))}

  ${card('2','Сех харажати ёздингиз',
    `<p class="muted" style="font-size:13.5px;line-height:1.6">«Харажатлар» → <b>+ Янги харажат</b>.
     Бу битта амал <b>иккита</b> жойга бирдан тушади: Харажатлар рўйхати ва Касса (Чиқим).` +
    ok('Такрор ёзиш шарт эмас — Кассага яна қўлда ёзманг, икки марта чиқим бўлади.'))}

  ${card('3','Мижоздан тўлов қабул қилдингиз',
    `<p class="muted" style="font-size:13.5px;line-height:1.6">«Мижозлар» → мижоз → <b>Деталлари</b> →
     <b>💰 Тўлов қабул қилиш</b>. Бу пул <b>мижознинг қарз-дафтарида</b> кўринади.` +
    warn('Кассада йўқлигини кўриб қўлда яна ёзманг — дубликат (икки марта санаш) бўлади.'))}

  ${card('4','Касса — алоҳида дафтар',
    `<p class="muted" style="font-size:13.5px;line-height:1.6">Касса ўзи алоҳида дафтар.
     Тавсия: <b>ҳар пулни фақат бир жойга ёзинг</b> — ходимга пул Ходимларга, мижоз тўлови
     Мижозларга, сех харажати Харажатларга. Кассага қўлда фақат бошқа ҳаракатларни
     (банкдан нақд олиш, эгасидан кирим) ёзинг.</p>`)}

  <div class="glass card mb">
    <p class="muted" style="font-size:12.5px;margin:0;text-align:center">
      Киритган ҳар амалингиз «<b>Молия → Амаллар тарихи</b>» да вақти билан сақланади — ҳеч нарса йўқолмайди.</p>
  </div>
  `;
};
