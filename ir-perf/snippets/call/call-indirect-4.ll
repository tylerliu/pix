%func_ptr1 = load i64 (i64)*, i64 (i64)** @function_ptr
%result1 = call i64 %func_ptr1(i64 %iv)
%func_ptr2 = load i64 (i64)*, i64 (i64)** @function_ptr
%result2 = call i64 %func_ptr2(i64 %iv)
%func_ptr3 = load i64 (i64)*, i64 (i64)** @function_ptr
%result3 = call i64 %func_ptr3(i64 %iv)
%func_ptr4 = load i64 (i64)*, i64 (i64)** @function_ptr
%result4 = call i64 %func_ptr4(i64 %iv)
%sum1 = add i64 %result1, %result2
%sum2 = add i64 %result3, %result4
%total = add i64 %sum1, %sum2
%next_op1 = add i64 %op1, %total 