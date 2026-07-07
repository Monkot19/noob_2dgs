# Progress

Last updated: 2026-07-07

## Current Status

The project is operational on AutoDL. The current focus is experiment management and reconstruction-quality tuning for `reception_hall_colmap`.

## Timeline

### 2026-07-02

- Cloned upstream 2DGS into `D:\workspace\2DGS`.
- Initialized submodules.
- Created GitHub repository `Monkot19/noob_2dgs`.
- Pushed local repository to GitHub.
- Created deployment workflow documentation.
- Attempted local Windows environment setup; local runtime was deprioritized due PyTorch/CUDA issues.

### 2026-07-06

- Deployed repository on AutoDL.
- Confirmed server CUDA/PyTorch and CUDA extensions work.
- Handled COLMAP conversion issues:
  - Qt display failure.
  - OpenGL context failure.
  - CPU feature extraction memory pressure.
  - System COLMAP without CUDA.
  - Mixed image dimensions.
- Modified `convert.py` for:
  - `--camera_per_image`
  - Mapper compatibility fallback
- Converted `reception_hall_colmap` successfully.
- Trained initial models.
- Rendered outputs and found `ffmpeg` missing for video writing.
- Created and expanded Chinese workflow documentation.

### 2026-07-07

- Expanded `docs/2DGS_CHINESE_WORKFLOW.md` with:
  - detailed `train.py` parameters,
  - detailed `render.py` parameters,
  - typical scene presets,
  - artifact-to-parameter troubleshooting,
  - context migration notes.
- Created this planning-file set:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
- Explicitly loaded the project-local `planning-with-files` skill from `.codex/skills/planning-with-files/SKILL.md`.
- Ran the skill's `session-catchup.py`; unsynced context only contained repeated interrupted requests to use the skill, with no new technical result beyond the existing planning files.
- Re-read `task_plan.md`, `findings.md`, and `progress.md`; confirmed the project is already captured and Git diff is clean before this update.
- Confirmed `.codex/` is local Codex tooling/configuration and should stay untracked for now.
- User explicitly requested that this project use `planning-with-files` for all future work; recorded this as a project operating convention in `task_plan.md`.

## Latest Known Server Commands

Check repository state on AutoDL:

```bash
cd /root/autodl-tmp/noob_2dgs
git pull --ff-only
git status --short
git rev-parse HEAD
```

Recommended next training run:

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

Recommended detail-preserving run if wall text remains poor:

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

Render check without mesh:

```bash
python render.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_balanced_v1 \
  --skip_mesh
```

Mesh check:

```bash
python render.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_balanced_v1 \
  --unbounded \
  --skip_train \
  --skip_test \
  --mesh_res 1024 \
  --num_cluster 20
```

## Open Questions

- Does `reception_hall_balanced_v1` preserve wall text better than `reception_hall_clean_v1`?
- Is `-r 1` feasible on the current RTX 3090 memory budget?
- Should the server use a custom COLMAP 3.9.1 CUDA build permanently?
- Should `ffmpeg`, `dash==2.14.2`, and `comm==0.1.4` be added to a server setup note or install script?
- Should future experiments save screenshots/renders into a structured comparison directory?

## Next Assistant Actions

1. Keep using `task_plan.md`, `findings.md`, and `progress.md` as the persistent working memory for this project.
2. Ask the user for the latest result images, mesh screenshots, or metrics from `reception_hall_balanced_v1` once it has run.
3. If artifacts persist, propose the next run based on observed failure:
   - floaters remain: increase cleanup.
   - text degraded: reduce regularization and use `-r 1`.
   - mesh fragmented: tune render `--num_cluster`, `--mesh_res`, and train cleanup parameters.
4. After every new server experiment or code change, update `progress.md`; if the result changes what we believe, also update `findings.md` and `task_plan.md`.
