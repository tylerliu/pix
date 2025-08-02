%func_ptr = load i64 (i64)*, i64 (i64)** @function_ptr
%result = call i64 %func_ptr(i64 %iv)
%next_op1 = add i64 %op1, %result 