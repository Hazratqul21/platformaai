/* ================= Start ================= */
if(TOKEN&&ME){
  fetch(API+'/api/auth/me',{headers:{'Authorization':'Bearer '+TOKEN}})
    .then(r=>r.ok?enterApp():logout()).catch(()=>{});
}
document.getElementById('pw').addEventListener('keydown',e=>{if(e.key==='Enter')doLogin();});
