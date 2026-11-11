#include <cuda_runtime.h>
#include <chrono>
#include <iostream>
#include "../common/matrix.hpp"

inline void check(cudaError_t error) {
    if (error != cudaSuccess) throw std::runtime_error(cudaGetErrorString(error));
}

__global__ void multiply_naive(const long long* a, const long long* b, long long* c, int n) {
    const int row = blockIdx.y*blockDim.y + threadIdx.y;
    const int col = blockIdx.x*blockDim.x + threadIdx.x;
    if (row >= n || col >= n) return;
    long long sum = 0;
    for (int k = 0; k < n; ++k) sum += a[static_cast<size_t>(row)*n+k]*b[static_cast<size_t>(k)*n+col];
    c[static_cast<size_t>(row)*n+col] = sum;
}

template<int T>
__global__ void multiply_tiled(const long long* a, const long long* b, long long* c, int n) {
    __shared__ long long aa[T][T], bb[T][T];
    const int row = blockIdx.y*T + threadIdx.y, col = blockIdx.x*T + threadIdx.x;
    long long sum = 0;
    for (int base = 0; base < n; base += T) {
        aa[threadIdx.y][threadIdx.x] = (row < n && base+threadIdx.x < n)
            ? a[static_cast<size_t>(row)*n+base+threadIdx.x] : 0;
        bb[threadIdx.y][threadIdx.x] = (col < n && base+threadIdx.y < n)
            ? b[static_cast<size_t>(base+threadIdx.y)*n+col] : 0;
        __syncthreads();
        for (int k = 0; k < T; ++k) sum += aa[threadIdx.y][k]*bb[k][threadIdx.x];
        __syncthreads();
    }
    if (row < n && col < n) c[static_cast<size_t>(row)*n+col] = sum;
}

struct DeviceBuffer {
    long long* ptr = nullptr;
    explicit DeviceBuffer(size_t bytes) { check(cudaMalloc(reinterpret_cast<void**>(&ptr), bytes)); }
    ~DeviceBuffer() { cudaFree(ptr); }
    DeviceBuffer(const DeviceBuffer&) = delete;
    DeviceBuffer& operator=(const DeviceBuffer&) = delete;
};
struct Event {
    cudaEvent_t value;
    Event() { check(cudaEventCreate(&value)); }
    ~Event() { cudaEventDestroy(value); }
};

int main(int argc, char** argv) {
    try {
        if (argc != 8) throw std::runtime_error("Usage: matrix_cuda A B C stats.csv naive|tiled block_x block_y");
        const std::string kernel(argv[5]);
        const int bx = positive_int(argv[6]), by = positive_int(argv[7]);
        if (kernel != "naive" && kernel != "tiled") throw std::runtime_error("Unknown kernel");
        if (kernel == "tiled" && (bx != by || (bx != 8 && bx != 16 && bx != 32)))
            throw std::runtime_error("Tiled blocks must be 8x8, 16x16 or 32x32");
        check(cudaSetDevice(0));
        cudaDeviceProp prop{};
        check(cudaGetDeviceProperties(&prop, 0));
        if (bx > prop.maxThreadsDim[0] || by > prop.maxThreadsDim[1] ||
            static_cast<long long>(bx)*by > prop.maxThreadsPerBlock)
            throw std::runtime_error("Block exceeds GPU limits");
        Matrix a = read_matrix(argv[1]), b = read_matrix(argv[2]);
        if (a.n != b.n) throw std::runtime_error("Matrix dimensions differ");
        const int n = a.n;
        Matrix c{n, std::vector<long long>(a.data.size())};
        const size_t bytes = a.data.size()*sizeof(long long);
        DeviceBuffer da(bytes), db(bytes), dc(bytes);
        Event begin, end;
        const dim3 block(bx, by), grid((n+bx-1)/bx, (n+by-1)/by);
        auto launch = [&]() {
            if (kernel == "naive") multiply_naive<<<grid,block>>>(da.ptr,db.ptr,dc.ptr,n);
            else if (bx == 8) multiply_tiled<8><<<grid,block>>>(da.ptr,db.ptr,dc.ptr,n);
            else if (bx == 16) multiply_tiled<16><<<grid,block>>>(da.ptr,db.ptr,dc.ptr,n);
            else multiply_tiled<32><<<grid,block>>>(da.ptr,db.ptr,dc.ptr,n);
            check(cudaGetLastError());
        };
        // Warm-up excludes first-use context/JIT costs from steady-state measurements.
        check(cudaMemcpy(da.ptr,a.data.data(),bytes,cudaMemcpyHostToDevice));
        check(cudaMemcpy(db.ptr,b.data.data(),bytes,cudaMemcpyHostToDevice));
        launch(); check(cudaDeviceSynchronize());
        const auto start = std::chrono::steady_clock::now();
        check(cudaMemcpy(da.ptr,a.data.data(),bytes,cudaMemcpyHostToDevice));
        check(cudaMemcpy(db.ptr,b.data.data(),bytes,cudaMemcpyHostToDevice));
        check(cudaEventRecord(begin.value));
        launch();
        check(cudaEventRecord(end.value));
        check(cudaEventSynchronize(end.value));
        check(cudaMemcpy(c.data.data(),dc.ptr,bytes,cudaMemcpyDeviceToHost));
        const double total_ms = std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        float kernel_ms;
        check(cudaEventElapsedTime(&kernel_ms,begin.value,end.value));
        write_matrix(argv[3],c);
        std::ofstream out(argv[4]);
        out << "n,kernel,block_x,block_y,grid_x,grid_y,kernel_ms,total_ms,gops\n" << std::setprecision(12)
            << n << ',' << kernel << ',' << bx << ',' << by << ',' << grid.x << ',' << grid.y << ','
            << kernel_ms << ',' << total_ms << ',' << 2.0*n*n*n/(kernel_ms*1e6) << '\n';
        out.close();
        if (!out) throw std::runtime_error("Cannot write statistics");
        std::cout << prop.name << " N=" << n << " kernel_ms=" << kernel_ms << " total_ms=" << total_ms << '\n';
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
