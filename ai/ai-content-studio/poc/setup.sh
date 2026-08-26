#!/usr/bin/env bash
# One-shot setup: ComfyUI + Flux.1-dev in /workspace/aistudio
set -euo pipefail
ROOT=/workspace/aistudio
mkdir -p "$ROOT" && cd "$ROOT"

echo "== 1/4 system deps"
apt-get update -qq && apt-get install -y -qq aria2 >/dev/null

echo "== 2/4 ComfyUI"
[ -d ComfyUI ] || git clone -q https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -q --upgrade pip
# RTX 5090 (Blackwell, sm_120) needs a recent CUDA 12.8+ torch build
pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -q -r requirements.txt
[ -d custom_nodes/ComfyUI-Manager ] || git clone -q https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager
pip install -q -r custom_nodes/ComfyUI-Manager/requirements.txt

echo "== 3/4 models (Flux.1-dev fp16 ~24GB + encoders + VAE)"
DL(){ [ -f "$2/$(basename "$1")" ] || aria2c -q -x16 -s16 -d "$2" "$1"; }
DL https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev.safetensors                              models/diffusion_models
DL https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors                   models/text_encoders
DL https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors               models/text_encoders
DL https://huggingface.co/Comfy-Org/Lumina_Image_2.0_Repackaged/resolve/main/split_files/vae/ae.safetensors   models/vae
DL https://huggingface.co/Kim2091/UltraSharp/resolve/main/4x-UltraSharp.pth                                  models/upscale_models

echo "== 4/4 helper scripts"
mkdir -p "$ROOT/output" "$ROOT/prompts"
cat > "$ROOT/start.sh" <<'S'
#!/usr/bin/env bash
cd /workspace/aistudio/ComfyUI
nohup python main.py --listen 0.0.0.0 --port 8188 --output-directory /workspace/aistudio/output > /workspace/aistudio/comfy.log 2>&1 &
echo "ComfyUI starting on :8188 — log: /workspace/aistudio/comfy.log"
S
chmod +x "$ROOT/start.sh"

# CLI generator: gen.sh "prompt" [count] [WxH]
cat > "$ROOT/gen.py" <<'P'
import json, sys, time, random, urllib.request, os
prompt = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
w, h = (map(int, sys.argv[3].split('x')) if len(sys.argv) > 3 else (1024, 1024))
wf = json.load(open('/workspace/aistudio/workflow_api.json'))
wf["6"]["inputs"]["text"] = prompt
wf["31"]["inputs"]["width"], wf["31"]["inputs"]["height"] = w, h; wf["30"]["inputs"]["width"], wf["30"]["inputs"]["height"] = w, h
wf["31"]["inputs"]["batch_size"] = n
wf["25"]["inputs"]["noise_seed"] = random.randint(0, 2**32)
req = urllib.request.Request("http://127.0.0.1:8188/prompt", json.dumps({"prompt": wf}).encode(), {"Content-Type": "application/json"})
pid = json.load(urllib.request.urlopen(req))["prompt_id"]
print("queued", pid)
while True:
    time.sleep(2)
    h = json.load(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{pid}"))
    if pid in h:
        for o in h[pid]["outputs"].values():
            for im in o.get("images", []): print("/workspace/aistudio/output/" + im["filename"])
        break
P
cat > "$ROOT/gen.sh" <<'G'
#!/usr/bin/env bash
python3 /workspace/aistudio/gen.py "$@"
G
chmod +x "$ROOT/gen.sh"

# Minimal Flux-dev API workflow
cat > "$ROOT/workflow_api.json" <<'W'
{
 "6":  {"class_type":"CLIPTextEncode","inputs":{"text":"","clip":["11",0]}},
 "8":  {"class_type":"VAEDecode","inputs":{"samples":["13",0],"vae":["10",0]}},
 "9":  {"class_type":"SaveImage","inputs":{"filename_prefix":"flux","images":["8",0]}},
 "10": {"class_type":"VAELoader","inputs":{"vae_name":"ae.safetensors"}},
 "11": {"class_type":"DualCLIPLoader","inputs":{"clip_name1":"t5xxl_fp16.safetensors","clip_name2":"clip_l.safetensors","type":"flux"}},
 "12": {"class_type":"UNETLoader","inputs":{"unet_name":"flux1-dev.safetensors","weight_dtype":"default"}},
 "13": {"class_type":"SamplerCustomAdvanced","inputs":{"noise":["25",0],"guider":["22",0],"sampler":["16",0],"sigmas":["17",0],"latent_image":["31",0]}},
 "16": {"class_type":"KSamplerSelect","inputs":{"sampler_name":"euler"}},
 "17": {"class_type":"BasicScheduler","inputs":{"scheduler":"simple","steps":28,"denoise":1.0,"model":["30",0]}},
 "22": {"class_type":"BasicGuider","inputs":{"model":["30",0],"conditioning":["26",0]}},
 "25": {"class_type":"RandomNoise","inputs":{"noise_seed":0}},
 "26": {"class_type":"FluxGuidance","inputs":{"guidance":3.5,"conditioning":["6",0]}},
 "30": {"class_type":"ModelSamplingFlux","inputs":{"max_shift":1.15,"base_shift":0.5,"width":1024,"height":1024,"model":["12",0]}},
 "31": {"class_type":"EmptySD3LatentImage","inputs":{"width":1024,"height":1024,"batch_size":1}}
}
W
echo "== DONE. Run: /workspace/aistudio/start.sh"
du -sh "$ROOT/ComfyUI/models"
