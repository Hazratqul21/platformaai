/* ---- Smeta kalkulyatori — maydonlar PROFILDAN ----
 *
 * Ilgari bu sahifa kartonga qotirilgan edi (узунлик/кенглик/баландлик,
 * «Қоғоз маркаси», «3 слой»). Endi maydonlarni `soha.js` profildan
 * chizadi va narxni `POST /api/orders/smeta` hisoblaydi — u karton
 * formulasini ham, retseptni ham, qo'lda narxni ham biladi.
 */
PAGES.calc = async () => {
  const [cs, soha] = await Promise.all([api('/api/clients'), sohaYukla(true)]);
  window._clients = cs;
  const birlik = esc(sohaBirlik());
  const qadam = soha.kasrli ? ' step="any"' : '';

  return `<div class="split">
  <div class="glass card">
    <h2 class="sec">Янги буюртма</h2>
    <div class="sec-sub">${esc(soha.nom)} — майдонлар шу соҳа профилидан олинган</div>
    <div style="margin-bottom:8px">
      <label class="fl">Маҳсулот номи (ихтиёрий)</label>
      <input class="fld" id="q_product_name" placeholder="мижоз тилидаги ном"/>
    </div>
    ${sohaFormaHtml('q_')}
    <div style="margin-top:8px">
      <label class="fl">Миқдор, ${birlik}</label>
      <input class="fld" id="q_qty" type="number"${qadam} value="${soha.kasrli ? 1 : 1000}"/>
    </div>
    <label class="fl">Мижоз (номи ёки телефони бўйича қидиринг)</label>
    <input class="fld" id="q_client_search" list="clientList" placeholder="🔍 масалан: Хос ёки 90 123..."
      oninput="clientTanlandi()" autocomplete="off"/>
    <datalist id="clientList">${cs.map(c => `<option value="${esc(c.company)}${c.phone ? ' · ' + esc(c.phone) : ''}">`).join('')}</datalist>
    <input type="hidden" id="q_client"/>
    <div id="q_client_orders"></div>
    <label class="fl">Қўшимча изоҳ (ихтиёрий)</label>
    <input class="fld" id="q_note" placeholder="масалан: шошилинч"/>
    <label class="fl">Маҳсулот расмлари (ихтиёрий, бир нечта)</label>
    <div class="glass card" style="padding:10px">
      <input type="file" id="q_photo_file" accept="image/*" capture="environment" multiple
        style="display:none" onchange="calcRasmTanlandi(this)"/>
      <div id="q_photo_grid" class="row" style="flex-wrap:wrap;gap:6px;margin-bottom:6px"></div>
      <div class="row" style="gap:6px">
        <button class="btn sm pri" style="flex:1;justify-content:center"
          onclick="document.getElementById('q_photo_file').click()">📷 Расм қўшиш</button>
      </div>
      <div class="muted" style="font-size:10.5px;margin-top:5px">
        Бир нечта расм қўшса бўлади. Телефонда камера очилади.</div>
    </div>
    <button class="btn pri" style="width:100%;justify-content:center;margin-top:16px"
      onclick="runQuote()">${icon('calc', 15)} Ҳисоблаш</button>
  </div>
  <div id="quoteRes"><div class="glass card muted" style="text-align:center;padding:40px 20px">
    Майдонларни тўлдиринг ва «Ҳисоблаш» тугмасини босинг</div></div>
  </div>`;
};

/* ---- Mijozni qidirib tanlash + oldingi buyurtmalar (povtor) ---- */
async function clientTanlandi() {
  const val = f('q_client_search').trim();
  const nom = val.split(' · ')[0].trim().toLowerCase();
  const c = (window._clients || []).find(x => x.company.toLowerCase() === nom)
        || (window._clients || []).find(x => x.company.toLowerCase().includes(nom) && nom.length > 2);
  const box = _id('q_client_orders');
  if (!c) { _id('q_client').value = ''; if (box) box.innerHTML = ''; return; }
  _id('q_client').value = c.id;
  if (!box) return;
  box.innerHTML = '<div class="muted" style="font-size:11px;padding:6px">Олдинги буюртмалар юкланмоқда…</div>';
  try {
    const orders = await api('/api/orders?firm=');
    const mine = orders.filter(o => o.client_id === c.id).slice(0, 6);
    if (!mine.length) {
      box.innerHTML = `<div class="muted" style="font-size:11px;padding:4px">${esc(c.company)} — биринчи буюртма</div>`;
      return;
    }
    box.innerHTML = `<div class="glass card" style="padding:8px;margin:6px 0;background:var(--hair)">
      <div class="muted" style="font-size:10.5px;margin-bottom:4px">🔁 ${esc(c.company)}нинг олдинги буюртмалари — босса, майдонлар тўлади</div>
      ${mine.map(o => `<div class="between" style="font-size:11.5px;padding:4px 0;border-top:1px solid var(--hair);cursor:pointer"
        onclick='povtorTanla(${JSON.stringify(o).replace(/'/g, "&#39;")})'>
        <span><b>#${o.id}</b> ${esc(o.product_name || o.tur)} <span class="muted">${esc(o.size)}</span></span>
        <span>${new Intl.NumberFormat('ru-RU').format(o.qty)} ${esc(o.qty_birlik || '')} · ${mshort(o.total)}</span></div>`).join('')}
    </div>`;
  } catch (e) { box.innerHTML = ''; }
}

/** Eski buyurtmani takrorlash — `attributes` dan, ya'ni har sohada ishlaydi. */
function povtorTanla(o) {
  if (_id('q_product_name')) _id('q_product_name').value = o.product_name || '';
  const at = o.attributes || {};
  for (const md of sohaMaydonlar()) {
    const el = _id('q_' + md.kalit);
    if (!el || at[md.kalit] === undefined || at[md.kalit] === null) continue;
    el.value = md.tur === 'mantiq' ? (at[md.kalit] ? '1' : '0') : at[md.kalit];
  }
  if (_id('q_qty')) _id('q_qty').value = o.qty || '';
  toast('o', 'check', 'Олдинги буюртмадан олинди', 'Ўзгартириб «Ҳисоблаш»ни босинг');
}

let LASTQ = null;
let CALC_RASMLAR = [];   // buyurtma yaratilgunga qadar rasmlar shu yerda (data URL)

async function calcRasmTanlandi(inp) {
  const files = [...(inp.files || [])];
  if (!files.length) return;
  for (const file of files) {
    if (CALC_RASMLAR.length >= 10) { toast('w', 'alertic', 'Кўп', 'Кўпи билан 10 та расм'); break; }
    try { CALC_RASMLAR.push(await rasmniKichiklashtir(file)); }
    catch (e) { toast('d', 'alertic', 'Расм юкланмади', e.message); }
  }
  inp.value = '';
  calcRasmGrid();
}
function calcRasmGrid() {
  const g = document.getElementById('q_photo_grid'); if (!g) return;
  g.innerHTML = CALC_RASMLAR.map((src, i) => `<div style="position:relative">
    <img src="${src}" style="width:72px;height:72px;object-fit:cover;border-radius:8px"/>
    <span onclick="calcRasmOchir(${i})" style="position:absolute;top:-6px;right:-6px;background:var(--danger);color:#fff;width:20px;height:20px;border-radius:50%;display:grid;place-items:center;cursor:pointer;font-size:12px">✕</span>
    </div>`).join('')
    + (CALC_RASMLAR.length ? `<div class="muted" style="font-size:10.5px;width:100%;margin-top:2px">✅ ${CALC_RASMLAR.length} та расм тайёр</div>` : '');
}
function calcRasmOchir(i) { CALC_RASMLAR.splice(i, 1); calcRasmGrid(); }

async function runQuote() {
  const bosh = sohaTekshir('q_');
  if (bosh) return toast('w', 'alertic', 'Майдон тўлдирилмаган', bosh);
  const qty = +f('q_qty') || 0;
  if (!(qty > 0)) return toast('w', 'alertic', 'Миқдор йўқ', 'Нечта эканини ёзинг');

  const body = {
    product_name: f('q_product_name'),
    attributes: sohaFormaOl('q_'),
    qty,
    client_id: +f('q_client') || null,
    note: f('q_note'),
  };
  try {
    const q = await post('/api/orders/smeta', body);
    LASTQ = { ...body, quote: q };
    document.getElementById('quoteRes').innerHTML = smetaHtml(q, body);
  } catch (e) { toast('d', 'alertic', 'Хатолик', e.message); }
}

/** Smeta natijasi — narx usuliga qarab uch xil ko'rinish. */
function smetaHtml(q, body) {
  const yarata = body.client_id && ['Rahbar', 'Menejer'].includes(ME.role);
  const birlik = esc(sohaBirlik());
  const ogoh = []
    .concat(q.ogohlantirish || [])
    .concat(q.narx_ogoh ? [q.narx_ogoh] : [])
    .concat(q.formula_ogoh ? [q.formula_ogoh] : []);

  // «Qo'lda» — formula yo'q: tannarx ham, taklif narxi ham yo'q.
  // Bu holatda narxni odam yozadi, tizim faqat jamini ko'rsatadi.
  if (q.usul === 'qolda') {
    return `<div class="glass card">
      <h2 class="sec mb">Смета</h2>
      ${alertBox('w', 'alertic', 'Бу соҳада формула йўқ',
        'Нархни ўзингиз ёзасиз. Хомашё ечилса — зарарига сотилмаётганини тизим текширади.')}
      ${yarata ? narxBloki(q, body, birlik) : sohaMijozOgoh()}
    </div>`;
  }

  const ichki = `
    <div style="background:rgba(124,127,240,.07);border-radius:12px;padding:12px;margin-bottom:10px">
      <div class="muted" style="font-size:10px;letter-spacing:1px;margin-bottom:6px">ФАҚАТ СИЗГА КЎРИНАДИ — мижозга чиқмайди</div>
      ${(q.materiallar || []).map(mt => `
        <div class="between" style="font-size:12px;padding:2px 0">
          <span class="muted">${esc(mt.material)} · ${new Intl.NumberFormat('ru-RU').format(mt.miqdor)} ${esc(mt.birlik)}</span>
          <b>${money(mt.summa)}</b></div>`).join('')}
      ${q.material_1dona != null ? `<div class="between" style="font-size:12.5px;padding:3px 0;border-top:1px solid var(--hair)">
        <span>Хомашё / ${birlik}</span><b>${money(q.material_1dona)}</b></div>` : ''}
      ${q.ish_haqi_1dona ? `<div class="between" style="font-size:12.5px;padding:3px 0"><span>Иш ҳақи</span><b>${money(q.ish_haqi_1dona)}</b></div>` : ''}
      ${q.qoshimcha_xarajat_1dona ? `<div class="between" style="font-size:12.5px;padding:3px 0"><span>Қўшимча харажат</span><b>${money(q.qoshimcha_xarajat_1dona)}</b></div>` : ''}
      ${q.labor ? `<div class="between" style="font-size:12.5px;padding:3px 0"><span>Иш ҳақи / дона</span><b>${money(q.labor)}</b></div>` : ''}
      ${q.printing ? `<div class="between" style="font-size:12.5px;padding:3px 0"><span>Босма</span><b>${money(q.printing)}</b></div>` : ''}
      <div class="between" style="font-size:13px;padding:5px 0;border-top:1px solid var(--hair)">
        <span><b>Таннарх / ${birlik}</b></span><b>${money(q.unit_cost)}</b></div>
      <div class="between" style="font-size:12.5px;padding:3px 0"><span>Устама</span>
        <b style="color:var(--ok)">${q.ustama_foiz ?? q.margin_percent}%</b></div>
    </div>`;

  const jami = q.jami_qqs_bilan ?? q.total;
  return `<div class="glass card">
    <h2 class="sec mb">Смета натижаси</h2>
    ${q.need_m2_total != null ? `
      <div class="between" style="padding:5px 0;font-size:13px"><span class="muted">Жами керак</span><b>${q.need_m2_total.toFixed(1)} м²</b></div>
      <div class="between" style="padding:5px 0;font-size:13px"><span class="muted">Омборда бор</span>
        <b style="color:${q.enough_material ? 'var(--ok)' : 'var(--danger)'}">${q.stock_m2.toFixed(1)} м² ${q.enough_material ? '✓' : '— ЕТМАЙДИ!'}</b></div>` : ''}
    ${ogoh.map(x => alertBox('d', 'alertic', 'ДИҚҚАТ', esc(x))).join('')}
    ${ichki}
    <div class="between" style="font-size:15px;padding:6px 0"><span>Таклиф нархи / ${birlik}</span><b>${money(q.unit_price)}</b></div>
    ${q.qqs ? `<div class="between muted" style="font-size:12px;padding:2px 0">
      <span>ҚҚС ${q.qqs_stavka}%</span><span>${money(q.qqs)}</span></div>` : ''}
    <div class="between" style="font-size:19px;font-weight:700;padding:8px 0;border-top:1px solid var(--hair)">
      <span>ЖАМИ (${new Intl.NumberFormat('ru-RU').format(body.qty)} ${birlik})</span>
      <span style="color:var(--primary-deep)">${money(jami)}</span></div>
    ${yarata ? narxBloki(q, body, birlik) : sohaMijozOgoh()}
  </div>`;
}

function sohaMijozOgoh() {
  return '<div class="muted" style="font-size:11.5px;margin-top:8px">Буюртма яратиш учун мижозни танланг</div>';
}

function narxBloki(q, body, birlik) {
  return `
    <label class="fl">Якуний нарх / ${birlik} (келишилган бўлса ўзгартиринг)</label>
    <input class="fld" id="q_final" type="number" step="any" value="${q.unit_price ?? ''}"/>
    <div class="grid g3" style="gap:8px;margin-top:8px">
      <div><label class="fl">Олдиндан тўлов %</label><input class="fld" id="q_prepaid" type="number" value="30"/></div>
      <div><label class="fl">Тайёрлаш муддати</label><input class="fld" id="q_due" type="number" value="15" title="Кун ҳисобида"/></div>
      <div><label class="fl">Тўлов муддати</label><input class="fld" id="q_pay_due" type="number" value="15" title="Кун ҳисобида"/></div>
    </div>
    <button class="btn pri" style="width:100%;justify-content:center;margin-top:12px"
      onclick="createOrder()">${icon('cart', 15)} Буюртмани яратиш</button>`;
}

async function createOrder() {
  const narx = +f('q_final') || null;
  if (!narx) return toast('w', 'alertic', 'Нарх йўқ', 'Якуний нархни ёзинг');
  try {
    const o = await post('/api/orders', {
      product_name: LASTQ.product_name, attributes: LASTQ.attributes,
      qty: LASTQ.qty, client_id: LASTQ.client_id, note: f('q_note'),
      unit_price: narx,
      prepaid_percent: +f('q_prepaid') || 0,
      due_days: +f('q_due') || 15, payment_due_days: +f('q_pay_due') || 15,
    });
    let rasmXato = '';
    for (const src of CALC_RASMLAR) {
      try { await post('/api/orders/' + o.id + '/photo', { data: src }); }
      catch (e) { rasmXato = ' · баъзи расм сақланмади'; }
    }
    CALC_RASMLAR = [];
    toast(rasmXato ? 'w' : 'o', 'check', `Буюртма №${o.id} яратилди`,
      `${money(o.total)}${o.credit_warning ? ' · ДИҚҚАТ: лимит ошди!' : ''}${rasmXato}`);
    go('orders');
  } catch (e) { toast('d', 'alertic', 'Блокланди', e.message); }
}
