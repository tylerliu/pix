gcc hello_world.c -o hello_world \
	dpa_program.a \
	-I/opt/mellanox/doca/include/ \
	-DDOCA_ALLOW_EXPERIMENTAL_API \
	-L/opt/mellanox/doca/lib/x86_64-linux-gnu/ -ldoca_dpa -ldoca_common \
	-L/opt/mellanox/flexio/lib/ -lflexio \
	-lstdc++ -libverbs -lmlx5
