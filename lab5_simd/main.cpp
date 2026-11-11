#include <stdio.h>
#include <algorithm>
#include <cstring>
#include <cstdlib>
#include <cstdint>
#include <math.h>
#include "CS149intrin.h"
#include "logger.h"
using namespace std;

#define EXP_MAX 10

Logger CS149Logger;

void usage(const char* progname);
void initValue(float* values, int* exponents, float* output, float* gold, unsigned int N);
void absSerial(float* values, float* output, int N);
void absVector(float* values, float* output, int N);
void clampedExpSerial(float* values, int* exponents, float* output, int N);
void clampedExpVector(float* values, int* exponents, float* output, int N);
float arraySumSerial(float* values, int N);
float arraySumVector(float* values, int N);
bool verifyResult(float* values, int* exponents, float* output, float* gold, int N);

int main(int argc, char * argv[]) {
  int N = 16;
  bool printLog = false;

  // parse commandline options ////////////////////////////////////////////
  for (int arg = 1; arg < argc; ++arg) {
    if ((!strcmp(argv[arg], "-s") || !strcmp(argv[arg], "--size")) && arg+1 < argc) {
      char* end = nullptr;
      long size = strtol(argv[++arg], &end, 10);
      if (*end || size <= 0 || size > 10000000) return 1;
      N = static_cast<int>(size);
    } else if (!strcmp(argv[arg], "-l") || !strcmp(argv[arg], "--log")) printLog = true;
    else { usage(argv[0]); return 1; }
  }


  float* values = new float[N+VECTOR_WIDTH];
  int* exponents = new int[N+VECTOR_WIDTH];
  float* output = new float[N+VECTOR_WIDTH];
  float* gold = new float[N+VECTOR_WIDTH];
  initValue(values, exponents, output, gold, N);

  clampedExpSerial(values, exponents, gold, N);
  clampedExpVector(values, exponents, output, N);

  //absSerial(values, gold, N);
  //absVector(values, output, N);

  printf("CLAMPED EXPONENT (required) \n");
  bool clampedCorrect = verifyResult(values, exponents, output, gold, N);
  if (printLog) CS149Logger.printLog();
  CS149Logger.printStats();

  printf("************************ Result Verification *************************\n");
  if (!clampedCorrect) {
    printf("@@@ Failed!!!\n");
  } else {
    printf("Passed!!!\n");
  }

  bool sumCorrect = true;
  printf("\nARRAY SUM (bonus) \n");
  if (N % VECTOR_WIDTH == 0) {
    float sumGold = arraySumSerial(values, N);
    float sumOutput = arraySumVector(values, N);
    float epsilon = 0.1;
    sumCorrect = abs(sumGold - sumOutput) < epsilon * 2;
    if (!sumCorrect) {
      printf("Expected %f, got %f\n.", sumGold, sumOutput);
      printf("@@@ Failed!!!\n");
    } else {
      printf("Passed!!!\n");
    }
  } else {
    printf("Must have N %% VECTOR_WIDTH == 0 for this problem (VECTOR_WIDTH is %d)\n", VECTOR_WIDTH);
  }

  delete [] values;
  delete [] exponents;
  delete [] output;
  delete [] gold;

  return clampedCorrect && sumCorrect ? 0 : 1;
}

void usage(const char* progname) {
  printf("Usage: %s [options]\n", progname);
  printf("Program Options:\n");
  printf("  -s  --size <N>     Use workload size N (Default = 16)\n");
  printf("  -l  --log          Print vector unit execution log\n");
  printf("  -?  --help         This message\n");
}

void initValue(float* values, int* exponents, float* output, float* gold, unsigned int N) {
  // Fixed, portable generator: identical input for all widths and operating systems.
  uint32_t state = 42;
  auto next = [&]() { state = state*1664525u + 1013904223u; return state; };
  for (unsigned int i=0; i<N+VECTOR_WIDTH; i++)
  {
    // random input values
    values[i] = -1.f + 4.f * static_cast<float>(next() >> 8) / 16777215.f;
    exponents[i] = (next() >> 16) % EXP_MAX;
    output[i] = 0.f;
    gold[i] = 0.f;
  }

}

bool verifyResult(float* values, int* exponents, float* output, float* gold, int N) {
  int incorrect = -1;
  float epsilon = 0.00001;
  for (int i=0; i<N+VECTOR_WIDTH; i++) {
    if ( abs(output[i] - gold[i]) > epsilon ) {
      incorrect = i;
      break;
    }
  }

  if (incorrect != -1) {
    if (incorrect >= N)
      printf("You have written to out of bound value!\n");
    printf("Wrong calculation at value[%d]!\n", incorrect);
    printf("value  = ");
    for (int i=0; i<N; i++) {
      printf("% f ", values[i]);
    } printf("\n");

    printf("exp    = ");
    for (int i=0; i<N; i++) {
      printf("% 9d ", exponents[i]);
    } printf("\n");

    printf("output = ");
    for (int i=0; i<N; i++) {
      printf("% f ", output[i]);
    } printf("\n");

    printf("gold   = ");
    for (int i=0; i<N; i++) {
      printf("% f ", gold[i]);
    } printf("\n");
    return false;
  }
  printf("Results matched with answer!\n");
  return true;
}

// computes the absolute value of all elements in the input array
// values, stores result in output
void absSerial(float* values, float* output, int N) {
  for (int i=0; i<N; i++) {
    float x = values[i];
    if (x < 0) {
      output[i] = -x;
    } else {
      output[i] = x;
    }
  }
}


// implementation of absSerial() above, but it is vectorized using CS149 intrinsics
void absVector(float* values, float* output, int N) {
  __cs149_vec_float x;
  __cs149_vec_float result;
  __cs149_vec_float zero = _cs149_vset_float(0.f);
  __cs149_mask maskAll, maskIsNegative, maskIsNotNegative;

//  Note: Take a careful look at this loop indexing.  This example
//  code is not guaranteed to work when (N % VECTOR_WIDTH) != 0.
//  Why is that the case?
  for (int i=0; i<N; i+=VECTOR_WIDTH) {

    // All ones
    maskAll = _cs149_init_ones();

    // All zeros
    maskIsNegative = _cs149_init_ones(0);

    // Load vector of values from contiguous memory addresses
    _cs149_vload_float(x, values+i, maskAll);               // x = values[i];

    // Set mask according to predicate
    _cs149_vlt_float(maskIsNegative, x, zero, maskAll);     // if (x < 0) {

    // Execute instruction using mask ("if" clause)
    _cs149_vsub_float(result, zero, x, maskIsNegative);      //   output[i] = -x;

    // Inverse maskIsNegative to generate "else" mask
    maskIsNotNegative = _cs149_mask_not(maskIsNegative);     // } else {

    // Execute instruction ("else" clause)
    _cs149_vload_float(result, values+i, maskIsNotNegative); //   output[i] = x; }

    // Write results back to memory
    _cs149_vstore_float(output+i, result, maskAll);
  }
}


// accepts an array of values and an array of exponents
//
// For each element, compute values[i]^exponents[i] and clamp value to
// 9.999.  Store result in output.
void clampedExpSerial(float* values, int* exponents, float* output, int N) {
  for (int i=0; i<N; i++) {
    float x = values[i];
    int y = exponents[i];
    if (y == 0) {
      output[i] = 1.f;
    } else {
      float result = x;
      int count = y - 1;
      while (count > 0) {
        result *= x;
        count--;
      }
      if (result > 9.999999f) {
        result = 9.999999f;
      }
      output[i] = result;
    }
  }
}

void clampedExpVector(float* values, int* exponents, float* output, int N) {
  auto zero = _cs149_vset_int(0);
  auto one = _cs149_vset_int(1);
  auto limit = _cs149_vset_float(9.999999f);
  for (int i = 0; i < N; i += VECTOR_WIDTH) {
    auto valid = _cs149_init_ones(std::min(VECTOR_WIDTH, N-i));
    __cs149_vec_float x{}, result{};
    __cs149_vec_int exponent{}, count{};
    auto isZero = _cs149_init_ones(0);
    _cs149_vload_float(x, values+i, valid);
    _cs149_vload_int(exponent, exponents+i, valid);
    _cs149_veq_int(isZero, exponent, zero, valid);
    _cs149_vmove_float(result, x, valid);
    _cs149_vset_float(result, 1.f, isZero);
    _cs149_vsub_int(count, exponent, one, valid);
    auto active = _cs149_init_ones(0);
    _cs149_vgt_int(active, count, zero, valid);
    while (_cs149_cntbits(active)) {
      _cs149_vmult_float(result, result, x, active);
      _cs149_vsub_int(count, count, one, active);
      _cs149_vgt_int(active, count, zero, valid);
    }
    auto large = _cs149_init_ones(0);
    _cs149_vgt_float(large, result, limit, valid);
    _cs149_vmove_float(result, limit, large);
    _cs149_vstore_float(output+i, result, valid);
  }
}

// returns the sum of all elements in values
float arraySumSerial(float* values, int N) {
  float sum = 0;
  for (int i=0; i<N; i++) {
    sum += values[i];
  }

  return sum;
}

// returns the sum of all elements in values
// You can assume N is a multiple of VECTOR_WIDTH
// You can assume VECTOR_WIDTH is a power of 2
float arraySumVector(float* values, int N) {
  auto all = _cs149_init_ones();
  auto sum = _cs149_vset_float(0.f);
  for (int i = 0; i < N; i += VECTOR_WIDTH) {
    __cs149_vec_float x{};
    auto valid = _cs149_init_ones(std::min(VECTOR_WIDTH, N-i));
    _cs149_vload_float(x, values+i, valid);
    _cs149_vadd_float(sum, sum, x, all);
  }
  // Bonus: tree reduction for powers of two, scalar reduction otherwise.
  if ((VECTOR_WIDTH & (VECTOR_WIDTH-1)) == 0) {
    for (int remaining = VECTOR_WIDTH; remaining > 1; remaining /= 2) {
      __cs149_vec_float pairs{}, packed{};
      _cs149_hadd_float(pairs, sum);
      _cs149_interleave_float(packed, pairs);
      sum = packed;
    }
    return sum.value[0];
  }
  float total = 0;
  for (int lane = 0; lane < VECTOR_WIDTH; ++lane) total += sum.value[lane];
  return total;
}

