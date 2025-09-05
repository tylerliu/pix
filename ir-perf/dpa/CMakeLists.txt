# DPA backend build integration

if (NOT ENABLE_DPA)
  return()
endif()

find_program(DPACC /opt/mellanox/doca/tools/dpacc)
if (NOT DPACC)
  message(WARNING "dpacc not found; DPA targets will be unavailable")
  return()
endif()

find_path(DOCA_INCLUDE_DIR NAMES doca_dpa.h HINTS /opt/mellanox/doca/include)
find_library(DOCA_DPA_LIB NAMES doca_dpa HINTS /opt/mellanox/doca/lib /opt/mellanox/doca/lib/x86_64-linux-gnu)
find_library(DOCA_COMMON_LIB NAMES doca_common HINTS /opt/mellanox/doca/lib /opt/mellanox/doca/lib/x86_64-linux-gnu)
find_library(FLEXIO_LIB NAMES flexio HINTS /opt/mellanox/flexio/lib)
find_library(MLX5_LIB NAMES mlx5)
find_library(IBVERBS_LIB NAMES ibverbs)

if (NOT DOCA_INCLUDE_DIR OR NOT DOCA_DPA_LIB OR NOT DOCA_COMMON_LIB OR NOT FLEXIO_LIB OR NOT MLX5_LIB OR NOT IBVERBS_LIB)
  message(WARNING "Missing DOCA/FlexIO libs; DPA targets will be unavailable")
  return()
endif()

set(DPA_LL_DIR ${CMAKE_BINARY_DIR}/dpa_ll)
set(DPA_ARTIFACTS_DIR ${CMAKE_BINARY_DIR}/dpa_artifacts)

file(MAKE_DIRECTORY ${DPA_LL_DIR})
file(MAKE_DIRECTORY ${DPA_ARTIFACTS_DIR})

# Convert existing CPU-oriented IR to DPA kernels
# Enumerate existing bench_*.ll produced by root CMake (from cached var)
set(SRC_LL_FILES ${BENCH_LL_FILES})

# Per-benchmark conversion rules
set(CONVERTED_LL)
foreach(SRC_LL ${SRC_LL_FILES})
  # Resolve to absolute path in case entries are relative
  get_filename_component(SRC_LL_ABS ${SRC_LL} ABSOLUTE BASE_DIR ${CMAKE_BINARY_DIR})
  get_filename_component(BENCH_NAME ${SRC_LL} NAME_WE)
  set(OUT_LL ${DPA_LL_DIR}/${BENCH_NAME}.ll)
  add_custom_command(
    OUTPUT ${OUT_LL}
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/convert_to_dpa_ll.py --in-ll ${SRC_LL_ABS} --out-ll ${OUT_LL}
    DEPENDS ${SRC_LL_ABS}
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Converting ${BENCH_NAME} to DPA kernel"
  )
  list(APPEND CONVERTED_LL ${OUT_LL})
endforeach()

add_custom_target(dpa_convert ALL DEPENDS ${CONVERTED_LL})

# Ensure original IRs are generated before conversion
add_dependencies(dpa_convert ir_bench_ll)

# Enumerate converted LLs
file(GLOB DPA_LL_FILES ${DPA_LL_DIR}/bench_*.ll)

# Build dpacc archives per bench and host runner
# Build an archive per converted bench via dpacc
set(DPA_ARCHIVES)
foreach(LL ${DPA_LL_FILES})
  get_filename_component(BENCH_NAME ${LL} NAME_WE)
  set(OUT_A ${DPA_ARTIFACTS_DIR}/${BENCH_NAME}.a)
  add_custom_command(
    OUTPUT ${OUT_A}
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/build_one_bench.py --ll ${LL} --out-dir ${DPA_ARTIFACTS_DIR}
    DEPENDS dpa_convert ${LL}
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Building dpacc archive for ${BENCH_NAME}"
  )
  list(APPEND DPA_ARCHIVES ${OUT_A})
endforeach()

add_custom_target(dpa_benches DEPENDS ${DPA_ARCHIVES})


