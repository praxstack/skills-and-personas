import {readFileSync} from 'node:fs';import vm from 'node:vm';
const [root]=process.argv.slice(2);const load=n=>{const c={window:{}};vm.createContext(c,{codeGeneration:{strings:false,wasm:false}});vm.runInContext(readFileSync(`${root}/${n}.lesson.js`,'utf8'),c,{timeout:2000});return c.window.LESSON;};
const base=load('base-rates'),diff=load('diffusion'),voice=load('voice-and-focus');
const b=[];for(let prior=1;prior<=50;prior++)for(let hit=50;hit<=100;hit++)for(let falseRate=0;falseRate<=20;falseRate++)b.push([prior,hit,falseRate,base.model({base:prior,hit,falseRate})]);
const d=[];for(let initialLeft=0;initialLeft<=60;initialLeft++)for(let j=0;j<=10;j++)for(let ticks=0;ticks<=20;ticks++){const p={initialLeft,cross:j/20,ticks},s=diff.model(p),dots=[];for(const narrow of [false,true]){let n=0;diff.figure.draw(null,s,p,{narrow,el:(tag,attrs)=>{if(tag==='circle')n++;}});dots.push(n);}d.push([initialLeft,j,ticks,s,dots]);}
const v=[];for(let example=0;example<=1;example++)for(let voiceIndex=0;voiceIndex<=1;voiceIndex++)for(let agent=0;agent<=1;agent++)v.push([{example,voice:voiceIndex,agent},voice.model({example,voice:voiceIndex,agent})]);
process.stdout.write(JSON.stringify({base:b,diffusion:d,voice:v}));
