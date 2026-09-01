(()=>{
// Stable review build: signal-quality logic is being consolidated into the primary render path.
// This file intentionally performs no delayed DOM rewrites, no secondary window.load(),
// and no placeholder section injection. Keeping it inert prevents flash/reflow while the
// underlying signal calculations remain available from market_context and options-risk data.
})();
