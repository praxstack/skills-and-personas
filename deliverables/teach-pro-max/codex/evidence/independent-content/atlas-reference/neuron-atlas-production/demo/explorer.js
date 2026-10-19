/* Offline browser host. The model owns arithmetic; media.currentTime owns film time. */
(function start() {
  'use strict';
  const M=window.NeuronAtlas, V=window.NeuronStill;
  if(!M || !V) return; // Complete static surface remains visible if a script cannot load.
  const $=id=>document.getElementById(id), f=V.format;
  const base=M.BASE, trained=M.step(base);
  const presets={baseline:{...base},inactive:{...base,b:-1},trained:{...trained}};
  let state={...base}, filmMode='idle', returnTime=0, pendingSeek=null, stepped=false, appliedPreset=null;
  const portrait=matchMedia('(max-width:1099px)');
  const controls=Array.from(document.querySelectorAll('[data-param]'));
  const video=$('neuron-video');
  const cues=Array.isArray(window.NeuronFilmCues)?window.NeuronFilmCues.filter(c=>Number.isFinite(c.start)&&Number.isFinite(c.end)&&c.end>c.start&&presets[c.preset]):[];
  const setStatus=(text,error=false)=>{$('video-status').textContent=text;$('video-status').dataset.error=String(error);};
  const clock=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
  function lockControls(locked) {
    controls.forEach(el=>el.disabled=locked);
    document.querySelectorAll('[data-preset],#reset,#train-step').forEach(el=>el.disabled=locked||(el.id==='train-step'&&stepped));
  }
  function render() {
    const r=M.evaluate(state);
    $('diagram').innerHTML=V.render(state,{portrait:portrait.matches});
    controls.forEach(el=>{el.value=state[el.dataset.param];$(el.id+'-value').textContent=f(state[el.dataset.param]);});
    [['z',r.z],['a',r.a],['target',state.target],['loss',r.loss]].forEach(([key,value])=>$('current-'+key).textContent=f(value,6));
    const prefix=`Input 1 contributes ${V.signed(r.c1)}; input 2 contributes ${V.signed(r.c2)}. Bias ${V.signed(state.b)} brings the sum to ${f(r.z)}. `;
    $('live-explanation').textContent=prefix+(r.z>0?`ReLU passes that positive sum through: output ${f(r.a)}.`:r.z<0?'ReLU clips the negative sum to zero. The output is 0.':'At the boundary, ReLU gives 0. This model uses derivative 0 at the kink.');
    $('loss-equation').textContent=`= ½(${f(r.a)} − ${f(state.target)})² = ${f(r.loss,6)}`;
    $('gradient-readout').replaceChildren(...[['w₁',r.grad.w1],['w₂',r.grad.w2],['b',r.grad.b]].map(([name,value])=>{const p=document.createElement('p');p.textContent=`∂L/∂${name} = ${f(value,6)}`;return p;}));
    $('scene-mode').textContent=filmMode==='film'?'Chapter worked result · parameters locked':filmMode==='explore'?`Live exploration · film paused at ${clock(returnTime)}`:'Live model · compare with the fixed starting example';
    lockControls(filmMode==='film');
    // Expose observable state for review, without persistence or scoring.
    $('diagram').dataset.state=JSON.stringify(state);
    $('diagram').dataset.result=JSON.stringify(r);
    $('diagram').dataset.mode=filmMode;
  }
  function change(next) {
    try {M.validate(next);state={...next};stepped=false;$('control-error').textContent='';$('update-detail').textContent='The button updates the current live model. Reset first to reproduce the worked step above.';render();}
    catch(error) {if(!(error instanceof TypeError||error instanceof RangeError))throw error;$('control-error').textContent=`The model could not change: ${error.message} The previous valid state is retained.`;render();}
  }
  controls.forEach(el=>el.addEventListener('input',()=>change({...state,[el.dataset.param]:Number(el.value)})));
  $('reset').addEventListener('click',()=>change(presets.baseline));
  document.querySelectorAll('[data-preset]').forEach(button=>button.addEventListener('click',()=>change(presets[button.dataset.preset])));
  $('train-step').addEventListener('click',()=>{
    try {
      const before={...state},beforeR=M.evaluate(before),next=M.step(before),after=M.evaluate(next);
      state={...next};stepped=true;render();
      $('update-detail').textContent=`One simultaneous step at η = ${f(before.eta)}: (w₁, w₂, b) changed from (${f(before.w1)}, ${f(before.w2)}, ${f(before.b)}) to (${f(next.w1)}, ${f(next.w2)}, ${f(next.b)}). Output ${f(beforeR.a)} → ${f(after.a)}; loss ${f(beforeR.loss,6)} → ${f(after.loss,6)}. ${beforeR.z<=0?'The zero local gradient leaves this inactive state unchanged.':'Change a parameter or reset before taking another step.'}`;
    } catch(error) {if(!(error instanceof RangeError||error instanceof TypeError))throw error;$('control-error').textContent=`This step would leave the supported parameter range. No parameters changed. Reset or reduce the current weights/bias. (${error.message})`;}
  });
  portrait.addEventListener('change',render);

  // Finite authored self-study content, with no tracking or grading.
  const cards=[
    ['What is actually multiplied by a weight?','An input value. Its signed product with the weight is that input’s contribution to z.'],
    ['What happens when z is negative?','ReLU outputs 0. In this demonstration its derivative is also 0 there, so this example supplies no gradient to change the parameters.'],
    ['Why update all three parameters together?','All gradients describe the same pre-update calculation. Computing a later gradient after changing an earlier parameter would be a different update rule.'],
    ['Does output 0.96 mean 96% confidence?','No. This is a dimensionless ReLU output fitted toward target 1 with squared error. A probability interpretation requires a suitable model and objective.']
  ];
  let card=0;
  $('reveal-card').addEventListener('click',()=>{const reveal=$('card-answer').hidden;$('card-answer').hidden=!reveal;$('reveal-card').setAttribute('aria-expanded',String(reveal));$('reveal-card').textContent=reveal?'Hide explanation':'Reveal explanation';});
  $('next-card').addEventListener('click',()=>{card=(card+1)%cards.length;$('card-position').textContent=`Card ${card+1} of ${cards.length} · self-study`;$('card-question').textContent=cards[card][0];$('card-answer').textContent=cards[card][1];$('card-answer').hidden=true;$('reveal-card').setAttribute('aria-expanded','false');$('reveal-card').textContent='Reveal explanation';});

  // Chromium's media clock truncates seeks to whole microseconds. Use the same
  // integer ticks for both authored bounds and currentTime. Half-open intervals
  // stay strict; only the sub-microsecond part unavailable to media is discarded.
  // Seek/return times themselves are never nudged or replaced by an app clock.
  const mediaTick=seconds=>Math.floor(seconds*1_000_000);
  function cueAt(t) {
    const tick=mediaTick(t);
    return cues.find(c=>tick>=mediaTick(c.start)&&tick<mediaTick(c.end)) ||
      (tick>=mediaTick((cues.at(-1)||{}).end||Infinity)?cues.at(-1):cues[0]);
  }
  function syncConcept() {
    const c=cueAt(video.currentTime);if(!c)return;
    $('cue-title').textContent=c.title;$('cue-text').textContent=c.text;
    document.querySelectorAll('[data-cue]').forEach(button=>button.setAttribute('aria-current',String(button.dataset.cue===String(c.id))));
    if(filmMode==='film'&&appliedPreset!==c.preset){state={...presets[c.preset]};stepped=false;appliedPreset=c.preset;render();}
    $('chapter-list').dataset.currentCue=String(c.id);
  }
  function setFilmMode(mode) {
    filmMode=mode;appliedPreset=null;
    $('return-film').hidden=mode!=='explore';$('pause-explore').hidden=mode==='explore';
    $('film-mode').textContent=mode==='explore'?`Explore mode · the film is paused at ${clock(returnTime)}. The live model can change; recorded facts remain fixed.`:'Film mode · the companion shows this chapter’s worked result, not each animated frame or your earlier live changes.';
    syncConcept();render();
  }
  function seekTo(t) {
    const requested=Math.max(0,t);pendingSeek=requested;
    if(video.readyState>=1&&Number.isFinite(video.duration)) {pendingSeek=null;video.currentTime=Math.min(requested,video.duration);syncConcept();}
    else setStatus('Waiting for video metadata before seeking. You can still read the explanation.');
  }
  async function playMedia() {
    try {await video.play();setStatus('Playing the recorded explanation. Use Pause & explore to change the live model.');}
    catch(error) {if(!['NotAllowedError','NotSupportedError','AbortError'].includes(error.name))throw error;setStatus(`Playback did not start (${error.name}). Use the native play control or read the transcript.`,true);}
  }
  function enterExplore() {
    returnTime=video.currentTime;video.pause();
    const cue=cueAt(returnTime);if(cue)state={...presets[cue.preset]};
    stepped=false;setFilmMode('explore');
    setStatus('Film paused. Explore the mechanism above, then return to this moment.');
    $('explore').scrollIntoView({behavior:'auto',block:'start'});
    $('bias').focus({preventScroll:true});
  }
  $('pause-explore').addEventListener('click',enterExplore);
  $('return-film').addEventListener('click',()=>{const t=returnTime;setFilmMode('film');seekTo(t);playMedia();});
  $('replay').addEventListener('click',()=>{setFilmMode('film');seekTo(0);playMedia();});
  video.addEventListener('play',()=>{
    if(filmMode==='explore'){const t=returnTime;setFilmMode('film');seekTo(t);}
    else if(filmMode!=='film')setFilmMode('film');
    syncConcept();
  });
  video.addEventListener('timeupdate',syncConcept);
  video.addEventListener('seeking',()=>{if(filmMode==='explore')setFilmMode('film');else if(filmMode==='idle')setFilmMode('film');syncConcept();});
  video.addEventListener('seeked',syncConcept);
  video.addEventListener('ended',()=>{syncConcept();setStatus('The film has ended. Replay, seek to a concept, or pause to explore.');});
  video.addEventListener('loadedmetadata',()=>{if(pendingSeek!==null)seekTo(pendingSeek);setStatus('Video ready. Play the narration or choose a concept.');syncConcept();});
  video.addEventListener('error',()=>setStatus('The video could not load or decode. Keep exploring the model, read the transcript, or open the MP4 directly.',true));
  if(cues.length){
    const transcript=document.createElement('div');
    cues.forEach(c=>{
      const b=document.createElement('button');b.type='button';b.dataset.cue=String(c.id);b.setAttribute('aria-current','false');
      const time=document.createElement('span');time.className='time';time.textContent=clock(c.start);const title=document.createElement('span');title.textContent=c.title;b.append(time,title);
      b.addEventListener('click',()=>{setFilmMode('film');seekTo(c.start);});$('chapter-list').append(b);
      const p=document.createElement('p'),link=document.createElement('button');link.type='button';link.className='transcript-seek';link.textContent=`${clock(c.start)} · ${c.text}`;link.addEventListener('click',()=>{setFilmMode('film');seekTo(c.start);});p.append(link);transcript.append(p);
    });
    $('transcript-content').replaceChildren(transcript);
    if(typeof VTTCue!=='undefined'){
      const track=video.addTextTrack('captions','English','en');
      const captions=Array.isArray(window.NeuronFilmCaptions)?window.NeuronFilmCaptions:cues;
      captions.filter(c=>Number.isFinite(c.start)&&Number.isFinite(c.end)&&c.end>c.start&&typeof c.text==='string').forEach(c=>track.addCue(new VTTCue(c.start,c.end,c.text)));track.mode='hidden';
    } else {setStatus('Native captions are unavailable in this browser. Use the full transcript or the downloadable WebVTT file.');}
  } else {
    const message=document.createElement('p');message.textContent='Concept cues are unavailable. Native video controls and the static explanation remain available.';$('chapter-list').append(message);
  }
  document.documentElement.classList.add('js');render();syncConcept();
  window.NeuronExplorer=Object.freeze({getState:()=>({...state}),getMode:()=>filmMode,getCue:()=>cueAt(video.currentTime)});
})();
