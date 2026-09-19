#include <iostream>
#include <fstream>
#include <vector>
#include <stdexcept>
#include <chrono>
#include <iomanip>
#include <string>

using Clock = std::chrono::high_resolution_clock;

class Matrix {
private:
    std::vector<std::vector<long long>> _data;
    int _n = 0;

public:
    Matrix() = default;
    explicit Matrix(int n) : _n(n), _data(n, std::vector<long long>(n, 0)) {}

    void loadFromFile(const std::string& path) {
        std::ifstream file(path);
        if (!file.is_open()) {
            throw std::runtime_error("Не могу открыть файл для чтения: " + path);
        }
        if (!(file >> _n) || _n <= 0) {
            throw std::runtime_error("Некорректный размер матрицы в файле: " + path);
        }
        _data.assign(_n, std::vector<long long>(_n));
        for (int i = 0; i < _n; ++i) {
            for (int j = 0; j < _n; ++j) {
                if (!(file >> _data[i][j])) {
                    throw std::runtime_error("Не хватает данных в файле: " + path);
                }
            }
        }
    }

    void saveToFile(const std::string& path) const {
        std::ofstream file(path);
        if (!file.is_open()) {
            throw std::runtime_error("Не могу создать файл для записи: " + path);
        }
        file << _n << "\n";
        for (int i = 0; i < _n; ++i) {
            for (int j = 0; j < _n; ++j) {
                file << _data[i][j] << (j + 1 < _n ? ' ' : '\n');
            }
        }
    }

    int size() const { return _n; }

    Matrix multiply(const Matrix& other) const {
        if (_n != other._n) {
            throw std::runtime_error("Размеры матриц не совпадают!");
        }
        Matrix result(_n);
        for (int i = 0; i < _n; ++i) {
            const auto& arow = _data[i];
            auto& crow = result._data[i];
            for (int k = 0; k < _n; ++k) {
                const long long a = arow[k];
                const auto& brow = other._data[k];
                for (int j = 0; j < _n; ++j) {
                    crow[j] += a * brow[j];
                }
            }
        }
        return result;
    }
};

int main(int argc, char** argv) {
    const std::string fileA     = argc > 1 ? argv[1] : "Matrix(A).txt";
    const std::string fileB     = argc > 2 ? argv[2] : "Matrix(B).txt";
    const std::string fileC     = argc > 3 ? argv[3] : "RESULT.txt";
    const std::string fileStats = argc > 4 ? argv[4] : "stats.txt";

    try {
        Matrix A, B;
        A.loadFromFile(fileA);
        B.loadFromFile(fileB);

        if (A.size() != B.size()) {
            std::cerr << "Ошибка: размеры матриц не совпадают (" << A.size()
                      << " и " << B.size() << ")\n";
            return 1;
        }
        const int N = A.size();

        const auto t0 = Clock::now();
        Matrix C = A.multiply(B);
        const auto t1 = Clock::now();
        const double seconds = std::chrono::duration<double>(t1 - t0).count();

        C.saveToFile(fileC);

        const long long operations = static_cast<long long>(N) * N * N;
        const double flop   = 2.0 * N * N * N;
        const double gflops = (seconds > 0.0) ? flop / seconds / 1e9 : 0.0;

        auto report = [&](std::ostream& os) {
            os << "ЛАБОРАТОРНАЯ РАБОТА: 1\n\n";
            os << "ВХОДНЫЕ ДАННЫЕ:\n\n";
            os << "Размер матрицы: " << N << "x" << N << "\n\n";
            os << "Матрица A: " << fileA << "\n";
            os << "Матрица B: " << fileB << "\n\n";
            os << "РЕЗУЛЬТАТЫ\n";
            os << "Результат в: " << fileC << "\n\n";
            os << "СТАТИСТИКА ВЫПОЛНЕНИЯ\n";
            os << std::fixed;
            os << "Время выполнения: " << std::setprecision(6) << seconds * 1000.0 << " ms\n";
            os << "Объем задачи (операций): " << operations << "\n";
            os << "Производительность: " << std::setprecision(4) << gflops << " GFLOPS\n";
        };

        report(std::cout);
        std::ofstream sout(fileStats);
        if (sout) {
            report(sout);
        } else {
            std::cerr << "Предупреждение: не удалось записать " << fileStats << "\n";
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
