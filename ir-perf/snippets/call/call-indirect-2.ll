%func_ptr1 = load i64 (i64)*, i64 (i64)** @function_ptr
%result1 = call i64 %func_ptr1(i64 %iv)
%func_ptr2 = load i64 (i64)*, i64 (i64)** @function_ptr
%result2 = call i64 %func_ptr2(i64 %iv)
%sum = add i64 %result1, %result2
%next_op1 = add i64 %op1, %sum 