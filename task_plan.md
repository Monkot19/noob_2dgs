# Task Plan

Last updated: 2026-07-07

## Goal

Maintain and improve this fork of 2D Gaussian Splatting for local editing plus AutoDL server execution. The immediate technical goal is to obtain a cleaner reconstruction for `reception_hall`, especially reducing floating Gaussians and wall artifacts while preserving wall text/detail.

## Current Project State

- Local repository: `D:\workspace\2DGS`
- GitHub repository: `https://github.com/Monkot19/noob_2dgs.git`
- Upstream repository: `https://github.com/hbb1/2d-gaussian-splatting.git`
- Server repository path: `/root/autodl-tmp/noob_2dgs`
- Main dataset: `/root/autodl-tmp/datasets/reception_hall_colmap`
- Main output root: `/root/autodl-tmp/outputs`

## Operating Convention

- Use `planning-with-files` throughout this project.
- At the start of future project work, read `task_plan.md`, `findings.md`, and `progress.md` before making decisions.
- After new experiments, errors, code changes, or important conclusions, update the relevant planning files before finishing.
- Keep project memory in root-level planning files; keep `.codex/` as local Codex tooling unless intentionally shared.

## Completed

- Cloned upstream 2DGS into the local workspace.
- Initialized submodules:
  - `submodules/diff-surfel-rasterization`
  - `submodules/simple-knn`
  - `submodules/diff-surfel-rasterization/third_party/glm`
- Renamed original remote to `upstream`.
- Added user GitHub repository as `origin`.
- Pushed local fork to GitHub.
- Created documentation:
  - `docs/DEPLOYMENT_WORKFLOW.md`
  - `docs/2DGS_CHINESE_WORKFLOW.md`
- Extended `convert.py`:
  - Added `--camera_per_image` for mixed image dimensions.
  - Added Mapper fallback when `--Mapper.ba_global_function_tolerance=...` is unsupported by older COLMAP.
- AutoDL environment reached a runnable state:
  - PyTorch CUDA works.
  - `diff_surfel_rasterization` imports successfully.
  - `simple_knn` imports successfully.
- COLMAP conversion succeeded for `reception_hall_colmap`:
  - 129 registered images.
  - 9715 sparse points.
  - Mean track length about 6.9.
  - Mean reprojection error about 0.96 px.
- Rendering reached image/video export; missing `ffmpeg` was identified as the blocker for MP4 video writing.
- Expanded Chinese workflow documentation with train/render parameter guide and context migration instructions.
- Created and committed persistent planning files:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
- Loaded the project-local `planning-with-files` skill and confirmed existing planning files are the active project memory.

## In Progress

- Tuning `train.py` parameters for `reception_hall_colmap`.
- Balancing:
  - reducing floating colored Gaussians,
  - keeping walls flat,
  - preserving wall text and high-frequency visual details,
  - producing cleaner mesh output.

## Planned Experiments

### Balanced Indoor Scene

Use when floaters are improved but text/detail should remain readable.

```bash
python train.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_balanced_v1 \
  --depth_ratio 0 \
  --lambda_normal 0.05 \
  --lambda_dist 50 \
  --opacity_cull 0.08 \
  --densify_grad_threshold 0.0003
```

### Detail-Preserving Indoor Scene

Use when wall text or small signs are blurred or become geometry protrusions.

```bash
python train.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_detail_r1 \
  -r 1 \
  --depth_ratio 0 \
  --lambda_normal 0.03 \
  --lambda_dist 10 \
  --opacity_cull 0.08 \
  --densify_grad_threshold 0.00025
```

### Strong Floater Cleanup

Use only when floaters dominate and texture detail is less important.

```bash
python train.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_clean_v2 \
  --depth_ratio 0 \
  --lambda_normal 0.1 \
  --lambda_dist 100 \
  --opacity_cull 0.1 \
  --densify_grad_threshold 0.0004 \
  --densify_until_iter 12000
```

## Render/Mesh Follow-Up

After each training run, render without mesh first:

```bash
python render.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/<run_name> \
  --skip_mesh
```

Then test unbounded mesh:

```bash
python render.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/<run_name> \
  --unbounded \
  --skip_train \
  --skip_test \
  --mesh_res 1024 \
  --num_cluster 20
```

## Risks

- Direct Gaussian point cloud visualization may look messy even when novel-view rendering is acceptable.
- Strong geometry regularization can convert high-frequency wall text into artificial protrusions.
- Lower regularization preserves texture but may reintroduce floaters.
- COLMAP quality is acceptable but sparse point count is not very high for an indoor scene; weak/repetitive texture may still hurt geometry.
- Current AutoDL system COLMAP may be `without CUDA` unless a custom COLMAP build is installed.
- `ffmpeg` may be missing on AutoDL, blocking MP4 creation from `render.py --render_path`.
- Local Windows environment is not the primary runtime; server Ubuntu is the preferred execution environment.

## Next Steps

1. Pull the latest repository state on AutoDL if needed:
   ```bash
   cd /root/autodl-tmp/noob_2dgs
   git pull --ff-only
   ```
2. Run or inspect `reception_hall_balanced_v1`.
3. Compare:
   - rendered train views,
   - trajectory video if `ffmpeg` is installed,
   - visual amount of floaters,
   - wall text readability,
   - mesh cleanliness.
4. If wall text remains degraded, run `reception_hall_detail_r1`.
5. If floaters remain unacceptable, run `reception_hall_clean_v2`.
6. Record each experiment result in `progress.md`.
7. If a code-level improvement becomes necessary, implement locally, commit, push, then update the server with `git pull --ff-only`.
