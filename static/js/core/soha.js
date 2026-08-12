/* ============== SOHA — formani PROFILDAN chizish ==============
 *
 * Bungacha buyurtma formasi kartonga qotirilgan edi: «Узунлик, мм»,
 * «Қоғоз маркаси», «3 слой». Nonvoyxona ham aynan shu maydonlarni
 * ko'rardi — ya'ni konstruktor backendda bor edi, ekranda yo'q.
 *
 * Bu yerda maydonlar `GET /api/soha/joriy` javobidan chiziladi. Yangi
 * soha qo'shilganda (yoki AI agent profil yaratganda) frontendga
 * TEGILMAYDI — forma o'zi o'zgaradi.
 *
 * Ishlatilishi:
 *     await sohaYukla();                       // profilni oladi (keshlanadi)
 *     sohaFormaHtml('q_', {ogirlik_g: 600})    // <input>lar
 *     sohaFormaOl('q_')                        // {ogirlik_g: 600, ...}
 */

let SOHA = null;

async function sohaYukla(majburan) {
  if (SOHA && !majburan) return SOHA;
  SOHA = await api('/api/soha/joriy');
  return SOHA;
}

/** Foydalanuvchi to'ldiradigan maydonlar (hisoblanadiganlari emas). */
function sohaMaydonlar() {
  return (SOHA?.maydonlar || []).filter(md => !md.hisoblanadi);
}

function sohaBirlik() { return SOHA?.birlik || 'dona'; }

/** Bitta maydonning <input>i. `id` = prefiks + kalit. */
function sohaMaydonHtml(md, prefix, qiymat) {
  const id = prefix + md.kalit;
  const nom = esc(md.nom) + (md.birlik ? ` <span class="muted">(${esc(md.birlik)})</span>` : '');
  const yulduz = md.majburiy ? ' <span style="color:var(--danger)">*</span>' : '';
  const bor = qiymat !== undefined && qiymat !== null && qiymat !== '';
  const q = bor ? qiymat : (md.standart !== null && md.standart !== undefined ? md.standart : '');

  let kirish;
  if (md.variantlar && md.variantlar.length) {
    // Variantlar ro'yxati bor, lekin YOPIQ emas: mijozda ro'yxatda yo'q
    // tur bo'lishi mumkin (masalan yangi qog'oz markasi). Shuning uchun
    // <select> emas, <input list> — tanlash ham, yozish ham mumkin.
    kirish = `<input class="fld" id="${id}" list="${id}_lst" value="${esc(q)}"/>
      <datalist id="${id}_lst">${md.variantlar
        .map(v => `<option value="${esc(v)}">`).join('')}</datalist>`;
  } else if (md.tur === 'mantiq') {
    kirish = `<select class="fld" id="${id}">
      <option value="0" ${!q ? 'selected' : ''}>Йўқ</option>
      <option value="1" ${q ? 'selected' : ''}>Ҳа</option></select>`;
  } else if (md.tur === 'butun' || md.tur === 'kasr') {
    const qadam = md.tur === 'kasr' ? ' step="any"' : '';
    const chek = (md.min != null ? ` min="${md.min}"` : '')
               + (md.max != null ? ` max="${md.max}"` : '');
    kirish = `<input class="fld" id="${id}" type="number"${qadam}${chek} value="${esc(q)}"/>`;
  } else {
    kirish = `<input class="fld" id="${id}" value="${esc(q)}"/>`;
  }
  return `<div><label class="fl">${nom}${yulduz}</label>${kirish}</div>`;
}

/** Hamma maydon — ikkitadan qatorga. */
function sohaFormaHtml(prefix, qiymatlar) {
  const q = qiymatlar || {};
  const mds = sohaMaydonlar();
  if (!mds.length) return '';
  return `<div class="grid g2" style="gap:8px">${
    mds.map(md => sohaMaydonHtml(md, prefix, q[md.kalit])).join('')}</div>`;
}

/** Formadan qiymatlarni TURI bilan oladi (backend tipni tekshiradi). */
function sohaFormaOl(prefix) {
  const natija = {};
  for (const md of sohaMaydonlar()) {
    const el = _id(prefix + md.kalit);
    if (!el) continue;
    const xom = String(el.value ?? '').trim();
    if (xom === '') continue;                       // bo'sh — yubormaymiz
    if (md.tur === 'mantiq') natija[md.kalit] = xom === '1' || xom === 'true';
    else if (md.tur === 'butun') natija[md.kalit] = parseInt(xom, 10);
    // Kasr STRING bo'lib ketadi: JSON float aniqlikni yo'qotadi, backend
    // esa Decimal kutadi. Shu bitta joyda ehtiyot bo'lmasak 2.5 m³ beton
    // 2.4999999 bo'lib yozilardi.
    else if (md.tur === 'kasr') natija[md.kalit] = xom.replace(',', '.');
    else natija[md.kalit] = xom;
  }
  return natija;
}

/** Majburiy maydon to'ldirilganmi. Bo'sh bo'lsa — nomini qaytaradi. */
function sohaTekshir(prefix) {
  for (const md of sohaMaydonlar()) {
    if (!md.majburiy) continue;
    const el = _id(prefix + md.kalit);
    if (el && String(el.value ?? '').trim() === '') return md.nom;
  }
  return null;
}

/* ---------------- Statuslar (oqim) ---------------- */

function sohaStatus(nom) {
  return (SOHA?.statuslar || []).find(s => s.nom === nom) || null;
}

/** Shu statusdan keyin qaysi holatlarga o'tish mumkin. */
function sohaKeyingi(nom) {
  return sohaStatus(nom)?.keyingi || [];
}

function sohaMano(nom) { return sohaStatus(nom)?.mano || ''; }

/** Progress chizig'i uchun — «bekor» va «muzokara» chetda qoladi. */
function sohaQadamlar() {
  const tartib = ['boshlanish', 'ishlab_chiqarish', 'tayyor', 'topshirildi'];
  return (SOHA?.statuslar || [])
    .filter(s => tartib.includes(s.mano))
    .sort((a, b) => tartib.indexOf(a.mano) - tartib.indexOf(b.mano));
}

/** Ro'yxat ustidagi filtr chiplari uchun statuslar (tugallanganlarsiz). */
function sohaFiltrStatuslari() {
  return (SOHA?.statuslar || [])
    .filter(s => s.mano !== 'topshirildi' && s.mano !== 'bekor')
    .map(s => s.nom);
}

/** Rang MA'NOдан olinadi, status NOMIDAN emas — nomlar har sohada boshqa. */
const MANO_RANG = {
  boshlanish: 'mut', muzokara: 'warn', ishlab_chiqarish: 'pri',
  tayyor: 'warn', topshirildi: 'ok', bekor: 'dn',
};
function sohaTag(nom) { return MANO_RANG[sohaMano(nom)] || stTag(nom); }

/** Ma'noga qarab tugma matni — soha nomlari har xil bo'lgani uchun. */
const MANO_TUGMA = {
  muzokara: '💬', ishlab_chiqarish: '▶', tayyor: '✓', topshirildi: '📤',
};
function sohaTugmaMatni(nom) {
  const belgi = MANO_TUGMA[sohaMano(nom)] || '→';
  return `${belgi} ${kir(nom)}`;
}
