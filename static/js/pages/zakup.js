/* ---- Xarid (Zakup) ---- */
PAGES.zakup=async()=>{
  const[data,mats,sups,units]=await Promise.all([api('/api/purchase'),
    api('/api/catalog/materials'),api('/api/warehouse/suppliers'),api('/api/catalog/units')]);
  window._mats=mats;window._sups=sups;window._units=units;
  return `
  <div class="grid g3 mb">
    ${kpi('boxIn','Жами харидлар',mshort(data.total_bought)+" сўм",data.purchases.length+' та','')}
    ${kpi('flag','Етказиб берувчига қарз',mshort(data.total_debt)+" сўм",data.total_debt>0?'тўланиши керак':'қарз йўқ',data.total_debt>0?'dn':'up')}
    <div class="glass card" style="display:flex;flex-direction:column;justify-content:center;gap:8px">
      ${['Rahbar','Sklad mudiri','Buxgalter'].includes(ME.role)?`<button class="btn pri" onclick="zakupForm()">${icon('plus',15)} Янги харид</button>`:''}
      ${dl('/api/reports/purchases.xlsx','📊 Excel ҳисобот')}
    </div>
  </div>
  <div class="glass card">
    <h2 class="sec mb">Харидлар тарихи</h2>
    <table><thead><tr><th>Сана</th><th>Материал</th><th class="hide-m">Формат</th><th>Миқдор</th><th>Нарх</th><th>Сумма</th><th>Тўлов</th><th>Қарз</th><th></th></tr></thead><tbody>
    ${data.purchases.map(p=>`<tr>
      <td class="muted" style="font-size:11px">${p.purchased_at}</td>
      <td><b>${esc(p.material)}</b>${p.grammaj?' <span class="muted" style="font-size:10px">'+esc(p.grammaj)+'</span>':''}</td>
      <td class="hide-m muted">${esc(p.fmt)||'—'}</td>
      <td>${new Intl.NumberFormat('ru-RU').format(p.qty)} ${esc(p.unit)}</td>
      <td class="muted">${money(p.unit_price)}</td>
      <td><b>${mshort(p.total)}</b></td>
      <td><span class="tag ${p.payment_type==='Naqd'?'ok':'warn'}">${kir(p.payment_type)}</span></td>
      <td>${p.debt>0?`<span class="tag dn">${mshort(p.debt)}</span> ${['Rahbar','Buxgalter','Sklad mudiri'].includes(ME.role)?`<button class="btn sm ghost" onclick="zakupPay(${p.id},${p.debt})">тўлаш</button>`:''}`:'<span class="tag ok">ёпиқ</span>'}</td>
      <td>${['Rahbar','Buxgalter','Sklad mudiri'].includes(ME.role)?`<button class="btn sm ghost" title="Тузатиш" onclick='zakupEdit(${JSON.stringify(p).replace(/'/g,"&#39;")})'>✎</button>${ME.role==='Rahbar'?`<button class="btn sm ghost" style="color:var(--danger)" title="Ўчириш" onclick="zakupDel(${p.id})">✕</button>`:''}`:''}</td>
    </tr>`).join('')||'<tr><td colspan="9" class="muted">Ҳали харид йўқ</td></tr>'}
    </tbody></table>
  </div>`;
};
function zakupForm(matId){
  if(!window._sups||!window._sups.length){toast('w','alertic','Аввал етказиб берувчи қўшинг','Омбор бўлимида');return;}
  const preMat=(matId&&window._mats)?window._mats.find(x=>x.id===matId):null;
  modal(`<h2 class="sec mb">Янги харид (Закуп)</h2>
  <label class="fl">Материал</label>
  <input class="fld" id="z_mat_name" list="mat_list" value="${preMat?esc(preMat.name):''}" placeholder="Материал номини киритинг (ўзи сақланади)" />
  <datalist id="mat_list">
    ${(window._mats||[]).map(x=>`<option value="${esc(x.name)}">`).join('')}
  </datalist>
  <label class="fl">Етказиб берувчи</label>
  <select class="fld" id="z_sup">${window._sups.map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join('')}</select>
  <div class="grid g3" style="gap:8px">
    <div><label class="fl">Миқдор</label><input class="fld" id="z_qty" type="number" oninput="zakupTotal()"/></div>
    <div><label class="fl">Бирлик</label><select class="fld" id="z_unit">${window._units?window._units.map(u=>`<option>${esc(u.name)}</option>`).join(''):'<option>kg</option>'}</select></div>
    <div><label class="fl">Нарх/бирлик</label><input class="fld" id="z_price" inputmode="numeric" value="${preMat?preMat.last_price:''}" oninput="zakupTotal()"/></div>
  </div>
  <label class="fl">Формат (қоғоз ўлчами, ихтиёрий)</label><input class="fld" id="z_fmt" placeholder="85*59 yoki ф62*85"/>
  <div class="between" style="font-size:16px;font-weight:700;padding:8px 0"><span>Жами:</span><span id="z_total" style="color:var(--primary-deep)">0 сўм</span></div>
  <label class="fl">Тўлов тури</label>
  <select class="fld" id="z_ptype" onchange="zakupPayToggle()">
    <option value="Naqd">Нақд — ҳозироқ тўланади</option>
    <option value="Qarz">Қарз — кейин тўланади</option>
    <option value="Keyinroq to'lash">Кейинроқ тўлаш</option>
  </select>
  <div id="z_debtbox" style="display:none">
    <div class="grid g2" style="gap:8px">
      <div><label class="fl">Олдиндан тўланди (ихтиёрий)</label><input class="fld" id="z_paid" inputmode="numeric" value="0" oninput="pulFmt(this)"/></div>
      <div><label class="fl">Тўлов муддати (кун)</label><input class="fld" id="z_due" type="number" value="30"/></div>
    </div>
  </div>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveZakup()">Сақлаш</button></div>`);
}
function zakupUnitSync(){
  const el=document.getElementById('z_mat');
  if(!el)return; // material endi qo'lda yoziladi
  const opt=el.selectedOptions[0];
  if(!opt)return;
  const u=opt.dataset.unit;const us=document.getElementById('z_unit');
  if(us)[...us.options].forEach(o=>{if(o.value===u)us.value=u});
  const pr=document.getElementById('z_price');if(pr&&!pr.value)pr.value=opt.dataset.price||'';
  zakupTotal();
}
function zakupTotal(){
  const t=(+f('z_qty')||0)*(fnum('z_price')||0);
  const el=document.getElementById('z_total');if(el)el.textContent=money(t);
}
function zakupPayToggle(){
  document.getElementById('z_debtbox').style.display=f('z_ptype')==='Naqd'?'none':'block';
}
async function saveZakup(){
  const body={material_name:f('z_mat_name').trim(),supplier_id:+f('z_sup'),qty:+f('z_qty'),
    unit:f('z_unit'),fmt:f('z_fmt'),unit_price:fnum('z_price'),payment_type:f('z_ptype'),
    paid_amount:fnum('z_paid')||0,due_days:+f('z_due')||30,firm:FIRM};
  // xatoni serverga bormasdan aniq aytamiz
  if(!body.material_name)return toast('w','alertic','Материал номи киритилмади','Масалан: Silver pak 140');
  if(!(body.qty>0))return toast('w','alertic','Миқдор киритилмади','0 дан катта сон ёзинг');
  if(!(body.unit_price>0))return toast('w','alertic','Нарх киритилмади',"1 бирлик нархини ёзинг");
  if(body.payment_type!=='Naqd'&&body.paid_amount>body.qty*body.unit_price)
    return toast('w','alertic','Олдиндан тўлов жамидан катта',"Жами: "+money(body.qty*body.unit_price));
  try{const r=await post('/api/purchase',body);
    closeModal();toast('o','check','Харид сақланди',money(r.total)+' · '+r.payment_type);go('zakup');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
function zakupPay(pid,debt){
  modal(`<h2 class="sec mb">Қарзга тўлов</h2>
  <div class="muted" style="font-size:12px;margin-bottom:10px">Қолган қарз: <b>${money(debt)}</b></div>
  <label class="fl">Сумма</label><input class="fld" id="zp_amount" inputmode="numeric" value="${debt}" oninput="pulFmt(this)"/>
  <label class="fl">Усул</label><select class="fld" id="zp_method"><option value="Naqd">Нақд</option><option value="O'tkazma">Ўтказма</option><option value="Karta">Карта</option></select>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveZakupPay(${pid})">Тўлаш</button></div>`);
}
async function saveZakupPay(pid){
  try{await post('/api/purchase/pay',{purchase_id:pid,amount:fnum('zp_amount'),method:f('zp_method')});
    closeModal();toast('o','check','To\'landi','');go('zakup');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}



/* ---- Xaridni tuzatish (xato ketsa) ---- */
function zakupEdit(p){
  modal(`<h2 class="sec mb">№${p.id} харидни тузатиш</h2>
  <div class="muted" style="font-size:11.5px;margin-bottom:10px">${esc(p.material)} · ${p.purchased_at}</div>
  <div class="grid g2" style="gap:8px">
    <div><label class="fl">Миқдор (${esc(p.unit)})</label><input class="fld" id="ze_qty" type="number" step="0.1" value="${p.qty}"/></div>
    <div><label class="fl">Нарх (сўм/${esc(p.unit)})</label><input class="fld" id="ze_price" type="number" value="${p.unit_price}"/></div>
  </div>
  <label class="fl">Формат</label><input class="fld" id="ze_fmt" value="${esc(p.fmt||'')}"/>
  <div class="grid g2" style="gap:8px">
    <div><label class="fl">Тўлов тури</label>
      <select class="fld" id="ze_ptype" onchange="zakupEditPaidToggle()">
        ${["Naqd","Qarz","Keyinroq to'lash"].map(x=>`<option value="${x}" ${p.payment_type===x?'selected':''}>${kir(x)}</option>`).join('')}
      </select></div>
    <div id="ze_paidbox" style="display:${p.payment_type==='Naqd'?'none':'block'}">
      <label class="fl">Шу харидда тўланган</label>
      <input class="fld" id="ze_paid" type="number" value="${Math.round(p.paid||0)}"/></div>
  </div>
  <label class="fl">Изоҳ</label><input class="fld" id="ze_note" value="${esc(p.note||'')}"/>
  <div class="muted" style="font-size:11px;margin-top:8px">Омбор қолдиғи автомат мос тузатилади.
  «Нақд» = пул ўша заҳоти тўлиқ берилган. Пулни алоҳида (кўпроқ ёки камроқ) берган бўлсангиз —
  «Қарз» қилиб қўйинг ва пулни Омбор > Етказиб берувчи > «Пул бериш» орқали ёзинг.</div>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="zakupEditSave(${p.id})">Сақлаш</button></div>`);
}
function zakupEditPaidToggle(){
  const box=document.getElementById('ze_paidbox');
  if(box)box.style.display=f('ze_ptype')==='Naqd'?'none':'block';
}
async function zakupEditSave(id){
  const body={qty:+f('ze_qty'),unit_price:+f('ze_price'),fmt:f('ze_fmt'),note:f('ze_note'),
    payment_type:f('ze_ptype')};
  if(f('ze_ptype')!=='Naqd')body.paid_amount=+f('ze_paid')||0;
  try{await api('/api/purchase/'+id,{method:'PUT',body:JSON.stringify(body)});
    closeModal();toast('o','check','Харид тузатилди','');go('zakup');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function zakupDel(id){
  if(!confirm('№'+id+' харид бутунлай ўчирилсинми? Омбор қолдиғи қайтарилади.'))return;
  try{await api('/api/purchase/'+id,{method:'DELETE'});
    toast('o','check','Харид ўчирилди','');go('zakup');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
