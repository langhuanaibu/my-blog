(function(root, factory){
  const api=factory();
  if(typeof module==="object"&&module.exports) module.exports=api;
  else root.NewsTimeline=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
  const DAY=/^\d{4}-\d{2}-\d{2}$/;
  function publishedDate(item, fallback){
    if(DAY.test(item&&item.published_date||"")) return {date:item.published_date,uncertain:false};
    const d=new Date(item&&item.time);
    if(!isNaN(d)){
      const parts=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Shanghai",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(d);
      const val=k=>parts.find(p=>p.type===k).value;
      return {date:`${val("year")}-${val("month")}-${val("day")}`,uncertain:false};
    }
    return {date:fallback,uncertain:true};
  }
  function canonicalUrl(raw){
    try{
      const u=new URL(raw); u.hash="";
      for(const k of [...u.searchParams.keys()]) if(/^utm_|^(ref|source|campaign|at_medium|at_campaign)$/i.test(k)) u.searchParams.delete(k);
      u.hostname=u.hostname.replace(/^www\./,"").toLowerCase();
      u.pathname=u.pathname.replace(/\/$/,"")||"/";
      return u.toString();
    }catch(e){return String(raw||"").trim();}
  }
  function sourceDomain(raw){try{return new URL(raw).hostname.replace(/^www\./,"").toLowerCase();}catch(e){return "";}}
  function norm(s){return String(s||"").toLowerCase().replace(/[\s\p{P}\p{S}]+/gu,"");}
  function grams(s){s=norm(s);const out=new Set();for(let i=0;i<Math.max(1,s.length-1);i++)out.add(s.slice(i,i+2));return out;}
  function similarity(a,b){
    const A=grams(a),B=grams(b);let n=0;for(const x of A)if(B.has(x))n++;
    return A.size&&B.size?2*n/(A.size+B.size):0;
  }
  function mergeSources(rows){
    const seen=new Set(),out=[];
    for(const r of rows) for(const s of (r.item.sources||[])){
      const key=canonicalUrl(s.url)||String(s.name||"").toLowerCase();
      if(!key||seen.has(key))continue; seen.add(key);out.push(s);
    }
    return out;
  }
  function sameFallback(a,b){
    const au=new Set((a.item.sources||[]).map(s=>canonicalUrl(s.url)).filter(Boolean));
    if((b.item.sources||[]).some(s=>au.has(canonicalUrl(s.url)))) return true;
    return similarity(a.item.title,b.item.title)>=.82;
  }
  function groupRows(rows){
    const groups=[];
    for(const row of rows){
      let g=row.item.event_id&&groups.find(x=>x.eventId===row.item.event_id);
      if(!g&&!row.item.event_id)g=groups.find(x=>!x.eventId&&sameFallback(x.rows[0],row));
      if(!g){g={eventId:row.item.event_id||"",rows:[]};groups.push(g);} g.rows.push(row);
    }
    return groups;
  }
  function groupHotEvents(rows){
    return groupRows(rows).map(g=>{
      const ordered=g.rows.slice().sort((a,b)=>new Date(b.item.time||0)-new Date(a.item.time||0));
      const sources=mergeSources(ordered),domains=new Set(sources.map(s=>sourceDomain(s.url)).filter(Boolean));
      return {latest:ordered[0],rows:ordered,sources,sourceCount:domains.size||sources.length};
    });
  }
  function hasProgress(newer,older){
    if(similarity(newer.item.title,older.item.title)<.64)return true;
    const a=newer.item.summary||newer.item.detail||"",b=older.item.summary||older.item.detail||"";
    return a&&b&&similarity(a,b)<.45;
  }
  function timelineRows(rows){
    const out=[];
    for(const g of groupRows(rows)){
      const ordered=g.rows.slice().sort((a,b)=>new Date(b.item.time||0)-new Date(a.item.time||0));
      const kept=[];
      for(const row of ordered){
        const pd=publishedDate(row.item,row.reportDate);
        const decorated={...row,publishedDate:pd.date,timeUncertain:pd.uncertain,isContinuation:false};
        if(!kept.length||hasProgress(kept[kept.length-1],decorated)) kept.push(decorated);
      }
      const allSources=mergeSources(ordered);
      if(kept.length===1) kept[0].item={...kept[0].item,sources:allSources};
      else for(let i=0;i<kept.length-1;i++)kept[i].isContinuation=true;
      out.push(...kept);
    }
    return out.sort((a,b)=>String(b.item.time||"").localeCompare(String(a.item.time||"")));
  }
  return {publishedDate,canonicalUrl,similarity,groupHotEvents,timelineRows};
});
