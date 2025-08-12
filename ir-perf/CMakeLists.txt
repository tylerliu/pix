
cmake_minimum_required(VERSION 3.13)
project(ir-perf LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD_REQUIRED ON)

################################################################################
# Find bitcode compiler
################################################################################
include("${CMAKE_SOURCE_DIR}/cmake/find_bitcode_compiler.cmake")
message(STATUS "LLVMCC: ${LLVMCC}")
if (NOT EXISTS "${LLVMCC}")
  message(FATAL_ERROR "Cannot find C bitcode compiler \"${LLVMCC}\"")
endif()
message(STATUS "LLVMCXX: ${LLVMCXX}")
if (NOT EXISTS "${LLVMCXX}")
  message(FATAL_ERROR "Cannot find C++ bitcode compiler \"${LLVMCXX}\"")
endif()
message(STATUS "LLC: ${LLVMLLC}")
if (NOT EXISTS "${LLVMLLC}")
  message(FATAL_ERROR "Cannot find IR compiler \"${LLVMLLC}\"")
endif()

###############################################################################
# Set LLVM compiler as the default
###############################################################################
set(CMAKE_C_COMPILER ${LLVMCC})
set(CMAKE_CXX_COMPILER ${LLVMCXX})

# Disable PIE to avoid relocation issues with large global arrays
set(CMAKE_POSITION_INDEPENDENT_CODE OFF)
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -no-pie")

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Define template types
set(TEMPLATE_TYPES arithmetic memory pointer fp-arithmetic conversion branching call alloca)

foreach(TEMPLATE_TYPE ${TEMPLATE_TYPES})
    # Find all snippet files for this template type
    file(GLOB SNIPPET_FILES "${CMAKE_CURRENT_SOURCE_DIR}/snippets/${TEMPLATE_TYPE}/*.ll")
    
    foreach(SNIPPET_FILE ${SNIPPET_FILES})
        get_filename_component(SNIPPET_NAME ${SNIPPET_FILE} NAME_WE)
        set(GEN_LL "${CMAKE_CURRENT_BINARY_DIR}/bench_${TEMPLATE_TYPE}_${SNIPPET_NAME}.ll")
        set(GEN_OBJ "${CMAKE_CURRENT_BINARY_DIR}/bench_${TEMPLATE_TYPE}_${SNIPPET_NAME}.o")
        set(EXE_NAME "bench_${TEMPLATE_TYPE}_${SNIPPET_NAME}")

        # Generate .ll file from template and snippet
        add_custom_command(
            OUTPUT ${GEN_LL}
            COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/generate_bench_ll.py
                    ${TEMPLATE_TYPE}
                    ${CMAKE_CURRENT_SOURCE_DIR}/templates/${TEMPLATE_TYPE}.ll
                    ${SNIPPET_FILE}
                    ${GEN_LL}
            DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/templates/${TEMPLATE_TYPE}.ll ${SNIPPET_FILE}
        )

        # Compile .ll to .o
        add_custom_command(
            OUTPUT ${GEN_OBJ}
            COMMAND ${LLVMLLC} -O0 -filetype=obj -o ${GEN_OBJ} ${GEN_LL}
            DEPENDS ${GEN_LL}
        )

        # Add executable for each snippet
        add_executable(${EXE_NAME} bench-driver.c ${GEN_OBJ})
        
        # Link against math library only for frem operations
        if(SNIPPET_NAME MATCHES "frem")
            target_link_libraries(${EXE_NAME} m)
        endif()
    endforeach()
endforeach()

################################################################################
# Generate load latency benchmarks
################################################################################

# Generate load latency benchmarks using Python script during cmake configuration
execute_process(
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/generate_load_benchmarks.py ${CMAKE_CURRENT_BINARY_DIR}
    RESULT_VARIABLE BENCHMARK_GEN_RESULT
    OUTPUT_VARIABLE BENCHMARK_GEN_OUTPUT
    ERROR_VARIABLE BENCHMARK_GEN_ERROR
)

if(BENCHMARK_GEN_RESULT EQUAL 0)
    message(STATUS "Load latency benchmarks generated successfully")
    if(BENCHMARK_GEN_OUTPUT)
        message(STATUS "${BENCHMARK_GEN_OUTPUT}")
    endif()
else()
    message(WARNING "Failed to generate load latency benchmarks: ${BENCHMARK_GEN_ERROR}")
endif()

# Include the generated benchmark list
set(LOAD_BENCHMARKS_CMAKE "${CMAKE_CURRENT_BINARY_DIR}/load_benchmarks.cmake")
if(EXISTS ${LOAD_BENCHMARKS_CMAKE})
    include(${LOAD_BENCHMARKS_CMAKE})
    
    # Create executables for each generated benchmark
    foreach(BENCHMARK_FILE ${LOAD_BENCHMARK_FILES})
        get_filename_component(BENCH_NAME ${BENCHMARK_FILE} NAME_WE)
        set(GEN_LL "${CMAKE_CURRENT_BINARY_DIR}/${BENCHMARK_FILE}")
        set(GEN_OBJ "${CMAKE_CURRENT_BINARY_DIR}/${BENCH_NAME}.o")
        
        # Compile .ll to .o
        add_custom_command(
            OUTPUT ${GEN_OBJ}
            COMMAND ${LLVMLLC} -O0 -filetype=obj -o ${GEN_OBJ} ${GEN_LL}
            DEPENDS ${GEN_LL}
        )
        
        # Add executable with bench_memory_ prefix
        add_executable(bench_memory_${BENCH_NAME} bench-driver.c ${GEN_OBJ})
    endforeach()
else()
    message(STATUS "Load benchmark list not found. Benchmarks may not have been generated.")
endif()

################################################################################
# Optional: DOCA Telemetry DPA helper
################################################################################

option(ENABLE_DPA "Enable building DPA telemetry helper if DOCA is available" ON)
if (ENABLE_DPA)
    find_library(DOCA_TELEMETRY_DPA_LIB NAMES doca_telemetry_dpa)
    find_path(DOCA_INCLUDE_DIR NAMES doca_telemetry_dpa.h
        HINTS /opt/mellanox/doca/include /usr/include /usr/local/include)

    if (DOCA_TELEMETRY_DPA_LIB AND DOCA_INCLUDE_DIR)
        message(STATUS "Found DOCA Telemetry DPA: lib=${DOCA_TELEMETRY_DPA_LIB} include=${DOCA_INCLUDE_DIR}")
        add_executable(dpa_telemetry_helper dpa_telemetry_helper.c)
        target_include_directories(dpa_telemetry_helper PRIVATE ${DOCA_INCLUDE_DIR})
        target_link_libraries(dpa_telemetry_helper ${DOCA_TELEMETRY_DPA_LIB})
        target_compile_definitions(dpa_telemetry_helper PRIVATE HAVE_DOCA_TELEMETRY_DPA=1)
    else()
        message(STATUS "DOCA Telemetry DPA not found. 'dpa_telemetry_helper' will not be built.")
    endif()
endif()