const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function worker(){
 const data={},listeners=[];const context=vm.createContext({console,AbortSignal,fetch:async()=>{throw Error('offline')},chrome:{storage:{local:{get:async key=>key===null?structuredClone(data):{[key]:structuredClone(data[key])},set:async patch=>Object.assign(data,structuredClone(patch)),remove:async keys=>{for(const k of Array.isArray(keys)?keys:[keys])delete data[k];}}},runtime:{onMessage:{addListener:fn=>listeners.push(fn)},onInstalled:{addListener:()=>{}}}}});
 context.importScripts=(...names)=>names.forEach(n=>vm.runInContext(fs.readFileSync(path.join(__dirname,'..',n),'utf8'),context));
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../background.js'),'utf8'),context);
 return {data,send:m=>new Promise(resolve=>listeners[0](m,{},resolve))};
}
test('service worker : consentement, concurrence, totaux primaires, reset',async()=>{
 const w=worker();await w.send({type:'FC_EVENT',kind:'watch',videoId:'v',seconds:4,category:'sport'});assert.equal(w.data.statsV4,undefined);
 w.data.tracking=true;w.data.version=4;w.data.favorites=['sport'];
 await Promise.all(Array.from({length:20},()=>w.send({type:'FC_EVENT',kind:'watch',videoId:'v',seconds:4,category:'sport'})));
 const d=Object.values(w.data.statsV4.days)[0];assert.equal(d.seconds,80);assert.equal(d.views,1);assert.equal(d.categories.sport.seconds,80);assert.equal(d.favoredSeconds,80);
 await w.send({type:'FC_CLEAR'});assert.equal(w.data.statsV4,undefined);
});
test('service worker : serveur arrêté = dégradé honnête ; retour persistant',async()=>{
 const w=worker();assert.equal((await w.send({type:'FC_STATUS'})).status,'offline');
 const v=await w.send({type:'FC_CLASSIFY',video:{videoId:'x',title:'Football analyse tactique'}});assert.equal(v.degraded,true);assert.equal(v.method,'heuristic_text');
 const res=await w.send({type:'FC_DISCOVER',topics:['sport']});assert.ok(res.error);assert.equal(res.videos,undefined);
 await w.send({type:'FC_FEEDBACK',videoId:'x',verdict:'wrong'});assert.equal(w.data.feedback.x.verdict,'wrong');
});
