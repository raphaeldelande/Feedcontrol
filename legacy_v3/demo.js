// Titres inventés pour rendre la démonstration reproductible et hors ligne.
const VIDEOS = [
  "SKIBIDI : le brainrot ultime en 60 secondes",
  "Les meilleures compilations de sigma memes",
  "Comprendre le phénomène Italian brainrot",
  "La discipline bat la motivation : 5 habitudes",
  "Deep Work : comment arrêter la procrastination",
  "Comment réussir ses études sans s'épuiser : motivation",
  "Documentaire : l'histoire de la Rome antique",
  "Culture générale : 10 dates qui ont changé le monde",
  "Philosophie : comprendre le stoïcisme",
  "Intelligence artificielle : comprendre les réseaux de neurones",
  "Maths : pourquoi le produit scalaire est utile",
  "Python : programmer son premier algorithme",
  "Football : les plus beaux buts de la Champions League",
  "Handball : entraînement sportif des champions",
  "Twerk dance : viral challenge",
  "Thirst trap : compilation de clips",
  "Quel appareil photo choisir pour voyager ?",
  "Comment cuisiner des pâtes au pesto ?"
];
let settings = { ...FeedControlClassifier.DEFAULTS, mode: "all", category: "brainrot", blockSuggestive: true };
const cards = document.querySelector("#videos");

function draw() {
  const approved = VIDEOS.map(title => ({ title, ...FeedControlClassifier.decide(title, settings) }));
  const visible = approved.filter(video => video.visible);
  cards.replaceChildren();
  for (const video of visible) {
    const article = document.createElement("article");
    article.className = "video";
    const thumb = document.createElement("div");
    thumb.className = `thumb ${video.category}`;
    thumb.textContent = FeedControlClassifier.LABELS[video.category].slice(0, 2).toUpperCase();
    const body = document.createElement("div");
    body.className = "video-body";
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = FeedControlClassifier.LABELS[video.category];
    const title = document.createElement("h3");
    title.textContent = video.title;
    const why = document.createElement("div");
    why.className = "reason";
    why.textContent = video.matches.length ? `Mot-clé : ${video.matches[0]}` : "Aucun mot-clé reconnu";
    body.append(pill,title,why);
    article.append(thumb,body);
    cards.append(article);
  }
  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Aucune vidéo ne correspond aux filtres sélectionnés. Choisis une autre catégorie ou désactive une restriction.";
    cards.append(empty);
  }
  document.querySelector("#visible-count").textContent = visible.length;
  document.querySelector("#hidden-count").textContent = approved.length - visible.length;
  document.querySelector("#detail").textContent = settings.mode === "all" ? "Toutes les vidéos, sauf restrictions supplémentaires." :
    `${settings.mode === "only" ? "Seulement" : "Sans"} ${FeedControlClassifier.LABELS[settings.category]}`;
  document.querySelector("#category").value = settings.category;
  document.querySelector("#block-suggestive").checked = settings.blockSuggestive;
  document.querySelectorAll("[data-mode]").forEach(button => {
    button.classList.toggle("active", button.dataset.mode === settings.mode);
    button.setAttribute("aria-pressed", button.dataset.mode === settings.mode ? "true" : "false");
  });
}
function update(patch) {
  settings = {...settings,...patch};
  settings.only = settings.mode === "only" ? [settings.category] : [];
  settings.blocked = [...new Set([
    ...(settings.mode === "hide" ? [settings.category] : []),
    ...(settings.blockSuggestive ? ["suggestif"] : [])
  ])];
  chrome.storage.local.set(settings);
  draw();
}
chrome.storage.local.get(FeedControlClassifier.DEFAULTS).then(saved => {
  settings = {...settings, ...saved};
  draw();
});
document.querySelector("#category").addEventListener("change", e => update({category:e.target.value}));
document.querySelector("#block-suggestive").addEventListener("change", e => update({blockSuggestive:e.target.checked}));
document.querySelectorAll("[data-mode]").forEach(button=>button.addEventListener("click",()=>update({mode:button.dataset.mode})));
chrome.storage.onChanged.addListener((changes,area) => {
  if (area !== "local") return;
  for (const [key, change] of Object.entries(changes)) settings[key] = change.newValue;
  draw();
});
draw();
