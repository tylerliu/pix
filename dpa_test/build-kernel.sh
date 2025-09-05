/opt/mellanox/doca/tools/dpacc \
	kernel.c \
	-o dpa_program.a \
	-mcpu=nv-dpa-bf3 \
	-hostcc=gcc \
	-hostcc-options="-Wno-deprecated-declarations -Werror -Wall -Wextra -W" \
	--devicecc-options="-D__linux__ -Wno-deprecated-declarations -Werror -Wall -Wextra -W" \
	--app-name="dpa_hello_world_app" \
	--ldoca_dpa \
	--dryrun \
	-I/opt/mellanox/doca/include/
