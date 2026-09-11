# 药材干燥多物理场开发环境搭建报告

生成日期：2026-09-11（Asia/Shanghai）

## 最终结论

ENVIRONMENT READY FOR MEDICINAL DRYING MVP

本阶段只完成环境、有限元 smoke test、二维轴对称验证、ALE API 验证和 PyTorch/CUDA 验证；没有实现完整药材模型，也没有开始 PINN 训练。

    PYOOMPH_BASIC_SOLVER = PASS
    PYOOMPH_AXISYMMETRIC = PASS
    PYOOMPH_ALE_IMPORT = PASS
    PYTORCH = PASS
    CUDA_AVAILABLE = True

## Environment Validation

- [x] Python OK
- [x] venv OK
- [x] NumPy/SciPy OK
- [x] pyoomph import OK
- [x] pyoomph basic FEM solve OK
- [x] axisymmetric solve OK
- [x] ALE module OK
- [x] pandas/openpyxl OK
- [x] matplotlib OK
- [x] PyTorch OK
- [x] Reproducible parameter design OK

## 主机与软件清单

| 项目 | 检查结果 |
|---|---|
| 操作系统 | Microsoft Windows 11 家庭版 中文版，64 位，10.0.26200（Build 26200） |
| CPU | Intel Core i9-14900HX，24 核 / 32 逻辑处理器 |
| RAM | 34,070,192,128 bytes，约 31.73 GiB |
| 当前工作目录 | C:\Users\xingkaikuo\Documents\Codex\2026-09-11\gei |
| 项目目录 | C:\Users\xingkaikuo\Documents\Codex\2026-09-11\gei\outputs\medicinal-drying-digital-twin |
| Python | CPython 3.13.9，64 位 |
| 项目解释器 | 项目根目录\.venv\Scripts\python.exe |
| 虚拟环境物理目录 | C:\Users\xingkaikuo\Documents\Codex\environments\pyoomph |
| pip / setuptools / wheel | 26.2.1 / 84.0.0 / 0.48.0 |
| Git | 2.54.0.windows.1 |
| 系统 gcc / clang / MSVC | 未发现；MVP 不需要 |
| pyoomph 编译器 | tccbox 2025.10.27，官方 compiler check 通过 |
| pyoomph | 0.2.1 |
| NumPy / SciPy | 2.5.3 / 1.18.1 |
| pandas / openpyxl / h5py | 3.0.5 / 3.1.5 / 3.16.0 |
| Matplotlib | 3.11.1 |
| PyTorch | 2.14.0+cu130 |
| NVIDIA GPU | NVIDIA GeForce RTX 5070 Laptop GPU，8151 MiB |
| NVIDIA Driver | 616.56 |
| CUDA 驱动兼容版本 | 13.4 |
| PyTorch CUDA runtime | 13.0 |
| torch.cuda.is_available() | True |
| CUDA device capability | 12.0 |

本机已有 Python 3.13 和 3.14。为避免额外安装或修改系统 Python，选择已有、兼容 pyoomph Windows wheel 的 64 位 Python 3.13。项目 .venv 是指向已经建立的独立 pyoomph 虚拟环境的 Windows junction；它不是系统 Python，也没有全局 pip 污染。

## 安装记录

所有 pip 命令都使用独立环境中的解释器。

| 组件 | 命令 | 版本/结果 |
|---|---|---|
| 独立环境 | py -3.13 -m venv C:\Users\xingkaikuo\Documents\Codex\environments\pyoomph | Python 3.13.9，PASS |
| 项目 .venv | New-Item -ItemType Junction -Path 项目\.venv -Target C:\Users\xingkaikuo\Documents\Codex\environments\pyoomph | 激活和前缀检查 PASS |
| 基础打包工具 | python -m pip install --upgrade pip setuptools wheel | 26.2.1 / 84.0.0 / 0.48.0，PASS |
| pyoomph | python -m pip install --only-binary=:all: pyoomph==0.2.1 | pyoomph 0.2.1、tccbox 2025.10.27，PASS |
| 数据环境 | python -m pip install pandas openpyxl h5py | 导入、Excel/HDF5 往返均 PASS |
| PyTorch GPU | python -m pip install --index-url https://download.pytorch.org/whl/cu130 torch==2.14.0+cu130 | CUDA 张量运算 PASS |
| 依赖一致性 | python -m pip check | No broken requirements found. |

NumPy、SciPy 和 Matplotlib 已作为 pyoomph 依赖安装。没有安装 WSL、PETSc、SLEPc、CUDA Toolkit、显卡驱动或 Microsoft Build Tools，也没有修改系统 PATH。

## pyoomph 官方检查解释

已运行并保存：

    python -m pyoomph check all
    python -m pyoomph check compiler tccbox

check all 会主动检查未安装的高级可选功能，并且即使内部项目失败仍可能返回进程退出码 0。PETSc、SLEPc 和 MPI 不属于本阶段要求。默认 system 编译器因没有 MSVC 而失败；部分 solver/eigen 的官方运行检查也会继承默认 system 编译器，因此同样报告 MSVC 缺失。

pyoomph 注册的内置编译器名称是 tccbox。官方检查结果为：

    Checking compiler / tccbox
     loading seems to work
      running seems to work
      JIT code cache seems to work (1 hit(s) on the second pass)

两个实际空间 FEM 测试显式调用 problem.set_c_compiler("tcc")，日志确认方程代码由 tccbox 编译，线性系统由 Pardiso 求解。因此普通 FEM/PDE transient solve 已通过真实求解验证，不依赖 MSVC。

完整日志在 outputs/setup_logs，包括 pyoomph-check-all.log、pyoomph-check-tccbox.log、pip-check.log、transient-smoke.log、axisymmetric.log、ale-import.log、dependency-validation.log 和 versions.log。

## 最小瞬态 FEM 验证

测试文件：tests/test_pyoomph_smoke.py

求解：

    dT/dt - d²T/dx² = 0
    x in [0, 1]
    T(0,t) = T(1,t) = 0
    T(x,0) = sin(pi*x)

设置 12 个二次有限元，步长 0.001，求解到 0.02，在 0、0.01、0.02 输出 VTU。

- 网格创建：PASS，25 个输出节点
- 场定义、方程装配和边界条件：PASS
- 瞬态求解：PASS，20 个时间步
- 数值输出：PASS，3 个 VTU 时刻
- 与解析解 sin(pi*x) exp(-pi²t) 的最大绝对误差：5.533169273519434e-05
- 程序退出码：0

结果在 outputs/smoke，包括 final_solution.csv、metrics.json、domain.pvd 和 VTU 文件。

## 二维轴对称 r-z 验证

测试文件：tests/test_axisymmetric.py。代码实际执行：

    self.set_coordinate_system("axisymmetric")

建立 r ∈ [0,1]、z ∈ [0,1] 的二维四边形网格，求解：

    -axisymmetric_laplacian(u) = 4
    u(r=1,z) = 0
    exact: u(r,z) = 1-r²

- AxisymmetricCoordinateSystem：PASS
- r-z 网格与 90 自由度系统：PASS
- tccbox 编译和 Pardiso 求解：PASS
- 输出节点：99
- 最大绝对误差：2.7755575615628914e-15
- 程序退出码：0

结果在 outputs/axisymmetric。

## ALE / Moving Mesh 验证

tests/test_ale_import.py 已实际导入 pyoomph.equations.ALE，检查并验证以下类的继承关系：

- BaseMovingMeshEquations
- LaplaceSmoothedMesh
- PseudoElasticMesh
- PrescribedMovingMesh

LaplaceSmoothedMesh 实例化成功。本阶段按范围只验证 API，没有实现收缩模型。

## Python 数据与 PyTorch 验证

scripts/validate_dependencies.py 实际完成：

- NumPy/SciPy 导入与数组计算：PASS
- pandas + openpyxl Excel 写入/读回：PASS
- h5py HDF5 写入/读回：PASS
- Matplotlib 无界面 PNG 渲染：PASS
- PyTorch CUDA 张量平方和：PASS，结果 14.0
- torch.cuda.is_available()：True
- 实际设备：NVIDIA GeForce RTX 5070 Laptop GPU

## 复现与运行

在当前电脑可双击 activate.cmd 激活环境。运行全部验收：

    cd C:\Users\xingkaikuo\Documents\Codex\2026-09-11\gei\outputs\medicinal-drying-digital-twin
    powershell -ExecutionPolicy Bypass -File scripts\run_validation.ps1

在另一台 Windows 64 位电脑上复现：

    py -3.13 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    powershell -ExecutionPolicy Bypass -File scripts\run_validation.ps1

requirements.txt 是直接依赖的固定版本；requirements-lock.txt 是完整传递依赖快照。GPU 复现使用 PyTorch 官方 CUDA 13.0 wheel 索引。没有兼容 NVIDIA GPU 的机器应改装官方 CPU wheel；pyoomph FEM 本身不依赖 GPU。

官方资料：

- https://pyoomph.readthedocs.io/en/latest/
- https://pyoomph.readthedocs.io/en/latest/tutorial/installation/pypa.html
- https://pypi.org/project/pyoomph/
- https://pytorch.org/get-started/locally/

## 后续数据生成准备

已加入参数化数据生成骨架，但没有提前实现完整药材 PDE：

- configs/base_case.json：集中管理几何、初始状态、热风、材料、传热传质、收缩开关、数值设置和输出字段，全部采用带单位的字段名。
- configs/doe_default.json：定义 11 个主要工况参数的范围，默认使用固定随机种子的 128 点 Latin hypercube。
- scripts/generate_design.py：生成唯一且稳定的 case ID、独立 case JSON 和 manifest；不启动 FEM。
- DATA_GENERATION_DESIGN.md：规定 HDF5/CSV 字段、状态文件、失败样本和分阶段工况策略。

设计生成器已经实际验证：128 个 case ID 全部唯一；固定种子重复运行得到相同设计；数据集在仿真前固定划分为 train 90、validation 19、test 19。这样后续更换热湿耦合方程、增加规定收缩或 ALE 时，数据入口和追溯方式保持一致。

生成默认设计：

    .\.venv\Scripts\python.exe scripts\generate_design.py

## 参数化热湿耦合 MVP

已增加 src/drying_twin/model.py 和 scripts/run_case.py。当前模型使用真实 axisymmetric r-z 网格，联合求解温度 temperature_K 与干基含水率 moisture_kg_per_kg_dry，包含内部扩散、外表面对流换热/传质和可选潜热边界耦合。

收缩模式 prescribed 与 ale 已在场景配置中预留。当前运行器会明确拒绝尚未实现的收缩模式并生成失败状态，避免把未验证数据放入训练集。

tests/test_coupled_drying_mvp.py 已完成短时实际运行：4×8 网格、120 秒、5 个快照；平均温度从 298.15 K 升至 301.80 K，平均含水率从 2.000 降至 1.99814，温度和含水率保持有限且非负。每个 case 输出 case.json、status.json、fields.h5 和 observables.csv。HDF5 保存每个时刻的时间、r/z 坐标、温度和含水率场；CSV 保存体积平均与范围观测量。

scripts/run_batch.py 提供按 manifest 顺序的可恢复批处理：已成功 case 自动跳过，失败 case 保留错误摘要并继续后续 case，最后写 batch_summary.json。默认设计仍只生成参数，不会自动启动 128 个高成本求解。

## 多工况数据接口

工况、模型开关和数值设置集中在 configs/base_case.json。传质边界采用带单位的质量通量系数；热风速度影响换热和传质系数，相对湿度影响平衡含水率，因此 DOE 参数会真实改变 PDE 响应。

- scripts/generate_design.py 使用固定种子生成 128 个 Latin hypercube 工况，预先划分 train 90、validation 19、test 19。
- configs/scenario_suite.json 定义 11 个固定边界和回归场景，包括冷热干湿、速度、尺寸、初始水分、扩散上下限、细网格、长时过程与收缩候选。
- scripts/run_case.py 运行单个二维轴对称热湿耦合 FEM 工况。
- scripts/run_batch.py 可恢复地运行 manifest，跳过成功工况，记录失败工况后继续。
- fields.h5 按时间保存 r/z 坐标、温度、水分、单元连通关系和单元类型；observables.csv 保存轴对称体积平均值和范围。

实际短时验证：平均温度从 298.15 K 升到 301.80 K，平均含水率从 2.000 降到 1.99814。热干高速和低温高湿慢风工况末时平均温度约为 307.55 K 与 298.66 K，前者失水更多。

prescribed/ALE 收缩案例已预留配置，但尚未实现的模式会被运行器明确拒绝，避免把无效结果混入训练集。本次没有自动运行 128 个生产算例，也没有开始 PINN 训练。
