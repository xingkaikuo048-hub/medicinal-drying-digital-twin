# Medicinal Drying Digital Twin

基于 [pyoomph](https://pyoomph.readthedocs.io/) 的药材干燥多物理场仿真与数据生成项目。当前实现二维轴对称圆柱药材的瞬态热传导和水分扩散耦合有限元模型，并提供参数化工况、Latin hypercube 试验设计、固定边界/回归场景、可恢复批处理以及 HDF5/CSV 数据接口，为后续 PINN 和代理模型训练准备可追踪的数据集。

## 当前能力

- 二维轴对称 `r-z` 有限元网格
- 温度和干基含水率瞬态耦合求解
- 热/质对流 Robin 边界条件及蒸发潜热耦合
- JSON 工况配置与稳定的内容哈希工况 ID
- 128 个 Latin hypercube 工况，按训练/验证/测试集固定划分
- 11 个边界、网格回归和收缩候选场景
- 单工况运行、失败记录、已完成工况跳过和批处理恢复
- 每个工况输出网格、温度场、含水率场、观测量和完整配置
- pyoomph、轴对称、ALE API、数据依赖及 CUDA 验证脚本

## 模型范围

当前 MVP 使用常物性、静态网格，求解固体内部的热传导和水分扩散。空气温度、相对湿度和流速通过边界换热/传质系数作用于表面。`prescribed` 和 `ale` 收缩模式已纳入配置与固定场景，但求解器尚未实现移动网格；选择这些模式会明确报错，避免生成物理含义不完整的数据。

模型现阶段也未包含空气域 CFD、多孔介质压力场、温湿相关物性、实验标定或 PINN 训练。

## 环境

本机验证环境：

- Windows 11，Python 3.13.9（64 位）
- pyoomph 0.2.1，tccbox JIT 编译器
- PyTorch 2.14.0 + CUDA 13.0
- NVIDIA GeForce RTX 5070，`torch.cuda.is_available() == True`

建立独立环境：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` 固定直接依赖，`requirements-lock.txt` 记录本次验证过的完整依赖快照。PyTorch 使用官方 CUDA 13.0 wheel；没有兼容 NVIDIA GPU 时应根据 PyTorch 官方说明安装 CPU wheel。pyoomph FEM 求解本身不依赖 GPU。

## 验证

运行全部核心检查：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_validation.ps1
```

验证覆盖 pyoomph 基础瞬态 FEM、二维轴对称求解、ALE 类导入、参数设计、固定场景、热湿耦合 MVP、环境边界响应、批处理恢复、HDF5/Excel/绘图和 PyTorch CUDA。完整的本机安装及验证结果见 [`setup_report.md`](setup_report.md)。

## 运行单工况

先执行短时 smoke 工况：

```powershell
.\.venv\Scripts\python.exe scripts\run_case.py configs\base_case.json --smoke
```

运行配置中的完整仿真：

```powershell
.\.venv\Scripts\python.exe scripts\run_case.py configs\base_case.json
```

结果写入 `outputs/simulations/simulation-<hash>/`：

- `case.json`：实际运行的完整配置
- `status.json`：状态、时间和错误信息
- `fields.h5`：时间、网格拓扑、节点坐标、温度场和含水率场
- `observables.csv`：各输出时刻的均值和极值
- `pyoomph/`：求解器日志、JIT 代码和可视化文件

## 生成参数工况

默认设计在 11 个几何、初始条件、空气条件、材料和传递参数上生成 128 个可复现的 Latin hypercube 样本：

```powershell
.\.venv\Scripts\python.exe scripts\generate_design.py
```

生成固定边界和回归场景：

```powershell
.\.venv\Scripts\python.exe scripts\generate_scenarios.py
```

参数范围分别定义在 [`configs/doe_default.json`](configs/doe_default.json) 和 [`configs/scenario_suite.json`](configs/scenario_suite.json)。生成的 manifest 固定记录 `train`、`validation`、`test` 划分，避免在后续建模阶段发生数据泄漏。

## 批量生成数据

先用少量工况验证完整链路：

```powershell
.\.venv\Scripts\python.exe scripts\run_batch.py outputs\designs\validation\manifest.csv --max-cases 2 --smoke
```

运行完整参数设计：

```powershell
.\.venv\Scripts\python.exe scripts\run_batch.py outputs\designs\default\manifest.csv
```

批处理根据稳定工况 ID 建目录。再次运行时会跳过状态为 `completed` 的工况，并保留失败工况的错误记录，便于长时间数据生成任务恢复。加入 `--include-fixed` 才会运行固定场景 manifest 中预留的非 MVP 收缩候选工况。

## 项目结构

```text
configs/                    基准工况、DOE 参数范围、固定场景
scripts/                    验证、设计生成、单工况和批处理入口
src/drying_twin/            配置校验、FEM 模型和数据写出
tests/                      数值链路与回归验证
DATA_GENERATION_DESIGN.md   数据模式、采样和扩展设计
setup_report.md             本机环境与验收记录
requirements*.txt           直接依赖与验证快照
```

运行生成的 `outputs/`、本地虚拟环境和 pyoomph 编译产物不提交到 Git。工况可由版本化配置和固定随机种子重建；大规模数据集应保存到对象存储、数据版本系统或 Git LFS，并记录与代码提交对应的 manifest。

## 后续方向

1. 实现并验证 prescribed shrinkage 和 ALE moving mesh。
2. 引入温度/含水率相关物性及实验参数标定。
3. 增加网格与时间步收敛研究、质量/能量守恒指标。
4. 批量生成训练数据并建立数据质量检查。
5. 基于统一 HDF5 schema 训练 PINN、DeepONet 或其他代理模型。

更详细的数据生成约束和扩展原则见 [`DATA_GENERATION_DESIGN.md`](DATA_GENERATION_DESIGN.md)。
