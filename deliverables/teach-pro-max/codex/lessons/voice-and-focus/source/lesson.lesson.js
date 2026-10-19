// Original examples; grammar rules are linked below. UI indices select
// qualitative examples. They are not measurements of language or certainty.
const EXAMPLES = [
  { agent: "Maya", action: "repaired", patient: "the bicycle", active: "Maya repaired the bicycle.", passive: "The bicycle was repaired", label: "a repair" },
  { agent: "The team", action: "painted", patient: "the gate", active: "The team painted the gate.", passive: "The gate was painted", label: "a painting" },
];
function languageState(p) {
  const example = EXAMPLES[Math.round(p.example)];
  const passive = Math.round(p.voice) === 1;
  const includeAgent = Math.round(p.agent) === 1;
  return { ...example, passive, includeAgent,
    sentence: passive ? `${example.passive}${includeAgent ? ` by ${example.agent === "The team" ? "the team" : example.agent}` : ""}.` : example.active,
    startsWith: passive ? example.patient : example.agent,
    pattern: passive ? "affected thing + was + past participle" : "doer + past-tense verb + object",
    information: passive && !includeAgent ? "Who did it is unstated." : "The doer is named.",
  };
}
window.LESSON = {
  id: "voice-and-focus-v3", title: "Same event. A different starting point.",
  subtitle: "See what English passive voice changes, and what it leaves intact.",
  subject: "Language · English grammar", level: "intuition → mechanism", style: "visual-explain",
  hook: "<p>You are writing about a bicycle. Starting with the bicycle keeps it as the thread of the story, even when somebody else does the work.</p>",
  sources: [
    { title: "British Council · Passives", url: "https://learnenglish.britishcouncil.org/free-resources/grammar/b1-b2/passives", note: "Why writers choose passive voice; be + past participle." },
    { title: "British Council · Active and passive voice", url: "https://learnenglish.britishcouncil.org/free-resources/grammar/english-grammar-reference/active-passive-voice", note: "Transitive verbs, by-phrases and passive forms." },
    { title: "Cambridge · Passive voice", url: "https://dictionary.cambridge.org/grammar/british-grammar/passive-voice", note: "Topic choice and optional agent. Page indexed; direct fetch returned 403 during review." },
  ],
  limits: "This lesson uses ordinary past-simple transitive clauses. It does not cover every passive construction. Sentence topic is not the same as the only important or new information; context and stress also affect focus.",
  params: {
    voice: { label: "Sentence voice", min: 0, max: 1, step: 1, value: 0, fmt: v => v < .5 ? "Active" : "Passive" },
    agent: { label: "Name the doer in the passive", min: 0, max: 1, step: 1, value: 1, fmt: v => v < .5 ? "Omit the by-phrase" : "Include the by-phrase" },
    example: { label: "Example", min: 0, max: 1, step: 1, value: 0, fmt: v => v < .5 ? "Repairing a bicycle" : "Painting a gate" },
  },
  model: languageState,
  readouts: s => [["Starts with", s.startsWith, { keepCase: true }], ["Information", s.information, { keepCase: true }]],
  figure: {
    viewBox: narrow => narrow ? "0 0 360 590" : "0 0 900 430", narrowText: 1.15,
    label: s => `In ${s.label}, ${s.agent} is the doer and ${s.patient} is affected. The selected ${s.passive ? "passive" : "active"} sentence is: ${s.sentence} ${s.information}`,
    draw(g, s, p, kit) {
      const { el, narrow } = kit;
      const W = narrow ? 360 : 900;
      el("rect", {x:0,y:0,width:W,height:narrow?590:430,fill:"#fcfcf8"});
      const text = (x,y,t,size=18,color="#263c44",anchor="start") => el("text", {x,y,text:t,"font-size":Math.max(narrow?14:16,size),fill:color,"text-anchor":anchor,"font-family":"Georgia,serif"});
      const box = (x,y,w,h,fill,stroke="#bbc8c7") => el("rect", {x,y,width:w,height:h,rx:12,fill,stroke,"stroke-width":1.5});
      const line = (x1,y1,x2,y2,color="#547a83") => el("line", {x1,y1,x2,y2,stroke:color,"stroke-width":2});
      text(20,30,"01  THE EVENT",14,"#547a83");
      const nodes = narrow ? [[18,55,150,s.agent,"DOER","#dfeeea"],[192,55,150,s.patient,"AFFECTED THING","#e7e5f3"]]
        : [[34,58,230,s.agent,"DOER","#dfeeea"],[636,58,230,s.patient,"AFFECTED THING","#e7e5f3"]];
      nodes.forEach(([x,y,w,label,role,fill]) => {box(x,y,w,82,fill);text(x+w/2,y+27,role,12,"#526567","middle");text(x+w/2,y+57,label,20,"#263c44","middle");});
      if (narrow) { line(82,153,278,153); text(180,180,s.action,19,"#526e76","middle"); }
      else { line(284,100,616,100); text(450,85,s.action,22,"#526e76","middle"); el("path",{d:"M606 94L616 100L606 106",fill:"none",stroke:"#547a83","stroke-width":2}); }
      const yy = narrow ? 224 : 188;
      text(20,yy,"02  CHOOSE THE STARTING POINT",14,"#547a83");
      const rowW = W-40;
      box(20,yy+20,rowW,narrow?103:70,s.passive?"#f8f7f2":"#dfeeea",s.passive?"#d5dcd8":"#428477");
      text(36,yy+44,"ACTIVE",12,"#426e64");
      if(narrow){text(36,yy+73,s.agent,19);text(36,yy+98,`${s.action} ${s.patient}.`,19);}else text(150,yy+63,s.active,24);
      const py=yy+(narrow?139:108);
      box(20,py,rowW,narrow?128:86,s.passive?"#e7e5f3":"#f8f7f2",s.passive?"#7d73a4":"#d5dcd8");
      text(36,py+25,"PASSIVE",12,"#6b6090");
      if(narrow){ text(36,py+56,EXAMPLES[Math.round(p.example)].passive,18);text(36,py+84,s.includeAgent ? `by ${s.agent === "The team" ? "the team" : s.agent}.` : "Doer not stated.",18);text(36,py+110,"was + past participle",14,"#6b6090"); }
      else {text(150,py+53,`${EXAMPLES[Math.round(p.example)].passive}${s.includeAgent ? ` by ${s.agent === "The team" ? "the team" : s.agent}` : ""}.`,23);text(150,py+75,"was + past participle",14,"#6b6090");}
      text(20,narrow?573:410,narrow ? (s.passive&&!s.includeAgent?"The doer is unstated, not nonexistent.":"Same event roles. A different subject.") : (s.passive&&!s.includeAgent?"Omitting the doer removes information about who.":"The roles stay the same. The sentence starts elsewhere."),narrow?14:18,"#526567");
    },
  },
  steps: [
    { id:"event", title:"Keep the event separate from word order", set:{voice:0,agent:1,example:0}, controls:["voice"],
      say:"<p>In our example, Maya does the repairing and the bicycle is affected. Those are roles in the event. In the active sentence, Maya is also the grammatical subject.</p><p>Switch to passive. The bicycle becomes the subject. Maya is still the doer.</p>",
      lookFor:"the coloured roles stay put while the sentence starts with a different participant",
      ask:{kind:"choice",q:"In 'The bicycle was repaired by Maya', who does the repairing?",options:["The bicycle","Maya","The sentence does not say"],answer:1,why:"Maya remains the doer. The bicycle is the passive subject and the affected thing."},
      note:"Grammatical subject and doer are different roles.", alts:[{label:"Follow the event",say:"Imagine watching the repair with the sound off. Changing the sentence cannot change the person holding the tools."}] },
    { id:"shape", title:"Change the sentence, not the event", set:{voice:1,agent:1,example:0}, controls:["voice","example"],
      say:"<p>These past-simple passives use <strong>was + past participle</strong>: was repaired, or was painted. A by-phrase can name the doer.</p>",
      ask:{kind:"choice",q:"Which is the passive of 'The team painted the gate'?",options:["The gate painted the team.","The gate was painted by the team.","The team was painting the gate."],answer:1,why:"'Was painted' is passive. Merely reversing the names changes who did what."},
      note:"Affected thing + was + past participle, with an optional by-phrase." },
    { id:"omission", title:"Omitting the doer loses some information", set:{voice:1,agent:0,example:0}, controls:["agent"],
      say:"<p>'The bicycle was repaired' leaves the doer unstated. It can suit a story about the bicycle when who repaired it is unknown, obvious or unimportant.</p><p>That shorter sentence does not tell its reader that Maya did it.</p>",
      ask:{kind:"choice",q:"Does 'The bicycle was repaired' identify Maya as the doer?",options:["Yes","No"],answer:1,why:"The event has a doer, but the sentence does not identify them. Omission is not evidence that nobody acted."},
      note:"Unstated is not the same as nonexistent." },
    { id:"choice", title:"Choose the form that connects the story", set:{voice:1,agent:1,example:1}, controls:["voice","agent","example"],
      say:"<p>If the gate is already your topic, 'The gate was painted' keeps that thread. If you are describing the team's work, the active sentence may fit better.</p><p>Passive is a choice about presentation. It is not automatically better, vaguer or more formal in every context.</p>",
      ask:{kind:"explain",q:"How can two sentences describe the same event but start differently?",model:"The grammatical subject can change while event roles stay the same. A passive makes the affected thing the subject; an optional by-phrase names the doer.",points:["Separate subject from doer","Keep the event roles intact","Notice what an omitted doer leaves unstated"]},
      note:"Use context, not a blanket ban on passive voice." },
  ],
  film: [
    { chapter:"The event",set:{voice:0,agent:1,example:0},say:"Maya repaired the bicycle. Maya is the doer, and the bicycle is affected. These are roles in the event." },
    { chapter:"A different subject",set:{voice:1,agent:1,example:0},say:"The bicycle was repaired by Maya. The bicycle is now the subject. Maya still does the repairing. The word order changes, while the event roles stay intact." },
    { chapter:"The passive pattern",set:{voice:1,agent:1,example:1},say:"The gate was painted by the team. For these past simple examples, the passive uses was plus a past participle. The by phrase names the doer." },
    { chapter:"The omitted doer",set:{voice:1,agent:0,example:0},say:"The bicycle was repaired. This sentence does not identify who did it. Leaving out the doer removes information about who, even though somebody still performed the action." },
    { chapter:"Choose for the context",set:{voice:1,agent:0,example:1},say:"If the gate is already the topic, starting with the gate can connect your story. Passive is a choice about presentation. Context decides which form helps the reader." },
  ],
  checks: [
    {name:"active preserves example roles",test:m=>m({voice:0,agent:1,example:0}).sentence==="Maya repaired the bicycle."},
    {name:"passive preserves named doer",test:m=>m({voice:1,agent:1,example:0}).sentence==="The bicycle was repaired by Maya."},
    {name:"omission does not invent a different doer",test:m=>m({voice:1,agent:0,example:0}).agent==="Maya"&&!m({voice:1,agent:0,example:0}).sentence.includes("Maya")},
    {name:"second example transfers same rule",test:m=>m({voice:1,agent:1,example:1}).sentence==="The gate was painted by the team."},
  ],
};
