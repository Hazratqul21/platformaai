/* ================= Auth ================= */
async function doLogin(){
  try{
    const r=await fetch(API+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({login:document.getElementById('lg').value.trim(),password:document.getElementById('pw').value})});
    if(!r.ok){const e=await r.json();return toast('d','alertic','Хатолик',e.detail||'Login xato');}
    const d=await r.json();TOKEN=d.token;ME=d;
    localStorage.setItem('tizim_token',TOKEN);localStorage.setItem('tizim_me',JSON.stringify(d));
    enterApp();
  }catch(e){toast('d','alertic','Server bilan aloqa yo\'q',e.message);}
}
async function logout(){
  try{if(TOKEN)await fetch(API+'/api/auth/logout',{method:'POST',headers:{'Authorization':'Bearer '+TOKEN}});}catch(e){}
  localStorage.removeItem('tizim_token');localStorage.removeItem('tizim_me');TOKEN='';location.reload();
}

