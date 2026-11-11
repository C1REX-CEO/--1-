CXX ?= g++
MPICXX ?= mpicxx
NVCC ?= nvcc
CXXFLAGS ?= -O2 -std=c++17
CUDA_ARCH ?= sm_86
WIDTHS = 1 2 3 4 8 16

.PHONY: simd mpi cuda
simd: $(addprefix build/myexp_,$(WIDTHS))
mpi: build/matrix_mpi
cuda: build/matrix_cuda

build:
	mkdir -p build

build/myexp_%: lab5_simd/main.cpp lab5_simd/CS149intrin.cpp lab5_simd/logger.cpp lab5_simd/CS149intrin.h lab5_simd/logger.h | build
	$(CXX) $(CXXFLAGS) -DVECTOR_WIDTH=$* lab5_simd/main.cpp lab5_simd/CS149intrin.cpp lab5_simd/logger.cpp -o $@

build/matrix_mpi: lab3_mpi/main.cpp common/matrix.hpp | build
	$(MPICXX) $(CXXFLAGS) lab3_mpi/main.cpp -o $@

build/matrix_cuda: lab4_cuda/main.cu common/matrix.hpp | build
	$(NVCC) $(CXXFLAGS) -arch=$(CUDA_ARCH) lab4_cuda/main.cu -o $@
