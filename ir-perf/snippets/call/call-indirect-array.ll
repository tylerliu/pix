%idx = and i64 %iv, 3
%func_ptr = getelementptr inbounds [4 x i64 (i64)*], [4 x i64 (i64)*]* @function_array, i64 0, i64 %idx
%func = load i64 (i64)*, i64 (i64)** %func_ptr
%result = call i64 %func(i64 %iv)
%next_op1 = add i64 %op1, %result 