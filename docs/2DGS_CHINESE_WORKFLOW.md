# 2DGS 从图片数据集到训练、渲染的完整流程

本文档记录本仓库在 Ubuntu / AutoDL 服务器上的推荐使用流程。目标是从“一组普通图片”开始，经过 COLMAP 重建相机位姿，再训练 2D Gaussian Splatting，最后渲染图片或导出网格。

## 1. 整体流程

完整流程如下：

```text
原始图片
  -> 整理为 input/ 目录
  -> COLMAP 估计相机位姿和稀疏点云
  -> 生成 2DGS 可读的数据集结构 images/ + sparse/0/
  -> train.py 训练 2DGS 模型
  -> render.py 渲染图片、深度、法线或导出网格
```

如果你已经有 COLMAP 格式数据集，可以跳过 COLMAP 转换步骤，直接训练。

## 2. 推荐目录结构

在 AutoDL 上建议把代码、数据和输出都放在 `/root/autodl-tmp`，避免占用系统盘。

```text
/root/autodl-tmp/
├── noob_2dgs/                 # 本代码仓库
├── datasets/
│   └── my_scene/
│       └── input/             # 原始图片放这里
└── outputs/
    └── my_scene/              # 训练输出放这里
```

其中 `my_scene` 可以换成你的场景名。

## 3. 克隆代码

```bash
cd /root/autodl-tmp
git clone --recursive https://github.com/Monkot19/noob_2dgs.git
cd noob_2dgs
```

如果克隆时没有带 `--recursive`，需要补拉子模块：

```bash
git submodule update --init --recursive
```

## 4. 检查服务器环境

先确认 GPU、CUDA 编译器和 PyTorch 都正常：

```bash
nvidia-smi
nvcc --version
python --version
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

理想情况类似：

```text
GPU: RTX 3090 / RTX 4090 / A 系列显卡
nvcc: 11.8
Python: 3.8.x
PyTorch: 2.0.0+cu118
torch.cuda.is_available(): True
```

如果 AutoDL 镜像已经自带合适的 PyTorch 和 CUDA，不建议强行执行：

```bash
conda env create --file environment.yml
```

这个文件比较旧，Conda 解依赖可能会卡很久。更稳的做法是在当前基础环境里补装项目依赖。

## 5. 安装 Python 依赖和 CUDA 扩展

进入仓库目录：

```bash
cd /root/autodl-tmp/noob_2dgs
```

安装普通 Python 依赖：

```bash
pip install open3d==0.18.0 mediapy==1.1.2 lpips==0.1.4 scikit-image==0.21.0 tqdm==4.66.2 trimesh==4.3.2 plyfile opencv-python
```

编译并安装 2DGS 需要的 CUDA 扩展：

```bash
pip install submodules/diff-surfel-rasterization
pip install submodules/simple-knn
```

验证扩展是否安装成功：

```bash
python -c "import diff_surfel_rasterization, simple_knn; print('extensions ok')"
```

看到下面输出就说明环境基本可用：

```text
extensions ok
```

## 6. 准备只有图片的数据集

假设场景名为 `my_scene`，先创建目录：

```bash
mkdir -p /root/autodl-tmp/datasets/my_scene/input
```

把所有原始图片放到：

```text
/root/autodl-tmp/datasets/my_scene/input/
```

推荐图片命名简单一些，例如：

```text
0001.jpg
0002.jpg
0003.jpg
...
```

图片拍摄建议：

- 图片之间要有足够重叠，不要每张都差太远。
- 尽量围绕同一个物体或场景多角度拍摄。
- 避免大量模糊、反光、纯色墙面、透明物体。
- 光照尽量稳定，不要一部分过曝、一部分太暗。
- 小物体可以绕物体拍，大场景可以沿路径移动拍。

## 7. 安装或检查 COLMAP

`convert.py` 会调用系统里的 `colmap` 命令，所以先检查：

```bash
colmap -h
```

如果提示 `command not found`，在 Ubuntu 上安装：

```bash
apt update
apt install -y colmap
```

安装后再次检查：

```bash
colmap -h
```

## 8. 用 COLMAP 转换图片数据集

进入代码仓库：

```bash
cd /root/autodl-tmp/noob_2dgs
```

运行转换：

```bash
python convert.py -s /root/autodl-tmp/datasets/my_scene
```

`convert.py` 默认会读取：

```text
/root/autodl-tmp/datasets/my_scene/input/
```

并生成：

```text
/root/autodl-tmp/datasets/my_scene/
├── input/
├── distorted/
├── images/
└── sparse/
    └── 0/
```

其中 `images/` 和 `sparse/0/` 是训练 2DGS 需要的关键目录。

如果服务器没有可用的 COLMAP GPU 支持，可以尝试 CPU 模式：

```bash
python convert.py -s /root/autodl-tmp/datasets/my_scene --no_gpu
```

CPU 模式会慢一些。

## 9. 检查 COLMAP 转换是否成功

转换完成后检查：

```bash
ls /root/autodl-tmp/datasets/my_scene/images
ls /root/autodl-tmp/datasets/my_scene/sparse/0
```

`sparse/0` 下通常应该有：

```text
cameras.bin
images.bin
points3D.bin
```

如果没有这些文件，说明 COLMAP 没有成功重建。常见原因是：

- 图片重叠太少。
- 场景纹理太少，特征点不够。
- 图片太模糊。
- 拍摄路径跨度太大。
- 多个物体或背景变化太大。

## 10. 开始训练

创建输出目录：

```bash
mkdir -p /root/autodl-tmp/outputs
```

训练：

```bash
cd /root/autodl-tmp/noob_2dgs
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene
```

如果图片分辨率很高，显存压力大，可以降低训练分辨率：

```bash
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene -r 2
```

如果是无界大场景，通常建议使用平均深度：

```bash
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --depth_ratio 0
```

如果是类似 DTU 这种前景物体、边界相对明确的场景，可以尝试：

```bash
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene -r 2 --depth_ratio 1
```

## 11. 用 tmux 跑长任务

训练通常需要较长时间，建议用 `tmux`，这样断开网页或 SSH 后训练不会停。

新建会话：

```bash
tmux new -s 2dgs
```

在 tmux 里运行训练：

```bash
cd /root/autodl-tmp/noob_2dgs
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene
```

临时离开 tmux：

```text
Ctrl+b 然后按 d
```

重新进入：

```bash
tmux attach -t 2dgs
```

## 12. 渲染测试集图片

训练完成后，可以渲染结果：

```bash
cd /root/autodl-tmp/noob_2dgs
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene
```

如果只想渲染，不重新处理训练集或测试集，可以根据需要加：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --skip_train
```

或者：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --skip_test
```

渲染结果通常会保存在模型输出目录下的相关子目录中。

## 13. 导出网格

### 13.1 有界场景网格

适合物体或边界明确的场景：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --skip_train --skip_test
```

可以根据效果调：

```bash
--voxel_size
--depth_trunc
--depth_ratio
```

例如：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --skip_train --skip_test --voxel_size 0.004 --depth_trunc 3.0
```

### 13.2 无界场景网格

适合室外、大范围或边界不明确的场景：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --unbounded --skip_train --skip_test --mesh_res 1024
```

`mesh_res` 越大，网格越细，但显存和时间开销也越大。显存不够时可以尝试：

```bash
--mesh_res 512
```

## 14. 常见问题

### 14.1 COLMAP 失败

表现：

```text
Feature extraction failed
Feature matching failed
Mapper failed
```

排查：

```bash
ls /root/autodl-tmp/datasets/my_scene/input
```

确认图片确实在 `input/` 下。

如果图片太少、重叠太低或特征太少，COLMAP 可能无法重建。需要重新拍摄或补充图片。

### 14.2 CUDA 扩展导入失败

重新安装两个子模块：

```bash
cd /root/autodl-tmp/noob_2dgs
pip install submodules/diff-surfel-rasterization --force-reinstall
pip install submodules/simple-knn --force-reinstall
```

再验证：

```bash
python -c "import diff_surfel_rasterization, simple_knn; print('extensions ok')"
```

### 14.3 显存不够

可以尝试：

```bash
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene -r 2
```

或者减少网格分辨率：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --unbounded --mesh_res 512
```

### 14.4 训练效果差

常见原因：

- COLMAP 稀疏点云质量差。
- 图片数量太少。
- 视角覆盖不完整。
- 场景中反光、透明、纯色区域太多。
- 相机曝光和白平衡变化太大。

建议先检查 COLMAP 输出是否合理，再考虑调训练参数。

## 15. 后续代码更新

本地修改代码并推送到 GitHub 后，服务器更新：

```bash
cd /root/autodl-tmp/noob_2dgs
git pull --ff-only
git submodule update --init --recursive
```

如果更新涉及 CUDA 子模块或依赖，重新安装：

```bash
pip install submodules/diff-surfel-rasterization --force-reinstall
pip install submodules/simple-knn --force-reinstall
```

## 16. 推荐的最小命令顺序

如果你已经把图片放入 `input/`，可以按下面顺序执行：

```bash
cd /root/autodl-tmp/noob_2dgs

python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
python -c "import diff_surfel_rasterization, simple_knn; print('extensions ok')"

python convert.py -s /root/autodl-tmp/datasets/my_scene

mkdir -p /root/autodl-tmp/outputs
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene

python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene
```
