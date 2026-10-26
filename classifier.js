/* Analyse de texte explicable : aucune vision, aucune promesse d'IA en mode local. */
const FeedControlClassifier = (() => {
 const TAX=typeof FeedControlTaxonomy!=='undefined'?FeedControlTaxonomy:require('./taxonomy.js');
 const RULES=typeof FeedControlRules!=='undefined'?FeedControlRules:require('./classification_rules.js');
 const POSITIVE=Object.keys(TAX).slice(0,16),NEGATIVE=Object.keys(TAX).slice(16);
 const LABELS=Object.fromEntries(Object.entries(TAX).map(([k,v])=>[k,v.label]));LABELS.autre='Non classé';
 const DEFAULTS={version:4,enabled:true,favorites:[],blocked:['brainrot','suggestif'],mode:'favor',shortsOff:false,quality:false,hideUnknown:false,educationalShorts:true,thumbnailAnalysis:true,qualityLevel:'balanced',discovery:false,smallCreators:false,subscriberThreshold:50000,feedThreshold:8,tracking:false,retentionDays:30};
 const normalize=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,' ').trim();
 const has=(text,term)=>(' '+text+' ').includes(' '+normalize(term)+' ');
 function migrate(raw={}){
  const s={...DEFAULTS,...raw};
  if(raw.version!==4){s.favorites=(raw.only||[]).flatMap(c=>c==='culture'?['histoire','philosophie','documentaires']:[c]);s.mode=raw.only?.length?'only':'favor';}
  s.favorites=(s.favorites||[]).filter(c=>POSITIVE.includes(c));s.blocked=(s.blocked||[]).filter(c=>Object.hasOwn(TAX,c));
  s.retentionDays=Math.max(1,Math.min(90,Number(s.retentionDays)||30));return s;
 }
 function classify(input){
  const v=typeof input==='string'?{title:input}:input;const visual=v.visualAnalysis;const text=normalize((v.title||'')+' '+(v.description||'')+' '+(v.channelTitle||'')+' '+(visual?.status==='analyzed'?visual.ocrText||'':''));
  const matches=Object.entries(TAX).filter(([k,t])=>k!=='shorts'&&t.terms.some(x=>has(text,x))).map(([k])=>k);
  const topics=matches.filter(k=>POSITIVE.includes(k));const flags=matches.filter(k=>NEGATIVE.includes(k));
  let contentType='inconnu',qualityScore=.5,qualityConfidence=.15;
  const evidence=[];
  if(flags.length){contentType=flags.includes('viral')||flags.includes('brainrot')?'compilation_virale':flags[0];qualityScore=.15;qualityConfidence=.75;evidence.push('Indices textuels : '+flags.join(', '));}
  else {
   const rules=RULES.types;
   const rule=rules.find(([,terms])=>terms.some(x=>has(text,x)));
   if(rule){[contentType,,qualityScore]=rule;qualityConfidence=.65;evidence.push('Indices textuels de type '+contentType+' ; qualité non vérifiée.');}
  }
  if(RULES.motivationTerms.some(term=>has(text,term))&&!topics.includes('motivation')){topics.push('motivation');evidence.push('Vocabulaire de motivation identifié dans le texte disponible.');}
  let presentationRisk=0;
  if(visual?.status==='analyzed'){const sig=visual.signals||{};if(sig.redCircleLikeCount||sig.redArrowLikeCount){evidence.push('Miniature analysée : formes rouges compatibles avec des cercles/flèches (indice de présentation, pas preuve de tromperie).');presentationRisk=.7;}if(sig.monochrome)evidence.push('Miniature principalement monochrome : le style seul ne détermine pas le thème.');if(visual.learned?.scene)evidence.push('Modèle visuel : '+visual.learned.scene);if(visual.learned?.montage)presentationRisk=Math.min(1,presentationRisk+.15);if(presentationRisk>=.7&&contentType==='inconnu'){qualityScore=.35;qualityConfidence=.55;}}
  if(!evidence.length)evidence.push('Informations insuffisantes pour évaluer la qualité.');
  return {...v,topics,flags,presentationRisk,thumbnailAnalyzed:visual?.status==='analyzed',category:topics[0]||'autre',contentType,qualityScore,qualityConfidence,evidence,blockedReasons:[],recommendationReasons:[],method:'heuristic_text',limitations:visual?.status==='analyzed'?'Texte et miniature examinés ; vidéo non regardée. Indices visuels incertains, aucune personne identifiée.':'Miniature non analysée ; jugement limité au texte disponible.'};
 }
 function decide(input,settings={},isShort=false,feedback={}){
  const s=migrate({...DEFAULTS,...settings}),v=typeof input==='string'?classify(input):input;
  const topics=v.topics||[],fav=topics.some(t=>s.favorites.includes(t));let blockedReasons=[];
  if(s.enabled){
   if(isShort&&s.shortsOff)blockedReasons.push('Shorts désactivés');
   for(const c of [...(v.flags||[]),...topics])if(s.blocked.includes(c))blockedReasons.push('Exclusion : '+(LABELS[c]||c));
   if(s.hideUnknown&&!topics.length)blockedReasons.push('Vidéo non classée — exclusion demandée');
   if(isShort&&s.educationalShorts&&!['analyse','cours','educatif','documentaire'].includes(v.contentType))blockedReasons.push('Short sans indice suffisant d’analyse ou d’apprentissage');
   if(s.blocked.includes('clickbait')&&v.presentationRisk>=.7&&!['analyse','cours','educatif','documentaire'].includes(v.contentType))blockedReasons.push('Présentation potentiellement racoleuse : annotations rouges sur la miniature');
   if(s.mode==='only'&&s.favorites.length&&!fav)blockedReasons.push(topics.length?'Hors de vos thèmes':'Thème inconnu — non validé');
   const thresholds={soft:[.4,.35],balanced:[.65,.55],strict:[.8,.65]},[q,c]=thresholds[s.qualityLevel]||thresholds.balanced;
   if(s.quality&&!(v.degraded&&s.mode==='favor'&&!topics.length)&&(v.qualityScore<q||v.qualityConfidence<c))blockedReasons.push('Qualité insuffisante ou incertaine');
  }
  const reasons=[...(v.evidence||[])];if(v.degraded&&!topics.length)reasons.push('Thème inconnu : serveur indisponible ; aucune validation sémantique.');if(fav)reasons.push('Correspond à vos thèmes');
  let score=(fav?2:0)+(v.qualityScore||0)*(v.qualityConfidence||0);
  if(s.smallCreators&&fav&&v.subscriberCount!=null&&v.subscriberCount<s.subscriberThreshold&&v.qualityScore>=.65&&v.qualityConfidence>=.55){score+=1.25;reasons.push(`Petite chaîne : ${v.subscriberCount} abonnés publics`);}
  if(feedback.verdict==='relevant'){score+=.25;reasons.push('Vous avez indiqué : pertinente');}
  if(feedback.verdict==='irrelevant'){score-=1;reasons.push('Vous avez indiqué : pas pertinente');}
  if(feedback.verdict==='wrong'){score-=.2;reasons.push('Classification signalée incorrecte — à vérifier');}
  return {...v,visible:!blockedReasons.length,blockedReasons,recommendationReasons:reasons,rank:score,favored:fav};
 }
 function potentialShort(video){
  const m=String(video.duration||'').match(/^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$/);
  return !m||((Number(m[1]||0)*3600+Number(m[2]||0)*60+Number(m[3]||0))<=180);
 }
 function watchDelta(previous,current,wallSeconds){
  if(!previous||!current.active||!previous.active||previous.id!==current.id)return 0;
  const delta=current.time-previous.time;
  return delta>0&&delta<=wallSeconds*Math.max(current.rate||1,1)+.5?Math.min(delta,wallSeconds):0;
 }
 return {TAX,RULES,POSITIVE,NEGATIVE,LABELS,DEFAULTS,normalize,migrate,classify,decide,watchDelta,potentialShort};
})();
if(typeof module!=='undefined')module.exports=FeedControlClassifier;
