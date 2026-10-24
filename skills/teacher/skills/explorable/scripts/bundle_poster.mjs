import {safeSourceUrl} from './bundle_templates.mjs';
// Layout the fixed-size poster with measured SVG text, never character-count truncation.
export async function createPoster(page, data, selected) {
 const refs=[...data.sources,...(selected.sources||[])].filter((s,i,a)=>a.findIndex(t=>t.title===s.title&&t.url===s.url&&t.locator===s.locator)===i).map(s=>({...s,posterHref:safeSourceUrl(s.url)}));
 return page.evaluate(({data, selected, refs}) => {
  const ns='http://www.w3.org/2000/svg',W=1440,H=900,M=58,width=W-2*M;
  const root=document.createElementNS(ns,'svg');root.setAttribute('xmlns',ns);root.setAttribute('width',W);root.setAttribute('height',H);root.setAttribute('viewBox',`0 0 ${W} ${H}`);root.setAttribute('role','img');root.setAttribute('aria-labelledby','poster-title poster-desc');
  const el=(tag,attrs={},text,parent=root)=>{const node=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))node.setAttribute(k,String(v));if(text!==undefined)node.textContent=text;parent.append(node);return node};
  el('title',{id:'poster-title'},`${data.title} — ${selected.title}`);el('desc',{id:'poster-desc'},`${selected.figureLabel}. ${selected.sayText}`);el('rect',{width:W,height:H,fill:'#faf8f2'});
  const group=el('g',{fill:'#202f3c','font-family':'Charter,Georgia,serif'});
  const measuring=el('text',{'font-family':'Charter,Georgia,serif',visibility:'hidden'},'',group);document.body.append(root);
  const measure=(s,size,family='Charter,Georgia,serif')=>{measuring.setAttribute('font-size',size);measuring.setAttribute('font-family',family);measuring.textContent=s;return measuring.getComputedTextLength()};
  const wrap=(text,size,max=width,family)=>{
   const lines=[];let line='';
   for(const token of String(text||'').trim().split(/\s+/).filter(Boolean)){
    if(measure(token,size,family)>max){
     if(line){lines.push(line);line=''}
     let chunk='';for(const char of token){if(chunk&&measure(chunk+char,size,family)>max){lines.push(chunk);chunk=''}chunk+=char}line=chunk;
    }else if(line&&measure(line+' '+token,size,family)>max){lines.push(line);line=token}else line+=(line?' ':'')+token;
   }
   if(line)lines.push(line);return lines;
  };
  const fit=(text,start,min,maxLines,max=width,family)=>{
   for(let size=start;size>=min;size--){const lines=wrap(text,size,max,family);if(lines.length<=maxLines)return {size,lines}}
   throw new Error(`Poster text needs more than ${maxLines} lines at ${min}px: ${String(text).slice(0,80)}. Use a shorter display title/note; the complete companion preserves the explanation.`);
  };
  const textBlock=(part,fit,x,top,gap=1.3,parent=group)=>{
   const baseline=top+fit.size;fit.lines.forEach((line,i)=>el('text',{x,y:baseline+i*fit.size*gap,'font-size':fit.size,'data-poster-part':part},line,parent));
   return top+fit.size+(fit.lines.length-1)*fit.size*gap+fit.size*.23;
  };
  const eyebrow=fit(data.subject||'Visual lesson',17,14,1,width,'sans-serif');textBlock('eyebrow',eyebrow,M,27,1,el('g',{fill:'#17695f','font-family':'sans-serif','letter-spacing':'1.5'},undefined,group));
  const title=fit(data.title,42,29,2);let headerBottom=textBlock('title',title,M,69,1.24);
  const step=fit(selected.title,25,20,2);headerBottom=textBlock('step-title',step,M,headerBottom+20,1.25);
  const ruleY=headerBottom+17;el('line',{x1:M,x2:W-M,y1:ruleY,y2:ruleY,stroke:'#ccd3d4'},undefined,group);
  const refItems=refs.map((s,i)=>({text:`[${i+1}]`,url:s.posterHref,title:[s.title,s.locator,s.url].filter(Boolean).join(' — ')}));
  refItems.push({text:refs.length?'Full references ↗':'Source lesson · no external references supplied',url:refs.length?'still.html#references':'explorer.html',title:refs.length?'All source titles, locators and URLs':'Authored source artifact; external factual verification is not supplied.'});
  const rows=[[]];let used=measure(refs.length?'Sources':'Provenance',15,'sans-serif')+22;
  for(const ref of refItems){const w=measure(ref.text,15,'sans-serif')+17;if(used+w>width){rows.push([]);used=0}rows.at(-1).push({...ref,x:M+used});used+=w}
  const sourceTop=H-27-rows.length*23;
  el('text',{x:M,y:sourceTop+15,'font-size':15,'font-family':'sans-serif','data-poster-part':'source-label'},refs.length?'Sources':'Provenance',group);
  rows.forEach((row,r)=>row.forEach(ref=>{const a=ref.url?el('a',{href:ref.url},undefined,group):el('g',{},undefined,group);el('title',{},ref.title,a);el('text',{x:ref.x,y:sourceTop+15+r*23,'font-size':15,'font-family':'sans-serif',fill:ref.url?'#17695f':'#202f3c','text-decoration':ref.url?'underline':'none','data-poster-part':'source-ref'},ref.text,a)}));
  const note=fit(selected.note||selected.sayText,18,16,2),noteHeight=note.size*1.3*(note.lines.length-1)+note.size*1.23,noteTop=sourceTop-17-noteHeight;
  textBlock('note',note,M,noteTop);
  const caption=fit(selected.lookFor||selected.figureLabel,23,18,2),captionHeight=caption.size*1.3*(caption.lines.length-1)+caption.size*1.23,captionTop=noteTop-22-captionHeight;
  textBlock('caption',caption,M,captionTop);
  const bottomRule=captionTop-16,figureTop=ruleY+16,figureHeight=bottomRule-figureTop-12;
  if(figureHeight<310)throw new Error(`Poster header/credits leave only ${Math.round(figureHeight)}px for the mechanism. Shorten display titles or notes; all full references remain in the companion.`);
  el('line',{x1:M,x2:W-M,y1:bottomRule,y2:bottomRule,stroke:'#ccd3d4'},undefined,group);
  const parsed=new DOMParser().parseFromString(selected.svg,'image/svg+xml');const figure=document.importNode(parsed.documentElement,true);figure.setAttribute('x',M);figure.setAttribute('y',figureTop);figure.setAttribute('width',width);figure.setAttribute('height',figureHeight);figure.setAttribute('preserveAspectRatio','xMidYMid meet');figure.setAttribute('data-poster-figure','true');group.insertBefore(figure,group.querySelector('[data-poster-part="caption"]'));
  measuring.remove();
  const bounds=[...root.querySelectorAll('[data-poster-part]')].map(node=>{const b=node.getBBox();return {part:node.getAttribute('data-poster-part'),text:node.textContent,x:b.x,y:b.y,width:b.width,height:b.height}});
  for(const b of bounds)if(b.x<M-1||b.x+b.width>W-M+1||b.y<12||b.y+b.height>H-12)throw new Error(`Poster text outside its canvas: ${b.part}: ${b.text}`);
  const lastTitle=Math.max(...bounds.filter(b=>b.part==='title').map(b=>b.y+b.height)),firstStep=Math.min(...bounds.filter(b=>b.part==='step-title').map(b=>b.y));if(firstStep-lastTitle<12)throw new Error('Poster title overlaps the step title.');
  const result={svg:new XMLSerializer().serializeToString(root),layout:{width:W,height:H,figure:{x:M,y:figureTop,width,height:figureHeight},title:{fontSize:title.size,lines:title.lines.length},references:refs.length,sourceRows:rows.length,textBounds:bounds,clippedText:0}};root.remove();return result;
 },{data,selected,refs});
}
