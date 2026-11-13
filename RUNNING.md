# Запуск лабораторных 3–5

Для текущего окружения «Сергея Королёва» (Slurm, проверено 11.11.2026)
следуйте [lab3/SLURM.md](lab3/SLURM.md). Прежний сценарий PBS
не подходит к этому подключению.

Все команды ниже выполняются из корня репозитория. Первые две лабораторные сохранены.
Формат входа и результата: размер N, затем N строк по N целых чисел.
Код работ 3 и 4 использует `long long`, как в исходной работе; показатель производительности
называется GOPS, поскольку арифметика целочисленная, а не FLOPS.

## Linux

Нужны C++17, Python 3.10+, MPI для работы 3, CUDA Toolkit и NVIDIA GPU для работы 4.

```bash
python3 -m pip install -r lab3/experiments/requirements.txt
make simd
python3 lab5/run_experiments.py --pattern 'build/myexp_{width}'
python3 lab3/experiments/summarize.py simd --input lab5/results
make mpi
python3 lab3/experiments/check.py mpi --exe build/matrix_mpi
python3 lab3/experiments/run.py mpi --exe build/matrix_mpi --label local --out lab3/results_local
python3 lab3/experiments/summarize.py mpi --input lab3/results_local
make cuda CUDA_ARCH=sm_86
python3 lab3/experiments/check.py cuda --exe build/matrix_cuda
python3 lab3/experiments/run.py cuda --exe build/matrix_cuda --label my-gpu --out lab4/results
python3 lab3/experiments/summarize.py cuda --input lab4/results
```

`sm_86` соответствует RTX 3060. Для другой GPU укажите её поддерживаемую архитектуру.
На кластере MPI-библиотека при сборке и при запуске должна быть одной и той же.
Число процессов задаётся MPI launcher; по одному процессу на физическое ядро
нужно закреплять средствами MPI/планировщика. `--launcher 'mpiexec --bind-to core'`
подходит для поддерживающей этот синтаксис Open MPI; это не универсальный флаг MPI.

## Windows

Нужны MSVC с C++17 и Windows SDK, для MPI — Microsoft MPI Runtime и SDK,
для CUDA — CUDA Toolkit и совместимая версия MSVC. Запустите x64 Native Tools
Command Prompt. `build_windows.cmd` также умеет находить использованную локальную
установку VS 2026 и выбирать установленный toolset 14.44, совместимый с CUDA 12.8.

```bat
python -m pip install -r lab3/experiments/requirements.txt
build_windows.cmd
build_windows.cmd mpi
build_windows.cmd cuda
python lab5/run_experiments.py
python lab3/experiments/check.py mpi --exe build/matrix_mpi.exe
python lab3/experiments/check.py cuda --exe build/matrix_cuda.exe
python lab3/experiments/run.py mpi --exe build/matrix_mpi.exe --label local --out lab3/results_local
python lab3/experiments/run.py cuda --exe build/matrix_cuda.exe --label my-gpu --out lab4/results
python lab3/experiments/summarize.py mpi --input lab3/results_local
python lab3/experiments/summarize.py cuda --input lab4/results
python lab3/experiments/summarize.py simd --input lab5/results
```

При необходимости задайте `CUDA_PATH`, `MSMPI_INC`, `MSMPI_LIB64` и добавьте
`C:\Program Files\Microsoft MPI\Bin` в PATH текущего терминала. В данной рабочей
папке Python расположен в `..\.lab-tools\python\python.exe`, CUDA и извлечённый
MPI SDK — в соседней `.lab-tools`. Эти инструменты не входят в репозиторий.

## Измерения и проверка

- Размеры по умолчанию: 200, 400, 800, 1200, 1600, 2000; по 3 повторения.
- `raw.csv` содержит каждый замер, `summary.csv` — медиану и диапазон min–max.
- Повторный запуск в той же папке заменяет её CSV; для нового компьютера используйте другую папку.
- Матрицы генерируются с seed `42+N`, целые от −10 до 10. Каждый результат
  проверяется целиком через NumPy, до включения замера в итоговую таблицу.
- Для больших матриц эталон считается NumPy/BLAS в float64 и переводится в int64:
  все произведения и частичные суммы целые и меньше 2^53, поэтому округления
  здесь нет. Малые граничные тесты дополнительно используют прямой `int64 @ int64`.
- Чтение/запись текстовых файлов и верификация в измеряемое время не входят.
- Программы отклоняют некорректные размеры, неполные/избыточные файлы и числа,
  способные вызвать переполнение int64 (используется консервативная граница).
- Папка `lab3/experiments/work` содержит временные матрицы; в Git она не включается.

## Что осталось для сдачи MPI

Официальные инструкции изучены: SSH `sk.ssau.ru`, TORQUE/Moab, подача задания
через `qsub`. Подготовлены `lab3/job.pbs` и адаптер Intel MPI по примеру СКЦ.
Подробная инструкция: [KOROLEV.md](lab3/KOROLEV.md).
Для загрузки через WinSCP подготовлен небольшой архив: запустите
`python lab3/prepare_upload.py` и возьмите `build/lab3-korolev-upload.zip`.
Он содержит отдельные последовательную и MPI-программы, скрипты сборки,
PBS-задание и [пошаговую инструкцию](lab3/START_HERE.md).
Нужны подключение к разрешённой сети (в том числе университетский VPN),
SSH-учётная запись и код проекта. Модули компилятора/MPI и Python нужно проверить
в действующем окружении; опубликованные версии ПО старые.

После настоящего запуска нужно добавить `results_korolev`, параметры узлов/ядер,
вывод планировщика и выводы по измерениям в отчёт №3. Локальные результаты
не заменяют этот обязательный пункт задания.
