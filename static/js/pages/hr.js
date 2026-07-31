/* ---- Xodimlar (HR) ---- */
PAGES.hr = async () => {
    setTitle(t('hr') || "Ходимлар", "Ишчилар ва ойлик маошлар");
    
    let html = `
    <div class="flx" style="justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3>${t('hr') || 'Ходимлар'}</h3>
        <div class="row" style="flex-wrap:wrap;gap:6px">
            <button class="btn pri sm" onclick="hrWorkModal()">✂️ Иш қайди</button>
            <button class="btn sm" onclick="hrSalaryModal()">💰 Оклад ёзиш</button>
            <button class="btn sm" onclick="hrPayModal()">💵 Пул бериш</button>
            <button class="btn sm" onclick="hrPayrollModal()">📋 Ойлик</button>
            ${dl('/api/reports/payroll.xlsx','Excel')}
            <button class="btn sm" onclick="hrAddModal()">+ Янги ходим</button>
        </div>
    </div>
    <div class="glass" style="padding:16px;">
        <table class="tbl">
            <thead>
                <tr>
                    <th>Ф.И.Ш</th>
                    <th>Лавозим</th>
                    <th>Бригада</th>
                    <th>Тел</th>
                    <th>Иш ҳақи / дона</th>
                </tr>
            </thead>
            <tbody id="hrList"></tbody>
        </table>
    </div>
    `;
    content.innerHTML = html;
    await hrLoad();
};

window.hrLoad = async () => {
    let res = await api('/api/hr/employees');
    window._emps = res || [];
    if(res) {
        let tbody = _id('hrList');
        if(!tbody) return;
        
        tbody.innerHTML = res.map(e => `
            <tr style="cursor:pointer" onclick="openEmployee(${e.id})" title="Батафсил кўриш">
                <td><b>${esc(e.name)}</b></td>
                <td>${kir(e.position)}</td>
                <td><span class="badge gray">${esc(e.brigade || '-')}</span></td>
                <td>${esc(e.phone)}</td>
                <td>${money(e.rate_per_box)}</td>
            </tr>
        `).join('');
        if(res.length === 0) tbody.innerHTML = `<tr><td colspan="5" class="empty">Топилмади</td></tr>`;
    }
};

window.hrAddModal = () => {
    openModal(`
    <h3>Янги ходим</h3>
    <label class="fl">Ф.И.Ш</label>
    <input class="fld" id="hr_name" />
    <label class="fl">Лавозим</label>
    <select class="fld" id="hr_pos">
        <option value="Stanokchi">Станокчи</option>
        <option value="Haydovchi">Ҳайдовчи</option>
        <option value="Texnolog">Технолог</option>
        <option value="Boshqa">Бошқа</option>
    </select>
    <label class="fl">Бригада</label>
    <input class="fld" id="hr_brigade" />
    <label class="fl">Телефон</label>
    <input class="fld" id="hr_ph" />
    <label class="fl">Иш ҳақи (1 дона қути учун, сўм)</label>
    <input class="fld" id="hr_rate" type="number" value="150" />
    <div class="flx" style="gap:10px;margin-top:16px;">
        <button class="btn ghost" style="flex:1" onclick="closeModal()">${t('cancel') || 'Bekor qilish'}</button>
        <button class="btn primary" style="flex:1" onclick="hrSave()">${t('save') || 'Saqlash'}</button>
    </div>
    `);
};

window.hrSave = async () => {
    let data = {
        name: _id('hr_name').value.trim(),
        position: _id('hr_pos').value,
        brigade: _id('hr_brigade').value.trim(),
        phone: _id('hr_ph').value.trim(),
        rate_per_box: parseFloat(_id('hr_rate').value) || 0,
        firm: window.FIRM || ""
    };
    if(!data.name) return toast("Исм киритилмади", "err");
    
    let res = await api('/api/hr/employees', 'POST', data);
    if(res) {
        toast("Сақланди");
        closeModal();
        await hrLoad();
    }
};


/* ---- Xodim detalizatsiyasi — daftar: ishlagani | olgan pullari | qolgan ---- */
window.openEmployee = async (id) => {
  const d = await api('/api/hr/employees/'+id+'/detalizatsiya');
  const rows = Math.max(d.ishlar.length, d.olgan_pullari.length, 1);
  let body = '';
  for(let i=0;i<rows;i++){
    const w = d.ishlar[i], p = d.olgan_pullari[i];
    body += `<tr>
      <td class="muted" style="font-size:10.5px">${w?w.sana:''}</td>
      <td>${w?(w.turi==='Oklad'?'<span class="tag pri">Оклад</span>':'<span class="tag mut">Ишбай</span>'):''}</td>
      <td class="muted" style="font-size:10.5px">${w?(w.buyurtma?'#'+w.buyurtma:'—'):''}</td>
      <td style="text-align:right">${w?(w.dona?new Intl.NumberFormat('ru-RU').format(w.dona):'—'):''}</td>
      <td style="text-align:right"><b style="${w&&!w.sifat?'text-decoration:line-through;color:var(--danger)':''}">${w?new Intl.NumberFormat('ru-RU').format(Math.round(w.summa)):''}</b>
        ${w&&!w.sifat?'<div style="font-size:9px;color:var(--danger)">брак — ёзилмади</div>':''}</td>
      <td class="muted" style="font-size:10.5px;border-left:2px solid var(--hair)">${p?p.sana:''}</td>
      <td style="text-align:right;color:var(--warn)"><b>${p?'−'+new Intl.NumberFormat('ru-RU').format(Math.round(p.summa)):''}</b></td>
      <td class="muted" style="font-size:10.5px">${p?esc(p.nimaga||'—'):''}</td>
    </tr>`;
  }
  modal(`<h2 class="sec">${esc(d.name)}</h2>
  <div class="muted" style="font-size:12px;margin:4px 0 12px">${esc(d.position||'')}${d.brigade?' · '+esc(d.brigade)+' brigada':''}${d.phone?' · '+esc(d.phone):''} · ${money(d.rate_per_box)}/dona</div>
  <div class="grid g3 mb" style="gap:8px">
    <div style="text-align:center"><div class="muted" style="font-size:10px">ҲИСОБЛАНДИ (ОЙЛИГИ)</div><b>${mshort(d.jami_hisoblandi)}</b>
      <div class="muted" style="font-size:9.5px">${new Intl.NumberFormat('ru-RU').format(d.jami_qutilar)} дона қути</div></div>
    <div style="text-align:center"><div class="muted" style="font-size:10px">ОЛГАН ПУЛЛАРИ</div><b style="color:var(--warn)">−${mshort(d.jami_olindi)}</b></div>
    <div style="text-align:center"><div class="muted" style="font-size:10px">ҚЎЛГА ТЕГАДИ</div>
      <b style="color:${d.qolgan>=0?'var(--ok)':'var(--danger)'}">${mshort(d.qolgan)}</b>
      ${d.qolgan<0&&d.jami_hisoblandi>0?'<div style="font-size:9.5px;color:var(--danger)">ортиқча олган</div>':''}</div>
  </div>
  ${d.jami_hisoblandi===0&&d.jami_olindi>0
    ? alertBox('w','alertic','Бу ходимнинг ойлиги ҳали ёзилмаган',
        "Шунинг учун «қўлга тегади» минус кўриняпти. Ойлигини киритинг: қатъий маош бўлса «Оклад ёзиш», "+
        "қути сонига қараб ишласа «Иш қайди». Шундан кейин олган пуллари ўша ойликдан айрилади.")
    : ''}
  <div class="row mb" style="flex-wrap:wrap;gap:6px;margin-top:8px">
    ${['Rahbar','Buxgalter',"Sex boshlig'i"].includes(ME.role)?`<button class="btn sm pri" onclick="closeModal();hrSalaryModal()">💰 Оклад ёзиш</button>
    <button class="btn sm" onclick="closeModal();hrWorkModal()">✂️ Иш қайди</button>
    <button class="btn sm" onclick="closeModal();hrPayModal()">💵 Пул бериш</button>`:''}
  </div>
  <div style="overflow-x:auto">
  <table style="font-size:11px;min-width:640px">
    <thead>
      <tr><th colspan="5" style="text-align:center;background:var(--hair)">ИШЛАГАНИ (ҳисобига ёзилди)</th>
          <th colspan="3" style="text-align:center;background:var(--hair);border-left:2px solid var(--ink-2)">ОЛГАН ПУЛЛАРИ</th></tr>
      <tr><th>Сана</th><th>Тури</th><th>Буюртма</th><th style="text-align:right">Дона</th><th style="text-align:right">Сумма</th>
          <th style="border-left:2px solid var(--hair)">Сана</th><th style="text-align:right">Сумма</th><th>Нимага</th></tr>
    </thead>
    <tbody>${body}</tbody>
    <tfoot>
      <tr style="border-top:2px solid var(--ink-2)">
        <td colspan="4"><b>Жами ҳисобланди</b></td>
        <td style="text-align:right"><b>${new Intl.NumberFormat('ru-RU').format(Math.round(d.jami_hisoblandi))}</b></td>
        <td style="border-left:2px solid var(--hair)"><b>Жами олинди</b></td>
        <td style="text-align:right;color:var(--warn)"><b>−${new Intl.NumberFormat('ru-RU').format(Math.round(d.jami_olindi))}</b></td>
        <td></td>
      </tr>
      <tr><td colspan="5"></td>
        <td style="border-left:2px solid var(--hair)"><b>ҚЎЛГА ТЕГАДИ</b></td>
        <td colspan="2" style="text-align:right;font-size:14px;color:${d.qolgan>=0?'var(--ok)':'var(--danger)'}">
          <b>${new Intl.NumberFormat('ru-RU').format(Math.round(d.qolgan))}</b></td>
      </tr>
    </tfoot>
  </table></div>
  ${d.ishlar.length?'':'<div class="muted" style="font-size:12px;margin-top:8px">Бу ходимга ҳали иш ёзилмаган</div>'}`, true);
};

/* ---- Ish qaydi (sifat nazorati bilan) ---- */
window.hrWorkModal = () => {
  if(!window._emps||!window._emps.length){toast("Аввал ходим қўшинг","err");return;}
  openModal(`<h3>Иш қайди — сифат назорати</h3>
  <label class="fl">Ходим</label>
  <select class="fld" id="w_emp">${window._emps.map(e=>`<option value="${e.id}">${esc(e.name)} (${money(e.rate_per_box)}/dona)</option>`).join('')}</select>
  <label class="fl">Буюртма № (ихтиёрий)</label><input class="fld" id="w_order" type="number"/>
  <label class="fl">Тайёрланган қутилар сони</label><input class="fld" id="w_qty" type="number"/>
  <label class="fl"><input type="checkbox" id="w_qc" checked/> Сифат назоратидан ўтди</label>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="hrWorkSave()">Сақлаш</button></div>`);
};
window.hrWorkSave = async () => {
  try{const r=await post('/api/hr/work',{employee_id:+f('w_emp'),order_id:+f('w_order')||null,qty:+f('w_qty'),qc_passed:_id('w_qc').checked});
    closeModal();toast('o','check','Иш қайд этилди','Ҳисобга ёзилди: '+money(r.amount));
  }catch(e){toast('d','alertic','Хатолик',e.message);}
};

/* ---- Xodimga Oklad yozish ---- */
window.hrSalaryModal = () => {
  if(!window._emps||!window._emps.length){toast("Аввал ходим қўшинг","err");return;}
  openModal(`<h3>Тайинли ойлик (Оклад) ёзиш</h3>
  <div class="muted" style="font-size:11px;margin-bottom:8px">Қути сонига қараб эмас, қатъий белгиланган маош.</div>
  <label class="fl">Ходим</label>
  <select class="fld" id="s_emp">${window._emps.map(e=>`<option value="${e.id}">${esc(e.name)}</option>`).join('')}</select>
  <label class="fl">Оклад суммаси (сўм)</label><input class="fld" id="s_amount" inputmode="numeric" oninput="pulFmt(this)"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="hrSalarySave()">Сақлаш</button></div>`);
};
window.hrSalarySave = async () => {
  try{const r=await post('/api/hr/salary',{employee_id:+f('s_emp'),amount:fnum('s_amount'),firm:FIRM||""});
    closeModal();toast('o','check','Оклад ёзилди',"Ҳисобга қўшилди: "+money(r.amount));
  }catch(e){toast('d','alertic','Хатолик',e.message);}
};

/* ---- Xodimga pul berish ---- */
window.hrPayModal = () => {
  if(!window._emps||!window._emps.length){toast("Аввал ходим қўшинг","err");return;}
  openModal(`<h3>Ходимга пул бериш</h3>
  <label class="fl">Ходим</label>
  <select class="fld" id="c_emp">${window._emps.map(e=>`<option value="${e.id}">${esc(e.name)}</option>`).join('')}</select>
  <label class="fl">Сумма (сўм)</label><input class="fld" id="c_amount" inputmode="numeric" oninput="pulFmt(this)"/>
  <label class="fl">Нимага (ихтиёрий)</label><input class="fld" id="c_note" placeholder="аванс, йўлкира, тушлик…"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="hrPaySave(this)">Бериш</button></div>`);
};
window.hrPaySave = async (btn) => {
  const amt=fnum('c_amount');
  if(!(amt>0)){toast('d','alertic','Хатолик','Сумма 0 дан катта бўлсин');return;}
  if(btn){btn.disabled=true;btn.textContent='…';}   // такрор босилмасин (дубликат олдини олиш)
  try{await post('/api/hr/cash',{kind:'Avans',employee_id:+f('c_emp'),amount:amt,note:f('c_note'),firm:FIRM});
    closeModal();toast('o','check','Пул берилди',money(amt));
    if(window.PAGE)_renderPage(PAGE);   // жорий саҳифани янгилаш (кўриниб турсин)
  }catch(e){if(btn){btn.disabled=false;btn.textContent='Бериш';}toast('d','alertic','Хатолик',e.message);}
};

/* ---- Oylik vedomost (joriy oy) ---- */
window.hrPayrollModal = async () => {
  const pr=await api('/api/hr/payroll');
  openModal(`<h3>Жорий ой — ойлик ҳисоб-китоб</h3>
  <div class="muted" style="font-size:11px;margin-bottom:8px">Ишбай − Берилган пуллар = Қўлга тегади</div>
  <table style="font-size:12px"><thead><tr><th>Ходим</th><th>Қутилар</th><th>Ишбай</th><th>Берилди</th><th>Қолади</th></tr></thead><tbody>
  ${pr.map(r=>`<tr><td><b>${esc(r.name)}</b></td><td>${r.boxes}</td><td>${mshort(r.earned)}</td>
    <td style="color:var(--warn)">−${mshort(r.advances)}</td>
    <td><b style="color:${r.net>=0?'var(--ok)':'var(--danger)'}">${mshort(r.net)}</b></td></tr>`).join('')||'<tr><td colspan="5" class="muted">Маълумот йўқ</td></tr>'}
  </tbody></table>
  <div class="row" style="margin-top:14px;justify-content:flex-end">
    ${dl('/api/reports/payroll.xlsx','Excel юклаб олиш')}
    <button class="btn" onclick="closeModal()">Ёпиш</button></div>`);
};
