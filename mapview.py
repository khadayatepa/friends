"""Builds the embedded Leaflet map (photo markers + live birthday flashing).
Friend data is injected as JSON; all date logic runs live in the browser so
'Happy Birthday' flashing and the 'within N hours' highlight update by the
minute without a Streamlit rerun."""
import json
import re

# Match a Google Drive file id in the common link shapes people paste.
_DRIVE_RE = re.compile(
    r"drive\.google\.com/(?:file/d/|open\?id=|uc\?(?:export=\w+&)?id=)([\w-]+)")


def normalize_photo(url):
    """Turn a Google Drive share/view link into a directly-embeddable image URL.
    Other URLs are returned unchanged. (The file must still be shared
    'Anyone with the link'.)"""
    if not url:
        return url
    m = _DRIVE_RE.search(url)
    if m:
        return f"https://drive.google.com/thumbnail?id={m.group(1)}&sz=w1000"
    return url

_TEMPLATE = r"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html,body{margin:0;height:100%;font-family:"Segoe UI",system-ui,sans-serif;}
  #map{height:__HEIGHT__px;width:100%;border-radius:10px;}
  #banner{position:relative;text-align:center;font-weight:800;font-size:18px;
    padding:8px;color:#1f2733;border-radius:8px;margin-bottom:6px;display:none;
    background:linear-gradient(90deg,#ffd166,#ff5d8f,#4895ef,#ffd166);
    background-size:300% 100%;animation:slide 4s linear infinite;}
  @keyframes slide{to{background-position:300% 0;}}
  .photo-marker{width:46px;height:46px;border-radius:50%;border:3px solid #fff;
    object-fit:cover;background:#ccc;box-shadow:0 1px 6px rgba(31,39,51,.35);}
  .photo-marker.bday{border-color:#ffd166;animation:bounce 1s infinite;}
  @keyframes bounce{0%,100%{transform:translateY(0) scale(1);border-color:#ffd166;}
    50%{transform:translateY(-6px) scale(1.12);border-color:#ff5d8f;}}
  .photo-marker.soon{border-color:#4895ef;}
  .leaflet-popup-content{font-size:13px;line-height:1.5;}
  .popup-photo{width:100%;max-width:170px;border-radius:8px;margin-bottom:6px;}
  .cheer{color:#d6336c;font-weight:700;}
</style></head><body>
<div id="banner"></div><div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const FRIENDS = __DATA__;
const WIN_MS = __WINDOW__ * 3600000;
const map = L.map("map",{worldCopyJump:true}).setView([20,0],2);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  {attribution:"© OpenStreetMap",maxZoom:18}).addTo(map);

function fallback(n){return "https://ui-avatars.com/api/?background=cccccc&color=333&name="+encodeURIComponent(n);}
function md(s){ if(!s) return null; const p=s.split("-"); if(p.length<3) return null;
  return {month:+p[1]-1, day:+p[2]}; }
function isToday(m,d,now){return now.getMonth()===m && now.getDate()===d;}
function msNext(m,d,now){let y=now.getFullYear();
  let nx=new Date(y,m,d,0,0,0,0);
  if(new Date(y,m,d,23,59,59,999)<now) nx=new Date(y+1,m,d,0,0,0,0);
  return nx-now;}

const MK={};
const pts=[];
FRIENDS.forEach(f=>{
  if(f.lat==null||f.lng==null) return;
  const events=[];
  let e=md(f.dob); if(e) events.push({type:"🎂 Birthday",label:"Happy Birthday, "+f.name+"!",m:e.month,d:e.day});
  e=md(f.anniversary); if(e) events.push({type:"💍 Anniversary",label:"Happy Anniversary, "+f.name+"!",m:e.month,d:e.day});
  (f.kids||[]).forEach(k=>{const kd=md(k.dob); if(kd) events.push({type:"👶 "+k.name+"'s Birthday",label:"Happy Birthday to "+k.name+"! ("+f.name+"'s kid)",m:kd.month,d:kd.day});});
  const icon=L.divIcon({className:"",iconSize:[46,46],iconAnchor:[23,23],popupAnchor:[0,-24],
    html:'<img class="photo-marker" src="'+(f.photo||fallback(f.name))+'" onerror="this.src=\''+fallback(f.name)+'\'">'});
  const mk=L.marker([f.lat,f.lng],{icon}).addTo(map);
  MK[f.name]={mk,f,events};
  pts.push([f.lat,f.lng]);
});
if(pts.length) map.fitBounds(pts,{padding:[40,40],maxZoom:5});

function popup(f,cheer){
  let kids=(f.kids||[]).map(k=>"<div>👶 "+k.name+(k.dob?" — "+k.dob:"")+"</div>").join("");
  return '<img class="popup-photo" src="'+(f.photo||fallback(f.name))+'" onerror="this.style.display=\'none\'">'
    +"<b>"+f.name+"</b><br>"
    +(cheer?'<div class="cheer">🎉 '+cheer+'</div>':"")
    +(f.location?"📍 "+f.location+"<br>":"")
    +(f.dob?"🎂 "+f.dob+"<br>":"")
    +(f.anniversary?"💍 "+f.anniversary+"<br>":"")
    +(f.phone?"📞 "+f.phone+"<br>":"")
    +(f.email?'✉️ <a href="mailto:'+f.email+'">'+f.email+"</a><br>":"")
    +(kids?"<hr style='border:none;border-top:1px solid #ddd'>"+kids:"");
}

function tick(){
  const now=new Date(); const cheers=[];
  Object.values(MK).forEach(o=>{
    let state=null,todayCheer=null;
    o.events.forEach(ev=>{
      if(isToday(ev.m,ev.d,now)){state="today";todayCheer=ev.label;cheers.push(ev.label);}
      else{const ms=msNext(ev.m,ev.d,now); if(ms>=0&&ms<=WIN_MS&&state!=="today") state="soon";}
    });
    const img=o.mk.getElement()?o.mk.getElement().querySelector("img"):null;
    if(img){img.classList.remove("bday","soon"); if(state==="today")img.classList.add("bday"); else if(state==="soon")img.classList.add("soon");}
    o.mk.bindPopup(popup(o.f,todayCheer));
  });
  const b=document.getElementById("banner");
  if(cheers.length){b.style.display="block";b.textContent="🎉 "+cheers.join("   •   ")+" 🎉";}
  else b.style.display="none";
}
tick(); setInterval(tick,60000);
</script></body></html>
"""


def build_map_html(friends, window_hours=2, height=560):
    payload = [{
        "name": f["name"], "lat": f["lat"], "lng": f["lng"],
        "photo": normalize_photo(f["photo"]), "phone": f["phone"], "email": f["email"],
        "location": f["location"], "dob": f["dob"], "anniversary": f["anniversary"],
        "kids": f["kids"],
    } for f in friends]
    return (_TEMPLATE
            .replace("__DATA__", json.dumps(payload))
            .replace("__WINDOW__", str(window_hours))
            .replace("__HEIGHT__", str(height)))
