CXX ?= g++
MPICXX ?= mpicxx
NVCC ?= nvcc
CXXFLAGS ?= -O2 -std=c++17
CUDA_ARCH ?= sm_86
WIDTHS = 1 2 3 4 8 16

.PHONY: simd mpi cuda serial lab3
lab3: serial mpi
serial: build/matrix_serial
simd: $(addprefix build/myexp_,$(WIDTHS))
mpi: build/matrix_mpi
cuda: build/matrix_cuda

build:
	mkdir -p build

build/myexp_%: lab5/main.cpp lab5/CS149intrin.cpp lab5/logger.cpp lab5/CS149intrin.h lab5/logger.h | build
	$(CXX) $(CXXFLAGS) -DVECTOR_WIDTH=$* lab5/main.cpp lab5/CS149intrin.cpp lab5/logger.cpp -o $@

build/matrix_mpi: lab3/main.cpp lab3/common/matrix.hpp | build
	$(MPICXX) $(CXXFLAGS) lab3/main.cpp -o $@

build/matrix_serial: lab3/serial.cpp lab3/common/matrix.hpp | build
	$(CXX) $(CXXFLAGS) lab3/serial.cpp -o $@

build/matrix_cuda: lab4/main.cu lab4/common/matrix.hpp | build
	$(NVCC) $(CXXFLAGS) -arch=$(CUDA_ARCH) lab4/main.cu -o $@
