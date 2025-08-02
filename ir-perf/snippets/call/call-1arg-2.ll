%result1 = call i64 @helper_1arg(i64 %iv)
%result2 = call i64 @helper_1arg(i64 %iv)
%sum = add i64 %result1, %result2
%next_op1 = add i64 %op1, %sum 