/* ================= DIZAYN KARKASI =================
 * Loyihaning vizual tilini bitta sahifada ko'rsatadi.
 * Bu yerda RANG YO'Q, SOYA YO'Q — hamma ko'rinish `liquid-glass.css`
 * dan keladi. Shu sababli karkas «yolg'on gapira olmaydi»: ilovada
 * qanday bo'lsa, shu yerda ham shunday.
 */
const H = (id, html) => { const e = document.getElementById(id); if (e) e.innerHTML = html; };

/* ---------- fon varianti ---------- */
const FONLAR = [['', 'To\'r'], ['fon-nuqta', 'Nuqta'], ['fon-toza', 'Toza']];
H('fonTanla', FONLAR.map(([k, n], i) =>
  `<button class="btn sm ${i === 0 ? 'pri' : ''}" data-fon="${k}">${n}</button>`).join(''));
document.getElementById('fonTanla').onclick = e => {
  const b = e.target.closest('[data-fon]'); if (!b) return;
  document.body.className = b.dataset.fon;
  [...e.currentTarget.children].forEach(x => x.classList.toggle('pri', x === b));
};

/* ---------- material darajalari ---------- */
const DARAJA = [
  ['L1', 'Fon', 'Ish maydoni. Eng shaffof, eng kam soya.'],
  ['L2', 'Kartochka', 'Kontent turadigan asosiy yuza.'],
  ['L3', 'Suzuvchi', 'Boshqaruv elementlari — chip, userchip.'],
  ['L4', 'Modal', 'Diqqatni to\'liq oladi. Kuchli blur.'],
  ['L5', 'AI paneli', 'Eng balandda. Alohida material hissi.'],
];
H('material', DARAJA.map(([k, n, i]) => `
  <div class="glass card krk-quti">
    <p class="krk-yorliq">${k}</p>
    <b style="display:block;font-size:15px;margin-bottom:5px">${n}</b>
    <span class="muted" style="font-size:12.5px;line-height:1.5">${i}</span>
  </div>`).join(''));

/* ---------- tipografika ---------- */
H('tipografika', `
  <div class="page-title" style="margin-bottom:2px">Sahifa sarlavhasi</div>
  <div class="page-sub" style="margin-bottom:18px">Sahifa izohi — nima qilinishini aytadi</div>
  <h2 class="sec">Bo'lim sarlavhasi</h2>
  <div class="sec-sub" style="margin-bottom:16px">Bo'lim izohi</div>
  <p style="font-size:13.5px;line-height:1.65;max-width:62ch;margin:0 0 16px">
    Oddiy matn. O'lchami o'qish uchun tanlangan, bezak uchun emas —
    ekranda uzoq turiladigan qatorlar shu vazndan yashaydi.</p>
  <div class="kpi" style="padding:0;background:none;border:none;box-shadow:none">
    <div class="val">240 800 000</div>
    <div class="lab">Raqam — tabular, qalin, yuqori kontrast</div>
  </div>
  <div class="muted" style="font-size:12px;margin-top:14px">Ikkinchi darajali matn</div>`);

/* ---------- rang ---------- */
const RANG = [
  ['#5B5BEF', 'Primary', 'asosiy amal'],
  ['#7B7CF6', 'Primary light', 'gradient yuqorisi'],
  ['#C9F05A', 'Lime', 'muvaffaqiyat · AI'],
  ['#E5484D', 'Red', 'xato · chiqim'],
  ['#17182B', 'Ink', 'asosiy matn'],
  ['#6D708C', 'Ink 2', 'ikkilamchi matn'],
];
H('ranglar', RANG.map(([c, n, i]) => `
  <div>
    <div style="height:56px;border-radius:14px;background:${c};
      border:1px solid rgba(23,24,43,.08);margin-bottom:8px"></div>
    <b style="font-size:12.5px">${n}</b>
    <div class="muted" style="font-size:11px">${i} · ${c}</div>
  </div>`).join(''));

/* ---------- ikonkalar ---------- */
H('ikonlar', Object.keys(I).map(k =>
  `<span title="${k}" style="display:grid;place-items:center;width:42px;height:42px;
     border-radius:12px;color:var(--lg-primary);background:rgba(91,91,239,.07);
     border:1px solid rgba(91,91,239,.14)">${icon(k, 20)}</span>`).join(''));

/* ---------- tugmalar ---------- */
const TUGMA = [
  ['btn pri', 'Asosiy', 'check'], ['btn', 'Ikkilamchi', ''],
  ['btn dngr', 'Xavfli', 'x'], ['btn ok', 'Muvaffaqiyat', 'tick'],
  ['btn ghost', 'Shaffof', ''],
];
const tugmalar = (kichik) => TUGMA.map(([c, n, ik]) =>
  `<button class="${c}${kichik ? ' sm' : ''}">${ik ? icon(ik, kichik ? 13 : 15) + ' ' : ''}${n}</button>`).join('')
  + `<button class="btn${kichik ? ' sm' : ''}" disabled style="opacity:.45;cursor:not-allowed">O'chirilgan</button>`;
H('tugma1', tugmalar(false));
H('tugma2', tugmalar(true));

/* ---------- maydonlar ---------- */
H('maydonlar', `
  <div><label class="fl">Oddiy matn</label>
    <input class="fld" placeholder="masalan: Rustam aka"/></div>
  <div><label class="fl">Qidiruv</label>
    <input class="fld qidir" placeholder="Nomi yoki telefon bo'yicha…"/></div>
  <div><label class="fl">Tanlov</label>
    <select class="fld"><option>Barcha firmalar</option><option>THE BILLIARD</option></select></div>
  <div><label class="fl">Sana</label>
    <input class="fld" type="date" value="2026-08-28"/></div>
  <div style="grid-column:1/-1"><label class="fl">Uzun matn</label>
    <textarea class="fld" rows="3" placeholder="Izoh…"></textarea></div>`);

/* ---------- chip va tag ---------- */
H('chiplar', ['Ҳаммаси', 'THE BILLIARD', 'Gofra Karton', 'Mebel']
  .map((n, i) => `<button class="fchip${i === 0 ? ' on' : ''}">${n}</button>`).join(''));
H('taglar', [['ok', 'Tayyor'], ['warn', 'Kutishda'], ['dn', 'Bekor'],
             ['pri', 'Sexda'], ['mut', 'Arxiv']]
  .map(([c, n]) => `<span class="tag ${c}">${n}</span>`).join(' '));

/* ---------- KPI ---------- */
H('kpilar',
  kpi('up', 'Жами кирим', '3.2 mln сўм', '+12%', 'up') +
  kpi('flag', 'Жами чиқим', '240.8 mln сўм', '', 'dn') +
  kpi('wallet', 'Баланс', '-237.6 mln сўм', 'минус', 'dn'));

/* ---------- jadval ---------- */
const QATOR = [['асвежител', 'Зарплата', '−800 000'], ['Програма', 'Зарплата', '−1 900 000'],
               ['Бар кофе', 'товар', '−1 200 000'], ['Рахим', '', '−100 000']];
H('jadval', `
  <div class="between" style="font-size:11px;color:var(--lg-text-3);padding:6px 2px;
    border-bottom:1px solid var(--hair)"><b>2026-08-21</b><span>−4.0 mln</span></div>
  ${QATOR.map(([w, n, a]) => `
  <div class="between" style="padding:9px 2px;border-bottom:1px solid var(--hair);gap:8px">
    <span style="flex:1"><b style="font-size:13px">${w}</b>
      <span class="tag mut" style="font-size:9px;padding:1px 6px">THE BILLIARD</span>
      ${n ? `<div class="muted" style="font-size:10.5px">${n}</div>` : ''}</span>
    <b style="color:var(--danger);font-variant-numeric:tabular-nums;white-space:nowrap">${a} сўм</b>
    <button class="btn sm ghost">${icon('x', 13)}</button>
  </div>`).join('')}`);

/* ---------- holatlar ---------- */
H('holatlar', `
  <div class="glass card krk-quti" style="text-align:center;padding:32px 18px">
    <div class="bosh-belgi">${icon('box', 30)}</div>
    <b style="display:block;margin:6px 0">Ombor hali bo'sh</b>
    <div class="muted" style="font-size:12px">Birinchi materialni qo'shing</div>
  </div>
  <div class="glass card krk-quti" style="text-align:center;padding:32px 18px">
    <div class="bosh-belgi">${icon('clock', 30)}</div>
    <b style="display:block;margin:6px 0">Yuklanmoqda…</b>
    <div class="muted" style="font-size:12px">Ma'lumot olinmoqda</div>
  </div>
  <div class="glass card krk-quti" style="text-align:center;padding:32px 18px">
    <div class="bosh-belgi" style="color:var(--danger);background:rgba(229,72,77,.08);
      border-color:rgba(229,72,77,.18)">${icon('alertic', 30)}</div>
    <b style="display:block;margin:6px 0">Bog'lanib bo'lmadi</b>
    <div class="muted" style="font-size:12px">Internetni tekshirib qayta urining</div>
  </div>`);

/* ---------- suzuvchi yuzalar ---------- */
H('suzuvchi', `
  <button class="btn pri" id="krkModal">Modal oynani ko'rish</button>
  <button class="btn" data-toast="o">Muvaffaqiyat</button>
  <button class="btn" data-toast="w">Ogohlantirish</button>
  <button class="btn" data-toast="d">Xato</button>`);
document.getElementById('krkModal').onclick = () => modal(`
  <h2 class="sec mb">${icon('arrowUp', 17)} Чиқим (pul ketdi)</h2>
  <label class="fl">Кимга — нимага</label><input class="fld" placeholder="masalan: Remont"/>
  <div class="grid g2" style="gap:8px;margin-top:10px">
    <div><label class="fl">Сумма</label><input class="fld" value="1 200 000"/></div>
    <div><label class="fl">Валюта</label><select class="fld"><option>сўм</option></select></div>
  </div>
  <div class="row" style="margin-top:18px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="closeModal()">Сақлаш</button></div>`);
document.getElementById('suzuvchi').onclick = e => {
  const b = e.target.closest('[data-toast]'); if (!b) return;
  const k = b.dataset.toast;
  toast(k, k === 'd' ? 'alertic' : 'check',
        k === 'o' ? 'Saqlandi' : k === 'w' ? 'Diqqat' : 'Xatolik',
        k === 'o' ? 'Yozuv kassa jurnaliga tushdi'
        : k === 'w' ? 'Omborda material kam qoldi' : 'Server javob bermadi');
};

/* ---------- motion ---------- */
H('motion', `
  <div class="krk-panjara">
    <div><p class="krk-yorliq">Tez — 180ms</p>
      <span class="muted" style="font-size:12.5px;line-height:1.5">Tugma bosilishi,
        hover, nishon rangi. Ko'z sezmaydigan darajada tez.</span></div>
    <div><p class="krk-yorliq">O'rta — 240ms</p>
      <span class="muted" style="font-size:12.5px;line-height:1.5">Modal ochilishi,
        yon menyu yig'ilishi. Ko'z kuzatib ulguradi.</span></div>
    <div><p class="krk-yorliq">Sekin — 300ms</p>
      <span class="muted" style="font-size:12.5px;line-height:1.5">AI paneli sirg'alishi.
        Katta yuza — sekinroq harakat tabiiy ko'rinadi.</span></div>
  </div>
  <div class="muted" style="font-size:12.5px;line-height:1.6;margin-top:18px;
    padding-top:16px;border-top:1px solid rgba(23,24,43,.08)">
    Egri chiziq bitta: <code>cubic-bezier(.22,1,.36,1)</code> — ease-out,
    prujina hissi bilan. Kirish harakatida <code>ease-in</code> ishlatilmaydi.
    Layout xossalari (<code>width</code>, <code>height</code>, <code>margin</code>)
    animatsiya qilinmaydi — faqat <code>transform</code> va <code>opacity</code>.
    Tizimda «harakatni kamaytirish» yoqilgan bo'lsa, ko'chish va masshtab
    o'chadi, rang va shaffoflik qoladi.</div>`);
