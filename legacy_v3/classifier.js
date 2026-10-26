const FeedControlClassifier = (() => {
 const LABELS={brainrot:'Brainrot',motivation:'Motivation',culture:'Culture',science:'IA et sciences',sport:'Sport',suggestif:'Contenus suggestifs',autre:'Autres'};
 const POSITIVE=['motivation','culture','science','sport'];
 const NEGATIVE=['brainrot','suggestif'];
 const TERMS={
 brainrot:['brainrot','skibidi','skibidi toilet','skipidi','skibidi toilets','sigma meme','rizz','fanum tax','italian brainrot','tralalero','tung tung','ohio meme','gyatt','meme compilation'],
 motivation:['motivation','discipline','mindset','developpement personnel','productivite','deep work','self improvement','habitudes','procrastination','study with me','stoicisme','stoicism'],
 culture:['culture generale','histoire','history','geographie','philosophie','documentaire','documentary','litterature','civilisation','musee','archeologie','renaissance'],
 science:['intelligence artificielle','machine learning','deep learning','neural network','reseau de neurones','mathematiques','maths','python','informatique','algorithme','physique','science','coding','chatgpt'],
 sport:['football','basketball','handball','tennis','rugby','champions league','musculation','marathon','natation','nba','ligue 1'],
 suggestif:['twerk','twerking','thirst trap','sexy dance','bikini haul','lingerie haul','nude prank','danse sensuelle']};
 const DEFAULTS={enabled:true,only:[],blocked:['brainrot','suggestif'],shortsOff:false,shortsFilter:true};
 const normalize=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,' ').trim();
 function classify(title){const text=' '+normalize(title)+' ';let best={category:'autre',score:0,matches:[]};for(const [category,terms] of Object.entries(TERMS)){const matches=terms.filter(term=>text.includes(' '+normalize(term)+' '));const score=matches.reduce((a,b)=>a+(b.includes(' ')?2:1),0);if(score>best.score){best={category,score,matches};}}return best;}
 function decide(title,settings={},isShort=false){const s={...DEFAULTS,...settings};const c=classify(title);let reason='autorise',visible=true;
 if(s.enabled){if(isShort&&s.shortsOff){visible=false;reason='shorts_desactives';}else if(!isShort||s.shortsFilter){if(s.blocked.includes(c.category)){visible=false;reason='categorie_bloquee';}else if(s.only.length&&!s.only.includes(c.category)){visible=false;reason='hors_selection';}}}
 return {...c,visible,reason};}
 return {LABELS,POSITIVE,NEGATIVE,TERMS,DEFAULTS,normalize,classify,decide};
})();
if(typeof module!=='undefined')module.exports=FeedControlClassifier;
