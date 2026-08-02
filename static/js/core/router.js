/* ================= Navigatsiya (rolga qarab) ================= */
// Tartib foydalanish statistikasiga qarab: amallarning ~75% i — yangi zakaz va
// mijoz qo'shish. Shuning uchun eng ko'p ishlatiladigan bo'limlar boshida turadi.
const NAV=[
  {p:'calc',t:t('smeta'),i:'calc',roles:['Rahbar','Menejer']},
  {p:'orders',t:t('orders'),i:'cart',roles:['Rahbar','Menejer',"Sex boshlig'i",'Sklad mudiri','Buxgalter']},
  {p:'crm',t:t('clients'),i:'users',roles:['Rahbar','Menejer','Buxgalter']},
  {p:'dash',t:t('dash'),i:'dash',roles:['Rahbar','Menejer','Buxgalter']},
  {p:'wh',t:t('wh'),i:'box',roles:['Rahbar','Sklad mudiri',"Sex boshlig'i"]},
  {p:'mat',t:t('mats'),i:'boxIn',roles:['Rahbar','Sklad mudiri']},
  {p:'zakup',t:t('zakup'),i:'boxIn',roles:['Rahbar','Sklad mudiri','Buxgalter']},
  {p:'hr',t:t('hr'),i:'hr',roles:['Rahbar',"Sex boshlig'i",'Buxgalter']},
  {p:'fin',t:t('fin'),i:'wallet',roles:['Rahbar','Buxgalter','Menejer']},
  {p:'kassa',t:t('kassa'),i:'wallet',roles:['Rahbar','Buxgalter']},
  {p:'exp',t:t('exp'),i:'doc',roles:['Rahbar','Buxgalter',"Sex boshlig'i"]},
  {p:'set',t:t('set'),i:'gear',roles:['Rahbar']},
  {p:'help',t:'Йўриқнома',i:'doc',roles:['Rahbar','Menejer',"Sex boshlig'i",'Sklad mudiri','Buxgalter']}
];
const META={
  dash:[t('dash'), t('dash_sub')],
  crm:[t('clients'), t('clients_sub')],
  calc:[t('smeta'), t('smeta_sub')],
  orders:[t('orders'), t('orders_sub')],
  wh:[t('wh'), t('wh_sub')],
  hr:[t('hr'), t('hr_sub')],
  fin:[t('fin'), t('fin_sub')],
  mat:[t('mats'), t('mats_sub')],
  zakup:[t('zakup'), t('zakup_sub')],
  kassa:[t('kassa'), t('kassa_sub')],
  exp:[t('exp'), t('exp_sub')],
  set:[t('set'), t('set_sub')],
  help:['Йўриқнома', 'Пул киритилса — қаерда кўринади']
};
let PAGE='dash';
function allowedNav(){return NAV.filter(n=>ME.role==='Rahbar'||n.roles.includes(ME.role));}
function renderNav(){
  const items=allowedNav();
  document.getElementById('nav').innerHTML=items.map(n=>
    `<a class="${n.p===PAGE?'active':''}" onclick="go('${n.p}')"><span class="ic">${icon(n.i)}</span><span>${n.t}</span></a>`).join('');
  const main3=items.slice(0,3);
  const rest=items.slice(3);
  const link=n=>`<a class="${n.p===PAGE?'active':''}" onclick="go('${n.p}')">${icon(n.i,19)}<span>${n.t.split(' ')[0]}</span></a>`;
  document.getElementById('bottomNav').innerHTML=
    main3.slice(0,2).map(link).join('')
    +`<a onclick="quickSheet()" style="flex:0 0 62px"><span class="fab">${icon('plus',24)}</span></a>`
    +(main3[2]?link(main3[2]):'')
    +(rest.length?`<a class="${rest.some(n=>n.p===PAGE)?'active':''}" onclick="moreNav()">${icon('dash',19)}<span>Яна</span></a>`:'');
  window._restNav=rest;
}
// Tartib — haqiqiy foydalanish statistikasi bo'yicha (audit jurnalidan):
// zakaz yaratish 68, yangi mijoz 43, pul berish 40, xarajat 39, to'lov 34,
// ish qaydi 0, xomashyo kirim 0 marta. Eng ko'p ishlatilgani yuqorida turadi.
const QUICK=[
  {t:'Янги заказ',d:'смета ҳисоблаш',i:'🧮',roles:['Rahbar','Menejer'],run:()=>{closeModal();go('calc')}},
  {t:'Янги мижоз',d:'мижоз қўшиш',i:'👤',roles:['Rahbar','Menejer'],run:()=>qaClient()},
  {t:'Пул бериш',d:'ходимга аванс',i:'🤝',roles:['Rahbar','Buxgalter',"Sex boshlig'i"],run:()=>qaPayEmp()},
  {t:'Харажат ёзиш',d:'клей, скотч…',i:'🧾',roles:['Rahbar','Buxgalter',"Sex boshlig'i"],run:()=>{closeModal();go('exp');setTimeout(()=>{if(window.expAddModal)expAddModal()},350)}},
  {t:"Тўлов олиш",d:'мижоздан пул',i:'💵',roles:['Rahbar','Menejer','Buxgalter'],run:()=>qaPay()},
  {t:'Иш қайди',d:'ходим нечта қути кесди',i:'✂️',roles:['Rahbar',"Sex boshlig'i"],run:()=>qaWork()},
  {t:'Хомашё кирим',d:'қоғоз келди',i:'📥',roles:['Rahbar','Sklad mudiri'],run:()=>qaLot()},
];
function quickActions(){return QUICK.filter(q=>ME.role==='Rahbar'||q.roles.includes(ME.role));}
function quickSheet(){
  modal(`<h2 class="sec mb">Тезкор амаллар</h2>
  <div class="qa-grid">
  ${quickActions().map((q,i)=>`<div class="qa" onclick="QUICK[${QUICK.indexOf(q)}].run()">
    <span class="qi">${q.i}</span><span>${q.t}</span><span class="muted" style="font-size:10px;font-weight:500">${q.d}</span></div>`).join('')}
  </div>`);
}
async function qaWork(){closeModal();if(!window._emps)window._emps=await api('/api/hr/employees');hrWorkModal();}
async function qaPayEmp(){closeModal();if(!window._emps)window._emps=await api('/api/hr/employees');hrPayModal();}
async function qaLot(){closeModal();if(!window._sups)window._sups=(await api('/api/warehouse/suppliers'));lotForm();}
async function qaPay(){closeModal();if(!window._clients)window._clients=await api('/api/clients');payForm(null);}
async function qaClient(){closeModal();if(window.crmAddModal)crmAddModal();else go('crm');}
function moreNav(){
  modal(`<h2 class="sec mb">Бошқа бўлимлар</h2>
  <div style="display:flex;flex-direction:column;gap:6px">
  ${window._restNav.map(n=>`<button class="btn" style="justify-content:flex-start;width:100%" onclick="closeModal();go('${n.p}')">${icon(n.i,17)} ${n.t}</button>`).join('')}
  </div>`);
}
let NAVSEQ=0;
function _renderPage(p){
  PAGE=p;renderNav();
  const seq=++NAVSEQ;
  const[t,s]=META[p];document.getElementById('ptitle').textContent=t;document.getElementById('psub').textContent=s;
  document.getElementById('content').innerHTML='<div class="muted" style="padding:30px;text-align:center">Юкланмоқда…</div>';
  PAGES[p]().then(html=>{if(seq!==NAVSEQ)return;
      // sahifa o'zi render qilgan bo'lsa (html qaytarmasa) — tegmaymiz
      if(html!==undefined&&html!==null)document.getElementById('content').innerHTML=`<div class="page show">${html}</div>`;
      if(window._postRender){const fn=window._postRender;window._postRender=null;fn();}})
    .catch(e=>{if(seq!==NAVSEQ)return;document.getElementById('content').innerHTML=`<div class="glass card">${esc(e.message)}</div>`;});
}

function go(p) {
  window.location.hash = '/' + p;
}

window.addEventListener('hashchange', () => {
  if (!ME) return; // Not logged in
  let p = window.location.hash.replace('#/', '');
  if (!p || !PAGES[p]) {
    const items = allowedNav();
    p = items[0].p;
    window.location.hash = '/' + p;
    return;
  }
  _renderPage(p);
});

function enterApp(){
  document.getElementById('loginScreen').style.display='none';
  document.getElementById('app').classList.add('on');
  document.getElementById('uname').textContent=ME.name;
  document.getElementById('urole').textContent='· '+kir(ME.role);
  document.getElementById('uav').textContent=ME.name[0];

  // AI agent paneli — faqat Rahbarga. U butun tizim konfiguratsiyasini
  // o'zgartira oladi, shuning uchun menejer/sklad ochmasligi kerak.
  if(ME.role==='Rahbar' && typeof agentPanelYasa==='function'){
    agentPanelYasa();
    agentYangiSuhbat();
  }
  
  // Hash routing
  let p = window.location.hash.replace('#/', '');
  const items = allowedNav();
  if (!p || !PAGES[p] || !items.find(x => x.p === p)) {
    p = items[0].p;
    window.location.hash = '/' + p;
  } else {
    _renderPage(p);
  }

  loadFirms();
}

