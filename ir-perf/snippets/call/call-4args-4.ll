%result1 = call i64 @helper_4args(i64 %iv, i64 %iv, i64 %iv, i64 %iv)
%result2 = call i64 @helper_4args(i64 %iv, i64 %iv, i64 %iv, i64 %iv)
%result3 = call i64 @helper_4args(i64 %iv, i64 %iv, i64 %iv, i64 %iv)
%result4 = call i64 @helper_4args(i64 %iv, i64 %iv, i64 %iv, i64 %iv)
%sum1 = add i64 %result1, %result2
%sum2 = add i64 %result3, %result4
%total = add i64 %sum1, %sum2
%next_op1 = add i64 %op1, %total 