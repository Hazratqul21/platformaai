/* ================= Auth ================= */
async function doLogin(){
  try{
    const r=await fetch(API+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({login:document.getElementById('lg').value.trim(),password:document.getElementById('pw').value})});
    if(!r.ok){const e=await r.json();return toast('d','alertic','Хатолик',e.detail||'Login xato');}
    const d=await r.json();TOKEN=d.token;ME=d;
    localStorage.setItem('tizim_token',TOKEN);localStorage.setItem('tizim_me',JSON.stringify(d));
    // Standart parol bilan kirildi — tizim ochilmaydi. Backend ham
    // qulflab turadi, bu oyna faqat foydalanuvchiga yo'l ko'rsatadi.
    if(d.parol_almashtirilsin){ parolMajburiy(); return; }
    enterApp();
  }catch(e){toast('d','alertic','Server bilan aloqa yo\'q',e.message);}
}
async function logout(){
  try{if(TOKEN)await fetch(API+'/api/auth/logout',{method:'POST',headers:{'Authorization':'Bearer '+TOKEN}});}catch(e){}
  localStorage.removeItem('tizim_token');localStorage.removeItem('tizim_me');TOKEN='';location.reload();
}


/* ---- Биринчи кириш: стандарт паролни алмаштириш мажбурий ---- */
function parolMajburiy(){
  modal(`<h2 class="sec">Паролни алмаштиринг</h2>
  <div class="muted" style="font-size:12px;margin:4px 0 10px;line-height:1.5">
    Тизимга стандарт пароль (<b>1234</b>) билан кирилди. Бу ерда пул, қарз ва
    мижозлар базаси турибди — янги пароль ўрнатмагунингизча тизим очилмайди.</div>
  <label class="fl">Эски пароль</label>
  <input class="fld" id="pm_old" type="password" value="1234"/>
  <label class="fl">Янги пароль (камида 8 белги)</label>
  <input class="fld" id="pm_new" type="password" autocomplete="new-password"/>
  <label class="fl">Янги паролни такрорланг</label>
  <input class="fld" id="pm_new2" type="password" autocomplete="new-password"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn pri" onclick="parolMajburiySaqla()">Сақлаш ва кириш</button></div>`,
    false, true);
}
async function parolMajburiySaqla(){
  const yangi=f('pm_new'), takror=f('pm_new2');
  if(yangi.length<8) return toast('w','alertic','Қисқа','Камида 8 белги');
  if(yangi!==takror) return toast('w','alertic','Мос эмас','Иккала пароль бир хил бўлсин');
  try{
    await post('/api/auth/change-password',{old_password:f('pm_old'),new_password:yangi});
    closeModal();
    ME.parol_almashtirilsin=false;
    localStorage.setItem('tizim_me',JSON.stringify(ME));
    toast('o','check','Пароль ўрнатилди','Энди тизим очиқ');
    enterApp();
  }catch(e){ toast('d','alertic','Сақланмади',e.message); }
}
