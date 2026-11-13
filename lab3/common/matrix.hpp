#pragma once
#include <algorithm>
#include <climits>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

// Same text format and integer arithmetic as labs 1/2.
struct Matrix {
    int n = 0;
    std::vector<long long> data;
};

inline Matrix read_matrix(const std::string& path) {
    std::ifstream in(path);
    long long n;
    if (!(in >> n) || n <= 0 || n > 46340)
        throw std::runtime_error("Invalid matrix size/file: " + path);
    Matrix a{static_cast<int>(n), std::vector<long long>(static_cast<size_t>(n*n))};
    // Conservative bound guarantees sum of N products fits signed int64.
    const long long bound = static_cast<long long>(std::sqrt(
        static_cast<long double>(LLONG_MAX) / n)) - 1;
    for (auto& x : a.data)
        if (!(in >> x) || x < -bound || x > bound)
            throw std::runtime_error("Missing/invalid element or int64 overflow risk: " + path);
    std::string extra;
    if (in >> extra) throw std::runtime_error("Extra matrix elements: " + path);
    return a;
}

inline void write_matrix(const std::string& path, const Matrix& a) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write: " + path);
    out << a.n << '\n';
    for (int i = 0; i < a.n; ++i)
        for (int j = 0; j < a.n; ++j)
            out << a.data[static_cast<size_t>(i)*a.n+j] << (j+1 == a.n ? '\n' : ' ');
    out.close();
    if (!out) throw std::runtime_error("Write failed: " + path);
}

inline int positive_int(const char* text) {
    std::string s(text);
    size_t end;
    int value = std::stoi(s, &end);
    if (end != s.size() || value <= 0) throw std::runtime_error("Expected positive integer: " + s);
    return value;
}

inline void multiply_rows(const long long* a, const long long* b,
                          long long* c, int rows, int n) {
    for (int i = 0; i < rows; ++i)
        for (int k = 0; k < n; ++k) {
            const long long x = a[static_cast<size_t>(i)*n+k];
            for (int j = 0; j < n; ++j)
                c[static_cast<size_t>(i)*n+j] += x*b[static_cast<size_t>(k)*n+j];
        }
}
