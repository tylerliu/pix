
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