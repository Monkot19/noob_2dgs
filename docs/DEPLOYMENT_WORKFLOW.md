# Deployment and Sync Workflow

This repository was cloned from:

```powershell
https://github.com/hbb1/2d-gaussian-splatting.git
```

The original remote is named `upstream`. Your own GitHub repository should be
added as `origin` after it is created.

## Local Repository Setup

Check remotes:

```powershell
git remote -v
```

Add your GitHub repository as the writable remote:

```powershell
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

Keep the original project available for future upstream updates:

```powershell
git fetch upstream
git merge upstream/main
```

## Server Setup

Clone your repository on the server:

```bash
git clone --recursive https://github.com/<your-user>/<your-repo>.git
cd <your-repo>
```

If the repository was cloned without submodules:

```bash
git submodule update --init --recursive
```

Create the environment from the upstream file:

```bash
conda env create --file environment.yml
conda activate surfel_splatting
```

If pip dependencies fail during environment creation, install the base conda
environment first, then install the two CUDA extensions after PyTorch imports
successfully:

```bash
pip install submodules/diff-surfel-rasterization
pip install submodules/simple-knn
```

## Normal Development Loop

When the server has an error:

1. Send the traceback, command, current branch, and latest commit hash from the
   server.
2. Fix the code locally in this workspace.
3. Commit and push the fix to `origin`.
4. Pull the update on the server.

Local push:

```powershell
git status
git add <changed-files>
git commit -m "Describe the fix"
git push
```

Server update:

```bash
git pull --ff-only
git submodule update --init --recursive
```

## Local Windows Notes

This project builds CUDA extensions. A working setup needs:

- NVIDIA driver
- CUDA compiler `nvcc`
- Visual Studio C++ Build Tools on Windows
- a PyTorch build compatible with the GPU and CUDA toolkit

On this machine, `nvidia-smi` sees an RTX 5060, but `nvcc` is not on PATH. The
upstream `environment.yml` creates a Python 3.8 / PyTorch 2.0 / CUDA 11.8
environment, but `import torch` currently fails on Windows with a
`nvfuser_codegen.dll` loading error. The repository itself and submodules are
ready; the remaining local issue is the Python/CUDA toolchain.

For server runs, prefer Linux with a CUDA toolkit installed. After creating the
environment, always verify:

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
nvcc --version
python -c "import diff_surfel_rasterization, simple_knn; print('cuda extensions ok')"
```
