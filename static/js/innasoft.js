/* Korporativ sayt: hozircha qasddan sokin karkas.
   Keyingi bosqichda scroll, sahna va mikro-animatsiyalar shu faylga qo'shiladi. */
document.querySelectorAll('[data-product]').forEach(card=>{
  card.addEventListener('click',()=>{
    // Analitika ulanmaguncha tashqi kuzatuv yo'q: foydalanuvchi darrov
    // mahsulot yoki kerakli bo'limga o'tadi.
  });
});

/* Mobil BrandHeader: navigatsiya holati URL yoki mahsulot mantiqiga
   bog'lanmaydi. Escape va bo'lim tanlash uni yopadi. */
const menuButton=document.querySelector('.menu-toggle');
const siteNav=document.getElementById('siteNav');
function siteMenuYop(){
  if(!menuButton||!siteNav)return;
  menuButton.setAttribute('aria-expanded','false');
  siteNav.classList.remove('open');
  document.body.classList.remove('menu-open');
}
if(menuButton&&siteNav){
  menuButton.addEventListener('click',()=>{
    const ochiq=menuButton.getAttribute('aria-expanded')==='true';
    menuButton.setAttribute('aria-expanded',String(!ochiq));
    siteNav.classList.toggle('open',!ochiq);
    document.body.classList.toggle('menu-open',!ochiq);
  });
  siteNav.querySelectorAll('a').forEach(a=>a.addEventListener('click',siteMenuYop));
  document.addEventListener('keydown',e=>{if(e.key==='Escape')siteMenuYop();});
}
