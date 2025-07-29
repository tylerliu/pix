
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

################################################################################
# Function for compiling bitcode
################################################################################
function(compile_bitcode_library library_name source_files compile_cc_flags compile_cxx_flags opt_suffix)
    # Compile every source file
    set(BC_FILES)
    foreach(source_file ${source_files})
        # Get filename without extension
        get_filename_component(file_name_only "${source_file}" NAME_WE)
        set(bc_file "${CMAKE_CURRENT_BINARY_DIR}/${file_name_only}${opt_suffix}.bc" )
        get_filename_component(source_file_type "${source_file}" EXT)
        if("${source_file_type}" STREQUAL ".cpp")
            add_custom_command(
                    OUTPUT ${bc_file}
                    COMMAND ${LLVMCXX} -c "-emit-llvm" ${compile_cxx_flags} "${source_file}" -o ${bc_file}
                    DEPENDS ${source_file}
            )
        else()
            add_custom_command(
                    OUTPUT ${bc_file}
                    COMMAND ${LLVMCC} -c "-emit-llvm" ${compile_cc_flags} "${source_file}" -o ${bc_file}
                    DEPENDS ${source_file}
            )
        endif()

        list(APPEND BC_FILES ${bc_file})
    endforeach()

    # Add command to link them to an archive
    add_custom_command(
            OUTPUT ${library_name}
            COMMAND ${LLVM_AR} rcs ${library_name} ${BC_FILES}
            DEPENDS ${BC_FILES}
    )
endfunction(compile_bitcode_library)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Define template types
set(TEMPLATE_TYPES arithmetic memory phi pointer fp-arithmetic conversion)

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