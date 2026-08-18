/* ---- Kataloglar boshqaruvi (Sozlamalar ichida) ---- */

PAGES.set = async () => {
    setTitle(t('set') || 'Sozlamalar', t('set_sub') || 'Tizimni moslashtirish');
    
    // Tab switching logic
    window.openSetTab = async (tabName) => {
        window._setTab = tabName;
        document.querySelectorAll('.set-tab').forEach(el => el.classList.remove('pri'));
        const activeTab = document.getElementById('tab_' + tabName);
        if(activeTab) activeTab.classList.add('pri');
        
        let html = '';
        if (tabName === 'users') {
            html = await usersAdmin();
        } else if (tabName === 'catalog') {
            html = await catalogAdmin();
        } else if (tabName === 'constructor') {
            html = await renderConstructor();
        } else if (tabName === 'sys') {
            html = await sysAdmin();
        } else if (tabName === 'rekvizit') {
            html = await rekvizitAdmin();
        } else if (tabName === 'ai') {
            html = await aiKorsatmaAdmin();
        } else if (tabName === 'lang') {
            const curLang = localStorage.getItem('tizim_lang') || 'uz_lat';
            html = `
            <div class="glass card mb">
                <h2 class="sec mb">Тил ва алифбо созламалари</h2>
                <div class="muted" style="font-size: 13px; margin-bottom: 16px;">
                    Dastur interfeysi qaysi til va alifboda ko'rsatilishini tanlang:
                </div>
                
                <div class="grid g3" style="gap: 12px; margin-bottom: 20px;">
                    <div class="glass card ${curLang === 'uz_lat' ? 'border-pri' : ''}" style="cursor:pointer; padding: 16px; text-align: center;" onclick="changeLang('uz_lat')">
                        <div style="font-size:24px; margin-bottom: 8px;">🇺🇿</div>
                        <b>O'zbek (Lotin)</b>
                        <div class="muted" style="font-size: 11px; margin-top: 4px;">Standart</div>
                    </div>
                    
                    <div class="glass card ${curLang === 'uz_cyr' ? 'border-pri' : ''}" style="cursor:pointer; padding: 16px; text-align: center;" onclick="changeLang('uz_cyr')">
                        <div style="font-size:24px; margin-bottom: 8px;">🇺🇿</div>
                        <b>Ўзбек (Кирил)</b>
                        <div class="muted" style="font-size: 11px; margin-top: 4px;">Кирилл алифбоси</div>
                    </div>
                    
                    <div class="glass card ${curLang === 'ru' ? 'border-pri' : ''}" style="cursor:pointer; padding: 16px; text-align: center;" onclick="changeLang('ru')">
                        <div style="font-size:24px; margin-bottom: 8px;">🇷🇺</div>
                        <b>Русский</b>
                        <div class="muted" style="font-size: 11px; margin-top: 4px;">Кириллица</div>
                    </div>
                </div>
            </div>`;
        }
        document.getElementById('setContent').innerHTML = html;
    };

    window.changeLang = (code) => {
        localStorage.setItem('tizim_lang', code);
        location.reload();
    };

    document.getElementById('content').innerHTML = `
    <div class="page show">
        <div class="tabs mb" style="display:flex; gap: 8px; overflow-x: auto; padding-bottom: 4px;">
            <button class="btn set-tab" id="tab_users" onclick="openSetTab('users')">${icon('users',14)} Фойдаланувчилар</button>
            <button class="btn set-tab" id="tab_catalog" onclick="openSetTab('catalog')">${icon('list',14)} Каталоглар</button>
            <button class="btn set-tab" id="tab_constructor" onclick="openSetTab('constructor')">${icon('box',14)} Конструктор</button>
            <button class="btn set-tab" id="tab_sys" onclick="openSetTab('sys')">${icon('settings',14)} Тизим созламалари</button>
            <button class="btn set-tab" id="tab_rekvizit" onclick="openSetTab('rekvizit')">${icon('doc',14)} Ҳужжат реквизитлари</button>
            <button class="btn set-tab" id="tab_ai" onclick="openSetTab('ai')">${icon('bot',14)} AI кўрсатмаси</button>
            <button class="btn set-tab" id="tab_lang" onclick="openSetTab('lang')">${icon('globe',14)} Тил (Language)</button>
        </div>
        <div id="setContent"></div>
    </div>`;
    
    // Default tab
    openSetTab(window._setTab || 'users');
};

/* ---- Ҳужжат реквизитлари: акт, юк хати, сверка шапкаси ---- */
async function rekvizitAdmin(){
  const st = await api('/api/finance/settings');
  const MAYDON = [
    ['nomi',   'Фирма номи',        'Масалан: «Интран» МЧЖ'],
    ['stir',   'СТИР (ИНН)',        '123456789'],
    ['manzil', 'Манзил',            'Тошкент ш., ... кўчаси, 12-уй'],
    ['tel',    'Телефон',           '+998 90 123-45-67'],
    ['bank',   'Банк',              'Ипотека банк, ... филиали'],
    ['hisob',  'Ҳисоб рақами',      '2020 8000 1234 5678 9001'],
    ['rahbar', 'Раҳбар (имзо учун)','Директор: Рустамов Р.'],
  ];
  const blok = (idx,sarlavha) => `
    <div class="glass card mb">
      <h2 class="sec mb">${sarlavha}</h2>
      <label class="fl">Қайси фирмага тегишли (мижоз фирмаси билан солиштирилади)</label>
      <input class="fld mb" id="rk_${idx}_kalit" value="${esc(st['rekvizit_'+idx+'_kalit']||'')}" placeholder="интран / макс стар"/>
      ${MAYDON.map(([k,lbl,ph])=>`
        <label class="fl">${lbl}</label>
        <input class="fld mb" id="rk_${idx}_${k}" value="${esc(st['rekvizit_'+idx+'_'+k]||'')}" placeholder="${ph}"/>
      `).join('')}
    </div>`;
  return `
  <div class="glass card mb">
    <div class="muted" style="font-size:13px;line-height:1.6">
      Бу маълумотлар <b>акт</b>, <b>юк хати (накладной)</b> ва <b>сверка</b> ҳужжатларининг тепасида чиқади.
      Мижознинг фирмасига қараб мос реквизит автомат танланади.<br>
      <b>Бўш қолдирилган майдон ҳужжатда умуман чиқмайди</b> — тўлдирмасангиз ҳам ҳужжат аввалгидек ишлайверади.
    </div>
  </div>
  ${blok('firma1','1-фирма')}
  ${blok('firma2','2-фирма')}
  <div class="glass card mb">
    <label class="fl">Ҳужжат пастидаги қўшимча ёзув (ихтиёрий)</label>
    <input class="fld" id="rk_footer" value="${esc(st['hujjat_footer']||'')}" placeholder="Масалан: Ҳужжат электрон тайёрланди"/>
    <div class="row" style="margin-top:16px;justify-content:flex-end">
      <button class="btn pri" onclick="saveRekvizit(this)">Сақлаш</button>
    </div>
  </div>`;
}

async function saveRekvizit(btn){
  const MAYDON=['kalit','nomi','stir','manzil','tel','bank','hisob','rahbar'];
  const values={};
  for(const idx of ['firma1','firma2'])
    for(const k of MAYDON){
      const el=_id(`rk_${idx}_${k}`);
      if(el)values[`rekvizit_${idx}_${k}`]=el.value.trim();
    }
  const f=_id('rk_footer'); if(f)values['hujjat_footer']=f.value.trim();
  if(btn){btn.disabled=true;btn.textContent='…';}
  try{
    await post('/api/finance/settings',{values});
    toast('o','check','Сақланди','Реквизитлар ҳужжатларда чиқади');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
  finally{if(btn){btn.disabled=false;btn.textContent='Сақлаш';}}
}

async function catalogAdmin(){
  const[units,positions,cats,services,formulas]=await Promise.all([
    api('/api/catalog/units'),api('/api/catalog/positions'),api('/api/catalog/categories'),
    api('/api/catalog/services'),api('/api/catalog/formulas')]);
  const chipList=(items,kind)=>items.map(x=>`<span class="tag mut" style="font-size:11.5px;padding:4px 10px">${esc(x.name)}
    <span style="cursor:pointer;color:var(--danger);margin-left:4px" onclick="delCatalog('${kind}',${x.id})">✕</span></span>`).join(' ')||'<span class="muted" style="font-size:12px">бўш</span>';
  return `
  <div class="glass card mb">
    <h2 class="sec mb">Bo'limlar (materiallar uchun)</h2>
    <div class="row" style="flex-wrap:wrap;gap:6px;margin-bottom:10px">${chipList(cats,'categories')}</div>
    <div class="row"><input class="fld" id="cat_new" placeholder="Янги бўлим номи" style="flex:1"/>
      <button class="btn pri sm" onclick="addCatalog('categories','cat_new')">Қўшиш</button></div>
  </div>
  <div class="split mb">
    <div class="glass card">
      <h2 class="sec mb">Ўлчов бирликлари</h2>
      <div class="row" style="flex-wrap:wrap;gap:6px;margin-bottom:10px">${chipList(units,'units')}</div>
      <div class="row"><input class="fld" id="unit_new" placeholder="масалан: тонна" style="flex:1"/>
        <button class="btn pri sm" onclick="addCatalog('units','unit_new')">+</button></div>
    </div>
    <div class="glass card">
      <h2 class="sec mb">Ходим лавозимлари</h2>
      <div class="row" style="flex-wrap:wrap;gap:6px;margin-bottom:10px">${chipList(positions,'positions')}</div>
      <div class="row"><input class="fld" id="pos_new" placeholder="масалан: Босмачи" style="flex:1"/>
        <button class="btn pri sm" onclick="addCatalog('positions','pos_new')">+</button></div>
    </div>
  </div>
  <div class="glass card mb">
    <div class="between mb"><h2 class="sec">Ишлаб чиқариш хизматлари</h2>
      <button class="btn pri sm" onclick="serviceForm()">${icon('plus',13)} Xizmat</button></div>
    <div class="sec-sub">Laminatsiya, noj, tisneniye, lak turlari — narx, o'lchov va formula bilan</div>
    <table><thead><tr><th>Хизмат</th><th>Нарх</th><th>Бирлик</th><th>Формула</th><th></th></tr></thead><tbody>
    ${services.map(s=>`<tr><td><b>${esc(s.name)}</b></td><td>${money(s.price)}</td><td>${esc(s.unit)}</td>
      <td class="muted" style="font-family:monospace;font-size:11px">${esc(s.formula)}</td>
      <td class="row" style="gap:4px"><button class="btn sm ghost" onclick='serviceForm(${JSON.stringify(s).replace(/'/g,"&#39;")})'>✎</button>
      <button class="btn sm dngr" onclick="delService(${s.id})">✕</button></td></tr>`).join('')}
    </tbody></table>
  </div>
  <div class="glass card">
    <div class="between mb"><h2 class="sec">Hisob-kitob formulalari</h2>
      <button class="btn pri sm" onclick="formulaForm()">${icon('plus',13)} Formula</button></div>
    <div class="sec-sub">Sebestoyimost formulalari — o'zgaruvchilar: x·y (m), g=grammaj, q=qatlam, n=soni</div>
    <table><thead><tr><th>Nomi</th><th>Формула</th><th class="hide-m">Изоҳ</th><th></th></tr></thead><tbody>
    ${formulas.map(fo=>`<tr><td><b>${esc(fo.name)}</b></td>
      <td class="muted" style="font-family:monospace;font-size:12px">${esc(fo.expression)}</td>
      <td class="hide-m muted" style="font-size:11px">${esc(fo.description)}</td>
      <td><button class="btn sm ghost" onclick='formulaForm(${JSON.stringify(fo).replace(/'/g,"&#39;")})'>✎</button></td></tr>`).join('')}
    </tbody></table>
  </div>`;
}
async function addCatalog(kind,inputId){
  const name=f(inputId);if(!name)return;
  try{await post('/api/catalog/'+kind,{name});toast('o','check','Qo\'shildi',name);go('set');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function delCatalog(kind,id){
  try{await api('/api/catalog/'+kind+'/'+id,{method:'DELETE'});go('set');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
function serviceForm(s){
  s=s||{};
  modal(`<h2 class="sec mb">${s.id?'Xizmatni tahrirlash':'Yangi xizmat'}</h2>
  <label class="fl">Номи</label><input class="fld" id="sv_name" value="${esc(s.name||'')}" placeholder="масалан: Ламинация"/>
  <div class="grid g2" style="gap:8px">
    <div><label class="fl">Нарх (сўм)</label><input class="fld" id="sv_price" type="number" value="${s.price||0}"/></div>
    <div><label class="fl">Ўлчов</label><input class="fld" id="sv_unit" value="${esc(s.unit||'m²')}"/></div>
  </div>
  <label class="fl">Формула (x·y = ўлчам м, n = сони)</label><input class="fld" id="sv_formula" value="${esc(s.formula||'x*y*n')}"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveService(${s.id||0})">Сақлаш</button></div>`);
}
async function saveService(id){
  const body={name:f('sv_name'),price:+f('sv_price')||0,unit:f('sv_unit'),formula:f('sv_formula')};
  try{await(id?api('/api/catalog/services/'+id,{method:'PUT',body:JSON.stringify(body)}):post('/api/catalog/services',body));
    closeModal();toast('o','check','Сақланди',body.name);go('set');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function delService(id){
  try{await api('/api/catalog/services/'+id,{method:'DELETE'});go('set');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
function formulaForm(fo){
  fo=fo||{};
  modal(`<h2 class="sec mb">${fo.id?'Formulani tahrirlash':'Yangi formula'}</h2>
  <label class="fl">Номи</label><input class="fld" id="fm_name" value="${esc(fo.name||'')}" ${fo.id?'readonly':''}/>
  <label class="fl">Формула</label><input class="fld" id="fm_expr" value="${esc(fo.expression||'x*y*n')}" style="font-family:monospace"/>
  <label class="fl">Изоҳ</label><input class="fld" id="fm_desc" value="${esc(fo.description||'')}"/>
  <div class="muted" style="font-size:11px;margin-top:8px">Ruxsat: o'zgaruvchilar (x,y,g,q,n...), raqamlar, + − × ÷ ( )</div>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveFormula(${fo.id||0})">Сақлаш</button></div>`);
}
async function saveFormula(id){
  const body={name:f('fm_name'),expression:f('fm_expr'),description:f('fm_desc')};
  try{await(id?api('/api/catalog/formulas/'+id,{method:'PUT',body:JSON.stringify(body)}):post('/api/catalog/formulas',body));
    closeModal();toast('o','check','Сақланди',body.name);go('set');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
// Rol qiymati bazaga lotincha yoziladi, ekranda kirillcha ko'rinadi
const ROLE_OPTS=[["Rahbar","тўлиқ ҳуқуқ (сиз каби)"],["Menejer","мижозлар, смета, буюртма"],
  ["Sklad mudiri","омбор, кирим, инвентаризация"],["Sex boshlig'i","иш қайди, статуслар"],
  ["Buxgalter","молия, касса, ойлик, экспорт"]];
function userForm(){
  modal(`<h2 class="sec mb">Янги фойдаланувчи</h2>
  <label class="fl">Исм фамилия</label><input class="fld" id="u_name"/>
  <label class="fl">Логин</label><input class="fld" id="u_login" autocomplete="off"/>
  <label class="fl">Пароль (камида 4 белги)</label><input class="fld" id="u_pass" autocomplete="off"/>
  <label class="fl">Ҳуқуқ даражаси</label>
  <select class="fld" id="u_role">${ROLE_OPTS.map(([r,d])=>`<option value="${r}" ${r==='Menejer'?'selected':''}>${kir(r)} — ${d}</option>`).join('')}</select>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveUser()">Яратиш</button></div>`);
}
async function saveUser(){
  try{await post('/api/users',{name:f('u_name'),login:f('u_login'),password:f('u_pass'),role:f('u_role')});
    closeModal();toast('o','check','Фойдаланувчи яратилди',f('u_login')+' · '+kir(f('u_role')));go('set');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
function pwForm(id,login){
  modal(`<h2 class="sec mb">Parolni yangilash — ${login}</h2>
  <label class="fl">Янги пароль</label><input class="fld" id="np_pass"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="savePw(${id})">Сақлаш</button></div>`);
}
async function savePw(id){
  try{await post('/api/users/'+id+'/password',{password:f('np_pass')});
    closeModal();toast('o','check','Пароль янгиланди','');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function delUser(id,login){
  if(!confirm(login+' фойдаланувчисини ўчирасизми?'))return;
  try{await api('/api/users/'+id,{method:'DELETE'});toast('o','check','Ўчирилди',login);go('set');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
/* ---- Formulani yozayotganda darhol tekshirish ---- */
let _fchkTimer={};
function formulaTekshir(key){
  clearTimeout(_fchkTimer[key]);
  const box=document.getElementById('chk_'+key);
  if(box)box.innerHTML='<span class="muted">текширилмоқда…</span>';
  // har harfda so'rov yubormaslik uchun biroz kutamiz
  _fchkTimer[key]=setTimeout(async()=>{
    const expr=f('s_'+key);
    if(!expr){if(box)box.innerHTML='';return;}
    try{
      const r=await post('/api/finance/formula-check',{key,expr});
      if(!box)return;
      box.innerHTML=r.ok
        ? `<span style="color:var(--ok)">✅ Тўғри. Синов: ${esc(r.izoh)} → <b>${r.natija}</b></span>`
        : `<span style="color:var(--danger)">❌ ${esc(r.xato)}</span>`;
    }catch(e){ if(box)box.innerHTML=`<span style="color:var(--danger)">❌ ${esc(e.message)}</span>`; }
  },500);
}

async function saveSettings(){
  const values={};
  ['brak_percent','labor_per_box','color_cost_per_box','margin_vip','margin_standart','margin_yangi','min_stock_days','credit_mode', 'formula_m2', 'formula_sebestoimost', 'paper_grades']
    .forEach(k=>{const el=document.getElementById('s_'+k);if(el)values[k]=el.value;});
  try{await post('/api/finance/settings',{values});toast('o','check','Сақланди','Созламалар янгиланди');
  }catch(e){toast('d','alertic','Сақланмади — формулани текширинг',e.message);}
}

async function sysAdmin(){
  const s = await api('/api/finance/settings');
  return `
  <div class="glass card mb">
    <h2 class="sec mb">Тизим созламалари</h2>
    <div class="sec-sub">Барча ҳисоб-китоб кўрсаткичлари ва формулалари</div>
    
    <div class="grid g2" style="gap: 16px;">
      <div>
        <label class="fl">Технологик брак (%)</label>
        <input class="fld" id="s_brak_percent" value="${esc(s.brak_percent||'')}"/>
      </div>
      <div>
        <label class="fl">1 қутига иш ҳақи (сўм)</label>
        <input class="fld" id="s_labor_per_box" value="${esc(s.labor_per_box||'')}"/>
      </div>
      <div>
        <label class="fl">Флексо 1 ранг учун (сўм/дона)</label>
        <input class="fld" id="s_color_cost_per_box" value="${esc(s.color_cost_per_box||'')}"/>
      </div>
      <div>
        <label class="fl">VIP мижоз устамаси (%)</label>
        <input class="fld" id="s_margin_vip" value="${esc(s.margin_vip||'')}"/>
      </div>
      <div>
        <label class="fl">Стандарт мижоз устамаси (%)</label>
        <input class="fld" id="s_margin_standart" value="${esc(s.margin_standart||'')}"/>
      </div>
      <div>
        <label class="fl">Янги мижоз устамаси (%)</label>
        <input class="fld" id="s_margin_yangi" value="${esc(s.margin_yangi||'')}"/>
      </div>
    </div>

    <h2 class="sec mb" style="margin-top: 24px;">Калькулятор формулалари</h2>
    <div class="sec-sub">Таннарх ва майдон ҳисоблаш формулалари (фақат мантиқий амаллар)</div>
    
    <div class="alert w" style="margin-bottom:10px"><div class="ai">${icon('alertic',16)}</div>
      <div><b>Диққат — ҳарфларга эътибор беринг</b>
      <p>Фақат кичик ҳарф ишлатилади (<b>l</b>, катта <b>L</b> эмас). Каср сон нуқта билан
      ёзилади: <b>3.3</b> (вергул билан эмас: 3,3). Хато ёзсангиз — сақламайди ва сабабини айтади.</p></div></div>

    <label class="fl">Қути майдони (м²) формуласи</label>
    <div class="muted" style="font-size:11px; margin-bottom:4px;">
      Ҳарфлар: <b>l</b> — узунлик (мм) · <b>w</b> — кенглик (мм) · <b>h</b> — баландлик (мм)</div>
    <input class="fld" id="s_formula_m2" value="${esc(s.formula_m2||'((l+w)*2+40)*(h+w)/1000000')}"
      style="font-family:monospace" oninput="formulaTekshir('formula_m2')" />
    <div id="chk_formula_m2" style="font-size:11.5px;margin-top:3px"></div>

    <label class="fl" style="margin-top: 12px;">Таннарх формуласи</label>
    <div class="muted" style="font-size:11px; margin-bottom:4px;">
      Ҳарфлар: <b>m</b> — 1 қути м² · <b>p</b> — қоғоз нархи (сўм/м²) · <b>b</b> — брак коэффициенти (1.05)
      · <b>l</b> — иш ҳақи · <b>c</b> — ранглар сони · <b>k</b> — 1 ранг нархи</div>
    <input class="fld" id="s_formula_sebestoimost" value="${esc(s.formula_sebestoimost||'m*p*b+l+c*k')}"
      style="font-family:monospace" oninput="formulaTekshir('formula_sebestoimost')" />
    <div id="chk_formula_sebestoimost" style="font-size:11.5px;margin-top:3px"></div>

    <label class="fl" style="margin-top: 12px;">Қоғоз маркалари (вергул билан)</label>
    <div class="muted" style="font-size:11px; margin-bottom:4px;">Масалан: K1,K2,T-22,T-23</div>
    <input class="fld" id="s_paper_grades" value="${esc(s.paper_grades||'K1,K2,T-22,T-23')}" />

    <div class="row" style="margin-top:20px;">
      <button class="btn pri" onclick="saveSettings()">Сақлаш</button>
    </div>
  </div>`;
}

/* ---- Konstruktor: o'z bo'limlaringiz ---- */
async function renderConstructor(){
  const ss=await api('/api/sections');
  return `
  <div class="glass card mb">
    <h2 class="sec mb">Konstruktor — O'z bo'limlaringiz</h2>
    <div class="between mb">
    <div class="muted" style="font-size:12.5px">O'zingizga kerakli bo'lim yarating — masalan «Transport», «Stanoklar», «Qarz daftari»</div>
    <button class="btn pri sm" onclick="sectionForm()">${icon('plus',13)} Yangi bo'lim</button>
  </div>
  <div class="grid g3">
  ${ss.map(s=>`<div class="glass card" style="cursor:pointer" onclick="openSection(${s.id})">
    <div style="font-size:30px">${esc(s.icon)}</div>
    <b style="display:block;margin:8px 0 3px;font-size:15px">${esc(s.name)}</b>
    <div class="muted" style="font-size:11.5px">${s.records_count} ta yozuv · ${s.fields.length} ustun</div>
    <div class="row" style="margin-top:10px" onclick="event.stopPropagation()">
      <button class="btn sm" onclick="openSection(${s.id})">Очиш</button>
      ${dl('/api/sections/'+s.id+'/export.xlsx','Excel')}
      <button class="btn sm dngr" onclick="delSection(${s.id},'${esc(s.name)}')">✕</button>
    </div>
  </div>`).join('')||'<div class="glass card muted" style="grid-column:1/-1;text-align:center;padding:36px">Hozircha bo\'lim yo\'q — «Yangi bo\'lim» tugmasini bosing</div>'}
  </div></div>`;
}
const FTYPES=[['matn','Matn'],['raqam','Raqam'],['pul',"Pul (so'm)"],['sana','Sana']];
function fieldRow(i){
  return `<div class="row" style="margin-bottom:6px" id="frow${i}">
    <input class="fld" placeholder="Устун номи (масалан: Изоҳ)" id="fl_${i}" style="flex:2"/>
    <select class="fld" id="ft_${i}" style="flex:1">${FTYPES.map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select>
  </div>`;
}
function sectionForm(){
  window._fcount=2;
  modal(`<h2 class="sec mb">Янги бўлим яратиш</h2>
  <label class="fl">Бўлим номи</label><input class="fld" id="sc_name" placeholder="масалан: Транспорт харажатлари"/>
  <label class="fl">Белгиси</label>
  <select class="fld" id="sc_icon">${['📋','🚚','⚙️','🧾','📦','💰','🛠','📁'].map(e=>`<option>${e}</option>`).join('')}</select>
  <label class="fl">Устунлар</label>
  <div id="fieldsBox">${fieldRow(1)}${fieldRow(2)}</div>
  <button class="btn sm ghost" onclick="window._fcount++;document.getElementById('fieldsBox').insertAdjacentHTML('beforeend',fieldRow(window._fcount))">+ Ustun qo'shish</button>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveSection()">Яратиш</button></div>`);
}
async function saveSection(){
  const fields=[];
  for(let i=1;i<=window._fcount;i++){
    const l=f('fl_'+i);if(l)fields.push({label:l,type:f('ft_'+i)});
  }
  try{await post('/api/sections',{name:f('sc_name'),icon:f('sc_icon'),fields});
    closeModal();toast('o','check',"Bo'lim yaratildi",f('sc_name'));go('set');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function delSection(id,name){
  if(!confirm('«'+name+'» bo\'limini ichidagi hamma yozuvlari bilan o\'chirasizmi?'))return;
  try{await api('/api/sections/'+id,{method:'DELETE'});toast('o','check',"O'chirildi",name);go('set');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function openSection(id){
  const d=await api('/api/sections/'+id+'/records');
  const s=d.section;window._cursec=s;
  document.getElementById('ptitle').textContent=s.icon+' '+s.name;
  document.getElementById('psub').textContent='Konstruktor bo\'limi · '+d.records.length+' ta yozuv';
  const fmt=(fld,v)=>fld.type==='pul'&&v!==''?money(+v):(v??'');
  document.getElementById('content').innerHTML=`<div class="page show">
    <div class="between mb">
      <button class="btn sm" onclick="go('set')">← Orqaga</button>
      <div class="row">
        <button class="btn pri sm" onclick="recordForm()">${icon('plus',13)} Yozuv qo'shish</button>
        ${dl('/api/sections/'+s.id+'/export.xlsx','Excel')}
      </div>
    </div>
    <div class="glass card">
      <table><thead><tr><th>Сана</th>${s.fields.map(fl=>`<th>${esc(fl.label)}</th>`).join('')}<th></th></tr></thead><tbody>
      ${d.records.map(r=>`<tr><td class="muted" style="font-size:11px">${r.created_at.slice(0,10)}</td>
        ${s.fields.map(fl=>`<td>${esc(fmt(fl,r.data[fl.key]))}</td>`).join('')}
        <td>${ME.role==='Rahbar'?`<button class="btn sm ghost" onclick="delRecord(${s.id},${r.id})">✕</button>`:''}</td></tr>`).join('')||`<tr><td colspan="${s.fields.length+2}" class="muted">Ёзув йўқ</td></tr>`}
      </tbody></table>
    </div></div>`;
}
function recordForm(){
  const s=window._cursec;
  modal(`<h2 class="sec mb">${esc(s.icon)} ${esc(s.name)} — yangi yozuv</h2>
  ${s.fields.map(fl=>`<label class="fl">${esc(fl.label)}</label>
    <input class="fld" id="rf_${fl.key}" type="${fl.type==='sana'?'date':fl.type==='matn'?'text':'number'}"/>`).join('')}
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveRecord()">Сақлаш</button></div>`);
}
async function saveRecord(){
  const s=window._cursec;const data={};
  s.fields.forEach(fl=>{data[fl.key]=f('rf_'+fl.key)});
  try{await post('/api/sections/'+s.id+'/records',{data});
    closeModal();toast('o','check','Yozuv saqlandi','');openSection(s.id);
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function delRecord(sid,rid){
  try{await api('/api/sections/'+sid+'/records/'+rid,{method:'DELETE'});openSection(sid);
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}



/* ---- Foydalanuvchilar boshqaruvi ---- */
async function usersAdmin(){
  const us=await api('/api/users');
  return `
  <div class="glass card mb">
    <h2 class="sec">Фойдаланувчилар</h2>
    <div class="sec-sub">Ходимларингизга ўзингиз логин-пароль яратасиз ва ҳуқуқ белгилайсиз</div>
    <div style="display:flex;flex-direction:column;gap:8px">
    ${us.map(u=>`<div class="between" style="padding:9px 0;border-top:1px solid var(--hair)">
      <span><b>${esc(u.name)}</b>${u.is_me?' <span class="tag pri">siz</span>':''}
        <div class="muted" style="font-size:10.5px">${esc(u.login)} · ${kir(u.role)}</div></span>
      <span class="row" style="gap:4px">
        <button class="btn sm ghost" title="Parol" onclick="pwForm(${u.id},'${esc(u.login)}')">🔑</button>
        ${u.is_me?'':`<button class="btn sm dngr" onclick="delUser(${u.id},'${esc(u.login)}')">✕</button>`}
      </span></div>`).join('')}
    </div>
    <button class="btn pri" style="margin-top:12px" onclick="userForm()">+ Янги фойдаланувчи</button>
  </div>`;
}

/* ================= AI KO'RSATMASI (agent prompti) ==================
   Mijoz AI ning xatti-harakatini o'zi moslaydi — kod qayta joylanmaydi.

   Uch daraja ko'rsatiladi: kod (zaxira) -> platforma (biz) -> akkaunt
   (mijoz). Xavfsizlik qismi alohida ko'rsatiladi va TAHRIRLANMAYDI —
   AI raqam o'ylab topmasligi uchun.
   ==================================================================== */
async function aiKorsatmaAdmin(){
  let d;
  try{ d = await api('/api/agent/korsatma'); }
  catch(e){ return `<div class="glass card"><div class="muted">Ko'rsatmalar yuklanmadi: ${esc(e.message)}</div></div>`; }

  const manbaTag = m => ({
    kod:       '<span class="lnd-chip">Standart</span>',
    platforma: '<span class="lnd-chip ai">Platforma yangilagan</span>',
    akkaunt:   '<span class="lnd-chip ai">Siz o\'zgartirgansiz</span>',
  }[m] || '');

  const kartalar = d.agentlar.map(a => `
    <div class="glass card mb">
      <div class="row" style="justify-content:space-between;align-items:flex-start;gap:10px">
        <div>
          <h3 class="sec" style="margin-bottom:2px">${esc(a.nom)}</h3>
          <div class="muted" style="font-size:12px">${esc(a.izoh)}</div>
          <div class="muted" style="font-size:11px;margin-top:4px">
            Rollar: ${a.rollar.map(esc).join(', ')} ·
            Asboblar: ${a.asboblar.length} ta</div>
        </div>
        <div style="text-align:right">${manbaTag(a.manba)}</div>
      </div>

      <textarea class="fld" id="kors_${a.kalit}" rows="9"
        style="margin-top:12px;font-family:ui-monospace,Menlo,monospace;font-size:12px;line-height:1.55"
        oninput="korsUzunlik('${a.kalit}', ${a.chegara})">${esc(a.korsatma)}</textarea>

      <div class="row" style="justify-content:space-between;align-items:center;margin-top:8px">
        <div class="muted" style="font-size:11px" id="kors_len_${a.kalit}">
          ${a.uzunlik} / ${a.chegara} belgi</div>
        <div class="row" style="gap:6px">
          ${a.manba === 'kod' ? '' :
            `<button class="btn sm ghost" onclick="korsTikla('${a.kalit}')">Standartga qaytarish</button>`}
          <button class="btn sm pri" onclick="korsSaqla('${a.kalit}')">Saqlash</button>
        </div>
      </div>
    </div>`).join('');

  return `
  <div class="glass card mb">
    <h2 class="sec mb">AI yordamchilarining ko'rsatmasi</h2>
    <div class="muted" style="font-size:13px;line-height:1.6">
      Har yordamchi nima qilishini shu yerdan o'zgartirasiz — dastur
      qayta o'rnatilmaydi. Masalan atamalarni o'zingiznikiga moslashingiz
      mumkin («sklad mudiri» → «omborchi»).
    </div>
    <div style="margin-top:12px;padding:12px;border-radius:12px;
      background:linear-gradient(120deg,rgba(183,121,31,.1),rgba(183,121,31,.03));
      border:1px solid rgba(183,121,31,.25);font-size:12px;line-height:1.6">
      <b>Ko'rsatma har so'rovda AI ga yuboriladi</b> — u qancha uzun bo'lsa,
      AI shuncha qimmatga tushadi. Qisqa va aniq yozing.
    </div>
  </div>

  ${kartalar}

  <div class="glass card">
    <h3 class="sec" style="margin-bottom:6px">O'zgartirib bo'lmaydigan qism</h3>
    <div class="muted" style="font-size:12px;margin-bottom:10px">
      ${esc(d.izoh)}
    </div>
    <pre style="white-space:pre-wrap;font-size:11.5px;line-height:1.55;
      background:rgba(255,255,255,.4);padding:12px;border-radius:12px;
      border:1px solid var(--hair);margin:0">${esc(d.xavfsizlik_qismi)}</pre>
  </div>`;
}

function korsUzunlik(kalit, chegara){
  const el = document.getElementById('kors_' + kalit);
  const out = document.getElementById('kors_len_' + kalit);
  if(!el || !out) return;
  const n = el.value.length;
  out.textContent = `${n} / ${chegara} belgi`;
  out.style.color = n > chegara ? 'var(--danger)' : '';
}

async function korsSaqla(kalit){
  const el = document.getElementById('kors_' + kalit);
  try{
    await api('/api/agent/korsatma/' + kalit, 'PUT', {korsatma: el.value});
    toast('o','check','Saqlandi','AI yangi ko\'rsatma bilan ishlaydi');
    openSetTab('ai');
  }catch(e){ toast('d','alertic','Saqlanmadi', e.message); }
}

async function korsTikla(kalit){
  try{
    await api('/api/agent/korsatma/' + kalit, 'DELETE');
    toast('o','check','Qaytarildi','Standart ko\'rsatma tiklandi');
    openSetTab('ai');
  }catch(e){ toast('d','alertic','Bajarilmadi', e.message); }
}
