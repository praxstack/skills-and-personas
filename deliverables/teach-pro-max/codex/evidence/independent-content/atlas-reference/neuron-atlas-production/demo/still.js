/* Exact vector compositions. Geometry and labels consume the authoritative model. */
(function expose(root) {
  'use strict';
  const M = typeof module !== 'undefined' && module.exports ? require('./model.js') : root.NeuronAtlas;
  const P = Object.freeze({bg:'#101828',panel:'#172236',ink:'#edf1f7',muted:'#aebbd0',rule:'#3d4b62',positive:'#c4b5fd',negative:'#ffaaa0',output:'#93e6ce'});
  const fmt = (v, digits=3) => {const n = Math.abs(v)<1e-9 ? 0 : Number(v.toFixed(digits)); return String(n).replace('-', '−');};
  const signed = v => (v>1e-9?'+':'')+fmt(v);
  const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
  function render(state, options={}) {
    const r=M.evaluate(state), portrait=Boolean(options.portrait), W=portrait?360:1120,H=portrait?860:435;
    const color=v=>v<0?P.negative:P.positive;
    const t=(x,y,text,cls='label',fill=P.ink,anchor='start')=>`<text x="${x}" y="${y}" class="${cls}" fill="${fill}" text-anchor="${anchor}">${esc(text)}</text>`;
    const line=(x1,y1,x2,y2,stroke=P.rule,width=1,dash='')=>`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${width}" ${dash?`stroke-dasharray="${dash}"`:''}/>`;
    let body='';
    const title=options.title || 'Follow the signed contributions';
    body+=t(24,34,title,'title');
    body+=t(24,59,(portrait?'Artificial neuron · ReLU · toy values':'Artificial neuron · ReLU · dimensionless toy values'),'meta',P.muted);
    // The same signed arithmetic is recomposed, rather than scaled to unreadability.
    const terms=[{name:'Input 1',formula:`${fmt(state.x1)} × ${fmt(state.w1)}`,value:r.c1}, {name:'Input 2',formula:`${fmt(state.x2)} × ${fmt(state.w2)}`,value:r.c2}, {name:'Bias',formula:'added directly',value:state.b}];
    const tx=24,tw=portrait?312:300,ty=portrait?97:116,dy=portrait?62:76;
    body+=t(tx,ty-15,'MULTIPLY / SIGNED TERMS','meta',P.muted);
    terms.forEach((term,i)=>{
      const y=ty+i*dy;
      body+=t(tx,y+9,term.name,'label',P.muted)+t(tx,y+34,term.formula,'number')+t(tx+tw,y+28,signed(term.value),'value',color(term.value),'end');
      body+=line(tx,y+47,tx+tw,y+47,P.rule);
    });
    // Waterfall: every segment uses one common linear scale, including its sign.
    const wx=portrait?24:397,wy=portrait?321:98,ww=portrait?312:315;
    body+=t(wx,wy,'ADD / FOLLOW THE ENDPOINT','meta',P.muted);
    const cumulative=[0,r.c1,r.c1+r.c2,r.z];
    const lo=Math.min(-0.5,...cumulative),hi=Math.max(1.6,...cumulative),span=hi-lo;
    const xp=v=>wx+14+(v-lo)/span*(ww-28);
    const ys=portrait?[wy+39,wy+84,wy+129]:[wy+53,wy+111,wy+169];
    const changes=[r.c1,r.c2,state.b];
    const zero=xp(0);
    body+=line(zero,wy+19,zero,ys[2]+22,P.rule,1,'3 5');
    changes.forEach((v,i)=>{
      const x1=xp(cumulative[i]),x2=xp(cumulative[i+1]),y=ys[i],c=color(v);
      body+=line(x1,y,x2,y,c,9);
      body+=`<circle cx="${x1}" cy="${y}" r="3" fill="${P.bg}" stroke="${c}" stroke-width="2"/><circle cx="${x2}" cy="${y}" r="5" fill="${c}"/>`;
      body+=t((x1+x2)/2,y-13,`${i===2?'b':`x${i+1}w${i+1}`} ${signed(v)}`,'number',c,'middle');
      if(i<2) body+=line(x2,y+7,x2,ys[i+1]-7,P.rule,1,'3 3');
    });
    const axisY=ys[2]+30;
    body+=line(wx+6,axisY,wx+ww-6,axisY,P.rule);
    [lo,0,hi].forEach(v=>body+=line(xp(v),axisY-3,xp(v),axisY+3,P.muted)+t(xp(v),axisY+21,fmt(v),'meta',P.muted,'middle'));
    body+=t(wx,axisY+59,`z = ${fmt(r.c1)} ${state.w2*state.x2<0?'−':'+'} ${fmt(Math.abs(r.c2))} ${state.b<0?'−':'+'} ${fmt(Math.abs(state.b))}`,'number');
    body+=t(wx,axisY+88,`sum  ${fmt(r.z)}`,'value',r.z<0?P.negative:P.output);
    // Activation curve: domain adapts explicitly so out-of-default values stay truthful.
    const gx=portrait?24:797,gy=portrait?624:98,gw=portrait?312:299;
    body+=t(gx,gy,'GATE / RECTIFIED LINEAR UNIT','meta',P.muted);
    const dMin=Math.min(-1,r.z-0.3),dMax=Math.max(1.5,r.z+0.3),aMax=Math.max(1.5,r.a+0.3);
    const left=gx+35,top=gy+26,pw=gw-54,ph=portrait?99:153;
    const px=v=>left+(v-dMin)/(dMax-dMin)*pw,py=v=>top+ph-v/aMax*ph;
    body+=line(left,top+ph,left+pw,top+ph,P.muted)+line(px(0),top,px(0),top+ph,P.rule);
    body+=`<path d="M ${px(dMin)} ${py(0)} L ${px(0)} ${py(0)} L ${px(dMax)} ${py(dMax)}" fill="none" stroke="${P.output}" stroke-width="3"/>`;
    body+=line(px(r.z),py(0),px(r.z),py(r.a),P.output,1,'4 4')+line(px(0),py(r.a),px(r.z),py(r.a),P.output,1,'4 4');
    body+=`<circle cx="${px(r.z)}" cy="${py(r.a)}" r="6" fill="${P.output}" stroke="${P.bg}" stroke-width="2"/>`;
    body+=t(px(0),top+ph+20,'0','meta',P.muted,'middle')+t(px(dMin),top+ph+20,fmt(dMin),'meta',P.muted,'middle')+t(px(dMax),top+ph+20,fmt(dMax),'meta',P.muted,'middle')+t(left+pw+14,top+ph+5,'z','meta',P.muted,'end')+t(px(0)-7,top-7,'a','meta',P.muted,'end')+t(px(0)-7,top+12,fmt(aMax),'meta',P.muted,'end');
    const ay=top+ph+52;
    body+=t(gx,ay,`a = max(0, ${fmt(r.z)})`,'number')+t(gx,ay+33,`output  ${fmt(r.a)}`,'value',P.output);
    if(!portrait){body+=line(365,90,365,385,P.rule)+line(752,90,752,385,P.rule);}
    const description=`Inputs ${fmt(state.x1)} and ${fmt(state.x2)} multiplied by weights ${fmt(state.w1)} and ${fmt(state.w2)} give contributions ${fmt(r.c1)} and ${fmt(r.c2)}. Bias ${fmt(state.b)} makes sum ${fmt(r.z)}. ReLU outputs ${fmt(r.a)}. Squared loss to target ${fmt(state.target)} is ${fmt(r.loss,5)}.`;
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="atlas-title atlas-desc"><title id="atlas-title">${esc(title)}</title><desc id="atlas-desc">${esc(description)}</desc><style>text{font-family:'Avenir Next','Trebuchet MS',sans-serif}.title{font-size:${portrait?19:25}px;font-weight:700}.label{font-size:${portrait?18:16}px}.meta{font-size:${portrait?14:13}px;letter-spacing:.05em}.number{font-family:'SFMono-Regular',Consolas,monospace;font-size:${portrait?18:18}px;font-variant-numeric:tabular-nums}.value{font-family:'SFMono-Regular',Consolas,monospace;font-size:${portrait?22:27}px;font-weight:500}</style><rect width="${W}" height="${H}" fill="${P.bg}"/>${body}</svg>`;
  }
  const API=Object.freeze({render,format:fmt,signed,palette:P});
  if(typeof module!=='undefined'&&module.exports) module.exports=API;
  root.NeuronStill=API;
})(typeof window!=='undefined'?window:globalThis);
