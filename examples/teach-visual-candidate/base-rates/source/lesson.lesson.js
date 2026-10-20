// Exact natural-frequency model. All slider settings yield whole-item counts.
function flags(p) {
  const total=10000, defective=total*p.base/100, sound=total-defective;
  const trueFlags=defective*p.hit/100, falseFlags=sound*p.falseRate/100;
  const flagged=trueFlags+falseFlags;
  return {total,defective,sound,trueFlags,falseFlags,flagged,missed:defective-trueFlags, precision:flagged?trueFlags/flagged:null};
}
const nf=n=>n.toLocaleString("en-US");
window.LESSON={
 id:"base-rates-v3",title:"A flag is not a verdict.",subtitle:"Count the flagged group before deciding how much a positive signal means.",subject:"Mathematics · conditional probability",level:"frequencies → Bayes' rule",style:"visual-explain",
 hook:"<p>A factory flags items for inspection. A good detector can still flag many sound items when defects are rare.</p>",
 sources:[{title:"OpenStax · Conditional probability",url:"https://openstax.org/books/introductory-statistics-2e/pages/3-1-terminology",note:"Conditional probability uses the conditioning event as its denominator."},{title:"OpenStax · Tree and Venn diagrams",url:"https://openstax.org/books/introductory-statistics-2e/pages/3-5-tree-and-venn-diagrams",note:"Represent branches and joint events without reversing the conditional."}],
 limits:"This is a hypothetical factory with exactly specified frequencies, not measured performance or a medical test. Population strip uses the whole batch. Detail bars name their local denominators; collection bars use one common count scale, then expand to all flags. Detector rates are conditional on item status.",
 params:{base:{label:"Defective items in the batch",min:1,max:50,step:1,value:1,unit:"%"},hit:{label:"Flag rate among defective items",min:50,max:100,step:1,value:90,unit:"%"},falseRate:{label:"Flag rate among sound items",min:0,max:20,step:1,value:5,unit:"%"},phase:{label:"Visual stage",min:0,max:6,step:0.01,value:0}},model:flags,

 readouts:(s,p)=>p.phase<1?[["Defective",nf(s.defective)],["Sound",nf(s.sound)]]:p.phase<4?[["True flags",nf(s.trueFlags)],["False flags",p.phase<2?"Not selected yet":nf(s.falseFlags)]]:[["All flags",nf(s.flagged)],["Defective among flags",s.precision===null?"Undefined":`${(100*s.precision).toFixed(1)}%`]],
 figure:{viewBox:n=>n?"0 0 360 790":"0 0 960 590",narrowText:1,label:(s,p)=>`Batch: ${s.defective} defective and ${s.sound} sound. ${p.phase>=1?`${s.trueFlags} true flags and ${s.missed} missed defective.`:""} ${p.phase>=2?`${s.falseFlags} false flags.`:""} ${p.phase>=3?`Selected: ${s.flagged} flags; excluded: ${s.total-s.flagged}.`:""} ${p.phase>=4?`Defective among flags: ${s.trueFlags}/${s.flagged}, ${(s.precision*100).toFixed(1)} percent.`:""}`,
 draw(g,s,p,k){
 const {el,narrow}=k,W=narrow?360:960,H=narrow?790:590,x=24,w=W-48,phase=p.phase;
 const C={ink:"#263c44",muted:"#536567",paper:"#fcfcf8",true:"#8471ac",false:"#ebc5ac",neutral:"#e6e9e5"};
 const tx=(xx,y,t,size=narrow?17:21)=>el("text",{x:xx,y,text:t,"font-size":size,fill:C.ink,"font-family":"Georgia,serif"});
 const rect=(id,xx,y,ww,h,fill,extra={})=>el("rect",{id,x:xx,y,width:Math.max(0,ww),height:h,fill,stroke:C.ink,"stroke-width":1,...extra});
 const mix=(a,b,t)=>a+(b-a)*Math.max(0,Math.min(1,t));
 el("rect",{x:0,y:0,width:W,height:H,fill:C.paper});
 const defs=el("defs",{});const pat=document.createElementNS("http://www.w3.org/2000/svg","pattern");pat.setAttribute("id","false-hatch");pat.setAttribute("width","8");pat.setAttribute("height","8");pat.setAttribute("patternUnits","userSpaceOnUse");pat.innerHTML='<rect width="8" height="8" fill="#ebc5ac"/><path d="M-2 2L2 -2M0 8L8 0M6 10L10 6" stroke="#815c43" stroke-width="1"/>';defs.append(pat);
 tx(x,30,"01  START WITH 10,000 ITEMS",narrow?17:20);
 rect("population-sound",x,48,w,25,C.neutral);rect("population-defective",x,48,w*s.defective/s.total,25,C.true);
 tx(x,101,`● ${nf(s.defective)} defective · ${p.base}%`);
 tx(narrow?x:470,narrow?129:101,`${nf(s.sound)} sound · ${100-p.base}%`);
 const yD=narrow?197:190,yS=narrow?315:290,collectY=narrow?491:422;
 if(phase>=1&&!(phase>2&&phase<3)){tx(x,narrow?170:151,"02  APPLY RATES WITHIN EACH GROUP",narrow?15:20);tx(x,yD-12,`● ${nf(s.trueFlags)} true flags / ${nf(s.defective)} defective`);tx(x,yD+56,`${p.hit}% hit rate · ${nf(s.missed)} missed`);}
 if(phase>=2&&!(phase>2&&phase<3)){tx(x,yS-12,`▧ ${nf(s.falseFlags)} false flags / ${nf(s.sound)} sound`);tx(x,yS+56,`${p.falseRate}% false flags · ${nf(s.sound-s.falseFlags)} unflagged`);}
 // Detail references stay behind when the selected segments move.
 if(phase>=1&&phase<2){rect("defective-detail-total",x,yD,w,28,C.neutral);}
 if(phase>=3){
 rect("defective-detail-total",x,yD,w,20,C.neutral);
 rect("defective-detail-reference",x,yD,w*p.hit/100,20,C.true,{"fill-opacity":0.32});
 rect("sound-detail-total",x,yS,w,20,C.neutral);
 rect("sound-detail-reference",x,yS,w*p.falseRate/100,20,"url(#false-hatch)",{"fill-opacity":0.6});
 tx(x+w-3,yD+16,"",15);
 }
 const common=Math.max(1000,s.flagged),unit=w/common;
 const move=Math.max(0,Math.min(1,phase-2)),expand=Math.max(0,Math.min(1,phase-3));
 let tw=phase<2?mix(w*p.hit/100,unit*s.trueFlags,phase-1):unit*s.trueFlags;
 let fw=unit*s.falseFlags;
 if(phase>=1){rect("true-flag-segment",x,mix(yD,collectY,move),mix(tw,w*(s.precision??0),expand),28,C.true);}
 if(phase>=2){rect("false-flag-segment",mix(x,x+tw,move),mix(yS,collectY,move),fw,28,"url(#false-hatch)");}
 if(phase>2&&phase<3){tx(x,mix(yD,collectY,move)-7,`● ${nf(s.trueFlags)}`);tx(mix(x,x+tw,move),mix(yS,collectY,move)-7,`▧ ${nf(s.falseFlags)}`);}
 // During denominator expansion both segments retain their identities and counts.
 if(phase>3){const f=g.querySelector('#false-flag-segment');f.setAttribute('x',x+mix(tw,w*(s.precision??0),expand));f.setAttribute('width',mix(fw,w*(1-(s.precision??0)),expand));}
 if(phase>1&&phase<=2)tx(x,narrow?405:374,`Rescale flags: ${nf(common)} items = full width`,narrow?15:18);
 if(phase>=3){
 tx(x,collectY-40,"03  KEEP ONLY THE FLAGS",narrow?17:20);
 rect("selected-boundary",x-5,collectY-5,mix(unit*s.flagged,w,expand)+10,38,"none",{"stroke-width":2});
 tx(x,collectY+57,`● ${nf(s.trueFlags)} + ▧ ${nf(s.falseFlags)} = ${nf(s.flagged)} flags`);
 tx(x,collectY+86,phase>=4?`Denominator: all ${nf(s.flagged)} flags`:phase>3?`Expand ${nf(s.flagged)} flags; counts unchanged`:`Same count scale; now one selected group`,narrow?16:20);
 if(phase>=4)tx(x,collectY+118,`${nf(s.trueFlags)} / ${nf(s.flagged)} = ${(100*s.precision).toFixed(1)}%`,narrow?24:27);
 tx(narrow?x:520,narrow?680:536,`Outside: ${nf(s.total-s.flagged)} not flagged`,narrow?17:20);
 tx(narrow?x:520,narrow?709:565,`Including ${nf(s.missed)} missed defective`,narrow?17:20);
 if(phase>=5&&phase<6)el("line",{x1:x+w*2/13,x2:x+w*2/13,y1:collectY-10,y2:collectY+35,stroke:C.ink,"stroke-width":2,"stroke-dasharray":"3 3"});
 if(phase>=5)tx(x,narrow?752:568,phase<6?"Earlier: 15.4% at a 1% base rate":"Zero false flags; missed defects remain.",narrow?16:18);
 }
 }},
 steps:[{"id": "population", "title": "Start with the batch", "set": {"base": 1, "hit": 90, "falseRate": 5, "phase": 0}, "controls": ["base"], "say": "<p><strong>Worked example: base 1%, hit 90%, false flags 5%.</strong> The hypothetical batch has 100 defective items and 9,900 sound items. Each rate starts with its own population.</p>", "note": "Hypothetical exact frequencies; every denominator names its group."}, {"id": "true-selection", "title": "Select within defective items", "set": {"base": 1, "hit": 90, "falseRate": 5, "phase": 1}, "controls": ["hit"], "say": "<p><strong>Worked example: base 1%, hit 90%, false flags 5%.</strong> The detector flags 90 of the 100 defective items. Its 90% hit rate leaves 10 defective items missed.</p>", "note": "Hypothetical exact frequencies; every denominator names its group."}, {"id": "branches", "title": "Select within sound items", "set": {"base": 1, "hit": 90, "falseRate": 5, "phase": 2}, "controls": ["hit", "falseRate"], "say": "<p><strong>Worked example: base 1%, hit 90%, false flags 5%.</strong> Five percent of 9,900 sound items gives 495 false flags. A smaller rate can produce more flags because its population is larger.</p>", "note": "Hypothetical exact frequencies; every denominator names its group."}, {"id": "collection", "title": "Collect only flags", "set": {"base": 1, "hit": 90, "falseRate": 5, "phase": 3}, "controls": ["base", "falseRate"], "say": "<p><strong>Worked example: base 1%, hit 90%, false flags 5%.</strong> Move the 90 true flags and 495 false flags into one group. Leave 9,415 unflagged items outside, including 10 missed defects.</p>", "note": "Hypothetical exact frequencies; every denominator names its group."}, {"id": "conditional", "title": "Change the denominator", "set": {"base": 1, "hit": 90, "falseRate": 5, "phase": 4}, "controls": ["base", "falseRate"], "say": "<p><strong>Worked example: base 1%, hit 90%, false flags 5%.</strong> Expand the same selected group. Its count stays 585. The defective share is 90 divided by 585, or 15.4%.</p>", "note": "Hypothetical exact frequencies; every denominator names its group.", "ask": {"kind": "choice", "q": "Which denominator answers defective among flagged items?", "options": ["100 defective", "585 flagged", "10,000 total"], "answer": 1, "why": "A flag selects all 585 flagged items, including false flags."}}, {"id": "prior", "title": "Change the base rate", "set": {"base": 10, "hit": 90, "falseRate": 5, "phase": 5}, "controls": ["base", "hit", "falseRate"], "say": "<p><strong>Worked example: base 10%, hit 90%, false flags 5%.</strong> At a 10% defect rate, the same detector gives 900 true flags and 450 false flags. Of 1,350 flags, 66.7% are defective.</p>", "note": "Hypothetical exact frequencies; every denominator names its group."}, {"id": "limits", "title": "Remove false flags", "set": {"base": 10, "hit": 90, "falseRate": 0, "phase": 6}, "controls": ["hit", "falseRate"], "say": "<p><strong>Worked example: base 10%, hit 90%, false flags 0%.</strong> With zero false flags, all 900 flags are true. Yet 100 defective items remain missed. Precision is 100%; hit rate is still 90%.</p>", "note": "Hypothetical exact frequencies; every denominator names its group."}],
 film:[{"chapter": "Start with the batch", "set": {"base": 1, "hit": 90, "falseRate": 5, "phase": 0}, "say": "The hypothetical batch has 100 defective items and 9,900 sound items. Each rate starts with its own population."}, {"chapter": "Select within defective items", "set": {"base": 1, "hit": 90, "falseRate": 5, "phase": 1}, "say": "The detector flags 90 of the 100 defective items. Its 90% hit rate leaves 10 defective items missed."}, {"chapter": "Select within sound items", "set": {"base": 1, "hit": 90, "falseRate": 5, "phase": 2}, "say": "Five percent of 9,900 sound items gives 495 false flags. A smaller rate can produce more flags because its population is larger."}, {"chapter": "Collect only flags", "set": {"base": 1, "hit": 90, "falseRate": 5, "phase": 3}, "say": "Move the 90 true flags and 495 false flags into one group. Leave 9,415 unflagged items outside, including 10 missed defects."}, {"chapter": "Change the denominator", "set": {"base": 1, "hit": 90, "falseRate": 5, "phase": 4}, "say": "Expand the same selected group. Its count stays 585. The defective share is 90 divided by 585, or 15.4%."}, {"chapter": "Change the base rate", "set": {"base": 10, "hit": 90, "falseRate": 5, "phase": 5}, "say": "At a 10% defect rate, the same detector gives 900 true flags and 450 false flags. Of 1,350 flags, 66.7% are defective."}, {"chapter": "Remove false flags", "set": {"base": 10, "hit": 90, "falseRate": 0, "phase": 6}, "say": "With zero false flags, all 900 flags are true. Yet 100 defective items remain missed. Precision is 100%; hit rate is still 90%."}],
 checks:[{name:"known natural frequencies",test:m=>{const s=m({base:1,hit:90,falseRate:5});return s.trueFlags===90&&s.falseFlags===495&&s.flagged===585&&Math.abs(s.precision-2/13)<1e-12;}},{name:"counts conserved",test:m=>[1,10,50].every(base=>{const s=m({base,hit:83,falseRate:7});return s.defective+s.sound===s.total&&s.trueFlags+s.missed===s.defective;})},{name:"zero false flags gives precision one",test:m=>m({base:1,hit:50,falseRate:0}).precision===1},{name:"larger prior raises posterior at fixed rates",test:m=>m({base:10,hit:90,falseRate:5}).precision>m({base:1,hit:90,falseRate:5}).precision}]
};
