const {test}=require('node:test'),assert=require('node:assert/strict');
const C=require('../classifier.js'),fixtures=require('./videos.json');
for(const f of fixtures)test(f.title,()=>{const v=C.classify(f.title);if(f.topic)assert.ok(v.topics.includes(f.topic));else assert.equal(v.topics.length,0);assert.equal(C.decide(v,{quality:true}).visible,f.quality);assert.ok(v.evidence.length);console.log(JSON.stringify({title:f.title,topics:v.topics,qualityScore:v.qualityScore,qualityConfidence:v.qualityConfidence,reasons:v.evidence}));});
test('exclusions > thèmes ; favoriser distinct de uniquement ; Shorts',()=>{
 const v=C.classify('Football analyse tactique');assert.equal(C.decide(v,{favorites:['bricolage']}).visible,true);assert.equal(C.decide(v,{mode:'only',favorites:['bricolage']}).visible,false);
 assert.equal(C.decide(v,{favorites:['sport'],blocked:['sport']}).visible,false);assert.equal(C.decide(v,{shortsOff:true},true).visible,false);
 assert.equal(C.decide(C.classify('inconnu'),{mode:'only',favorites:['sport']}).visible,false);
 assert.equal(C.decide(C.classify('Football demain'),{quality:true,qualityLevel:'strict'}).visible,false);
 assert.equal(C.decide(C.classify('Sport training'),{quality:true,qualityLevel:'soft'}).visible,true);
});
test('petite chaîne seulement si pertinente et sans qualité inventée',()=>{
 const a={...C.classify('Bricolage tutoriel'),subscriberCount:3200};const b={...C.classify('Football full match'),subscriberCount:1000000};
 assert.ok(C.decide(a,{favorites:['bricolage'],smallCreators:true}).rank>C.decide(b,{favorites:['bricolage'],smallCreators:true}).rank);
 const unknown={...C.classify('rien'),subscriberCount:2};assert.equal(C.decide(unknown,{favorites:['bricolage'],smallCreators:true,quality:true}).visible,false);
 assert.ok(!C.decide({...a,subscriberCount:null},{favorites:['bricolage'],smallCreators:true}).recommendationReasons.some(x=>x.includes('abonnés')));
});
test('temps actif ; pause, arrière-plan, recherche et changement de vidéo',()=>{
 const a={id:'x',time:10,active:true,rate:1};assert.equal(C.watchDelta(a,{...a,time:11},1),1);
 assert.equal(C.watchDelta(a,{...a,time:11,active:false},1),0);assert.equal(C.watchDelta({...a,active:false},{...a,time:11},1),0);
 assert.equal(C.watchDelta(a,{...a,time:90},1),0);assert.equal(C.watchDelta(a,{...a,time:11,id:'y'},1),0);assert.equal(C.watchDelta(a,{...a,time:10},1),0);
});
test('migration V3 et taxonomie commune',()=>{assert.deepEqual(C.migrate({only:['culture']}).favorites,['histoire','philosophie','documentaires']);assert.deepEqual(C.TAX,require('../taxonomy.json'));});

test('Shorts découverte : exclusion prudente des durées courtes ou inconnues',()=>{assert.equal(C.potentialShort({duration:'PT3M'}),true);assert.equal(C.potentialShort({duration:'PT4M'}),false);assert.equal(C.potentialShort({}),true);assert.equal(C.potentialShort({duration:'PT1H2M3S'}),false);});

test('favoriser en mode dégradé préserve les inconnues sans les valider',()=>{const v={...C.classify('inconnu'),degraded:true};assert.equal(C.decide(v,{mode:'favor',quality:true}).visible,true);assert.equal(C.decide(v,{mode:'only',favorites:['science'],quality:true}).visible,false);});

test('régression motivation : punchline et OCR sans inférer qualité depuis un portrait',()=>{
 const a=C.classify('FOCUS IN LIFE — stay focused');assert.ok(a.topics.includes('motivation'));assert.equal(a.qualityConfidence,.15);
 const b=C.classify({title:'Episode 8',visualAnalysis:{status:'analyzed',ocrText:'FOCUS ON YOURSELF',signals:{monochrome:true}}});assert.ok(b.topics.includes('motivation'));
 const c=C.classify({title:'Episode 9',visualAnalysis:{status:'analyzed',ocrText:'',signals:{monochrome:true}}});assert.deepEqual(c.topics,[]);
});
test('régression Shorts : sport ne garantit ni pédagogie ni qualité',()=>{
 assert.equal(C.decide(C.classify('football insane highlights'),{},true).visible,false);
 assert.equal(C.decide(C.classify('Football analyse tactique'),{},true).visible,true);
 assert.equal(C.decide(C.classify('Football full match'),{},true).visible,false);
 assert.equal(C.decide(C.classify('Football full match'),{},false).visible,true);
 assert.equal(C.decide(C.classify('titre inconnu'),{hideUnknown:true}).visible,false);
});
test('miniatures : annotations suspectes filtrables, diagramme pédagogique conservé',()=>{
 const visualAnalysis={status:'analyzed',ocrText:'',signals:{redCircleLikeCount:1}};
 const risky=C.classify({title:'Football surprise',visualAnalysis});assert.equal(risky.thumbnailAnalyzed,true);assert.equal(C.decide(risky,{blocked:['clickbait']}).visible,false);
 const diagram=C.classify({title:'Football analyse tactique',visualAnalysis});assert.equal(C.decide(diagram,{blocked:['clickbait'],quality:true}).visible,true);
});
test('petits créateurs : bonus significatif réservé aux candidats de qualité',()=>{
 const v=C.classify('Cuisine recette pas à pas');const small={...v,subscriberCount:2000},big={...v,subscriberCount:200000};
 assert.ok(C.decide(small,{favorites:['cuisine'],smallCreators:true}).rank-C.decide(big,{favorites:['cuisine'],smallCreators:true}).rank>=1);
 const unknown={...C.classify('Cuisine demain'),subscriberCount:100};assert.ok(!C.decide(unknown,{favorites:['cuisine'],smallCreators:true}).recommendationReasons.some(t=>t.includes('Petite chaîne')));
 assert.deepEqual(C.RULES,require('../classification_rules.json'));
});
