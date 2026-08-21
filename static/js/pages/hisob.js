/* ================= BUXGALTERIYA (Bosh kitob) ========================
   Balans, aylanma qaydnoma, foyda-zarar, provodkalar, hisoblar rejasi,
   provodka qoidalari, davrlar.

   ⚠️ HALOL KO'RSATISH: GL hozircha eski hisob-kitob bilan PARALLEL
   ishlaydi. Ekranning boshida shu yozilgan — mijoz «to'liq buxgalteriya
   tayyor» deb o'ylab qolmasin (docs/00-STRATEGIYA.md §0.6).
   ==================================================================== */

const HISOB_TABLAR = [
  ['balans',    'Баланс'],
  ['qaydnoma',  'Айланма қайднома'],
  ['fz',        'Фойда-зарар'],
  ['provodka',  'Проводкалар'],
  ['schetlar',  'Ҳисоблар режаси'],
  ['qoidalar',  'Проводка қоидалари'],
  ['davr',      'Даврлар'],
];

PAGES.hisob = async () => {
  setTitle('Бухгалтерия', 'Бош китоб — икки ёқлама ёзув');
  const tugmalar = HISOB_TABLAR.map(([k, n]) =>
    `<button class="btn set-tab" id="htab_${k}" onclick="hisobTab('${k}')">${n}</button>`
  ).join('');

  setTimeout(() => hisobTab(window._hisobTab || 'balans'), 0);

  return `
  <div class="glass card mb" style="border-color:rgba(183,121,31,.3)">
    <div style="font-size:12.5px;line-height:1.6">
      <b>Синов босқичи.</b> Бош китоб мавжуд ҳисоб-китоб билан
      <b>параллел</b> ишлайди — рақамлар солиштирилмоқда. Расмий ҳисобот
      топшириш учун бухгалтер тасдиғи керак.
    </div>
  </div>
  <div class="tabs mb">${tugmalar}</div>
  <div id="hisobBody"><div class="muted">Юкланмоқда…</div></div>`;
};

async function hisobTab(kalit) {
  window._hisobTab = kalit;
  document.querySelectorAll('.set-tab').forEach(el => el.classList.remove('pri'));
  const t = document.getElementById('htab_' + kalit);
  if (t) t.classList.add('pri');
  const box = document.getElementById('hisobBody');
  if (!box) return;
  box.innerHTML = '<div class="muted">Юкланмоқда…</div>';
  try {
    box.innerHTML = await ({
      balans: hisobBalans, qaydnoma: hisobQaydnoma, fz: hisobFZ,
      provodka: hisobProvodka, schetlar: hisobSchetlar,
      qoidalar: hisobQoidalar, davr: hisobDavr,
    }[kalit])();
  } catch (e) {
    box.innerHTML = `<div class="glass card"><div class="muted">Хатолик: ${esc(e.message)}</div></div>`;
  }
}

const som = n => new Intl.NumberFormat('ru-RU').format(Math.round(n || 0));

/* ---------- BALANS ---------- */
async function hisobBalans() {
  const b = await api('/api/hisob/balans');
  // Bo'sh balans (provodka yo'q) — chalkash 0 lar o'rniga tushuntirish.
  // Ko'chirilgan tarixiy ma'lumotda provodka bo'lmaydi: GL faqat YANGI
  // amallardan boshlanadi.
  if(!b.aktiv.length && !b.passiv.length){
    return `<div class="glass card" style="text-align:center;padding:40px 24px">
      <div style="font-size:34px;margin-bottom:12px">📖</div>
      <h2 class="sec" style="margin-bottom:8px">Бош китоб ҳали бўш</h2>
      <div class="muted" style="font-size:13px;line-height:1.65;max-width:520px;margin:0 auto">
        Баланс <b>янги амаллардан</b> тўлади: буюртма топширилганда,
        тўлов қабул қилинганда ва харид қилинганда автомат проводка ёзилади.<br>
        Эски маълумот (қарзлар, касса, омбор) баланста кўриниши учун
        <b>бошланғич қолдиқ</b> киритилади — тизим ҳозирги ҳолатдан
        (мижоз қарзи, етказувчи қарзи, касса, омбор) автомат ҳисоблаб беради.</div>
      <button class="btn pri" style="margin-top:18px" onclick="boshlangichSehrgar()">
        Бошланғич қолдиқ киритиш</button>
    </div>`;
  }
  const qator = x => `<tr><td class="muted" style="width:64px">${x.kod}</td>
    <td>${esc(x.nom)}</td><td style="text-align:right"><b>${som(x.qoldiq)}</b></td></tr>`;
  const bos = b.yigildimi
    ? `<span class="tag ok">Баланс йиғилди</span>`
    : `<span class="tag dn">Баланс йиғилмади — фарқ ${som(b.farq)}</span>`;

  return `
  <div class="glass card mb">
    <div class="between"><h2 class="sec">Баланс · ${b.sana}</h2>${bos}</div>
    <div class="sec-sub">Актив — корхонада нима бор. Пассив — у кимнинг пулига олинган.
      Иккаласи ТЕНГ бўлиши шарт.</div>
  </div>
  <div class="split teng mb">
    <div class="glass card">
      <h3 class="sec">АКТИВ</h3>
      <table class="oralsin"><tbody>${b.aktiv.map(qator).join('') ||
        '<tr><td class="muted">ёзув йўқ</td></tr>'}</tbody>
        <tfoot><tr><td colspan="2"><b>ЖАМИ</b></td>
        <td style="text-align:right"><b>${som(b.aktiv_jami)}</b></td></tr></tfoot></table>
    </div>
    <div class="glass card">
      <h3 class="sec">ПАССИВ</h3>
      <table class="oralsin"><tbody>${b.passiv.map(qator).join('') ||
        '<tr><td class="muted">ёзув йўқ</td></tr>'}</tbody>
        <tfoot><tr><td colspan="2"><b>ЖАМИ</b></td>
        <td style="text-align:right"><b>${som(b.passiv_jami)}</b></td></tr></tfoot></table>
    </div>
  </div>`;
}

/* ---------- AYLANMA QAYDNOMA ---------- */
async function hisobQaydnoma() {
  const q = await api('/api/hisob/qaydnoma');
  return `
  <div class="glass card">
    <h2 class="sec">Айланма қайднома</h2>
    <div class="sec-sub">Ҳар счёт бўйича дебет/кредит оборот ва қолдиқ</div>
    <table><thead><tr><th>Счёт</th><th>Номи</th><th style="text-align:right">Дебет</th>
      <th style="text-align:right">Кредит</th><th style="text-align:right">Қолдиқ</th></tr></thead>
    <tbody>${q.qatorlar.map(x => `<tr>
      <td class="muted">${x.kod}</td><td>${esc(x.nom)}</td>
      <td style="text-align:right">${som(x.debet)}</td>
      <td style="text-align:right">${som(x.kredit)}</td>
      <td style="text-align:right"><b>${som(x.qoldiq)}</b></td></tr>`).join('') ||
      '<tr><td colspan="5" class="muted">Ҳали ҳаракат йўқ</td></tr>'}</tbody>
    <tfoot><tr><td colspan="2"><b>ЖАМИ</b></td>
      <td style="text-align:right"><b>${som(q.jami_debet)}</b></td>
      <td style="text-align:right"><b>${som(q.jami_kredit)}</b></td><td></td></tr></tfoot></table>
  </div>`;
}

/* ---------- FOYDA-ZARAR ---------- */
async function hisobFZ() {
  const f = await api('/api/hisob/foyda-zarar');
  const musbat = f.foyda >= 0;
  return `
  <div class="grid g3 mb">
    ${kpi('up', 'Даромад', som(f.daromad) + ' сўм', '', 'up')}
    ${kpi('dn', 'Харажат', som(f.xarajat) + ' сўм', '', 'dn')}
    ${kpi('wallet', musbat ? 'Фойда' : 'Зарар', som(Math.abs(f.foyda)) + ' сўм',
      musbat ? 'фойда' : 'зарар', musbat ? 'up' : 'dn')}
  </div>
  <div class="glass card">
    <h2 class="sec">Тафсилот — 9-синф счётлари</h2>
    <table><thead><tr><th>Счёт</th><th>Номи</th><th>Тур</th>
      <th style="text-align:right">Сумма</th></tr></thead>
    <tbody>${f.tafsilot.map(x => `<tr><td class="muted">${x.kod}</td>
      <td>${esc(x.nom)}</td>
      <td><span class="tag ${x.tur === 'daromad' ? 'ok' : 'dn'}">${x.tur}</span></td>
      <td style="text-align:right"><b>${som(x.qoldiq)}</b></td></tr>`).join('') ||
      '<tr><td colspan="4" class="muted">Ҳали даромад/харажат йўқ</td></tr>'}</tbody></table>
  </div>`;
}

/* ---------- PROVODKALAR ---------- */
async function hisobProvodka() {
  const p = await api('/api/hisob/provodkalar?nechta=100');
  const satr = x => `
    <div class="glass card mb" style="padding:14px">
      <div class="between">
        <div><b>${esc(x.hodisa)}</b>
          ${x.hujjat ? `<span class="muted" style="font-size:11px"> · ${esc(x.hujjat)}</span>` : ''}
          ${x.storno_id ? '<span class="tag dn">СТОРНО</span>' : ''}
        </div>
        <div class="muted" style="font-size:11.5px">${x.sana} · ${esc(x.kim || '—')}</div>
      </div>
      ${x.izoh ? `<div class="muted" style="font-size:12px;margin-top:2px">${esc(x.izoh)}</div>` : ''}
      <table style="margin-top:8px"><tbody>
        ${x.qatorlar.map(q => `<tr>
          <td style="width:80px"><span class="tag">Дт ${q.debet}</span></td>
          <td style="width:80px"><span class="tag">Кт ${q.kredit}</span></td>
          <td>${esc(q.izoh || '')}</td>
          <td style="text-align:right"><b>${som(q.summa)}</b></td></tr>`).join('')}
      </tbody></table>
      ${x.storno_id ? '' : `<div class="row" style="justify-content:flex-end;margin-top:6px">
        <button class="btn sm ghost" onclick="hisobStorno(${x.id})">Сторно</button></div>`}
    </div>`;

  return `
  <div class="glass card mb">
    <div class="between"><h2 class="sec">Проводкалар</h2>
      <button class="btn sm pri" onclick="hisobQolda()">+ Қўлда проводка</button></div>
    <div class="sec-sub">Проводка ЎЧИРИЛМАЙДИ — хато бўлса сторно (тескари ёзув) қилинади</div>
  </div>
  ${p.provodkalar.map(satr).join('') ||
    '<div class="glass card"><div class="muted">Ҳали проводка йўқ</div></div>'}`;
}

async function hisobStorno(id) {
  modal(`<h2 class="sec">Проводкани бекор қилиш</h2>
  <div class="muted" style="font-size:12px;margin:4px 0 10px;line-height:1.5">
    Ёзув <b>ўчирилмайди</b> — тескариси ёзилади ва иккаласи ҳам тарихда қолади.
    Бу бухгалтерия қоидаси: аудит изи сақланиши керак.</div>
  <label class="fl">Сабаби (мажбурий)</label>
  <input class="fld" id="st_sabab" placeholder="масалан: мижоз буюртмадан воз кечди"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end;gap:8px">
    <button class="btn ghost" onclick="closeModal()">Бекор</button>
    <button class="btn dngr" onclick="hisobStornoSaqla(${id})">Сторно қилиш</button></div>`);
}

async function hisobStornoSaqla(id) {
  const sabab = f('st_sabab').trim();
  if (!sabab) return toast('w', 'alertic', 'Сабаб', 'Сабабини ёзинг');
  try {
    await api(`/api/hisob/provodka/${id}/storno`, 'POST', { sabab });
    closeModal(); toast('o', 'check', 'Сторно қилинди', '');
    hisobTab('provodka');
  } catch (e) { toast('d', 'alertic', 'Бажарилмади', e.message); }
}

async function hisobQolda() {
  const s = await api('/api/hisob/schetlar');
  const opt = s.schetlar.map(x =>
    `<option value="${x.kod}">${x.kod} — ${esc(x.nom)}</option>`).join('');
  modal(`<h2 class="sec">Қўлда проводка</h2>
  <div class="muted" style="font-size:12px;margin:4px 0 10px">
    Бошланғич қолдиқ, бухгалтер тузатиши учун.</div>
  <label class="fl">Сана</label>
  <input class="fld" id="pv_sana" type="date" value="${new Date().toISOString().slice(0,10)}"/>
  <label class="fl">Изоҳ</label>
  <input class="fld" id="pv_izoh" placeholder="масалан: устав капитали"/>
  <div class="row" style="gap:8px">
    <div style="flex:1"><label class="fl">Дебет</label>
      <select class="fld" id="pv_debet">${opt}</select></div>
    <div style="flex:1"><label class="fl">Кредит</label>
      <select class="fld" id="pv_kredit">${opt}</select></div>
  </div>
  <label class="fl">Сумма</label>
  <input class="fld" id="pv_summa" inputmode="numeric" placeholder="0"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end;gap:8px">
    <button class="btn ghost" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="hisobQoldaSaqla()">Сақлаш</button></div>`);
}

async function hisobQoldaSaqla() {
  const summa = fnum('pv_summa');
  if (summa <= 0) return toast('w', 'alertic', 'Сумма', '0 дан катта бўлсин');
  try {
    await api('/api/hisob/provodka', 'POST', {
      sana: f('pv_sana'), izoh: f('pv_izoh'),
      qatorlar: [{ debet: f('pv_debet'), kredit: f('pv_kredit'), summa }],
    });
    closeModal(); toast('o', 'check', 'Ёзилди', '');
    hisobTab('provodka');
  } catch (e) { toast('d', 'alertic', 'Ёзилмади', e.message); }
}

/* ---------- HISOBLAR REJASI ---------- */
async function hisobSchetlar() {
  const s = await api('/api/hisob/schetlar');
  const sinflar = {};
  s.schetlar.forEach(x => (sinflar[x.sinf] = sinflar[x.sinf] || []).push(x));
  return `
  <div class="glass card mb" style="border-color:rgba(183,121,31,.3)">
    <div style="font-size:12.5px;line-height:1.6">
      <b>${esc(s.asos)}</b><br>
      <span class="muted">${esc(s.ogohlantirish)}</span></div>
  </div>
  ${Object.keys(sinflar).sort().map(k => `
    <div class="glass card mb">
      <h3 class="sec">${k}-синф</h3>
      <table><tbody>${sinflar[k].map(x => `<tr>
        <td class="muted" style="width:64px">${x.kod}</td>
        <td>${esc(x.nom)}</td>
        <td style="width:90px"><span class="tag">${x.tur}</span></td></tr>`).join('')}
      </tbody></table>
    </div>`).join('')}`;
}

/* ---------- PROVODKA QOIDALARI ---------- */
async function hisobQoidalar() {
  const q = await api('/api/hisob/qoidalar');
  return `
  <div class="glass card mb">
    <h2 class="sec">Проводка қоидалари</h2>
    <div class="sec-sub">Ҳар ҳодиса қайси счётларга тушиши. Ўзгартириш мумкин —
      масалан савдо корхонаси 2810 ўрнига 2910 ишлатади.</div>
  </div>
  ${q.qoidalar.map(r => `
    <div class="glass card mb">
      <div class="between"><b>${esc(r.nom)}</b>
        ${r.ozgartirilgan ? '<span class="tag ok">ўзгартирилган</span>' : ''}</div>
      ${r.izoh ? `<div class="muted" style="font-size:12px">${esc(r.izoh)}</div>` : ''}
      <table style="margin-top:8px"><tbody>
        ${r.qatorlar.map(x => `<tr>
          <td style="width:80px"><span class="tag">Дт ${x.debet}</span></td>
          <td style="width:80px"><span class="tag">Кт ${x.kredit}</span></td>
          <td class="muted">${esc(x.izoh || '')}</td>
          <td style="width:110px"><span class="tag">${esc(x.summa || 'summa')}</span></td>
          </tr>`).join('')}
      </tbody></table>
    </div>`).join('')}`;
}

/* ---------- DAVRLAR ---------- */
async function hisobDavr() {
  const d = await api('/api/hisob/davrlar');
  const oy = new Date().toISOString().slice(0, 7);
  return `
  <div class="glass card mb">
    <h2 class="sec">Ҳисобот даврлари</h2>
    <div class="sec-sub">Ёпилган даврга янги ёзув тушмайди — топширилган ҳисобот
      билан база мос қолиши учун</div>
    <div class="row" style="gap:8px;align-items:flex-end;margin-top:10px">
      <div><label class="fl">Ой</label>
        <input class="fld" id="dv_oy" value="${oy}" placeholder="2026-08" style="width:130px"/></div>
      <button class="btn pri" onclick="davrYop()">Ойни ёпиш</button>
    </div>
  </div>
  <div class="glass card">
    <table><thead><tr><th>Ой</th><th>Ким ёпди</th><th>Қачон</th><th></th></tr></thead>
    <tbody>${d.yopilgan.map(x => `<tr><td><b>${x.oy}</b></td>
      <td>${esc(x.kim || '—')}</td>
      <td class="muted">${(x.yopilgan || '').slice(0, 16).replace('T', ' ')}</td>
      <td style="text-align:right">
        <button class="btn sm ghost" onclick="davrOch('${x.oy}')">Қайта очиш</button></td>
      </tr>`).join('') || '<tr><td colspan="4" class="muted">Ёпилган давр йўқ</td></tr>'}
    </tbody></table>
  </div>`;
}

async function davrYop() {
  try {
    await api('/api/hisob/davr/yop', 'POST', { oy: f('dv_oy') });
    toast('o', 'check', 'Давр ёпилди', ''); hisobTab('davr');
  } catch (e) { toast('d', 'alertic', 'Ёпилмади', e.message); }
}

async function davrOch(oy) {
  if (!confirm(`${oy} даврини қайта очасизми? Ҳисобот аллақачон топширилган бўлиши мумкин.`)) return;
  try {
    await api('/api/hisob/davr/och', 'POST', { oy });
    toast('w', 'alertic', 'Давр очилди', 'Аудитга ёзилди'); hisobTab('davr');
  } catch (e) { toast('d', 'alertic', 'Бажарилмади', e.message); }
}


/* ---------- BOSHLANG'ICH QOLDIQ SEHRGARI ---------- */
async function boshlangichSehrgar() {
  let d;
  try { d = await api('/api/hisob/boshlangich-qoldiq'); }
  catch (e) { return toast('d','alertic','Хатолик', e.message); }
  if (d.bor) return toast('w','alertic','Аллақачон','Бошланғич қолдиқ киритилган');

  const qator = (nom, val, akt) => `<tr>
    <td>${nom}</td>
    <td style="text-align:right"><b>${som(val)}</b> сўм</td>
    <td class="muted" style="font-size:11px">${akt}</td></tr>`;

  modal(`<h2 class="sec">Бошланғич қолдиқ</h2>
  <div class="muted" style="font-size:12px;margin:4px 0 12px;line-height:1.55">
    Тизим ҳозирги ҳолатдан ҳисоблади. Тасдиқласангиз, ушбу қолдиқлар
    билан <b>очилиш проводкаси</b> ёзилади ва баланс тўлади.
    Актив ва пассив ТЕНГ бўлади (2-ёқлама ёзув).</div>
  <table><tbody>
    ${qator('Мижозлар қарзи (актив)', d.mijoz_qarzi, 'Дт 4010')}
    ${qator('Касса (актив)', d.kassa, 'Дт 5010')}
    ${qator('Омбор қолдиғи (актив)', d.ombor, 'Дт 1010')}
    ${qator('Етказиб берувчи қарзи (пассив)', d.yetkazuvchi_qarzi, 'Кт 6010')}
    ${d.mijoz_avansi>0 ? qator('Мижоз аванси (пассив)', d.mijoz_avansi, 'Кт 6310') : ''}
  </tbody></table>
  <label class="fl" style="margin-top:10px">Сана</label>
  <input class="fld" id="bq_sana" type="date" value="${new Date().toISOString().slice(0,10)}"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end;gap:8px">
    <button class="btn ghost" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="boshlangichSaqla()">Тасдиқлаш ва ёзиш</button></div>`);
}

async function boshlangichSaqla() {
  try {
    await api('/api/hisob/boshlangich-qoldiq', 'POST', { sana: f('bq_sana') });
    closeModal();
    toast('o','check','Ёзилди','Баланс энди ҳақиқий рақам кўрсатади');
    hisobTab('balans');
  } catch (e) { toast('d','alertic','Ёзилмади', e.message); }
}
