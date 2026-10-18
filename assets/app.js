/* Super Street Rentals prototype front end - vanilla JS, no build step. */
(function(){
const C = window.SSR_CONFIG || {};
const $ = (s, el=document) => el.querySelector(s);
const $$ = (s, el=document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmtET = iso => iso ? new Date(iso).toLocaleString("en-US",{timeZone:"America/New_York",weekday:"short",month:"short",day:"numeric",hour:"numeric",minute:"2-digit"})+" ET" : "TBD";
const money = n => n==null ? "" : "$"+Number(n).toLocaleString("en-US");
const page = document.body.dataset.page;

/* ---------- layout ---------- */
const NAV = [["index.html","Home"],["exotic.html","Exotic Auctions"],["ex-rental.html","Ex-Rental Auctions"],["rent.html","Rent a Car"],
             ["list-your-car.html","List Your Car"],["how-it-works.html","How It Works"],["faq.html","FAQ"],["contact.html","Contact"]];
function layout(){
  const cur = location.pathname.split("/").pop() || "index.html";
  document.body.insertAdjacentHTML("afterbegin", `
  <div class="ph-banner">PROTOTYPE - demo rental data, forms not yet connected to a backend. No bids are placed by this site.</div>
  <header class="nav"><div class="wrap">
    <a class="logo" href="index.html"><img class="brand-logo" src="assets/logo.svg" alt="Super Street Rentals"></a>
    ${NAV.map(([h,t])=>`<a class="l ${cur===h?"on":""}" href="${h}">${t}</a>`).join("")}
    <a class="btn sm" href="request.html">Request a Car</a>
  </div></header>`);
  document.body.insertAdjacentHTML("beforeend", `
  <footer><div class="wrap">
   <p><b>${esc(C.brandName)}</b> (placeholder) - independent vehicle-buying broker & peer-to-peer rental marketplace prototype.
   Auction listings are aggregated from third-party public pages for information only; we are not affiliated with Bring a Trailer, PCARMARKET, IAA, Copart or any auction house.
   Bids and end times change constantly - always confirm on the source listing. Final terms, licensing and insurance TBD.</p>
   <p><a href="host-dashboard.html">Host dashboard (mock)</a> · <a href="faq.html">FAQ</a> · <a href="contact.html">Contact</a> · Legal/terms: TBD</p>
  </div></footer>
  <div class="modal" id="modal"><div class="box" id="modalBox"></div></div>`);
  $("#modal").addEventListener("click", e => { if (e.target.id==="modal") closeModal(); });
}
function openModal(html){ $("#modalBox").innerHTML = html + `<p><button class="btn alt sm" onclick="SSR.closeModal()">Close</button></p>`; $("#modal").classList.add("open"); }
function closeModal(){ $("#modal").classList.remove("open"); }

/* ---------- countdowns ---------- */
function tick(){
  const now = Date.now();
  $$(".cd[data-end]").forEach(el=>{
    const end = Date.parse(el.dataset.end); if (!end){ el.textContent="Date TBD"; return; }
    let s = Math.floor((end-now)/1000);
    if (s<=0){ el.textContent="Ended / live now"; el.classList.add("soon"); return; }
    const d=Math.floor(s/86400); s%=86400; const h=Math.floor(s/3600); s%=3600; const m=Math.floor(s/60); s%=60;
    el.textContent = (d?d+"d ":"")+String(h).padStart(2,"0")+"h "+String(m).padStart(2,"0")+"m "+String(s).padStart(2,"0")+"s";
    el.classList.toggle("soon", end-now < 6*3600e3);
  });
}
setInterval(tick, 1000);

/* ---------- auctions ---------- */
let FEED = null;
async function loadFeed(){
  if (FEED) return FEED;
  const r = await fetch(C.feedUrl + "?t=" + Date.now()); FEED = await r.json(); return FEED;
}
function auctionCard(x){
  const img = x.image_url ? `style="background-image:url('${esc(x.image_url)}')"` : "";
  return `<div class="card">
   <div class="img" ${img}>${x.image_url?"":'<div class="noimg">No public photo</div>'}<span class="badge">${esc(x.source.replace(" (Insurance Auto Auctions)",""))}</span>
   ${x.category==="rental"?'<span class="badge r">Ex-rental</span>':""}</div>
   <div class="b"><h3>${esc(x.title)}</h3>
    <div class="meta">${esc(x.location||"")}${x.mileage?" · "+esc(typeof x.mileage==="number"?x.mileage.toLocaleString()+" mi":x.mileage):""}${x.damage?" · "+esc(x.damage):""}</div>
    <div class="row"><span class="${x.current_bid!=null?"bid":"meta"}">${esc(x.current_bid!=null?(x.current_bid_text||money(x.current_bid)):(x.current_bid_text||"See listing"))}</span></div>
    <div class="row"><span class="meta">Ends ${esc(fmtET(x.end_time_utc))}${x.end_time_is_approx?" (approx)":""}</span><span class="cd" data-end="${esc(x.end_time_utc)}"></span></div>
    <div class="row" style="margin-top:auto">
      <button class="btn alt sm" onclick="SSR.detail('${esc(x.id)}')">Details</button>
      <a class="btn alt sm" href="${esc(x.url)}" target="_blank" rel="noopener nofollow">Source ↗</a>
      <a class="btn sm" href="request.html?listing=${encodeURIComponent(x.id)}">Request this car</a></div>
   </div></div>`;
}
async function detail(id){
  const f = await loadFeed(); const x = f.listings.find(l=>l.id===id); if(!x) return;
  const rows = [["Site",x.source],["Current bid",x.current_bid_text||money(x.current_bid)],["Ends (ET)",fmtET(x.end_time_utc)+(x.end_time_is_approx?" (approx)":"")],
    ["Location",x.location],["Mileage",x.mileage],["Damage",x.damage],["Title",x.title_status],["Rental evidence",x.rental_evidence],
    ["How to buy",x.access],["Notes",x.notes],["Data fetched",x.fetched_at_et]].filter(r=>r[1]);
  openModal(`<h2>${esc(x.title)}</h2>${x.image_url?`<img src="${esc(x.image_url)}" alt="" style="border-radius:10px">`:""}
   <p class="cd" data-end="${esc(x.end_time_utc)}"></p>
   <table class="kv">${rows.map(r=>`<tr><td>${esc(r[0])}</td><td>${esc(r[1])}</td></tr>`).join("")}</table>
   <p><a class="btn" href="request.html?listing=${encodeURIComponent(x.id)}">Request this car</a> <a class="btn alt" target="_blank" rel="noopener nofollow" href="${esc(x.url)}">View on ${esc(x.source)} ↗</a></p>
   <p class="note">We never bid without your written max-bid authorization and deposit. Photos/data © the source site.</p>`);
  tick();
}
async function auctionsPage(cat){
  const f = await loadFeed();
  const all = f.listings.filter(l=>l.category===cat);
  $("#updated").textContent = `Feed updated ${f.generated_at_et} · ${all.length} listings`;
  const makes = [...new Set(all.map(l=>l.make).filter(Boolean))].sort();
  const sites = [...new Set(all.map(l=>l.source))].sort();
  $("#fMake").innerHTML = `<option value="">All makes</option>`+makes.map(m=>`<option>${esc(m)}</option>`).join("");
  $("#fSite").innerHTML = `<option value="">All sites</option>`+sites.map(m=>`<option>${esc(m)}</option>`).join("");
  const render = ()=>{
    const mk=$("#fMake").value, st=$("#fSite").value, q=$("#fQ").value.toLowerCase(), win=$("#fEnd").value, sp=$("#fSporty")?.checked;
    const now=Date.now();
    let L = all.filter(l=>(!mk||l.make===mk)&&(!st||l.source===st)&&(!q||l.title.toLowerCase().includes(q))&&(!sp||l.sporty));
    if (win) L = L.filter(l=>l.end_time_utc && Date.parse(l.end_time_utc)-now < +win*3600e3);
    const sort=$("#fSort").value;
    L.sort((a,b)=> sort==="bid" ? (b.current_bid||0)-(a.current_bid||0) : (Date.parse(a.end_time_utc)||9e15)-(Date.parse(b.end_time_utc)||9e15));
    $("#count").textContent = `${L.length} shown`;
    $("#grid").innerHTML = L.slice(0,300).map(auctionCard).join("") || "<p>No listings match.</p>";
    tick();
  };
  $$(".filters input,.filters select").forEach(el=>el.addEventListener("input",render));
  render();
}
async function homeFeatured(){
  try{ const f = await loadFeed(); const now=Date.now();
    const ex = f.listings.filter(l=>l.category==="exotic"&&l.current_bid&&Date.parse(l.end_time_utc)>now).sort((a,b)=>Date.parse(a.end_time_utc)-Date.parse(b.end_time_utc)).slice(0,6);
    $("#featured").innerHTML = ex.map(auctionCard).join(""); $("#updated").textContent=`Live feed updated ${f.generated_at_et}`; tick();
  }catch(e){ $("#featured").innerHTML="<p>Feed unavailable.</p>"; }
}

/* ---------- forms (Formspree or mailto fallback) ---------- */
function wireForm(form, subject){
  form.addEventListener("submit", async e=>{
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    data._subject = subject; data.page = location.href;
    const out = form.querySelector(".out");
    if (C.formEndpoint){
      try{ const r = await fetch(C.formEndpoint,{method:"POST",headers:{"Accept":"application/json","Content-Type":"application/json"},body:JSON.stringify(data)});
        out.innerHTML = r.ok ? '<div class="note">Thanks! We received your request and will contact you shortly.</div>' : '<div class="note warn">Submission failed - please email us.</div>';
        if (r.ok) form.reset(); return; }catch(err){}
    }
    const body = Object.entries(data).map(([k,v])=>`${k}: ${v}`).join("\n");
    location.href = `mailto:${C.leadEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    out.innerHTML = '<div class="note">No form backend configured yet (placeholder) - opening your email app instead.</div>';
  });
}
async function requestPage(){
  const id = new URLSearchParams(location.search).get("listing");
  const form = $("#leadForm"); wireForm(form, "Broker request" + (id?" - "+id:""));
  if (id){ form.listing_id.value = id;
    try{ const f = await loadFeed(); const x=f.listings.find(l=>l.id===id);
      if (x){ form.listing_url.value = x.url; $("#picked").innerHTML = `<div class="grid">${auctionCard(x)}</div>`; tick(); } }catch(e){}
  }
}

/* ---------- P2P rentals (DEMO stub data) ---------- */
let CARS=null;
async function loadCars(){ if(CARS) return CARS; CARS = await (await fetch(C.stubCarsUrl)).json(); return CARS; }
function carCard(c){
  return `<div class="card"><div class="img" style="background-image:url('${esc(c.photo||"")}')"><div class="noimg">${c.photo?"":"Photo placeholder"}</div>
   <span class="badge">${esc(c.city)}</span><span class="badge r">DEMO</span></div>
   <div class="b"><h3>${esc(c.year+" "+c.make+" "+c.model)}</h3><div class="meta">Host: ${esc(c.host)} · ★ ${c.rating} (${c.trips} trips)</div>
   <div class="row"><span class="bid">${money(c.price_per_day)}/day</span><span class="meta">${esc(c.miles_included)} mi/day incl.</span></div>
   <a class="btn sm" href="car.html?id=${encodeURIComponent(c.id)}" style="margin-top:auto">View & request</a></div></div>`;
}
const isBooked = (c, d) => c.booked.some(([a,b]) => d>=a && d<=b);
async function rentPage(){
  const cars = await loadCars();
  const cities=[...new Set(cars.map(c=>c.city))].sort(), makes=[...new Set(cars.map(c=>c.make))].sort();
  $("#rCity").innerHTML='<option value="">Any city</option>'+cities.map(c=>`<option>${esc(c)}</option>`).join("");
  $("#rMake").innerHTML='<option value="">Any make</option>'+makes.map(c=>`<option>${esc(c)}</option>`).join("");
  const render=()=>{
    const city=$("#rCity").value, mk=$("#rMake").value, s=$("#rStart").value, e=$("#rEnd").value, max=+$("#rMax").value||1e9;
    const L=cars.filter(c=>(!city||c.city===city)&&(!mk||c.make===mk)&&c.price_per_day<=max&&
      (!s||!e||!c.booked.some(([a,b])=>!(e<a||s>b))));
    $("#cars").innerHTML=L.map(carCard).join("")||"<p>No demo cars match those dates/filters.</p>";
  };
  $$(".filters input,.filters select").forEach(el=>el.addEventListener("input",render)); render();
}
function calendar(c, months=2){
  let html=""; const t=new Date(); 
  for(let m=0;m<months;m++){
    const first=new Date(t.getFullYear(), t.getMonth()+m, 1), days=new Date(first.getFullYear(), first.getMonth()+1, 0).getDate();
    html+=`<h4>${first.toLocaleString("en-US",{month:"long",year:"numeric"})}</h4><div class="cal">`+["S","M","T","W","T","F","S"].map(d=>`<div class="h">${d}</div>`).join("");
    for(let i=0;i<first.getDay();i++) html+='<div class="h"></div>';
    for(let d=1;d<=days;d++){ const iso=`${first.getFullYear()}-${String(first.getMonth()+1).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
      html+=`<div class="${isBooked(c,iso)?"x":""}" title="${isBooked(c,iso)?"Booked":"Available"}">${d}</div>`; }
    html+="</div>";
  }
  return html;
}
async function carPage(){
  const cars=await loadCars(); const id=new URLSearchParams(location.search).get("id"); const c=cars.find(x=>x.id===id)||cars[0];
  $("#car").innerHTML=`<div class="grid" style="grid-template-columns:1.3fr 1fr"><div>
    <div class="card"><div class="img" style="background-image:url('${esc(c.photo||"")}')"><div class="noimg">Photo placeholder (host uploads to Supabase Storage)</div><span class="badge r">DEMO LISTING</span></div></div>
    <h1>${esc(c.year+" "+c.make+" "+c.model)}</h1><p class="meta">${esc(c.city)} · Host ${esc(c.host)} · ★ ${c.rating} (${c.trips} trips)</p><p>${esc(c.description)}</p>
    <table class="kv"><tr><td>Price</td><td>${money(c.price_per_day)}/day</td></tr><tr><td>Miles included</td><td>${c.miles_included}/day</td></tr>
    <tr><td>Security deposit</td><td>${money(c.deposit)}</td></tr><tr><td>Min renter age</td><td>${c.min_age}</td></tr><tr><td>Features</td><td>${esc(c.features.join(", "))}</td></tr></table>
    <h3>Availability</h3><p class="meta">Red = booked (demo data)</p>${calendar(c)}</div>
   <div><form class="f" id="bookForm" style="grid-template-columns:1fr">
    <h3 class="full" style="margin:0">Request to book</h3><input type="hidden" name="car_id" value="${esc(c.id)}">
    <label>Start date<input type="date" name="start" required></label><label>End date<input type="date" name="end" required></label>
    <label>Full name<input name="name" required></label><label>Email<input type="email" name="email" required></label><label>Phone<input name="phone" required></label>
    <label>Driver age<input type="number" name="age" min="18" required></label>
    <div id="quote" class="note">Pick dates to see an estimate.</div>
    <label><span><input type="checkbox" required> I understand this is a booking <b>request</b>; the host must approve and ID/insurance verification is required before pickup.</span></label>
    <button class="btn">Send booking request</button><div class="out"></div>
    <p class="meta">MVP: requests are emailed and handled manually. Later: Stripe Connect payment + Stripe Identity check.</p></form></div></div>`;
  const f=$("#bookForm");
  const q=()=>{ const s=f.start.value,e=f.end.value; if(!s||!e||e<s) return;
    const days=Math.round((Date.parse(e)-Date.parse(s))/864e5)+1, clash=c.booked.some(([a,b])=>!(e<a||s>b));
    const sub=days*c.price_per_day, fee=Math.round(sub*0.10);
    $("#quote").innerHTML = clash?'<b style="color:var(--accent)">Those dates overlap a booking.</b>':
      `${days} day(s) × ${money(c.price_per_day)} = ${money(sub)}<br>Trip fee (example 10%): ${money(fee)}<br><b>Est. total ${money(sub+fee)}</b> + refundable deposit ${money(c.deposit)}<br><span class="meta">Example pricing only.</span>`; };
  f.start.addEventListener("input",q); f.end.addEventListener("input",q);
  wireForm(f, "Booking request - "+c.id);
}
async function dashboardPage(){
  const cars=(await loadCars()).filter(c=>c.host==="Alex R."); 
  $("#myCars").innerHTML=cars.map(carCard).join("");
  const reqs=[["REQ-1001","Jordan P.",cars[0]?.model,"2026-11-06 → 2026-11-08","Pending"],["REQ-1002","Sam T.",cars[1]?.model||cars[0]?.model,"2026-11-14 → 2026-11-15","Approved"],["REQ-0997","Chris L.",cars[0]?.model,"2026-10-10 → 2026-10-12","Completed"]];
  $("#reqs").innerHTML=reqs.map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td><td>${esc(r[2])}</td><td>${r[3]}</td><td>${r[4]}</td>
    <td>${r[4]==="Pending"?'<button class="btn sm" onclick="this.closest(\'tr\').cells[4].textContent=\'Approved (mock)\'">Approve</button> <button class="btn alt sm" onclick="this.closest(\'tr\').cells[4].textContent=\'Declined (mock)\'">Decline</button>':""}</td></tr>`).join("");
}

window.SSR={detail,closeModal};
layout();
const init = {home:homeFeatured, exotic:()=>auctionsPage("exotic"), rental:()=>auctionsPage("rental"), request:requestPage, rent:rentPage, car:carPage, dashboard:dashboardPage,
  host:()=>wireForm($("#hostForm"),"New host application"), contact:()=>wireForm($("#contactForm"),"Website contact")}[page];
if (init) init();
})();
