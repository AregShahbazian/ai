# POC — local Flux-schnell on the laptop

Repo: `~/git/ai-content-studio/` (scripts staged; `ComfyUI/`, models, `output/` ignored).
Pod variant of setup: `~/ai/ai-content-studio/poc/setup.sh` (Flux-dev, RTX 5090).

## Stack
- ComfyUI (CPU mode, venv in `ComfyUI/.venv`) + ComfyUI-GGUF node
- Model: Flux.1-schnell Q8 GGUF (12.7 GB) + T5-XXL fp8 + CLIP-L + Flux VAE
- Laptop: Meteor Lake iGPU (unused), 30 GB RAM → ~3–8 min per 1024² image, 4 steps

## Use
```
cd ~/git/ai-content-studio
./start.sh                       # ComfyUI on http://127.0.0.1:8188 (UI usable in browser)
./gen.sh "prompt" [count] [WxH]  # e.g. ./gen.sh "a red apple" 2 768x1024
```
Output: `~/git/ai-content-studio/output/flux_*.png`. Log: `comfy.log`.
Workflow used by gen.sh: `workflow_api.json` (edit steps/guidance/seed there or in the UI).

## Prompting Flux
- Natural sentences, not keyword soup (T5 understands grammar). 30–80 words is the sweet spot.
- Order: subject → clothing/pose → setting → lighting → camera ("85mm, f/2, shallow depth of field").
- No negative prompts (Flux ignores them); say what you want instead.
- Photoreal boosters: "candid photograph", "natural skin texture", "soft window light", named camera/lens.
- Avoid: "masterpiece, 8k, best quality" — SD-era noise, hurts Flux.
- Schnell = 4 steps, guidance fixed. Dev (on GPU) = 20–28 steps, guidance 3–4, better hands/text.

## Finetuning (later, GPU only)
- Persona consistency = train a **LoRA** on 15–30 pics of one (generated) face: ai-toolkit or kohya, ~1 h on a 4090, ~€1.
- Workflow: generate candidate face → pick 20 best angles → train LoRA → load LoRA in workflow → every image is the same person.
- Not feasible on CPU.

## Reference photos of women (style targets)
- Not needed for a plain text-to-image POC; Flux-schnell already has strong photoreal priors.
- Useful later for img2img / IP-Adapter / LoRA training data — keep in `~/git/ai-content-studio/refs/` (gitignored).
