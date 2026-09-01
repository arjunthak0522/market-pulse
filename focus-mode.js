(()=>{
// Stable review boot: focus-mode styling is loaded statically in <head>.
// Do not dynamically load scripts/styles or rewrite/reorder the DOM after first paint.
document.body.classList.add('focus-mode');
})();
