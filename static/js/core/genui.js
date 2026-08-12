/* ============ GenUI — AI javobini HAQIQIY UI qilib chizish ============
 *
 * Agent `korsat` asbobi orqali komponent yuboradi, bu yerda ular
 * chiziladi. Backend (app/genui.py) allaqachon tekshirib, tozalab
 * bergan — bu yerda esa MATN HECH QACHON HTML sifatida qo'yilmaydi.
 *
 * XAVFSIZLIK QOIDASI: hamma matn `textContent` bilan qo'yiladi.
 * `innerHTML` faqat O'ZIMIZ yozgan tuzilma uchun ishlatiladi, model
 * bergan matn uchun EMAS. Model javobi — ishonchsiz manba (mijoz
 * ma'lumoti ichida ham `<script>` bo'lishi mumkin).
 */

/** Element yasash yordamchisi: matn har doim textContent orqali. */
function el(teg, sinf, matn) {
  const d = document.createElement(teg);
  if (sinf) d.className = sinf;
  if (matn !== undefined && matn !== null) d.textContent = String(matn);
  return d;
}

const GENUI_RANG = { ok: 'ok', ogoh: 'warn', xavf: 'dn', '': 'mut' };

/** Komponentlar ro'yxatini chizadi va bitta konteyner qaytaradi. */
function genuiChiz(komponentlar, suhbatId) {
  const quti = el('div', 'genui');
  for (const k of (komponentlar || [])) {
    try {
      const bolak = GENUI_CHIZUVCHI[k.tur] && GENUI_CHIZUVCHI[k.tur](k, suhbatId);
      if (bolak) quti.appendChild(bolak);
    } catch (e) {
      console.error('genui', k.tur, e);
    }
  }
  return quti.children.length ? quti : null;
}

function genuiKarta(sarlavha) {
  const karta = el('div', 'genui-karta');
  if (sarlavha) karta.appendChild(el('div', 'genui-sarlavha', sarlavha));
  return karta;
}

const GENUI_CHIZUVCHI = {

  /* ---- 1. JADVAL — tizimning aksariyat ro'yxati shu ---- */
  jadval(k) {
    const karta = genuiKarta(k.sarlavha);
    const aylan = el('div', 'genui-aylan');   // tor ekranda gorizontal scroll
    const jadval = el('table', 'genui-jadval');

    if (k.ustunlar && k.ustunlar.length) {
      const bosh = el('tr');
      k.ustunlar.forEach(u => bosh.appendChild(el('th', null, u)));
      jadval.appendChild(el('thead')).appendChild(bosh);
    }
    const tana = el('tbody');
    for (const q of (k.qatorlar || [])) {
      const tr = el('tr', q.holat ? 'genui-q-' + (GENUI_RANG[q.holat] || 'mut') : null);
      (q.hujayralar || []).forEach((h, i) => {
        const td = el('td', null, h);
        // Raqamli ustunni o'ngga tekislash — pul ustunlari shunda o'qiladi
        if (i > 0 && /^[\d\s.,+\-]+( ?(so'm|сўм|%|kg|dona))?$/i.test(h)) {
          td.style.textAlign = 'right';
        }
        tr.appendChild(td);
      });
      tana.appendChild(tr);
    }
    jadval.appendChild(tana);
    aylan.appendChild(jadval);
    karta.appendChild(aylan);
    if (k.izoh) karta.appendChild(el('div', 'genui-izoh', k.izoh));
    return karta;
  },

  /* ---- 2. KO'RSATKICHLAR — KPI plitalari ---- */
  korsatkichlar(k) {
    const karta = genuiKarta(k.sarlavha);
    const tor = el('div', 'genui-plitalar');
    for (const e of (k.elementlar || [])) {
      const p = el('div', 'genui-plita');
      p.appendChild(el('div', 'genui-plita-nom', e.nom));
      p.appendChild(el('div', 'genui-plita-qiymat ' +
        (e.holat ? 'genui-t-' + (GENUI_RANG[e.holat] || 'mut') : ''), e.qiymat));
      if (e.ozgarish) p.appendChild(el('div', 'genui-plita-ozg', e.ozgarish));
      tor.appendChild(p);
    }
    karta.appendChild(tor);
    return karta;
  },

  /* ---- 3. TAFSILOT — bitta obyektning ma'lumoti ---- */
  tafsilot(k) {
    const karta = genuiKarta(k.sarlavha);
    for (const q of (k.qatorlar || [])) {
      const qator = el('div', 'genui-qator');
      qator.appendChild(el('span', 'genui-nom', q.nom));
      qator.appendChild(el('b', q.holat ? 'genui-t-' + (GENUI_RANG[q.holat] || 'mut') : '',
                           q.qiymat));
      karta.appendChild(qator);
    }
    if (k.izoh) karta.appendChild(el('div', 'genui-izoh', k.izoh));
    return karta;
  },

  /* ---- 4. TAQSIMOT — nisbatni ko'rsatuvchi ustunlar ---- */
  taqsimot(k) {
    const karta = genuiKarta(k.sarlavha);
    const elementlar = k.elementlar || [];
    // Eng katta qiymat 100% — nisbat shundan hisoblanadi. Hammasi nol
    // bo'lsa 1 ga bo'lamiz, aks holda NaN kelib chiziq umuman chizilmaydi.
    const eng = Math.max(1, ...elementlar.map(e => Math.abs(+e.qiymat || 0)));
    for (const e of elementlar) {
      const qiymat = +e.qiymat || 0;
      const qator = el('div', 'genui-bar-qator');
      qator.appendChild(el('div', 'genui-bar-nom', e.nom));
      const yolak = el('div', 'genui-bar-yolak');
      const chiziq = el('div', 'genui-bar ' +
        (e.holat ? 'genui-b-' + (GENUI_RANG[e.holat] || 'mut') : ''));
      chiziq.style.width = Math.max(2, Math.abs(qiymat) / eng * 100) + '%';
      yolak.appendChild(chiziq);
      qator.appendChild(yolak);
      qator.appendChild(el('div', 'genui-bar-son',
        new Intl.NumberFormat('ru-RU').format(Math.round(qiymat)) +
        (k.birlik ? ' ' + k.birlik : '')));
      karta.appendChild(qator);
    }
    return karta;
  },

  /* ---- 5. PROFIL OYNASI — konstruktorning yuragi ----
   * Oddiy odam «non zavodim bor» deb aytgach, tizimi QANDAY bo'lishini
   * shu yerda ko'radi: qaysi maydonlar, nima ketadi, qanday bosqichlar.
   * Tasdiqlashdan oldin ko'rsatiladi — bu eng muhim ekran. */
  profil_oynasi(k) {
    const karta = genuiKarta(k.sarlavha || 'Tizimingiz shunday bo\'ladi');
    if (k.nom) karta.appendChild(el('div', 'genui-profil-nom', k.nom));
    if (k.izoh) karta.appendChild(el('div', 'genui-izoh', k.izoh));

    if (k.bosqichlar && k.bosqichlar.length) {
      karta.appendChild(el('div', 'genui-kichik-sarlavha', 'Buyurtma bosqichlari'));
      const oqim = el('div', 'genui-oqim');
      k.bosqichlar.forEach((b, i) => {
        if (i) oqim.appendChild(el('span', 'genui-oqim-strelka', '→'));
        oqim.appendChild(el('span', 'genui-oqim-qadam', b));
      });
      karta.appendChild(oqim);
    }

    if (k.maydonlar_royxati && k.maydonlar_royxati.length) {
      karta.appendChild(el('div', 'genui-kichik-sarlavha',
        'Buyurtma formasida so\'raladigan ma\'lumot'));
      const tor = el('div', 'genui-maydonlar');
      for (const md of k.maydonlar_royxati) {
        const chip = el('div', 'genui-maydon');
        chip.appendChild(el('span', 'genui-maydon-nom',
          md.nom + (md.majburiy ? ' *' : '')));
        chip.appendChild(el('span', 'genui-maydon-tur',
          [md.tur, md.birlik].filter(Boolean).join(', ')));
        tor.appendChild(chip);
      }
      karta.appendChild(tor);
    }

    if (k.retsept && k.retsept.length) {
      karta.appendChild(el('div', 'genui-kichik-sarlavha',
        'Bir buyurtmaga nima ketadi'));
      for (const r of k.retsept) {
        const qator = el('div', 'genui-qator');
        qator.appendChild(el('span', 'genui-nom', r.material));
        qator.appendChild(el('b', null, r.miqdor + (r.birlik ? ' ' + r.birlik : '')));
        karta.appendChild(qator);
      }
    }
    return karta;
  },

  /* ---- 6. TASDIQ — harakat taklifi (Genkit: interrupt) ----
   * Agent hech narsani o'zi bajarmaydi. Bu tugma bosilgandagina
   * `/api/agent/amal` chaqiriladi va audit jurnaliga tugmani bosgan
   * ODAM yoziladi. */
  tasdiq(k) {
    const karta = genuiKarta(k.sarlavha);
    karta.classList.add('genui-tasdiq');
    if (k.xavfli) karta.classList.add('genui-xavfli');
    if (k.matn) karta.appendChild(el('div', 'genui-tasdiq-matn', k.matn));

    const qator = el('div', 'genui-tugmalar');
    const tugma = el('button', 'btn sm ' + (k.xavfli ? 'dngr' : 'pri'), k.tugma);
    const holat = el('span', 'genui-holat');
    tugma.onclick = async () => {
      if (k.xavfli && !confirm(k.tugma + '?\n\n' + (k.matn || ''))) return;
      tugma.disabled = true;
      holat.textContent = 'bajarilmoqda…';
      try {
        const j = await post('/api/agent/amal', { amal: k.amal, kirish: k.kirish });
        holat.textContent = '✓ ' + (j.xabar || 'bajarildi');
        holat.className = 'genui-holat genui-t-ok';
        tugma.remove();
        // Amal tizimni o'zgartirgan bo'lishi mumkin (profil, maqom) —
        // sahifani yangilaymiz, aks holda ekranda eskisi turaveradi.
        if (typeof route === 'function') route();
      } catch (e) {
        holat.textContent = '✕ ' + (e.message || e);
        holat.className = 'genui-holat genui-t-dn';
        tugma.disabled = false;
      }
    };
    qator.appendChild(tugma);
    qator.appendChild(holat);
    karta.appendChild(qator);
    return karta;
  },

  /* ---- 7. HUJJAT ---- */
  hujjat(k) {
    const karta = genuiKarta(k.sarlavha);
    const qator = el('div', 'genui-tugmalar');
    for (const h of (k.havolalar || [])) {
      const a = el('button', 'btn sm', '📄 ' + h.nom);
      // `download()` tokenni qo'shib yuklab beradi — oddiy havola
      // 401 bilan qaytardi, chunki hujjat endpointlari himoyalangan.
      a.onclick = () => download(h.havola);
      qator.appendChild(a);
    }
    karta.appendChild(qator);
    return karta;
  },

  /* ---- 8. OGOH ---- */
  ogoh(k) {
    const sinf = { xavf: 'd', ogoh: 'w', ok: 'o' }[k.daraja] || 'w';
    const quti = el('div', 'alert ' + sinf);
    const ichi = el('div');
    ichi.appendChild(el('b', null, k.sarlavha || 'Diqqat'));
    ichi.appendChild(el('p', null, k.matn));
    quti.appendChild(el('div', 'ai', '!'));
    quti.appendChild(ichi);
    return quti;
  },
};
